# C001-GEO-03 — headless turntable render of the visual-hull GLB.
# Run: blender --background --python tools/render_hull.py -- --glb <path> --out <dir>
import bpy
import math
from math import radians, sin, cos
import sys
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
glb = argv[argv.index("--glb") + 1]
out_dir = Path(argv[argv.index("--out") + 1])
out_dir.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
# untextured flat check: replace materials with a neutral principled BSDF
if "--flat" in argv:
    flat = bpy.data.materials.new("flat")
    flat.use_nodes = True
    bsdf = flat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.75, 0.62, 0.55, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(flat)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh in GLB")
print("[import] objects:", [(o.name, len(o.data.vertices)) for o in meshes])

# gray world + neutral key light
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.30, 0.30, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
bpy.context.scene.world = world

light_data = bpy.data.lights.new(name="keylight", type="SUN")
light_data.energy = 3.0
light = bpy.data.objects.new("keylight", light_data)
bpy.context.scene.collection.objects.link(light)
light.rotation_euler = (math.radians(55), math.radians(10), math.radians(35))

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam_data.type = "ORTHO"
cam_data.ortho_scale = 0.55

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.image_settings.file_format = "PNG"

# glTF is Y-up and Blender is Z-up; Blender's glTF importer applies +90 deg about X,
# mapping glTF +z (face direction of the neutral pose) to Blender -Y and glTF +y (head up) to Blender +Z.
# Camera azimuth in glTF-neutral terms: yaw around the up axis from the face direction.
# This maps to Blender positions (face -Y, x unchanged):
dist = 0.65
frames = {                     # Blender camera offset (dx, dy, dz)
    "front":   (0.0, -dist, 0.0),
    "left45":  (-sin(radians(45)) * dist, -cos(radians(45)) * dist, 0.0),
    "left90":  (-dist, 0.0, 0.0),
    "back":    (0.0, dist, 0.0),
    "right45": (sin(radians(45)) * dist, -cos(radians(45)) * dist, 0.0),
    "right90": (dist, 0.0, 0.0),
}
for name, offset in frames.items():
    cam.location = offset
    track = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y")
    cam.rotation_euler = track.to_euler()
    scene.render.filepath = str(out_dir / f"render_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("[render]", name)

print("DONE")
