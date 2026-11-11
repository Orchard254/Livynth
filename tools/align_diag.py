"""Diagnose render-vs-reference alignment: search translation/scale for best IoU.

Separates two failure modes:
  - geometry wrong  -> best achievable IoU stays low even after alignment
  - camera frame off -> best IoU is high, but only after a shift/scale correction
Run from the visual-hull worktree root:
    python tools/align_diag.py --renders <dir> --signs <signs.json> --images <dir> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo.visual_hull import VIEWS, segment_head  # noqa: E402


def shift_mask(mask, dy, dx):
    return ndimage.shift(mask.astype(np.uint8), (dy, dx), order=0, mode="constant", cval=0) > 0


def scale_mask(mask, s):
    if abs(s - 1.0) < 1e-3:
        return mask
    zoom = (s, s)
    out = ndimage.zoom(mask.astype(np.uint8), zoom, order=1) > 0
    h, w = mask.shape
    # centre-crop/pad back to the original frame
    res = np.zeros_like(mask)
    oh, ow = out.shape
    y0, x0 = max(0, (oh - h) // 2), max(0, (ow - w) // 2)
    y1, x1 = min(h, oh - (oh - h) // 2), min(w, ow - (ow - w) // 2)
    src = out[y0:y1, x0:x1]
    dst = res[: src.shape[0], : src.shape[1]]
    dst[:] = src
    return res


def best_iou(ref, cand):
    inter = float((ref & cand).sum())
    union = float((ref | cand).sum())
    return inter / union if union else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--signs", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    signs = json.loads(Path(args.signs).read_text(encoding="utf-8"))
    images_dir = Path(args.images)
    renders_dir = Path(args.renders)
    out = {"views": {}}

    for name, sgn in signs.items():
        fname = VIEWS[name]["file"]
        ref_rgb = np.asarray(Image.open(images_dir / fname).convert("RGB"), dtype=np.float32)
        ref, _ = segment_head(ref_rgb)
        tag = "p" if sgn["sign"] == "+" else "n"
        ren_rgb = np.asarray(Image.open(renders_dir / f"probe_{name}_{tag}.png").convert("RGB"), dtype=np.float32)
        ren, _ = segment_head(ren_rgb)
        h = min(ref.shape[0], ren.shape[0]); w = min(ref.shape[1], ren.shape[1])
        ref = ref[:h, :w]; ren = ren[:h, :w]

        base = best_iou(ref, ren)
        best = (base, 0, 0, 1.0)
        for s in (0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2):
            rs = scale_mask(ren, s)
            for dy in range(-160, 161, 8):
                for dx in range(-80, 81, 8):
                    v = best_iou(ref, shift_mask(rs, dy, dx))
                    if v > best[0]:
                        best = (v, dy, dx, s)
        # refine around the coarse optimum
        v0, dy0, dx0, s0 = best
        for s in (s0 - 0.03, s0, s0 + 0.03):
            if s <= 0:
                continue
            rs = scale_mask(ren, s)
            for dy in range(dy0 - 8, dy0 + 9, 2):
                for dx in range(dx0 - 8, dx0 + 9, 2):
                    v = best_iou(ref, shift_mask(rs, dy, dx))
                    if v > best[0]:
                        best = (v, dy, dx, s)
        out["views"][name] = {"iou_no_alignment": round(base, 4), "iou_after_alignment": round(best[0], 4),
                              "dy_px": int(best[1]), "dx_px": int(best[2]), "scale": round(best[3], 3)}
        print(f"{name:9s} iou_raw={base:.4f} -> iou_aligned={best[0]:.4f} "
              f"(dy={best[1]} dx={best[2]} scale={best[3]})")

    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
