"""Deterministic pose-review contract shared by Blender and local QA.

Rendering evidence remains distinct from identity likeness or photorealism.
No external image packages, model weights or user images required.
"""
from __future__ import annotations
import html
import math
from pathlib import Path
import struct
import zlib

POSES = {
    'neutral': {},
    'blink': {'eyeBlinkLeft': 1.0, 'eyeBlinkRight': 1.0},
    'jaw_open': {'jawOpen': 0.85},
    'viseme_aa': {'viseme_aa': 0.9},
    'viseme_pp': {'viseme_PP': 0.9},
    'smile': {'mouthSmileLeft': 0.75, 'mouthSmileRight': 0.75},
    'pucker': {'mouthPucker': 0.85},
}
VIEW_POSES = {
    'front': tuple(POSES),
    'three_quarter': ('neutral', 'blink', 'jaw_open'),
}
CHARACTERS = ('demo_head_a', 'demo_head_b')
SCHEMA = 'livynth.identity.rendered-pose-review.v1'


class PoseReviewError(ValueError):
    pass


def render_jobs():
    """Stable ordered (view, pose, weights) records: 10 per character."""
    return [(view, pose, POSES[pose].copy())
            for view, poses in VIEW_POSES.items() for pose in poses]


def check_png_dimensions(path, width, height):
    """Check full PNG chunks, CRC, RGBA 8-bit data and expected dimensions.

    PNG files are the human review evidence: accepting a signature-only fake
    would allow a render to be called successful without actual image data.
    """
    path = Path(path)
    data = path.read_bytes()
    if not 70 <= len(data) <= 20_000_000 or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise PoseReviewError('E_NOT_PNG: ' + str(path))
    i = 8
    seen_ihdr = seen_iend = False
    compressed = bytearray()
    while i < len(data):
        if i+12 > len(data):
            raise PoseReviewError('E_PNG_TRUNCATED')
        length, = struct.unpack_from('>I', data, i)
        end = i + length + 12
        if length > len(data) or end > len(data):
            raise PoseReviewError('E_PNG_TRUNCATED')
        tag = data[i+4:i+8]
        payload = data[i+8:i+8+length]
        expected_crc, = struct.unpack_from('>I', data, i+8+length)
        if zlib.crc32(tag+payload) & 0xffffffff != expected_crc:
            raise PoseReviewError('E_PNG_CRC')
        if tag == b'IHDR':
            if seen_ihdr or i != 8 or length != 13:
                raise PoseReviewError('E_PNG_IHDR')
            image_w, image_h, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', payload)
            if (image_w, image_h) != (width,height):
                raise PoseReviewError('E_PNG_DIMENSIONS')
            if (depth,color,comp,filt,interlace)!=(8,6,0,0,0):
                raise PoseReviewError('E_PNG_RGBA_FORMAT')
            seen_ihdr = True
        elif tag == b'IDAT':
            if not seen_ihdr or seen_iend:
                raise PoseReviewError('E_PNG_IDAT_ORDER')
            compressed.extend(payload)
        elif tag == b'IEND':
            if not seen_ihdr or length != 0 or end != len(data):
                raise PoseReviewError('E_PNG_IEND')
            seen_iend = True
        elif tag and tag[0] & 32 == 0:
            raise PoseReviewError('E_PNG_UNKNOWN_CRITICAL')
        i = end
    if not seen_iend or not compressed:
        raise PoseReviewError('E_PNG_MISSING_IMAGE_DATA')
    try:
        decompressed=zlib.decompress(compressed)
    except zlib.error as exc:
        raise PoseReviewError('E_PNG_INVALID_DEFLATE') from exc
    if len(decompressed)!=height*(1+width*4):
        raise PoseReviewError('E_PNG_PIXEL_BYTE_COUNT')
    # Every PNG row begins with one of the five permitted filter methods.
    stride=1+width*4
    if any(decompressed[y*stride] > 4 for y in range(height)):
        raise PoseReviewError('E_PNG_INVALID_FILTER')
    return width,height


