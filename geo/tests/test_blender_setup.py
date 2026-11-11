"""Preflight checks for Blender workspace script. Does not require Blender."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stderr
from io import StringIO
from geo.setup_blender_fit_scene import CAMERAS, arguments, pick_face_mesh


class BlenderSetupPreflightTests(unittest.TestCase):
    def test_camera_views_have_unique_angles_and_sources(self):
        self.assertEqual(len(CAMERAS), 5)
        self.assertEqual({view[2] for view in CAMERAS}, {0, -45, 45, -90, 90})
        self.assertEqual(len({view[1] for view in CAMERAS}), 5)

    def test_requires_model_and_five_reference_images(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "avatar.glb").touch()
            (root / "photos").mkdir()
            args = ["--glb", str(root / "avatar.glb"),
                    "--images", str(root / "photos")]
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                arguments(args)
            for _, name, _ in CAMERAS:
                (root / "photos" / name).touch()
            result = arguments(args)
            self.assertEqual(result.front, "negative-y")

    def test_bad_output_extension_and_scale_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "avatar.glb").touch()
            (root / "photos").mkdir()
            for _, name, _ in CAMERAS:
                (root / "photos" / name).touch()
            common = ["--glb", str(root / "avatar.glb"),
                      "--images", str(root / "photos")]
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                arguments(common + ["--out", "wrong.json"])
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                arguments(common + ["--frame-height", "0.9"])

    def test_morphable_head_mesh_preferred(self):
        def mesh(name, names):
            keys = (SimpleNamespace(key_blocks=[
                SimpleNamespace(name=x) for x in names]) if names else None)
            return SimpleNamespace(name=name, data=SimpleNamespace(shape_keys=keys))
        head = mesh("face", ["eyeBlinkLeft", "eyeBlinkRight",
                             "jawOpen", "mouthSmileLeft"])
        eyes = mesh("eyes", [])
        brows = mesh("brows", ["eyeBlinkLeft"])
        self.assertIs(pick_face_mesh([eyes, brows, head]), head)

    def test_empty_import_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "No meshes"):
            pick_face_mesh([])


if __name__ == "__main__":
    unittest.main()
