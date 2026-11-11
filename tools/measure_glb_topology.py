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
  NOTE: this is CONFOUNDED by glTF's vertex duplication at UV/normal seams,
  so it is DIAGNOSTIC ONLY and must not be used as evidence of quad origin.
* boundary edge count (open shells)
* connected component (shell) count
* morph target inventory (names + per-target moved-vertex counts)
* skin / joint inventory and whether the skin is actually attached
* scene root inventory and which objects are exported

Multi-mesh awareness (C001-GEO-04 defect D1/D2/D3 fix)
--------------------------------------------------------
A GLB may contain several meshes (e.g. Blender's default `Cube` next to the
character). Reading only `meshes[0]` is WRONG and produced a false
"0 morph targets" reading. This tool therefore:
  * reports EVERY mesh,
  * picks the CHARACTER mesh explicitly (override with `--mesh NAME`, or
    auto: the mesh with the most morph targets, tie-broken by triangle count),
  * lists scene roots and flags meshes/objects that are not part of the
    character.

Usage:
    python tools/measure_glb_topology.py <file.glb> [--json out.json] [--mesh NAME]
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter, defaultdict

NUM = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
       5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
TYPESTRUCT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

# Blender's startup scene object. A candidate character asset must not ship it.
DEFAULT_CUBE_NAMES = {"cube", "default cube"}


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
        ncomp = TYPESTRUCT[acc["type"]]
        return [tuple([0.0] * ncomp) for _ in range(acc["count"])]
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    fmt, size = NUM[acc["componentType"]]
    ncomp = TYPESTRUCT[acc["type"]]
    count = acc["count"]
    stride = bv.get("byteStride") or (size * ncomp)
    out = []
    for i in range(count):
        o = base + i * stride
        out.append(struct.unpack_from("<%d%s" % (ncomp, fmt), bin_chunk, o))
    return out


def _node_name(js, index):
    nodes = js.get("nodes", [])
    if index is None or index >= len(nodes):
        return None
    return nodes[index].get("name")


def _primitive_report(js, bin_chunk, prim):
    attrs = prim.get("attributes", {})
    if "POSITION" not in attrs:
        # A primitive without POSITION carries no geometry (e.g. a stub).
        return {
            "vertices": 0, "triangles": 0, "edges": 0,
            "edge_use_histogram": {}, "boundary_edges": 0,
            "non_manifold_edges": 0, "vertex_triangle_valence_histogram": {},
            "even_valence_vertex_pct": None, "connected_shells": 0,
            "largest_shell_triangle_pct": None,
            "has_uv": "TEXCOORD_0" in attrs,
            "has_skin": "JOINTS_0" in attrs,
            "has_normals": "NORMAL" in attrs,
            "morph_target_count": 0, "morph_targets": [],
            "error": "primitive has no POSITION attribute",
        }
    pos = read_accessor(js, bin_chunk, attrs["POSITION"])
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
        for p, q in zip(pos, tpos):
            d = sum((p[k] - q[k]) ** 2 for k in range(3)) ** 0.5
            if d > 1e-6:
                moved += 1
                maxd = max(maxd, d)
        targets.append({"index": t_i, "vertices_moved": moved,
                        "max_displacement": round(maxd, 6)})

    return {
        "vertices": len(pos),
        "triangles": len(tris),
        "edges": len(edge_use),
        "edge_use_histogram": {str(k): v for k, v in
                              sorted(Counter(edge_use.values()).items())},
        "boundary_edges": boundary,
        "non_manifold_edges": nonman,
        "vertex_triangle_valence_histogram": {
            str(k): v for k, v in sorted(Counter(vval.values()).items())},
        "even_valence_vertex_pct": round(100.0 * even / len(pos), 3) if pos else None,
        "connected_shells": len(comps),
        "largest_shell_triangle_pct": round(
            100.0 * max(comps.values()) / len(tris), 3) if tris else None,
        "has_uv": "TEXCOORD_0" in attrs,
        "has_skin": "JOINTS_0" in attrs,
        "has_normals": "NORMAL" in attrs,
        "morph_target_count": len(targets),
        "morph_targets": targets,
    }


