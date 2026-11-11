"""Offline M001 unit tests: no Blender and no external models needed."""
import json
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from video.make_timeline import (
    approximate_words, blink, make_timeline, read_wav_energy,
    smoothstep, validate_words, visemes_for
)
from video.model_check import inspect_glb


def make_wav(path, seconds=2, sample_rate=8000, amplitude=0.18):
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        data=[]
        for i in range(int(sample_rate*seconds)):
            t=i/sample_rate
            strength=amplitude if 0.2<t<seconds-0.15 else 0
            sample=int(32767*strength*math.sin(2*math.pi*220*t))
            data.append(struct.pack('<h',sample))
        wav.writeframes(b''.join(data))


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.audio=Path(self.tmp.name)/'test.wav'
        make_wav(self.audio)

    def tearDown(self):
        self.tmp.cleanup()

    def test_wav_read(self):
        duration,energy=read_wav_energy(self.audio,30)
        self.assertAlmostEqual(duration,2,places=2)
        self.assertEqual(len(energy),60)
        self.assertLess(energy[0],0.001)
        self.assertGreater(max(energy),0.08)

    def test_visemes(self):
        self.assertEqual(visemes_for('TH'),['viseme_TH'])
        self.assertEqual(visemes_for('SH'),['viseme_CH'])
        self.assertEqual(visemes_for('M'),['viseme_PP'])
        self.assertEqual(visemes_for('OO'),['viseme_U'])

    def test_approximate_word_times(self):
        duration,energy=read_wav_energy(self.audio,30)
        words=approximate_words('Hello, world!',duration,energy,30)
        self.assertEqual(len(words),2)
        self.assertGreater(words[0]['start'],0)
        self.assertLessEqual(words[-1]['end'],duration)

    def test_word_times_validation(self):
        valid=validate_words([{'text':'hi','start':0.2,'end':0.6}],2)
        self.assertEqual(valid[0]['text'],'hi')
        with self.assertRaises(ValueError):
            validate_words([{'text':'x','start':1.1,'end':0.4}],2)
        with self.assertRaises(ValueError):
            validate_words([{'text':'x','start':0.1,'end':1.0},
                            {'text':'y','start':0.8,'end':1.4}],2)

    def test_smoothstep_clamped(self):
        self.assertEqual(smoothstep(-50),0)
        self.assertEqual(smoothstep(50),1)

    def test_blink_profile(self):
        self.assertEqual(blink(0.5,2),0)
        self.assertEqual(blink(2.13,2),1)
        self.assertEqual(blink(2.4,2),0)

    def test_bounded_shapes(self):
        timeline=make_timeline(self.audio,'Hello world')
        self.assertEqual(timeline['schema'],'livynth.timeline.v1')
        self.assertEqual(len(timeline['frames']),60)
        self.assertTrue(all(0<=v<=1 for fr in timeline['frames']
                            for v in fr['morphs'].values()))
        self.assertTrue(any(fr['morphs']['jawOpen']>0 for fr in timeline['frames']))
        self.assertEqual(timeline['frames'][0]['morphs']['jawOpen'],0)

    def test_timeline_json(self):
        self.assertIn('frames',json.loads(json.dumps(make_timeline(self.audio,'Test'))))

    def test_silence_gate(self):
        make_wav(self.audio,amplitude=0)
        timeline=make_timeline(self.audio,'no speech')
        self.assertTrue(all(f['morphs']['jawOpen']==0 for f in timeline['frames']))

    def test_fps_validation(self):
        with self.assertRaises(ValueError):
            make_timeline(self.audio,'hello',fps=4)

    def test_reject_invalid_glb(self):
        bad=Path(self.tmp.name)/'bad.glb'
        bad.write_bytes(b'garbage')
        with self.assertRaises(ValueError):
            inspect_glb(bad)


if __name__=='__main__':
    unittest.main()
