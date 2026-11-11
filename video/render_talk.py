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
    p.add_argument('--preview-set', action='store_true', help='Render neutral, half-blink, full-blink, smile test stills')
    p.add_argument('--preset', choices=('studio','legacy'), default='studio')
    p.add_argument('--preview-scale', type=int, default=50, help='Preview resolution percent: 10 to 100')
    p.add_argument('--preview-samples', type=int, default=16)
    p.add_argument('--final-samples', type=int, default=32)
    p.add_argument('--max-frames', type=int, default=0, help='Limit MP4 to N frames for cheap audio smoke testing')
    p.add_argument('--front', choices=('negative-y','positive-y'), default='negative-y')
    p.add_argument('--width', type=int, default=1080)
    p.add_argument('--height', type=int, default=1920)
    args = p.parse_args(argv)
    if not 10 <= args.preview_scale <= 100:
        p.error('--preview-scale must be between 10 and 100')
    if not 1 <= args.preview_samples <= 256 or not 1 <= args.final_samples <= 256:
        p.error('sample counts must be between 1 and 256')
    if args.max_frames < 0:
        p.error('--max-frames must be >= 0')
    return args


def bounds(meshes):
    from mathutils import Vector
    corners = [obj.matrix_world @ Vector(v) for obj in meshes for v in obj.bound_box]
    return ([min(v[i] for v in corners) for i in range(3)],
            [max(v[i] for v in corners) for i in range(3)])


def animate(meshes, frames):
    all_names = set().union(*(f['morphs'].keys() for f in frames))
    targets, found, present = [], set(), set()
    for obj in meshes:
        keys = getattr(obj.data, 'shape_keys', None)
        if not keys:
            continue
        blocks = keys.key_blocks
        present.update(block.name for block in blocks)
        supported = sorted(name for name in all_names if name in blocks)
        if supported:
            targets.append((blocks, supported))
            found.update(supported)
    expected = {'eyeBlinkLeft','eyeBlinkRight','jawOpen','viseme_aa'}
    if not expected.issubset(present):
        raise RuntimeError(f"GLB missing morph targets: {sorted(expected-present)}")
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


def shot_settings(height, preset):
    """Portrait framing in fraction-of-character-height units (pure, testable)."""
    if not 0.1 < height < 10:
        raise ValueError('Unexpected full-body height')
    # Review of actual 540x960 smoke frames: prior crop placed the crown at
    # y~110 but left the face small, with excessive chest filling the portrait.
    # Reduce ortho scale and raise the aim to keep the crown from clipping.
    # This is a diagnostic shot; confirm on Windows before a full render.
    return {'camera_drop':0.06, 'ortho_scale':0.215} if preset == 'studio' else {
        'camera_drop':0.19, 'ortho_scale':0.48}


def studio_palette():
    """Diagnostic clay/garment colors only; not Character 001 texture/identity."""
    return {
        'skin': (0.59, 0.40, 0.32, 1.0),
        'shirt': (0.025, 0.055, 0.105, 1.0),
    }


def shirt_cutoff(x, z, horizontal_center, crown, height):
    """Approximate crew-neck boundary in world Z without changing topology.

    The center front neck opening is lower than the shirt at the shoulders.
    This is a *material-only* preview garment, not cloth geometry.
    """
    if height <= 0:
        raise ValueError('Height must be positive')
    shoulder = min(1.0, abs(x-horizontal_center)/(0.22*height))
    neckline = crown - height*(0.22 - 0.055*shoulder)
    return z < neckline


def find_face_body_mesh(meshes):
    """Find the morph-rich body mesh independently of imported object names.

    Blender glTF imports can rename objects, even when glTF mesh metadata
    reports "base.001". The full body has 67 ARKit/viseme keys; eyebrow/hair
    meshes have fewer. Reject helpers without the essential face controls.
    """
    markers = {'eyeBlinkLeft', 'eyeBlinkRight', 'jawOpen', 'viseme_aa'}
    candidates = []
    for obj in meshes:
        keys = getattr(getattr(obj, 'data', None), 'shape_keys', None)
        if keys is None:
            continue
        names = {block.name for block in keys.key_blocks}
        if markers.issubset(names):
            candidates.append((len(names), obj))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def mesh_shape_inventory(meshes):
    """Names and morph counts for useful diagnostics on Windows Blender."""
    out = []
    for obj in meshes:
        keys = getattr(getattr(obj, 'data', None), 'shape_keys', None)
        n = len(keys.key_blocks) if keys else 0
        out.append(f'{obj.name} ({n} shape keys)')
    return ', '.join(out)


