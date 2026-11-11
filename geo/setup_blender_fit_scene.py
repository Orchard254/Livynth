#!/usr/bin/env python3
"""Create an editable Blender 4.5+ reference workspace for Character 001.

This imports an EXISTING morph-capable human base, preserves its shape keys,
and adds frontal, two 45-degree, and two 90-degree camera references. It does
NOT automatically fit facial identity or produce a finished digital human.

Example (PowerShell):
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python geo/setup_blender_fit_scene.py -- --glb assets/ours-photoreal.glb --images assets/characters/character_001/identity_capture_v1 --proxy output/character001_geo01/character001_silhouette_proxy.glb --out output/character001_fit_workspace.blend
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

CAMERAS = (
    ("C001 Front", "01_subject_front.png", 0),
    ("C001 Left 45", "02_subject_left_45.png", -45),
    ("C001 Right 45", "03_subject_right_45.png", 45),
    ("C001 Left 90", "04_left_profile.png", -90),
    ("C001 Right 90", "05_right_profile.png", 90),
)


def arguments(argv):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--glb", type=Path, required=True)
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--proxy", type=Path, help="Optional diagnostic hull GLB")
    p.add_argument("--out", type=Path,
                   default=Path("output/character001_fit_workspace.blend"))
    p.add_argument("--front", choices=("negative-y", "positive-y"),
                   default="negative-y")
    p.add_argument("--frame-height", type=float, default=.30,
                   help="Fraction of model height visible in each camera")
    args = p.parse_args(argv)
    if not .20 <= args.frame_height <= .55:
        p.error("--frame-height must be 0.20–0.55")
    if args.out.suffix.lower() != ".blend":
        p.error("--out must have .blend extension")
    if not args.glb.is_file():
        p.error(f"Missing GLB: {args.glb}")
    for _, filename, _ in CAMERAS:
        if not (args.images / filename).is_file():
            p.error(f"Missing reference: {args.images / filename}")
    if args.proxy and not args.proxy.is_file():
        p.error(f"Missing proxy: {args.proxy}")
    return args


def bounds(meshes):
    from mathutils import Vector
    world = [obj.matrix_world @ Vector(v)
             for obj in meshes for v in obj.bound_box]
    return ([min(v[i] for v in world) for i in range(3)],
            [max(v[i] for v in world) for i in range(3)])


def pick_face_mesh(meshes):
    markers = {"eyeBlinkLeft", "eyeBlinkRight", "jawOpen"}
    candidates = []
    for obj in meshes:
        shape_keys = getattr(obj.data, "shape_keys", None)
        names = {key.name for key in shape_keys.key_blocks} if shape_keys else set()
        candidates.append((len(names & markers), len(names), obj))
    if not candidates:
        raise RuntimeError("No meshes imported from GLB")
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def main(args):
    import bpy
    import math
    from mathutils import Vector
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()))
    source_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    subject = pick_face_mesh(source_meshes)
    bbmin, bbmax = bounds(source_meshes)
    height = bbmax[2] - bbmin[2]
    if not .5 < height < 5:
        raise RuntimeError(f"Implausible character height {height:.3f} m")
    cx = (bbmin[0] + bbmax[0]) * .5
    cy = (bbmin[1] + bbmax[1]) * .5
    focus = Vector((cx, cy, bbmax[2] - .135 * height))
    scene = bpy.context.scene
    distance = max(2., height * 2.2)
    collection = bpy.data.collections.new("C001 Reference Cameras")
    scene.collection.children.link(collection)
    sign = -1 if args.front == "negative-y" else 1
    for idx, (name, filename, angle) in enumerate(CAMERAS):
        r = math.radians(angle)
        offset = Vector((math.sin(r) * distance,
                         sign * math.cos(r) * distance, 0))
        data = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data)
        collection.objects.link(camera)
        camera.location = focus + offset
        camera.rotation_euler = (focus - camera.location).to_track_quat(
            "-Z", "Y").to_euler()
        data.type = "ORTHO"
        data.ortho_scale = height * args.frame_height
        data.show_background_images = True
        photo = data.background_images.new()
        photo.image = bpy.data.images.load(
            str((args.images / filename).resolve()), check_existing=True)
        photo.alpha = .46
        photo.display_depth = "BACK"
        photo.frame_method = "FIT"
        camera["reference_image"] = filename
        camera["camera_azimuth_deg"] = angle
        if idx == 0:
            scene.camera = camera
    if args.proxy:
        original_objects = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(args.proxy.resolve()))
        proxies = [o for o in bpy.context.scene.objects
                   if o not in original_objects and o.type == "MESH"]
        for obj in proxies:
            obj.name = "C001 diagnostic HULL (NOT facial topology)"
            scale = height * .225 / .245
            obj.scale = (scale, scale, scale)
            obj.location = (cx, cy, bbmax[2] - height * .225)
            obj.display_type = "WIRE"
            obj.show_in_front = True
            obj.hide_render = True
            obj["warning"] = "Silhouette shell only; not a facial base mesh"
    bpy.ops.object.select_all(action="DESELECT")
    subject.select_set(True)
    bpy.context.view_layer.objects.active = subject
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1448
    scene.render.resolution_percentage = 50
    scene["livynth_milestone"] = "C001-GEO-01 workspace; likeness not fitted"
    scene["canonical_identity"] = "01_subject_front.png"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
    print("[C001] Saved Blender workspace:", args.out)
    print("[C001] Selected morph-capable source:", subject.name)
    print("[C001] Source shape keys:",
          [k.name for k in subject.data.shape_keys.key_blocks]
          if subject.data.shape_keys else [])


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise SystemExit("Pass arguments after blender --")
    main(arguments(sys.argv[sys.argv.index("--") + 1:]))
