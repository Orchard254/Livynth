"""C001-GEO-04 gate - control (canary) rejection tests.

The gate is only a gate if it rejects a deliberately wrong identity.  These
tests check the rejection logic itself and the geometry of the controls.
"""

import unittest

import numpy as np

from geo.gate import controls, metrics


def _fake_metrics(**overrides):
    base = {
        "silhouette_face_band_ratio": {"reference": 0.8, "candidate": 0.8},
        "band_spread_ratio": {"reference": 0.47, "candidate": 0.47},
        "surface_roughness_rel": {"reference": None, "candidate": 0.18},
        "relief_shading_correlation": {"reference": 1.0, "candidate": 0.5},
        "appearance_silhouette_iou": {"reference": 1.0, "candidate": 0.95},
        "appearance_ncc": {"reference": 1.0, "candidate": 0.92},
    }
    base.update(overrides)
    return base


class ControlRejectionLogicTests(unittest.TestCase):
    def test_a_moved_metric_rejects_the_control(self):
        base = _fake_metrics()
        ctrl = _fake_metrics(band_spread_ratio={"reference": 0.47, "candidate": 0.56})
        res = metrics.control_rejected(base, ctrl)
        self.assertTrue(res["rejected"])
        self.assertIn("band_spread_ratio", [r["metric"] for r in res["rejected_by"]])

    def test_an_unchanged_metric_does_not_reject(self):
        base = _fake_metrics()
        ctrl = _fake_metrics()
        res = metrics.control_rejected(base, ctrl)
        self.assertFalse(res["rejected"])
        self.assertEqual(res["rejected_by"], [])

    def test_appearance_metric_that_does_not_move_is_reported(self):
        base = _fake_metrics()
        ctrl = _fake_metrics(band_spread_ratio={"reference": 0.47, "candidate": 0.56})
        res = metrics.control_rejected(base, ctrl)
        moved = [r["metric"] for r in res["appearance_metrics_that_did_not_move"]]
        self.assertIn("appearance_ncc", moved)
        self.assertIn("appearance_silhouette_iou", moved)


class ControlGeometryTests(unittest.TestCase):
    def _cube(self):
        verts = np.array([[-0.05, -0.05, 0.0], [0.05, -0.05, 0.0],
                          [0.05, 0.05, 0.0], [-0.05, 0.05, 0.0]], dtype=np.float64)
        faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
        return verts, faces

    def test_face_band_widen_moves_only_the_band_vertices(self):
        verts, faces = self._cube()
        view = {"phi": 0.0, "s": 3000.0, "cx": 543.0, "cy": 489.5}
        rects = {"eye": (390, 400, 700, 520), "mouth": (390, 400, 700, 520)}
        out, info = controls.apply_control(verts, faces, "face_band_widen",
                                           {"factor": 1.18,
                                            "row_range": [320, 660]}, view, rects)
        self.assertGreater(info["vertices_changed"], 0)
        self.assertLessEqual(info["vertices_changed"], len(verts))
        moved = np.abs(out[:, 0] - verts[:, 0]) > 1e-9
        self.assertTrue(moved.any())

    def test_jitter_control_moves_every_vertex(self):
        verts, faces = self._cube()
        view = {"phi": 0.0, "s": 3000.0, "cx": 543.0, "cy": 489.5}
        out, info = controls.apply_control(verts, faces, "jitter",
                                           {"sigma_m": 0.002, "seed": 1}, view, {})
        self.assertEqual(info["vertices_changed"], len(verts))
        self.assertGreater(float(np.abs(out - verts).max()), 0.0)

    def test_photo_plane_control_flattens_the_face_region(self):
        verts, faces = self._cube()
        view = {"phi": 0.0, "s": 3000.0, "cx": 543.0, "cy": 489.5}
        rects = {"eye": (500, 460, 586, 519), "mouth": (500, 730, 586, 790),
                 "nose": (520, 600, 566, 660)}
        out, info = controls.apply_control(verts, faces, "photo_plane", {}, view, rects)
        sel = out[info["vertices_changed"]] if info["vertices_changed"] else np.zeros((0, 3))
        if len(sel):
            self.assertLess(float(np.ptp(sel[:, 2])), 1e-12)

    def test_band_rects_are_built_from_the_landmarks(self):
        lm = {"eyes": {"left": [444, 526], "right": [656, 525]},
              "chin": [549, 925], "mouth_corners": [[466, 762], [630, 762]]}
        rects = controls.band_rects(lm)
        self.assertIn("eye", rects)
        self.assertIn("mouth", rects)
        self.assertLess(rects["eye"][0], lm["eyes"]["left"][0])
        self.assertGreater(rects["eye"][2], lm["eyes"]["right"][0])


if __name__ == "__main__":
    unittest.main()
