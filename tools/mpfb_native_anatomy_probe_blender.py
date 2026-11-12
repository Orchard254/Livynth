#!/usr/bin/env python3
"""Isolated Blender/MPFB fitted eye + oral anatomy experiment.

This intentionally does NOT alter the two proven demo_head_*.glb files.
It does NOT apply detailed head_shape to this preliminary neutral test human.
Anatomy asset compatibility with the parametric face is a subsequent gate.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from character.native_anatomy import load_plan,resolve_native_assets


def render_view(scene, body, name, out, angle=0.0):
    import bpy
    from mathutils import Vector
    from video.render_talk import bounds,shot_settings
    lo,hi=bounds([body])
    height=hi[2]-lo[2]
    shot=shot_settings(height,'studio')
    target=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,
                   hi[2]-height*shot['camera_drop']))
    camera=scene.camera
    radius=max(1.4,2.0*height)
    rad=math.radians(angle)
    camera.location=target+Vector((radius*math.sin(rad),
                                    -radius*math.cos(rad),0))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    path=out/(name+'.png')
    scene.render.filepath=str(path.resolve())
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size<1000:
        raise RuntimeError('E_RENDER_NOT_WRITTEN_'+name)
    return {'view':name,'file':str(path.resolve()),'bytes':path.stat().st_size}


def main(plan_file, out):
    import bpy
    from bl_ext.user_default.mpfb.services import (
        HumanService,TargetService,AssetService)
    from video.render_talk import camera_and_lights
    from character.identity_recipe import load_recipe,apply_macro_overrides

    out=Path(out).resolve()
    if out.exists() or out.is_symlink():
        raise FileExistsError('E_OUTPUT_EXISTS: '+str(out))
    plan=load_plan(plan_file)
    resolved=resolve_native_assets(plan,AssetService.find_asset_absolute_path)
    # All installed file SHA fingerprints verified before mutating Blender.
    out.mkdir(parents=True,exist_ok=False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    macro=TargetService.get_default_macro_info_dict()
    baseline=load_recipe(ROOT/'character/recipes/demo_head_a.json')
    macro=apply_macro_overrides(macro,baseline['macros'])
    body=HumanService.create_human(
        mask_helpers=True,detailed_helpers=True,extra_vertex_groups=True,
        feet_on_ground=True,scale=0.1,macro_detail_dict=macro)
    if body is None or body.type!='MESH':
        raise RuntimeError('E_MPFb_HUMAN_NOT_CREATED')
    rig=HumanService.add_builtin_rig(body,'default',import_weights=True)
    if rig is None or rig.type!='ARMATURE':
        raise RuntimeError('E_MPFb_RIG_NOT_CREATED')
    records=[]
    for selection in resolved:
        cat=selection['category']
        asset=HumanService.add_mhclo_asset(
            selection['_absolute_path_for_blender_only'],body,
            asset_type=cat.title(),subdiv_levels=0,
            material_type=selection['material_type'],
            set_up_rigging=True,interpolate_weights=True,
            import_subrig=True,import_weights=True)
        if asset is None or asset.type!='MESH' or not len(asset.data.vertices):
            raise RuntimeError('E_ATTACHMENT_EMPTY_'+cat)
        modifier_armatures=[m.object.name for m in asset.modifiers
                            if m.type=='ARMATURE' and m.object]
        parent=asset.parent.name if asset.parent else None
        if not modifier_armatures and not parent and not len(asset.vertex_groups):
            raise RuntimeError('E_ATTACHMENT_NOT_RIGGED_'+cat)
        records.append({
            'category':cat,
            'relative_path':selection['relative_path'],
            'sha256':selection['sha256'],
            'vertices':len(asset.data.vertices),
            'faces':len(asset.data.polygons),
            'object_name':asset.name,
            'parent_name':parent,
            'armature_modifier_targets':modifier_armatures,
            'vertex_groups':len(asset.vertex_groups),
            'material_slots':len(asset.material_slots),
            'material_type':selection['material_type'],
        })
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=480
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.eevee.taa_render_samples=16
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.image_settings.color_depth='8'
    scene.view_settings.view_transform='AgX'
    camera_and_lights(scene,[body],'negative-y','studio')
    # This is a neutral fitted-asset visibility test, NOT an animated jaw test.
    images=[render_view(scene,body,'neutral_front',out,0),
            render_view(scene,body,'neutral_three_quarter',out,38)]
    result={
        'schema':'livynth.native-anatomy.attach-probe.v1',
        'status':'ATTACHED_NEUTRAL_ASSETS_PENDING_VISUAL_AND_EXPRESSION_QA',
        'blender_version':bpy.app.version_string,
        'character_macros':'demo_head_a',
        'detailed_head_shape_applied':False,
        'body_native_vertices':len(body.data.vertices),
        'rig_joint_count':len(rig.data.bones),
        'expected_asset_categories':['eyes','teeth','tongue'],
        'attachments':records,
        'images':images,
        'source_unchanged':True,
        'existing_glbs_modified':False,
        'eyes_teeth_tongue_animation':'NOT_TESTED',
        'glb_export':'NOT_TESTED',
        'identity_likeness':'UNVERIFIED',
    }
    (out/'anatomy_probe.json').write_text(
        json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('[LIVYNTH IDENTITY-010] '+json.dumps({
        'status':result['status'],'rig_joints':result['rig_joint_count'],
        'categories':[row['category'] for row in records],
        'folder':str(out)},indent=2))
    return result


if __name__=='__main__':
    if '--' not in sys.argv:
        raise SystemExit('Arguments required after --')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    main(args.plan,args.out)
