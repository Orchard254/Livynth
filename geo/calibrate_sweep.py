#!/usr/bin/env python3
"""Calibration sweep for weakly-annotated views (02/03/06/07).

Fits per-view (s, cx, cy) so the *carved hull* projects onto the reference
foreground mask with maximum IoU. Rasterises kept voxel centres (point cloud)
dilated to a few px — fast, consistent for comparison; final IoU in the report
uses full polygon rasterisation of the exported mesh.

Usage (from worktree root):
  python -m geo.calibrate_sweep --images <dir> --out output/calib_sweep \
      --views left45,right45,back,top --keep-voxels 82151 --cell 0.0042
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from geo import visual_hull as vh


def points_mask(points, w, h, vp, dilate_px=8):
    u, v = vh.project_points(points, vp)
    ix = np.floor(u).astype(np.int64)
    iy = np.floor(v).astype(np.int64)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    m = np.zeros((h, w), dtype=bool)
    m[iy[ok], ix[ok]] = True
    if dilate_px:
        m = ndimage.binary_dilation(m, iterations=dilate_px)
    return m


def iou(m, fg):
    inter = np.logical_and(m, fg).sum()
    union = np.logical_or(m, fg).sum()
    return float(inter / union) if union else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--views", required=True)
    ap.add_argument("--cell", type=float, default=vh.CELL_M)
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    # --- segment once
    raw = {}
    imgs = {}
    masks = {}
    for name, view in vh.VIEWS.items():
        p = args.images / view["file"]
        img = Image.open(p).convert("RGB")
        imgs[name] = img
        raw[name] = np.asarray(img)
        masks[name], _ = vh.segment_head(raw[name])

    # --- initial carve for point sampling (6 horizontal views, baseline calib)
    vp0 = {}
    for name, view in vh.VIEWS.items():
        vp0[name] = vh.view_params(view, imgs[name].size[0], imgs[name].size[1],
                                   vh.FRONT_FALLBACK_SCALE)

    xs, ys, zs, pts = vh.grid_points(args.cell)
    shape = (len(xs), len(ys), len(zs))
    active = [k for k in ["front", "left45", "right45", "left90", "right90", "back"]]

    def carve_with(vps):
        occ = vh.carve({k: masks[k] for k in active}, {k: vps[k] for k in active},
                       pts, shape, args.cell)
        return pts[occ.reshape(-1)]

    fitted = json.loads(args.out.joinpath("fitted_calib.json").read_text()) if args.out.joinpath("fitted_calib.json").exists() else {}

    def current_vp(name):
        vp = dict(vp0[name])
        vp.update(fitted.get(name, {}))
        return vp

    for round_i in range(args.rounds):
        print(f"=== round {round_i + 1} ===")
        vps_now = {n: current_vp(n) for n in vp0}
        kept = carve_with(vps_now)
        print(f"kept voxels: {len(kept)}")
        for name in args.views.split(","):
            img = imgs[name]
            w, h = img.size
            fg = masks[name]
            base = current_vp(name)
            # sweep space (relative to current best)
            scales = [0.94, 0.97, 1.0, 1.03, 1.06]
            best = (iou(points_mask(kept, w, h, base), fg), dict(s=base["s"], cx=base["cx"], cy=base["cy"]))
            print(f"[{name}] base IoU={best[0]:.4f} s={base['s']:.1f} cx={base['cx']:.1f} cy={base['cy']:.1f}")
            for f_s in scales:
                for dcx in (-30, -15, 0, 15, 30):
                    for dcy in (-30, -15, 0, 15, 30):
                        vp = dict(base)
                        vp["s"] = base["s"] * f_s
                        vp["cx"] = base["cx"] + dcx
                        vp["cy"] = base["cy"] + dcy
                        val = iou(points_mask(kept, w, h, vp), fg)
                        if val > best[0]:
                            best = (val, {"s": vp["s"], "cx": vp["cx"], "cy": vp["cy"]})
            print(f"[{name}] fitted IoU={best[0]:.4f} -> s={best[1]['s']:.1f} cx={best[1]['cx']:.1f} cy={best[1]['cy']:.1f}")
            fitted[name] = best[1]
            args.out.joinpath("fitted_calib.json").write_text(json.dumps(fitted, indent=2))

    print(json.dumps(fitted, indent=2))


if __name__ == "__main__":
    main()
