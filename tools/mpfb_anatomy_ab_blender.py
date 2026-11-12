#!/usr/bin/env python3
"""Blender 4.5 / MPFB: matched A/B facial poses with fitted anatomy.

This is an isolated *scene-only* experiment. It does not read or rewrite
the successful existing A/B GLBs, and it never certifies anatomy quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from character.identity_recipe import (
    load_recipe,apply_macro_overrides,neutral_positions_sha256,neutral_topology_sha256)
from character.native_anatomy import load_plan,resolve_native_assets,REQUIRED
from character.head_shape import apply_head_shape,audit_realized_head_shape

SCHEMA='livynth.anatomy-ab-render.v1'
POSES={
    'neutral':{},
    'blink':{'eyeBlinkLeft':1.0,'eyeBlinkRight':1.0},
    'jaw_open':{'jawOpen':0.85},
    'viseme_aa':{'viseme_aa':0.90},
    'viseme_pp':{'viseme_PP':0.90},
}


def _render(scene,body,filename,angle_deg,output):
    import bpy
    from mathutils import Vector
    from video.render_talk import bounds,shot_settings
    lo,hi=bounds([body])
    h=hi[2]-lo[2]
    settings=shot_settings(h,'studio')
    target=Vector(((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,
                   hi[2]-h*settings['camera_drop']))
    radius=max(1.4,2.0*h)
    theta=math.radians(angle_deg)
    scene.camera.location=target+Vector(
        (radius*math.sin(theta),-radius*math.cos(theta),0))
    scene.camera.rotation_euler=(
        target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    path=output/(filename+'.png')
    scene.render.filepath=str(path.resolve())
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size<1000:
        raise RuntimeError('E_ANATOMY_POSE_RENDER_MISSING_'+filename)
    return {'pose':filename,'filename':path.name,'bytes':path.stat().st_size}


def _set_morphs(body,weights):
    import bpy
    keys=body.data.shape_keys
    if keys is None:
        raise RuntimeError('E_ANATOMY_POSE_SHAPE_KEYS_MISSING')
    blocks=keys.key_blocks
    if not set(weights).issubset({k.name for k in blocks}):
        raise RuntimeError('E_ANATOMY_POSE_TARGET_MISSING')
    for key in blocks:
        if key.name=='Basis': continue
        key.value=float(weights.get(key.name,0))
        key.keyframe_insert(data_path='value',frame=1)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def run(character,plan_file,output,*,align_accessories=False):
    import bpy
    import numpy as np
    from bl_ext.user_default.mpfb.services import (
        HumanService,TargetService,ExportService,FaceService,RigService,AssetService)
    from video.render_talk import camera_and_lights
    from tools.mpfb_headless_probe import _stash_armature_modifier

    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ANATOMY_POSE_OUTPUT_EXISTS')
    recipe=load_recipe(ROOT/'character/recipes'/f'{character}.json')
    if 'head_shape' not in recipe:
        raise ValueError('E_NEEDS_DETAILED_HEAD_SHAPE')
    plan=load_plan(plan_file)
    resolved=resolve_native_assets(plan,AssetService.find_asset_absolute_path)
    # Validate all files and parameters BEFORE creating the Blender scene.
    macro=apply_macro_overrides(TargetService.get_default_macro_info_dict(),
                                recipe['macros'])
    output.mkdir(parents=True,exist_ok=False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    source=HumanService.create_human(
        mask_helpers=True,detailed_helpers=True,extra_vertex_groups=True,
        feet_on_ground=True,scale=0.1,macro_detail_dict=macro)
    if source is None or source.type!='MESH':
        raise RuntimeError('E_MPFb_HUMAN_SOURCE_MISSING')
    rig=HumanService.add_builtin_rig(source,'default',import_weights=True)
    if rig is None or rig.type!='ARMATURE' or len(rig.data.bones)!=163:
        raise RuntimeError('E_MPFb_SOURCE_RIG')
    for asset in resolved:
        obj=HumanService.add_mhclo_asset(
            asset['_absolute_path_for_blender_only'],source,
            asset_type=asset['category'].title(),
            subdiv_levels=0,material_type=asset['material_type'],
            set_up_rigging=True,interpolate_weights=True,
            import_subrig=True,import_weights=True)
        if obj is None or obj.type!='MESH' or not len(obj.data.vertices):
            raise RuntimeError('E_SOURCE_ANATOMY_ATTACH_'+asset['category'])

    collection=bpy.data.collections.new('livynth_anatomy_ab_export_copy')
    bpy.context.scene.collection.children.link(collection)
    copied=ExportService.create_character_copy(
        source,name_suffix='_anatomy_ab_copy',place_in_collection=collection)
    if copied is None:
        raise RuntimeError('E_ANATOMY_COPY_NOT_CREATED')
    copies=list(collection.objects)
    meshes=[o for o in copies if o.type=='MESH']
    if len(meshes)<4:
        raise RuntimeError('E_COPIED_ANATOMY_MISSING: '+repr([x.name for x in meshes]))
    # The unbaked full-body mesh has far more vertices than eyes/teeth/tongue.
    # Never identify an attached tooth mesh as the character basemesh.
    body=max(meshes,key=lambda item:len(item.data.vertices))
    if len(body.data.vertices)<15000:
        raise RuntimeError('E_COPIED_BASEMESH_NOT_FOUND')
    copied_rigs=[o for o in copies if o.type=='ARMATURE' and len(o.data.bones)==163]
    if len(copied_rigs)!=1:
        raise RuntimeError('E_COPIED_163_JOINT_RIG')
    copy_rig=copied_rigs[0]
    actual_assets={}
    for item in resolved:
        label=Path(item['relative_path']).stem
        choices=[obj for obj in meshes if obj!=body and
                 label.lower() in obj.name.lower()]
        if len(choices)!=1:
            raise RuntimeError('E_COPIED_ASSET_'+item['category']+
                               ': '+repr([x.name for x in meshes]))
        actual_assets[item['category']]=choices[0]
    for obj in actual_assets.values():
        if (not obj.vertex_groups or
            not any(m.type=='ARMATURE' and m.object==copy_rig
                    for m in obj.modifiers)):
            raise RuntimeError('E_COPIED_ASSET_RIG_MISMATCH_'+obj.name)

    # Same verified pre-face-keys sequence used by the working Head A/B GLBs.
    _stash_armature_modifier(body)
    TargetService.bake_targets(body)
    ExportService.bake_modifiers_remove_helpers(
        body,bake_masks=True,bake_subdiv=True,
        remove_helpers=True,also_proxy=True)
    if len(body.data.vertices)!=13380 or len(body.data.polygons)!=13378:
        raise RuntimeError('E_ANATOMY_NATIVE_TOPOLOGY_CHANGED')
    source_points=np.asarray([tuple(v.co) for v in body.data.vertices],dtype=np.float64)
    quads=np.asarray([tuple(p.vertices) for p in body.data.polygons],dtype=np.int64)
    planned,_=apply_head_shape(source_points,quads,recipe['head_shape'])
    for vertex,position in zip(body.data.vertices,planned):
        vertex.co=tuple(float(v) for v in position)
    body.data.update()
    actual=np.asarray([tuple(v.co) for v in body.data.vertices],dtype=np.float64)
    shape_audit=audit_realized_head_shape(source_points,planned,actual,quads)
    alignment_audits={}
    if align_accessories:
        from character.anatomy_alignment import apply_to_blender_object
        # This is an OPT-IN IDENTITY-012 experiment. Same identity field as
        # body, evaluated in the original baked BODY coordinate frame.
        # Do not move original source anatomical objects or replace GLBs.
        bpy.context.view_layer.update()
        for cat,proxy in actual_assets.items():
            alignment_audits[cat]=apply_to_blender_object(
                body,proxy,source_points,recipe['head_shape'])
            if not alignment_audits[cat]['mesh_vertices_unchanged']:
                raise RuntimeError('E_ANATOMY_ALIGNMENT_CHANGED_TOPOLOGY_'+cat)
    RigService.ensure_armature_modifier(body,copy_rig)
    FaceService.load_targets(body,load_microsoft_visemes=False,
                             load_meta_visemes=True,load_arkit_faceunits=True)
    FaceService.interpolate_targets(body)
    if body.data.shape_keys is None:
        raise RuntimeError('E_ANATOMY_FACE_TARGETS_MISSING')
    names=[k.name for k in body.data.shape_keys.key_blocks if k.name!='Basis']
    if len(names)!=67 or not set().union(*(set(x) for x in POSES.values())).issubset(set(names)):
        raise RuntimeError('E_ANATOMY_67_MORPH_INTERFACE')

    # Remove the original character so it cannot obscure the cloned one.
    for obj in list(bpy.data.objects):
        if obj not in copies:
            bpy.data.objects.remove(obj,do_unlink=True)

    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=400
    scene.render.resolution_y=600
    scene.render.resolution_percentage=100
    scene.eevee.taa_render_samples=16
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.image_settings.color_depth='8'
    scene.view_settings.view_transform='AgX'
    camera_and_lights(scene,list(actual_assets.values())+[body],
                      'negative-y','studio')

    images=[]
    for label,weights in POSES.items():
        _set_morphs(body,weights)
        images.append(_render(scene,body,'front_'+label,0,output))
    _set_morphs(body,POSES['jaw_open'])
    images.append(_render(scene,body,'three_quarter_jaw_open',38,output))
    report={
        'schema':SCHEMA,'character_id':character,
        'status':'CAPTURED_ANATOMY_AB_REQUIRES_VISUAL_REVIEW',
        'blender_version':bpy.app.version_string,
        'source_body_sha256':neutral_positions_sha256(source_points),
        'fitted_body_sha256':neutral_positions_sha256(actual),
        'native_topology_sha256':neutral_topology_sha256(quads),
        'head_shape_audit':shape_audit,
        'native_body_vertices':len(body.data.vertices),
        'native_quads':len(body.data.polygons),
        'rig_joints':len(copy_rig.data.bones),
        'facial_morph_count':len(names),
        'facial_morph_names':names,
        'anatomy_alignment_mode':(
            'shared_identity_field' if align_accessories else 'original_mpfb_fit'),
        'anatomy_alignment_audit':alignment_audits,
        'assets':[
            {'category':cat,'source_sha256':entry['sha256'],
             'mesh_vertices':len(actual_assets[cat].data.vertices),
             'rigged_to_copied_armature':True}
            for cat,entry in [(x['category'],x) for x in resolved]
        ],
        'images':images,
        'existing_glbs_modified':False,
        'eyes_teeth_tongue_follow_expression':'PENDING_VISUAL_REVIEW',
        'natural_animation':'NOT_TESTED',
        'character_001_likeness':'NOT_TESTED',
    }
    (output/'anatomy_pose_report.json').write_text(
        json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('[LIVYNTH IDENTITY-011] '+json.dumps(
        {'character':character,'status':report['status'],
         'images':len(images),'morphs':len(names)},indent=2))
    return report


if __name__=='__main__':
    if '--' not in sys.argv: raise SystemExit('Arguments required after Blender --')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--character',choices=('demo_head_a','demo_head_b'),required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--align-accessories',action='store_true',
                        help='Apply same detailed identity field to copied eyes/teeth/tongue')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    run(args.character,args.plan,args.out,align_accessories=args.align_accessories)
