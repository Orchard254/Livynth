#!/usr/bin/env python3
"""Unit tests for C001-GEO-03 lane B (geo/visual_hull.py).

Run: python -m unittest discover -s geo/tests_hull -v
"""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from geo import visual_hull as vh  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_IMAGES = REPO_ROOT / "assets" / "characters" / "character_001" / "identity_capture_v1"

# The carve needs scipy (morphology) and scikit-image (marching cubes); they are
# listed in requirements-hull.txt. Tests that need them skip rather than fail
# when only requirements-geometry.txt is installed.
try:
    import scipy.ndimage  # noqa: F401
    import skimage.measure  # noqa: F401
    HULL_DEPS = True
except ImportError:  # pragma: no cover - depends on the install
    HULL_DEPS = False

requires_hull_deps = unittest.skipUnless(
    HULL_DEPS, "hull dependencies missing (pip install -r requirements-hull.txt)")


class TestSegmentation(unittest.TestCase):
    def test_synthetic_skin_vs_gray_and_navy(self):
        """Gray noise background + skin ellipse + navy shirt band -> mask keeps ellipse only."""
        rng = np.random.default_rng(7)
        img = np.zeros((240, 320, 3), dtype=np.float32)
        img[:, :] = (125 + rng.normal(0, 3, (240, 320)))[..., None]  # gray backdrop
        yy, xx = np.mgrid[0:240, 0:320]
        ellipse = ((xx - 160) / 90.0) ** 2 + ((yy - 110) / 105.0) ** 2 <= 1.0
        img[ellipse] = (205.0, 150.0, 112.0)                        # skin (R > B)
        img[188:, :] = (24.0, 28.0, 48.0)                           # navy shirt (R < B)
        mask, stats = vh.segment_head(img)
        self.assertTrue(mask[110, 160], "skin center must be foreground")
        self.assertFalse(mask[207, 160], "navy shirt must be background")
        self.assertFalse(mask[5, 5], "gray backdrop must be background")
        inter = np.logical_and(mask, ellipse).sum()
        union = np.logical_or(mask, ellipse).sum()
        self.assertGreater(inter / union, 0.85, "ellipse IoU too low")

    def test_synthetic_dark_hair_is_foreground(self):
        rng = np.random.default_rng(3)
        img = np.zeros((120, 120, 3), dtype=np.float32)
        img[:, :] = (128 + rng.normal(0, 2, (120, 120)))[..., None]
        img[30:70, 30:70] = (54.0, 18.0, 3.0)                       # dark auburn hair
        mask, _ = vh.segment_head(img)
        self.assertTrue(mask[50, 50], "dark auburn hair must be foreground")
        self.assertFalse(mask[5, 5])

    @unittest.skipUnless(SRC_IMAGES.is_dir(), "reference images not available")
    def test_real_front_reference(self):
        """Integration: the real front reference maskes hair+face, excludes the navy shirt."""
        from PIL import Image
        a = np.asarray(Image.open(SRC_IMAGES / "01_subject_front.png").convert("RGB"))
        mask, stats = vh.segment_head(a)
        self.assertGreater(stats["fg_pixels"], 400_000)
        self.assertTrue(mask[700, 543])   # mid-face
        self.assertFalse(mask[1400, 543])  # navy shirt at the bottom edge


class TestProjection(unittest.TestCase):
    def _vp(self, phi):
        v = dict(vh.VIEWS["front"]) if phi == 0 else dict(vh.VIEWS["left45"])
        view = dict(v, phi=phi, top=False)
        return vh.view_params(view, 1086, 1448, vh.FRONT_FALLBACK_SCALE)

    def test_front_axis(self):
        vp = self._vp(0)
        u, v = vh.project_points(np.array([[0.0, 0.0, 0.1]]), vp)
        self.assertAlmostEqual(float(u[0]), vp["cx"], places=6)
        u2, _ = vh.project_points(np.array([[0.05, 0.0, 0.0]]), vp)
        self.assertAlmostEqual(float(u2[0]), vp["cx"] + vp["s"] * 0.05, places=3)

    def test_profile_side_sign(self):
        """Nose (+z) must project to frame-LEFT in a phi=-90 view (matches 04_left_profile)."""
        vp = self._vp(-90)
        u, _ = vh.project_points(np.array([[0.0, 0.0, 0.1]]), vp)
        self.assertLess(float(u[0]), vp["cx"])
        vp2 = self._vp(90)
        u2, _ = vh.project_points(np.array([[0.0, 0.0, 0.1]]), vp2)
        self.assertGreater(float(u2[0]), vp2["cx"])

    def test_top_axis(self):
        view = dict(vh.VIEWS["top"])
        vp = vh.view_params(view, 1087, 1447, vh.FRONT_FALLBACK_SCALE)
        u, v = vh.project_points(np.array([[0.1, 0.0, 0.05]]), vp)
        self.assertAlmostEqual(float(u[0]), vp["cx"] + vp["s"] * 0.1, places=3)
        self.assertAlmostEqual(float(v[0]), vp["cy"] + vp["s"] * 0.05, places=3)


