"""Read-only MP4 track presence and dimensions check (standard-library only).

Checks that MP4 contains at least one video track and one audio track, plus
nonempty media data. Does NOT prove clips are audible, synced, playable,
faithful to reference imagery, or aesthetically acceptable.
"""
from __future__ import annotations

from pathlib import Path


class InvalidMp4(ValueError):
    pass


def _boxes(stream, start, stop):
    """Yield (atom name, payload start, atom end); reject corrupt ranges."""
    p = start
    while p < stop:
        if stop - p < 8:
            raise InvalidMp4('E_TRUNCATED_MP4_BOX_HEADER')
        stream.seek(p)
        header = stream.read(8)
        size = int.from_bytes(header[:4], 'big')
        name = header[4:8]
        header_len = 8
        if size == 1:
            if stop - p < 16:
                raise InvalidMp4('E_TRUNCATED_MP4_LONG_BOX')
            size = int.from_bytes(stream.read(8), 'big')
            header_len = 16
        elif size == 0:
            size = stop - p
        if size < header_len or size > stop - p:
            raise InvalidMp4('E_INVALID_MP4_BOX_SIZE')
        yield name, p + header_len, p + size
        p += size


def _handlers_in_trak(stream, start, stop):
    found = []
    width = height = None
    for name, payload, end in _boxes(stream, start, stop):
        if name == b'tkhd':
            if end - payload >= 8:
                stream.seek(end - 8)
                # Width and height are 16.16 fixed point in the tkhd box.
                width, height = tuple(int.from_bytes(stream.read(4), 'big') / 65536 for _ in range(2))
        if name != b'mdia':
            continue
        for mdia_name, inner, mdia_end in _boxes(stream, payload, end):
            if mdia_name != b'hdlr':
                continue
            if mdia_end - inner < 12:
                raise InvalidMp4('E_SHORT_MP4_HANDLER')
            stream.seek(inner + 8)
            found.append(stream.read(4))
    if len(found) != 1:
        raise InvalidMp4('E_MP4_TRACK_HANDLER_COUNT')
    return found[0], width, height


def inspect_mp4(path):
    """Return track count, video dimensions, and basic MP4 container QA.

    Doesn't depend on FFprobe. Validates only enough structural data to
    distinguish H264/AAC track presence from a silent or empty file.
    """
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 32:
        raise InvalidMp4('E_MP4_MISSING_OR_EMPTY')
    size = path.stat().st_size
    with path.open('rb') as f:
        containers = list(_boxes(f, 0, size))
        if containers[0][0] != b'ftyp':
            raise InvalidMp4('E_NOT_MP4_FTYP')
        moov_boxes = [(a, b) for n, a, b in containers if n == b'moov']
        mdat_boxes = [(a, b) for n, a, b in containers if n == b'mdat']
        if len(moov_boxes) != 1 or not mdat_boxes:
            raise InvalidMp4('E_MP4_MOOV_OR_MDAT_MISSING')
        if sum(b - a for a, b in mdat_boxes) < 1:
            raise InvalidMp4('E_MP4_EMPTY_MEDIA_DATA')
        moov_start, moov_end = moov_boxes[0]
        tracks = []
        for name, a, b in _boxes(f, moov_start, moov_end):
            if name == b'trak':
                handler, width, height = _handlers_in_trak(f, a, b)
                tracks.append({'handler': handler.decode('ascii', 'replace'),
                               'width': width, 'height': height})
    video = [t for t in tracks if t['handler'] == 'vide']
    audio = [t for t in tracks if t['handler'] == 'soun']
    if not video:
        raise InvalidMp4('E_MP4_VIDEO_TRACK_MISSING')
    if not audio:
        raise InvalidMp4('E_MP4_AUDIO_TRACK_MISSING')
    return {'status': 'PASS_TRACK_PRESENCE_NOT_PLAYBACK', 'video_tracks': len(video),
            'audio_tracks': len(audio), 'first_video_width': video[0]['width'],
            'first_video_height': video[0]['height'], 'media_data_bytes': sum(b - a for a, b in mdat_boxes)}