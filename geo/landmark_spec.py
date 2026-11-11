"""Canonical Character 001 landmark schema (livynth.c001.landmarks).

This module defines the *schema* for image-space facial landmark annotations of
the LIVYNTH Character 001 reference images. It is deliberately free of any
detection backend: MediaPipe output, legacy manual estimates and future manual
corrections all serialise to the same format.

Key properties
--------------
- Image-space coordinates in pixels (x right, y down), origin top-left.
- ``_l`` / ``_r`` suffixes are **subject-anatomical** (subject's left/right),
  not image-left/image-right. In an unmirrored frontal photograph the
  subject's left side appears on the image's right. Whether the reference
  photographs are anatomically mirrored is UNKNOWN (AI-generated, not
  calibrated); the convention is documented here and never silently flipped.
- Ears, jaw angles and the hairline are NOT modelled by MediaPipe FaceMesh;
  they are part of the schema but may be absent (recorded in
  ``unmapped_points``) for detection-backed annotations.
- Per-point ``confidence`` is either a float in [0, 1] or the literal string
  ``"legacy-manual"`` for the legacy manual annotation migration.
- ``calibrated`` is always ``false`` for these AI-generated reference images:
  they are uncalibrated 2D renderings, not measurement photographs. Detections
  are measurements of the *drawing*, not of a real head.

Schema version: 2.0.0 (supersedes the legacy ``livynth.c001.reference-landmarks.v1``).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SCHEMA_NAME = "livynth.c001.landmarks"
SCHEMA_VERSION = "2.0.0"

LEGACY_CONFIDENCE = "legacy-manual"
ALLOWED_CATEGORICAL_CONFIDENCE = {LEGACY_CONFIDENCE}

# ---------------------------------------------------------------------------
# Canonical point registry
# ---------------------------------------------------------------------------

# group -> tuple of canonical point ids (subject-anatomical L/R convention)
CANONICAL_GROUPS: Dict[str, Tuple[str, ...]] = {
    "brows": (
        "brow_inner_l", "brow_mid_l", "brow_outer_l",
        "brow_inner_r", "brow_mid_r", "brow_outer_r",
    ),
    "eyes": (
        "upper_eyelid_l", "lower_eyelid_l",
        "upper_eyelid_r", "lower_eyelid_r",
        "canthus_inner_l", "canthus_outer_l",
        "canthus_inner_r", "canthus_outer_r",
        "pupil_center_l", "pupil_center_r",
        "iris_center_l", "iris_center_r",
    ),
    "nose": (
        "nose_bridge_top", "nose_bridge_bottom",
        "nostril_l", "nostril_r", "nose_tip",
    ),
    "mouth": (
        "mouth_corner_l", "mouth_corner_r",
        "upper_lip_mid", "lower_lip_mid",
    ),
    "face": (
        "chin", "jaw_angle_l", "jaw_angle_r", "hairline_center",
    ),
    "ears": (
        "ear_top_l", "ear_bottom_l", "tragus_l",
        "ear_top_r", "ear_bottom_r", "tragus_r",
    ),
}

CANONICAL_POINTS: Tuple[str, ...] = tuple(
    point for group in CANONICAL_GROUPS.values() for point in group
)

POINT_GROUP: Dict[str, str] = {
    point: group for group, points in CANONICAL_GROUPS.items() for point in points
}

# The eight views that carry facial geometry we attempt to detect.
# Back/top/macro/ear views are not expected to yield a usable face mesh.
GEOMETRY_VIEWS: Tuple[str, ...] = (
    "front", "left_45", "right_45", "profile_left", "profile_right",
    "back", "top", "front_closeup",
)

KNOWN_VIEW_IDS: Tuple[str, ...] = GEOMETRY_VIEWS + (
    "left_ear", "right_ear", "eyes_closeup", "iris_macro",
    "skin_macro", "lips_closeup", "hair_closeup",
)

# Views for which a full face mesh is structurally plausible with a frontal-ish
# detector. Honest expectation: back/top and most macro views fail detection.
FACE_MESH_PLAUSIBLE_VIEWS: Tuple[str, ...] = (
    "front", "left_45", "right_45", "profile_left", "profile_right",
    "front_closeup", "eyes_closeup", "lips_closeup",
)

EAR_POINTS: Tuple[str, ...] = CANONICAL_GROUPS["ears"]


class LandmarkSchemaError(ValueError):
    """Raised when a landmark document fails schema validation."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_confidence(value: Any, where: str, errors: List[str]) -> None:
    if isinstance(value, str):
        if value not in ALLOWED_CATEGORICAL_CONFIDENCE:
            errors.append(f"{where}: categorical confidence {value!r} not in {sorted(ALLOWED_CATEGORICAL_CONFIDENCE)}")
        return
    if _is_finite_number(value):
        if not (0.0 <= float(value) <= 1.0):
            errors.append(f"{where}: confidence {value} outside [0, 1]")
        return
    errors.append(f"{where}: confidence must be a float in [0, 1] or one of {sorted(ALLOWED_CATEGORICAL_CONFIDENCE)}, got {value!r}")


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class LandmarkPoint:
    x: float
    y: float
    confidence: Any  # float in [0, 1] or categorical string
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": float(self.x),
            "y": float(self.y),
            "confidence": self.confidence,
            "source": self.source,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any], where: str, errors: List[str]) -> Optional["LandmarkPoint"]:
        if not isinstance(data, Mapping):
            errors.append(f"{where}: point must be an object, got {type(data).__name__}")
            return None
        missing = [k for k in ("x", "y", "confidence", "source") if k not in data]
        if missing:
            errors.append(f"{where}: missing keys {missing}")
            return None
        x, y = data["x"], data["y"]
        if not _is_finite_number(x):
            errors.append(f"{where}.x: not a finite number: {x!r}")
        if not _is_finite_number(y):
            errors.append(f"{where}.y: not a finite number: {y!r}")
        _validate_confidence(data["confidence"], f"{where}.confidence", errors)
        if not isinstance(data["source"], str) or not data["source"].strip():
            errors.append(f"{where}.source: must be a non-empty string")
        if errors:
            return None
        return LandmarkPoint(float(x), float(y), data["confidence"], str(data["source"]))


