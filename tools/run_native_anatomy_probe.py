#!/usr/bin/env python3
"""One-command, isolated MPFB native eye/teeth/tongue fitting smoke test.

Creates new Blender scene and preview PNGs. Never modifies existing GLBs.
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
from character.native_anatomy import REQUIRED,load_plan
from tools.identity_pose_review import check_png_dimensions


def build_command(blender,plan,output):
    load_plan(plan)  # Fail quickly before expensive Blender startup.
    return [str(blender),'--background','--python',
            str(ROOT/'tools/mpfb_native_anatomy_probe_blender.py'),
            '--','--plan',str(Path(plan).resolve()),
            '--out',str(Path(output).resolve())]


def validate_output(directory):
    directory=Path(directory)
    report=directory/'anatomy_probe.json'
    doc=json.loads(report.read_text(encoding='utf-8'))
    if (doc.get('schema')!='livynth.native-anatomy.attach-probe.v1'
        or doc.get('status')!='ATTACHED_NEUTRAL_ASSETS_PENDING_VISUAL_AND_EXPRESSION_QA'
        or doc.get('existing_glbs_modified') is not False
        or doc.get('detailed_head_shape_applied') is not False
        or doc.get('rig_joint_count')!=163):
        raise ValueError('E_INVALID_ANATOMY_PROBE')
    attachments=doc.get('attachments')
    if (not isinstance(attachments,list) or
        [a.get('category') for a in attachments]!=list(REQUIRED) or
        any(a.get('vertices',0)<=0 for a in attachments)):
        raise ValueError('E_ANATOMY_ATTACHMENTS')
    views=doc.get('images')
    expected=('neutral_front.png','neutral_three_quarter.png')
    if not isinstance(views,list) or len(views)!=2:
        raise ValueError('E_ANATOMY_IMAGES')
    for i,filename in enumerate(expected):
        path=directory/filename
        if Path(views[i].get('file','')).resolve()!=path.resolve():
            raise ValueError('E_ANATOMY_IMAGE_PATH')
        check_png_dimensions(path,480,720)
    return doc


def run(blender,plan,output,*,execute=subprocess.run):
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ANATOMY_OUTPUT_EXISTS')
    command=build_command(blender,plan,output)
    output.parent.mkdir(parents=True,exist_ok=True)
    execute(command,cwd=str(ROOT),check=True)
    return validate_output(output)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',default='')
    p.add_argument('--plan',type=Path,default=ROOT/'character/appearance/native_anatomy_demo.json')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    from livynth_studio import find_blender
    out=args.out or ROOT/'output'/'anatomy_probe'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        doc=run(find_blender(args.blender),args.plan,out)
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        p.exit(2,'LIVYNTH anatomy probe FAILED: '+str(exc)+
               '\nPartial output (if any): '+str(out)+'\n')
    print(json.dumps({'status':doc['status'],
        'out':str(Path(out).resolve()),
        'eyes_teeth_tongue':['eyes','teeth','tongue'],
        'images':['neutral_front.png','neutral_three_quarter.png'],
        'glb_export':'NOT_TESTED','animation':'NOT_TESTED'},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
