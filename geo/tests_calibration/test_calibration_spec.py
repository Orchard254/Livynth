# LIVYNTH C001-GEO-03 — synthetic unit tests for geo/calibration_spec.py.
#
# Tests 1-15 use synthetic data only. Tests 16-17 verify SHA-256 digests and
# pixel dimensions against the REAL reference files, which live in the main
# repository checkout (not in this worktree, not in git). They skip with a
# clear reason when the images are unavailable; set LIVYNTH_MAIN_REPO to
# override the default main-repo path (C:\\PROJECT\\Livynth).
#
# Run from the repository root of THIS worktree:
#   python -m unittest discover -s geo/tests_calibration -v
# or with real-file verification:
#   set LIVYNTH_MAIN_REPO=C:\PROJECT\Livynth && python -m unittest discover -s geo/tests_calibration -v
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import geo.calibration_spec as cs  # noqa: E402

MAIN_REPO = Path(os.environ.get("LIVYNTH_MAIN_REPO", r"C:\PROJECT\Livynth"))
MAIN_IMAGES = MAIN_REPO / "assets" / "characters" / "character_001" / "identity_capture_v1"

# Regression guard: the exact digests measured 2026-11-11. If these literals
# and cs.MAIN_VIEW_SHA256 ever diverge, something was edited by accident.
EXPECTED_MAIN_VIEW_SHA256 = {
    "01_subject_front.png": "9d84f485883ce613d12d02d9f8f85e338ebe950d7248d522bf3117901eaed2dd",
    "02_subject_left_45.png": "86243d7eeb906fa955c95fe10341451256b116857b661549b8c3a11ed78030a9",
    "03_subject_right_45.png": "0f0c748a582763d4d9abf66130ea6a1759fb9e5c266f07580a03dd0b98e37a3a",
    "04_left_profile.png": "702eb69b4e3ddd9470a64c86e6c28e5ff9795c441b41d28e262001978597d1cd",
    "05_right_profile.png": "65101246912c969c55596bb97a5a3622001d10fc8497539b7d86844f0d863eba",
    "06_back_head.png": "8339543d8b383dfd17fbdb750d4df9ad2fa7526d5738899e598ecb7ef9bfd684",
    "07_top_head.png": "219cba0eb70144f0c7d8e0cc9cba33e3b98c568d97f7bc0dd2553eeb755f0b4a",
    "08_front_closeup.png": "af8e3a85043f7eb998a653da72885f73d255d8f9d2b04138d965bf2dc6b832cd",
}
EXPECTED_MAIN_VIEW_DIMENSIONS = {
    "01_subject_front.png": (1086, 1448),
    "02_subject_left_45.png": (1086, 1448),
    "03_subject_right_45.png": (1086, 1448),
    "04_left_profile.png": (1086, 1448),
    "05_right_profile.png": (1086, 1448),
    "06_back_head.png": (1086, 1448),
    "07_top_head.png": (1087, 1447),
    "08_front_closeup.png": (1087, 1446),
}


def make_view(**overrides):
    """A valid synthetic view; override fields as needed."""
    data = dict(
        view_id="T1",
        label="synthetic",
        image_file="synthetic.png",
        image_sha256="ab" * 32,
        width=800,
        height=1000,
        fx=2000.0,
        fy=2000.0,
        cx=400.0,
        cy=500.0,
        azimuth_deg=0.0,
        pitch_deg=0.0,
        radius_mm=1500.0,
        interocular_mm=63.0,
        focal_equivalent_mm=90.0,
        look_at_mm=(0.0, 0.0, 0.0),
        status={"intrinsics": "ASSUMED"},
        notes="synthetic test view",
    )
    data.update(overrides)
    return cs.ViewCalibration(**data)


def make_set(views=None, **overrides):
    views = views if views is not None else [make_view()]
    return cs.CalibrationSet(views=views, estimator="synthetic-test",
                             created="2026-11-11", **overrides)


