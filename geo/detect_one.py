"""Detect canonical Character 001 landmarks on ONE arbitrary image (candidate renders).

Reuses the validated detector in geo/detect_landmarks.py (MediaPipe 1.2.2 Tasks API) so
candidate renders are measured with exactly the same point set as the references.

Usage:
    python -m geo.detect_one --image <png> --out <json> [--model-path <task file>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from geo.detect_landmarks import TasksFaceLandmarker, build_points


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-path", default=None)
    args = ap.parse_args(argv)

    import cv2
    import mediapipe as mp

    img_path = Path(args.image)
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        raise SystemExit(f"unreadable image: {img_path}")
    height, width = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    model_path = Path(args.model_path) if args.model_path else (
        Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task")

    with TasksFaceLandmarker(mp, model_path, 0.5) as marker:
        result = marker.process(rgb)

    faces = list(getattr(result, "multi_face_landmarks", None) or [])
    if not faces:
        doc = {
            "schema": "livynth.c001.landmarks", "schema_version": "2.0.0",
            "view_id": img_path.stem, "image_file": img_path.name,
            "image_sha256": sha256_file(img_path), "image_dimensions_px": [int(width), int(height)],
            "annotation_method": f"mediapipe-facemesh-{getattr(mp, '__version__', '?')} (Tasks API)",
            "calibrated": False,
            "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "points": {}, "unmapped_points": [], "notes": "no face detected in this image",
            "provenance": {"tool": "geo.detect_landmarks", "mediapipe_version": getattr(mp, "__version__", "?")},
        }
        Path(args.out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print("no face detected")
        return 3

    landmarks = [(float(p.x) * width, float(p.y) * height) for p in faces[0].landmark]
    points, unmapped = build_points(landmarks, width, height)
    doc = {
        "schema": "livynth.c001.landmarks", "schema_version": "2.0.0",
        "view_id": img_path.stem, "image_file": img_path.name,
        "image_sha256": sha256_file(img_path), "image_dimensions_px": [int(width), int(height)],
        "annotation_method": f"mediapipe-facemesh-{getattr(mp, '__version__', '?')} (Tasks API)",
        "calibrated": False,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "points": {k: {"x": float(v.x), "y": float(v.y), "confidence": v.confidence, "source": v.source}
                   for k, v in points.items()},
        "unmapped_points": list(unmapped),
        "notes": "candidate render measured with the reference detector",
        "provenance": {"tool": "geo.detect_landmarks", "mediapipe_version": getattr(mp, "__version__", "?")},
    }
    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"detected {len(points)} points ({len(unmapped)} unmapped) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
