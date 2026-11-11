"""Offline Studio orchestration tests (not Blender rendering tests)."""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import livynth_studio as studio


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.glb = self.folder / 'existing.glb'
        self.glb.write_bytes(b'glTF'+b'0'*1000)
        self.wav = self.folder / 'voice.wav'
        with wave.open(str(self.wav), 'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(b'\0\0' * 16000)

    def plan(self, mode='preview'):
        return studio.make_plan(text='Hello from Studio.', mode=mode, output_dir=self.folder,
                   blender='fake-blender', glb=self.glb, audio=self.wav)

    def test_preview_plan_uses_existing_inputs(self):
        tasks=self.plan()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].artifact.name, 'livynth_preview.png')
        self.assertIn('--preview', tasks[0].argv)
        self.assertNotIn('--max-frames', tasks[0].argv)

    def test_smoke_and_final_plan_are_distinct(self):
        smoke=self.plan('smoke')[0]
        final=self.plan('video')[0]
        self.assertEqual(smoke.artifact.suffix, '.mp4')
        self.assertIn('--max-frames', smoke.argv)
        self.assertEqual(smoke.argv[smoke.argv.index('--max-frames')+1], '30')
        self.assertNotIn('--max-frames', final.argv)
        self.assertNotEqual(smoke.artifact, final.artifact)

    def test_reject_missing_inputs(self):
        with self.assertRaisesRegex(ValueError, 'GLB character does not exist'):
            studio.make_plan(text='hello', mode='preview', output_dir=self.folder,
                             blender='fake', glb=self.folder/'no.glb', audio=self.wav)
        with self.assertRaisesRegex(ValueError, 'Voice WAV does not exist'):
            studio.make_plan(text='hello', mode='preview', output_dir=self.folder,
                             blender='fake', glb=self.glb, audio=self.folder/'no.wav')

    def test_reject_empty_and_overlong_scripts(self):
        for text in ['', '  ', 'x'*2001]:
            with self.subTest(textlen=len(text)), self.assertRaises(ValueError):
                studio.make_plan(text=text, mode='preview', output_dir=self.folder,
                                 blender='fake', glb=self.glb, audio=self.wav)

    def test_reject_nonwindows_tts(self):
        if sys.platform == 'win32':
            self.skipTest('Windows has built-in System.Speech')
        with self.assertRaisesRegex(ValueError, 'requires Windows'):
            studio.make_plan(text='hello', mode='video', output_dir=self.folder,
                             blender='fake', glb=self.glb, audio=None)

    def test_accept_pcm_wav(self):
        studio.check_output(studio.Task('Voice', (), self.wav, 'wav'))

    def test_reject_fake_mp4(self):
        p=self.folder/'fake.mp4';p.write_bytes(b'not mp4'*30)
        with self.assertRaisesRegex(ValueError, 'E_INVALID_MP4_BOX_SIZE'):
            studio.check_output(studio.Task('Video', (), p, 'mp4'))

    def test_reject_incomplete_glb_audit(self):
        report = {'errors':[], 'assertions_passed':True,
                  'glb_audit':{'joint_count':162,'morph_targets_in_exported_glb':67}}
        (self.folder/'character_report.json').write_text(json.dumps(report),encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'lost required'):
            studio.check_output(studio.Task('Character', (), self.glb, 'glb'))

    def test_exec_writes_manifest_for_success(self):
        output=self.folder/'sample.png'
        script=f'from pathlib import Path;Path({str(output)!r}).write_bytes(bytes.fromhex("89504e470d0a1a0a")+bytes(128))'
        task=studio.Task('Preview', (sys.executable,'-c',script), output, 'png')
        messages=[]
        report=studio.execute([task],output_dir=self.folder,log=messages.append)
        self.assertEqual(report['status'],'PASS_ARTIFACTS_NOT_IDENTITY')
        self.assertEqual(report['video_audio_stream'],'UNVERIFIED_REQUIRES_PLAYBACK')
        self.assertTrue((self.folder/'studio_run.json').is_file())
        self.assertTrue(any('Saved' in msg for msg in messages))

    def test_exec_fail_is_reported(self):
        output=self.folder/'missing.png'
        task=studio.Task('Fail', (sys.executable,'-c','raise RuntimeError("failed")'), output,'png')
        with self.assertRaises(RuntimeError):
            studio.execute([task],output_dir=self.folder,log=lambda msg: None)
        report=json.loads((self.folder/'studio_run.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'],'FAILED')


if __name__ == '__main__':unittest.main()