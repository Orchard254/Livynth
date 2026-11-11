"""C001-GEO-04 gate - clean-room Blender evidence renderer (runs INSIDE Blender).

For one GLB and a set of orthographic views this writes

  clay_<view>.png       uniform grey matte, all textures disabled, alpha = silhouette
  wire_<view>.png       Freestyle silhouette / crease / border edge visualisation
  wireframe_<view>.png  triangle wireframe (Wireframe modifier, replace)
  textured_<view>.png   original materials (DIAGNOSTIC appearance evidence only)
  depth_<view>.npy      exact orthographic depth in metres (numpy rasteriser)
  normal_<view>.npy     world-space unit normals (numpy rasteriser)
  render_manifest.json  camera convention + per-view self-check numbers

Depth and normal maps are produced by geo/gate/raster.py inside the same
Blender run instead of Blender's render passes, because EEVEE Next's Z pass
does not survive the compositor on this build and because an exact,
renderer-independent depth map is required by the geometry metrics.  The
rasteriser's silhouette is cross-checked against Blender's own alpha channel
on every view (mask_iou) so the two can never silently diverge.

The camera convention is documented in geo/gate/camera.py and is reproduced
here verbatim; this file must stay self-contained for Blender's interpreter.

Run:
  blender --background --factory-startup --python geo/gate/blender_render.py -- \
      --glb <path> --out <dir> --calib <json> [--views front,left90,...] \
      [--res 1086 1448] [--passes clay,wire,wireframe,textured] \
      [--yaw-offset 0] [--samples 8]
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geo.gate import raster  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


GLB = Path(arg("--glb")).resolve()
OUT = Path(arg("--out")).resolve()
CALIB = json.loads(Path(arg("--calib")).read_text(encoding="utf-8"))
RES = [int(x) for x in arg("--res", "1086 1448").split()]
VIEWS = arg("--views", ",".join(CALIB["views"].keys())).split(",")
PASSES = arg("--passes", "clay,wire,wireframe,textured").split(",")
YAW_OFFSET = float(arg("--yaw-offset", "0"))
SAMPLES = int(arg("--samples", "8"))
W, H = RES[0], RES[1]
L = max(W, H)

OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("no mesh found in %s" % GLB)

# ---- world space geometry, converted into the GATE MODEL FRAME -------------
# model: +x right, +y up, +z face direction
# blender: p_B = (x, -z, y)  =>  model = (p_B.x, p_B.z, -p_B.y)
all_verts = []
all_faces = []
for o in meshes:
    mw = o.matrix_world
    base = len(all_verts)
    co = np.empty(len(o.data.vertices) * 3, dtype=np.float64)
    o.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    n = len(co)
    M = np.array(mw.to_4x4(), dtype=np.float64)
    homo = np.concatenate([co, np.ones((n, 1))], axis=1)
    world = (M @ homo.T).T[:, :3]
    model = np.stack([world[:, 0], world[:, 2], -world[:, 1]], axis=1)
    all_verts.append(model)
    idx = np.empty(len(o.data.loops), dtype=np.int64)
    o.data.loops.foreach_get("vertex_index", idx)
    tris = idx.reshape(-1, 3) + base
    all_faces.append(tris)
VERTS = np.concatenate(all_verts, axis=0)
FACES = np.concatenate(all_faces, axis=0)

lo = VERTS.min(axis=0)
hi = VERTS.max(axis=0)
EXTENT = float(max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.display_settings.display_device = "sRGB"
try:
    scene.eevee.taa_render_samples = SAMPLES
except Exception:
    pass
try:
    scene.eevee.use_raytracing = False
except Exception:
    pass

world = bpy.data.worlds.new("gate_world")
scene.world = world
world.use_nodes = True
bgn = world.node_tree.nodes.get("Background")
if bgn:
    bgn.inputs[0].default_value = (0.62, 0.62, 0.63, 1.0)
    bgn.inputs[1].default_value = 1.0

for name, energy, rot in (("key", 3.0, (55, 8, 35)), ("fill", 1.2, (65, -20, -120))):
    ld = bpy.data.lights.new(name=name, type="SUN")
    ld.energy = energy
    ob = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(ob)
    ob.rotation_euler = tuple(math.radians(a) for a in rot)

cam_data = bpy.data.cameras.new("gate_cam")
cam = bpy.data.objects.new("gate_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = "ORTHO"
cam_data.clip_start = 0.01
cam_data.clip_end = 100.0


def clay_material():
    mat = bpy.data.materials.new("gate_clay")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.55, 0.55, 0.57, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.85
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.15
    return mat


CLAY = clay_material()


ORIG_MATS = [[m for m in o.data.materials] for o in meshes]


def set_material(mode):
    """Swap every material slot to the grey clay, or restore the originals.

    The original material datablocks are kept, so the textured pass shows the
    candidate's real appearance instead of a destroyed material list.
    """
    if mode == "clay":
        for o in meshes:
            for i in range(len(o.data.materials)):
                o.data.materials[i] = CLAY
    else:
        for o, mats in zip(meshes, ORIG_MATS):
            for i, m in enumerate(mats):
                o.data.materials[i] = m


view_layer = bpy.context.view_layer


def place_camera(psi_deg, s, cx, cy):
    """Orthographic camera reproducing the gate camera convention.

        u = cx + s * (cos(psi) * x + sin(psi) * z)
        v = cy - s * y

    The camera AIMS AT THE MODEL ORIGIN so that the origin lands on the
    principal point (cx, cy); the shift_* terms carry the principal point
    offset inside the orthographic frame.  The camera sits on the model-frame
    ray (-sin psi, 0, cos psi).
    """
    psi = math.radians(psi_deg)
    dist = 4.0 * EXTENT + 1.0
    cam.location = Vector((-math.sin(psi) * dist, -math.cos(psi) * dist, 0.0))
    direction = Vector((0.0, 0.0, 0.0)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = L / s
    cam_data.shift_x = (cx - W / 2.0) / L
    cam_data.shift_y = (cy - H / 2.0) / L
    cam_data.clip_start = max(0.001, dist - 3.0 * EXTENT)
    cam_data.clip_end = dist + 3.0 * EXTENT
    return dist


def analytic_bbox(view):
    u, v, _ = raster.project(VERTS, view)
    return [float(u.min()), float(v.min()), float(u.max()), float(v.max())]


def render_to(path, freestyle=False):
    scene.use_nodes = False
    view_layer.use_freestyle = bool(freestyle)
    if freestyle:
        fs = view_layer.freestyle_settings
        fs.mode = "EDITOR"
        fs.crease_angle = math.radians(140.0)
        if not fs.linesets:
            fs.linesets.new("gate_lines")
        for ls in fs.linesets:
            ls.select_silhouette = True
            ls.select_border = True
            ls.select_crease = True
            ls.select_edge_mark = False
            ls.select_material_boundary = False
            ls.select_contour = True
            ls.select_external_contour = True
            if ls.linestyle is None:
                ls.linestyle = bpy.data.linestyles.new("gate_line_style")
            ls.linestyle.color = (0.0, 0.0, 0.0)
            ls.linestyle.thickness = 1.6
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def read_alpha(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    px = px[::-1]
    bpy.data.images.remove(img)
    return px[:, :, 3] > 0.5


wire_objs = []


def build_wireframe_copy():
    if wire_objs:
        return
    mat = bpy.data.materials.new("gate_wire")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    for o in meshes:
        dup = o.copy()
        dup.data = o.data.copy()
        scene.collection.objects.link(dup)
        mod = dup.modifiers.new("gate_wire", "WIREFRAME")
        mod.use_replace = True
        mod.use_even_offset = True
        mod.use_relative_offset = False
        mod.thickness = max(0.0006, EXTENT * 0.0012)
        dup.data.materials.clear()
        dup.data.materials.append(mat)
        wire_objs.append(dup)


def set_wire_visible(visible):
    for o in wire_objs:
        o.hide_render = not visible
    for o in meshes:
        o.hide_render = not visible


manifest = {
    "schema": "livynth.c001.gate.render.v1",
    "glb": str(GLB),
    "resolution_px": [W, H],
    "ortho_scale_px_reference": L,
    "blender": bpy.app.version_string,
    "engine": scene.render.engine,
    "yaw_offset_deg": YAW_OFFSET,
    "axis_mapping": {
        "model_frame": "+x right, +y up, +z face direction",
        "blender_frame": "p_B = (x, -z, y) after glTF import",
        "image_frame": "u right, v down, origin top-left",
    },
    "model": "orthographic; u = cx + s*(cos psi*x + sin psi*z); v = cy - s*y; camera aims at the model origin",
    "mesh": {"vertices": int(VERTS.shape[0]), "faces": int(FACES.shape[0]),
             "model_bbox_min": lo.tolist(), "model_bbox_max": hi.tolist(),
             "extent_m": EXTENT},
    "depth_source": "geo/gate/raster.py (numpy z-buffer) - not a Blender render pass",
    "views": {},
}

views_done = []

for name in VIEWS:
    c = CALIB["views"][name]
    psi = float(c["phi"]) + YAW_OFFSET
    view = {"phi": psi, "s": float(c["s"]), "cx": float(c["cx"]), "cy": float(c["cy"])}
    analytic = analytic_bbox(view)

    place_camera(psi, view["s"], view["cx"], view["cy"])
    clay_path = OUT / ("clay_%s.png" % name)
    set_material("clay")
    if "clay" in PASSES:
        render_to(clay_path)
    elif "wire" in PASSES or "wireframe" in PASSES:
        render_to(clay_path)

    blender_mask = read_alpha(clay_path)
    rast = raster.rasterize(VERTS, FACES, view, W, H)
    rast_mask = rast["mask"]
    inter = np.logical_and(blender_mask, rast_mask).sum()
    union = np.logical_or(blender_mask, rast_mask).sum()
    mask_iou = float(inter) / float(union) if union else 0.0

    np.save(OUT / ("depth_%s.npy" % name), rast["depth"].astype(np.float32))
    np.save(OUT / ("normal_%s.npy" % name), rast["normal"].astype(np.float32))

    if "wire" in PASSES:
        try:
            set_material("clay")
            render_to(OUT / ("wire_%s.png" % name), freestyle=True)
        except Exception as exc:
            print("[gate-render] wire pass failed:", repr(exc))
    if "wireframe" in PASSES:
        try:
            build_wireframe_copy()
            set_wire_visible(True)
            render_to(OUT / ("wireframe_%s.png" % name))
            set_wire_visible(False)
        except Exception as exc:
            print("[gate-render] wireframe pass failed:", repr(exc))
            set_wire_visible(False)
    if "textured" in PASSES:
        try:
            set_material("original")
            render_to(OUT / ("textured_%s.png" % name))
        except Exception as exc:
            print("[gate-render] textured pass failed:", repr(exc))
        set_material("clay")

    ys, xs = np.nonzero(rast_mask)
    rast_bbox = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())] if len(xs) else None
    manifest["views"][name] = {
        "psi_deg": psi,
        "s_px_per_m": view["s"],
        "cx_px": view["cx"],
        "cy_px": view["cy"],
        "ortho_scale_m_per_px": L / view["s"],
        "shift_x": (view["cx"] - W / 2.0) / L,
        "shift_y": (view["cy"] - H / 2.0) / L,
        "camera_position_model": [-math.sin(math.radians(psi)), 0.0, math.cos(math.radians(psi))],
        "analytic_bbox_px": analytic,
        "raster_bbox_px": rast_bbox,
        "blender_alpha_bbox_px": [float(np.nonzero(blender_mask.any(axis=0))[0].min()),
                                  float(np.nonzero(blender_mask.any(axis=1))[0].min()),
                                  float(np.nonzero(blender_mask.any(axis=0))[0].max()),
                                  float(np.nonzero(blender_mask.any(axis=1))[0].max())],
        "raster_vs_blender_mask_iou": mask_iou,
        "depth_range_m": [float(np.nanmin(rast["depth"][rast_mask])) if rast_mask.any() else None,
                          float(np.nanmax(rast["depth"][rast_mask])) if rast_mask.any() else None],
        "clip_start_m": cam_data.clip_start,
        "clip_end_m": cam_data.clip_end,
    }
    views_done.append(name)
    print("[gate-render] view %s mask_iou %.5f" % (name, mask_iou))

manifest["views_done"] = views_done
manifest["passes"] = PASSES
(OUT / "render_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("[gate-render] wrote", OUT / "render_manifest.json")
