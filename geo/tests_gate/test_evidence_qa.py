"""Synthetic evidence-quality regressions; no Blender or private images required."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from geo.gate.evidence_qa import audit_wireframe


class WireframeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "wireframe_front.png"

    def tearDown(self):
        self.temp.cleanup()

    def write_image(self, pixels):
        Image.fromarray(pixels, "RGBA").save(self.path)
        return audit_wireframe(self.path)

    def test_readable_black_wire_on_opaque_light_background_passes(self):
        pixels = np.full((128, 128, 4), [210, 210, 210, 255], dtype=np.uint8)
        pixels[:, ::8, :3] = 0
        self.assertTrue(self.write_image(pixels)["ok"])

    def test_transparent_black_wire_fails(self):
        pixels = np.zeros((128, 128, 4), dtype=np.uint8)
        pixels[::8, :, 3] = 255
        result = self.write_image(pixels)
        self.assertIn("transparent_or_missing_backdrop", result["errors"])

    def test_all_black_fails(self):
        pixels = np.full((128, 128, 4), [0, 0, 0, 255], dtype=np.uint8)
        self.assertIn("no_light_backdrop", self.write_image(pixels)["errors"])

    def test_all_light_no_wire_fails(self):
        pixels = np.full((128, 128, 4), [200, 200, 200, 255], dtype=np.uint8)
        self.assertIn("no_visible_dark_wire_edges", self.write_image(pixels)["errors"])

    def test_one_black_pixel_is_not_a_wireframe(self):
        pixels = np.full((128, 128, 4), [210, 210, 210, 255], dtype=np.uint8)
        pixels[64, 64, :3] = 0
        self.assertFalse(self.write_image(pixels)["ok"])

    def test_invalid_png_fails_closed(self):
        self.path.write_bytes(b"invalid PNG")
        self.assertIn("image_unreadable", audit_wireframe(self.path)["errors"])


if __name__ == "__main__":
    unittest.main()
