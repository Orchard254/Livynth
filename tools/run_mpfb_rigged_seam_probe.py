#!/usr/bin/env python3
"""IDENTITY-021: one MPFB rigged-teeth disposable-copy seam probe; no renders."""
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

SCHEMA='livynth.mhclo.rigged-seam-probe.v1'
PASS='PASS_RIGGED_COPY_STRUCTURE_NOT_JAW_MOTION_OR_VISUAL_QA'


def command(blender,asset_plan,output):
    return [str(blender),'--background','--python',
            str(ROOT/'tools/mpfb_anatomy_ab_blender.py'),'--',
            '--character','demo_head_a',
            '--plan',str(Path(asset_plan).resolve()),
            '--out',str(Path(output).resolve()),
            '--rigged-seam-probe']


def run(blender,asset_plan,output,*,execute=subprocess.run):
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_RIGGED_SEAM_OUTPUT_EXISTS')
    result=execute(command(blender,asset_plan,output),
                   cwd=str(ROOT),check=False)
    report=output/'rigged_seam_probe.json'
    if not report.is_file():
        raise RuntimeError('E_RIGGED_SEAM_REPORT_MISSING: Blender exit '+
                           str(result.returncode))
    data=json.loads(report.read_text(encoding='utf-8'))
    if (not isinstance(data,dict) or data.get('schema')!=SCHEMA or
        data.get('character')!='demo_head_a' or
        data.get('source_asset_modified') is not False or
        data.get('existing_glbs_modified') is not False or
        data.get('render_started') is not False):
        raise RuntimeError('E_RIGGED_SEAM_REPORT_CONTRACT')
    if result.returncode!=0 or data.get('status')!=PASS:
        raise RuntimeError('E_RIGGED_SEAM_REJECTED: '+str(data.get('error'))+
                           '; report '+str(report))
    if (data.get('vertices_preserved')!=3868 or
        data.get('retained_faces')!=3540 or
        data.get('bridge_faces_removed_on_disposable_copy')!=20 or
        data.get('vertex_order_preserved') is not True or
        data.get('armature_modifier_preserved') is not True or
        data.get('vertex_groups_preserved') is not True or
        data.get('materials_preserved') is not True or
        data.get('cross_jaw_edges_after')!=0 or
        data.get('facial_motion')!='NOT_TESTED' or
        data.get('visual_quality')!='NOT_TESTED' or
        not isinstance(data.get('skin_weight_sha256_before_after'),str) or
        len(data['skin_weight_sha256_before_after'])!=64):
        raise RuntimeError('E_RIGGED_SEAM_REPORT_FALSE_PASS')
    return data


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',default='')
    p.add_argument('--plan',type=Path,
                   default=ROOT/'character/appearance/native_anatomy_demo.json')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    from livynth_studio import find_blender
    output=args.out or (ROOT/'output/rigged_seam_probe'/
                       datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    try:
        data=run(find_blender(args.blender),args.plan,output)
    except (OSError,ValueError,RuntimeError) as exc:
        p.exit(2,'LIVYNTH rigged seam proof FAIL: '+str(exc)+'\n')
    print(json.dumps({
        'status':data['status'],
        'vertices':data['vertices_preserved'],
        'bridge_faces_removed':data['bridge_faces_removed_on_disposable_copy'],
        'skin_weight_assignments':data['skin_weight_assignments'],
        'report':str((Path(output).resolve()/'rigged_seam_probe.json')),
        'visual_quality':'NOT_TESTED',
    },indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
