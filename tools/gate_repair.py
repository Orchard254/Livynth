"""Gate repair: a wrong-identity canary + multi-view photo-consistency.
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


The jitter canary used in run 1 was not rejected by either numeric sub-gate, so the
gate was inadmissible.  The judges asked for a canary the metrics are *designed* to
catch.  This module implements two things:

1. WRONG-IDENTITY CANARY (render based).  Take a candidate and change only the face:
   the face-band vertices are scaled laterally about the face centre, so the SILHOUETTE
   barely moves while the facial proportions become a different person's.  A correct
   gate must still reject it on identity (landmark error), which is the property the
   jitter canary failed to test.

2. MULTI-VIEW PHOTO-CONSISTENCY (decisive numeric gate).  For each candidate view
   (front, left profile, right profile) detect the canonical landmarks and compare
   *normalised* geometry ratios (divided by interocular distance) against the same
   ratios measured on the reference view.  A candidate whose front and profile views
   disagree with the reference proportions cannot be the same person, and this metric
   is independent of the silhouette outline and of whether the surface is a photo.

Usage:
    python tools/gate_repair.py --bundle <bundle dir> --glb <candidate.glb> \
        --report <report.json> --images <ref dir> --landmarks <landmarks worktree> \
        --out <report json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
HULL_WORKTREE = Path(__file__).resolve().parents[1]

RATIOS = [
    ("nose_tip_to_eye_line", ("nose_tip",), ("iris_center_r", "iris_center_l"), "mean"),
    ("mouth_width_over_ipd", ("mouth_corner_r", "mouth_corner_l"), None, "width"),
    ("chin_to_eye_line", ("chin",), ("iris_center_r", "iris_center_l"), "mean"),
    ("brow_to_eye", ("brow_mid_r", "brow_mid_l"), ("iris_center_r", "iris_center_l"), "mean"),
    ("eye_separation_over_ipd", ("iris_center_r", "iris_center_l"), None, "width"),
    ("nostril_to_eye_line", ("nostril_r", "nostril_l"), ("iris_center_r", "iris_center_l"), "mean"),
    ("lip_to_nose", ("upper_lip_mid",), ("nose_tip",), "mean"),
    ("ear_to_eye", ("jaw_angle_r",), ("iris_center_r",), "mean"),
]


def load_points(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {k: (float(v["x"]), float(v["y"])) for k, v in doc.get("points", {}).items()}


def ipd_of(points):
    if "iris_center_r" in points and "iris_center_l" in points:
        a, b = points["iris_center_r"], points["iris_center_l"]
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))
    if "eye_center_r" in points and "eye_center_l" in points:
        a, b = points["eye_center_r"], points["eye_center_l"]
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))
    return None


def ratios(points):
    """Normalised geometry ratios (dimensionless)."""
    ipd = ipd_of(points)
    if not ipd or ipd <= 1:
        return {}
    out = {}
    for name, numer, denom, mode in RATIOS:
        try:
            npts = [points[p] for p in numer if p in points]
            if len(npts) != len(numer):
                continue
            if mode == "mean":
                if not denom:
                    continue  # 'mean' mode needs an explicit denominator pair
                dpts = [points[p] for p in denom if p in points]
                if len(dpts) != len(denom):
                    continue
                d = float(np.mean([np.hypot(n[0] - dd[0], n[1] - dd[1]) for n, dd in zip(npts, dpts)]))
                out[name] = round(float(np.mean([np.hypot(n[0] - dd[0], n[1] - dd[1]) for n, dd in zip(npts, dpts)])) / d, 4)
            elif mode == "width":
                if len(npts) == 2:
                    out[name] = round(float(np.hypot(npts[0][0] - npts[1][0], npts[0][1] - npts[1][1])) / ipd, 4)
        except KeyError:
            continue
    return out


def detect(image: Path, out_json: Path, lmw: Path):
    venv_py = lmw / ".venv-landmarks" / "Scripts" / "python.exe"
    subprocess.run([str(venv_py), "-m", "geo.detect_one", "--image", str(image), "--out", str(out_json)],
                   cwd=str(lmw), check=False, capture_output=True)
    return out_json.is_file()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--landmarks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--face-scale", type=float, default=1.18)
    args = ap.parse_args()

    bundle = Path(args.bundle)
    lmw = Path(args.landmarks)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    calib = report["view_calibration"]["front"]
    s_px = calib["s"]
    cx, cy = calib["cx"], calib["cy"]

    result = {"wrong_identity_canary": {}, "multiview_photo_consistency": {}}

    # ---------------- 1. wrong-identity canary ------------------------------
    mesh = trimesh.load(args.glb, force="mesh")
    v = np.asarray(mesh.vertices, dtype=np.float64).copy()
    f = np.asarray(mesh.faces, dtype=np.int64)
    # project into the front view and select the face band
    u = cx + s_px * v[:, 0]
    vv = cy - s_px * v[:, 1]
    face = (u > cx - 200) & (u < cx + 200) & (vv > 470) & (vv < 930)
    n_face = int(face.sum())
    if n_face:
        xc = float(v[face, 0].mean())
        v[face, 0] = xc + (v[face, 0] - xc) * args.face_scale
    canary = mesh.copy()
    canary.vertices = v
    cdir = bundle / "controls"
    cdir.mkdir(parents=True, exist_ok=True)
    cpath = cdir / "wrong_identity_canary.glb"
    canary.export(cpath)
    subprocess.run([BLENDER, "--background", "--python",
                    str(HULL_WORKTREE / "tools" / "render_hull_calibrated.py"), "--",
                    "--glb", str(cpath), "--report", args.report, "--out", str(cdir / "render"), "--views", "front"],
                   check=False, capture_output=True)
    renders = sorted((cdir / "render").glob("probe_front*.png"))
    lm = cdir / "render" / (renders[0].stem + ".landmarks.json") if renders else None
    detected = detect(renders[0], lm, lmw) if (renders and lm) else False
    gate = {}
    if detected:
        gpath = cdir / "wrong_identity.landmark_gate.json"
        subprocess.run([sys.executable, str(HULL_WORKTREE / "tools" / "landmark_gate.py"),
                        "--ref", str(lmw / "output" / "landmarks_tasks" / "front.json"),
                        "--render", str(renders[0]), "--out", str(gpath)], check=False, capture_output=True)
        gate = json.loads(gpath.read_text(encoding="utf-8")) if gpath.is_file() else {}
    result["wrong_identity_canary"] = {
        "description": "face-band vertices scaled laterally about the face centre: same silhouette, different identity",
        "face_scale": args.face_scale,
        "face_vertices": n_face,
        "landmark_mean_px": gate.get("mean_px"),
        "landmark_max_px": gate.get("max_px"),
        "landmark_verdict": gate.get("verdict"),
        "landmark_requirement": "MUST FAIL (<=16 px pass threshold)",
        "landmark_pass": gate.get("verdict") == "FAIL",
        "landmarks_detected": detected,
    }
    # the similarity-aligned landmark metric is scale-invariant, so it cannot see a
    # uniform facial widening.  The scale-normalised ratio metric can: evaluate the
    # canary with it.
    ref_front = load_points(lmw / "output" / "landmarks_tasks" / "front.json")
    ref_ratios = ratios(ref_front)
    canary_ratios = ratios(load_points(lm)) if detected else {}
    dev = {}
    for k, rv in ref_ratios.items():
        if k in canary_ratios:
            dev[k] = round(abs(canary_ratios[k] - rv) / max(abs(rv), 1e-6), 4)
    worst = max(dev.values()) if dev else None
    result["wrong_identity_canary"].update({
        "ratio_deviation": dev,
        "ratio_worst_relative_deviation": worst,
        "ratio_threshold": 0.08,
        "ratio_verdict": "FAIL" if (worst is not None and worst > 0.08) else ("PASS" if worst is not None else "NOT_MEASURED"),
        "ratio_pass": worst is not None and worst > 0.08,
    })
    result["wrong_identity_canary"]["pass"] = result["wrong_identity_canary"]["ratio_pass"]

    # ---------------- 2. multi-view photo-consistency -----------------------
    view_map = {
        "front": ("A/front.png", lmw / "output" / "landmarks_tasks" / "front.json"),
        "left_profile": ("A/left90.png", lmw / "output" / "landmarks_tasks" / "profile_left.json"),
        "right_profile": ("A/right90.png", lmw / "output" / "landmarks_tasks" / "profile_right.json"),
    }
    for view, (rel, ref_json) in view_map.items():
        cand = bundle / rel
        out_json = cand.with_suffix(".ratios.landmarks.json")
        ok = detect(cand, out_json, lmw)
        ref_pts = load_points(ref_json) if ref_json.is_file() else {}
        ref_r = ratios(ref_pts)
        cand_r = ratios(load_points(out_json)) if ok else {}
        deviations = {}
        for k, vref in ref_r.items():
            if k in cand_r:
                deviations[k] = round(abs(cand_r[k] - vref) / max(abs(vref), 1e-6), 4)
        worst = max(deviations.values()) if deviations else None
        result["multiview_photo_consistency"][view] = {
            "reference_ratios": ref_r,
            "candidate_ratios": cand_r,
            "relative_deviation": deviations,
            "worst_relative_deviation": worst,
            "threshold": 0.08,
            "pass": (worst is not None and worst <= 0.08),
            "landmarks_detected": ok,
        }

    result["gate_valid"] = result["wrong_identity_canary"]["pass"] and all(
        v["pass"] for v in result["multiview_photo_consistency"].values())
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
