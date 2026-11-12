#!/usr/bin/env python3
"""IDENTITY-023: isolated Head A jaw-open teeth/tongue visibility evidence."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools.identity_pose_review import check_png_dimensions
from tools.oral_asset_visibility import VARIANTS
from tools.run_mpfb_seam_jaw_stills import command as jaw_command

STATUS='CAPTURED_HEAD_A_ORAL_ISOLATION_PENDING_VISUAL_REVIEW'
SCOPE='HEAD_A_JAW_OPEN_ORAL_ASSET_VISIBILITY_ONLY'
FILES=tuple(name+'.png' for name,_,_ in VARIANTS)
ZIP='identity023_oral_isolation.zip'


class IsolationReviewError(ValueError):
    pass


def command(blender,plan,output):
    return jaw_command(blender,plan,output)+['--oral-isolation']


def validate(data,output):
    if (not isinstance(data,dict) or
        data.get('status')!=STATUS or
        data.get('schema')!='livynth.anatomy-ab-render.v1' or
        data.get('character_id')!='demo_head_a' or
        data.get('render_scope')!=SCOPE or
        data.get('framing')!='MOUTH_FOCUSED_FACE_CLOSEUP' or
        data.get('existing_glbs_modified') is not False or
        data.get('dental_visual_quality')!='PENDING_INDEPENDENT_REVIEW' or
        data.get('full_character_glb_export')!='NOT_TESTED' or
        data.get('rig_joints')!=163 or
        data.get('native_body_vertices')!=13380 or
        data.get('native_quads')!=13378 or
        data.get('facial_morph_count')!=67):
        raise IsolationReviewError('E_ID023_REPORT_CONTRACT')
    seam=data.get('seamed_render_copy_audit')
    jaw=data.get('seamed_jaw_motion_audit')
    if (not isinstance(seam,dict) or
        seam.get('status')!='PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA' or
        seam.get('original_mpfb_asset_modified') is not False or
        seam.get('seamed_faces')!=3540 or
        not isinstance(jaw,dict) or
        jaw.get('status')!='PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA'):
        raise IsolationReviewError('E_ID023_SEAM_GATE')
    images=data.get('images')
    audit=data.get('oral_asset_visibility_audit')
    if (not isinstance(images,list) or len(images)!=len(FILES) or
        [x.get('filename') for x in images if isinstance(x,dict)]!=list(FILES) or
        not isinstance(audit,list) or len(audit)!=len(FILES)):
        raise IsolationReviewError('E_ID023_IMAGE_SET')
    for index,(name,hide_teeth,hide_tongue) in enumerate(VARIANTS):
        item=audit[index]
        if (not isinstance(item,dict) or
            item.get('filename')!=name+'.png' or
            item.get('teeth_visible') is not (not hide_teeth) or
            item.get('tongue_visible') is not (not hide_tongue) or
            item.get('body_visible') is not True or
            item.get('source_geometry_modified') is not False or
            item.get('rendered_visual_inference')!='PENDING_INDEPENDENT_REVIEW'):
            raise IsolationReviewError('E_ID023_VISIBILITY_AUDIT')
    # Validate every visibility label before touching the disk. A broken
    # metadata contract must not be obscured by missing synthetic PNG fixtures.
    for name in FILES:
        check_png_dimensions(Path(output)/name,400,600)
    return True


def run(blender,plan,output,*,execute=subprocess.run):
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ID023_OUTPUT_EXISTS')
    completed=execute(command(blender,plan,output),cwd=str(ROOT),
                      check=False)
    report=output/'anatomy_pose_report.json'
    if not report.is_file():
        raise IsolationReviewError(
            'E_ID023_REPORT_MISSING: Blender exit '+str(completed.returncode)+
            '; output '+str(output))
    data=json.loads(report.read_text(encoding='utf-8'))
    if completed.returncode!=0:
        raise IsolationReviewError('E_ID023_BLENDER_EXIT_'+str(completed.returncode))
    validate(data,output)
    bundle=output/ZIP
    if bundle.exists() or bundle.is_symlink():
        raise FileExistsError('E_ID023_ZIP_EXISTS')
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in FILES+('anatomy_pose_report.json',):
            archive.write(output/filename,arcname=filename)
    return data,bundle


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',default='')
    parser.add_argument('--plan',type=Path,default=ROOT/
                        'character/appearance/native_anatomy_demo.json')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    from livynth_studio import find_blender
    output=args.out or (ROOT/'output/identity023_oral_isolation'/
                        datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    try:
        data,bundle=run(find_blender(args.blender),args.plan,output)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2,'LIVYNTH IDENTITY-023 FAIL: '+str(exc)+
                    '\nGenerated files if any: '+str(output)+'\n')
    print(json.dumps({
        'status':data['status'],'render_scope':data['render_scope'],
        'images':list(FILES),'upload_zip':str(bundle),
        'visual_approval':'PENDING',
    },indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
