"""Head-region silhouette IoU between calibrated hull renders and references.

The reference photographs include shoulders/torso; the carved hull is head+hair+neck
only. A whole-frame IoU therefore punishes the candidate for missing the bust.
This crops BOTH masks to the annotated crown..chin band (head region) before
comparing, and reports both numbers (full frame and head crop).

Run from the visual-hull worktree root:
    python tools/head_iou.py --report <report.json> --renders <dir> --signs <signs.json> --out <json>
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
    ap.add_argument("--signs", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    calib = report["view_calibration"]
    prov = report.get("provenance", {})
    signs = json.loads(Path(args.signs).read_text(encoding="utf-8"))
    images_dir = Path(args.images)
    renders_dir = Path(args.renders)

    out = {"method": "head-region crop (crown..chin) + full-frame IoU, same segmentation rule for both",
           "views": {}}
    for name, c in calib.items():
        if name not in signs:
            continue
        fname = VIEWS[name]["file"]
        ref_rgb = np.asarray(Image.open(images_dir / fname).convert("RGB"), dtype=np.float32)
        ref_mask, _ = segment_head(ref_rgb)
        tag = "p" if signs[name]["sign"] == "+" else "n"
        probe = renders_dir / f"probe_{name}_{tag}.png"
        ren_rgb = np.asarray(Image.open(probe).convert("RGB"), dtype=np.float32)
        ren_mask, _ = segment_head(ren_rgb)

        h = min(ref_mask.shape[0], ren_mask.shape[0])
        w = min(ref_mask.shape[1], ren_mask.shape[1])
        ref_mask = ref_mask[:h, :w]
        ren_mask = ren_mask[:h, :w]

        def iou(a, b):
            u = int((a | b).sum())
            return round(float((a & b).sum() / u), 4) if u else 0.0

        full = iou(ref_mask, ren_mask)

        crown = (prov.get(name) or {}).get("crown_row_annotated")
        chin = (prov.get(name) or {}).get("chin_row_annotated")
        head_iou = None
        if crown is not None and chin is not None and 0 <= crown < chin <= h:
            band = slice(crown, chin)
            head_iou = iou(ref_mask[band], ren_mask[band])

        out["views"][name] = {"yaw_sign": signs[name]["sign"], "iou_full_frame": full,
                              "iou_head_crop": head_iou,
                              "crown_row": crown, "chin_row": chin}
        print(f"{name:9s} sign={signs[name]['sign']} iou_full={full:.4f} iou_head_crop={head_iou}")

    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
