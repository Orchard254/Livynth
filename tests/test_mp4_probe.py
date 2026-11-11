import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from video.mp4_probe import inspect_mp4, InvalidMp4


def box(name, payload):
    return (len(payload)+8).to_bytes(4, 'big') + name.encode('ascii') + payload


def synthetic_mp4(*, sound=True, video=True, bad_size=False, empty_media=False):
    ftyp = box('ftyp', b'isom\0\0\0\x01isom')
    tracks=[]
    for name in (['vide'] if video else []) + (['soun'] if sound else []):
        hdlr=box('hdlr', b'\0'*8 + name.encode('ascii') + b'\0'*8)
        mdia=box('mdia', hdlr)
        tkhd=box('tkhd', b'\0'*12 + ((540 if name=='vide' else 0)<<16).to_bytes(4,'big') + ((960 if name=='vide' else 0)<<16).to_bytes(4,'big'))
        tracks.append(box('trak',tkhd+mdia))
    moov=box('moov',b''.join(tracks))
    mdat=box('mdat',b'' if empty_media else b'\x12'*200)
    if bad_size:
        moov=(4294967295).to_bytes(4,'big')+moov[4:]
    return ftyp+moov+mdat


class MP4ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'clip.mp4'

    def check(self, **options):
        self.path.write_bytes(synthetic_mp4(**options))
        return inspect_mp4(self.path)

    def test_video_audio_tracks_present(self):
        result=self.check()
        self.assertEqual(result['video_tracks'],1)
        self.assertEqual(result['audio_tracks'],1)
        self.assertEqual(result['first_video_width'],540)
        self.assertEqual(result['first_video_height'],960)
        self.assertEqual(result['status'],'PASS_TRACK_PRESENCE_NOT_PLAYBACK')

    def test_missing_audio_fails_closed(self):
        with self.assertRaisesRegex(InvalidMp4,'E_MP4_AUDIO_TRACK_MISSING'):
            self.check(sound=False)

    def test_missing_video_fails_closed(self):
        with self.assertRaisesRegex(InvalidMp4,'E_MP4_VIDEO_TRACK_MISSING'):
            self.check(video=False)

    def test_bad_box_size(self):
        with self.assertRaisesRegex(InvalidMp4,'E_INVALID_MP4_BOX_SIZE'):
            self.check(bad_size=True)

    def test_empty_media_data(self):
        with self.assertRaisesRegex(InvalidMp4,'E_MP4_EMPTY_MEDIA_DATA'):
            self.check(empty_media=True)

    def test_not_an_mp4(self):
        self.path.write_bytes(b'not mp4'*100)
        with self.assertRaises(InvalidMp4):inspect_mp4(self.path)

    def test_no_file(self):
        with self.assertRaisesRegex(InvalidMp4,'E_MP4_MISSING_OR_EMPTY'):
            inspect_mp4(self.path)


if __name__=='__main__':unittest.main()