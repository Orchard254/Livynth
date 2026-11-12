"""Offline Studio orchestration tests (not Blender rendering tests)."""
import json
import math
import struct
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
            f.writeframes(b''.join(struct.pack('<h',int(9000*math.sin(2*math.pi*220*i/16000))) for i in range(16000)))

    def plan(self, mode='preview'):
        return studio.make_plan(text='Hello from Studio.', mode=mode, output_dir=self.folder,
                   blender='fake-blender', glb=self.glb, audio=self.wav)

    def test_optional_identity_recipe_reaches_mpfb_exporter(self):
        recipe = Path(__file__).resolve().parents[1]/'character/recipes/demo_b.json'
        tasks = studio.make_plan(text='Demo.', mode='preview', output_dir=self.folder,
                                 blender='fake-blender', glb=None, audio=self.wav,
                                 identity_recipe=recipe)
        self.assertEqual([x.kind for x in tasks], ['glb','png'])
        self.assertEqual(tasks[0].argv[tasks[0].argv.index('--identity-recipe')+1],
                         str(recipe.resolve()))

    def test_existing_glb_and_recipe_are_exclusive(self):
        recipe = Path(__file__).resolve().parents[1]/'character/recipes/demo_a.json'
        with self.assertRaisesRegex(ValueError, 'either an existing GLB or an identity recipe'):
            studio.make_plan(text='Demo.',mode='preview',output_dir=self.folder,
                             blender='fake-blender',glb=self.glb,audio=self.wav,
                             identity_recipe=recipe)

    def test_invalid_identity_recipe_rejected_before_subprocess(self):
        bad = self.folder/'fake_recipe.json'
        bad.write_text('{"schema":"fake"}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'E_RECIPE_FIELDS'):
            studio.make_plan(text='Demo.',mode='preview',output_dir=self.folder,
                             blender='fake-blender',glb=None,audio=self.wav,
                             identity_recipe=bad)

    def test_studio_baseline_without_identity_flag_unchanged(self):
        tasks = studio.make_plan(text='Demo.',mode='preview',output_dir=self.folder,
                                 blender='fake-blender',glb=None,audio=self.wav)
        self.assertEqual(tasks[0].kind, 'glb')
        self.assertNotIn('--identity-recipe',tasks[0].argv)

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

    def test_complete_demo_reuses_character_and_audio(self):
        tasks = self.plan('demo')
        self.assertEqual([t.artifact.name for t in tasks],
            ['livynth_preview.png', 'livynth_smoke.mp4', 'livynth_video.mp4'])
        self.assertIn('--preview', tasks[0].argv)
        self.assertIn('--max-frames', tasks[1].argv)
        self.assertNotIn('--max-frames', tasks[2].argv)
        for task in tasks:
            self.assertEqual(task.argv[task.argv.index('--glb')+1], str(self.glb.resolve()))
            self.assertEqual(task.argv[task.argv.index('--audio')+1], str(self.wav.resolve()))

    def test_complete_demo_generates_character_and_voice_once(self):
        with patch.object(studio.os, 'name', 'nt'):
            tasks = studio.make_plan(text='Hello.', mode='demo', output_dir=self.folder,
                blender='fake-blender', glb=None, audio=None)
        self.assertEqual([t.kind for t in tasks], ['glb','wav','png','mp4','mp4'])
        self.assertEqual(sum(t.kind == 'glb' for t in tasks), 1)
        self.assertEqual(sum(t.kind == 'wav' for t in tasks), 1)

    def test_complete_demo_stops_before_full_render_if_smoke_fails(self):
        preview = self.folder / 'preview.png'
        preview_script = ('from pathlib import Path;'
             f'Path({str(preview)!r}).write_bytes(bytes.fromhex("89504e470d0a1a0a")+bytes(128))')
        smoke = self.folder / 'missing.mp4'
        final = self.folder / 'should_not_exist.txt'
        smoke_script = 'print("simulated smoke render did not produce MP4")'
        final_script = f'from pathlib import Path;Path({str(final)!r}).write_text("BAD")'
        tasks = [
            studio.Task('Preview', (sys.executable, '-c', preview_script), preview,'png'),
            studio.Task('Smoke', (sys.executable, '-c', smoke_script), smoke,'mp4'),
            studio.Task('Full', (sys.executable, '-c', final_script), final,'mp4'),
        ]
        with self.assertRaisesRegex(RuntimeError, 'expected output'):
            studio.execute(tasks, output_dir=self.folder, log=lambda _msg: None)
        self.assertFalse(final.exists())
        report = json.loads((self.folder/'studio_run.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'],'FAILED')
        self.assertEqual(report['failed_step'],'Smoke')
        self.assertEqual(len(report['steps']),1)

    def test_video_dimensions_are_qualified(self):
        good = self.folder / 'good.mp4'
        def box(name, payload):
            return (len(payload)+8).to_bytes(4, 'big') + name + payload
        ftyp = box(b'ftyp', b'isom\0\0\0\x01isom')
        trak = b''
        for name in (b'vide', b'soun'):
            hdlr = box(b'hdlr', b'\0'*8 + name + b'\0'*8)
            tkhd = box(b'tkhd', b'\0'*12 +
                       ((540 if name == b'vide' else 0)<<16).to_bytes(4,'big') +
                       ((960 if name == b'vide' else 0)<<16).to_bytes(4,'big'))
            trak += box(b'trak', tkhd + box(b'mdia', hdlr))
        good.write_bytes(ftyp + box(b'moov', trak) + box(b'mdat', b'\x12'*200))
        check = studio.Task('Smoke', (), good, 'mp4', (540, 960))
        self.assertEqual(studio.check_output(check)['audio_tracks'], 1)
        wrong = studio.Task('Full', (), good, 'mp4', (1080, 1920))
        with self.assertRaisesRegex(RuntimeError, 'MP4 dimensions'):
            studio.check_output(wrong)
        self.assertEqual(self.plan('smoke')[0].expected_dimensions, (540,960))
        self.assertEqual(self.plan('video')[0].expected_dimensions, (1080,1920))

    def test_reject_existing_silent_audio_before_render(self):
        silent = self.folder/'silent.wav'
        with wave.open(str(silent), 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b'\0\0' * 16000)
        with self.assertRaisesRegex(ValueError, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            studio.make_plan(text='hello', mode='video', output_dir=self.folder,
                             blender='fake-blender', glb=self.glb, audio=silent)

    def test_reject_generated_silent_audio_after_synthesis(self):
        silent = self.folder/'silent.wav'
        with wave.open(str(silent), 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b'\0\0' * 16000)
        with self.assertRaisesRegex(ValueError, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            studio.check_output(studio.Task('Voice', (), silent, 'wav'))

    def test_execution_preflight_records_existing_narration_signal(self):
        output = self.folder / 'preview.png'
        script = ('from pathlib import Path;'
                  f'Path({str(output)!r}).write_bytes(bytes.fromhex("89504e470d0a1a0a")+bytes(128))')
        task = studio.Task('Render studio preview',
            (sys.executable, '-c', script, '--audio', str(self.wav)), output, 'png')
        report = studio.execute([task], output_dir=self.folder, log=lambda _m: None)
        self.assertEqual(report['narration_signal']['status'], 'PASS_SIGNAL_NOT_SPEECH_QUALITY')
        stored = json.loads((self.folder / 'studio_run.json').read_text(encoding='utf-8'))
        self.assertGreater(stored['narration_signal']['active_signal_s'], 0.12)

    def test_execution_preflight_blocks_silent_narration_before_render(self):
        silent = self.folder / 'silent.wav'
        with wave.open(str(silent), 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b'\0\0' * 16000)
        output = self.folder / 'should_not_exist.png'
        script = f'from pathlib import Path;Path({str(output)!r}).write_bytes(b"bad")'
        task = studio.Task('Render studio preview',
            (sys.executable, '-c', script, '--audio', str(silent)), output, 'png')
        with self.assertRaisesRegex(ValueError, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            studio.execute([task], output_dir=self.folder, log=lambda _m: None)
        self.assertFalse(output.exists())
        report = json.loads((self.folder/'studio_run.json').read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'FAILED')
        self.assertEqual(report['failed_step'], 'Render studio preview')

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
        audit = studio.check_output(studio.Task('Voice', (), self.wav, 'wav'))
        self.assertEqual(audit['status'], 'PASS_SIGNAL_NOT_SPEECH_QUALITY')

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