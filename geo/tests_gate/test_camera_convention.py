"""C001-GEO-04 gate - camera convention tests.

The reviewer has to be able to reproduce the framing, so the camera
convention is pinned by tests: the analytic projection, the rasteriser and
the Blender camera placement must all agree.
"""

import math
import unittest

import numpy as np

from geo.gate import camera, raster


class CameraConventionTests(unittest.TestCase):
    def test_projection_matches_the_documented_formula(self):
        view = {"phi": 37.0, "s": 3546.9387755102043, "cx": 543.0, "cy": 489.5}
        p = (0.03, 0.12, -0.02)
        u, v = camera.project_point(p, view)
        psi = math.radians(view["phi"])
        self.assertAlmostEqual(u, view["cx"] + view["s"] * (math.cos(psi) * p[0] + math.sin(psi) * p[2]), places=6)
        self.assertAlmostEqual(v, view["cy"] - view["s"] * p[1], places=6)

    def test_view_basis_is_orthonormal_and_right_handed(self):
        for phi in (-90.0, -45.0, 0.0, 45.0, 90.0, 180.0):
            right, up, fwd = raster.view_basis({"phi": phi})
            self.assertAlmostEqual(float(np.dot(right, up)), 0.0, places=9)
            self.assertAlmostEqual(float(np.dot(right, fwd)), 0.0, places=9)
            self.assertAlmostEqual(float(np.dot(up, fwd)), 0.0, places=9)
            self.assertAlmostEqual(float(np.linalg.norm(right)), 1.0, places=9)
            self.assertAlmostEqual(float(np.linalg.norm(up)), 1.0, places=9)
            self.assertAlmostEqual(float(np.linalg.norm(fwd)), 1.0, places=9)
            # the camera frame is (local X = right, local Y = up, local Z = -fwd)
            self.assertAlmostEqual(float(np.dot(np.cross(right, up), -fwd)), 1.0, places=9)

    def test_camera_position_sits_on_the_documented_ray(self):
        for phi in (-90.0, 0.0, 90.0):
            spec = camera.blender_camera({"phi": phi, "s": 3500.0, "cx": 543.0, "cy": 489.5},
                                         1086, 1448, (0.0, 0.0, 0.0), 0.25)
            psi = math.radians(phi)
            # the camera lies on the blender ray (-sin psi, -cos psi)
            loc = spec["location"]
            norm = math.hypot(loc[0], loc[1])
            self.assertGreater(norm, 0.0)
            self.assertAlmostEqual(loc[0] / norm, -math.sin(psi), places=6)
            self.assertAlmostEqual(loc[1] / norm, -math.cos(psi), places=6)
            self.assertAlmostEqual(spec["ortho_scale"], 1448.0 / 3500.0, places=9)

    def test_raster_bbox_matches_the_analytic_projection(self):
        view = {"phi": 0.0, "s": 3000.0, "cx": 543.0, "cy": 489.5}
        verts = np.array([[-0.05, -0.08, 0.0], [0.05, -0.08, 0.0],
                           [0.05, 0.08, 0.0], [-0.05, 0.08, 0.0],
                           [0.0, 0.0, 0.05]], dtype=np.float64)
        faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
        u, v, _ = raster.project(verts, view)
        analytic = [u.min(), v.min(), u.max(), v.max()]
        r = raster.rasterize(verts, faces, view, 1086, 1448)
        ys, xs = np.nonzero(r["mask"])
        self.assertTrue(len(xs) > 0)
        got = [xs.min(), ys.min(), xs.max(), ys.max()]
        for a, g in zip(analytic, got):
            self.assertLess(abs(a - g), 2.0)

    def test_depth_increases_away_from_the_camera(self):
        view = {"phi": 0.0, "s": 3000.0, "cx": 543.0, "cy": 489.5}
        near = camera.project_depth((0.0, 0.0, 0.1), view)
        far = camera.project_depth((0.0, 0.0, 0.0), view)
        self.assertLess(near, far)

    def test_reference_views_json_is_self_consistent(self):
        cfg = camera.load_reference_views()
        self.assertIn("views", cfg)
        for name, v in cfg["views"].items():
            self.assertIn("phi", v)
            self.assertIn("s", v)
            self.assertIn("cx", v)
            self.assertIn("cy", v)
            self.assertGreater(v["s"], 0.0)


if __name__ == "__main__":
    unittest.main()