@dataclass
class LandmarkDocument:
    view_id: str
    image_file: str
    image_sha256: Optional[str]
    image_dimensions_px: Optional[Tuple[int, int]]
    annotation_method: str
    points: Dict[str, LandmarkPoint]
    unmapped_points: List[str] = field(default_factory=list)
    calibrated: bool = False
    created_utc: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    schema_version: str = SCHEMA_VERSION

    # -- serialisation ------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA_NAME,
            "schema_version": self.schema_version,
            "view_id": self.view_id,
            "image_file": self.image_file,
            "image_sha256": self.image_sha256,
            "image_dimensions_px": list(self.image_dimensions_px) if self.image_dimensions_px else None,
            "annotation_method": self.annotation_method,
            "calibrated": bool(self.calibrated),
            "created_utc": self.created_utc,
            "points": {name: point.to_dict() for name, point in self.points.items()},
            "unmapped_points": list(self.unmapped_points),
            "provenance": dict(self.provenance),
            "notes": self.notes,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    # -- loading -----------------------------------------------------------
    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "LandmarkDocument":
        errors: List[str] = []
        doc = _parse_document(data, errors)
        if errors:
            raise LandmarkSchemaError("landmark document invalid:\n- " + "\n- ".join(errors))
        assert doc is not None
        return doc

    @staticmethod
    def load(path: Path) -> "LandmarkDocument":
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LandmarkSchemaError(f"{path}: not valid JSON: {exc}") from exc
        if not isinstance(data, Mapping):
            raise LandmarkSchemaError(f"{path}: top-level JSON value must be an object")
        return LandmarkDocument.from_dict(data)