def raster_change(neutral_rgba, posed_rgba, width, height, *,
                  channel_threshold=0.035, step=2):
    """Quantify changed RGB pixels in the face crop, not the full frame.

    Inputs are Blender RGBA float pixel buffers, bottom-up. This is only a
    presence-of-rendered-change diagnostic, not a shape-quality metric.
    """
    if (not isinstance(width, int) or not isinstance(height, int)
        or width < 128 or height < 128 or step < 1
        or len(neutral_rgba) != len(posed_rgba) or
        len(neutral_rgba) != width * height * 4
        or not 0 < channel_threshold < 1):
        raise PoseReviewError('E_RASTER_INPUT')
    x0, x1 = int(width * 0.18), int(width * 0.82)
    # Blender raster origin is bottom-left: face is in upper 80% of the image.
    y0, y1 = int(height * 0.16), int(height * 0.94)
    sampled = changed = 0
    total = peak = 0.0
    for y in range(y0, y1, step):
        for x in range(x0, x1, step):
            i = (y * width + x) * 4
            delta = 0.0
            for ch in range(3):
                p, q = float(neutral_rgba[i+ch]), float(posed_rgba[i+ch])
                if not (math.isfinite(p) and math.isfinite(q)):
                    raise PoseReviewError('E_RASTER_NONFINITE')
                delta = max(delta, abs(p-q))
            total += delta
            peak = max(peak, delta)
            sampled += 1
            if delta > channel_threshold:
                changed += 1
    if not sampled:
        raise PoseReviewError('E_EMPTY_FACE_CROP')
    return {'changed_face_samples':changed,'total_face_samples':sampled,
            'changed_face_fraction':round(changed/sampled,6),
            'mean_max_rgb_delta':round(total/sampled,7),
            'peak_rgb_delta':round(peak,7),
            'status':('SIGNAL_PRESENT_NOT_VISUAL_APPROVAL' if changed >= 12
                      else 'NO_CONFIDENT_RENDERED_POSE_SIGNAL')}


def validate_character_report(report, root, character, *, width=400, height=600):
    if (not isinstance(report,dict)
        or report.get('schema')!=SCHEMA
        or report.get('character_id')!=character
        or report.get('status')!='CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW'
        or report.get('native_animation_interface')!='EXPORTED_MORPH_SIGNAL_VERIFIED'):
        raise PoseReviewError('E_CHARACTER_REPORT')
    entries = report.get('renders')
    required={(view,pose) for view,pose,_ in render_jobs()}
    if not isinstance(entries,list) or len(entries)!=len(required):
        raise PoseReviewError('E_MISSING_POSE_RENDERS')
    found=set()
    for item in entries:
        if not isinstance(item,dict):
            raise PoseReviewError('E_RENDER_ENTRY')
        view,pose=item.get('view'),item.get('pose')
        if (view,pose) not in required or (view,pose) in found:
            raise PoseReviewError('E_RENDER_KEY')
        found.add((view,pose))
        expected=Path(root)/character/(view+'_'+pose+'.png')
        if Path(item.get('path','')).resolve()!=expected.resolve():
            raise PoseReviewError('E_RENDER_PATH_MISMATCH')
        check_png_dimensions(expected,width,height)
        if pose!='neutral':
            delta=item.get('rendered_motion')
            if not isinstance(delta,dict) or delta.get('status')!='SIGNAL_PRESENT_NOT_VISUAL_APPROVAL':
                raise PoseReviewError('E_RENDERED_POSE_INERT_'+view+'_'+pose)
    return True


def gallery_html(report):
    """Self-contained, local-only human-review gallery (no network scripts)."""
    if report.get('schema')!=SCHEMA or report.get('status')!='CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW':
        raise PoseReviewError('E_GALLERY_REPORT')
    cards=[]
    for view,pose,_ in render_jobs():
        tiles=[]
        for char in CHARACTERS:
            # All paths derive exclusively from fixed known slugs.
            src=f'{char}/{view}_{pose}.png'
            tiles.append(f'<figure><img src="{src}" alt="{char} {view} {pose}">'
                         f'<figcaption>{html.escape(char)}</figcaption></figure>')
        cards.append('<section><h2>'+html.escape(view.replace('_',' ').title())+' — '
                     +html.escape(pose.replace('_',' ').title())+
                     '</h2><div class="pair">'+''.join(tiles)+'</div></section>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>LIVYNTH two-character expression review</title>'
            '<style>body{font:16px system-ui;background:#17212b;color:#eef3f8;'
            'max-width:1100px;margin:auto;padding:20px}'
            '.pair{display:flex;flex-wrap:wrap;gap:12px}'
            'figure{margin:0}img{width:min(42vw,360px);height:auto;border:1px solid #667;}'
            'section{border-bottom:1px solid #556;padding:12px 0}figcaption{padding:5px}'
            '</style></head><body><h1>LIVYNTH — Character A/B expression review</h1>'
            '<p>Identity likeness and expression naturalness require human review. '
            'This gallery is NOT an accepted likeness or animation certificate.</p>'
            +''.join(cards)+'</body></html>')
