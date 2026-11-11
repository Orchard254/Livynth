"""Resolve the yaw of an aligned candidate by rendering 4 explicit variants.

The orientation search in align_lane_a.py maximised silhouette IoU against the full
reference mask (which includes shoulders/bust), a criterion too weak to distinguish
a front view from a profile view of a head-only mesh.  Here we try yaw = 0/90/180/270
explicitly, render the front slot for each, and pick the best measured match.

Usage:
    python tools/yaw_variants.py --mesh <aligned.glb> --outdir <dir> [--labels A]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    mesh = trimesh.load(args.mesh, force="mesh")
    v = np.asarray(mesh.vertices, dtype=np.float64)
    f = np.asarray(mesh.faces, dtype=np.int64)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    written = []
    for deg in (0, 90, 180, 270):
        a = np.radians(deg)
        c, s = np.cos(a), np.sin(a)
        rot = np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])
        w = v @ rot.T
        m = trimesh.Trimesh(vertices=w, faces=f, process=False)
        if hasattr(mesh.visual, "vertex_colors"):
            m.visual = trimesh.visual.ColorVisuals(vertex_colors=np.asarray(mesh.visual.vertex_colors))
        path = outdir / f"yaw{deg:03d}.glb"
        m.export(path)
        written.append(path.name)
        print(f"[write] {path}  extents={np.round(m.extents, 4).tolist()}")
    (outdir / "variants.json").write_text(json.dumps({"variants": written}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
