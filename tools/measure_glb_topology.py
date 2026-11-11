#!/usr/bin/env python3
"""Measure a GLB/GLTF mesh container's topology without Blender.

C001-GEO-04 / ADR-C001-004 Decision 1. glTF stores triangles only, so this
tool reports triangle counts and *quad-grid consistency evidence* rather than
claiming "quads":

* triangle count
* edge-use histogram (how many triangles share each undirected edge)
* vertex triangle-valence histogram
* "even vertex valence" fraction -- in a triangulated quad grid every vertex
  is incident to an even number of triangles (2 per quad corner)
* boundary edge count (open shells)
* connected component (shell) count
* morph target inventory (names + per-target moved-vertex counts)
* skin/joint inventory
* UV accessor presence

Usage:
    python tools/measure_glb_topology.py <file.glb> [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter, defaultdict

COMP = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
NUM = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
       5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
TYPESTRUCT = {"SCALAR": ("", 1), "VEC2": ("", 2), "VEC3": ("", 3), "VEC4": ("", 4)}


def load_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, ver, length = struct.unpack("<III", data[:12])
    if magic != 0x46546C67:
        raise ValueError("not a GLB: %s" % path)
    off = 12
    js = None
    bin_chunk = b""
    while off < length:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        payload = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(payload.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_chunk = payload
        off += 8 + clen
    return js, bin_chunk


def read_accessor(js, bin_chunk, index):
    acc = js["accessors"][index]
    if "bufferView" not in acc:
        # Zero-filled accessor (no backing buffer view): glTF allows this for
        # morph targets that only carry NORMAL, and some exporters emit it.
        ncomp = TYPESTRUCT[acc["type"]][1]
        return [tuple([0.0] * ncomp) for _ in range(acc["count"])]
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    fmt, size = NUM[acc["componentType"]]
    ncomp = TYPESTRUCT[acc["type"]][1]
    count = acc["count"]
    stride = bv.get("byteStride") or (size * ncomp)
    out = []
    for i in range(count):
        o = base + i * stride
        out.append(struct.unpack_from("<%d%s" % (ncomp, fmt), bin_chunk, o))
    return out


def analyse(path):
    js, bin_chunk = load_glb(path)
    report = {
        "path": os.path.abspath(path),
        "size_bytes": os.path.getsize(path),
        "generator": (js.get("asset") or {}).get("generator"),
        "copyright": (js.get("asset") or {}).get("copyright"),
        "meshes": [],
        "skins": [],
        "animations": [],
        "nodes": [n.get("name") for n in js.get("nodes", [])],
    }
    for skin in js.get("skins", []):
        report["skins"].append({"name": skin.get("name"),
                                "joint_count": len(skin.get("joints", []))})
    for anim in js.get("animations", []):
        report["animations"].append(anim.get("name"))

    for mesh in js.get("meshes", []):
        tn = (mesh.get("extras") or {}).get("targetNames")
        mrep = {"name": mesh.get("name"), "primitives": []}
        for prim in mesh["primitives"]:
            attrs = prim.get("attributes", {})
            pos = read_accessor(js, bin_chunk, attrs["POSITION"])
            idx = None
            if "indices" in prim:
                idx = [v[0] for v in read_accessor(js, bin_chunk, prim["indices"])]
            else:
                idx = list(range(len(pos)))
            tris = [tuple(idx[i:i + 3]) for i in range(0, len(idx) - 2, 3)]

            edge_use = Counter()
            for a, b, c in tris:
                for e in ((a, b), (b, c), (c, a)):
                    edge_use[(e[0], e[1]) if e[0] < e[1] else (e[1], e[0])] += 1
            vval = Counter()
            for a, b, c in tris:
                for v in (a, b, c):
                    vval[v] += 1
            even = sum(1 for v in range(len(pos)) if vval.get(v, 0) % 2 == 0)
            boundary = sum(1 for v_ in edge_use.values() if v_ == 1)
            nonman = sum(1 for v_ in edge_use.values() if v_ > 2)

            # connected components over triangles via shared edges
            parent = list(range(len(tris)))

            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a

            v2t = defaultdict(list)
            for ti, (a, b, c) in enumerate(tris):
                for v in (a, b, c):
                    v2t[v].append(ti)
            for v, tl in v2t.items():
                for i in range(1, len(tl)):
                    ra, rb = find(tl[0]), find(tl[i])
                    if ra != rb:
                        parent[rb] = ra
            comps = Counter(find(i) for i in range(len(tris)))

            targets = []
            for t_i, tgt in enumerate(prim.get("targets", [])):
                if "POSITION" not in tgt:
                    continue
                tpos = read_accessor(js, bin_chunk, tgt["POSITION"])
                moved = 0
                maxd = 0.0
                for i, (p, q) in enumerate(zip(pos, tpos)):
                    d = sum((p[k] - q[k]) ** 2 for k in range(3)) ** 0.5
                    if d > 1e-6:
                        moved += 1
                        maxd = max(maxd, d)
                targets.append({
                    "name": tn[t_i] if tn and t_i < len(tn) else "target_%d" % t_i,
                    "vertices_moved": moved,
                    "max_displacement": round(maxd, 6),
                })

            mrep["primitives"].append({
                "vertices": len(pos),
                "triangles": len(tris),
                "edges": len(edge_use),
                "edge_use_histogram": {str(k): v for k, v in
                                      sorted(Counter(edge_use.values()).items())},
                "boundary_edges": boundary,
                "non_manifold_edges": nonman,
                "vertex_triangle_valence_histogram": {
                    str(k): v for k, v in sorted(Counter(vval.values()).items())},
                "even_valence_vertex_pct": round(
                    100.0 * even / len(pos), 3) if pos else None,
                "connected_shells": len(comps),
                "largest_shell_triangle_pct": round(
                    100.0 * max(comps.values()) / len(tris), 3) if tris else None,
                "has_uv": "TEXCOORD_0" in attrs,
                "has_skin": "JOINTS_0" in attrs,
                "morph_target_count": len(targets),
                "morph_targets": targets,
            })
        report["meshes"].append(mrep)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.glb):
        print("ERROR: not a file: %s" % args.glb, file=sys.stderr)
        return 2
    rep = analyse(args.glb)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)
    print("=" * 78)
    print("GLB MEASUREMENT: %s" % rep["path"])
    print("size_bytes : %d" % rep["size_bytes"])
    print("generator  : %s" % rep["generator"])
    print("copyright  : %s" % rep["copyright"])
    print("skins      : %s" % rep["skins"])
    for m in rep["meshes"]:
        print("-" * 78)
        print("MESH %s" % m["name"])
        for p in m["primitives"]:
            print("   verts=%d tris=%d edges=%d shells=%d(largest %.1f%%)"
                  % (p["vertices"], p["triangles"], p["edges"],
                     p["connected_shells"], p["largest_shell_triangle_pct"] or 0))
            print("   edge_use_hist=%s boundary=%d nonmanifold=%d"
                  % (p["edge_use_histogram"], p["boundary_edges"], p["non_manifold_edges"]))
            print("   even_valence_verts=%.2f%%  uv=%s skin=%s  morphs=%d"
                  % (p["even_valence_vertex_pct"] or 0.0, p["has_uv"],
                     p["has_skin"], p["morph_target_count"]))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
