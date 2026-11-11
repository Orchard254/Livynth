"""Score a TripoSR input variant end-to-end: align -> yaw sweep -> render -> landmarks.

For each variant:
  1. align the mesh into the reference frame (silhouette-IoU fit)
  2. render the four yaw variants (front slot only)
  3. pick the yaw with the best head-crop IoU against the front reference
  4. detect landmarks on the winning render with the same detector as the references
  5. report the scorecard's primary metric: landmark mean error in px (and the
     silhouette IoU) so variants are directly comparable

Usage:
    python tools/score_variant.py --variant <name> --mesh <mesh.glb> --bundle <dir> \
        --hull <visual-hull worktree> --landmarks <landmarks worktree> --out <json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--hull", required=True)
    ap.add_argument("--landmarks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--images", default=r"C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1")
    args = ap.parse_args()

    hull = Path(args.hull)
    lmw = Path(args.landmarks)
    bundle = Path(args.bundle)
    work = bundle / "variants" / args.variant
    work.mkdir(parents=True, exist_ok=True)

    report = hull / "output" / "character001_visual_hull_v8" / "visual_hull_report.json"
    here = Path(__file__).resolve().parent

    # 1. align
    aligned = work / "mesh_aligned.glb"
    subprocess.run([sys.executable, str(here / "align_lane_a.py"),
                    "--mesh", args.mesh, "--report", str(report), "--images", args.images,
                    "--out", str(aligned), "--json", str(work / "alignment.json")], check=False,
                   capture_output=True)
    if not aligned.is_file():
        print("alignment failed")
        return 1

    # 2. yaw variants + render
    yawdir = work / "yaw"
    subprocess.run([sys.executable, str(here / "yaw_variants.py"),
                    "--mesh", str(aligned), "--outdir", str(yawdir)], check=False, capture_output=True)
    for glb in sorted(yawdir.glob("yaw*.glb")):
        subprocess.run([BLENDER, "--background", "--python", str(hull / "tools" / "render_hull_calibrated.py"),
                        "--", "--glb", str(glb), "--report", str(report),
                        "--out", str(yawdir / f"render_{glb.stem[-3:]}"), "--views", "front"],
                       check=False, capture_output=True)

    # 3. score each yaw render
    sys.path.insert(0, str(hull))
    from geo.visual_hull import segment_head  # noqa: E402
    rep = json.loads(report.read_text(encoding="utf-8"))
    prov = rep["provenance"]["front"]
    ref = np.asarray(Image.open(Path(args.images) / prov["file"]).convert("RGB"), dtype=np.float32)
    rm, _ = segment_head(ref)
    crown, chin = prov["crown_row_annotated"], prov["chin_row_annotated"]
    band = slice(crown, chin)

    results = []
    for d in sorted(yawdir.glob("render_*")):
        for png in sorted(d.glob("probe_front*.png")):
            ren = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32)
            mm, _ = segment_head(ren)
            h = min(rm.shape[0], mm.shape[0]); w = min(rm.shape[1], mm.shape[1])
            a, b = rm[:h, :w], mm[:h, :w]
            full = float((a & b).sum() / max((a | b).sum(), 1))
            ab, bb = a[band], b[band]
            head = float((ab & bb).sum() / max((ab | bb).sum(), 1))
            results.append({"render": str(png), "iou_full": round(full, 4), "iou_head": round(head, 4)})
    results.sort(key=lambda r: -r["iou_head"])
    print(json.dumps(results, indent=2))
    if not results:
        print("no renders")
        return 1
    best = results[0]

    # 4. landmarks on the winning render
    venv_py = lmw / ".venv-landmarks" / "Scripts" / "python.exe"
    lm_out = Path(best["render"]).with_suffix(".landmarks.json")
    subprocess.run([str(venv_py), "-m", "geo.detect_one", "--image", best["render"],
                    "--out", str(lm_out)], cwd=str(lmw), check=False, capture_output=True)

    # 5. scorecard primary metric
    gate_out = work / "landmark_gate.json"
    subprocess.run([sys.executable, str(hull / "tools" / "landmark_gate.py"),
                    "--ref", str(lmw / "output" / "landmarks_tasks" / "front.json"),
                    "--render", best["render"], "--out", str(gate_out)], check=False, capture_output=True)
    gate = json.loads(gate_out.read_text(encoding="utf-8")) if gate_out.is_file() else {}

    summary = {
        "variant": args.variant,
        "mesh": args.mesh,
        "best_render": best["render"],
        "iou_full": best["iou_full"],
        "iou_head": best["iou_head"],
        "landmark_mean_px": gate.get("mean_px"),
        "landmark_max_px": gate.get("max_px"),
        "landmark_verdict": gate.get("verdict"),
        "all_renders": results,
    }
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
