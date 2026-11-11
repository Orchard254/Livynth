"""Synthetic front <-> mirrored-profile consistency check.

This is a SYNTHETIC interface test: it constructs an idealised symmetric
frontal point set, mirrors it (x' = width - x, L/R names swapped) as a
stand-in for the opposite-profile geometry interface, and verifies that the
schema, pairing helpers and distance relations behave. It measures no real
image and asserts no likeness property.
"""

import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from geo.landmark_spec import (  # noqa: E402
    CANONICAL_POINTS,
    KNOWN_VIEW_IDS,
    LandmarkDocument,
    LandmarkPoint,
    iter_paired_points,
    mirror_point_name,
)

WIDTH, HEIGHT = 1086, 1448
CX = WIDTH / 2.0


# All L/R pairs sum to exactly WIDTH (1086) so they are mirrored about CX = 543.
RAW_FRONT = {
    "brow_inner_l": (600, 430), "brow_mid_l": (645, 415), "brow_outer_l": (700, 425),
    "brow_inner_r": (486, 430), "brow_mid_r": (441, 415), "brow_outer_r": (386, 425),
    "upper_eyelid_l": (655, 500), "lower_eyelid_l": (655, 545),
    "upper_eyelid_r": (431, 500), "lower_eyelid_r": (431, 545),
    "canthus_inner_l": (620, 522), "canthus_outer_l": (690, 522),
    "canthus_inner_r": (466, 522), "canthus_outer_r": (396, 522),
    "pupil_center_l": (655, 522), "pupil_center_r": (431, 522),
    "iris_center_l": (655, 522), "iris_center_r": (431, 522),
    "nose_bridge_top": (543, 470), "nose_bridge_bottom": (543, 620),
    "nostril_l": (590, 665), "nostril_r": (496, 665), "nose_tip": (543, 630),
    "mouth_corner_l": (630, 762), "mouth_corner_r": (456, 762),
    "upper_lip_mid": (543, 745), "lower_lip_mid": (543, 795),
    "chin": (543, 925),
    "jaw_angle_l": (675, 800), "jaw_angle_r": (411, 800),
    "hairline_center": (543, 300),
    "ear_top_l": (733, 480), "ear_bottom_l": (733, 620), "tragus_l": (738, 560),
    "ear_top_r": (353, 480), "ear_bottom_r": (353, 620), "tragus_r": (348, 560),
}


def symmetric_front_points() -> dict[str, LandmarkPoint]:
    """Idealised symmetric face: all _l/_r pairs mirrored about CX."""
    raw = RAW_FRONT
    assert set(raw) == set(CANONICAL_POINTS)
    return {name: LandmarkPoint(float(x), float(y), 1.0, "synthetic") for name, (x, y) in raw.items()}


def make_front_doc() -> LandmarkDocument:
    return LandmarkDocument(
        view_id="front",
        image_file="synthetic_front.png",
        image_sha256=None,
        image_dimensions_px=(WIDTH, HEIGHT),
        annotation_method="synthetic-test-fixture",
        points=symmetric_front_points(),
        unmapped_points=[],
        calibrated=False,
        created_utc="2026-11-11T00:00:00Z",
        provenance={"tool": "unit-test", "synthetic": True},
        notes="Synthetic idealised symmetric face; not an image measurement.",
    )


def mirror_document(doc: LandmarkDocument, view_id: str) -> LandmarkDocument:
    mirrored: dict[str, LandmarkPoint] = {}
    for name, point in doc.points.items():
        twin = mirror_point_name(name)
        target = twin if twin is not None else name
        mirrored[target] = LandmarkPoint(WIDTH - point.x, point.y, point.confidence, f"{point.source}:mirrored-x")
    return LandmarkDocument(
        view_id=view_id,
        image_file=doc.image_file,
        image_sha256=doc.image_sha256,
        image_dimensions_px=doc.image_dimensions_px,
        annotation_method=doc.annotation_method,
        points=mirrored,
        unmapped_points=list(doc.unmapped_points),
        calibrated=False,
        created_utc=doc.created_utc,
        provenance={**doc.provenance, "mirrored_from": doc.view_id, "transform": "x' = width - x; L/R swapped"},
        notes="Mirrored synthetic companion.",
    )


def dist(a: LandmarkPoint, b: LandmarkPoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


class TestSyntheticFrontMirroredProfile(unittest.TestCase):
    def setUp(self):
        self.front = make_front_doc()
        self.mirrored = mirror_document(self.front, "profile_right")

    def test_front_document_validates(self):
        self.assertEqual(set(self.front.points), set(CANONICAL_POINTS))

    def test_mirrored_document_validates(self):
        # round-trip through JSON to prove serialisability of the mirrored interface
        reparsed = LandmarkDocument.from_dict(__import__("json").loads(self.mirrored.to_json()))
        self.assertEqual(set(reparsed.points), set(CANONICAL_POINTS))

    def test_symmetry_about_image_centre(self):
        pts = self.front.points
        for left, right in iter_paired_points(pts):
            mid = (pts[left].x + pts[right].x) / 2.0
            self.assertAlmostEqual(mid, CX, places=6, msg=f"pair {left}/{right} not centred")
            self.assertAlmostEqual(pts[left].y, pts[right].y, places=6, msg=f"pair {left}/{right} vertical mismatch")

    def test_mirror_is_involution_on_pairs(self):
        pts = self.front.points
        mirrored_twice = mirror_document(self.mirrored, "front")
        for name, point in pts.items():
            self.assertAlmostEqual(mirrored_twice.points[name].x, point.x, places=6, msg=name)
            self.assertAlmostEqual(mirrored_twice.points[name].y, point.y, places=6, msg=name)

    def test_distances_preserved_under_mirror(self):
        pairs = [("iris_center_l", "iris_center_r"), ("mouth_corner_l", "mouth_corner_r"),
                 ("brow_outer_l", "brow_outer_r"), ("canthus_inner_l", "canthus_outer_l"),
                 ("ear_top_l", "ear_bottom_l"), ("nose_bridge_top", "nose_tip")]
        for a, b in pairs:
            self.assertAlmostEqual(dist(self.front.points[a], self.front.points[b]),
                                   dist(self.mirrored.points[a], self.mirrored.points[b]),
                                   places=6, msg=f"{a}-{b}")

    def test_unpaired_points_map_through_mirror(self):
        for name in ("chin", "nose_tip", "hairline_center", "upper_lip_mid", "lower_lip_mid", "nose_bridge_bottom"):
            self.assertAlmostEqual(self.mirrored.points[name].x, WIDTH - self.front.points[name].x, places=6, msg=name)
            self.assertAlmostEqual(self.mirrored.points[name].y, self.front.points[name].y, places=6, msg=name)

    def test_paired_names_swapped_under_mirror(self):
        # After mirroring, the point now called iris_center_l sits at the old iris_center_r location.
        self.assertAlmostEqual(self.mirrored.points["iris_center_l"].x, WIDTH - self.front.points["iris_center_r"].x, places=6)
        self.assertAlmostEqual(self.mirrored.points["iris_center_r"].x, WIDTH - self.front.points["iris_center_l"].x, places=6)

    def test_mirror_view_id_is_known(self):
        self.assertIn("profile_right", KNOWN_VIEW_IDS)


if __name__ == "__main__":
    unittest.main()
