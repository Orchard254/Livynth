"""Synthetic acceptance and failure-injection tests for narration PCM WAV."""
import math
import tempfile
import unittest
import wave
from pathlib import Path

from video.wav_qa import inspect_narration_wav, InvalidNarration


def make_wav(path, *, rate=16000, channels=1, width=2, duration=.6,
             amplitude=.1, frequency=220, dc=0.0, one_spike=False):
    frames = int(rate * duration)
    payload = bytearray()
    for i in range(frames):
        sample = dc + (amplitude * math.sin(2 * math.pi * frequency * i / rate))
        if one_spike:
            sample = 0.6 if i == 100 else 0
        sample = max(-0.98, min(.98, sample))
        for j in range(channels):
            value = -sample if j == 1 else sample
            integer = int(round(value * ((1 << (width * 8 - 1)) - 1)))
            if width == 1:
                payload.append(max(0, min(255, integer + 128)))
            else:
                payload.extend(integer.to_bytes(width, 'little', signed=True))
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(channels)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(bytes(payload))


class WavSignalQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'voice.wav'

    def test_mono_speech_like_tone_accepted(self):
        make_wav(self.path)
        actual = inspect_narration_wav(self.path)
        self.assertEqual(actual['status'], 'PASS_SIGNAL_NOT_SPEECH_QUALITY')
        self.assertGreater(actual['active_signal_s'], .12)
        self.assertGreater(actual['loudest_block_dbfs'], -55)

    def test_silent_16bit_rejected(self):
        make_wav(self.path, amplitude=0)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            inspect_narration_wav(self.path)

    def test_unsigned_8bit_silence_rejected(self):
        make_wav(self.path, width=1, amplitude=0)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            inspect_narration_wav(self.path)

    def test_8bit_signal_accepted(self):
        make_wav(self.path, width=1, amplitude=.2)
        self.assertEqual(inspect_narration_wav(self.path)['sample_width_bits'], 8)

    def test_24bit_signal_accepted(self):
        make_wav(self.path, width=3)
        self.assertEqual(inspect_narration_wav(self.path)['sample_width_bits'], 24)

    def test_32bit_signal_accepted(self):
        make_wav(self.path, width=4)
        self.assertEqual(inspect_narration_wav(self.path)['sample_width_bits'], 32)

    def test_stereo_out_of_phase_signal_accepted(self):
        make_wav(self.path, channels=2)
        result = inspect_narration_wav(self.path)
        self.assertEqual(result['channels'], 2)

    def test_nonzero_dc_is_not_counted_as_voice(self):
        make_wav(self.path, amplitude=0, dc=.25)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            inspect_narration_wav(self.path)

    def test_click_is_not_accepted_as_speech(self):
        make_wav(self.path, one_spike=True)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            inspect_narration_wav(self.path)

    def test_extremely_quiet_signal_rejected(self):
        make_wav(self.path, amplitude=0.0001)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_NO_MEANINGFUL_SIGNAL'):
            inspect_narration_wav(self.path)

    def test_short_audio_rejected(self):
        make_wav(self.path, duration=.2)
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_DURATION_OUT_OF_RANGE'):
            inspect_narration_wav(self.path)

    def test_missing_and_nonwave_rejected(self):
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_UNREADABLE'):
            inspect_narration_wav(self.path)
        self.path.write_bytes(b'NOT_WAVE_FILE')
        with self.assertRaisesRegex(InvalidNarration, 'E_WAV_UNREADABLE'):
            inspect_narration_wav(self.path)

    def test_file_not_modified(self):
        make_wav(self.path)
        data = self.path.read_bytes()
        inspect_narration_wav(self.path)
        self.assertEqual(data, self.path.read_bytes())


if __name__ == '__main__':
    unittest.main()
