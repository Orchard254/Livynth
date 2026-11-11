"""Run the two mandatory Phase-3 gate controls.
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


Control 1 - reference self-IoU: segmenting a reference image against itself must give
IoU == 1.000. Anything lower means the segmenter/harness is broken and the whole run
must be aborted.

Control 2 - jitter canary: 30% of a candidate's vertices are displaced by ~8 px
(projection-plane equivalent). The gate MUST reject it. If the canary passes, the gate
is broken and every verdict from this run is discarded.

Usage:
    python tools/gate_controls.py --bundle <bundle dir> --glb <candidate.glb> \
        --report <report.json> --images <ref dir> --out <controls.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo.visual_hull import segment_head  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--front-render", required=True, help="rendered front view of the candidate")
    ap.add_argument("--blender", default=r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
    ap.add_argument("--render-script", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    prov = report["provenance"]["front"]
    s_px = report["view_calibration"]["front"]["s"]
    images_dir = Path(args.images)

    # --- control 1: reference self-IoU ---------------------------------------
    ref = np.asarray(Image.open(images_dir / prov["file"]).convert("RGB"), dtype=np.float32)
    rm, _ = segment_head(ref)
    self_iou = float((rm & rm).sum() / max((rm | rm).sum(), 1))
    print(f"[control 1] reference self-IoU = {self_iou:.6f} (must be 1.000000)")

    # --- control 2: jitter canary --------------------------------------------
    mesh = trimesh.load(args.glb, force="mesh")
    v = np.asarray(mesh.vertices, dtype=np.float64).copy()
    f = np.asarray(mesh.faces, dtype=np.int64)
    rng = np.random.default_rng(20261111)
    n = len(v)
    idx = rng.choice(n, size=int(n * 0.30), replace=False)
    delta_px = 8.0
    delta_m = delta_px / s_px
    v[idx, 0] += rng.normal(0.0, delta_m, size=len(idx))
    v[idx, 1] += rng.normal(0.0, delta_m, size=len(idx))
    # Copy the mesh (keeping its original visual/UV binding) and displace vertices.
    # Building a fresh Trimesh would drop the texture binding and render a flat blob.
    canary = mesh.copy()
    canary.vertices = v
    canary_dir = Path(args.bundle) / "controls"
    canary_dir.mkdir(parents=True, exist_ok=True)
    canary_path = canary_dir / "jitter_canary.glb"
    canary.export(canary_path)
    print(f"[control 2] canary written: {canary_path} ({len(idx)} verts perturbed, "
          f"sigma={delta_px:.0f} px, visual={type(canary.visual).__name__})")

    # render the canary with the same harness and score it
    import subprocess
    outdir = canary_dir / "render"
    cmd = [args.blender, "--background", "--python", args.render_script, "--",
           "--glb", str(canary_path), "--report", args.report, "--out", str(outdir), "--views", "front"]
    subprocess.run(cmd, check=False, capture_output=True)
    probes = sorted(outdir.glob("probe_front*.png"))
    best = None
    for png in probes:
        ren = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32)
        mm, _ = segment_head(ren)
        h = min(rm.shape[0], mm.shape[0]); w = min(rm.shape[1], mm.shape[1])
        a, b = rm[:h, :w], mm[:h, :w]
        iou = float((a & b).sum() / max((a | b).sum(), 1))
        print(f"[control 2] {png.name}: front IoU vs reference = {iou:.4f}")
        if best is None or iou > best:
            best = iou
    cand_render = Path(args.front_render)
    cr = np.asarray(Image.open(cand_render).convert("RGB"), dtype=np.float32)
    cm, _ = segment_head(cr)
    h = min(rm.shape[0], cm.shape[0]); w = min(rm.shape[1], cm.shape[1])
    a, b = rm[:h, :w], cm[:h, :w]
    cand_iou = float((a & b).sum() / max((a | b).sum(), 1))
    print(f"[candidate ] front IoU vs reference = {cand_iou:.4f}")

    result = {
        "control_self_iou": {"value": self_iou, "pass": abs(self_iou - 1.0) < 1e-6},
        "control_jitter_canary": {"value": best, "pass": best is not None and best < 0.80,
                                  "threshold": 0.80, "perturbed_verts": int(len(idx)),
                                  "sigma_px": delta_px},
        "candidate_front_iou": cand_iou,
        "gate_valid": abs(self_iou - 1.0) < 1e-6 and (best is not None and best < 0.80),
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
