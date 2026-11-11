"""Opt-in C001-GEO-05 bridge: fit the baked MPFB neutral BEFORE face targets.

Never call after FaceService.load_targets. No network, renderer or image access.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geo.stage1_fit import FitRejected, SCHEMA, positions_sha256, propose_fit, load_spec


def _geometry(mesh_object):
    if mesh_object is None or mesh_object.type != "MESH":
        raise FitRejected("E_NOT_MESH")
    mesh = mesh_object.data
    if len(mesh.vertices) < 4:
        raise FitRejected("E_EMPTY_BASEMESH")
    if any(len(poly.vertices) != 4 for poly in mesh.polygons):
        raise FitRejected("E_QUAD_BASEMESH_REQUIRED")
    if mesh.shape_keys and len(mesh.shape_keys.key_blocks) > 1:
        raise FitRejected("E_EXISTING_SHAPE_TARGETS")
    xyz = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
    faces = np.array([tuple(p.vertices) for p in mesh.polygons], dtype=np.int64)
    return xyz, faces


def write_template(mesh_object, destination):
    """Write an intentionally NON-RUNNABLE specification to review and complete."""
    xyz, faces = _geometry(mesh_object)
    doc = {
        "schema": SCHEMA,
        "source": {
            "vertex_count": len(xyz),
            "positions_sha256": positions_sha256(xyz),
            "quad_face_count": len(faces),
            "mesh_object": mesh_object.name,
        },
        "reference_calibrated": False,
        "input_kind": "MANUALLY_REVIEWED_3D_CONSTRAINTS",
        "radius_m": .035,
        "max_displacement_m": .02,
        "region": {"axis": "z", "min_m": None, "max_m": None, "taper_m": None},
        "anchors": [],
        "_instructions": (
            "INCOMPLETE: review anatomical camera/3D target assumptions, set "
            "region bounds and list 3D anchors. Each anchor must have "
            "vertex_index, target_m:[x,y,z], name and basis:'MANUAL_3D_ESTIMATE'. "
            "2D image pixels are NOT 3D targets. Remove this note after review."
        ),
    }
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {"template": str(path), "vertex_count": len(xyz),
            "source_positions_sha256": doc["source"]["positions_sha256"],
            "stage1": "NOT_RUN"}


def apply_constraints(mesh_object, specification_path):
    """Validate completely before making ANY edit to the Blender mesh."""
    old, faces = _geometry(mesh_object)
    spec = load_spec(specification_path)
    new, report = propose_fit(old, spec, faces)
    mesh = mesh_object.data
    current = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float64)
    if positions_sha256(current) != report["source_positions_sha256"]:
        raise FitRejected("E_MESH_MUTATED_DURING_VALIDATION")
    for i, vertex in enumerate(mesh.vertices):
        vertex.co = new[i].tolist()
    if mesh.shape_keys:
        basis = mesh.shape_keys.key_blocks[0]
        for i, keypoint in enumerate(basis.data):
            keypoint.co = new[i].tolist()
    mesh.update()
    return report
