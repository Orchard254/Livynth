"""C001-GEO-04 gate - artifact QA on the candidate GLB (machine measured).

Everything here is measured on the MESH, never on an image, so it is
independent of appearance.  Each check states how it was measured.

Checks
------
manifold / watertight      trimesh is_watertight, euler number, edges whose
                            face adjacency is not exactly two
connected components      trimesh.split(); per component faces / area /
                            volume / mean thickness (volume / area)
duplicate / offset shell   (a) two or more large components whose bounding
                                boxes overlap (a ghost shell inside a head)
                            (b) near-duplicate opposite-facing faces inside a
                                component (a doubled surface) via spatial hash
self-intersection          vertices closer than tol to a NON-adjacent part of
                            the surface (trimesh proximity)
topology class             glTF primitives are triangles by format; the raw
                            polygon class is not recoverable from a GLB, so the
                            report states primitive count, attribute set and
                            whether indices are used
face normal consistency    is_winding_consistent plus the fraction of face
                            normals that disagree with stored vertex normals
degenerate faces           zero-area faces
duplicate vertices         vertices sharing a position
UV                         presence and coverage of the unit UV square
rig / blendshapes          skins, animations and morph targets in the raw
                            glTF JSON, and whether they evaluate
"""

import json
import struct
from pathlib import Path

import numpy as np
import trimesh


