#!/usr/bin/env python3
"""Inspect the native MPFB pre-morph neutral archive; write an offline vertex atlas.

No identity targets are inferred. This tool never changes the NPZ, an MPFB mesh,
or a fitted constraint file. Requires NumPy; does not require Blender or a GPU.

    python tools/stage1_mesh_inspect.py output/c001_geo05/neutral_mesh.npz \
        --out output/c001_geo05/neutral_inspection \
        --expect-sha 64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

SCHEMA = "livynth.c001.stage1.neutral-mesh.v1"
ATLAS_SCHEMA = "livynth.c001.stage1.inspection.v1"


class InvalidNeutralMesh(ValueError):
    """Untrusted or inconsistent neutral-mesh archive; do not use for anchors."""


def _xyz_hash(points):
    return hashlib.sha256(np.ascontiguousarray(points, dtype="<f8").tobytes()).hexdigest()


def load_and_validate(path, *, expected_sha=None):
    """Load bounded NPZ with pickle disabled; reject inconsistent hashes/topology."""
    with np.load(path, allow_pickle=False) as package:
        if set(package.files) != {"vertices", "quads", "metadata_utf8"}:
            raise InvalidNeutralMesh("E_ARCHIVE_FIELDS")
        points = np.asarray(package["vertices"])
        faces = np.asarray(package["quads"])
        metadata_bytes = np.asarray(package["metadata_utf8"])
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 4 or len(points) > 1000000:
        raise InvalidNeutralMesh("E_VERTICES_SHAPE")
    if points.dtype.kind not in "f" or not np.isfinite(points).all():
        raise InvalidNeutralMesh("E_VERTICES_NONFINITE_OR_DTYPE")
    if faces.ndim != 2 or faces.shape[1] != 4 or not len(faces) or len(faces) > 2000000:
        raise InvalidNeutralMesh("E_QUADS_SHAPE")
    if faces.dtype.kind not in "iu":
        raise InvalidNeutralMesh("E_QUADS_DTYPE")
    if np.any(faces >= len(points)) or np.any(faces < 0):
        raise InvalidNeutralMesh("E_QUADS_OUT_OF_RANGE")
    sorted_faces = np.sort(faces, axis=1)
    if np.any(sorted_faces[:, 1:] == sorted_faces[:, :-1]):
        raise InvalidNeutralMesh("E_DEGENERATE_QUAD_INDEX")
    if metadata_bytes.dtype != np.dtype("uint8") or metadata_bytes.ndim != 1:
        raise InvalidNeutralMesh("E_METADATA_BYTES")
    try:
        meta = json.loads(metadata_bytes.tobytes().decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidNeutralMesh("E_METADATA_JSON") from exc
    actual_hash = _xyz_hash(points)
    if (not isinstance(meta, dict) or meta.get("schema") != SCHEMA or
        meta.get("stage1") != "NOT_RUN" or
        meta.get("source") != "MPFB_BAKED_NEUTRAL_BEFORE_FACE_TARGETS"):
        raise InvalidNeutralMesh("E_METADATA_SOURCE_STATUS")
    if (meta.get("vertex_count") != len(points) or
        meta.get("quad_face_count") != len(faces) or
        meta.get("positions_sha256") != actual_hash):
        raise InvalidNeutralMesh("E_METADATA_MISMATCH")
    if expected_sha is not None and actual_hash != expected_sha.lower():
        raise InvalidNeutralMesh("E_EXPECTED_SHA_MISMATCH")
    bounds_min, bounds_max = points.min(axis=0), points.max(axis=0)
    for field, observed in (("bounds_min", bounds_min), ("bounds_max", bounds_max)):
        reference = np.asarray(meta.get(field, []))
        if reference.shape != (3,) or reference.dtype.kind not in "fi" or not np.allclose(
                reference, observed, atol=1e-10, rtol=0):
            raise InvalidNeutralMesh("E_BOUNDS_MISMATCH")
    return np.asarray(points, dtype=np.float64), np.asarray(faces, dtype=np.int64), meta


def topology_stats(vertices, faces):
    """Count connected components and undirected edge incidence; not collisions."""
    parents = np.arange(len(vertices))
    ranks = np.zeros(len(vertices), dtype=np.uint8)

    def find(i):
        i = int(i)
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = int(parents[i])
        return i

    def union(a, b):
        a, b = find(a), find(b)
        if a == b:
            return
        if ranks[a] < ranks[b]:
            a, b = b, a
        parents[b] = a
        if ranks[a] == ranks[b]:
            ranks[a] += 1

    edges = Counter()
    for face in faces:
        for start, end in zip(face, np.roll(face, -1)):
            a, b = sorted((int(start), int(end)))
            edges[(a, b)] += 1
            union(a, b)
    used = set(int(v) for v in faces.flat)
    components = len({find(i) for i in used})
    return {
        "connected_face_components": components,
        "isolated_vertices": len(vertices) - len(used),
        "boundary_edges": sum(n == 1 for n in edges.values()),
        "nonmanifold_edges": sum(n > 2 for n in edges.values()),
        "unique_edges": len(edges),
        "global_self_intersection": "UNVERIFIED",
    }


def inspect(points, quads, meta, *, head_height_m=0.35):
    """Find a diagnostic upper-Z crop. This is NOT a face-region annotation."""
    if not np.isfinite(head_height_m) or not .1 <= head_height_m <= .7:
        raise InvalidNeutralMesh("E_CROP_HEIGHT")
    top = float(points[:, 2].max())
    zmin = top - head_height_m
    selected = np.flatnonzero(points[:, 2] >= zmin)
    in_crop = np.all(points[quads, 2] >= zmin, axis=1)
    face_indices = np.flatnonzero(in_crop)
    return {
        "schema": ATLAS_SCHEMA,
        "input_positions_sha256": meta["positions_sha256"],
        "stage1": "NOT_RUN",
        "vertex_count": len(points),
        "quad_face_count": len(quads),
        "bounds_min": points.min(axis=0).tolist(),
        "bounds_max": points.max(axis=0).tolist(),
        "topology": topology_stats(points, quads),
        "diagnostic_upper_z_crop": {
            "zmin_m": zmin,
            "zmax_m": top,
            "vertices": len(selected),
            "fully_contained_quads": len(face_indices),
            "semantic_anatomy": "NOT_INFERRED",
        },
        "identity_likeness": "UNVERIFIED",
        "notes": (
            "Local-coordinate crop by height only. Atlas labels +Y/-Y/+X/-X "
            "are camera directions, not proven anatomical front/back. "
            "Clicking vertices collects inspection candidates, NOT valid 3D fit anchors."
        ),
    }, selected, face_indices


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LIVYNTH neutral mesh inspector</title>
<style>
:root{font-family:system-ui,Segoe UI,Arial,sans-serif;color-scheme:dark}
body{background:#101721;color:#e7ebf1;margin:24px;max-width:1420px}
header{margin-bottom:16px}h1{font-size:1.35rem;margin:0 0 8px}.muted{color:#abb9cc}
.views{display:grid;grid-template-columns:repeat(2,minmax(300px,1fr));gap:16px}
.panel{background:#1b2735;border:1px solid #43566b;border-radius:10px;padding:12px}
canvas{width:100%;height:auto;aspect-ratio:1;display:block;cursor:crosshair;background:#19222f}
.panel b{display:block;margin-bottom:8px}.columns{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}
textarea{box-sizing:border-box;width:100%;height:132px;background:#111923;color:#aee1d9;font:12px monospace}
button{padding:8px 14px;border:1px solid #7b9bb5;background:#28475e;color:#fff;border-radius:6px;cursor:pointer}
code{color:#b7d1ee}
@media(max-width:760px){.views{grid-template-columns:1fr}}
</style></head><body>
<header><h1>LIVYNTH — indexed neutral-mesh explorer</h1>
<div class="muted">Geometry-only diagnostic. No camera calibration, identity-fit targets, or likeness claims.</div>
<p><code id="meta"></code></p>
</header>
<div class="views">
<div class="panel"><b>Camera +Y (looking toward −Y)</b><canvas width="600" height="600" data-view="py"></canvas></div>
<div class="panel"><b>Camera −Y (looking toward +Y)</b><canvas width="600" height="600" data-view="ny"></canvas></div>
<div class="panel"><b>Camera +X (looking toward −X)</b><canvas width="600" height="600" data-view="px"></canvas></div>
<div class="panel"><b>Camera −X (looking toward +X)</b><canvas width="600" height="600" data-view="nx"></canvas></div>
</div>
<div class="columns"><div><b>Selected native vertex:</b> <code id="last">click a point</code></div>
<div><button id="reset">Clear selection</button></div></div>
<p class="muted">Click a visible surface point for nearby vertex index and mesh-local coordinates. The selection is a *candidate list* only; validate anatomical labels and 3D targets separately.</p>
<textarea readonly id="selected">[]</textarea>
<script>
const DATA = __DATA__;
const points=DATA.vertices, faces=DATA.quads, ids=DATA.indices;
const panelConfigs={py:{h:p=>-p[0],d:p=>p[1]},ny:{h:p=>p[0],d:p=>-p[1]},
 px:{h:p=>p[1],d:p=>p[0]},nx:{h:p=>-p[1],d:p=>-p[0]}};
const chosen=[];
document.querySelector('#meta').textContent='SHA '+DATA.hash+' · '+DATA.total_vertices+' original vertices · crop z ≥ '+DATA.zmin.toFixed(4)+' m';
function projectCanvas(canvas){
 const cfg=panelConfigs[canvas.dataset.view], W=canvas.width,H=canvas.height;
 const horizontals=points.map(cfg.h),vert=points.map(p=>p[2]);
 const xmin=Math.min(...horizontals),xmax=Math.max(...horizontals),ymin=Math.min(...vert),ymax=Math.max(...vert);
 const span=Math.max(xmax-xmin,ymax-ymin,0.001)*1.15;
 const xm=(xmin+xmax)/2,ym=(ymin+ymax)/2;
 const screen=points.map((p,i)=>({x:W/2+(horizontals[i]-xm)*W/span,
    y:H/2-(p[2]-ym)*H/span,depth:cfg.d(p),id:ids[i],coords:p}));
 return {screen,W,H};
}
function draw(canvas){
 const cfg=panelConfigs[canvas.dataset.view], ctx=canvas.getContext('2d');
 const {screen,W,H}=projectCanvas(canvas);
 ctx.clearRect(0,0,W,H);
 const order=faces.map((f,i)=>({f,i,depth:f.reduce((sum,j)=>sum+screen[j].depth,0)/4}));
 order.sort((a,b)=>a.depth-b.depth);
 for(const item of order){
  const f=item.f, p0=points[f[0]],p1=points[f[1]],p2=points[f[2]];
  const ab=p1.map((v,i)=>v-p0[i]),ac=p2.map((v,i)=>v-p0[i]);
  const normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];
  const norm=Math.hypot(...normal)||1;
  const lit=Math.abs((normal[0]*.25+normal[1]*.4+normal[2]*.88)/norm);
  const shade=Math.round(78+Math.min(1,lit)*94);
  ctx.beginPath();f.forEach((k,i)=>{i===0?ctx.moveTo(screen[k].x,screen[k].y):ctx.lineTo(screen[k].x,screen[k].y)});ctx.closePath();
  ctx.fillStyle='rgb('+shade+','+(shade+8)+','+(shade+14)+')';ctx.fill();
  ctx.strokeStyle='rgba(14,23,35,.28)';ctx.lineWidth=.55;ctx.stroke();
 }
 for(const idx of chosen){const j=ids.indexOf(idx);if(j<0)continue;const s=screen[j];
  ctx.beginPath();ctx.arc(s.x,s.y,5,0,Math.PI*2);ctx.fillStyle='#ffe08a';ctx.fill();
  ctx.strokeStyle='#000';ctx.lineWidth=2;ctx.stroke();
 }
 return screen;
}
function updateText(){
 const output=chosen.map(id=>{const j=ids.indexOf(id);return {vertex_index:id,source_xyz_m:points[j]}});
 document.querySelector('#selected').value=JSON.stringify(output,null,2);
 document.querySelector('#last').textContent=output.length?JSON.stringify(output[output.length-1]):'click a point';
}
function redraw(){document.querySelectorAll('canvas').forEach(draw)}
document.querySelectorAll('canvas').forEach(canvas=>{
 canvas.addEventListener('click',e=>{
  const rect=canvas.getBoundingClientRect(),x=(e.clientX-rect.left)*canvas.width/rect.width,
        y=(e.clientY-rect.top)*canvas.height/rect.height;
  const screen=draw(canvas);
  const nearby=screen.map(p=>({p,dist:(p.x-x)**2+(p.y-y)**2})).filter(i=>i.dist<100);
  nearby.sort((a,b)=>a.dist-b.dist || b.p.depth-a.p.depth);
  if(!nearby.length)return;
  const closest=nearby[0].p;
  if(!chosen.includes(closest.id))chosen.push(closest.id);
  updateText();redraw();
 });
});
document.querySelector('#reset').addEventListener('click',()=>{chosen.splice(0);updateText();redraw()});
redraw();
</script></body></html>'''


def write_outputs(npz_path, output_prefix, *, expected_sha=None, head_height_m=0.35):
    points, faces, meta = load_and_validate(npz_path, expected_sha=expected_sha)
    report, picked, face_ids = inspect(points, faces, meta, head_height_m=head_height_m)
    index_lookup = {int(global_id): i for i, global_id in enumerate(picked)}
    local_quads = [[index_lookup[int(j)] for j in faces[int(fi)]] for fi in face_ids]
    data = {
        "hash": report["input_positions_sha256"],
        "total_vertices": len(points),
        "zmin": report["diagnostic_upper_z_crop"]["zmin_m"],
        "indices": picked.tolist(),
        "vertices": points[picked].round(9).tolist(),
        "quads": local_quads,
    }
    out = Path(output_prefix)
    out.parent.mkdir(parents=True, exist_ok=True)
    report_path = out.with_suffix(".json")
    html_path = out.with_suffix(".html")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(HTML.replace("__DATA__", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
    return report_path, html_path, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Original stage1-neutral-dump .npz")
    parser.add_argument("--out", type=Path, required=True, help="Output prefix, e.g. output/c001_geo05/neutral_inspection")
    parser.add_argument("--expect-sha", help="Exact expected Stage-1 source fingerprint")
    parser.add_argument("--head-height-m", type=float, default=.35, help="Diagnostic upper Z crop in metres (not face localization)")
    args = parser.parse_args(argv)
    try:
        report_path, html_path, report = write_outputs(args.archive, args.out,
            expected_sha=args.expect_sha, head_height_m=args.head_height_m)
    except (InvalidNeutralMesh, ValueError, OSError) as exc:
        parser.exit(2, "NEUTRAL INSPECTION BLOCKED: %s\n" % exc)
    print(json.dumps({"status": "PASS_ARCHIVE_ONLY_NOT_LIKENESS", "report": str(report_path),
        "atlas": str(html_path), "topology": report["topology"],
        "diagnostic_upper_z_crop": report["diagnostic_upper_z_crop"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
