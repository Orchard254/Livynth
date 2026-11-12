#!/usr/bin/env python3
"""Blender 4.5: render matched low-cost facial poses from an EXISTING rigged GLB.

Called by tools/run_identity_pose_review.py:
blender --background --python tools/render_identity_poses_blender.py -- \
    --glb old.glb --character demo_head_a --out fresh_dir/demo_head_a

This is a visual diagnostic ONLY. It does not reconstruct a character, train
models, add animation clips, assert photorealism or certify human likeness.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools.identity_pose_review import (
    SCHEMA, CHARACTERS, render_jobs, raster_change, PoseReviewError)


def parse(argv):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glb',type=Path,required=True)
    parser.add_argument('--character',choices=CHARACTERS,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=16)
    args=parser.parse_args(argv)
    if not 4<=args.samples<=64:
        parser.error('--samples must be between 4 and 64')
    if not args.glb.is_file():
        parser.error('Input GLB missing')
    if args.out.exists():
        parser.error('Output character folder already exists')
    return args


def apply_expression(meshes,weights):
    """Set all imported shape keys, not just the six older preview controls."""
    import bpy
    found=set()
    for obj in meshes:
        if obj.data.shape_keys is None:
            continue
        blocks=obj.data.shape_keys.key_blocks
        for block in blocks:
            if block.name=='Basis':
                continue
            block.value=float(weights.get(block.name,0.0))
            block.keyframe_insert(data_path='value',frame=1)
            found.add(block.name)
    absent=set(weights)-found
    if absent:
        raise PoseReviewError('E_REQUIRED_POSE_SHAPE_MISSING: '+repr(sorted(absent)))
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def read_rendered_rgba(path, width, height):
    import bpy
    image=bpy.data.images.load(str(path.resolve()),check_existing=False)
    try:
        actual=tuple(image.size)
        if actual!=(width,height):
            raise PoseReviewError('E_RENDER_DIMENSIONS: '+repr(actual))
        buf=array('f',[0.0])*(width*height*4)
        image.pixels.foreach_get(buf)
        return buf
    finally:
        bpy.data.images.remove(image)


def apply_view(scene,front_camera,angle_deg,center):
    from mathutils import Vector
    front_camera=scene.camera
    radius=max(1.4,2.0*float(center['height']))
    angle=math.radians(angle_deg)
    target=Vector(center['point'])
    front_camera.location=target+Vector((radius*math.sin(angle),
                                           -radius*math.cos(angle),0))
    front_camera.rotation_euler=(target-front_camera.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    import bpy
    bpy.context.view_layer.update()


def main(args):
    import bpy
    from mathutils import Vector
    from video.render_talk import (
        bounds,shot_settings,find_face_body_mesh,add_preview_shirt,camera_and_lights)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()))
    scene=bpy.context.scene
    meshes=[x for x in scene.objects if x.type=='MESH']
    body=find_face_body_mesh(meshes)
    if body is None:
        raise PoseReviewError('E_IMPORTED_FACE_KEYS_MISSING')
    names={key.name for key in body.data.shape_keys.key_blocks}
    required=set().union(*(set(weights) for _,_,weights in render_jobs()))
    if not required.issubset(names):
        raise PoseReviewError('E_IMPORTED_POSE_CONTROLS: '+repr(sorted(required-names)))
    scene.frame_start,scene.frame_end=1,2
    scene.frame_set(1)
    scene.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version<(5,0,0) else 'BLENDER_EEVEE'
    scene.render.resolution_x=400
    scene.render.resolution_y=600
    scene.render.resolution_percentage=100
    scene.eevee.taa_render_samples=args.samples
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.image_settings.color_depth='8'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX'
    add_preview_shirt(meshes)
    minimum,maximum=bounds([body])
    h=maximum[2]-minimum[2]
    settings=shot_settings(h,'studio')
    target=(0.5*(minimum[0]+maximum[0]),
            0.5*(minimum[1]+maximum[1]),
            maximum[2]-h*settings['camera_drop'])
    camera_and_lights(scene,meshes,'negative-y','studio')
    args.out.mkdir(parents=True,exist_ok=False)
    metrics=[]
    neutral_by_view={}
    for view,pose,weights in render_jobs():
        if view not in neutral_by_view:
            if pose!='neutral':
                raise PoseReviewError('E_VIEW_WITHOUT_NEUTRAL')
            apply_view(scene,scene.camera,0 if view=='front' else 38,
                       {'point':target,'height':h})
        apply_expression(meshes,weights)
        output=args.out/(view+'_'+pose+'.png')
        scene.render.filepath=str(output.resolve())
        bpy.ops.render.render(write_still=True)
        if not output.is_file() or output.stat().st_size<1000:
            raise PoseReviewError('E_RENDER_FILE_MISSING: '+str(output))
        raster=read_rendered_rgba(output,400,600)
        if pose=='neutral':
            neutral_by_view[view]=raster
            motion=None
        else:
            motion=raster_change(neutral_by_view[view],raster,400,600)
            if motion['status']!='SIGNAL_PRESENT_NOT_VISUAL_APPROVAL':
                raise PoseReviewError('E_INVISIBLE_RENDERED_POSE: '+view+' '+pose+
                                      ' '+json.dumps(motion))
        metrics.append({'view':view,'pose':pose,'path':str(output.resolve()),
                        'weights':weights,'rendered_motion':motion})
        print('[LIVYNTH IDENTITY-007]',view,pose,'rendered',output,
              'motion=',(motion or {}).get('status'),flush=True)
    report={
        'schema':SCHEMA,
        'status':'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW',
        'character_id':args.character,
        'glb_source':str(args.glb.resolve()),
        'glb_sha256':hashlib.sha256(args.glb.read_bytes()).hexdigest(),
        'blender_version':bpy.app.version_string,
        'samples':args.samples,'resolution':[400,600],
        'poses':len(metrics),'native_animation_interface':'EXPORTED_MORPH_SIGNAL_VERIFIED',
        'identity_likeness':'UNVERIFIED',
        'visible_expression_naturalness':'PENDING_HUMAN_REVIEW',
        'renders':metrics,
    }
    (args.out/'render_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    if '--' not in sys.argv:
        raise SystemExit('Pass arguments after blender --')
    main(parse(sys.argv[sys.argv.index('--')+1:]))
