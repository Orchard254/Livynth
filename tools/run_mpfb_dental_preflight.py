#!/usr/bin/env python3
"""One-command MHCLO dental preflight; does not rebuild or render A/B humans."""
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

SCHEMA='livynth.mhclo.dental-preflight.v1'


def command(blender,plan,out):
    return [str(blender),'--background','--python',
            str(ROOT/'tools/mpfb_dental_preflight_blender.py'),'--',
            '--plan',str(Path(plan).resolve()),'--out',str(Path(out).resolve())]


def run(blender,plan,out,*,execute=subprocess.run):
    output=Path(out).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_PREFLIGHT_REPORT_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    completed=execute(command(blender,plan,output),cwd=str(ROOT),check=False)
    if not output.is_file():
        raise RuntimeError('E_PREFLIGHT_REPORT_MISSING: Blender exit '+str(completed.returncode))
    data=json.loads(output.read_text(encoding='utf-8'))
    if (not isinstance(data,dict) or data.get('schema')!=SCHEMA or
        data.get('status') not in (
           'PASS_REAL_MHCLO_JAW_GROUP_MAPPING_NOT_VISUAL_QA',
           'FAIL_REAL_MHCLO_JAW_GROUP_MAPPING') or
        data.get('human_created') is not False or
        data.get('glbs_touched') is not False):
        raise RuntimeError('E_PREFLIGHT_REPORT_INVALID')
    if data['status'].startswith('PASS_'):
        jaw=data.get('jaw_assignment')
        count=data.get('obj_vertices')
        if (not isinstance(jaw,dict) or type(count) is not int or count<32 or
            data.get('mhclo_entries')!=count or
            jaw.get('status')!='PASS_HELPER_GROUP_JAW_MAPPING_NOT_VISUAL_APPROVAL' or
            jaw.get('total_teeth_vertices')!=count or
            type(jaw.get('lower_teeth_vertices')) is not int or
            type(jaw.get('upper_teeth_vertices')) is not int or
            jaw['lower_teeth_vertices']<20 or jaw['upper_teeth_vertices']<20 or
            jaw['lower_teeth_vertices']+jaw['upper_teeth_vertices']!=count or
            jaw.get('mixed_jaw_faces')!=0 or
            jaw.get('mesh_topology_modified') is not False):
            raise RuntimeError('E_PREFLIGHT_REPORT_INVALID_PASS_MAPPING')
    if completed.returncode!=0 or data['status'].startswith('FAIL_'):
        raise RuntimeError('E_PREFLIGHT_REJECTED: '+str(data.get('first_error'))+
                           '; details in '+str(output))
    return data


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',default='')
    p.add_argument('--plan',type=Path,
                   default=ROOT/'character/appearance/native_anatomy_demo.json')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    from livynth_studio import find_blender
    output=args.out or ROOT/'output/dental_preflight'/datetime.now().strftime(
        '%Y%m%d_%H%M%S_%f')/'dentition_probe.json'
    try:
        doc=run(find_blender(args.blender),args.plan,output)
    except (OSError,ValueError,RuntimeError) as exc:
        p.exit(2,'LIVYNTH MHCLO preflight failed: '+str(exc)+
               '\nThe report, if created, can be shared without GLBs.\n')
    print(json.dumps({
        'status':doc['status'],
        'report':str(Path(output).resolve()),
        'upper_teeth_vertices':doc['jaw_assignment']['upper_teeth_vertices'],
        'lower_teeth_vertices':doc['jaw_assignment']['lower_teeth_vertices'],
        'visual_quality':'NOT_TESTED',
    },indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
