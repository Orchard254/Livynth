#!/usr/bin/env python3
"""IDENTITY-022: Head A only, two face-closeup jaw stills, no GLB export."""
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

SCHEMA='livynth.anatomy-ab-render.v1'
PASS='CAPTURED_HEAD_A_SEAM_JAW_STILLS_PENDING_VISUAL_REVIEW'
POSE_IMAGES=('front_neutral.png','front_jaw_open.png')
ZIP_NAME='identity022_head_a_jaw_review.zip'


class SeamJawStillsError(ValueError):
    pass


def command(blender,asset_plan,output):
    return [
        str(blender),'--background','--python',
        str(ROOT/'tools/mpfb_anatomy_ab_blender.py'),'--',
        '--character','demo_head_a','--plan',str(Path(asset_plan).resolve()),
        '--out',str(Path(output).resolve()),
        '--align-accessories','--audit-oral-motion',
        '--oral-correctives','--mhclo-dentition','--seam-jaw-stills',
    ]


def validate_report(data,output):
    if (not isinstance(data,dict) or data.get('schema')!=SCHEMA or
            data.get('status')!=PASS or data.get('character_id')!='demo_head_a' or
            data.get('render_scope')!='HEAD_A_FRONT_NEUTRAL_AND_JAW_OPEN_ONLY' or
            data.get('framing')!='MOUTH_FOCUSED_FACE_CLOSEUP' or
            data.get('native_body_vertices')!=13380 or
            data.get('native_quads')!=13378 or data.get('rig_joints')!=163 or
            data.get('facial_morph_count')!=67 or
            data.get('existing_glbs_modified') is not False or
            data.get('full_character_glb_export')!='NOT_TESTED' or
            data.get('dental_visual_quality')!='PENDING_INDEPENDENT_REVIEW'):
        raise SeamJawStillsError('E_ID022_REPORT_CONTRACT')

    surgery=data.get('seamed_render_copy_audit')
    jaw=data.get('dental_mapping_audit')
    motion=data.get('seamed_jaw_motion_audit')
    oral=data.get('oral_motion_audit')
    correction=data.get('oral_corrective_audit')
    if (not isinstance(surgery,dict) or
            surgery.get('status')!='PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA' or
            surgery.get('retained_vertices')!=3868 or
            surgery.get('removed_bridge_faces')!=20 or
            surgery.get('seamed_faces')!=3540 or
            surgery.get('rigged_skin_weights_preserved') is not True or
            surgery.get('cross_jaw_edges_after')!=0 or
            surgery.get('original_mpfb_asset_modified') is not False or
            not isinstance(jaw,dict) or
            jaw.get('status')!='PASS_HELPER_GROUP_JAW_MAPPING_NOT_VISUAL_APPROVAL' or
            jaw.get('mesh_topology_modified') is not True or
            jaw.get('modified_only_on_in_memory_export_copy') is not True or
            jaw.get('face_count')!=3540 or jaw.get('mixed_jaw_faces')!=0 or
            jaw.get('lower_teeth_vertices')!=1884 or
            jaw.get('upper_teeth_vertices')!=1984 or
            not isinstance(motion,dict) or
            motion.get('status')!='PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA' or
            motion.get('lower_vertices')!=1884 or
            motion.get('upper_vertices')!=1984 or
            not isinstance(oral,dict) or
            not isinstance(oral.get('jaw_open'),dict) or
            oral['jaw_open'].get('status')!='ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED' or
            not isinstance(correction,dict) or
            not isinstance(correction.get('jaw_open'),dict) or
            correction['jaw_open'].get('teeth',{}).get('moved_vertices_gt_0_1_mm')!=1884 or
            correction['jaw_open'].get('teeth',{}).get('stationary_vertices_lt_0_1_mm')!=1984):
        raise SeamJawStillsError('E_ID022_ORAL_CONTRACT')

    images=data.get('images')
    if (not isinstance(images,list) or
            [entry.get('filename') for entry in images
             if isinstance(entry,dict)]!=list(POSE_IMAGES) or
            len(images)!=len(POSE_IMAGES)):
        raise SeamJawStillsError('E_ID022_IMAGE_SET')
    for name in POSE_IMAGES:
        check_png_dimensions(Path(output)/name,400,600)
    return True


def run(blender,asset_plan,output,*,execute=subprocess.run):
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ID022_OUTPUT_EXISTS')
    complete=execute(command(blender,asset_plan,output),
                     cwd=str(ROOT),check=False)
    report_path=output/'anatomy_pose_report.json'
    if not report_path.is_file():
        raise SeamJawStillsError(
            'E_ID022_REPORT_MISSING: Blender exit '+str(complete.returncode)+
            '; inspect output folder '+str(output))
    data=json.loads(report_path.read_text(encoding='utf-8'))
    if complete.returncode!=0:
        raise SeamJawStillsError(
            'E_ID022_BLENDER_EXIT_'+str(complete.returncode))
    validate_report(data,output)
    archive=output/ZIP_NAME
    if archive.exists() or archive.is_symlink():
        raise FileExistsError('E_ID022_ARCHIVE_EXISTS')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as zf:
        for name in POSE_IMAGES+('anatomy_pose_report.json',):
            zf.write(output/name,arcname=name)
    return data,archive


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',default='')
    parser.add_argument('--plan',type=Path,
                        default=ROOT/'character/appearance/native_anatomy_demo.json')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    from livynth_studio import find_blender
    output=args.out or (ROOT/'output/identity022_jaw_stills'/
                        datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    try:
        data,archive=run(find_blender(args.blender),args.plan,output)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2,'LIVYNTH IDENTITY-022 FAIL: '+str(exc)+
                    '\nGenerated files if any: '+str(output)+'\n')
    print(json.dumps({
        'status':data['status'],
        'scope':data['render_scope'],
        'images':list(POSE_IMAGES),
        'lower_jaw_movement':data['seamed_jaw_motion_audit'],
        'review_zip':str(archive),
        'visual_quality':'PENDING_INDEPENDENT_REVIEW',
    },indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
