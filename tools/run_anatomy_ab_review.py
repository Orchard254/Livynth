#!/usr/bin/env python3
"""One command: attach native MPFB anatomy to both detailed heads and render poses.

Creates a new folder and portable ZIP. Never overwrites existing Head A/B GLBs.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from character.native_anatomy import load_plan,REQUIRED
from tools.identity_pose_review import check_png_dimensions

CHARACTERS=('demo_head_a','demo_head_b')
POSE_FILES=(
    'front_neutral.png','front_blink.png','front_jaw_open.png',
    'front_viseme_aa.png','front_viseme_pp.png',
    'three_quarter_jaw_open.png',
)
SCHEMA='livynth.anatomy-ab-render.v1'


class AnatomyABError(ValueError):
    pass


def plan(blender,asset_plan,output,*,align_accessories=False):
    load_plan(asset_plan)
    output=Path(output).resolve()
    return [(char,[
        str(blender),'--background','--python',
        str(ROOT/'tools/mpfb_anatomy_ab_blender.py'),'--',
        '--character',char,'--plan',str(Path(asset_plan).resolve()),
        '--out',str((output/char).resolve())]+(
        ['--align-accessories'] if align_accessories else []))
        for char in CHARACTERS]


def validate_character(report,folder,character,*,expect_alignment=False):
    if (not isinstance(report,dict) or report.get('schema')!=SCHEMA or
        report.get('status')!='CAPTURED_ANATOMY_AB_REQUIRES_VISUAL_REVIEW' or
        report.get('character_id')!=character or
        report.get('existing_glbs_modified') is not False or
        report.get('rig_joints')!=163 or report.get('facial_morph_count')!=67 or
        report.get('native_body_vertices')!=13380 or
        report.get('native_quads')!=13378):
        raise AnatomyABError('E_ANATOMY_AB_REPORT_'+character)
    if (not isinstance(report.get('head_shape_audit'),dict) or
        report['head_shape_audit'].get('status')!='PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS' or
        not isinstance(report.get('facial_morph_names'),list) or
        len(set(report['facial_morph_names']))!=67 or
        not report.get('source_body_sha256') or not report.get('fitted_body_sha256') or
        not report.get('native_topology_sha256')):
        raise AnatomyABError('E_ANATOMY_AB_GEOMETRY_'+character)
    if expect_alignment:
        if report.get('anatomy_alignment_mode')!='shared_identity_field':
            raise AnatomyABError('E_IDENTITY_FIELD_ALIGNMENT_NOT_APPLIED_'+character)
        audits=report.get('anatomy_alignment_audit')
        if not isinstance(audits,dict) or set(audits)!=set(REQUIRED):
            raise AnatomyABError('E_IDENTITY_FIELD_ALIGNMENT_AUDIT_'+character)
        for category,audit in audits.items():
            if (audit.get('status')!='IDENTITY_FIELD_APPLIED_NOT_VISUALLY_APPROVED'
                or audit.get('vertices',0)<100
                or audit.get('mesh_vertices_unchanged') is not True
                or audit.get('max_displacement_m',1)>0.025
                or audit.get('max_storage_error_m',1)>0.000002):
                raise AnatomyABError('E_IDENTITY_FIELD_ALIGNMENT_'+category)
    assets=report.get('assets')
    if (not isinstance(assets,list) or
        [a.get('category') for a in assets]!=list(REQUIRED) or
        any(a.get('mesh_vertices',0)<100 or
            a.get('rigged_to_copied_armature') is not True for a in assets)):
        raise AnatomyABError('E_ANATOMY_AB_RIGGED_ASSETS_'+character)
    imgs=report.get('images')
    if not isinstance(imgs,list) or [x.get('filename') for x in imgs]!=list(POSE_FILES):
        raise AnatomyABError('E_ANATOMY_AB_IMAGE_SET_'+character)
    for filename in POSE_FILES:
        check_png_dimensions(folder/filename,400,600)
    return True


def compare_reports(a,b):
    for character,report in zip(CHARACTERS,(a,b)):
        validate_character(report,Path(report['_validated_folder']),character)
    if (a['source_body_sha256']!=b['source_body_sha256'] or
        a['native_topology_sha256']!=b['native_topology_sha256'] or
        a['facial_morph_names']!=b['facial_morph_names']):
        raise AnatomyABError('E_INCOMPATIBLE_SOURCE_TOPOLOGY_OR_FACE_TARGETS')
    if a['fitted_body_sha256']==b['fitted_body_sha256']:
        raise AnatomyABError('E_SAME_FITTED_IDENTITY')
    return {'schema':'livynth.anatomy-ab-compare.v1',
            'status':'CAPTURED_REQUIRES_INDEPENDENT_ANATOMY_REVIEW',
            'characters':list(CHARACTERS),
            'images_total':len(POSE_FILES)*len(CHARACTERS),
            'rig_joints':163,
            'face_targets':67,
            'same_native_source_and_topology':True,
            'different_head_geometry':True,
            'native_eye_teeth_tongue_rigged':'STRUCTURAL_ONLY',
            'eye_lid_teeth_tongue_visual_quality':'PENDING',
            'oral_anatomy_following_jaw':'PENDING',
            'full_character_glb_export':'NOT_TESTED',
            'image_reference_likeness':'NOT_TESTED'}


def _gallery():
    blocks=['<!doctype html><html><head><meta charset="utf-8"><title>LIVYNTH anatomy A/B</title>',
            '<style>body{background:#23303e;color:white;font:16px system-ui;margin:20px}'
            'img{width:min(42vw,400px);border:1px solid #677}'
            '.pair{display:flex;gap:16px;margin-bottom:18px}</style></head><body>',
            '<h1>LIVYNTH anatomy fitting on both identities</h1>',
            '<p>Human review required: inspect eyelid/eyeball fit and'
            ' teeth/tongue alignment in jaw and viseme images.</p>']
    for image in POSE_FILES:
        blocks.append('<h2>'+image.replace('_',' ').replace('.png','')+'</h2><div class="pair">')
        for char in CHARACTERS:
            blocks.append('<figure><img src="'+char+'/'+image+'"><figcaption>'+char+'</figcaption></figure>')
        blocks.append('</div>')
    blocks.append('</body></html>')
    return ''.join(blocks)


def run(blender,asset_plan,output,*,align_accessories=False,execute=subprocess.run):
    output=Path(output).resolve()
    jobs=plan(blender,asset_plan,output,align_accessories=align_accessories)
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ANATOMY_AB_OUTPUT_EXISTS')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.mkdir(exist_ok=False)
    reports=[]
    for character,command in jobs:
        print('[LIVYNTH IDENTITY-011] Rendering',character,flush=True)
        execute(command,cwd=str(ROOT),check=True)
        where=output/character
        report=json.loads((where/'anatomy_pose_report.json').read_text(encoding='utf-8'))
        report['_validated_folder']=str(where)
        validate_character(report,where,character,expect_alignment=align_accessories)
        reports.append(report)
    final=compare_reports(*reports)
    final['anatomy_alignment_mode']=(
        'shared_identity_field' if align_accessories else 'original_mpfb_fit')
    final['anatomy_alignment_quality']='PENDING_VISUAL_REVIEW'
    (output/'anatomy_ab_review.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    (output/'index.html').write_text(_gallery(),encoding='utf-8')
    zip_path=output.with_suffix('.zip')
    if zip_path.exists() or zip_path.is_symlink():
        raise FileExistsError('E_ANATOMY_AB_ZIP_EXISTS')
    # Never package geometry, photos, Blender project files, or local absolute
    # source paths beyond those already present in the per-character reports.
    files=[output/'anatomy_ab_review.json',output/'index.html']
    for character in CHARACTERS:
        folder=output/character
        files.append(folder/'anatomy_pose_report.json')
        files.extend(folder/name for name in POSE_FILES)
    manifest={'schema':'livynth.anatomy-ab-archive.v1',
              'status':'UNREVIEWED_ANATOMY_RENDER_EVIDENCE',
              'files':{str(p.relative_to(output)).replace('\\','/'):
                        hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in files}}
    with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in files:
            z.write(file,arcname=file.relative_to(output).as_posix())
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
    return final,zip_path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',default='')
    parser.add_argument('--plan',type=Path,
                        default=ROOT/'character/appearance/native_anatomy_demo.json')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--align-accessories',action='store_true',
                        help='Opt-in aligned anatomy experiment; originals remain unchanged')
    args=parser.parse_args(argv)
    from livynth_studio import find_blender
    output=args.out or ROOT/'output'/'anatomy_ab_review'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        result,archive=run(find_blender(args.blender),args.plan,output,align_accessories=args.align_accessories)
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        parser.exit(2,'LIVYNTH IDENTITY-011 FAILED: '+str(exc)+
                    '\nPartial evidence: '+str(output)+'\n')
    print(json.dumps({'status':result['status'],'review_archive':str(archive),
                      'images':result['images_total']},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
