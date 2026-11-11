#!/usr/bin/env python3
"""C001-GEO-03 Lane B — multi-view visual hull of Character 001's head.

Classical, deterministic, local reconstruction candidate. Carves a voxel grid
against weak-perspective silhouettes segmented from the 15-pose reference set
(front/±45/±90/back/top are used), triangulates with marching cubes and bakes
a planar-projected photo texture atlas.

THIS IS NOT A FACE SCAN AND NOT A LIKENESS SOLUTION. It recovers an approximate
head/hair/neck volume only. Eyes, lips, wrinkles, skin microdetail, correct
eye sockets and hair strand structure are NOT recovered. Uncalibrated
AI-generated references => absolute dimensions and camera poses are assumptions
(documented in the report).

Dependencies: numpy, Pillow, scipy, scikit-image (marching cubes), trimesh,
fast-simplification (optional decimation). See fit_report.json for versions.

Usage:
  python -m geo.visual_hull --images C:\\PROJECT\\Livynth\\assets\\characters\\character_001\\identity_capture_v1 \
      --out output/character001_visual_hull
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

IMAGE_DIR_NAME = "identity_capture_v1"
HEAD_HEIGHT_M = 0.245          # illustrative, same prior as GEO-01 (ASSUMPTION)
HEAD_CENTER_Y_M = 0.0          # world y = 0 at mid crown/chin
BASE_Y_M = -0.175              # grid bottom (neck stub)
TOP_Y_M = 0.145                # grid top (hair margin above crown, crown=+0.1225)
HALF_X_M = 0.115               # grid half width (hair + ears)
NEAR_Z_M = 0.125               # grid max z (in front of nose)
FAR_Z_M = -0.135               # grid min z (behind skull)
CELL_M = 0.0042                # voxel edge
# single global tolerance (soft-edge margin when carving); overridable per view
MASK_DILATE_PX = 2             # tolerance when carving (soft AI edges)
MASK_DILATE_45 = 2             # tolerance for the ±45° views (uncalibrated framing)
TARGET_TRIS = 14000            # decimation target if marching cubes exceeds it
ATLAS_CELL = 1024
ATLAS_COLS = 4
ATLAS_ROWS = 2

# Weak-perspective view table.
#   phi_deg : camera azimuth; camera at origin + L*(sinφ, 0, cosφ) (front=0,
#             back=180). Frame-right in the front image = +x_world.
#   crown/chin : annotated pixel rows (reused from proxy_fit.py anchors, same
#             image set; NEVER use with reframed images).
#   scale    : px per meter; None => derive from annotated crown/chin vs
#             HEAD_HEIGHT_M, else fall back to the front view's scale.
#   The head is centred horizontally by assumption (cx = width/2): framing is
#   consistent to ±1.5% across the set; cameras are NOT calibrated.
VIEWS = {
    "front":  dict(file="01_subject_front.png",  phi=0,   crown=55, chin=924, scale=None),
    "left45": dict(file="02_subject_left_45.png", phi=-45, crown=53, chin=None, scale=None),
    "right45":dict(file="03_subject_right_45.png",phi=45,  crown=42, chin=None, scale=None),
    "left90": dict(file="04_left_profile.png",   phi=-90, crown=40, chin=980, scale=None),
    "right90":dict(file="05_right_profile.png",  phi=90,  crown=34, chin=940, scale=None),
    "back":   dict(file="06_back_head.png",      phi=180, crown=19, chin=None, scale=None),
    "top":    dict(file="07_top_head.png",       phi=None, top=True, crown=None, chin=None, scale=None),
}
TOP_DEFAULTS = dict(s=4680.0, cx=543.5, cy=723.5)  # fitted, see report; ASSUMPTION
FRONT_FALLBACK_SCALE = (924 - 55) / HEAD_HEIGHT_M  # 3547.1 px/m


# ---------------------------------------------------------------- segmentation

def segment_head(rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    """Binary foreground mask for the head/neck (skin+hair), not the shirt.

    Technique: warm-hue dominance. Skin and auburn hair satisfy R - B > 15;
    the gray studio backdrop satisfies R ≈ B; the navy shirt satisfies R < B.
    Specular near-gray skin is rescued by a distance-to-border test. Interior
    holes are filled; specks/hair wisps above MIN_CC_PX are kept to preserve
    the silhouette.
    """
    from scipy import ndimage

    a = rgb.astype(np.float32)
    h, w, _ = a.shape
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    border = np.concatenate([a[:16].reshape(-1, 3), a[-16:].reshape(-1, 3),
                             a[:, :16].reshape(-1, 3), a[:, -16:].reshape(-1, 3)])
    bg = np.median(border, axis=0)                      # gray studio backdrop
    distance = np.max(np.abs(a - bg[None, None, :]), axis=2)
    warm = (R - B) > 15.0
    # rescue bright near-neutral skin highlights (forehead shine) far from bg
    bright = (distance > 70) & (R >= B)
    fg = warm | bright
    fg = ndimage.binary_closing(fg, structure=np.ones((5, 5)))
    fg = ndimage.binary_fill_holes(fg)
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        keep = np.flatnonzero(sizes >= 400) + 1         # drop specks, keep wisps
        fg = np.isin(lab, keep)
    ys, xs = np.nonzero(fg)
    stats = {
        "fg_pixels": int(fg.sum()),
        "top_row": int(ys.min()) if len(ys) else None,
        "bottom_row": int(ys.max()) if len(ys) else None,
        "col_left": int(xs.min()) if len(xs) else None,
        "col_right": int(xs.max()) if len(xs) else None,
        "bg_rgb_median": [float(v) for v in bg],
    }
    return fg, stats


# --------------------------------------------------------------- calibration

def view_params(view: dict, w: int, h: int, front_scale: float) -> dict:
    """Weak-perspective camera parameters for one view.

    Returns dict(s px/m, cx, cy (row of world y=0 / back axis), phi, top, dilate).
    """
    if view.get("top"):
        return dict(s=view.get("s", TOP_DEFAULTS["s"]), cx=view.get("cx", TOP_DEFAULTS["cx"]),
                    cy=view.get("cy", TOP_DEFAULTS["cy"]), phi=None, top=True,
                    dilate=view.get("dilate", MASK_DILATE_45))
    if view["chin"] is not None and view["crown"] is not None:
        s = (view["chin"] - view["crown"]) / HEAD_HEIGHT_M
    else:
        s = front_scale
    crown = view["crown"]
    cy = crown + s * (HEAD_HEIGHT_M / 2.0)   # row of world y=0
    return dict(s=float(s), cx=w / 2.0, cy=float(cy), phi=float(view["phi"]), top=False,
                dilate=view.get("dilate", MASK_DILATE_PX))


def project_points(points: np.ndarray, vp: dict) -> tuple[np.ndarray, np.ndarray]:
    """World (N,3) -> (u, v) pixel coords. v grows downward.

    Model: world is the subject's NEUTRAL pose (nose = +z, anatomical-left
    ear = +x) and the camera is fixed at +z; each reference photo instead
    yaws the head by psi. Orthographic (weak-perspective) projection:
        u = cx + s * (cos psi * x + sin psi * z)
        v = cy - s * y
    """
    if vp["top"]:
        u = vp["cx"] + vp["s"] * points[:, 0]
        v = vp["cy"] + vp["s"] * points[:, 2]
        return u, v
    psi = math.radians(vp["phi"])          # head yaw for this view
    c, s_ = math.cos(psi), math.sin(psi)
    u = vp["cx"] + vp["s"] * (c * points[:, 0] + s_ * points[:, 2])
    v = vp["cy"] - vp["s"] * points[:, 1]
    return u, v


# ------------------------------------------------------------------ carving

def grid_points(cell: float = CELL_M):
    xs = np.arange(-HALF_X_M, HALF_X_M, cell)
    ys = np.arange(BASE_Y_M, TOP_Y_M, cell)
    zs = np.arange(FAR_Z_M, NEAR_Z_M, cell)
    grid = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1)  # (nx,ny,nz,3)
    return xs, ys, zs, grid.reshape(-1, 3)


def carve(masks: dict[str, np.ndarray], vp_all: dict[str, dict],
          grid: np.ndarray, shape: tuple[int, int, int], cell: float = CELL_M):
    from scipy import ndimage
    keep = np.ones(len(grid), dtype=bool)
    dil = {}
    for k, m in masks.items():
        d = int(vp_all[k].get("dilate", MASK_DILATE_PX))
        dil[k] = ndimage.binary_dilation(m, iterations=d) if d > 0 else m
    for k, vp in vp_all.items():
        m = dil[k].astype(np.float32)
        u, v = project_points(grid, vp)
        hh, ww = m.shape
        coords = [v, u]
        val = ndimage.map_coordinates(m, coords, order=1, mode="constant", cval=0.0)
        keep &= val > 0.5
        print(f"  view {k}: remaining voxels {int(keep.sum())}")
    return keep.reshape(shape)


def hull_mesh(occupancy: np.ndarray, xs, ys, zs, cell: float = CELL_M) -> "trimesh.Trimesh":
    import trimesh
    from skimage.measure import marching_cubes
    # pad with a zero voxel frame so the surface always closes inside the array
    volume = np.pad(occupancy.astype(np.float32), 1)
    verts, faces, normals, _ = marching_cubes(volume, level=0.5, spacing=(cell, cell, cell))
    verts += np.array([xs[0] - cell, ys[0] - cell, zs[0] - cell])
    mesh = trimesh.Trimesh(vertices=verts.astype(np.float64), faces=faces.astype(np.int64), process=False)
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


# ------------------------------------------------------------------ texture

VIEW_ORDER = ["front", "back", "left45", "right45", "left90", "right90", "top"]
_CELL_POS = {"front": (0, 0), "back": (1, 0), "left45": (2, 0), "right45": (3, 0),
             "left90": (0, 1), "right90": (1, 1), "top": (2, 1)}


def cam_dir(vp: dict) -> np.ndarray:
    """Unit direction from the object toward the camera, in neutral world coords.

    Camera is fixed at +z; the head is yawed by psi for the view, so the only
    faces visible in the photo are those whose world normal n satisfies
    dot(Ry(psi) n, (0,0,1)) > 0, i.e. dot(n, Ry(-psi) zhat) > 0, with
    Ry(-psi) zhat = (-sin psi, 0, cos psi).
    """
    if vp["top"]:
        return np.array([0.0, 1.0, 0.0])
    psi = math.radians(vp["phi"])
    return np.array([-math.sin(psi), 0.0, math.cos(psi)])


def build_atlas(images: dict[str, Image.Image]) -> Image.Image:
    atlas = Image.new("RGB", (ATLAS_COLS * ATLAS_CELL, ATLAS_ROWS * ATLAS_CELL), (127, 127, 127))
    for name in VIEW_ORDER:
        src = images.get(name)
        if src is None:
            continue
        col, row = _CELL_POS[name]
        atlas.paste(src.convert("RGB").resize((ATLAS_CELL, ATLAS_CELL), Image.LANCZOS), (col * ATLAS_CELL, row * ATLAS_CELL))
    return atlas


def texture_face_soup(mesh, images, vp_all):
    """Assign each face to the view whose camera direction best matches the face
    normal, then project its three corners to that view's atlas cell.

    Returns (vertices, faces/corner-uvs, atlas_image) as a per-face-soup mesh.
    """
    import trimesh

    faces = mesh.faces
    vnormals = mesh.vertex_normals       # smooth, per-corner
    verts = mesh.vertices
    # Texture assignment uses ONLY the two reliable identity anchors (front + back
    # photos).  Mixing the +/-45 and +/-90 photos into the albedo produced a visible
    # double-exposure of the face (their projections shift the sampled facial pixels
    # laterally), so geometry still uses all seven views while albedo stays clean.
    TEXTURE_VIEWS = ("front", "back")
    dirs = {k: cam_dir(vp_all[k]) for k in TEXTURE_VIEWS if k in vp_all}
    keys = list(dirs)
    D = np.stack([dirs[k] for k in keys])          # (V,3)
    fnormals = mesh.face_normals                    # (F,3), outward (watertight hull)
    weights = fnormals @ D.T                        # (F,V)
    assign = weights.argmax(axis=1)                 # (F,)

    atlas = build_atlas(images)
    aw, ah = atlas.size
    soup_v = np.empty((len(faces) * 3, 3), dtype=np.float64)
    soup_uv = np.empty((len(faces) * 3, 2), dtype=np.float64)
    corner_normals = np.empty((len(faces) * 3, 3), dtype=np.float64)
    src_sizes = {k: images[k].size for k in images}  # (w,h)

    for vi, k in enumerate(keys):
        idx = np.flatnonzero(assign == vi)
        if len(idx) == 0:
            continue
        vp = vp_all[k]
        vv = verts[faces[idx].reshape(-1)].reshape(len(idx), 3, 3)
        u, v = project_points(vv.reshape(-1, 3), vp)
        sw, sh = src_sizes[k]
        # to atlas px
        col, row = _CELL_POS[k]
        u_cell = col * ATLAS_CELL + u / sw * ATLAS_CELL
        v_cell = row * ATLAS_CELL + v / sh * ATLAS_CELL
        uv = np.stack([u_cell / aw, 1.0 - v_cell / ah], axis=1).reshape(len(idx), 3, 2)
        soup_v[idx * 3] = vv[:, 0]
        soup_v[idx * 3 + 1] = vv[:, 1]
        soup_v[idx * 3 + 2] = vv[:, 2]
        soup_uv.reshape(len(faces), 3, 2)[idx] = uv
        # smooth corner normals from the welded mesh
        corner = np.stack([vnormals[faces[idx][:, 0]], vnormals[faces[idx][:, 1]], vnormals[faces[idx][:, 2]]], axis=1)
        corner_normals.reshape(len(faces), 3, 3)[idx] = corner

    soup_faces = np.arange(len(soup_v), dtype=np.int64).reshape(-1, 3)
    soup_src = np.empty(len(soup_v), dtype=np.int64)
    for vi, k in enumerate(keys):
        idx = np.flatnonzero(assign == vi)
        if len(idx) == 0:
            continue
        f = faces[idx]
        soup_src[idx * 3] = f[:, 0]
        soup_src[idx * 3 + 1] = f[:, 1]
        soup_src[idx * 3 + 2] = f[:, 2]
    soup = trimesh.Trimesh(vertices=soup_v, faces=soup_faces, vertex_normals=corner_normals, process=False)
    return soup, soup_uv, atlas, soup_src


def export_glb(mesh, images, vp_all, path: Path):
    """Export a watertight, indexed GLB with a projected texture.

    The per-face soup carries one vertex per corner, which destroys edge sharing
    (exported mesh was non-watertight and ~6x inflated). We weld by
    (position, uv) instead: vertices are shared everywhere except at UV seams,
    which is the standard glTF layout. Position-only welding must reproduce the
    closed carve, so the export asserts that explicitly.
    """
    import trimesh

    soup, uv, atlas, src = texture_face_soup(mesh, images, vp_all)
    comb = np.concatenate([np.asarray(soup.vertices), uv], axis=1)
    uniq, inv = np.unique(comb, axis=0, return_inverse=True)
    new_v = np.ascontiguousarray(uniq[:, :3])
    new_uv = np.ascontiguousarray(uniq[:, 3:5])
    new_f = np.ascontiguousarray(inv.reshape(-1, 3).astype(np.int64))

    # Smooth vertex normals: average the per-corner smooth normals inside each weld group.
    corner_n = np.asarray(mesh.vertex_normals)[src]
    acc = np.zeros((len(uniq), 3), dtype=np.float64)
    np.add.at(acc, inv, corner_n)
    cnt = np.bincount(inv, minlength=len(uniq)).astype(np.float64)[:, None]
    new_n = acc / np.maximum(cnt, 1.0)

    # Integrity check on the geometry only (position welding): the carve must be closed.
    bare = trimesh.Trimesh(vertices=new_v, faces=new_f, process=True)
    watertight = bool(bare.is_watertight)
    print(f"[export] welded mesh: {len(new_v)} verts / {len(new_f)} faces; "
          f"position-weld watertight={watertight} euler={bare.euler_number}")
    if not watertight:
        raise RuntimeError(
            "export aborted: carved hull is not closed after position welding "
            f"(euler={bare.euler_number}); refusing to ship a non-watertight candidate"
        )

    material = trimesh.visual.material.PBRMaterial(
        name="character001_visual_hull",
        baseColorTexture=atlas,
        metallicFactor=0.0,
        roughnessFactor=0.85,
    )
    welded = trimesh.Trimesh(vertices=new_v, faces=new_f, vertex_normals=new_n, process=False)
    welded.visual = trimesh.visual.TextureVisuals(uv=new_uv, material=material, image=atlas)
    scene = trimesh.Scene(welded)
    scene.export(str(path))
    return welded


# --------------------------------------------------------------- evaluation

def render_silhouette(mesh, vp: dict, w: int, h: int) -> Image.Image:
    canvas = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(canvas)
    for tri in mesh.faces:
        pts = mesh.vertices[tri]
        u, v = project_points(pts, vp)
        draw.polygon(list(zip(u, v)), fill=255)
    return canvas


def silhouette_iou(mesh, vp: dict, fg: np.ndarray) -> dict:
    h, w = fg.shape
    cand = np.asarray(render_silhouette(mesh, vp, w, h)) > 0
    inter = np.logical_and(cand, fg).sum()
    union = np.logical_or(cand, fg).sum()
    return {
        "iou": float(inter / union) if union else 0.0,
        "candidate_pixels": int(cand.sum()),
        "reference_pixels": int(fg.sum()),
        "intersection_pixels": int(inter),
    }


# --------------------------------------------------------------------- main

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(image_dir: Path, out_dir: Path, views: list[str], top_override: dict | None,
        cell: float, target_tris: int, skip_texture: bool, calib_path: Path | None = None,
        dilate45: int | None = None, smooth: int = 3):
    import trimesh  # noqa: F401  (ensures available before work)

    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    images_raw: dict[str, np.ndarray] = {}
    images_pil: dict[str, Image.Image] = {}
    masks: dict[str, np.ndarray] = {}
    stats: dict[str, dict] = {}
    vp_all: dict[str, dict] = {}
    provenance: dict[str, dict] = {}

    # --- load + segment
    for name, view in VIEWS.items():
        path = image_dir / view["file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        img = Image.open(path).convert("RGB")
        images_pil[name] = img
        a = np.asarray(img)
        images_raw[name] = a
        fg, st = segment_head(a)
        masks[name] = fg
        provenance[name] = {"file": view["file"], "sha256": sha256(path),
                            "px": list(img.size), "crown_row_annotated": view.get("crown"),
                            "chin_row_annotated": view.get("chin")}
        stats[name] = st
        print(f"[seg] {name}: {st}")

    if dilate45 is not None:
        for name in ("left45", "right45"):
            VIEWS[name] = dict(VIEWS[name], dilate=int(dilate45))

    calib = {}
    if calib_path and calib_path.is_file():
        calib = json.loads(calib_path.read_text(encoding="utf8"))
        print(f"[calib] overrides for {sorted(calib)} from {calib_path}")

    for name in VIEWS:
        v = VIEWS[name]
        if v.get("top"):
            vp = view_params(v, images_pil[name].size[0], images_pil[name].size[1], FRONT_FALLBACK_SCALE)
            if top_override:
                vp.update({k: val for k, val in top_override.items() if val is not None})
        else:
            vp = view_params(v, images_pil[name].size[0], images_pil[name].size[1], FRONT_FALLBACK_SCALE)
        if name in calib:
            for k in ("s", "cx", "cy"):
                if k in calib[name]:
                    vp[k] = float(calib[name][k])
        vp_all[name] = vp
    # (annotated views derive scale from their own crown/chin; the rest use the
    # front view's scale — the set is framed consistently except the profiles.)

    active = {k: v for k, v in vp_all.items() if k in views}
    if not active:
        raise ValueError("No views selected")

    # --- carve
    print(f"[carve] grid cell {cell} m, active views: {sorted(active)}")
    xs, ys, zs, pts = grid_points(cell)
    shape = (len(xs), len(ys), len(zs))
    print(f"[carve] voxels {shape} = {shape[0] * shape[1] * shape[2]}")
    occupancy = carve({k: masks[k] for k in active}, active, pts, shape, cell)
    volume_m3 = float(occupancy.sum() * cell**3)
    print(f"[carve] kept voxels {int(occupancy.sum())}, volume {volume_m3:.6f} m^3")

    mesh = hull_mesh(occupancy, xs, ys, zs, cell)
    raw_faces = int(len(mesh.faces))
    print(f"[mesh] marching cubes: {len(mesh.vertices)} verts, {raw_faces} faces, watertight={mesh.is_watertight}")
    if smooth > 0:
        from trimesh.smoothing import filter_laplacian
        filter_laplacian(mesh, lamb=0.5, iterations=smooth, volume_constraint=True)
        mesh.fix_normals()
        print(f"[mesh] laplacian smooth x{smooth}: watertight={mesh.is_watertight}")

    if len(mesh.faces) > target_tris:
        import trimesh
        try:
            import fast_simplification
            v, f = fast_simplification.simplify_mesh(mesh.vertices.astype(np.float64),
                                                     mesh.faces.astype(np.int64),
                                                     target_count=target_tris)
            mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
            mesh.fix_normals()
            print(f"[mesh] decimated to {len(mesh.faces)} faces, watertight={mesh.is_watertight}")
        except Exception as exc:  # pyvista missing / simplifier failure -> keep unsimplified mesh
            print(f"[mesh] decimation skipped ({exc!r}); keeping {len(mesh.faces)} faces")

    # --- texture + export
    glb_path = out_dir / "character001_visual_hull.glb"
    if not skip_texture:
        soup = export_glb(mesh, images_pil, active, glb_path)
        print(f"[export] {glb_path} ({glb_path.stat().st_size} bytes, soup faces {len(soup.faces)})")
    else:
        mesh.export(glb_path)
        print(f"[export] {glb_path} (no texture)")

    # --- evaluation: silhouette IoU per view (unoptimized, vs raw masks)
    ious = {}
    for name, fg in masks.items():
        vp = vp_all[name]
        ious[name] = silhouette_iou(mesh, vp, fg)
        print(f"[iou] {name}: {ious[name]['iou']:.3f}")
        overlay = images_pil[name].convert("RGB").copy()
        sil = np.asarray(render_silhouette(mesh, vp, fg.shape[1], fg.shape[0]))
        edge = np.zeros_like(sil)
        from scipy import ndimage
        edge[np.logical_xor(ndimage.binary_erosion(sil > 0, iterations=2), sil > 0)] = 255
        oa = np.asarray(overlay).copy()
        oa[edge > 0] = (255, 230, 0)
        Image.fromarray(oa).save(out_dir / f"overlay_{name}.png")

    report = {
        "schema": "livynth.character001.visual_hull.v1",
        "status": "experimental candidate; NOT a validated likeness; NOT animation-ready",
        "head_height_assumption_m": HEAD_HEIGHT_M,
        "cell_m": cell,
        "grid_shape": list(shape),
        "carved_voxel_volume_m3": volume_m3,
        "active_views": sorted(active),
        "top_view_params": vp_all.get("top"),
        "view_calibration": {k: {kk: vv for kk, vv in v.items()} for k, v in vp_all.items()},
        "segmentation": stats,
        "provenance": provenance,
        "mesh": {
            "marching_cubes_faces": raw_faces,
            "final_faces": int(len(mesh.faces)),
            "final_vertices": int(len(mesh.vertices)),
            "watertight": bool(mesh.is_watertight),
            "extents_m": [float(x) for x in mesh.extents],
            "bounds_m": [[float(x) for x in b] for b in mesh.bounds],
        },
        "silhouette_iou_unoptimized": ious,
        "elapsed_s": round(time.time() - t0, 2),
        "known_failure_modes": [
            "AI-generated references are uncalibrated; cameras assumed weak-perspective, same distance class per framing tier",
            "Back view distance differs from front (wider framing); scale fitted separately, may still bias carve",
            "Top view principal point/scale ASSUMED (sweep-fitted); carving against it is unverified",
            "Visual hull cannot recover eyes, nose detail, lips, sockets, ears canal detail, hair curls",
            "Texture is planar projection; seams appear where faces switch contributing view",
            "Silhouette includes hair volume; hull is head+hair, not skull",
        ],
        "glb_file": "character001_visual_hull.glb",
    }
    (out_dir / "visual_hull_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--out", type=Path, default=Path("output/character001_visual_hull"))
    p.add_argument("--views", default="front,left45,right45,left90,right90,back,top")
    p.add_argument("--cell", type=float, default=CELL_M)
    p.add_argument("--target-tris", type=int, default=TARGET_TRIS)
    p.add_argument("--top-s", type=float, default=None)
    p.add_argument("--top-cx", type=float, default=None)
    p.add_argument("--top-cy", type=float, default=None)
    p.add_argument("--calib", type=Path, default=None,
                   help="JSON file {view: {s, cx, cy}} overriding fitted calibration")
    p.add_argument("--dilate45", type=int, default=None,
                   help="carve tolerance (px) applied to the two ±45° views")
    p.add_argument("--smooth", type=int, default=3,
                   help="laplacian smoothing iterations after marching cubes (0 = off)")
    p.add_argument("--no-texture", action="store_true")
    args = p.parse_args()
    top = {"s": args.top_s, "cx": args.top_cx, "cy": args.top_cy} if any([args.top_s, args.top_cx, args.top_cy]) else None
    run(args.images, args.out, args.views.split(","), top, args.cell, args.target_tris, args.no_texture, args.calib, args.dilate45, args.smooth)


if __name__ == "__main__":
    sys.exit(main())
