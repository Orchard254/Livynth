"""Migrate the legacy manual landmark annotation to the canonical schema.

Source (read-only): ``geo/character001_landmarks.json`` — the legacy manual
visual estimate for ``01_subject_front.png`` (schema
``livynth.c001.reference-landmarks.v1``).

Migration rules (verbatim carry-over, never re-measured):
- legacy ``eyes.left``  -> ``iris_center_l`` (confidence ``legacy-manual``)
- legacy ``eyes.right`` -> ``iris_center_r`` (confidence ``legacy-manual``)
- legacy ``chin``       -> ``chin``
- legacy ``mouth_corners[0]`` -> ``mouth_corner_l``
- legacy ``mouth_corners[1]`` -> ``mouth_corner_r``

The legacy file does NOT state whether "left"/"right" mean image-left/right or
subject anatomical left/right. This migration preserves the legacy labels
verbatim instead of guessing; consumers must treat them as unverified manual
estimates. ``pupil_center_*``, brows, ears, nose, hairline etc. are absent and
listed in ``unmapped_points``.

Usage:
    python geo/migrate_legacy_landmarks.py \
        --legacy geo/character001_landmarks.json \
        --image "C:/PROJECT/Livynth/assets/characters/character_001/identity_capture_v1/01_subject_front.png" \
        --out output/landmarks/front_legacy_manual.json
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
    LEGACY_CONFIDENCE,
    SCHEMA_VERSION,
    LandmarkDocument,
    LandmarkPoint,
    sha256_file,
)

# Canonical points that remain unmapped after migration (everything not produced by the legacy file).
_MIGRATED = ("iris_center_l", "iris_center_r", "chin", "mouth_corner_l", "mouth_corner_r")


def migrate(legacy_path: Path, image_path: Path | None, out_path: Path) -> LandmarkDocument:
    legacy_path = Path(legacy_path)
    raw = json.loads(legacy_path.read_text(encoding="utf-8"))
    if raw.get("schema") != "livynth.c001.reference-landmarks.v1":
        raise SystemExit(
            f"refusing to migrate: unexpected legacy schema {raw.get('schema')!r} "
            "(expected 'livynth.c001.reference-landmarks.v1')"
        )

    points: dict[str, LandmarkPoint] = {}
    src = f"legacy:{legacy_path.name}"

    eyes = raw.get("eyes", {})
    for legacy_key, canonical in (("left", "iris_center_l"), ("right", "iris_center_r")):
        if legacy_key in eyes:
            xy = eyes[legacy_key]
            points[canonical] = LandmarkPoint(float(xy[0]), float(xy[1]), LEGACY_CONFIDENCE, f"{src}:eyes.{legacy_key}")

    if "chin" in raw:
        xy = raw["chin"]
        points["chin"] = LandmarkPoint(float(xy[0]), float(xy[1]), LEGACY_CONFIDENCE, f"{src}:chin")

    corners = raw.get("mouth_corners", [])
    for index, canonical in enumerate(("mouth_corner_l", "mouth_corner_r")):
        if index < len(corners):
            xy = corners[index]
            points[canonical] = LandmarkPoint(float(xy[0]), float(xy[1]), LEGACY_CONFIDENCE, f"{src}:mouth_corners[{index}]")

    unmapped = [p for p in CANONICAL_POINTS if p not in points]

    dims = raw.get("source_dimensions_px")
    image_sha256 = None
    if image_path is not None and Path(image_path).exists():
        image_sha256 = sha256_file(Path(image_path))

    doc = LandmarkDocument(
        view_id="front",
        image_file=str(raw.get("source_image", "01_subject_front.png")),
        image_sha256=image_sha256,
        image_dimensions_px=(int(dims[0]), int(dims[1])) if dims else None,
        annotation_method="legacy-manual-migration (manual visual estimate; uncalibrated AI portrait)",
        points=points,
        unmapped_points=unmapped,
        calibrated=False,
        created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        provenance={
            "tool": "geo/migrate_legacy_landmarks.py",
            "source_file": str(legacy_path),
            "source_schema": raw.get("schema"),
            "source_annotation_method": raw.get("annotation_method"),
            "source_interpretation": raw.get("interpretation"),
            "image_sha256_source": str(image_path) if image_path else None,
            "migrated_points": sorted(points),
            "confidence_label": LEGACY_CONFIDENCE,
            "migration_notes": (
                "Legacy left/right labels carried verbatim; the legacy file does not state whether "
                "they denote image-left/right or subject anatomical left/right. Legacy mouth_corners "
                "order preserved ([0]->mouth_corner_l, [1]->mouth_corner_r). Only ratios and "
                "conservative fitting hints are valid downstream; not ground-truth anatomy."
            ),
        },
        notes=(
            "Migrated from the legacy manual estimate. Coordinates are uncalibrated and "
            "unverified; do not treat as measurements of a real head."
        ),
    )
    out_path = Path(out_path)
    doc.save(out_path)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--legacy", default="geo/character001_landmarks.json")
    parser.add_argument("--image", default=None, help="Path to 01_subject_front.png for sha256 provenance (read-only)")
    parser.add_argument("--out", default="output/landmarks/front_legacy_manual.json")
    args = parser.parse_args(argv)

    doc = migrate(Path(args.legacy), Path(args.image) if args.image else None, Path(args.out))
    print(f"migrated {len(doc.points)} points -> {args.out}")
    print(f"unmapped: {len(doc.unmapped_points)} canonical points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
