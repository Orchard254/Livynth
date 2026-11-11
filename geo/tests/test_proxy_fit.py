"""C001-GEO-01 numerical and topology regression tests (optional deps)."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from geo.proxy_fit import read_profile, mesh_from_profiles, Profile


class SilhouetteTests(unittest.TestCase):
    @staticmethod
    def synthetic(n, span=.52):
        return Profile("test", Path("fake.png"), 1000, 1000, 10, 800,
                       np.zeros(n), np.full(n, span), "testhash")

    def test_synthetic_background_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.png"
            im = Image.new("RGB", (650, 850), (135, 135, 135))
            ImageDraw.Draw(im).ellipse((150, 80, 490, 760), fill=(205, 138, 105))
            im.save(path)
            profile = read_profile(path, "front", 85, 750, steps=37)
            self.assertEqual(profile.width, 650)
            self.assertLess(profile.uleft[15], profile.uright[15])
            self.assertGreater(profile.uright[18] - profile.uleft[18], .45)

    def test_rejects_thumbnail(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "small.png"
            Image.new("RGB", (300, 400), (135, 135, 135)).save(path)
            with self.assertRaisesRegex(ValueError, "thumbnail"):
                read_profile(path, "x", 20, 350)

    def test_nonuniform_profile_samples_rejected(self):
        p = self.synthetic(33)
        with self.assertRaisesRegex(ValueError, "counts differ"):
            mesh_from_profiles(p, self.synthetic(34), p)

    def test_closed_hull_and_repeatability(self):
        import trimesh
        p = self.synthetic(51)
        v, f, m = mesh_from_profiles(p, p, p, sides=32)
        self.assertEqual(len(v), 51 * 32 + 2)
        self.assertEqual(len(f), (51 - 1) * 32 * 2 + 32 * 2)
        mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
        self.assertTrue(mesh.is_watertight)
        vv, ff, mm = mesh_from_profiles(p, p, p, sides=32)
        np.testing.assert_array_equal(v, vv)
        np.testing.assert_array_equal(f, ff)
        self.assertEqual(m, mm)

    def test_invalid_sides_rejected(self):
        p = self.synthetic(51)
        with self.assertRaises(ValueError):
            mesh_from_profiles(p, p, p, sides=11)
        with self.assertRaises(ValueError):
            mesh_from_profiles(p, p, p, sides=18)

    def test_profile_disagreement_reported(self):
        p = self.synthetic(51)
        narrow = self.synthetic(51, span=.31)
        _, _, metrics = mesh_from_profiles(p, p, narrow)
        self.assertGreater(
            metrics["median_LR_profile_depth_disagreement_fraction"], .1)


if __name__ == "__main__":
    unittest.main()