def analyse(path, mesh_name=None):
    js, bin_chunk = load_glb(path)
    nodes = js.get("nodes", [])

    # ---- scene roots ------------------------------------------------------
    scenes = js.get("scenes", [])
    scene = scenes[0] if scenes else {}
    scene_roots = [_node_name(js, i) for i in scene.get("nodes", [])]
    scene_roots = [n for n in scene_roots if n is not None]

    # ---- skins ------------------------------------------------------------
    skins = []
    joint_names_all = set()
    for skin in js.get("skins", []):
        joints = skin.get("joints", [])
        names = [_node_name(js, j) for j in joints]
        names = [n for n in names if n]
        joint_names_all.update(names)
        skins.append({
            "name": skin.get("name"),
            "joint_count": len(joints),
            "joint_names": names,
            "skeleton": _node_name(js, skin.get("skeleton")),
        })

    report = {
        "path": os.path.abspath(path),
        "size_bytes": os.path.getsize(path),
        "generator": (js.get("asset") or {}).get("generator"),
        "copyright": (js.get("asset") or {}).get("copyright"),
        "scene_roots": scene_roots,
        "exported_object_names": [n.get("name") for n in nodes if n.get("name")],
        "node_count": len(nodes),
        "skin_present": bool(skins),
        "armature_present": bool(skins) and bool(joint_names_all),
        "joint_count": max([s["joint_count"] for s in skins], default=0),
        "skins": skins,
        "animations": [a.get("name") for a in js.get("animations", [])],
        "meshes": [],
        "character_mesh_name": None,
        "character": None,
        "non_character_meshes": [],
        "default_cube_present": False,
    }

    # ---- per-mesh ---------------------------------------------------------
    for mesh in js.get("meshes", []):
        tn = (mesh.get("extras") or {}).get("targetNames")
        mrep = {
            "name": mesh.get("name"),
            "node_names": [],
            "target_names_present": tn is not None,
            "target_names": list(tn) if tn else [],
            "primitives": [],
        }
        for prim in mesh["primitives"]:
            mrep["primitives"].append(_primitive_report(js, bin_chunk, prim))
        # which nodes use this mesh
        for n in nodes:
            if n.get("mesh") is not None and js["meshes"][n["mesh"]] is mesh:
                if n.get("name"):
                    mrep["node_names"].append(n["name"])
        mrep["total_morph_targets"] = sum(
            p["morph_target_count"] for p in mrep["primitives"])
        mrep["declared_target_name_count"] = len(mrep["target_names"])
        # In a well-formed glTF these agree; a mismatch is worth flagging.
        mrep["target_names_match_primitives"] = (
            mrep["declared_target_name_count"] == mrep["total_morph_targets"])
        mrep["total_triangles"] = sum(
            p["triangles"] for p in mrep["primitives"])
        mrep["total_vertices"] = sum(
            p["vertices"] for p in mrep["primitives"])
        mrep["default_cube_name_match"] = (
            (mesh.get("name") or "").strip().lower() in DEFAULT_CUBE_NAMES)
        mrep["default_cube_geometry_match"] = (
            mrep["total_vertices"] == 24 and mrep["total_triangles"] == 12)
        # Conservative: either signal flags it. A QA gate should flag and let
        # a human look, never silently pass a stray Blender default object.
        mrep["is_default_cube"] = bool(
            mrep["default_cube_name_match"] or mrep["default_cube_geometry_match"])
        report["meshes"].append(mrep)

    report["default_cube_present"] = any(
        m["is_default_cube"] for m in report["meshes"])

    # ---- pick the character mesh ------------------------------------------
    # explicit override wins; otherwise the mesh with the most morph targets
    # (tie-break: most triangles), and a default cube is never chosen.
    chosen = None
    if mesh_name:
        for m in report["meshes"]:
            if m["name"] == mesh_name or mesh_name in (m["node_names"] or []):
                chosen = m
                break
        if chosen is None:
            raise SystemExit("ERROR: no mesh named %r in %s" % (mesh_name, path))
    else:
        candidates = [m for m in report["meshes"] if not m["is_default_cube"]]
        if candidates:
            chosen = max(candidates,
                         key=lambda m: (m["total_morph_targets"], m["total_triangles"]))
    if chosen is not None:
        report["character_mesh_name"] = chosen["name"]
        report["character"] = chosen
        report["non_character_meshes"] = [
            {"name": m["name"], "node_names": m["node_names"],
             "is_default_cube": m["is_default_cube"],
             "morph_targets": m["total_morph_targets"]}
            for m in report["meshes"] if m is not chosen]
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--mesh", dest="mesh_name",
                    help="force the character mesh by name (default: auto-detect)")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.glb):
        print("ERROR: not a file: %s" % args.glb, file=sys.stderr)
        return 2
    rep = analyse(args.glb, args.mesh_name)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)
    print("=" * 78)
    print("GLB MEASUREMENT: %s" % rep["path"])
    print("size_bytes : %d" % rep["size_bytes"])
    print("generator  : %s" % rep["generator"])
    print("copyright  : %s" % rep["copyright"])
    print("scene_roots: %s" % rep["scene_roots"])
    print("skin_present=%s  armature_present=%s  joint_count=%d  animations=%s"
          % (rep["skin_present"], rep["armature_present"], rep["joint_count"],
             rep["animations"]))
    print("meshes (%d):" % len(rep["meshes"]))
    for m in rep["meshes"]:
        print("   %-14s verts=%-7d tris=%-7d morphs=%-4d nodes=%s%s"
              % (m["name"], m["total_vertices"], m["total_triangles"],
                 m["total_morph_targets"], m["node_names"],
                 "  <-- DEFAULT CUBE" if m["is_default_cube"] else ""))
    print("-" * 78)
    print("character mesh : %s" % rep["character_mesh_name"])
    if rep["character"]:
        c = rep["character"]
        print("   targetNames present: %s (%d names)"
              % (c["target_names_present"], len(c["target_names"])))
        for p in c["primitives"]:
            print("   verts=%d tris=%d edges=%d shells=%d(largest %.1f%%)"
                  % (p["vertices"], p["triangles"], p["edges"],
                     p["connected_shells"], p["largest_shell_triangle_pct"] or 0))
            print("   edge_use_hist=%s boundary=%d nonmanifold=%d"
                  % (p["edge_use_histogram"], p["boundary_edges"],
                     p["non_manifold_edges"]))
            print("   uv=%s skin=%s normals=%s morphs=%d"
                  % (p["has_uv"], p["has_skin"], p["has_normals"],
                     p["morph_target_count"]))
    print("non-character meshes: %s" % (rep["non_character_meshes"],))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
