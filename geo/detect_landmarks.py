"""Detect Character 001 landmarks with MediaPipe FaceMesh and emit canonical JSON.

Runs on the approved reference photographs. The photographs are uncalibrated
AI-generated images; every output is flagged ``calibrated=false``. Per-point
confidence is a **constant heuristic** (MediaPipe FaceMesh exports no
per-landmark confidence); a value of ``DETECTED_CONFIDENCE`` means "detected by
FaceMesh on this drawing", nothing more. Points FaceMesh cannot provide
(ears, true hairline) or that are outside its topology are listed in
``unmapped_points``.

Usage:
    python geo/detect_landmarks.py --images-dir "C:/PROJECT/Livynth/assets/characters/character_001/identity_capture_v1" \
        --out-dir output/landmarks [--views front left_45 ...]

Outputs per view: ``<out-dir>/<view_id>.json`` and, with ``--overlays``,
``<out-dir>/overlays/<view_id>_overlay.png``. A machine-readable detection
report is written to ``<out-dir>/detection_report.json``.
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
    KNOWN_VIEW_IDS,
    SCHEMA_VERSION,
    LandmarkDocument,
    LandmarkPoint,
    sha256_file,
)

# filename -> view_id (approved identity_capture_v1 inventory)
VIEW_MANIFEST = {
    "01_subject_front.png": "front",
    "02_subject_left_45.png": "left_45",
    "03_subject_right_45.png": "right_45",
    "04_left_profile.png": "profile_left",
    "05_right_profile.png": "profile_right",
    "06_back_head.png": "back",
    "07_top_head.png": "top",
    "08_front_closeup.png": "front_closeup",
    "09_left_ear.png": "left_ear",
    "10_right_ear.png": "right_ear",
    "11_eyes_closeup.png": "eyes_closeup",
    "12_iris_macro.png": "iris_macro",
    "13_skin_macro.png": "skin_macro",
    "14_lips_closeup.png": "lips_closeup",
    "15_hair_closeup.png": "hair_closeup",
}

DETECTED_CONFIDENCE = 0.9  # constant heuristic; FaceMesh exports no per-landmark confidence
APPROXIMATE_CONFIDENCE = 0.6  # points whose topology is approximate (jaw, hairline, pupil)

# Canonical point -> mediapipe FaceMesh landmark index (468-face mesh + iris via refine_landmarks).
# Subject-anatomical convention: _l = subject's left (image-right on an unmirrored frontal photo).
# Verified against 01_subject_front.png overlays on 2026-11-11 (see docs/C001_GEO03_LANDMARKS.md).
MP_INDEX = {
    "canthus_outer_r": 33,   "canthus_inner_r": 133,
    "canthus_outer_l": 263,  "canthus_inner_l": 362,
    "upper_eyelid_r": 159,   "lower_eyelid_r": 145,
    "upper_eyelid_l": 386,   "lower_eyelid_l": 374,
    "brow_inner_r": 107,     "brow_mid_r": 66,     "brow_outer_r": 46,
    "brow_inner_l": 336,     "brow_mid_l": 296,    "brow_outer_l": 276,
    "nose_bridge_top": 168,  "nose_bridge_bottom": 6,
    "nose_tip": 1,
    "nostril_r": 129,        "nostril_l": 358,
    "mouth_corner_r": 61,    "mouth_corner_l": 291,
    "upper_lip_mid": 13,     "lower_lip_mid": 14,
    "chin": 152,
    # Approximate stand-ins (FaceMesh has no gonion / hairline):
    "jaw_angle_r": 172,      "jaw_angle_l": 397,
    "hairline_center": 10,
}
# Iris landmarks (refine_landmarks=True): 468..472 subject-right iris, 473..477 subject-left iris.
IRIS_CENTER_R, IRIS_CENTER_L = 468, 473

APPROXIMATE_POINTS = {"jaw_angle_l", "jaw_angle_r", "hairline_center", "pupil_center_l", "pupil_center_r"}

# Points with no MediaPipe topology at all -> always unmapped for detection output.
NEVER_MAPPED = ("ear_top_l", "ear_bottom_l", "tragus_l", "ear_top_r", "ear_bottom_r", "tragus_r")


def build_points(landmarks_px, width: int, height: int):
    points = {}
    src = "mediapipe-facemesh"
    for canonical, index in MP_INDEX.items():
        if index >= len(landmarks_px):
            continue
        x, y = landmarks_px[index]
        conf = APPROXIMATE_CONFIDENCE if canonical in APPROXIMATE_POINTS else DETECTED_CONFIDENCE
        points[canonical] = LandmarkPoint(float(x), float(y), conf, f"{src}:{index}")
    # Iris centres (only present with refine_landmarks=True).
    if len(landmarks_px) >= 478:
        xr, yr = landmarks_px[IRIS_CENTER_R]
        xl, yl = landmarks_px[IRIS_CENTER_L]
        points["iris_center_r"] = LandmarkPoint(float(xr), float(yr), DETECTED_CONFIDENCE, f"{src}:{IRIS_CENTER_R}")
        points["iris_center_l"] = LandmarkPoint(float(xl), float(yl), DETECTED_CONFIDENCE, f"{src}:{IRIS_CENTER_L}")
        # Pupil not separately detectable; approximated by iris centre (documented, lower confidence).
        points["pupil_center_r"] = LandmarkPoint(float(xr), float(yr), APPROXIMATE_CONFIDENCE, f"{src}:{IRIS_CENTER_R}(pupil~iris)")
        points["pupil_center_l"] = LandmarkPoint(float(xl), float(yl), APPROXIMATE_CONFIDENCE, f"{src}:{IRIS_CENTER_L}(pupil~iris)")
    unmapped = [p for p in CANONICAL_POINTS if p not in points]
    return points, unmapped


def draw_overlay(image, points: dict, out_path: Path) -> None:
    import cv2
    canvas = image.copy()
    for name, pt in points.items():
        x, y = int(round(pt.x)), int(round(pt.y))
        cv2.circle(canvas, (x, y), 5, (0, 255, 0), -1)
        cv2.putText(canvas, name, (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


class _Landmark:
    """Minimal stand-in for a MediaPipe normalized landmark (x, y only)."""

    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _Face:
    __slots__ = ("landmark",)

    def __init__(self, landmark) -> None:
        self.landmark = landmark


class _Result:
    __slots__ = ("multi_face_landmarks",)

    def __init__(self, multi_face_landmarks) -> None:
        self.multi_face_landmarks = multi_face_landmarks


class TasksFaceLandmarker:
    """Adapter exposing the legacy `solutions.face_mesh` surface on mediapipe >= 1.0.

    mediapipe 1.2.2 removed `mp.solutions.face_mesh`; the replacement Tasks API needs an
    external `face_landmarker.task` asset that is not bundled with the wheel. This adapter
    lets the existing detection body run unchanged on either API.
    """

    def __init__(self, mp, model_path: Path, min_confidence: float) -> None:
        self._mp = mp
        self._model_path = model_path
        self._min_confidence = min_confidence
        self._landmarker = None

    def __enter__(self):
        from mediapipe.tasks.python import vision as mp_vision

        base = self._mp.tasks.BaseOptions(model_asset_path=str(self._model_path))
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=self._min_confidence,
            min_face_presence_confidence=self._min_confidence,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        return self

    def __exit__(self, *exc):
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
        return False

    def process(self, rgb):
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(image)
        faces = list(getattr(result, "face_landmarks", None) or [])
        if not faces:
            return _Result([])
        landmarks = [_Landmark(float(p.x), float(p.y)) for p in faces[0]]
        return _Result([_Face(landmarks)])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--out-dir", default="output/landmarks")
    parser.add_argument("--views", nargs="*", default=None, help="Restrict to these view ids")
    parser.add_argument("--overlays", action="store_true")
    parser.add_argument("--min-detection-confidence", type=float, default=0.5)
    parser.add_argument(
        "--model-path",
        default=None,
        help=(
            "Path to the MediaPipe FaceLandmarker .task asset (used by the Tasks API on "
            "mediapipe >= 1.0, where mp.solutions.face_mesh no longer exists). Default: "
            "models/face_landmarker.task next to the repository root."
        ),
    )
    args = parser.parse_args(argv)

    images_dir = Path(args.images_dir)
    if not images_dir.is_dir():
        print(f"error: images dir not found: {images_dir}", file=sys.stderr)
        return 2

    import cv2
    import mediapipe as mp

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Probe the detector API ---------------------------------------------
    # mediapipe <= 0.10: mp.solutions.face_mesh (legacy).
    # mediapipe >= 1.0 : mp.tasks.vision.FaceLandmarker (Tasks API) + external .task asset.
    solutions = getattr(mp, "solutions", None)
    face_mesh_legacy = getattr(solutions, "face_mesh", None) if solutions is not None else None
    api_available = face_mesh_legacy is not None

    model_path = Path(args.model_path) if args.model_path else (Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task")
    tasks_available = False
    if not api_available:
        tasks_available = bool(getattr(mp, "tasks", None)) and model_path.is_file()
        if not tasks_available:
            print(
                "mediapipe blocker: mp.solutions.face_mesh does not exist in this build "
                f"(mediapipe {getattr(mp, '__version__', '?')}) and no FaceLandmarker asset was found at "
                f"{model_path}. The Tasks FaceLandmarker API requires an external face_landmarker.task "
                "model asset that is not bundled with the wheel and is not auto-fetched. "
                "Writing an honest 'api-unavailable' report; no landmarks are emitted.",
                file=sys.stderr,
            )
            created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            selected = args.views or list(VIEW_MANIFEST.values())
            report = {
                "tool": "geo/detect_landmarks.py",
                "mediapipe_version": getattr(mp, "__version__", "unknown"),
                "opencv_version": getattr(cv2, "__version__", "unknown"),
                "created_utc": created,
                "status": "api-unavailable",
                "reason": "mp.solutions.face_mesh absent; Tasks FaceLandmarker needs unbundled external asset (not downloaded)",
                "calibrated": False,
                "views": {vid: {"view_id": vid, "status": "api-unavailable", "detected": False, "num_points": 0} for vid in selected},
            }
            (out_dir / "detection_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 3

    selected = args.views or list(VIEW_MANIFEST.values())
    unknown = sorted(set(selected) - set(KNOWN_VIEW_IDS))
    if unknown:
        print(f"error: unknown view ids {unknown}", file=sys.stderr)
        return 2

    report = {
        "tool": "geo/detect_landmarks.py",
        "mediapipe_version": getattr(mp, "__version__", "unknown"),
        "opencv_version": getattr(cv2, "__version__", "unknown"),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calibrated": False,
        "views": {},
    }

    detector = (
        mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=args.min_detection_confidence,
        )
        if api_available
        else TasksFaceLandmarker(mp, model_path, args.min_detection_confidence)
    )

    with detector as mesh:
        for filename, view_id in VIEW_MANIFEST.items():
            if view_id not in selected:
                continue
            image_path = images_dir / filename
            entry = {"image_file": filename, "view_id": view_id, "exists": image_path.exists()}
            if not image_path.exists():
                entry.update(status="missing-image", detected=False, num_points=0, error="file not found")
                report["views"][view_id] = entry
                continue

            bgr = cv2.imread(str(image_path))
            if bgr is None:
                entry.update(status="unreadable-image", detected=False, num_points=0, error="cv2.imread returned None")
                report["views"][view_id] = entry
                continue
            height, width = bgr.shape[:2]
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            result = mesh.process(rgb)

            base = dict(
                view_id=view_id,
                image_file=filename,
                image_sha256=sha256_file(image_path),
                image_dimensions_px=(int(width), int(height)),
                annotation_method=f"mediapipe-facemesh-{report['mediapipe_version']} (refine_landmarks=True)",
                calibrated=False,
                created_utc=report["created_utc"],
                provenance={
                    "tool": "geo/detect_landmarks.py",
                    "images_dir": str(images_dir),
                    "mediapipe_version": report["mediapipe_version"],
                    "opencv_version": report["opencv_version"],
                    "min_detection_confidence": args.min_detection_confidence,
                    "confidence_model": "constant heuristic per detected point; no per-landmark confidence from FaceMesh",
                    "note": "AI-generated uncalibrated reference image; measurements of the drawing, not of a real head",
                },
            )

            if not result.multi_face_landmarks:
                doc = LandmarkDocument(
                    points={},
                    unmapped_points=list(CANONICAL_POINTS),
                    notes="MediaPipe FaceMesh found no face in this view; no landmarks emitted.",
                    **base,
                )
                doc.save(out_dir / f"{view_id}.json")
                entry.update(status="no-face-detected", detected=False, num_points=0, json=f"{view_id}.json")
                report["views"][view_id] = entry
                continue

            face = result.multi_face_landmarks[0]
            landmarks_px = [(lm.x * width, lm.y * height) for lm in face.landmark]
            points, unmapped = build_points(landmarks_px, width, height)
            doc = LandmarkDocument(
                points=points,
                unmapped_points=unmapped,
                notes=(
                    "Constant-heuristic confidence; pupil approximated by iris centre; "
                    "jaw angles and hairline are nearest-FaceMesh stand-ins; ears unmapped."
                ),
                **base,
            )
            doc.save(out_dir / f"{view_id}.json")
            if args.overlays:
                draw_overlay(bgr, points, out_dir / "overlays" / f"{view_id}_overlay.png")
            entry.update(
                status="detected",
                detected=True,
                num_points=len(points),
                unmapped_points=unmapped,
                json=f"{view_id}.json",
            )
            report["views"][view_id] = entry

    report_path = out_dir / "detection_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    detected = sum(1 for v in report["views"].values() if v.get("detected"))
    total = len(report["views"])
    print(f"views processed: {total}; detected: {detected}; no-face/missing: {total - detected}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
