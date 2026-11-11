"""Score a candidate render against the reference with the scorecard's PRIMARY gate:
SUPERSEDED BY ADR-C001-004 -- Phase-3 appearance-metric gate.

This tool measures RENDERED APPEARANCE (silhouette IoU, similarity-aligned
landmark error). ADR-C001-004 requires the decisive gate to rest on
geometry-level evidence, because the Phase-3 controls proved these metrics
cannot see identity on a photo-projected candidate: a jitter canary
(sigma = 8 px) scored 0.9036 silhouette IoU and 8.92 px landmark error, and
a wrong-identity canary (face band widened 1.18x) scored 13.0 px -- both
PASSED the thresholds that were supposed to reject them.

Retained as the evidence trail for that negative result and as the seeding
point for the geometry-level gate. Do NOT cite its output as proof that a
candidate matches Character 001.

image-space landmark error (px) after a similarity-transform alignment.

Inputs
  reference landmarks : MediaPipe JSON produced by geo/detect_landmarks.py
  candidate render    : PNG of the candidate in the reference frame (1086x1448)

Method (docs/C001_GEO03_BLIND_SCORECARD.md 2a)
  - canonical 10-point front set: eye centres, brow peaks, nose tip, mouth corners,
    chin, gonion
  - fit a similarity transform (translation + uniform scale + rotation) on the shared
    points, then measure the residual error per point
  - report mean / median / p95 / max in px and in IPD fractions

Usage:
    python tools/landmark_gate.py --ref <ref.json> --render <png> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# canonical 10-point front set -> how to derive it from the detected point names
GROUPS = {
    "eye_center_r": ("iris_center_r",),
    "eye_center_l": ("iris_center_l",),
    "brow_peak_r": ("brow_mid_r", "brow_outer_r"),
    "brow_peak_l": ("brow_mid_l", "brow_outer_l"),
    "nose_tip": ("nose_tip",),
    "mouth_corner_r": ("mouth_corner_r",),
    "mouth_corner_l": ("mouth_corner_l",),
    "chin": ("chin",),
    "gonion_r": ("jaw_angle_r",),
    "gonion_l": ("jaw_angle_l",),
}


def load_points(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("points", {})
    out = {}
    for canon, candidates in GROUPS.items():
        for c in candidates:
            if c in raw:
                out[canon] = (float(raw[c]["x"]), float(raw[c]["y"]))
                break
    return out


def similarity_fit(src, dst):
    """Least-squares similarity transform (scale, rotation, translation) src -> dst."""
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    s0, d0 = src - mu_s, dst - mu_d
    num = float((s0[:, 0] * d0[:, 0] + s0[:, 1] * d0[:, 1]).sum())
    den = float((s0[:, 0] * d0[:, 1] - s0[:, 1] * d0[:, 0]).sum())
    theta = np.arctan2(den, num)
    a = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    scale = 0.0
    if num or den:
        scale = float(np.sqrt(num * num + den * den) / max((s0 ** 2).sum(), 1e-9))
    t = mu_d - scale * (a @ mu_s)
    return scale, a, t


def apply_tf(pts, scale, a, t):
    p = np.asarray(pts, dtype=np.float64)
    return (scale * (p @ a.T)) + t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--render", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--ipd", type=float, default=212.0)
    args = ap.parse_args()

    ref = load_points(Path(args.ref))
    det = json.loads(Path(args.det_json).read_text(encoding="utf-8")) if hasattr(args, "det_json") else None

    # candidate landmarks: produced by geo/detect_one.py next to the render
    cand_path = Path(args.render)
    cand_json = cand_path.with_suffix(".landmarks.json")
    cand = load_points(cand_json) if cand_json.is_file() else {}

    shared = sorted(set(ref) & set(cand))
    result = {"reference": str(args.ref), "render": str(args.render),
              "ref_points": len(ref), "cand_points": len(cand), "shared": len(shared)}
    if len(shared) < 6:
        result.update(status="BLOCKED", reason=f"only {len(shared)} shared canonical points (need >= 6)")
        print(json.dumps(result, indent=2))
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 2

    src = [cand[k] for k in shared]
    dst = [ref[k] for k in shared]
    scale, a, t = similarity_fit(src, dst)
    warped = apply_tf(src, scale, a, t)
    errs = np.linalg.norm(np.asarray(dst) - warped, axis=1)
    ipd = args.ipd
    result.update(
        status="MEASURED",
        similarity_scale=round(float(scale), 5),
        rotation_deg=round(float(np.degrees(np.arctan2(a[1, 0], a[0, 0]))), 3),
        mean_px=round(float(errs.mean()), 2),
        median_px=round(float(np.median(errs)), 2),
        p95_px=round(float(np.percentile(errs, 95)), 2),
        max_px=round(float(errs.max()), 2),
        mean_ipd=round(float(errs.mean()) / ipd, 4),
        max_ipd=round(float(errs.max()) / ipd, 4),
        per_point={k: round(float(e), 2) for k, e in zip(shared, errs)},
        thresholds={"mean_px_pass": 16, "mean_px_warn": 21, "ipd_pass": 0.075},
        verdict="PASS" if errs.mean() <= 16 else ("WARN" if errs.mean() <= 21 else "FAIL"),
    )
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