class TestProjection(unittest.TestCase):
    def test_roundtrip_all_default_views(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        rng = np.random.default_rng(1234)
        pts = rng.normal(0.0, 60.0, size=(32, 3))  # ~head-sized cloud, mm
        for v in s.views:
            with self.subTest(view=v.view_id):
                px = v.project(pts)
                _, _, forward = v.camera_basis()
                rel = pts - v.camera_position()
                depth = rel @ forward
                back = np.array([v.unproject(p[0], p[1], d) for p, d in zip(px, depth)])
                np.testing.assert_allclose(back, pts, atol=1e-6)

    def test_projection_lands_inside_frame_for_head_points(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        pts = np.array([[0.0, 0.0, 0.0], [50.0, 30.0, -80.0], [-40.0, -20.0, 90.0]])
        for v in s.views:
            if v.view_id == "07":
                continue  # top view: head-centre crop framing not guaranteed
            px = v.project(pts)
            self.assertTrue(np.all(px[:, 0] >= 0) and np.all(px[:, 0] <= v.width))
            self.assertTrue(np.all(px[:, 1] >= 0) and np.all(px[:, 1] <= v.height))

    def test_unproject_then_project_is_identity(self):
        v = make_view()
        px, py, depth = 123.0, 456.0, 1500.0
        pt = v.unproject(px, py, depth)
        p2 = v.project(pt.reshape(1, 3))[0]
        np.testing.assert_allclose(p2, [px, py], atol=1e-9)

    def test_project_behind_camera_raises(self):
        v = make_view()
        with self.assertRaises(cs.CalibrationError):
            # front view camera sits at +z=1500 looking toward -z; a point at
            # z=+10000 is behind the camera (depth < 0)
            v.project(np.array([[0.0, 0.0, 10000.0]]))

    def test_pixel_ray_unit_and_forward(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        for v in s.views:
            origin, direction = v.pixel_ray(v.cx, v.cy)
            self.assertAlmostEqual(float(np.linalg.norm(direction)), 1.0, places=12)
            _, _, forward = v.camera_basis()
            self.assertGreater(float(np.dot(direction, forward)), 0.99)

    def test_camera_positions_on_assumed_circle(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        diag = 1500.0 * (2.0 ** 0.5) / 2.0
        expected = {"01": (0, 0, 1500), "02": (diag, 0, diag),
                    "03": (-diag, 0, diag), "04": (1500, 0, 0),
                    "05": (-1500, 0, 0), "06": (0, 0, -1500),
                    "07": (0, 1500, 0)}
        for view_id, want in expected.items():
            with self.subTest(view=view_id):
                np.testing.assert_allclose(s.view(view_id).camera_position(),
                                           np.array(want, dtype=float), atol=1e-6)

    def test_camera_basis_orthonormal_all_views(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        for v in s.views:
            right, up, forward = v.camera_basis()
            np.testing.assert_allclose(right @ up, 0.0, atol=1e-12)
            np.testing.assert_allclose(right @ forward, 0.0, atol=1e-12)
            np.testing.assert_allclose(up @ forward, 0.0, atol=1e-12)
            for vec in (right, up, forward):
                self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=12)


class TestDefaultSet(unittest.TestCase):
    def test_default_set_builds_valid(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        self.assertEqual(s.validate(), [])
        self.assertEqual([v.view_id for v in s.views],
                         ["01", "02", "03", "04", "05", "06", "07", "08"])
        az = {v.view_id: v.azimuth_deg for v in s.views}
        self.assertEqual(az["01"], 0.0)
        self.assertEqual(az["02"], 45.0)
        self.assertEqual(az["03"], -45.0)
        self.assertEqual(az["04"], 90.0)
        self.assertEqual(az["05"], -90.0)
        self.assertEqual(az["06"], 180.0)
        self.assertEqual(s.view("07").pitch_deg, -90.0)

    def test_embedded_hashes_match_literal_regression_guard(self):
        self.assertEqual(cs.MAIN_VIEW_SHA256, EXPECTED_MAIN_VIEW_SHA256)
        self.assertEqual(cs.MAIN_VIEW_DIMENSIONS, EXPECTED_MAIN_VIEW_DIMENSIONS)
        for name, digest in cs.MAIN_VIEW_SHA256.items():
            self.assertEqual(len(digest), 64)
            int(digest, 16)  # raises if not hex

    def test_every_set_carries_status_labels(self):
        s = cs.build_default_calibration_set(created="2026-11-11")
        for v in s.views:
            self.assertEqual(v.status.get("intrinsics"), "ASSUMED")
            self.assertEqual(v.status.get("azimuth_pitch"), "KNOWN_ASSUMED")
            self.assertEqual(v.status.get("image_sha256"), "MEASURED")
            self.assertEqual(v.status.get("dimensions"), "MEASURED")

    def test_scale_is_parameter_not_measured(self):
        v = make_view(interocular_mm=61.5)
        self.assertEqual(v.interocular_mm, 61.5)
        self.assertEqual(cs.mm_per_pixel_from_interocular(300.0), 63.0 / 300.0)
        with self.assertRaises(cs.CalibrationError):
            cs.mm_per_pixel_from_interocular(0.0)
        with self.assertRaises(cs.CalibrationError):
            cs.mm_per_pixel_from_interocular(300.0, 0.0)


class TestSchema(unittest.TestCase):
    def setUp(self):
        self.view = make_view()
        self.cs = make_set()

    def base_dict(self):
        return self.cs.to_dict()

    def test_json_roundtrip(self):
        text = self.cs.to_json(indent=2)
        back = cs.CalibrationSet.from_json(text)
        self.assertEqual(back.to_dict(), self.cs.to_dict())

    def test_save_and_load_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.cs.save_json(Path(tmp) / "cal" / "set.json")
            back = cs.CalibrationSet.load_json(p)
            self.assertEqual(back.view("T1").fx, self.view.fx)

    def test_schema_rejects_wrong_version(self):
        d = self.base_dict()
        d["schema_version"] = "0.9.0"
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_missing_top_level_key(self):
        d = self.base_dict()
        del d["views"]
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_unknown_top_level_key(self):
        d = self.base_dict()
        d["telemetry"] = {"a": 1}
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_unknown_view_key(self):
        d = self.base_dict()
        d["views"][0]["lens_distortion_k1"] = 0.01
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_nonpositive_fx(self):
        d = self.base_dict()
        d["views"][0]["fx"] = 0.0
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_negative_fy(self):
        d = self.base_dict()
        d["views"][0]["fy"] = -10.0
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_cy_out_of_bounds(self):
        d = self.base_dict()
        d["views"][0]["cy"] = 1000.5  # height is 1000
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_cx_out_of_bounds(self):
        d = self.base_dict()
        d["views"][0]["cx"] = -0.5
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_azimuth_not_in_allowed_set(self):
        d = self.base_dict()
        d["views"][0]["azimuth_deg"] = 30.0
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_pitch_not_in_allowed_set(self):
        d = self.base_dict()
        d["views"][0]["pitch_deg"] = 45.0
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_missing_hash(self):
        d = self.base_dict()
        del d["views"][0]["image_sha256"]
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_malformed_hash(self):
        d = self.base_dict()
        d["views"][0]["image_sha256"] = "not-a-hash"
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_short_hash(self):
        d = self.base_dict()
        d["views"][0]["image_sha256"] = "ab" * 16
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_duplicate_view_ids(self):
        d = self.base_dict()
        d["views"].append(json.loads(json.dumps(d["views"][0])))
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_dict(d)

    def test_schema_rejects_bad_json_text(self):
        with self.assertRaises(cs.CalibrationError):
            cs.CalibrationSet.from_json("{not json")

    def test_validate_collects_multiple_issues(self):
        v = make_view(fx=-1.0, azimuth_deg=30.0)
        issues = v.validate()
        self.assertGreaterEqual(len(issues), 2)

    def test_intrinsics_from_focal_long_lens(self):
        fx, fy = cs.intrinsics_from_focal(1086, 1448, 90.0)
        self.assertAlmostEqual(fx, 4072.5)
        self.assertAlmostEqual(fy, 4072.5)
        with self.assertRaises(cs.CalibrationError):
            cs.intrinsics_from_focal(1086, 1448, 0.0)

    def test_verify_image_hashes_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic.png"
            p.write_bytes(b"fake png bytes for hash test")
            expected = hashlib.sha256(p.read_bytes()).hexdigest()
            v = make_view(image_file="synthetic.png", image_sha256=expected)
            s = make_set(views=[v])
            res = s.verify_image_hashes(tmp)
            self.assertEqual(res, [("T1", True, expected, expected)])
            # Tamper with the file -> mismatch reported, not raised
            p.write_bytes(b"tampered")
            res = s.verify_image_hashes(tmp)
            self.assertEqual(res[0][1], False)
            # Missing file -> reported as missing
            (Path(tmp) / "synthetic.png").unlink()
            res = s.verify_image_hashes(tmp)
            self.assertEqual(res[0][3], "<missing>")

    def test_verify_real_files_sha256(self):
        if not MAIN_IMAGES.is_dir():
            self.skipTest(f"reference images not found at {MAIN_IMAGES} "
                          f"(set LIVYNTH_MAIN_REPO to override)")
        s = cs.build_default_calibration_set(created="2026-11-11")
        results = s.verify_image_hashes(MAIN_IMAGES)
        self.assertEqual(len(results), 8)
        for view_id, ok, expected, actual in results:
            with self.subTest(view=view_id):
                self.assertTrue(ok, f"{view_id}: hash mismatch expected={expected} actual={actual}")

    def test_verify_real_files_dimensions(self):
        if not MAIN_IMAGES.is_dir():
            self.skipTest(f"reference images not found at {MAIN_IMAGES} "
                          f"(set LIVYNTH_MAIN_REPO to override)")
        from PIL import Image
        for name, (w, h) in EXPECTED_MAIN_VIEW_DIMENSIONS.items():
            with self.subTest(image=name):
                with Image.open(MAIN_IMAGES / name) as im:
                    self.assertEqual(im.size, (w, h))
                    self.assertEqual(im.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
