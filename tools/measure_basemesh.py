#!/usr/bin/env python3
"""Measure a Wavefront OBJ basemesh without Blender.

C001-GEO-04 / ADR-C001-004 Decision 1 (Topology Option B).
The ADR requires topology suitability to be assessed "with measurements, not
adjectives". This script produces the measured evidence for any candidate
quad base mesh found on the machine.

It is dependency-light (stdlib + numpy if available) and re-runnable:

    python tools/measure_basemesh.py <path-to.obj> [--json out.json]

Axis convention for MakeHuman-style basemeshes (verified empirically, see
`axis_convention` in the JSON report): X = left/right, Y = UP, Z = front(+)/back(-).

Reported quantities
-------------------
* vertex / face counts
* polygon-size histogram (how many faces are tris, quads, ngons ...)
* quad dominance ratio
* edge manifoldness (boundary / manifold / non-manifold edge counts)
* connected components (shell count + sizes) -- answers "is the head one shell?"
* per-group shell counts (body vs helper vs joint-cube geometry)
* loose vertices
* UV presence and coverage (does a usable UV layer exist for baking?)
* vertex groups (MakeHuman-style region groups) -- answers "can we isolate
  nose / eye socket / lips / jaw / neck?"
* mirror symmetry about X=0 (MakeHuman basemeshes are built symmetric)
* per-region face/edge census for the face deformation regions, with the
  regions derived from *measured* joint-cube anchors (head/jaw/neck/eyes/mouth)
  rather than hand-guessed coordinates
* bounding box and derived head metrics
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is in requirements-geometry.txt
    np = None


def parse_obj(path):
    verts = []
    vts = []
    faces = []          # list of tuples of (v_idx, vt_idx) -- 0-based
    group_of_face = []
    mat_of_face = []
    cur_group = "_default"
    cur_mat = "_none"
    materials = []
    header = []

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line:
                continue
            if line[0] == "#":
                header.append(line.rstrip("\n"))
                continue
            # NOTE: "vt" must be tested before the generic "v" prefix.
            if line.startswith("vt "):
                parts = line.split()
                vts.append((float(parts[1]), float(parts[2])))
                continue
            if line.startswith("v "):
                verts.append(tuple(float(x) for x in line.split()[1:4]))
                continue
            if line.startswith("g "):
                cur_group = line[2:].strip()
                continue
            if line.startswith("usemtl"):
                cur_mat = line[7:].strip()
                if cur_mat not in materials:
                    materials.append(cur_mat)
                continue
            if line.startswith("f "):
                nv_so_far = len(verts)
                nt_so_far = len(vts)
                idx = []
                for tok in line.split()[1:]:
                    bits = tok.split("/")
                    # OBJ indices are 1-based; negative values are relative to
                    # the end of the current vertex list. Store 0-based.
                    vi = int(bits[0])
                    vi = vi - 1 if vi > 0 else (nv_so_far + vi)
                    ti = None
                    if len(bits) > 1 and bits[1]:
                        ti = int(bits[1])
                        ti = ti - 1 if ti > 0 else (nt_so_far + ti)
                    idx.append((vi, ti))
                faces.append(idx)
                group_of_face.append(cur_group)
                mat_of_face.append(cur_mat)

    groups_map = defaultdict(list)
    for fi, g in enumerate(group_of_face):
        groups_map[g].append(fi)

    return dict(
        verts=verts, vts=vts, faces=faces, groups=groups_map,
        materials=materials, header=header,
        group_of_face=group_of_face, mat_of_face=mat_of_face,
    )


def _components(edge_faces, faces, subset=None):
    """Union-find connected components over faces (optionally a face subset)."""
    nf = len(faces)
    parent = list(range(nf))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for key, fl in edge_faces.items():
        if subset is not None and not (set(fl) & subset):
            continue
        for i in range(1, len(fl)):
            union(fl[0], fl[i])

    comp = defaultdict(int)
    for fi in range(nf):
        if subset is not None and fi not in subset:
            continue
        comp[find(fi)] += 1
    return sorted(comp.values(), reverse=True)


def analyse(path):
    data = parse_obj(path)
    verts = data["verts"]
    vts = data["vts"]
    faces = data["faces"]
    nv = len(verts)
    nf = len(faces)

    # ---- polygon size histogram -------------------------------------------
    poly_hist = Counter(len(f) for f in faces)
    quads = poly_hist.get(4, 0)
    tris = poly_hist.get(3, 0)
    ngons = sum(c for k, c in poly_hist.items() if k > 4)
    quads_pct = 100.0 * quads / nf if nf else 0.0

    # ---- edges ------------------------------------------------------------
    edge_faces = defaultdict(list)
    for fi, f in enumerate(faces):
        n = len(f)
        for i in range(n):
            a = f[i][0]
            b = f[(i + 1) % n][0]
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            edge_faces[key].append(fi)

    boundary = manifold = nonmanifold = 0
    for key, fl in edge_faces.items():
        c = len(fl)
        if c == 1:
            boundary += 1
        elif c == 2:
            manifold += 1
        else:
            nonmanifold += 1

    comp_sizes = _components(edge_faces, faces)

    # ---- connected components per vertex-group family ---------------------
    group_faces = data["groups"]
    body_idx = set(group_faces.get("body", []))
    body_components = _components(edge_faces, faces, body_idx) if body_idx else []

    # ---- loose vertices ---------------------------------------------------
    used = set()
    for f in faces:
        for vi, _ in f:
            used.add(vi)
    loose = nv - len(used)

    # ---- UVs --------------------------------------------------------------
    has_vt = len(vts) > 0
    faces_with_uv = 0
    uv_invalid = 0
    uv_area_total = 0.0
    uv_lo = [1e9, 1e9]
    uv_hi = [-1e9, -1e9]
    if has_vt:
        for f in faces:
            if any(t is not None for _, t in f):
                faces_with_uv += 1
        for f in faces:
            pts = []
            ok = True
            for _, t in f:
                if t is None or not (0 <= t < len(vts)):
                    ok = False
                    break
                pts.append(vts[t])
            if not ok or len(pts) < 3:
                uv_invalid += 1
                continue
            a = 0.0
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                a += x1 * y2 - x2 * y1
                uv_lo[0] = min(uv_lo[0], x1)
                uv_lo[1] = min(uv_lo[1], y1)
                uv_hi[0] = max(uv_hi[0], x1)
                uv_hi[1] = max(uv_hi[1], y1)
            uv_area_total += abs(a) * 0.5
    else:
        faces_with_uv = 0

    # ---- vertex groups ----------------------------------------------------
    group_sizes = {k: len(v) for k, v in sorted(data["groups"].items())}

    # ---- joint-cube anchors (measured anatomical landmarks) ---------------
    anchors = {}
    for gname, flist in group_faces.items():
        if not gname.startswith("joint-"):
            continue
        vids = set()
        for fi in flist:
            for vi, _ in faces[fi]:
                vids.add(vi)
        if not vids:
            continue
        pts = [verts[i] for i in vids]
        anchors[gname] = [
            round(sum(p[0] for p in pts) / len(pts), 4),
            round(sum(p[1] for p in pts) / len(pts), 4),
            round(sum(p[2] for p in pts) / len(pts), 4),
        ]

    # ---- bounding box + symmetry -----------------------------------------
    bbox = None
    sym = None
    axis_convention = None
    if nv and np is not None:
        V = np.asarray(verts, dtype=float)
        bb_min = V.min(axis=0)
        bb_max = V.max(axis=0)
        extent = bb_max - bb_min
        bbox = dict(min=[round(float(v), 6) for v in bb_min],
                    max=[round(float(v), 6) for v in bb_max],
                    extent=[round(float(v), 6) for v in extent])
        # MakeHuman convention is Y-up; confirm by checking the head anchor.
        head = anchors.get("joint-head")
        axis_convention = {
            "assumed": "X=left/right, Y=UP, Z=front(+)",
            "head_anchor_y": head[1] if head else None,
            "foot_anchor_y": anchors.get("joint-ground", [None, None, None])[1],
            "up_axis_is_Y": bool(head and anchors.get("joint-ground")
                                and head[1] > anchors["joint-ground"][1]),
        }
        key_to_idx = defaultdict(list)
        for i, (x, y, z) in enumerate(verts):
            key_to_idx[(round(y, 5), round(z, 5))].append(i)
        matched = 0
        for i, (x, y, z) in enumerate(verts):
            cands = key_to_idx.get((round(y, 5), round(z, 5)), [])
            if any(abs(verts[j][0] + x) < 1e-4 for j in cands):
                matched += 1
        sym = dict(vertices_with_mirror_partner=matched,
                   mirror_pct=round(100.0 * matched / nv, 3) if nv else 0.0)

    # ---- vertex face-incidence histogram ---------------------------------
    vcount = Counter()
    for f in faces:
        for vi, _ in f:
            vcount[vi] += 1
    valence_hist = Counter(vcount.get(i, 0) for i in range(nv))

    # ---- per-region census ------------------------------------------------
    regions = {}
    if nv and np is not None and anchors:
        V = np.asarray(verts, dtype=float)

        def anchor(name):
            return anchors.get(name)

        eye_l = anchor("joint-l-eye")
        eye_r = anchor("joint-r-eye")
        mouth = anchor("joint-mouth")
        jaw = anchor("joint-jaw")
        neck = anchor("joint-neck")
        head = anchor("joint-head")

        probes = {}
        if eye_l and eye_r:
            ey = (eye_l[1] + eye_r[1]) / 2.0
            ez = (eye_l[2] + eye_r[2]) / 2.0
            probes["eye_socket"] = dict(
                x=(-0.60, 0.60), y=(ey - 0.35, ey + 0.35), z=(ez - 0.45, ez + 0.45))
        if mouth:
            probes["lips"] = dict(
                x=(-0.55, 0.55),
                y=(mouth[1] - 0.30, mouth[1] + 0.30),
                z=(mouth[2] - 0.40, mouth[2] + 0.40))
        if jaw:
            probes["jaw"] = dict(
                x=(-0.75, 0.75),
                y=(jaw[1] - 0.55, jaw[1] + 0.55),
                z=(jaw[2] - 0.90, jaw[2] + 0.90))
        if neck:
            probes["neck"] = dict(
                x=(-0.60, 0.60),
                y=(neck[1] - 0.60, neck[1] + 0.60),
                z=(neck[2] - 0.70, neck[2] + 0.70))
        if head and eye_l and eye_r:
            ey = (eye_l[1] + eye_r[1]) / 2.0
            probes["brow"] = dict(
                x=(-0.60, 0.60), y=(ey + 0.30, ey + 0.75),
                z=(eye_l[2] - 0.55, eye_l[2] + 0.45))
            top = anchors.get("joint-head-2", head)
            probes["forehead"] = dict(
                x=(-0.70, 0.70), y=(ey + 0.70, top[1] + 0.10),
                z=(eye_l[2] - 0.60, eye_l[2] + 0.55))
        if mouth and eye_l:
            probes["nose"] = dict(
                x=(-0.32, 0.32),
                y=(mouth[1] + 0.20, eye_l[1] - 0.05),
                z=(eye_l[2] + 0.05, eye_l[2] + 0.60))

        for name, box in probes.items():
            sel = np.where(
                (V[:, 0] >= box["x"][0]) & (V[:, 0] <= box["x"][1]) &
                (V[:, 1] >= box["y"][0]) & (V[:, 1] <= box["y"][1]) &
                (V[:, 2] >= box["z"][0]) & (V[:, 2] <= box["z"][1])
            )[0]
            selset = set(int(v) for v in sel)
            fcount = 0
            qcount = 0
            vsum = 0
            rv = set()
            for f in faces:
                if all(vi in selset for vi, _ in f):
                    fcount += 1
                    vsum += len(f)
                    if len(f) == 4:
                        qcount += 1
                    for vi, _ in f:
                        rv.add(vi)
            # Edge-loop regularity: in a regular quad grid every vertex has
            # exactly 4 incident faces. Poles (valence != 4) break clean loops.
            poles = sum(1 for vi in rv if vcount.get(vi, 0) != 4)
            regions[name] = dict(
                probe_box=box,
                vertices_in_box=len(selset),
                faces_fully_inside=fcount,
                quads_fully_inside=qcount,
                mean_verts_per_face=round(vsum / fcount, 3) if fcount else None,
                quad_pct=round(100.0 * qcount / fcount, 2) if fcount else None,
                loop_vertices=len(rv),
                loop_poles_valence_ne_4=poles,
                pole_pct=round(100.0 * poles / len(rv), 3) if rv else None,
            )

    # ---- body-group pole statistics (global, unbiased) --------------------
    body_poles = None
    if body_idx:
        body_verts = set()
        for fi in body_idx:
            for vi, _ in faces[fi]:
                body_verts.add(vi)
        val_hist = Counter(vcount.get(vi, 0) for vi in body_verts)
        body_poles = dict(
            vertices=len(body_verts),
            valence_histogram={str(k): v for k, v in sorted(val_hist.items())},
            regular_quad_valence4_pct=round(
                100.0 * val_hist.get(4, 0) / len(body_verts), 4) if body_verts else None,
        )

    # ---- UV overlap estimate (rasterised) ---------------------------------
    uv_overlap = None
    if has_vt:
        RES = 512
        grid = Counter()
        for f in faces:
            pts = []
            ok = True
            for _, t in f:
                if t is None or not (0 <= t < len(vts)):
                    ok = False
                    break
                pts.append(vts[t])
            if not ok or len(pts) < 3:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, x1 = max(0, int(min(xs) * RES)), min(RES - 1, int(max(xs) * RES))
            y0, y1 = max(0, int(min(ys) * RES)), min(RES - 1, int(max(ys) * RES))
            for gy in range(y0, y1 + 1):
                for gx in range(x0, x1 + 1):
                    cx = (gx + 0.5) / RES
                    cy = (gy + 0.5) / RES
                    # point-in-triangle
                    d1 = (cx - pts[0][0]) * (pts[1][1] - pts[0][1]) - \
                         (pts[1][0] - pts[0][0]) * (cy - pts[0][1])
                    d2 = (cx - pts[1][0]) * (pts[2][1] - pts[1][1]) - \
                         (pts[2][0] - pts[1][0]) * (cy - pts[1][1])
                    d3 = (cx - pts[2][0]) * (pts[0][1] - pts[2][1]) - \
                         (pts[0][0] - pts[2][0]) * (cy - pts[2][1])
                    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                    if not (neg and pos):
                        grid[(gx, gy)] += 1
        covered = len(grid)
        overlapping = sum(1 for v in grid.values() if v > 1)
        uv_overlap = dict(
            grid_resolution=RES,
            covered_cells=covered,
            covered_fraction=round(covered / float(RES * RES), 5),
            overlapping_cells=overlapping,
            overlapping_fraction=round(overlapping / float(max(covered, 1)), 5),
        )

    # ---- head shell continuity -------------------------------------------
    head_shell = None
    if nv and np is not None and anchors.get("joint-neck"):
        V = np.asarray(verts, dtype=float)
        neck_y = anchors["joint-neck"][1]
        head_faces = {fi for fi, f in enumerate(faces)
                      if all(V[vi][1] > neck_y for vi, _ in f)}
        if head_faces:
            hs = _components(edge_faces, faces, head_faces)
            head_shell = dict(
                neck_y=round(neck_y, 4),
                faces_above_neck=len(head_faces),
                components=len(hs),
                sizes_top10=hs[:10],
                single_shell=len(hs) == 1,
            )

    return dict(
        path=os.path.abspath(path),
        size_bytes=os.path.getsize(path),
        sha256=_sha256(path),
        header_comment=data["header"],
        axis_convention=axis_convention,
        counts=dict(
            vertices=nv,
            texture_vertices=len(vts),
            faces=nf,
            groups=len(data["groups"]),
            materials=len(data["materials"]),
            edges=len(edge_faces),
        ),
        polygon_size_histogram={str(k): v for k, v in sorted(poly_hist.items())},
        quads=quads,
        tris=tris,
        ngons_gt4=ngons,
        quad_dominance_pct=round(quads_pct, 3),
        edges=dict(
            total=len(edge_faces),
            boundary_open=boundary,
            manifold_2face=manifold,
            nonmanifold_gt2face=nonmanifold,
            euler_V_minus_E_plus_F=(nv - len(edge_faces) + nf),
        ),
        connected_components=dict(
            count=len(comp_sizes),
            sizes_top20=comp_sizes[:20],
            largest_fraction=round(comp_sizes[0] / nf, 4) if nf and comp_sizes else None,
        ),
        body_group_components=dict(
            count=len(body_components),
            sizes_top20=body_components[:20],
        ),
        body_group_pole_stats=body_poles,
        loose_vertices=loose,
        uvs=dict(
            texture_vertices=len(vts),
            has_uv_layer=has_vt,
            faces_with_texture_indices=faces_with_uv,
            faces_with_invalid_texture_indices=uv_invalid,
            total_uv_area=round(uv_area_total, 6),
            uv_bounds=[uv_lo, uv_hi] if has_vt else None,
        ),
        materials=data["materials"],
        vertex_groups=group_sizes,
        joint_anchors=anchors,
        bbox=bbox,
        symmetry=sym,
        head_shell_continuity=head_shell,
        uv_overlap_estimate=uv_overlap,
        face_region_census=regions,
        vertex_face_incidence_histogram={str(k): v for k, v in sorted(valence_hist.items())},
    )


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("obj", help="path to the .obj basemesh")
    ap.add_argument("--json", dest="json_out", help="write the full report as JSON here")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.obj):
        print("ERROR: not a file: %s" % args.obj, file=sys.stderr)
        return 2

    rep = analyse(args.obj)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2)

    c = rep["counts"]
    print("=" * 78)
    print("BASEMESH MEASUREMENT: %s" % rep["path"])
    print("sha256            : %s" % rep["sha256"])
    print("size_bytes        : %d" % rep["size_bytes"])
    print("-" * 78)
    print("vertices          : %d" % c["vertices"])
    print("texture_vertices  : %d" % c["texture_vertices"])
    print("faces             : %d" % c["faces"])
    print("edges             : %d" % c["edges"])
    print("vertex groups     : %d" % c["groups"])
    print("-" * 78)
    print("polygon size histogram : %s" % rep["polygon_size_histogram"])
    print("quads=%d  tris=%d  ngons(>4)=%d  quad_dominance=%.2f%%"
          % (rep["quads"], rep["tris"], rep["ngons_gt4"], rep["quad_dominance_pct"]))
    print("-" * 78)
    print("edges: total=%d boundary(open)=%d manifold(2-face)=%d non-manifold(>2)=%d"
          % (rep["edges"]["total"], rep["edges"]["boundary_open"],
             rep["edges"]["manifold_2face"], rep["edges"]["nonmanifold_gt2face"]))
    print("euler V-E+F       : %d" % rep["edges"]["euler_V_minus_E_plus_F"])
    print("connected shells  : %d (largest holds %.2f%% of faces)"
          % (rep["connected_components"]["count"],
             100.0 * (rep["connected_components"]["largest_fraction"] or 0.0)))
    print("body-group shells : %d (sizes %s)"
          % (rep["body_group_components"]["count"],
             rep["body_group_components"]["sizes_top20"][:8]))
    bp = rep.get("body_group_pole_stats")
    if bp:
        print("body-group valence: %s   valence-4 (regular quad) = %.3f%%"
              % (bp["valence_histogram"], bp["regular_quad_valence4_pct"]))
    print("loose vertices    : %d" % rep["loose_vertices"])
    print("-" * 78)
    print("UV layer          : %s   faces_with_uv=%d  invalid_uv_faces=%d  uv_area=%.4f"
          % (rep["uvs"]["has_uv_layer"], rep["uvs"]["faces_with_texture_indices"],
             rep["uvs"]["faces_with_invalid_texture_indices"], rep["uvs"]["total_uv_area"]))
    print("uv bounds         : %s" % (rep["uvs"]["uv_bounds"],))
    print("materials         : %s" % (rep["materials"],))
    print("-" * 78)
    print("axis convention   : %s" % (rep["axis_convention"],))
    print("bbox              : %s" % (rep["bbox"],))
    print("mirror symmetry   : %s" % (rep["symmetry"],))
    print("-" * 78)
    print("joint anchors (measured):")
    for k in sorted(rep["joint_anchors"]):
        if any(t in k for t in ("head", "jaw", "neck", "eye", "mouth", "ground", "spine")):
            print("   %-22s %s" % (k, rep["joint_anchors"][k]))
    print("-" * 78)
    print("face-region census:")
    for k, v in rep["face_region_census"].items():
        print("   %-12s verts=%-6d faces=%-6d quads=%-6d quad%%=%s poles(val!=4)=%s (%.2f%%)"
              % (k, v["vertices_in_box"], v["faces_fully_inside"], v["quads_fully_inside"],
                 v["quad_pct"], v["loop_poles_valence_ne_4"], v["pole_pct"] or 0.0))
    print("-" * 78)
    print("head shell continuity : %s" % (rep["head_shell_continuity"],))
    print("UV overlap estimate   : %s" % (rep["uv_overlap_estimate"],))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
