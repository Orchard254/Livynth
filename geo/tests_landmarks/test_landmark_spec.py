"""Unit tests for geo.landmark_spec (canonical Character 001 schema)."""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from geo import landmark_spec as spec  # noqa: E402


def minimal_doc_dict() -> dict:
    return {
        "schema": spec.SCHEMA_NAME,
        "schema_version": spec.SCHEMA_VERSION,
        "view_id": "front",
        "image_file": "01_subject_front.png",
        "image_sha256": "a" * 64,
        "image_dimensions_px": [1086, 1448],
        "annotation_method": "unit-test",
        "calibrated": False,
        "created_utc": "2026-11-11T00:00:00Z",
        "points": {
            "chin": {"x": 549.0, "y": 925.0, "confidence": 0.9, "source": "test"},
        },
        "unmapped_points": [p for p in spec.CANONICAL_POINTS if p != "chin"],
        "provenance": {"tool": "unit-test"},
        "notes": "",
    }


class TestSchemaAcceptReject(unittest.TestCase):
    def test_minimal_document_accepted(self):
        doc = spec.LandmarkDocument.from_dict(minimal_doc_dict())
        self.assertEqual(doc.view_id, "front")
        self.assertIn("chin", doc.points)
        self.assertEqual(len(doc.unmapped_points), len(spec.CANONICAL_POINTS) - 1)

    def test_roundtrip_json(self):
        doc = spec.LandmarkDocument.from_dict(minimal_doc_dict())
        reparsed = spec.LandmarkDocument.from_dict(json.loads(doc.to_json()))
        self.assertEqual(reparsed.to_dict(), doc.to_dict())

    def test_wrong_schema_name_rejected(self):
        data = minimal_doc_dict()
        data["schema"] = "livynth.c001.reference-landmarks.v1"
        with self.assertRaises(spec.LandmarkSchemaError):
            spec.LandmarkDocument.from_dict(data)

    def test_wrong_schema_version_rejected(self):
        data = minimal_doc_dict()
        data["schema_version"] = "1.0.0"
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_unknown_view_id_rejected(self):
        data = minimal_doc_dict()
        data["view_id"] = "underwater_selfie"
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("view_id" in e for e in errors))

    def test_unknown_point_id_rejected(self):
        data = minimal_doc_dict()
        data["points"]["nose_dolosus"] = {"x": 1, "y": 2, "confidence": 0.5, "source": "test"}
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("unknown canonical point ids" in e for e in errors))

    def test_confidence_out_of_range_rejected(self):
        data = minimal_doc_dict()
        data["points"]["chin"]["confidence"] = 1.5
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_categorical_legacy_confidence_accepted(self):
        data = minimal_doc_dict()
        data["points"]["chin"]["confidence"] = spec.LEGACY_CONFIDENCE
        doc = spec.LandmarkDocument.from_dict(data)
        self.assertEqual(doc.points["chin"].confidence, spec.LEGACY_CONFIDENCE)

    def test_unknown_categorical_confidence_rejected(self):
        data = minimal_doc_dict()
        data["points"]["chin"]["confidence"] = "trust-me-bro"
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("categorical confidence" in e for e in errors))

    def test_non_finite_coordinates_rejected(self):
        data = minimal_doc_dict()
        data["points"]["chin"]["x"] = float("nan")
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("finite" in e for e in errors))

    def test_point_outside_image_bounds_rejected(self):
        data = minimal_doc_dict()
        data["points"]["chin"]["x"] = 1086.0 + 1.0
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("outside image width" in e for e in errors))

    def test_mapped_and_unmapped_overlap_rejected(self):
        data = minimal_doc_dict()
        data["unmapped_points"].append("chin")
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("both mapped and unmapped" in e for e in errors))

    def test_duplicate_unmapped_rejected(self):
        data = minimal_doc_dict()
        data["unmapped_points"] = ["nose_tip", "nose_tip"]
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_bad_sha256_rejected(self):
        data = minimal_doc_dict()
        data["image_sha256"] = "xyz"
        errors = spec.validate_document_dict(data)
        self.assertTrue(any("image_sha256" in e for e in errors))


class TestHelpers(unittest.TestCase):
    def test_mirror_point_name(self):
        self.assertEqual(spec.mirror_point_name("brow_inner_l"), "brow_inner_r")
        self.assertEqual(spec.mirror_point_name("jaw_angle_r"), "jaw_angle_l")
        self.assertIsNone(spec.mirror_point_name("chin"))
        self.assertIsNone(spec.mirror_point_name("not_a_point_l"))

    def test_iter_paired_points(self):
        pairs = list(spec.iter_paired_points(["iris_center_l", "iris_center_r", "chin"]))
        self.assertEqual(pairs, [("iris_center_l", "iris_center_r")])

    def test_canonical_count_and_groups(self):
        self.assertEqual(len(spec.CANONICAL_POINTS), 37)
        self.assertEqual(len(set(spec.CANONICAL_POINTS)), 37)
        self.assertEqual(spec.point_ids_for_group("ears"), spec.CANONICAL_GROUPS["ears"])
        with self.assertRaises(KeyError):
            spec.point_ids_for_group("wings")


if __name__ == "__main__":
    unittest.main()