def _parse_document(data: Mapping[str, Any], errors: List[str]) -> Optional[LandmarkDocument]:
    schema = data.get("schema")
    if schema != SCHEMA_NAME:
        errors.append(f"schema: expected {SCHEMA_NAME!r}, got {schema!r}")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION!r}, got {version!r}")

    view_id = data.get("view_id")
    if not isinstance(view_id, str) or view_id not in KNOWN_VIEW_IDS:
        errors.append(f"view_id: must be one of {KNOWN_VIEW_IDS}, got {view_id!r}")

    image_file = data.get("image_file")
    if not isinstance(image_file, str) or not image_file.strip():
        errors.append("image_file: must be a non-empty string")

    image_sha256 = data.get("image_sha256")
    if image_sha256 is not None:
        if not isinstance(image_sha256, str) or len(image_sha256) != 64 or any(c not in "0123456789abcdef" for c in image_sha256.lower()):
            errors.append(f"image_sha256: expected 64 lowercase hex chars, got {image_sha256!r}")
        else:
            image_sha256 = image_sha256.lower()

    dims = data.get("image_dimensions_px")
    image_dimensions_px: Optional[Tuple[int, int]] = None
    if dims is not None:
        ok = (
            isinstance(dims, Sequence) and not isinstance(dims, (str, bytes)) and len(dims) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in dims)
        )
        if not ok:
            errors.append(f"image_dimensions_px: expected [width, height] of positive ints, got {dims!r}")
        else:
            image_dimensions_px = (int(dims[0]), int(dims[1]))

    method = data.get("annotation_method")
    if not isinstance(method, str) or not method.strip():
        errors.append("annotation_method: must be a non-empty string")

    calibrated = data.get("calibrated", False)
    if not isinstance(calibrated, bool):
        errors.append(f"calibrated: must be a boolean, got {calibrated!r}")

    created_utc = data.get("created_utc", "")
    if not isinstance(created_utc, str):
        errors.append("created_utc: must be a string")
        created_utc = ""

    notes = data.get("notes", "")
    if not isinstance(notes, str):
        errors.append("notes: must be a string")
        notes = ""

    provenance = data.get("provenance", {})
    if not isinstance(provenance, Mapping):
        errors.append("provenance: must be an object")
        provenance = {}

    raw_points = data.get("points")
    points: Dict[str, LandmarkPoint] = {}
    if not isinstance(raw_points, Mapping):
        errors.append("points: must be an object keyed by canonical point id")
    else:
        unknown = sorted(set(raw_points) - set(CANONICAL_POINTS))
        if unknown:
            errors.append(f"points: unknown canonical point ids {unknown}")
        for name, payload in raw_points.items():
            if name not in CANONICAL_POINTS:
                continue
            before = len(errors)
            point = LandmarkPoint.from_dict(payload, f"points.{name}", errors)
            if point is not None and len(errors) == before:
                points[name] = point

    raw_unmapped = data.get("unmapped_points", [])
    unmapped_points: List[str] = []
    if not isinstance(raw_unmapped, Sequence) or isinstance(raw_unmapped, (str, bytes)):
        errors.append("unmapped_points: must be a list of canonical point ids")
    else:
        unknown_unmapped = sorted(set(raw_unmapped) - set(CANONICAL_POINTS))
        if unknown_unmapped:
            errors.append(f"unmapped_points: unknown point ids {unknown_unmapped}")
        else:
            duplicates = sorted({p for p in raw_unmapped if list(raw_unmapped).count(p) > 1})
            if duplicates:
                errors.append(f"unmapped_points: duplicate entries {duplicates}")
            unmapped_points = list(raw_unmapped)
        overlap = sorted(set(unmapped_points) & set(points))
        if overlap:
            errors.append(f"unmapped_points: points present in both mapped and unmapped: {overlap}")

    # Range check against declared dimensions (soft: reported as error, never silently clipped).
    if image_dimensions_px is not None:
        width, height = image_dimensions_px
        for name, point in points.items():
            if not (0.0 <= point.x <= float(width)):
                errors.append(f"points.{name}.x: {point.x} outside image width [0, {width}]")
            if not (0.0 <= point.y <= float(height)):
                errors.append(f"points.{name}.y: {point.y} outside image height [0, {height}]")

    if errors:
        return None

    return LandmarkDocument(
        view_id=view_id,
        image_file=image_file,
        image_sha256=image_sha256,
        image_dimensions_px=image_dimensions_px,
        annotation_method=method,
        points=points,
        unmapped_points=unmapped_points,
        calibrated=bool(calibrated),
        created_utc=created_utc,
        provenance=dict(provenance),
        notes=notes,
        schema_version=schema_version_safe(version),
    )


def schema_version_safe(version: Any) -> str:
    return version if isinstance(version, str) else SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Convenience: validation entry point returning error list (no raise)
# ---------------------------------------------------------------------------

def validate_document_dict(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    _parse_document(data, errors)
    return errors


def point_ids_for_group(group: str) -> Tuple[str, ...]:
    if group not in CANONICAL_GROUPS:
        raise KeyError(f"unknown group {group!r}; known: {sorted(CANONICAL_GROUPS)}")
    return CANONICAL_GROUPS[group]


def mirror_point_name(name: str) -> Optional[str]:
    """Return the subject-mirrored counterpart of a canonical point id, if any."""
    if name.endswith("_l"):
        candidate = name[:-2] + "_r"
    elif name.endswith("_r"):
        candidate = name[:-2] + "_l"
    else:
        return None
    return candidate if candidate in CANONICAL_POINTS else None


def iter_paired_points(points: Iterable[str]) -> Iterable[Tuple[str, str]]:
    """Yield (left, right) canonical pairs present in the iterable."""
    seen = set(points)
    for name in sorted(seen):
        if name.endswith("_l"):
            twin = mirror_point_name(name)
            if twin and twin in seen:
                yield name, twin
