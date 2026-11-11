#!/usr/bin/env python3
"""Run LIVYNTH M001 checks locally without GitHub Actions or dependencies.

Examples:
  python tools/local_check.py
  python tools/local_check.py --glb assets/ours-photoreal.glb
  python tools/local_check.py --glb assets/ours-photoreal.glb --audio assets/voice.wav \
      --text "Welcome to Livynth."

The optional --preview command invokes installed Blender; all other checks are
standard-library Python only. A preview still requires a real GLB and WAV.
"""
import argparse
import os
import shutil
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_blender(configured):
    """Use an explicit path, Blender on PATH, or the newest Windows installation."""
    if configured != 'blender':
        return configured
    found = shutil.which('blender')
    if found:
        return found
    if os.name == 'nt':
        candidates = []
        for env in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)'):
            root = os.environ.get(env)
            if root:
                candidates.extend(Path(root).glob('Blender Foundation/Blender */blender.exe'))
        for path in sorted(set(candidates), reverse=True):
            if path.is_file():
                return str(path)
    return configured


def check(args):
    def run(command):
        print('\n[livynth local] $', ' '.join(str(x) for x in command), flush=True)
        subprocess.run([str(v) for v in command], cwd=ROOT, check=True)

    run([sys.executable, '-m', 'compileall', '-q', 'video', 'tests', 'tools'])
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'])

    if args.glb:
        glb = args.glb.resolve()
        if not glb.is_file():
            raise FileNotFoundError(glb)
        run([sys.executable, 'video/model_check.py', '--glb', glb])
    if args.audio:
        audio = args.audio.resolve()
        if not audio.is_file():
            raise FileNotFoundError(f"Missing voice WAV: {audio}. Copy the smoke-kit livynth_demo_voice.wav to assets/voice.wav or generate a PCM WAV.")
        output = ROOT / 'output' / 'local_timeline_check.json'
        run([sys.executable, 'video/make_timeline.py', '--audio', audio,
             '--text', args.text, '--out', output])
        data = json.loads(output.read_text(encoding='utf8'))
        if not data.get('frames') or data.get('schema') != 'livynth.timeline.v1':
            raise RuntimeError('Audio produced invalid or empty timeline')
        if any(not (0 <= value <= 1) for frame in data['frames']
               for value in frame['morphs'].values()):
            raise RuntimeError('Animation includes out-of-range weights')
        print(f"[livynth local] {len(data['frames'])} animation frames verified")

    if args.preview or args.preview_set:
        if not args.glb or not args.audio:
            raise ValueError('--preview requires both --glb and --audio')
        run([sys.executable, 'video/build_video.py',
             '--glb', args.glb.resolve(), '--audio', args.audio.resolve(),
             '--text', args.text, '--blender', find_blender(args.blender),
             '--preview-set' if args.preview_set else '--preview'])

    print('\n[livynth local] PASS — all requested local checks completed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glb', type=Path, help='Optional GLB to verify')
    parser.add_argument('--audio', type=Path, help='Optional real or test PCM WAV')
    parser.add_argument('--text', default='Welcome to Livynth. Imagination comes alive here.')
    parser.add_argument('--preview', action='store_true', help='Render one neutral preview with Blender')
    parser.add_argument('--preview-set', action='store_true', help='Render four diagnostic stills in Blender')
    parser.add_argument('--blender', default='blender', help='Blender executable path for --preview')
    args = parser.parse_args()
    try:
        check(args)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, RuntimeError) as error:
        print(f'[livynth local] FAILED: {error}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
