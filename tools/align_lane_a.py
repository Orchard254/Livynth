"""Align a TripoSR candidate into the LIVYNTH reference frame (measured, not guessed).

TripoSR emits a mesh in its own normalized camera space (no UVs, vertex colours only,
not watertight).  To compare it with the reference photographs:
  1. find the axis convention by silhouette IoU over the 24 proper rotations,
  2. fit a uniform scale + lateral/vertical offset so the projected silhouette
     matches the reference foreground (measured IoU, no analytic guessing),
  3. export the transformed mesh so the calibrated render harness can shoot it.

Usage:
    python tools/align_lane_a.py --mesh <mesh.glb> --report <visual_hull_report.json> \
        --images <ref dir> --out <aligned.glb> [--json <stats.json>]
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo.visual_hull import segment_head  # noqa: E402

RES = 256


def rotations():
    mats = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = np.zeros((3, 3))
            for row, col in enumerate(perm):
                m[row, col] = signs[row]
            if np.linalg.det(m) == 1:
                mats.append(m)
    return mats


def rasterize(uv, faces, size=RES):
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    for f in faces:
        draw.polygon([(uv[f[0], 0], uv[f[0], 1]), (uv[f[1], 0], uv[f[1], 1]), (uv[f[2], 0], uv[f[2], 1])], fill=255)
    return np.asarray(img) > 0


def iou(a, b):
    u = int((a | b).sum())
    return float((a & b).sum()) / u if u else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    calib = report["view_calibration"]
    prov = report["provenance"]

    mesh = trimesh.load(args.mesh, force="mesh")
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    print(f"[mesh] {len(verts)} verts / {len(faces)} faces")

    # Reference front mask at native resolution + a downscaled copy for the search.
    ref_path = Path(args.images) / prov["front"]["file"]
    ref_rgb = np.asarray(Image.open(ref_path).convert("RGB"), dtype=np.float32)
    ref_mask, _ = segment_head(ref_rgb)
    H, W = ref_mask.shape
    ref_small = np.asarray(Image.fromarray((ref_mask * 255).astype(np.uint8)).resize((RES, RES), Image.BILINEAR)) > 127
    s_px = calib["front"]["s"]
    cx, cy = calib["front"]["cx"], calib["front"]["cy"]
    print(f"[ref] mask {ref_mask.shape}  s={s_px:.1f} px/m  cx={cx} cy={cy}")

    sub = faces[:: max(1, len(faces) // 40000)]

    def project(unit_verts, k, dx, dy):
        """Project unit-space vertices into the 256px reference frame."""
        u = (cx + s_px * (unit_verts[:, 0] * k) + dx) / W * RES
        v = (cy - s_px * (unit_verts[:, 1] * k) + dy) / H * RES
        return np.stack([u, v], axis=1)

    # --- 1. orientation search ----------------------------------------------
    best = None
    for m in rotations():
        r = verts @ m.T
        lo, hi = r.min(axis=0), r.max(axis=0)
        span = hi - lo
        base = (RES - 4) / max(span[0], span[1])
        r2 = r.copy()
        r2[:, 0] = (r2[:, 0] - lo[0]) * base + 2
        r2[:, 1] = (RES - 2) - (r2[:, 1] - lo[1]) * base
        mask = rasterize(r2[:, :2], sub)
        v = iou(ref_small, mask)
        if best is None or v > best[0]:
            best = (v, m.copy(), r.copy())
    rot_iou, m, r = best
    print(f"[orient] best rotation IoU={rot_iou:.4f}")

    # world axes: x = image right, y = image up, z = depth (towards camera)
    # neutral LIVYNTH pose: +y up, +z forward (nose), +x = anatomical left
    unit = r.copy()
    unit[:, 1] = unit[:, 1]
    unit[:, 2] = -unit[:, 2]
    # normalise to unit height and centre
    unit[:, 1] -= (unit[:, 1].max() + unit[:, 1].min()) / 2.0
    unit[:, 0] -= unit[:, 0].mean()

    # --- 2. scale + offset fit (measured) -----------------------------------
    def score(k, dx, dy):
        uv = project(unit, k, dx, dy)
        return iou(ref_small, rasterize(uv, sub))

    best_fit = None
    for k in (0.18, 0.22, 0.26, 0.30, 0.34, 0.40, 0.46):
        for dy in range(-40, 41, 8):
            for dx in range(-30, 31, 10):
                v = score(k, dx, dy)
                if best_fit is None or v > best_fit[0]:
                    best_fit = (v, k, dx, dy)
    v0, k0, dx0, dy0 = best_fit
    for k in (k0 - 0.02, k0, k0 + 0.02):
        if k <= 0:
            continue
        for dy in range(dy0 - 8, dy0 + 9, 4):
            for dx in range(dx0 - 10, dx0 + 11, 5):
                v = score(k, dx, dy)
                if v > best_fit[0]:
                    best_fit = (v, k, dx, dy)
    fit_iou, k, dx, dy = best_fit
    print(f"[fit] IoU={fit_iou:.4f}  k={k:.3f} dx={dx} dy={dy}")

    # k is metres per unit: a unit-height mesh maps to k metres; convert the
    # pixel offsets into metres along the camera axes.
    metres_x = dx / W * RES * 0 + (dx / RES) * (W / s_px)
    metres_y = -(dy / RES) * (H / s_px)

    world = unit.copy()
    world[:, 0] = world[:, 0] * k + metres_x
    world[:, 1] = world[:, 1] * k + metres_y
    world[:, 2] = world[:, 2] * k
    # metres_x/metres_y above are already metres; world is now in metres
    world[:, 0] = unit[:, 0] * k + metres_x
    world[:, 1] = unit[:, 1] * k + metres_y

    out_mesh = trimesh.Trimesh(vertices=world, faces=faces, process=False)
    if hasattr(mesh.visual, "vertex_colors"):
        out_mesh.visual = trimesh.visual.ColorVisuals(vertex_colors=np.asarray(mesh.visual.vertex_colors))
    out_mesh.export(args.out)
    print(f"[export] {args.out} extents={np.round(out_mesh.extents, 4).tolist()}")

    stats = {
        "mesh_in": str(args.mesh),
        "aligned_out": str(args.out),
        "verts": int(len(world)),
        "faces": int(len(faces)),
        "rotation": m.tolist(),
        "orientation_iou_proxy": round(float(rot_iou), 4),
        "fit_iou_front_256": round(float(fit_iou), 4),
        "metres_per_unit": float(k),
        "offset_m": [round(float(metres_x), 5), round(float(metres_y), 5)],
        "extents_m": np.round(out_mesh.extents, 4).tolist(),
        "notes": ["scale/offset fitted by silhouette IoU against the front reference mask",
                  "lateral/vertical offsets expressed in metres using the front view scale"],
    }
    if args.json:
        Path(args.json).write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
