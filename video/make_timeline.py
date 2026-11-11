#!/usr/bin/env python3
"""PCM WAV + transcript → bounded ARKit/viseme timeline (approximate lip-sync).

This is a deterministic fallback, NOT a phoneme aligner. Optional word timings
can be supplied as JSON records with text, start and end in seconds.
"""
import argparse
import json
import math
import re
import wave
from pathlib import Path

VOWELS = {'a':'viseme_aa','e':'viseme_E','i':'viseme_I',
          'o':'viseme_O','u':'viseme_U','y':'viseme_I'}
DIGRAPHS = {'th':'viseme_TH','ch':'viseme_CH','sh':'viseme_CH',
            'ph':'viseme_FF','oo':'viseme_U','ee':'viseme_I',
            'ng':'viseme_nn','wh':'viseme_U'}
CONSONANTS = {'f':'viseme_FF','v':'viseme_FF','m':'viseme_PP',
              'b':'viseme_PP','p':'viseme_PP','s':'viseme_SS',
              'z':'viseme_SS','c':'viseme_kk','k':'viseme_kk',
              'g':'viseme_kk','t':'viseme_DD','d':'viseme_DD',
              'n':'viseme_nn','l':'viseme_nn','r':'viseme_RR',
              'w':'viseme_U','j':'viseme_CH','q':'viseme_kk',
              'h':'viseme_aa','x':'viseme_SS'}


def read_wav_energy(path, fps):
    """Return WAV duration and RMS per video frame; only uncompressed PCM."""
    with wave.open(str(path), 'rb') as audio:
        channels, width, rate, count, compression = audio.getparams()[:5]
        if compression != 'NONE' or width not in (1, 2, 3, 4):
            raise ValueError('Expected uncompressed PCM WAV')
        if rate < 1 or channels < 1 or count < 1:
            raise ValueError('Empty or malformed WAV')
        raw = audio.readframes(count)
    stride = channels * width
    samples = []
    for i in range(0, len(raw)-stride+1, stride):
        value = 0.0
        for ch in range(channels):
            byte = raw[i+ch*width:i+(ch+1)*width]
            sample = ((byte[0]-128)/128) if width == 1 else (
                int.from_bytes(byte, 'little', signed=True)/float(1 << (width*8-1)))
            value += sample
        samples.append(value/channels)
    duration = len(samples)/rate
    energy = []
    for i in range(math.ceil(duration*fps)):
        start = int(i*rate/fps)
        end = min(len(samples), max(start+1, int((i+1)*rate/fps)))
        section = samples[start:end]
        energy.append(math.sqrt(sum(v*v for v in section)/len(section)) if section else 0)
    return duration, energy


def visemes_for(word):
    result, pos, word = [], 0, word.lower()
    while pos < len(word):
        pair = word[pos:pos+2]
        if pair in DIGRAPHS:
            result.append(DIGRAPHS[pair])
            pos += 2
        else:
            shape = VOWELS.get(word[pos], CONSONANTS.get(word[pos]))
            if shape:
                result.append(shape)
            pos += 1
    return result or ['viseme_aa']


def approximate_words(text, duration, energy, fps):
    words = re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", text)
    if not words:
        return []
    ceiling = max(energy, default=0)
    active = [i for i, value in enumerate(energy) if value > max(0.008, ceiling*0.12)]
    start = active[0]/fps if active else 0
    end = min(duration, (active[-1]+1)/fps) if active else duration
    weights = [max(2, len(word)) for word in words]
    total = sum(weights)
    result = []
    position = start
    for word, weight in zip(words, weights):
        span = (end-start)*weight/total
        result.append({'text':word,'start':round(position,5),'end':round(position+span,5)})
        position += span
    return result


def validate_words(words, duration):
    clean = []
    for word in words:
        start, end = float(word['start']), float(word['end'])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration+0.05):
            raise ValueError(f'Invalid word timing: {word}')
        clean.append({'text':str(word['text']),'start':start,'end':end})
    clean.sort(key=lambda item: item['start'])
    if any(b['start'] < a['end']-0.005 for a, b in zip(clean, clean[1:])):
        raise ValueError('Word boundaries overlap')
    return clean


def smoothstep(x):
    x = max(0, min(1, x))
    return x*x*(3-2*x)


def blink(t, center, width=0.32):
    x = (t-center)/width
    if x < 0 or x > 1:
        return 0
    if x < 0.35:
        return smoothstep(x/0.35)
    if x < 0.49:
        return 1
    return 1-smoothstep((x-0.49)/0.51)


def make_timeline(audio, text, fps=30, words=None):
    if not 12 <= fps <= 60:
        raise ValueError('fps must be 12–60')
    duration, rms = read_wav_energy(audio, fps)
    if not 0.1 <= duration <= 120:
        raise ValueError('M001 audio length must be between 0.1 and 120 seconds')
    timed = words is not None
    words = validate_words(words, duration) if timed else approximate_words(text, duration, rms, fps)
    high = sorted(rms)[int((len(rms)-1)*0.9)] or 0.001
    frames = []
    for i, energy in enumerate(rms):
        t = i/fps
        gate = smoothstep((energy/max(high, 0.008)-0.10)/0.45)
        values = {'eyeBlinkLeft':0.0,'eyeBlinkRight':0.0,
                  'jawOpen':0.0,'mouthSmileLeft':0.10,'mouthSmileRight':0.10}
        word = next((w for w in words if w['start'] <= t < w['end']), None)
        if word and gate > 0:
            shapes = visemes_for(word['text'])
            progress = (t-word['start'])/max(1e-6, word['end']-word['start'])
            active = shapes[min(len(shapes)-1, int(progress*len(shapes)))]
            envelope = min(1,(t-word['start'])/0.07,(word['end']-t)/0.09)
            values[active] = round(gate*smoothstep(envelope)*0.73, 4)
            values['jawOpen'] = round(min(0.58, gate*(0.10 if active == 'viseme_PP' else 0.29)),4)
            values['mouthSmileLeft'] = values['mouthSmileRight'] = 0.035
        closed = max(blink(t, c) for c in (2.15,5.70,9.35,12.60,16.30))
        values['eyeBlinkLeft'] = values['eyeBlinkRight'] = round(closed,4)
        frames.append({'frame':i+1, 't':round(t,5),
                       'morphs':{k:round(max(0,min(1,v)),4) for k,v in values.items()}})
    return {'schema':'livynth.timeline.v1','fps':fps,'duration':round(duration,5),
            'sync_method':'word-timed-spelling-heuristic' if timed else 'approximate-spelling-and-energy',
            'disclaimer':'Not phoneme-accurate: add a real aligner before production use.',
            'text':text,'words':words,'frames':frames}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--text', default='')
    parser.add_argument('--text-file', type=Path)
    parser.add_argument('--words-json', type=Path)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--out', type=Path, default=Path('output/timeline.json'))
    args = parser.parse_args()
    text = args.text_file.read_text(encoding='utf8').strip() if args.text_file else args.text
    words = json.loads(args.words_json.read_text(encoding='utf8')) if args.words_json else None
    if not text and not words:
        parser.error('Provide --text, --text-file or --words-json')
    timeline = make_timeline(args.audio, text, fps=args.fps, words=words)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(timeline, indent=2), encoding='utf8')
    print(f"Wrote {len(timeline['frames'])} frames to {args.out}; {timeline['sync_method']}")


if __name__ == '__main__':
    main()
