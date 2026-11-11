"""Tests for geo.migrate_legacy_landmarks (legacy manual annotation migration)."""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from geo import migrate_legacy_landmarks as mig  # noqa: E402
from geo.landmark_spec import CANONICAL_POINTS, LEGACY_CONFIDENCE, LandmarkDocument  # noqa: E402

LEGACY_PATH = REPO_ROOT / "geo" / "character001_landmarks.json"


class TestLegacyMigration(unittest.TestCase):
    def test_legacy_file_present(self):
        self.assertTrue(LEGACY_PATH.exists(), f"legacy file missing: {LEGACY_PATH}")

    def test_migrated_document_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "migrated.json"
            doc = mig.migrate(LEGACY_PATH, None, out)
            self.assertTrue(out.exists())
            reparsed = LandmarkDocument.load(out)  # raises if invalid
            self.assertEqual(reparsed.view_id, "front")

    def test_migrated_values_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "migrated.json"
            doc = mig.migrate(LEGACY_PATH, None, out)
            self.assertEqual((doc.points["iris_center_l"].x, doc.points["iris_center_l"].y), (444.0, 526.0))
            self.assertEqual((doc.points["iris_center_r"].x, doc.points["iris_center_r"].y), (656.0, 525.0))
            self.assertEqual((doc.points["chin"].x, doc.points["chin"].y), (549.0, 925.0))
            self.assertEqual((doc.points["mouth_corner_l"].x, doc.points["mouth_corner_l"].y), (466.0, 762.0))
            self.assertEqual((doc.points["mouth_corner_r"].x, doc.points["mouth_corner_r"].y), (630.0, 762.0))

    def test_all_migrated_points_legacy_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = mig.migrate(LEGACY_PATH, None, Path(tmp) / "migrated.json")
            for name, point in doc.points.items():
                self.assertEqual(point.confidence, LEGACY_CONFIDENCE, name)

    def test_unmapped_cover_remainder(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = mig.migrate(LEGACY_PATH, None, Path(tmp) / "migrated.json")
            self.assertEqual(set(doc.unmapped_points) | set(doc.points), set(CANONICAL_POINTS))
            self.assertFalse(set(doc.unmapped_points) & set(doc.points))
            self.assertIn("ear_top_l", doc.unmapped_points)
            self.assertIn("hairline_center", doc.unmapped_points)
            self.assertIn("brow_mid_l", doc.unmapped_points)

    def test_provenance_labels_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = mig.migrate(LEGACY_PATH, None, Path(tmp) / "migrated.json")
            self.assertEqual(doc.provenance.get("confidence_label"), LEGACY_CONFIDENCE)
            self.assertFalse(doc.calibrated)
            self.assertIn("legacy", doc.annotation_method.lower())

    def test_refusal_on_unexpected_legacy_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "bogus_legacy.json"
            bogus.write_text('{"schema": "livynth.c001.reference-landmarks.v999"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                mig.migrate(bogus, None, Path(tmp) / "out.json")


if __name__ == "__main__":
    unittest.main()
