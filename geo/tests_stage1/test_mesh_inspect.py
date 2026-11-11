"""Synthetic negative/control cases for the offline native-mesh explorer."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from stage1_mesh_inspect import (InvalidNeutralMesh, SCHEMA, _xyz_hash,
                                 load_and_validate, topology_stats, write_outputs)


CUBE = np.array([
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
], dtype='<f8')
QUADS = np.array([
    [0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
    [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
], dtype='<i4')


def synthetic_archive(path, *, points=None, quads=None, modify_meta=None):
    points = CUBE if points is None else points
    quads = QUADS if quads is None else quads
    meta = dict(
        schema=SCHEMA, stage1='NOT_RUN', source='MPFB_BAKED_NEUTRAL_BEFORE_FACE_TARGETS',
        vertex_count=len(points), quad_face_count=len(quads),
        positions_sha256=_xyz_hash(points),
        bounds_min=np.min(points, axis=0).tolist(),
        bounds_max=np.max(points, axis=0).tolist(),
    )
    if modify_meta:
        modify_meta(meta)
    np.savez_compressed(path, vertices=points, quads=quads,
                        metadata_utf8=np.frombuffer(json.dumps(meta).encode(), dtype=np.uint8))
    return meta


class MeshInspectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'test.npz'

    def test_valid_archive_and_atlas(self):
        meta = synthetic_archive(self.path)
        result = write_outputs(self.path, self.path.parent / 'atlas', expected_sha=meta['positions_sha256'])
        report = json.loads(result[0].read_text(encoding='utf-8'))
        html = result[1].read_text(encoding='utf-8')
        self.assertEqual(report['stage1'], 'NOT_RUN')
        self.assertEqual(report['topology']['connected_face_components'], 1)
        self.assertEqual(report['topology']['boundary_edges'], 0)
        self.assertEqual(report['topology']['nonmanifold_edges'], 0)
        self.assertIn('data-view="py"', html)
        self.assertIn('Camera −X', html)
        self.assertIn('charset="utf-8"', html)
        self.assertIn('Camera −X'.encode('utf-8'), result[1].read_bytes())
        self.assertIn(meta['positions_sha256'], html)
        self.assertEqual(report['diagnostic_upper_z_crop']['semantic_anatomy'], 'NOT_INFERRED')
        self.assertEqual(report['identity_likeness'], 'UNVERIFIED')

    def test_reject_incorrect_expected_sha(self):
        synthetic_archive(self.path)
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_EXPECTED_SHA_MISMATCH'):
            load_and_validate(self.path, expected_sha='0'*64)

    def test_reject_tampered_sha(self):
        synthetic_archive(self.path, modify_meta=lambda m: m.update(positions_sha256='x'*64))
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_METADATA_MISMATCH'):
            load_and_validate(self.path)

    def test_reject_tampered_vertex_count(self):
        synthetic_archive(self.path, modify_meta=lambda m: m.update(vertex_count=18))
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_METADATA_MISMATCH'):
            load_and_validate(self.path)

    def test_reject_tampered_bounds(self):
        synthetic_archive(self.path, modify_meta=lambda m: m.update(bounds_min=[100,100,100]))
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_BOUNDS_MISMATCH'):
            load_and_validate(self.path)

    def test_reject_nonfinite_points(self):
        points=CUBE.copy();points[0,0]=np.nan
        synthetic_archive(self.path, points=points)
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_VERTICES_NONFINITE_OR_DTYPE'):
            load_and_validate(self.path)

    def test_reject_invalid_quad_index(self):
        quads=QUADS.copy();quads[0,0]=99
        synthetic_archive(self.path, quads=quads)
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_QUADS_OUT_OF_RANGE'):
            load_and_validate(self.path)

    def test_reject_degenerate_quad(self):
        quads=QUADS.copy();quads[0,0]=quads[0,1]
        synthetic_archive(self.path, quads=quads)
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_DEGENERATE_QUAD_INDEX'):
            load_and_validate(self.path)

    def test_reject_non_neutral_status(self):
        synthetic_archive(self.path, modify_meta=lambda m: m.update(stage1='FITTED'))
        with self.assertRaisesRegex(InvalidNeutralMesh, 'E_METADATA_SOURCE_STATUS'):
            load_and_validate(self.path)

    def test_mesh_not_modified_by_inspector(self):
        synthetic_archive(self.path)
        original=self.path.read_bytes()
        write_outputs(self.path, self.path.parent/'view')
        self.assertEqual(original,self.path.read_bytes())

    def test_nonmanifold_edge_reported(self):
        faces=np.concatenate([QUADS, QUADS[:1]])
        stats=topology_stats(CUBE,faces)
        self.assertGreater(stats['nonmanifold_edges'],0)
        self.assertEqual(stats['global_self_intersection'],'UNVERIFIED')


if __name__=='__main__':
    unittest.main()
