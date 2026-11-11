"""C001-GEO-04 gate - candidate handling: load, camera fit, render, load back.

A candidate is an exported GLB.  The model frame is the glTF frame:
+x right, +y up, +z the direction the face points.  trimesh loads a GLB
without rotating it, so trimesh coordinates ARE the model frame.

CAMERA FIT (per candidate, per view)
-----------------------------------
The reference photographs have a per-view scale s_ref (px per metre) and a
principal point that were fitted to the photographs themselves.  A candidate
may be in a different frame and a different size, so the gate fits, for each
view, the orthographic camera that puts the CANDIDATE's head silhouette into
the SAME pixel frame as the corresponding reference photograph:

    s_cand_v   = reference_head_width_px_v / candidate_head_width_m_v
    cx_cand_v  = reference_head_centre_u_v - s_cand_v * candidate_centre_u_m
    cy_cand_v  = reference_head_centre_v_v + s_cand_v * candidate_centre_y_m

The head width of a candidate is measured on its own geometry (the lateral
extent of the model frame), never on an image, so the fit cannot launder
appearance into the geometry.  The scale factor s_cand_v is a per-view
normalisation: shape ratios are therefore compared in METRES on both sides.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from . import raster
from .raster import view_basis

GATE_DIR = Path(__file__).resolve().parent
REPO_ROOT = GATE_DIR.parents[1]
BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


def load_candidate(path):
    """Vertices and faces of every mesh in the GLB, in the model frame."""
    scene = trimesh.load(str(path), force="scene")
    verts = []
    faces = []
    for g in scene.geometry.values():
        base = sum(len(v) for v in verts)
        verts.append(np.asarray(g.vertices, dtype=np.float64))
        faces.append(np.asarray(g.faces, dtype=np.int64) + base)
    if not verts:
        raise ValueError("no geometry in %s" % path)
    return {"verts": np.concatenate(verts, 0), "faces": np.concatenate(faces, 0)}


def _model_bbox_for_view(verts, psi):
    right, up, fwd = view_basis({"phi": psi})
    lat = verts @ right
    vert = verts @ up
    return {
        "lat_min": float(lat.min()), "lat_max": float(lat.max()),
        "up_min": float(vert.min()), "up_max": float(vert.max()),
        "lat_centre": float((lat.min() + lat.max()) / 2.0),
        "up_centre": float((vert.min() + vert.max()) / 2.0),
        "lat_width_m": float(lat.max() - lat.min()),
        "up_height_m": float(vert.max() - vert.min()),
    }


def fit_cameras(cand, ref, view_names):
    """Fit the per-view orthographic cameras of one candidate."""
    out = {"schema": "livynth.c001.gate.camera-fit.v1", "views": {}, "notes": {
        "method": "per view: s = reference head width px / candidate head width m; "
                  "cx, cy align the head bounding boxes",
        "reference_scale_px_per_m": "geo/gate/reference_views.json (fitted to the photographs)",
    }}
    for name in view_names:
        v = ref["views"][name]
        rc = v["reference_camera"]
        bb = _model_bbox_for_view(cand["verts"], float(rc["phi"]))
        ref_w_px = float(rc["head_width_px"])
        s_cand = ref_w_px / max(bb["lat_width_m"], 1e-9)
        cx = float(rc["centre_u_px"]) - s_cand * bb["lat_centre"]
        cy = float(rc["centre_v_px"]) + s_cand * bb["up_centre"]
        out["views"][name] = {
            "phi": float(rc["phi"]),
            "s": float(s_cand),
            "cx": float(cx),
            "cy": float(cy),
            "reference_s_px_per_m": float(rc["s_px_per_m"]),
            "reference_head_width_px": ref_w_px,
            "candidate_head_width_m": bb["lat_width_m"],
            "candidate_head_height_m": bb["up_height_m"],
            "scale_ratio_vs_reference": float(s_cand / max(rc["s_px_per_m"], 1e-9)),
        }
    return out


def render_candidate(glb_path, calib_path, out_dir, views, blender=BLENDER,
                     passes="clay,wire,wireframe,textured", samples=8):
    """One Blender run producing every geometry evidence image."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [blender, "--background", "--factory-startup",
           "--python", str(GATE_DIR / "blender_render.py"), "--",
           "--glb", str(glb_path), "--out", str(out_dir),
           "--calib", str(calib_path),
           "--views", ",".join(views),
           "--passes", passes,
           "--samples", str(samples)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    log = out_dir / "blender_render.log"
    log.write_text(res.stdout + "\n--- STDERR ---\n" + res.stderr, encoding="utf-8")
    return {"returncode": res.returncode, "log": str(log),
            "tail": (res.stdout or "")[-2000:]}


def _grey_background(rgba, colour=(150, 150, 152)):
    bg = np.zeros(rgba.shape[:2] + (3,), dtype=np.float64)
    bg[:, :] = np.array(colour, dtype=np.float64) / 255.0
    a = rgba[:, :, 3:4]
    return bg * (1.0 - a) + rgba[:, :, :3] * a


def _turbo_like(x):
    x = np.clip(x, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0, 1)
    g = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0, 1)
    b = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0, 1)
    return np.stack([r, g, b], axis=-1)


def load_renders(out_dir, views, write_review=True):
    """Read the Blender outputs back and build the review images."""
    out_dir = Path(out_dir)
    res = {}
    for name in views:
        clay_path = out_dir / ("clay_%s.png" % name)
        if not clay_path.exists():
            continue
        rgba = np.asarray(Image.open(clay_path).convert("RGBA"), dtype=np.float64) / 255.0
        mask = rgba[:, :, 3] > 0.5
        depth = np.load(out_dir / ("depth_%s.npy" % name)).astype(np.float64)
        normal = np.load(out_dir / ("normal_%s.npy" % name)).astype(np.float64)
        entry = {"mask": mask, "depth": depth, "normal": normal,
                 "rgba": rgba, "width": rgba.shape[1], "height": rgba.shape[0]}
        if write_review:
            comp = (_grey_background(rgba) * 255.0).astype(np.uint8)
            Image.fromarray(comp).save(out_dir / ("review_clay_%s.png" % name))
            d = depth.copy()
            finite = np.isfinite(d)
            if finite.any():
                lo = np.percentile(d[finite], 1)
                hi = np.percentile(d[finite], 99)
                norm = np.zeros_like(d)
                norm[finite] = (d[finite] - lo) / max(hi - lo, 1e-9)
                rgb = (_turbo_like(norm) * 255.0).astype(np.uint8)
                rgb[~finite] = 20
            else:
                rgb = np.zeros(d.shape + (3,), dtype=np.uint8)
            Image.fromarray(rgb).save(out_dir / ("review_depth_%s.png" % name))
            n = normal.copy()
            nn = np.linalg.norm(n, axis=2, keepdims=True)
            nn[nn == 0] = 1.0
            n = n / nn
            nrgb = ((n * 0.5 + 0.5) * 255.0).astype(np.uint8)
            nrgb[~mask] = 20
            Image.fromarray(nrgb).save(out_dir / ("review_normal_%s.png" % name))
        res[name] = entry
    return res
