"""Read-only C001-GEO-05 diagnostic export of MPFB's *baked neutral* mesh.

Run only after ExportService.bake_modifiers_remove_helpers and before the
ARKit/Meta target loading. This saves original Blender vertex indices; a GLB
cannot substitute because its export duplicates vertices at attribute seams.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

import numpy as np

from stage1_blender_bridge import _geometry
from geo.stage1_fit import FitRejected, positions_sha256

SCHEMA = "livynth.c001.stage1.neutral-mesh.v1"


def write_neutral_dump(mesh_object, destination):
    """Save positions and quad indices plus auditable metadata without editing mesh.

    This archive contains *geometry only*. It contains no original portrait,
    appearance texture, training data, fitted landmarks or identity assertion.
    """
    dest = Path(destination)
    if dest.suffix.lower() != ".npz":
        raise FitRejected("E_NEUTRAL_DUMP_SUFFIX_NPZ_REQUIRED")
    xyz, faces = _geometry(mesh_object)
    if not (len(xyz) and len(faces)):
        raise FitRejected("E_NEUTRAL_DUMP_EMPTY")
    xyz = np.ascontiguousarray(xyz, dtype="<f8")
    faces = np.ascontiguousarray(faces, dtype="<i4")
    source_hash = positions_sha256(xyz)
    metadata = {
        "schema": SCHEMA,
        "stage1": "NOT_RUN",
        "source": "MPFB_BAKED_NEUTRAL_BEFORE_FACE_TARGETS",
        "coordinate_space": "Blender mesh local space; coordinates as stored",
        "mesh_object": mesh_object.name,
        "vertex_count": int(xyz.shape[0]),
        "quad_face_count": int(faces.shape[0]),
        "positions_sha256": source_hash,
        "bounds_min": xyz.min(axis=0).tolist(),
        "bounds_max": xyz.max(axis=0).tolist(),
        "notes": "3D vertex indices only; no image-to-vertex correspondence inferred",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=".npz", delete=False) as fh:
            tmp = Path(fh.name)
            np.savez_compressed(
                fh, vertices=xyz, quads=faces,
                metadata_utf8=np.frombuffer(json.dumps(metadata, sort_keys=True).encode("utf-8"), dtype=np.uint8),
            )
        with np.load(tmp, allow_pickle=False) as audit:
            if set(audit.files) != {"vertices", "quads", "metadata_utf8"}:
                raise FitRejected("E_NEUTRAL_DUMP_CONTENTS")
            if positions_sha256(audit["vertices"]) != source_hash or not np.array_equal(audit["quads"], faces):
                raise FitRejected("E_NEUTRAL_DUMP_ROUNDTRIP")
        os.replace(tmp, dest)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()
    return {"archive": str(dest), "stage1": "NOT_RUN", "vertex_count": int(len(xyz)),
            "quad_face_count": int(len(faces)), "positions_sha256": source_hash,
            "bounds_min": metadata["bounds_min"], "bounds_max": metadata["bounds_max"]}
