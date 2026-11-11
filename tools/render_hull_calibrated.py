# C001-GEO-03 Lane B — calibrated reference-matching renders of the visual-hull candidate.
#
# Renders the hull with the SAME orthographic cameras the carve used (per-view
# scale s, principal point (cx, cy), head yaw phi), so the output is pixel-comparable
# with the reference photographs at 1086x1448 (the blind scorecard render spec).
#
# Run:
#   blender --background --python tools/render_hull_calibrated.py -- \
#       --glb <path> --report <visual_hull_report.json> --out <dir> [--views front left90 ...]
#
# Camera mapping (orthographic, weak-perspective model used by geo/visual_hull.py):
#   u = cx + s * (cos psi * x + sin psi * z)
#   v = cy - s * y
# Blender: ORTHO camera, ortho_scale = L / s  (L = max(W,H) = 1448 px),
#   shift_y = (H/2 - cy) / L,  shift_x = (cx - W/2) / L
# The yaw sign (camera azimuth vs head yaw) is resolved empirically per view by
# picking the sign whose rendered silhouette has the better IoU against the
# reference segmentation, and is reported in the render manifest.
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


glb = Path(arg("--glb"))
report_path = Path(arg("--report"))
out_dir = Path(arg("--out"))
out_dir.mkdir(parents=True, exist_ok=True)
W, H = 1086, 1448
L = max(W, H)
only_views = arg("--views")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh in GLB")
print("[import] objects:", [(o.name, len(o.data.vertices)) for o in meshes])

scene = bpy.context.scene
world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
nt = world.node_tree
if nt is None:                      # defensive: some builds need re-assignment
    world.use_nodes = False
    world.use_nodes = True
    nt = world.node_tree
bg = nt.nodes.get("Background")
if bg is None:
    bg = nt.nodes.new("ShaderNodeBackground")
    out_node = nt.nodes.get("World Output")
    nt.links.new(bg.outputs[0], out_node.inputs[0])
bg.inputs[0].default_value = (0.30, 0.30, 0.30, 1.0)
bg.inputs[1].default_value = 1.0

key_data = bpy.data.lights.new(name="key", type="SUN")
key_data.energy = 3.0
key = bpy.data.objects.new("key", key_data)
bpy.context.scene.collection.objects.link(key)
key.rotation_euler = (math.radians(55), math.radians(10), math.radians(35))

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam_data.type = "ORTHO"

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

calib = json.loads(report_path.read_text(encoding="utf-8"))["view_calibration"]
manifest = {
    "glb": str(glb),
    "resolution_px": [W, H],
    "blender": bpy.app.version_string,
    "engine": scene.render.engine,
    "model": "orthographic weak-perspective (same s/cx/cy/phi as the carve)",
    "views": {},
}


def place_camera(phi_deg, s, cx, cy, dist=2.0, yaw_sign=1.0):
    """Place an ORTHO camera matching the carve projection for one view."""
    psi = math.radians(phi_deg) * yaw_sign
    # Blender glTF import: glTF +x -> Blender +x, glTF +y(up) -> Blender +z,
    # glTF +z(face) -> Blender -y.  Head yaw psi is applied to the object frame:
    # camera azimuth = -psi keeps the projection u = cx + s*(cos psi*x + sin psi*z).
    az = -psi
    cam.location = (math.sin(az) * dist, -math.cos(az) * dist, 0.0)
    track = (Vector((0.0, 0.0, 0.0)) - cam.location).to_track_quat("-Z", "Y")
    cam.rotation_euler = track.to_euler()
    cam_data.ortho_scale = L / s
    cam_data.shift_x = (cx - W / 2.0) / L
    # Blender's shift_y moves the rendered content in the opposite sense to a naive
    # image-space offset: measured against the carve's own projection, the correct
    # sign is (cy - H/2)/L.  Verified with tools/camera_probe.py.
    cam_data.shift_y = (cy - H / 2.0) / L


# --- optional --signs <json>: render only the sign resolved by pick_render_signs.py
# (per view "+"/"-") and drop the probe_ prefix/suffix; used for the A1 vs A2
# comparison package where one image per candidate is required.
signs_path = arg("--signs")
prefix = arg("--prefix", "probe")
signs = {}
if signs_path:
    signs = json.loads(Path(signs_path).read_text(encoding="utf-8"))
    print("[signs] using per-view signs from", signs_path)

for name, c in calib.items():
    if only_views and name not in only_views.split(","):
        continue
    if c.get("top"):
        continue  # top view is rendered separately (camera looks down)
    if signs:
        sign = 1.0 if signs.get(name, {}).get("sign", "+") == "+" else -1.0
        place_camera(c["phi"], c["s"], c["cx"], c["cy"], yaw_sign=sign)
        scene.render.filepath = str(out_dir / f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)
        manifest["views"][name] = {
            "s": c["s"],
            "cx": c["cx"],
            "cy": c["cy"],
            "phi": c["phi"],
            "sign": "+" if sign > 0 else "-",
            "ortho_scale": L / c["s"],
            "shift_x": (c["cx"] - W / 2.0) / L,
            "shift_y": (H / 2.0 - c["cy"]) / L,
        }
        continue
    for sign in (1.0, -1.0):
        place_camera(c["phi"], c["s"], c["cx"], c["cy"], yaw_sign=sign)
        scene.render.filepath = str(out_dir / f"probe_{name}_{'p' if sign > 0 else 'n'}.png")
        bpy.ops.render.render(write_still=True)
    manifest["views"][name] = {
        "s": c["s"],
        "cx": c["cx"],
        "cy": c["cy"],
        "phi": c["phi"],
        "ortho_scale": L / c["s"],
        "shift_x": (c["cx"] - W / 2.0) / L,
        "shift_y": (H / 2.0 - c["cy"]) / L,
    }

(out_dir / "render_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("[manifest]", out_dir / "render_manifest.json")
print("[done] probe renders written for both yaw signs; pick the matching sign by silhouette IoU")
