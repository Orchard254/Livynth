"""Calibrate the Blender render camera against the carve's own projection.

The carve projects the mesh with geo.visual_hull.project_points (orthographic,
u = cx + s*(cos psi*x + sin psi*z), v = cy - s*y). This script projects the mesh
with that model (ground truth) and compares the resulting bounding box with the
bounding box of the mesh as rendered by Blender, then reports the pixel delta and
the shift/scale correction needed to make the render reproduce the projection.

Run from the visual-hull worktree root:
    python tools/camera_probe.py --glb <path> --report <report.json> --renders <dir> --signs <signs.json>
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
from geo.visual_hull import project_points, segment_head  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--renders", required=True)
    ap.add_argument("--signs", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    calib = report["view_calibration"]
    signs = json.loads(Path(args.signs).read_text(encoding="utf-8"))
    mesh = trimesh.load(args.glb, force="mesh")
    verts = np.asarray(mesh.vertices)
    renders = Path(args.renders)

    out = {"views": {}}
    for name, c in calib.items():
        if name not in signs or c.get("top"):
            continue
        tag = "p" if signs[name]["sign"] == "+" else "n"
        probe = renders / f"probe_{name}_{tag}.png"
        if not probe.is_file():
            continue
        u, v = project_points(verts, c)
        pu0, pu1 = float(u.min()), float(u.max())
        pv0, pv1 = float(v.min()), float(v.max())
        rgb = np.asarray(Image.open(probe).convert("RGB"), dtype=np.float32)
        mask, _ = segment_head(rgb)
        ys, xs = np.nonzero(mask)
        if len(xs) == 0:
            print(f"{name}: render mask empty")
            continue
        ru0, ru1 = float(xs.min()), float(xs.max())
        rv0, rv1 = float(ys.min()), float(ys.max())
        out["views"][name] = {
            "projected_u": [round(pu0, 1), round(pu1, 1)],
            "projected_v": [round(pv0, 1), round(pv1, 1)],
            "rendered_u": [ru0, ru1],
            "rendered_v": [rv0, rv1],
            "d_center_u": round((pu0 + pu1) / 2 - (ru0 + ru1) / 2, 1),
            "d_center_v": round((pv0 + pv1) / 2 - (rv0 + rv1) / 2, 1),
            "height_ratio_proj_over_render": round((pv1 - pv0) / max(rv1 - rv0, 1), 3),
        }
        print(f"{name:9s} proj_u[{pu0:7.1f},{pu1:7.1f}] v[{pv0:7.1f},{pv1:7.1f}] | "
              f"render_u[{ru0:6.0f},{ru1:6.0f}] v[{rv0:6.0f},{rv1:6.0f}] | "
              f"dU={out['views'][name]['d_center_u']:7.1f} dV={out['views'][name]['d_center_v']:7.1f} "
              f"h_ratio={out['views'][name]['height_ratio_proj_over_render']}")

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
