"""Pick the yaw sign per view by silhouette IoU (probe renders vs references).

Run from the visual-hull worktree root:
    python tools/pick_render_signs.py --report <report.json> --renders <dir> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo.visual_hull import VIEWS, segment_head  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--renders", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--images", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    calib = report["view_calibration"]
    images_dir = Path(args.images)
    renders_dir = Path(args.renders)

    ref_masks = {}
    for name, vdef in VIEWS.items():
        fname = vdef["file"]
        if name not in calib:
            continue
        rgb = np.asarray(Image.open(images_dir / fname).convert("RGB"), dtype=np.float32)
        mask, _ = segment_head(rgb)
        ref_masks[name] = mask

    decisions = {}
    for name in calib:
        best = None
        for tag in ("p", "n"):
            probe = renders_dir / f"probe_{name}_{tag}.png"
            if not probe.is_file():
                continue
            rgb = np.asarray(Image.open(probe).convert("RGB"), dtype=np.float32)
            mask, _ = segment_head(rgb)
            ref = ref_masks[name]
            if ref.shape != mask.shape:
                continue
            inter = int((ref & mask).sum())
            union = int((ref | mask).sum())
            iou = inter / union if union else 0.0
            if best is None or iou > best["iou"]:
                best = {"sign": "+" if tag == "p" else "-", "iou": round(float(iou), 4)}
        if best:
            decisions[name] = best
            print(f"{name:9s} best_sign={best['sign']} iou={best['iou']:.4f}")

    Path(args.out).write_text(json.dumps(decisions, indent=2) + "\n", encoding="utf-8")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

