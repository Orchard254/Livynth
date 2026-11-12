#!/usr/bin/env python3
"""IDENTITY-024: Head A jaw-open upper/lower dental arch attribution, 4 stills."""
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
from tools.run_mpfb_oral_isolation import command as oral_command

STATUS='CAPTURED_HEAD_A_DENTAL_ARCH_ISOLATION_PENDING_VISUAL_REVIEW'
SCOPE='HEAD_A_JAW_OPEN_DENTAL_ARCH_ATTRIBUTION_ONLY'
FILES=tuple(s+'.png' for s in (
    'jaw_upper_only','jaw_lower_only','jaw_both_arches','jaw_lower_no_body'))
ZIP_NAME='identity024_dental_arch_isolation.zip'


class ArchReviewError(ValueError):
    pass


def command(blender,plan,output):
    base=oral_command(blender,plan,output)
    if base[-1]!='--oral-isolation':
        raise ArchReviewError('E_ID024_PARENT_COMMAND_CONTRACT')
    return base[:-1]+['--dental-arch-isolation']


def validate(data,output):
    if (not isinstance(data,dict) or
        data.get('schema')!='livynth.anatomy-ab-render.v1' or
        data.get('status')!=STATUS or
        data.get('character_id')!='demo_head_a' or
        data.get('render_scope')!=SCOPE or
        data.get('framing')!='MOUTH_FOCUSED_FACE_CLOSEUP' or
        data.get('dental_visual_quality')!='PENDING_INDEPENDENT_REVIEW' or
        data.get('existing_glbs_modified') is not False or
        data.get('full_character_glb_export')!='NOT_TESTED' or
        data.get('rig_joints')!=163 or
        data.get('facial_morph_count')!=67 or
        data.get('native_body_vertices')!=13380 or
        data.get('native_quads')!=13378):
        raise ArchReviewError('E_ID024_REPORT_CONTRACT')
    surgery=data.get('seamed_render_copy_audit')
    motion=data.get('seamed_jaw_motion_audit')
    coords=data.get('dental_arch_location_audit')
    attrib=data.get('dental_arch_render_audit')
    if (not isinstance(surgery,dict) or
        surgery.get('status')!='PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA' or
        surgery.get('removed_bridge_faces')!=20 or
        surgery.get('rigged_skin_weights_preserved') is not True or
        surgery.get('original_mpfb_asset_modified') is not False or
        not isinstance(motion,dict) or
        motion.get('status')!='PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA' or
        not isinstance(coords,dict) or
        coords.get('schema')!='livynth.mhclo.arch-attribution.v1' or
        set(('upper_dental_arch','lower_dental_arch','tongue'))-
             set(coords) or
        coords.get('anatomical_contact')!='NOT_TESTED' or
        not isinstance(attrib,dict) or
        attrib.get('schema')!='livynth.mhclo.arch-attribution.v1' or
        attrib.get('source_face_count')!=3540 or
        attrib.get('upper_face_count')!=1818 or
        attrib.get('lower_face_count')!=1722 or
        attrib.get('temporary_evaluated_arch_objects_removed_on_exit') is not True):
        raise ArchReviewError('E_ID024_SOURCE_GEOMETRY_GATE')
    imgs=data.get('images')
    records=attrib.get('rendered_variants')
    if (not isinstance(imgs,list) or len(imgs)!=4 or
        not all(isinstance(v,dict) for v in imgs) or
        [v.get('filename') for v in imgs]!=list(FILES) or
        not isinstance(records,list) or len(records)!=4):
        raise ArchReviewError('E_ID024_STILL_FILES')
    states=((True,False,True),(False,True,True),
            (True,True,True),(False,True,False))
    for i,record in enumerate(records):
        upper,lower,body=states[i]
        if (not isinstance(record,dict) or
            record.get('filename')!=FILES[i] or
            record.get('upper_arch_visible') is not upper or
            record.get('lower_arch_visible') is not lower or
            record.get('body_visible') is not body or
            record.get('tongue_visible') is not False or
            record.get('original_rigged_teeth_visible') is not False or
            record.get('source_assets_modified') is not False or
            record.get('visual_approval')!='PENDING'):
            raise ArchReviewError('E_ID024_ARCH_RENDER_LABELS')
    for name in FILES:
        check_png_dimensions(Path(output)/name,400,600)
    return True


def run(blender,plan,output,*,execute=subprocess.run):
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ID024_OUTPUT_EXISTS')
    completed=execute(command(blender,plan,output),cwd=str(ROOT),check=False)
    report=output/'anatomy_pose_report.json'
    if not report.is_file():
        raise ArchReviewError('E_ID024_REPORT_MISSING: Blender exit '+
                              str(completed.returncode)+'; folder '+str(output))
    data=json.loads(report.read_text(encoding='utf-8'))
    if completed.returncode!=0:
        raise ArchReviewError('E_ID024_BLENDER_EXIT_'+str(completed.returncode))
    validate(data,output)
    bundle=output/ZIP_NAME
    if bundle.exists() or bundle.is_symlink():
        raise FileExistsError('E_ID024_ZIP_EXISTS')
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
    output=args.out or (ROOT/'output/identity024_dental_arch_isolation'/
                        datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    try:
        data,bundle=run(find_blender(args.blender),args.plan,output)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2,'LIVYNTH IDENTITY-024 FAIL: '+str(exc)+
                    '\nGenerated files if any: '+str(output)+'\n')
    print(json.dumps({
        'status':data['status'],'scope':data['render_scope'],
        'images':list(FILES),'upload_zip':str(bundle),
        'arch_and_tongue_positions':data['dental_arch_location_audit'],
        'visual_approval':'PENDING',
    },indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
