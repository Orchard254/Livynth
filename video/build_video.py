#!/usr/bin/env python3
"""One command: narration WAV → timeline.json → Blender portrait MP4."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--glb',required=True,type=Path)
    p.add_argument('--audio',required=True,type=Path)
    p.add_argument('--text',required=True)
    p.add_argument('--words-json',type=Path)
    p.add_argument('--blender',default='blender',help='blender or absolute blender.exe path')
    p.add_argument('--out',type=Path,default=Path('output/livynth_m001.mp4'))
    p.add_argument('--preview',action='store_true')
    p.add_argument('--front',choices=('negative-y','positive-y'),default='negative-y')
    args=p.parse_args()
    if not shutil.which(args.blender) and not Path(args.blender).is_file():
        p.error('Blender not found; provide --blender path/to/blender.exe')
    for path in (args.glb,args.audio):
        if not path.is_file():
            p.error(f'Missing input: {path}')
    scripts=Path(__file__).resolve().parent
    output=args.out.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    timeline=output.with_name('timeline.json')
    command=[sys.executable,str(scripts/'make_timeline.py'),'--audio',str(args.audio),
             '--text',args.text,'--out',str(timeline)]
    if args.words_json:
        command+=['--words-json',str(args.words_json)]
    subprocess.run(command,check=True)
    command=[args.blender,'-b','--python',str(scripts/'render_talk.py'),'--',
             '--glb',str(args.glb),'--timeline',str(timeline),
             '--audio',str(args.audio),'--out',str(output),'--front',args.front]
    if args.preview:
        command.append('--preview')
    print('Executing:', ' '.join(command),flush=True)
    subprocess.run(command,check=True)


if __name__=='__main__':
    main()
