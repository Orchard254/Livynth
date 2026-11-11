"""C001-GEO-05: bounded, neutral MPFB basemesh fitting.

Applies independently reviewed *3D* anatomical constraints to a baked Blender
neutral mesh before the ARKit/Meta face targets are loaded. This is not a
photo-to-3D solver, calibrated camera system, or proof of Character 001 likeness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

SCHEMA = "livynth.c001.stage1.constraints.v1"


class FitRejected(ValueError):
    """Invalid/unsafe proposed fit: caller must not export the candidate."""


def _points(values):
    p = np.asarray(values, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4:
        raise FitRejected("E_VERTICES_SHAPE")
    if not np.isfinite(p).all():
        raise FitRejected("E_VERTICES_NONFINITE")
    return p


def positions_sha256(vertices):
    p = _points(vertices)
    return hashlib.sha256(np.ascontiguousarray(p, dtype="<f8").tobytes()).hexdigest()


def _region_weight(points, region):
    if not isinstance(region, dict) or set(region) != {"axis", "min_m", "max_m", "taper_m"}:
        raise FitRejected("E_REGION_SCHEMA")
    if region["axis"] not in ("x", "y", "z"):
        raise FitRejected("E_REGION_AXIS")
    try:
        lo, hi, taper = (float(region[k]) for k in ("min_m", "max_m", "taper_m"))
    except (TypeError, ValueError) as exc:
        raise FitRejected("E_REGION_BOUNDS") from exc
    if not (np.isfinite([lo, hi, taper]).all() and hi > lo and taper > 0 and 2 * taper < hi - lo):
        raise FitRejected("E_REGION_BOUNDS")
    v = points[:, "xyz".index(region["axis"])]
    q = np.minimum(np.clip((v - lo) / taper, 0, 1), np.clip((hi - v) / taper, 0, 1))
    return q * q * (3 - 2 * q)


def _face_safety(before, after, faces):
    if faces is None:
        return {"face_check": "UNVERIFIED", "minimum_area_ratio": None}
    f = np.asarray(faces)
    if f.ndim != 2 or f.shape[1] not in (3, 4) or not np.issubdtype(f.dtype, np.integer):
        raise FitRejected("E_FACES_SHAPE")
    if f.size == 0 or f.min() < 0 or f.max() >= len(before):
        raise FitRejected("E_FACE_INDICES")
    def normals(points):
        q = points[f]
        n1 = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
        if f.shape[1] == 3:
            return n1[:, None, :]
        n2 = np.cross(q[:, 2] - q[:, 0], q[:, 3] - q[:, 0])
        return np.stack([n1, n2], axis=1)
    n0, n1 = normals(before), normals(after)
    a0, a1 = np.linalg.norm(n0, axis=-1), np.linalg.norm(n1, axis=-1)
    if (a0 < 1e-12).any():
        raise FitRejected("E_BASELINE_DEGENERATE_FACE")
    ratio = a1 / a0
    if (ratio < .25).any() or (np.sum(n0 * n1, axis=-1) <= 0).any():
        raise FitRejected("E_FACE_COLLAPSE_OR_FLIP")
    return {"face_check": "PASS_LOCAL_NONFLIP_ONLY",
            "minimum_area_ratio": float(ratio.min())}


def propose_fit(vertices, specification, faces=None):
    """Pure numeric fit: never mutates input vertices.

    Mirror control fields around x=0, lock the rest of the mesh outside a
    specified face zone, and reject impossible, ill-conditioned or overshooting
    displacement fields. Does NOT test global self-intersections or likeness.
    """
    before = _points(vertices)
    s = specification
    if not isinstance(s, dict) or s.get("schema") != SCHEMA:
        raise FitRejected("E_SCHEMA")
    source = s.get("source", {})
    if source.get("vertex_count") != len(before) or source.get("positions_sha256") != positions_sha256(before):
        raise FitRejected("E_SOURCE_MISMATCH")
    if faces is not None and source.get("quad_face_count") != len(faces):
        raise FitRejected("E_TOPOLOGY_COUNT_MISMATCH")
    if s.get("reference_calibrated") is not False:
        raise FitRejected("E_REFERENCE_STATUS")
    if s.get("input_kind") != "MANUALLY_REVIEWED_3D_CONSTRAINTS":
        raise FitRejected("E_3D_CONSTRAINTS_REQUIRED")
    controls = s.get("anchors")
    if not isinstance(controls, list) or not 1 <= len(controls) <= 48:
        raise FitRejected("E_ANCHORS_COUNT")
    try:
        radius = float(s.get("radius_m", 0))
        limit = float(s.get("max_displacement_m", 0))
    except (TypeError, ValueError) as exc:
        raise FitRejected("E_FIT_BOUNDS") from exc
    if not (np.isfinite([radius, limit]).all() and .002 <= radius <= .15 and .001 <= limit <= .05):
        raise FitRejected("E_FIT_BOUNDS")
    region = _region_weight(before, s.get("region"))
    anchors, deltas, used = [], [], set()
    for a in controls:
        if not isinstance(a, dict) or set(a) != {"vertex_index", "target_m", "name", "basis"}:
            raise FitRejected("E_ANCHOR_SCHEMA")
        i = a["vertex_index"]
        if type(i) is not int or i < 0 or i >= len(before) or i in used:
            raise FitRejected("E_ANCHOR_VERTEX")
        if not isinstance(a["name"], str) or not a["name"].strip():
            raise FitRejected("E_ANCHOR_NAME")
        if a["basis"] != "MANUAL_3D_ESTIMATE":
            raise FitRejected("E_UNSUPPORTED_ANCHOR_BASIS")
        used.add(i)
        target = np.asarray(a["target_m"], dtype=np.float64)
        if target.shape != (3,) or not np.isfinite(target).all():
            raise FitRejected("E_ANCHOR_TARGET")
        delta = target - before[i]
        if np.linalg.norm(delta) > limit + 1e-12:
            raise FitRejected("E_ANCHOR_EXCEEDS_LIMIT")
        if region[i] < .999:
            raise FitRejected("E_ANCHOR_OUTSIDE_INTERIOR")
        anchors.append(before[i]); deltas.append(delta)
        if abs(before[i, 0]) > 1e-5:
            anchors.append(before[i] * [-1., 1., 1.])
            deltas.append(delta * [-1., 1., 1.])
        elif abs(delta[0]) > 1e-6:
            raise FitRejected("E_MIDLINE_LATERAL_DISPLACEMENT")
    p, d = np.array(anchors), np.array(deltas)
    pair = p[:, None, :] - p[None, :, :]
    K = np.exp(-np.sum(pair * pair, axis=-1) / (2 * radius * radius))
    cond = float(np.linalg.cond(K))
    if not np.isfinite(cond) or cond > 1e9:
        raise FitRejected("E_ILL_CONDITIONED_ANCHORS")
    w = np.linalg.solve(K, d)
    out = np.empty_like(before)
    for start in range(0, len(before), 4096):
        part = before[start:start + 4096]
        dist = part[:, None, :] - p[None, :, :]
        kernel = np.exp(-np.sum(dist * dist, axis=-1) / (2 * radius * radius))
        out[start:start + 4096] = part + (kernel @ w) * region[start:start + 4096, None]
    displacement = np.linalg.norm(out - before, axis=1)
    if not np.isfinite(out).all() or displacement.max() > limit + 1e-9:
        raise FitRejected("E_INTERPOLATION_OVERSHOOT")
    errors = [float(np.linalg.norm(out[a["vertex_index"]] - a["target_m"])) for a in controls]
    if max(errors) > 1e-4:
        raise FitRejected("E_ANCHOR_RESIDUAL")
    face_report = _face_safety(before, out, faces)
    return out, {
        "schema": "livynth.c001.stage1.fit-report.v1",
        "status": "GEOMETRY_ONLY_FEASIBILITY_NOT_IDENTITY",
        "source_positions_sha256": source["positions_sha256"],
        "output_positions_sha256": positions_sha256(out),
        "vertex_count": len(before),
        "anchor_count": len(controls),
        "mirrored_rbf_control_count": len(p),
        "anchor_residual_max_m": max(errors),
        "max_displacement_m": float(displacement.max()),
        "changed_vertices": int((displacement > 1e-7).sum()),
        "condition_number": cond,
        "self_intersection": "UNVERIFIED",
        "appearance_likeness": "UNVERIFIED",
        "rig_after_target_bake": "UNVERIFIED",
        **face_report,
    }


def load_spec(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