def add_preview_shirt(meshes):
    """Tint lower basemesh as a non-destructive fitted shirt.

    A visual QA placeholder: reassigns material per polygon, preserving all
    faces, morph deltas, and vertex indices. Not an anatomical garment model.
    """
    import bpy
    from mathutils import Vector
    body = find_face_body_mesh(meshes)
    if body is None:
        raise RuntimeError(
            'Cannot identify facial basemesh for preview wardrobe. '
            'Imported objects: '+mesh_shape_inventory(meshes))
    print(f'[Livynth] Preview wardrobe selected {body.name!r}; '
          f'{len(body.data.shape_keys.key_blocks)} shape keys')
    minimum, maximum = bounds(meshes)
    h = maximum[2]-minimum[2]
    cx = (minimum[0]+maximum[0])*0.5
    # The neutral MPFB export arrives with near-uniform dark-blue material.
    # Assign distinct warm clay and navy shirt material on this imported copy
    # so geometry, mouth motion and neckline remain visible for diagnosis.
    # No textures or likeness are implied and the original GLB is untouched.
    palette = studio_palette()
    indexes = {}
    for role, label, roughness in (
        ('skin', 'Livynth Neutral Skin Clay', 0.72),
        ('shirt', 'Livynth Navy Preview Shirt', 0.88),
    ):
        mat = bpy.data.materials.new(label)
        mat.use_nodes = True
        mat.diffuse_color = palette[role]
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = palette[role]
            bsdf.inputs['Roughness'].default_value = roughness
            bsdf.inputs['Metallic'].default_value = 0.0
        body.data.materials.append(mat)
        indexes[role] = len(body.data.materials)-1
    vertices = body.data.vertices
    matrix = body.matrix_world
    assigned = 0
    clay_faces = 0
    for face in body.data.polygons:
        # Average corner positions, not face.center (which is mesh local).
        coords = [matrix @ vertices[idx].co for idx in face.vertices]
        c = sum(coords,Vector((0,0,0)))/len(coords)
        if shirt_cutoff(c.x,c.z,cx,maximum[2],h):
            face.material_index = indexes['shirt']
            assigned += 1
        else:
            face.material_index = indexes['skin']
            clay_faces += 1
    if not assigned or not clay_faces:
        raise RuntimeError('Studio preview material mask has no shirt or visible skin')
    print(f'[Livynth] Studio diagnostic materials: {clay_faces} clay and '
          f'{assigned} navy-shirt polygons; no geometry changed')


def set_test_pose(meshes, weights):
    """Set a fixed diagnostic expression on imported Blender shape keys."""
    names = ('eyeBlinkLeft','eyeBlinkRight','jawOpen',
             'mouthSmileLeft','mouthSmileRight','viseme_aa')
    for obj in meshes:
        if not obj.data.shape_keys:
            continue
        blocks = obj.data.shape_keys.key_blocks
        for name in names:
            if name in blocks:
                blocks[name].value = float(weights.get(name,0))
                # Replace the frame-one key deliberately; this prevents
                # animation evaluation from restoring the original expression
                # when Blender starts each still render.
                blocks[name].keyframe_insert(data_path='value',frame=1)
    import bpy
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def render_preview_set(scene, meshes, out):
    import bpy
    poses = {
        'neutral': {},
        'half_blink': {'eyeBlinkLeft':0.5,'eyeBlinkRight':0.5},
        'full_blink': {'eyeBlinkLeft':1.0,'eyeBlinkRight':1.0},
        'smile': {'mouthSmileLeft':0.65,'mouthSmileRight':0.65}
    }
    scene.frame_set(1)
    scene.render.image_settings.file_format = 'PNG'
    for name,weights in poses.items():
        set_test_pose(meshes,weights)
        file = out.with_name(out.stem+'_'+name+'.png')
        scene.render.filepath = str(file.resolve())
        bpy.ops.render.render(write_still=True)
        print(f'[Livynth] Rendered diagnostic {name}: {file}')