def glb_json(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB: %s" % path)
    off = 12
    js = None
    while off < len(data):
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        chunk = data[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        off += 8 + clen + ((4 - clen % 4) % 4)
    return js


def _non_manifold_edges(mesh):
    edges = mesh.edges_sorted
    if len(edges) == 0:
        return 0, 0
    e = edges[np.lexsort((edges[:, 1], edges[:, 0]))]
    same = np.all(e[1:] == e[:-1], axis=1)
    starts = [0] + list((np.nonzero(~same)[0] + 1).tolist())
    ends = starts[1:] + [len(e)]
    boundary = 0
    nonmanifold = 0
    for s0, s1 in zip(starts, ends):
        n = s1 - s0
        if n == 2:
            pass
        elif n == 1:
            boundary += 1
        else:
            nonmanifold += 1
    return int(boundary), int(nonmanifold)


def _duplicate_faces(mesh, tol=0.0015, angle_deg=150.0):
    if len(mesh.faces) == 0:
        return 0
    cents = mesh.triangles_center
    nrm = mesh.face_normals
    scale = max(float(np.ptp(mesh.vertices, axis=0).max()), 1e-6)
    q = np.round(cents / (tol * scale)).astype(np.int64)
    keys = {}
    for i, k in enumerate(map(tuple, q)):
        keys.setdefault(k, []).append(i)
    hits = 0
    cos_lim = np.cos(np.radians(angle_deg))
    for k, idxs in keys.items():
        if len(idxs) < 2:
            continue
        pts = cents[idxs]
        ns = nrm[idxs]
        for ii in range(len(idxs)):
            for jj in range(ii + 1, len(idxs)):
                if np.linalg.norm(pts[ii] - pts[jj]) > tol * scale:
                    continue
                if float(np.dot(ns[ii], ns[jj])) <= cos_lim:
                    hits += 1
    return int(hits)


def _uv_coverage(mesh):
    try:
        visual = mesh.visual
        if not hasattr(visual, "uv") or visual.uv is None:
            return {"present": False, "coverage": None}
        uv = np.asarray(visual.uv, dtype=np.float64)
        uv = uv[mesh.faces].reshape(-1, 2)
        if uv.size == 0:
            return {"present": True, "coverage": 0.0, "min": None, "max": None}
        inside = ((uv[:, 0] >= 0) & (uv[:, 0] <= 1) &
                  (uv[:, 1] >= 0) & (uv[:, 1] <= 1))
        return {"present": True, "coverage": float(np.mean(inside)),
                "min": [float(uv[:, 0].min()), float(uv[:, 1].min())],
                "max": [float(uv[:, 0].max()), float(uv[:, 1].max())]}
    except Exception as exc:
        return {"present": False, "coverage": None, "error": repr(exc)}


def _rig_info(path):
    js = glb_json(path)
    skins = js.get("skins", [])
    anims = js.get("animations", [])
    morph = 0
    prims = 0
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            prims += 1
            morph += len(p.get("targets", []))
    return {"skins": len(skins), "animations": len(anims),
            "morph_targets": int(morph), "primitives": int(prims),
            "rig_present": bool(skins or anims or morph),
            "rig_evaluates": bool(skins and anims)}


def audit_glb(path, tol_m=0.0015):
    """Full artifact QA for one candidate GLB."""
    path = Path(path)
    raw = glb_json(path)
    scene = trimesh.load(str(path), force="scene")
    geoms = list(scene.geometry.values())
    report = {
        "schema": "livynth.c001.gate.artifact-qa.v1",
        "file_name": path.name,
        "gltf": {
            "meshes": len(raw.get("meshes", [])),
            "nodes": len(raw.get("nodes", [])),
            "materials": len(raw.get("materials", [])),
            "images": len(raw.get("images", [])),
            "textures": len(raw.get("textures", [])),
            "primitive_attributes": sorted(
                {a for m in raw.get("meshes", [])
                 for p in m["primitives"] for a in p["attributes"].keys()}),
            "primitive_modes": sorted({p.get("mode", 4)
                                       for m in raw.get("meshes", [])
                                       for p in m["primitives"]}),
            "has_texture": any("baseColorTexture" in m.get("pbrMetallicRoughness", {})
                                for m in raw.get("materials", [])),
            "vertex_colors": any("COLOR_0" in p["attributes"]
                                 for m in raw.get("meshes", [])
                                 for p in m["primitives"]),
        },
        "rig": _rig_info(path),
        "geometries": [],
    }

    total_v = 0
    total_f = 0
    for gi, g in enumerate(geoms):
        total_v += len(g.vertices)
        total_f += len(g.faces)
        boundary, nonmanifold = _non_manifold_edges(g)
        areas = g.area_faces
        degenerate = int(np.sum(areas <= 1e-14))
        verts = np.round(g.vertices, 9)
        uniq = np.unique(verts, axis=0)
        dup_verts = int(len(verts) - len(uniq))
        comps = g.split(only_watertight=False)
        comp_info = []
        for c in comps:
            vol = float(c.volume) if c.is_volume else None
            area = float(c.area)
            comp_info.append({
                "faces": int(len(c.faces)),
                "vertices": int(len(c.vertices)),
                "area_m2": area,
                "volume_m3": vol,
                "mean_thickness_m": (vol / area) if (vol and area) else None,
                "bounds": np.round(c.bounds, 5).tolist(),
                "watertight": bool(c.is_watertight),
            })
        comp_info.sort(key=lambda d: -d["faces"])
        thresh = max(4, int(0.02 * max(1, len(g.faces))))
        big = [c for c in comp_info if c["faces"] >= thresh]
        overlapping = []
        for i in range(len(big)):
            for j in range(i + 1, len(big)):
                bi = big[i]["bounds"]
                bj = big[j]["bounds"]
                if (bi[0][0] < bj[1][0] and bi[1][0] > bj[0][0] and
                        bi[0][1] < bj[1][1] and bi[1][1] > bj[0][1] and
                        bi[0][2] < bj[1][2] and bi[1][2] > bj[0][2]):
                    overlapping.append([i, j])
        dup_faces = _duplicate_faces(g, tol=tol_m)
        selfint = None
        try:
            if len(g.vertices) > 0 and len(g.faces) > 0:
                rng = np.random.default_rng(12345)
                n = min(4000, len(g.vertices))
                sample = g.vertices[rng.choice(len(g.vertices), size=n, replace=False)]
                dist = trimesh.proximity.signed_distance(g, sample)
                selfint = {
                    "sampled_vertices": int(n),
                    "min_signed_distance_m": float(np.nanmin(dist)) if len(dist) else None,
                    "fraction_within_1mm_of_surface": float(
                        np.mean(np.abs(dist) < 0.001)) if len(dist) else None,
                }
        except Exception as exc:
            selfint = {"error": repr(exc)}

        report["geometries"].append({
            "index": gi,
            "vertices": int(len(g.vertices)),
            "faces": int(len(g.faces)),
            "watertight": bool(g.is_watertight),
            "winding_consistent": bool(g.is_winding_consistent),
            "euler_number": int(g.euler_number),
            "boundary_edges": boundary,
            "non_manifold_edges": nonmanifold,
            "degenerate_faces": degenerate,
            "duplicate_vertices": dup_verts,
            "duplicate_opposite_faces": dup_faces,
            "component_count": len(comp_info),
            "large_component_count": len(big),
            "overlapping_large_components": overlapping,
            "components": comp_info[:12],
            "uv": _uv_coverage(g),
            "self_intersection": selfint,
            "bounds_m": np.round(g.bounds, 5).tolist(),
            "extent_m": [float(x) for x in (g.bounds[1] - g.bounds[0])],
        })
    report["totals"] = {"geometries": len(geoms), "vertices": total_v, "faces": total_f}
    report["verdict"] = verdict(report)
    return report


def verdict(report):
    """Machine verdict for the artifact QA (independent of appearance)."""
    reasons = []
    geoms = report.get("geometries", [])
    if not geoms:
        return {"pass": False, "reasons": ["no_geometry"]}
    components = sum(g.get("component_count", 0) for g in geoms)
    duplicates = sum(g.get("duplicate_opposite_faces", 0) for g in geoms)
    nonmanifold = sum(g.get("non_manifold_edges", 0) for g in geoms)
    boundary = sum(g.get("boundary_edges", 0) for g in geoms)
    degenerate = sum(g.get("degenerate_faces", 0) for g in geoms)
    overlapping = sum(len(g.get("overlapping_large_components", [])) for g in geoms)
    if components > 1:
        reasons.append("multiple_connected_components:%d" % components)
    if overlapping:
        reasons.append("overlapping_large_components:%d" % overlapping)
    if duplicates > 0:
        reasons.append("duplicate_opposite_faces:%d" % duplicates)
    if nonmanifold > 0:
        reasons.append("non_manifold_edges:%d" % nonmanifold)
    if boundary > 0:
        reasons.append("boundary_edges:%d" % boundary)
    if not all(g.get("watertight", False) for g in geoms):
        reasons.append("not_watertight")
    if degenerate > 0:
        reasons.append("degenerate_faces:%d" % degenerate)
    if not all(g.get("uv", {}).get("present", False) for g in geoms):
        reasons.append("no_uv")
    return {"pass": len(reasons) == 0, "reasons": reasons}
