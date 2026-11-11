"""Manual visual landmark annotations for the 15 Character 001 reference images.

Context (2026-11-11): MediaPipe 1.2.2 installed successfully in the worktree
venv, but its legacy ``mp.solutions.face_mesh`` API does not exist in this
build, and the Tasks ``FaceLandmarker`` requires an external
``face_landmarker.task`` model asset that is NOT bundled with the wheel and is
NOT auto-fetched by the API. Downloading model weights was out of scope, so
FaceMesh detection was NOT executed. This module is the documented fallback:
coordinates are hand-estimated by visually inspecting each image. They are
**not measurements of a real head** and are expected to be off by tens of
pixels. confidence=0.3 = direct visual estimate; 0.2 = uncertain estimate;
0.15 = rough estimate. Ears' tragi hidden from behind are unmapped.

Coordinate system: either fractions of the full frame (use_frac views) or
nominal 1086x1448 pixels scaled to the actual file dimensions (use_px views),
then written as absolute image pixels.

Usage:
    python geo/manual_annotations.py --images-dir <identity_capture_v1> --out-dir output/landmarks
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geo.landmark_spec import (  # noqa: E402
    CANONICAL_POINTS,
    LandmarkDocument,
    LandmarkPoint,
    sha256_file,
)
from geo.detect_landmarks import VIEW_MANIFEST  # noqa: E402

NOMINAL_W, NOMINAL_H = 1086, 1448

# view_id -> ("px"|"frac", {canonical_point: (x, y)}, {point: confidence override})
ESTIMATES: dict[str, tuple[str, dict[str, tuple[float, float]], dict[str, float]]] = {
    "front": ("px", {
        "brow_inner_l": (610, 478), "brow_mid_l": (670, 468), "brow_outer_l": (753, 487),
        "brow_inner_r": (515, 478), "brow_mid_r": (455, 468), "brow_outer_r": (368, 487),
        "upper_eyelid_l": (652, 505), "lower_eyelid_l": (652, 562),
        "upper_eyelid_r": (455, 505), "lower_eyelid_r": (455, 562),
        "canthus_inner_l": (595, 540), "canthus_outer_l": (715, 537),
        "canthus_inner_r": (510, 540), "canthus_outer_r": (390, 537),
        "pupil_center_l": (655, 535), "pupil_center_r": (448, 535),
        "iris_center_l": (655, 535), "iris_center_r": (448, 535),
        "nose_bridge_top": (550, 470), "nose_bridge_bottom": (550, 650),
        "nostril_l": (597, 692), "nostril_r": (505, 692), "nose_tip": (550, 685),
        "mouth_corner_l": (633, 795), "mouth_corner_r": (467, 795),
        "upper_lip_mid": (549, 775), "lower_lip_mid": (549, 818),
        "chin": (549, 985), "jaw_angle_l": (748, 855), "jaw_angle_r": (352, 855),
        "hairline_center": (549, 375),
        "ear_top_l": (838, 505), "ear_bottom_l": (822, 700), "tragus_l": (795, 605),
        "ear_top_r": (258, 505), "ear_bottom_r": (275, 700), "tragus_r": (300, 605),
    }, {"hairline_center": 0.2, "tragus_l": 0.2, "tragus_r": 0.2}),

    "left_45": ("px", {
        "brow_inner_l": (465, 463), "brow_mid_l": (542, 462), "brow_outer_l": (612, 468),
        "brow_inner_r": (385, 472), "brow_mid_r": (330, 463), "brow_outer_r": (272, 458),
        "upper_eyelid_l": (512, 512), "lower_eyelid_l": (512, 558),
        "upper_eyelid_r": (330, 515), "lower_eyelid_r": (330, 560),
        "canthus_inner_l": (462, 537), "canthus_outer_l": (572, 533),
        "canthus_inner_r": (375, 538), "canthus_outer_r": (290, 534),
        "pupil_center_l": (512, 538), "pupil_center_r": (330, 540),
        "iris_center_l": (512, 538), "iris_center_r": (330, 540),
        "nose_bridge_top": (420, 470), "nose_bridge_bottom": (400, 622),
        "nostril_l": (395, 678), "nostril_r": (335, 683), "nose_tip": (352, 660),
        "mouth_corner_l": (475, 791), "mouth_corner_r": (343, 800),
        "upper_lip_mid": (402, 770), "lower_lip_mid": (402, 818),
        "chin": (392, 900), "jaw_angle_l": (600, 875), "jaw_angle_r": (315, 845),
        "hairline_center": (460, 335),
        "ear_top_l": (815, 490), "ear_bottom_l": (808, 690), "tragus_l": (772, 590),
    }, {"hairline_center": 0.2, "nostril_r": 0.2, "tragus_l": 0.2}),

    "right_45": ("px", {
        "brow_inner_l": (742, 460), "brow_mid_l": (797, 462), "brow_outer_l": (838, 465),
        "brow_inner_r": (640, 468), "brow_mid_r": (572, 466), "brow_outer_r": (498, 458),
        "upper_eyelid_l": (788, 497), "lower_eyelid_l": (786, 540),
        "upper_eyelid_r": (575, 512), "lower_eyelid_r": (575, 556),
        "canthus_inner_l": (738, 520), "canthus_outer_l": (838, 497),
        "canthus_inner_r": (625, 533), "canthus_outer_r": (505, 529),
        "pupil_center_l": (785, 508), "pupil_center_r": (575, 525),
        "iris_center_l": (785, 508), "iris_center_r": (575, 525),
        "nose_bridge_top": (665, 455), "nose_bridge_bottom": (712, 618),
        "nostril_l": (736, 667), "nostril_r": (690, 662), "nose_tip": (745, 655),
        "mouth_corner_l": (812, 753), "mouth_corner_r": (657, 787),
        "upper_lip_mid": (733, 768), "lower_lip_mid": (736, 810),
        "chin": (715, 898), "jaw_angle_l": (800, 852), "jaw_angle_r": (470, 835),
        "hairline_center": (608, 340),
        "ear_top_r": (285, 520), "ear_bottom_r": (312, 685), "tragus_r": (345, 600),
    }, {"canthus_outer_l": 0.2, "hairline_center": 0.2, "tragus_r": 0.2}),

    "profile_left": ("px", {
        "brow_inner_l": (72, 508), "brow_mid_l": (138, 490), "brow_outer_l": (205, 477),
        "upper_eyelid_l": (213, 548), "lower_eyelid_l": (213, 577),
        "canthus_outer_l": (205, 566), "canthus_inner_l": (248, 573),
        "pupil_center_l": (228, 569), "iris_center_l": (228, 569),
        "nose_bridge_top": (128, 553), "nose_bridge_bottom": (92, 638),
        "nostril_l": (118, 733), "nose_tip": (55, 703),
        "mouth_corner_l": (103, 853),
        "upper_lip_mid": (92, 833), "lower_lip_mid": (97, 878),
        "chin": (128, 988), "jaw_angle_l": (555, 733),
        "hairline_center": (212, 415),
        "ear_top_l": (630, 503), "ear_bottom_l": (602, 743), "tragus_l": (578, 643),
    }, {"hairline_center": 0.2, "tragus_l": 0.2}),

    "profile_right": ("px", {
        "brow_inner_r": (897, 452), "brow_mid_r": (815, 467), "brow_outer_r": (733, 477),
        "upper_eyelid_r": (826, 525), "lower_eyelid_r": (826, 560),
        "canthus_inner_r": (858, 544), "canthus_outer_r": (788, 541),
        "pupil_center_r": (828, 546), "iris_center_r": (828, 546),
        "nose_bridge_top": (888, 508), "nose_bridge_bottom": (925, 618),
        "nostril_r": (933, 689), "nose_tip": (970, 658),
        "mouth_corner_r": (883, 813),
        "upper_lip_mid": (933, 799), "lower_lip_mid": (928, 829),
        "chin": (888, 905), "jaw_angle_r": (445, 698),
        "hairline_center": (700, 380),
        "ear_top_r": (428, 498), "ear_bottom_r": (470, 708), "tragus_r": (503, 615),
    }, {"hairline_center": 0.2, "tragus_r": 0.2}),

    "back": ("px", {
        "ear_top_l": (948, 542), "ear_bottom_l": (902, 708),
        "ear_top_r": (205, 548), "ear_bottom_r": (233, 705),
    }, {"ear_top_l": 0.2, "ear_bottom_l": 0.2, "ear_top_r": 0.2, "ear_bottom_r": 0.2}),

    "top": ("frac", {
        "hairline_center": (0.511, 0.546),
        "brow_mid_r": (0.345, 0.674), "brow_mid_l": (0.678, 0.674),
        "brow_outer_r": (0.232, 0.625), "brow_outer_l": (0.800, 0.623),
        "nose_tip": (0.538, 0.845),
    }, {"hairline_center": 0.2, "brow_mid_r": 0.15, "brow_mid_l": 0.15,
        "brow_outer_r": 0.15, "brow_outer_l": 0.15, "nose_tip": 0.2}),

    "front_closeup": ("px", {
        "brow_inner_l": (618, 568), "brow_mid_l": (700, 548), "brow_outer_l": (798, 555),
        "brow_inner_r": (480, 572), "brow_mid_r": (398, 560), "brow_outer_r": (300, 560),
        "upper_eyelid_l": (692, 615), "lower_eyelid_l": (692, 658),
        "upper_eyelid_r": (405, 618), "lower_eyelid_r": (405, 660),
        "canthus_inner_l": (628, 634), "canthus_outer_l": (768, 627),
        "canthus_inner_r": (465, 640), "canthus_outer_r": (330, 631),
        "pupil_center_l": (692, 632), "pupil_center_r": (405, 632),
        "iris_center_l": (692, 632), "iris_center_r": (405, 632),
        "nose_bridge_top": (550, 580), "nose_bridge_bottom": (553, 795),
        "nostril_l": (600, 818), "nostril_r": (503, 818), "nose_tip": (553, 812),
        "mouth_corner_l": (657, 947), "mouth_corner_r": (458, 947),
        "upper_lip_mid": (555, 937), "lower_lip_mid": (555, 993),
        "chin": (555, 1132), "jaw_angle_l": (800, 1008), "jaw_angle_r": (300, 1008),
        "hairline_center": (550, 380),
        "ear_top_l": (913, 588), "ear_bottom_l": (885, 810), "tragus_l": (855, 697),
        "ear_top_r": (185, 598), "ear_bottom_r": (213, 815), "tragus_r": (243, 700),
    }, {"hairline_center": 0.2, "tragus_l": 0.2, "tragus_r": 0.2}),

    "left_ear": ("frac", {
        "ear_top_l": (0.600, 0.131), "ear_bottom_l": (0.440, 0.697), "tragus_l": (0.454, 0.483),
    }, {"tragus_l": 0.25}),

    "right_ear": ("frac", {
        "ear_top_r": (0.453, 0.167), "ear_bottom_r": (0.559, 0.697), "tragus_r": (0.626, 0.447),
    }, {"tragus_r": 0.25}),

    "eyes_closeup": ("frac", {
        "brow_inner_l": (0.600, 0.370), "brow_mid_l": (0.750, 0.280), "brow_outer_l": (0.900, 0.290),
        "brow_inner_r": (0.430, 0.360), "brow_mid_r": (0.280, 0.285), "brow_outer_r": (0.130, 0.320),
        "upper_eyelid_l": (0.740, 0.500), "lower_eyelid_l": (0.740, 0.685),
        "upper_eyelid_r": (0.282, 0.480), "lower_eyelid_r": (0.282, 0.665),
        "canthus_inner_l": (0.650, 0.660), "canthus_outer_l": (0.855, 0.600),
        "canthus_inner_r": (0.375, 0.650), "canthus_outer_r": (0.185, 0.605),
        "pupil_center_l": (0.740, 0.580), "pupil_center_r": (0.282, 0.590),
        "iris_center_l": (0.740, 0.580), "iris_center_r": (0.282, 0.590),
        "nose_bridge_top": (0.515, 0.380),
    }, {"nose_bridge_top": 0.2}),

    "iris_macro": ("frac", {
        "upper_eyelid_r": (0.470, 0.330), "lower_eyelid_r": (0.495, 0.690),
        "canthus_outer_r": (0.105, 0.565), "canthus_inner_r": (0.880, 0.630),
        "pupil_center_r": (0.495, 0.490), "iris_center_r": (0.495, 0.490),
    }, {}),

    "skin_macro": ("frac", {
        "ear_top_r": (0.048, 0.300), "ear_bottom_r": (0.095, 0.720), "tragus_r": (0.105, 0.470),
        "upper_eyelid_r": (0.640, 0.090), "lower_eyelid_r": (0.660, 0.190),
        "canthus_outer_r": (0.515, 0.130), "canthus_inner_r": (0.792, 0.140),
        "pupil_center_r": (0.665, 0.115), "iris_center_r": (0.665, 0.115),
        "nostril_r": (0.900, 0.700),
    }, {"upper_eyelid_r": 0.2, "tragus_r": 0.2}),

    "lips_closeup": ("frac", {
        "mouth_corner_l": (0.775, 0.493), "mouth_corner_r": (0.265, 0.488),
        "upper_lip_mid": (0.505, 0.445), "lower_lip_mid": (0.505, 0.725),
        "chin": (0.500, 0.935),
    }, {"chin": 0.15}),

    "hair_closeup": ("frac", {
        "brow_inner_l": (0.628, 0.788), "brow_mid_l": (0.752, 0.748), "brow_outer_l": (0.872, 0.778),
        "brow_inner_r": (0.375, 0.795), "brow_mid_r": (0.245, 0.752), "brow_outer_r": (0.135, 0.772),
        "upper_eyelid_l": (0.700, 0.845), "lower_eyelid_l": (0.712, 0.940),
        "upper_eyelid_r": (0.340, 0.870), "lower_eyelid_r": (0.350, 0.975),
        "canthus_inner_l": (0.612, 0.905), "canthus_outer_l": (0.815, 0.868),
        "canthus_inner_r": (0.420, 0.920), "canthus_outer_r": (0.245, 0.890),
        "pupil_center_l": (0.700, 0.918), "pupil_center_r": (0.345, 0.930),
        "iris_center_l": (0.700, 0.918), "iris_center_r": (0.345, 0.930),
        "hairline_center": (0.500, 0.345),
        "ear_top_l": (0.955, 0.810), "ear_top_r": (0.045, 0.810),
    }, {"hairline_center": 0.2, "ear_top_l": 0.15, "ear_top_r": 0.15}),
}

DEFAULT_CONFIDENCE = 0.3


def build_document(view_id: str, images_dir: Path, created_utc: str) -> LandmarkDocument:
    filename = next(name for name, vid in VIEW_MANIFEST.items() if vid == view_id)
    image_path = images_dir / filename
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    import cv2
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise RuntimeError(f"cv2 cannot read {image_path}")
    height, width = bgr.shape[:2]

    kind, raw, conf_overrides = ESTIMATES[view_id]
    points: dict[str, LandmarkPoint] = {}
    for name, (x, y) in raw.items():
        if kind == "px":
            ax, ay = x * width / NOMINAL_W, y * height / NOMINAL_H
        else:
            ax, ay = x * width, y * height
        conf = conf_overrides.get(name, DEFAULT_CONFIDENCE)
        points[name] = LandmarkPoint(ax, ay, conf, f"manual-visual-estimate:{name}")
    unmapped = [p for p in CANONICAL_POINTS if p not in points]

    return LandmarkDocument(
        view_id=view_id,
        image_file=filename,
        image_sha256=sha256_file(image_path),
        image_dimensions_px=(int(width), int(height)),
        annotation_method="manual-visual-estimate (AI-generated uncalibrated image; not a detection)",
        points=points,
        unmapped_points=unmapped,
        calibrated=False,
        created_utc=created_utc,
        provenance={
            "tool": "geo/manual_annotations.py",
            "images_dir": str(images_dir),
            "method": "hand-estimated by visually inspecting each image; expected error tens of pixels",
            "mediapipe_blocker": (
                "mediapipe 1.2.2 installed, but mp.solutions.face_mesh does not exist in this build and "
                "tasks FaceLandmarker requires an external face_landmarker.task asset not bundled with the "
                "wheel (API does not auto-fetch it); model downloads were out of scope. UNVERIFIED detection."
            ),
            "confidence_model": f"0.3 direct visual estimate; 0.2 uncertain; 0.15 rough; pupil~=iris",
            "chirality_note": (
                "Canonical _l/_r are subject-anatomical; AI drawing anatomy chirality is unverified. "
                "All _l/_r assignments carry a possible systematic swap."
            ),
        },
        notes="Manual estimate, low precision. Use only as a coarse blockout hint; never as anatomy ground truth.",
    )


def draw_overlay(image_path: Path, doc: LandmarkDocument, out_path: Path) -> None:
    import cv2
    canvas = cv2.imread(str(image_path))
    for name, pt in doc.points.items():
        x, y = int(round(pt.x)), int(round(pt.y))
        cv2.circle(canvas, (x, y), 6, (0, 255, 0), -1)
        cv2.circle(canvas, (x, y), 6, (0, 0, 0), 1)
        cv2.putText(canvas, name, (x + 7, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 0), 1, cv2.LINE_AA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--out-dir", default="output/landmarks")
    parser.add_argument("--overlays", action="store_true")
    args = parser.parse_args(argv)

    images_dir = Path(args.images_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    summary = {}
    for filename, view_id in VIEW_MANIFEST.items():
        doc = build_document(view_id, images_dir, created)
        doc.save(out_dir / f"{view_id}.json")
        if args.overlays:
            draw_overlay(images_dir / filename, doc, out_dir / "overlays" / f"{view_id}_manual_overlay.png")
        summary[view_id] = {"image_file": filename, "num_points": len(doc.points),
                            "unmapped_points": len(doc.unmapped_points)}
        print(f"{view_id}: {len(doc.points)} points, {len(doc.unmapped_points)} unmapped")

    (out_dir / "manual_annotation_report.json").write_text(
        json.dumps({"created_utc": created, "method": "manual-visual-estimate", "views": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