def camera_and_lights(scene, meshes, front, preset):
    import bpy
    from mathutils import Vector
    minimum, maximum = bounds(meshes)
    h = maximum[2]-minimum[2]
    settings = shot_settings(h, preset)
    center = Vector(((minimum[0]+maximum[0])/2,
                     (minimum[1]+maximum[1])/2,
                     maximum[2]-h*settings['camera_drop']))
    cam_data = bpy.data.cameras.new('Livynth Camera')
    cam = bpy.data.objects.new('Livynth Camera', cam_data)
    scene.collection.objects.link(cam)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = h*settings['ortho_scale']
    toward = -1 if front == 'negative-y' else 1
    cam.location = center+Vector((0, toward*max(1.4, h*2), 0))
    cam.rotation_euler = (center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.camera = cam
    cam_data.keyframe_insert(data_path='ortho_scale',frame=1)
    cam_data.ortho_scale *= 0.975
    cam_data.keyframe_insert(data_path='ortho_scale',frame=scene.frame_end)
    strengths = (370,195,285) if preset == 'studio' else (450,230,390)
    for name, offset, strength, size in [
        ('Key',(-0.8,-1.4,1.4),strengths[0],1.7),
        ('Fill',(0.9,-1.2,0.6),strengths[1],1.9),
        ('Rim',(0.2,0.8,0.9),strengths[2],1.1),
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
    if preset == 'studio':
        # Uniform backdrop so brightness changes do not wash out the background.
        nodes=mat.node_tree.nodes
        nodes.clear()
        output=nodes.new('ShaderNodeOutputMaterial')
        emission=nodes.new('ShaderNodeEmission')
        emission.inputs['Color'].default_value=(0.045,0.065,0.09,1.0)
        emission.inputs['Strength'].default_value=1.0
        mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
        scene.view_settings.exposure=0.05
        if scene.world:
            scene.world.use_nodes=True
            bg=scene.world.node_tree.nodes.get('Background')
            if bg:
                bg.inputs['Color'].default_value=(0.045,0.065,0.09,1)
                bg.inputs['Strength'].default_value=0.5


def include_narration(scene, path):
    editor=scene.sequence_editor_create()
    # The Blender 4.5 SequenceEditor.strips collection is empty before the
    # first sound is inserted. An empty bpy_prop_collection can be false-y,
    # so never use `or` here: it mistakes a valid empty collection for None.
    strips=getattr(editor,'strips',None)
    if strips is None:  # Blender versions exposing the older API
        strips=getattr(editor,'sequences',None)
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
    if args.max_frames:
        scene.frame_end=min(scene.frame_end,args.max_frames)
    scene.render.fps=int(timeline['fps'])
    scene.render.resolution_x=args.width
    scene.render.resolution_y=args.height
    scene.render.resolution_percentage=100
    scene.render.engine='BLENDER_EEVEE_NEXT' if bpy.app.version<(5,0,0) else 'BLENDER_EEVEE'
    scene.view_settings.view_transform='AgX'
    animate(meshes,frames)
    if args.preset == 'studio':
        add_preview_shirt(meshes)
    camera_and_lights(scene,meshes,args.front,args.preset)
    scene.eevee.taa_render_samples = (
        args.preview_samples if args.preview or args.preview_set or args.max_frames
        else args.final_samples
    )
    scene.render.resolution_percentage = args.preview_scale if (
        args.preview or args.preview_set or args.max_frames) else 100
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.preview_set:
        render_preview_set(scene,meshes,args.out.with_suffix('.png'))
    elif args.preview:
        scene.frame_set(1)
        if args.preset == 'studio':
            set_test_pose(meshes,{})
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
