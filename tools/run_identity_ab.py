#!/usr/bin/env python3
"""One command: build two reusable MPFB humans and verify identity separation."""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from character.identity_recipe import load_recipe, recipe_sha256
from tools.identity_compare import compare


def make_ab_plan(*, blender, out, a, b):
    aa,bb=load_recipe(a),load_recipe(b)
    if aa['character_id']==bb['character_id'] or recipe_sha256(aa)==recipe_sha256(bb):
        raise ValueError('E_NOT_TWO_DISTINCT_RECIPES')
    result=[]
    for recipe_file, recipe in ((a,aa),(b,bb)):
        tag=recipe['character_id']
        glb=out/(tag+'.glb'); report=out/(tag+'.json')
        command=[str(blender),'--background','--python',str(ROOT/'tools/mpfb_headless_probe.py'),
                 '--','--identity-recipe',str(recipe_file.resolve()),
                 '--out',str(glb),'--json',str(report)]
        result.append((command,report))
    return result


def run(*, blender, out, a, b, execute=subprocess.run):
    steps=make_ab_plan(blender=blender,out=out,a=a,b=b)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.mkdir(exist_ok=False)  # never overwrite previous outputs
    for command,_ in steps:
        print('[LIVYNTH identity] executing:', ' '.join(command),flush=True)
        execute(command,cwd=str(ROOT),check=True)
    reports=[json.loads(report.read_text(encoding='utf-8')) for _,report in steps]
    result=compare(*reports)
    result['source']='Windows Blender A/B export audit'
    result['output_directory']=str(out)
    (out/'identity_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a',type=Path,default=ROOT/'character/recipes/demo_head_a.json')
    p.add_argument('--b',type=Path,default=ROOT/'character/recipes/demo_head_b.json')
    p.add_argument('--blender',default='')
    p.add_argument('--out',type=Path,default=None)
    args=p.parse_args(argv)
    from livynth_studio import find_blender
    path=Path(args.out).resolve() if args.out else ROOT/'output'/'identity_ab'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        blender=find_blender(args.blender)
        run(blender=blender,out=path,a=args.a,b=args.b)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        p.exit(2,'LIVYNTH identity A/B FAILED: '+str(exc)+'\nOutputs (if any): '+str(path)+'\n')
    return 0


if __name__=='__main__':
    sys.exit(main())
