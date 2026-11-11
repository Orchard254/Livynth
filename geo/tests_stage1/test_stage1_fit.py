"""Synthetic C001-GEO-05 tests. PASS is not a Character 001 likeness claim."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from geo.stage1_fit import (
    FitRejected, SCHEMA, _face_safety, positions_sha256, propose_fit,
)
from tools.stage1_blender_bridge import _geometry, write_template


class Stage1FitTests(unittest.TestCase):
    def setUp(self):
        x = np.linspace(-.07, .07, 15)
        z = np.linspace(0, .18, 19)
        xx, zz = np.meshgrid(x, z)
        self.v = np.stack([xx.ravel(), np.zeros(xx.size), zz.ravel()], axis=1)
        self.mid, self.side = 9 * 15 + 7, 9 * 15 + 10
        self.spec = {
            "schema": SCHEMA,
            "source": {"vertex_count": len(self.v), "positions_sha256": positions_sha256(self.v)},
            "reference_calibrated": False,
            "input_kind": "MANUALLY_REVIEWED_3D_CONSTRAINTS",
            "radius_m": .035, "max_displacement_m": .022,
            "region": {"axis": "z", "min_m": 0., "max_m": .18, "taper_m": .02},
            "anchors": [{
                "vertex_index": self.side,
                "target_m": (self.v[self.side] + [.004, .004, 0]).tolist(),
                "name": "cheek", "basis": "MANUAL_3D_ESTIMATE",
            }],
        }

    def test_anchor_pin_and_unaffected_boundary(self):
        out, r = propose_fit(self.v, self.spec)
        self.assertLess(r["anchor_residual_max_m"], 1e-4)
        np.testing.assert_array_equal(out[0], self.v[0])
        self.assertLess(r["max_displacement_m"], .022)
        self.assertEqual(r["self_intersection"], "UNVERIFIED")
        self.assertEqual(r["appearance_likeness"], "UNVERIFIED")

    def test_mirror_symmetry(self):
        out, _ = propose_fit(self.v, self.spec)
        np.testing.assert_allclose(out[9 * 15 + 4, 0], -out[self.side, 0], atol=1e-10)
        np.testing.assert_allclose(out[9 * 15 + 4, 1:], out[self.side, 1:], atol=1e-10)

    def test_stale_basemesh_rejected(self):
        x = self.v.copy()
        x[0, 0] += .001
        with self.assertRaisesRegex(FitRejected, "E_SOURCE_MISMATCH"):
            propose_fit(x, self.spec)

    def test_image_points_not_accepted_as_3d(self):
        self.spec["input_kind"] = "IMAGE_LANDMARKS_2D"
        with self.assertRaisesRegex(FitRejected, "E_3D_CONSTRAINTS_REQUIRED"):
            propose_fit(self.v, self.spec)

    def test_oversized_anchor_rejected(self):
        self.spec["anchors"][0]["target_m"][0] += .05
        with self.assertRaisesRegex(FitRejected, "E_ANCHOR_EXCEEDS_LIMIT"):
            propose_fit(self.v, self.spec)

    def test_duplicate_indices_rejected(self):
        self.spec["anchors"].append(dict(self.spec["anchors"][0]))
        with self.assertRaisesRegex(FitRejected, "E_ANCHOR_VERTEX"):
            propose_fit(self.v, self.spec)

    def test_edge_anchor_rejected(self):
        self.spec["anchors"][0]["vertex_index"] = 2
        self.spec["anchors"][0]["target_m"] = self.v[2].tolist()
        with self.assertRaisesRegex(FitRejected, "E_ANCHOR_OUTSIDE_INTERIOR"):
            propose_fit(self.v, self.spec)

    def test_midline_lateral_move_rejected(self):
        self.spec["anchors"][0]["vertex_index"] = self.mid
        self.spec["anchors"][0]["target_m"] = (self.v[self.mid] + [.003, 0, 0]).tolist()
        with self.assertRaisesRegex(FitRejected, "E_MIDLINE_LATERAL_DISPLACEMENT"):
            propose_fit(self.v, self.spec)

    def test_nonfinite_vertices_rejected(self):
        x = self.v.copy()
        x[0, 0] = np.nan
        with self.assertRaises(FitRejected):
            propose_fit(x, self.spec)

    def test_missing_anchor_rejected(self):
        self.spec["anchors"] = []
        with self.assertRaisesRegex(FitRejected, "E_ANCHORS_COUNT"):
            propose_fit(self.v, self.spec)

    def test_source_not_mutated_when_fit_fails(self):
        original = self.v.copy()
        self.spec["source"]["vertex_count"] += 1
        with self.assertRaises(FitRejected):
            propose_fit(self.v, self.spec)
        np.testing.assert_array_equal(self.v, original)

    def test_face_flip_rejected(self):
        a = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0, 1, 0]])
        b = a.copy()
        b[2] = [0., -1, 0.]
        with self.assertRaisesRegex(FitRejected, "E_FACE_COLLAPSE_OR_FLIP"):
            _face_safety(a, b, np.array([[0, 1, 2, 3]]))

    def test_valid_quad_local_check(self):
        a = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0, 1, 0]])
        b = a.copy()
        b[2, 2] = .05
        self.assertEqual(_face_safety(a, b, np.array([[0, 1, 2, 3]]))["face_check"],
                         "PASS_LOCAL_NONFLIP_ONLY")

    def test_topology_face_count_must_match(self):
        self.spec["source"]["quad_face_count"] = 5
        with self.assertRaisesRegex(FitRejected, "E_TOPOLOGY_COUNT_MISMATCH"):
            propose_fit(self.v, self.spec, np.array([[0, 1, 2, 3]]))


class BridgeTests(unittest.TestCase):
    def test_template_is_not_a_fit(self):
        class Point:
            def __init__(self, co): self.co = co
        class Poly:
            vertices = (0, 1, 2, 3)
        class Mesh:
            vertices = [Point(x) for x in
                        ([0., 0, 0], [1., 0, 0], [1., 1, 0], [0, 1, 0])]
            polygons = [Poly()]
            shape_keys = None
        class Object:
            type = "MESH"
            name = "fixture"
            data = Mesh()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "template.json"
            result = write_template(Object(), path)
            spec = json.loads(path.read_text())
            self.assertEqual(result["stage1"], "NOT_RUN")
            self.assertEqual(spec["anchors"], [])
            with self.assertRaises(FitRejected):
                propose_fit(np.array([v.co for v in Object.data.vertices]), spec)

    def test_preexisting_face_morphs_rejected(self):
        class Poly:
            vertices = (0, 1, 2, 3)
        class Mesh:
            vertices = [object() for _ in range(4)]
            polygons = [Poly()]
            shape_keys = type("Keys", (), {"key_blocks": [1, 2]})()
        class Object:
            type = "MESH"
            data = Mesh()
        with self.assertRaisesRegex(FitRejected, "E_EXISTING_SHAPE_TARGETS"):
            _geometry(Object())


if __name__ == "__main__":
    unittest.main()