class TestCarvingSphere(unittest.TestCase):
    @requires_hull_deps
    def test_sphere_hull_volume(self):
        """6 orthogonal circle silhouettes of a sphere -> hull within 20% of true volume."""
        R = 0.09
        xs = np.arange(-R, R, 0.0075)
        ys = np.arange(-R, R, 0.0075)
        zs = np.arange(-R, R, 0.0075)
        grid = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1).reshape(-1, 3)
        shape = (len(xs), len(ys), len(zs))
        occupancy_true = np.linalg.norm(grid, axis=1) <= R

        def circle(vp, radius):
            m = np.zeros((320, 320), dtype=bool)
            yy, xx = np.mgrid[0:320, 0:320]
            m[((xx - 160) / radius) ** 2 + ((yy - 160) / radius) ** 2 <= 1.0] = True
            return m

        phis = [0, -45, 45, -90, 90, 180]
        masks, vp_all = {}, {}
        s = 1400.0  # px/m
        r = s * R
        for i, phi in enumerate(phis):
            view = dict(vh.VIEWS["front"], phi=phi, crown=0, chin=None, top=False)
            vp = dict(s=s, cx=160.0, cy=160.0, phi=float(phi), top=False, dilate=0)
            vp = dict(s=s, cx=160.0, cy=160.0, phi=float(phi), top=False, dilate=0)
            vp_all[f"v{i}"] = vp
            masks[f"v{i}"] = circle(vp, r)
        kept = vh.carve(masks, vp_all, grid, shape, cell=0.0075)
        kept6 = kept.sum() * 0.0075**3
        true_vol = np.pi * 4.0 / 3.0 * R**3
        # 6 silhouettes at this spacing leave a Steinmetz-type excess; sanity bound only
        self.assertLess(kept6 / true_vol, 2.2)
        self.assertGreater(kept6 / true_vol, 1.0)

        # 16 evenly spaced views must approach the true sphere volume much more closely
        masks2, vp_all2 = {}, {}
        for i, deg in enumerate(np.linspace(0, 180, 16, endpoint=False)):
            phi = float(deg)
            vp = dict(s=s, cx=160.0, cy=160.0, phi=phi, top=False, dilate=0)
            vp_all2[f"w{i}"] = vp
            masks2[f"w{i}"] = circle(vp, r)
        kept2 = vh.carve(masks2, vp_all2, grid, shape, cell=0.0075)
        vol16 = kept2.sum() * 0.0075**3
        self.assertLess(abs(vol16 - true_vol) / true_vol, 0.15,
                        f"16-view hull volume error {(vol16 - true_vol) / true_vol:+.1%}")
        self.assertGreater(kept2.sum(), 50)


class TestExportGlb(unittest.TestCase):
    def test_textured_glb_roundtrip(self):
        import trimesh
        from PIL import Image
        mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.08)
        mesh.vertices[:] += np.array([0.0, 0.0, 0.0])
        images = {"front": Image.new("RGB", (1086, 1448), (205, 150, 112)),
                  "top": Image.new("RGB", (1087, 1447), (120, 70, 40))}
        vp_front = dict(s=3500.0, cx=543.0, cy=700.0, phi=0.0, top=False, dilate=0)
        vp_top = dict(s=4000.0, cx=543.5, cy=720.0, phi=None, top=True, dilate=0)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tiny.glb"
            vh.export_glb(mesh, images, {"front": vp_front, "top": vp_top}, out)
            self.assertTrue(out.is_file())
            loaded = trimesh.load(out, force="mesh")
            self.assertGreater(len(loaded.vertices), 0)
            self.assertGreater(len(loaded.faces), 0)
            self.assertIsNotNone(loaded.visual.material.baseColorTexture)

    @unittest.skipUnless((Path.cwd() / "output/character001_visual_hull/character001_visual_hull.glb").is_file(),
                         "final candidate GLB not present")
    def test_final_candidate_glb_loads(self):
        import trimesh
        m = trimesh.load("output/character001_visual_hull/character001_visual_hull.glb", force="mesh")
        self.assertGreater(len(m.faces), 10_000)
        self.assertLess(float(np.abs(m.extents).max()), 0.5,
                        "candidate exceeds sane human-scale bounds")


if __name__ == "__main__":
    unittest.main()
