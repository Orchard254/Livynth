#!/usr/bin/env python3
"""One-command visual pose audit of EXISTING two-character MPFB GLB exports.

This runs Blender twice for controlled stills, not MP4 or character rebuilds.
An HTML gallery provides two characters side by side for human inspection.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools.identity_pose_review import (
    CHARACTERS, SCHEMA, validate_character_report, gallery_html)
from tools.glb_morph_qa import compare_existing_glbs


def build_plan(folder,output,blender,*,samples=16):
    folder=Path(folder)
    output=Path(output)
    if samples<4 or samples>64:
        raise ValueError('E_RENDER_SAMPLE_RANGE')
    jobs=[]
    for char in CHARACTERS:
        glb=folder/(char+'.glb')
        if not glb.is_file():
            raise FileNotFoundError('Missing existing rigged GLB: '+str(glb))
        argv=[str(blender),'--background','--python',
              str(ROOT/'tools/render_identity_poses_blender.py'),'--',
              '--glb',str(glb.resolve()),'--character',char,
              '--out',str((output/char).resolve()),'--samples',str(samples)]
        jobs.append((char,argv))
    return jobs


def run(folder,output,blender,*,samples=16,execute=subprocess.run,
        inspect_glbs=compare_existing_glbs):
    folder=Path(folder).resolve()
    output=Path(output).resolve()
    jobs=build_plan(folder,output,blender,samples=samples)
    # Preflight checked the actual GLB bytes, not only old JSON audit claims.
    morph=inspect_glbs(folder/'demo_head_a.glb',folder/'demo_head_b.glb')
    if morph.get('status')!='PASS_NONZERO_EXPORTED_MORPH_SIGNAL_NOT_VISUAL_ANIMATION':
        raise ValueError('E_MORPH_PREFLIGHT')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(exist_ok=False)
    reports=[]
    for char,argv in jobs:
        print('[LIVYNTH IDENTITY-007] rendering existing GLB',char,flush=True)
        execute(argv,cwd=str(ROOT),check=True)
        path=output/char/'render_report.json'
        report=json.loads(path.read_text(encoding='utf-8'))
        validate_character_report(report,output,char)
        reports.append(report)
    result={
        'schema':SCHEMA,'status':'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW',
        'existing_glb_morph_signal':'PASS',
        'raster_signal':'PASS_VISIBLE_DIFFERENCES_NOT_VISUAL_QUALITY',
        'character_count':len(reports),
        'views':['front','three_quarter'],
        'renders_per_character':len(reports[0]['renders']),
        'native_animation_interface':'EXPORTED_MORPH_SIGNAL_VERIFIED',
        'face_shape_identity_likeness':'UNVERIFIED',
        'expression_naturalness':'PENDING_HUMAN_REVIEW',
        'photo_reconstruction':'NOT_IMPLEMENTED',
        'source_folder':str(folder),
        'output_folder':str(output),
        'report_files':[str((output/char/'render_report.json')) for char in CHARACTERS],
        'html_gallery':str(output/'index.html'),
    }
    (output/'pose_review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (output/'index.html').write_text(gallery_html(result),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True,
                        help='Existing output/identity_ab/.. folder containing two GLBs')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--blender',default='')
    parser.add_argument('--samples',type=int,default=16)
    args=parser.parse_args(argv)
    from livynth_studio import find_blender
    out=args.out or args.folder/'pose_review'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        blender=find_blender(args.blender)
        run(args.folder,out,blender,samples=args.samples)
    except (OSError,ValueError,KeyError,IndexError,subprocess.CalledProcessError) as exc:
        parser.exit(2,'LIVYNTH IDENTITY-007 FAILED: '+str(exc)+
                    '\nPartial output folder, if any: '+str(out)+'\n')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
