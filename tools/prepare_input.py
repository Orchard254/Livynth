"""Prepare a TripoSR input image: subject over neutral gray, using LIVYNTH's own
validated segmentation instead of rembg's 1.02 GB model download.

rembg's bria-rmbg-2.0.onnx download timed out twice on this network. TripoSR's
`run.py --no-remove-bg` path expects an already-composited RGB image, and rembg's own
pipeline composites the subject over 0.5 gray - so we reproduce that with
geo.visual_hull.segment_head (validated: keeps skin+hair, rejects backdrop and shirt).

Usage:
    python tools/prepare_input.py --image <png> --out <png> [--mask-out <png>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mask-out", default=None)
    ap.add_argument("--geo-root", default=None,
                    help="Directory that contains the `geo` package (e.g. the visual-hull worktree)")
    ap.add_argument("--background", type=float, default=0.5)
    ap.add_argument("--crop", default=None,
                    help="head crop in 'top,bottom,left,right' pixels (default: no crop)")
    args = ap.parse_args()

    if args.geo_root:
        sys.path.insert(0, str(Path(args.geo_root).resolve()))
    from geo.visual_hull import segment_head  # noqa: E402

    rgb = np.asarray(Image.open(args.image).convert("RGB"), dtype=np.float32)
    mask, stats = segment_head(rgb)
    if args.crop:
        top, bottom, left, right = (int(v) for v in args.crop.split(","))
        rgb = rgb[top:bottom, left:right]
        mask = mask[top:bottom, left:right]
    alpha = mask.astype(np.float32)
    if args.mask_out:
        Image.fromarray((alpha * 255).astype(np.uint8)).save(args.mask_out)
    out = rgb * alpha[..., None] + (args.background * 255.0) * (1.0 - alpha[..., None])
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(args.out)
    print(f"foreground_px={int(mask.sum())} of {mask.size} ({100.0 * mask.mean():.1f}%)")
    print("segmentation stats:", {k: v for k, v in stats.items() if k in ("fg_pixels", "top_row", "bottom_row")})
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
