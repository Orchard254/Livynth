#!/usr/bin/env python3
"""Blender 4.5 headless GLB → talking-human portrait MP4.

blender -b --python video/render_talk.py -- --glb model.glb \
  --timeline timeline.json --audio voice.wav --out output/livynth_m001.mp4
"""
import argparse
import json
import math
import sys
from pathlib import Path


def args_from(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--glb', required=True, type=Path)
    p.add_argument('--timeline', required=True, type=Path)
    p.add_argument('--audio', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--front', choices=('negative-y','positive-y'), default='negative-y')
    p.add_argument('--width', type=int, default=1080)
    p.add_argument('--height', type=int, default=1920)
    return p.parse_args(argv)


def bounds(meshes):
    from mathutils import Vector
    corners = [obj.matrix_world @ Vector(v) for obj in meshes for v in obj.bound_box]
    return ([min(v[i] for v in corners) for i in range(3)],
            [max(v[i] for v in corners) for i in range(3)])


def animate(meshes, frames):
    all_names = set().union(*(f['morphs'].keys() for f in frames))
    targets, found = [], set()
    for obj in meshes:
        keys = getattr(obj.data, 'shape_keys', None)
        if not keys:
            continue
        blocks = keys.key_blocks
        supported = sorted(name for name in all_names if name in blocks)
        if supported:
            targets.append((blocks, supported))
            found.update(supported)
    expected = {'eyeBlinkLeft','eyeBlinkRight','jawOpen','viseme_aa'}
    if not expected.issubset(found):
        raise RuntimeError(f"GLB missing morph targets: {sorted(expected-found)}")
    for blocks, names in targets:
        for name in names:
            blocks[name].value = 0
    for frame in frames:
        number, weights = frame['frame'], frame['morphs']
        for blocks, names in targets:
            for name in names:
                blocks[name].value = float(weights.get(name, 0))
                blocks[name].keyframe_insert(data_path='value', frame=number)
    print(f'[Livynth] Animated {len(targets)} mesh shape-key groups, {len(found)} shapes')


def camera_and_lights(scene, meshes, front):
    import bpy
    from mathutils import Vector
    minimum, maximum = bounds(meshes)
    h = maximum[2]-minimum[2]
    if not 0.1 < h < 10:
        raise RuntimeError(f'Unexpected character height {h}')
    center = Vector(((minimum[0]+maximum[0])/2,
                     (minimum[1]+maximum[1])/2,
                     maximum[2]-h*0.19))
    cam_data = bpy.data.cameras.new('Livynth Camera')
    cam = bpy.data.objects.new('Livynth Camera', cam_data)
    scene.collection.objects.link(cam)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = h*0.48
    toward = -1 if front == 'negative-y' else 1
    cam.location = center+Vector((0, toward*max(1.4, h*2), 0))
    cam.rotation_euler = (center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.camera = cam
    cam_data.keyframe_insert(data_path='ortho_scale',frame=1)
    cam_data.ortho_scale *= 0.975
    cam_data.keyframe_insert(data_path='ortho_scale',frame=scene.frame_end)
    for name, offset, strength, size in [
        ('Key',(-0.8,-1.4,1.4),450,1.7),
        ('Fill',(0.9,-1.2,0.6),230,1.9),
        ('Rim',(0.2,0.8,0.9),390,1.1),
    ]:
        light=bpy.data.lights.new('Livynth '+name,'AREA')
        light.energy=strength
        light.shape='DISK'
        light.size=size
        obj=bpy.data.objects.new(light.name,light)
        scene.collection.objects.link(obj)
        obj.location=center+Vector(offset)*max(0.65,h)
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    behind = 1 if front == 'negative-y' else -1
    bpy.ops.mesh.primitive_plane_add(size=2,location=(center.x,center.y+behind*h*0.55,center.z))
    plane=bpy.context.object
    plane.name='Livynth Backdrop'
    plane.rotation_euler=(math.pi/2,0,0)
    plane.scale=(h*2.5,h*2.5,1)
    mat=bpy.data.materials.new('Livynth Slate')
    mat.diffuse_color=(0.11,0.135,0.17,1)
    mat.use_nodes=True
    principled=mat.node_tree.nodes.get('Principled BSDF')
    if principled:
        principled.inputs['Base Color'].default_value=(0.11,0.135,0.17,1)
        principled.inputs['Roughness'].default_value=1
    plane.data.materials.append(mat)


def include_narration(scene, path):
    editor=scene.sequence_editor_create()
    strips=getattr(editor,'strips',None) or getattr(editor,'sequences',None)
    if strips is None:
        raise RuntimeError('Blender sequence editor missing strips collection')
    sound=strips.new_sound('Livynth Voice',str(path.resolve()),channel=1,frame_start=1)
    sound.volume=1
    scene.render.use_sequencer=True
    scene.render.ffmpeg.audio_codec='AAC'
    scene.render.ffmpeg.audio_bitrate=192


def main(args):
    import bpy
    for file in (args.glb,args.timeline,args.audio):
        if not file.is_file():
            raise FileNotFoundError(file)
    timeline=json.loads(args.timeline.read_text(encoding='utf8'))
    frames=timeline.get('frames',[])
    if timeline.get('schema')!='livynth.timeline.v1' or not frames:
        raise ValueError('Invalid timeline schema or empty frames')
    if any(f.get('frame')!=i+1 for i,f in enumerate(frames)):
        raise ValueError('Frames must be numbered 1, 2, ...')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()))
    scene=bpy.context.scene
    meshes=[obj for obj in scene.objects if obj.type=='MESH']
    if not meshes:
        raise RuntimeError('No meshes imported from GLB')
    scene.frame_start,scene.frame_end=1,len(frames)
    scene.render.fps=int(timeline['fps'])
    scene.render.resolution_x=args.width
    scene.render.resolution_y=args.height
    scene.render.resolution_percentage=100
    scene.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version<(5,0,0) else 'BLENDER_EEVEE'
    scene.view_settings.view_transform='AgX'
    animate(meshes,frames)
    camera_and_lights(scene,meshes,args.front)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.preview:
        scene.frame_set(1)
        scene.render.image_settings.file_format='PNG'
        scene.render.filepath=str(args.out.with_suffix('.png').resolve())
        bpy.ops.render.render(write_still=True)
    else:
        include_narration(scene,args.audio)
        scene.render.image_settings.file_format='FFMPEG'
        scene.render.ffmpeg.format='MPEG4'
        scene.render.ffmpeg.codec='H264'
        scene.render.ffmpeg.constant_rate_factor='MEDIUM'
        scene.render.filepath=str(args.out.resolve())
        bpy.ops.render.render(animation=True)
    print('[Livynth] output:',scene.render.filepath)


if __name__=='__main__':
    if '--' not in sys.argv:
        raise SystemExit('Pass arguments after blender --')
    main(args_from(sys.argv[sys.argv.index('--')+1:]))
