# SPDX-License-Identifier: MIT
# LIVYNTH C001-GEO-03 — camera calibration / projection specification.
#
# Purpose: a single, dependency-light (numpy only) projection model shared by
# (a) the multi-view reconstruction lanes (Lane B visual hull, Lane A neural
#     reconstruction consumers) and
# (b) landmark projection/unprojection for Character 001
#     (`assets/characters/character_001/identity_capture_v1/`).
#
# !!! TRUTHFULNESS NOTICE !!!
# The 15 reference images are independently AI-generated "photographs", NOT
# calibrated scans. NO true intrinsic or extrinsic parameter can be recovered
# from them without an external calibration target (checkerboard/ChArUco) or a
# laser scanner. Every intrinsic number produced by this module is therefore
# ASSUMED, not measured, unless the caller explicitly overrides it with values
# measured elsewhere. Azimuths are KNOWN_ASSUMED (taken from the capture
# prompts in docs/characters/character_001_identity_capture.md, which describe
# the intended camera direction of each shot) — they are not verified by a
# calibration procedure either. See docs/C001_GEO03_CALIBRATION.md, section
# "ASSUMED vs MEASURED".
#
# Frame conventions (world = head-centred, right-handed)
# --------------------------------------------------------
#   +y  : toward the crown (up)
#   +z  : subject's facing direction (toward the viewer in the front view)
#   +x  : viewer's right in the front view == subject's ANATOMICAL LEFT
# The origin is the head centre (look-at point). All distances/angles in this
# module are millimetres/degrees. Image coordinates: origin top-left,
# +x right, +y DOWN (standard raster order).
# Positive azimuth rotates the camera toward the subject's anatomical left.
#
# Camera orbit
# ------------
#   azimuth_deg  0    -> camera directly in front of the face (+z)
#                +45  -> camera 45 deg toward subject's anatomical left  (view 02)
#                -45  -> camera 45 deg toward subject's anatomical right (view 03)
#                +90  -> true anatomical left profile                  (view 04)
#                -90  -> true anatomical right profile                 (view 05)
#                180  -> behind the subject (back view, view 06)
#   pitch_deg    0    -> eye-level shot (default)
#                -90  -> camera directly above looking straight down   (view 07 top)
#                      (image-up is the subject's occiput, i.e. the face appears
#                       at the BOTTOM of the frame; this is a convention, not a measurement)
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

SCHEMA_VERSION = "1.0.0"
TOOL_NAME = "livynth-geo-03/calibration_spec"
TOOL_VERSION = "1.0.0"

# Allowed values, mirroring the capture spec's shot definitions.
# 180 (not -180) is used for the back view.
ALLOWED_AZIMUTH_DEG: Tuple[float, ...] = (0.0, 45.0, -45.0, 90.0, -90.0, 180.0)
ALLOWED_PITCH_DEG: Tuple[float, ...] = (0.0, -90.0)

# Population-mean interocular distance (iris-to-iris, adults), used ONLY as a
# scale prior. Commonly cited anthropometric value (cf. Farkas measurements);
# NOT a measurement of this subject. ASSUMED — user may override per view.
DEFAULT_INTEROCULAR_MM = 63.0

# Long-lens assumption from the capture spec ("about 85–105 mm
# full-frame-equivalent"). fx = fy = focal * pixels / sensor_mm with a 24 x 32
# mm portrait crop and square pixels. 90 mm equivalent -> 4072.5 px on the
# 1086 px wide images. ASSUMED, not measured.
DEFAULT_FOCAL_EQUIVALENT_MM = 90.0
ASSUMED_SENSOR_WIDTH_MM = 24.0
ASSUMED_SENSOR_HEIGHT_MM = 32.0

# Studio-distance assumption for near-orthographic long-lens framing.
# ASSUMED, not measured. Lane B (visual hull) consumes this as the circle
# radius on which the eight cameras sit.
DEFAULT_CAMERA_RADIUS_MM = 1500.0

# Real SHA-256 of the eight main views, measured 2026-11-11 on the development
# machine (see docs/C001_GEO03_CALIBRATION.md). These are file digests, i.e.
# MEASURED facts about the artefacts, independent of any geometric assumption.
MAIN_VIEW_SHA256: Dict[str, str] = {
    "01_subject_front.png": "9d84f485883ce613d12d02d9f8f85e338ebe950d7248d522bf3117901eaed2dd",
    "02_subject_left_45.png": "86243d7eeb906fa955c95fe10341451256b116857b661549b8c3a11ed78030a9",
    "03_subject_right_45.png": "0f0c748a582763d4d9abf66130ea6a1759fb9e5c266f07580a03dd0b98e37a3a",
    "04_left_profile.png": "702eb69b4e3ddd9470a64c86e6c28e5ff9795c441b41d28e262001978597d1cd",
    "05_right_profile.png": "65101246912c969c55596bb97a5a3622001d10fc8497539b7d86844f0d863eba",
    "06_back_head.png": "8339543d8b383dfd17fbdb750d4df9ad2fa7526d5738899e598ecb7ef9bfd684",
    "07_top_head.png": "219cba0eb70144f0c7d8e0cc9cba33e3b98c568d97f7bc0dd2553eeb755f0b4a",
    "08_front_closeup.png": "af8e3a85043f7eb998a653da72885f73d255d8f9d2b04138d965bf2dc6b832cd",
}

# Real pixel dimensions of the eight main views, measured 2026-11-11 with PIL.
MAIN_VIEW_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    "01_subject_front.png": (1086, 1448),
    "02_subject_left_45.png": (1086, 1448),
    "03_subject_right_45.png": (1086, 1448),
    "04_left_profile.png": (1086, 1448),
    "05_right_profile.png": (1086, 1448),
    "06_back_head.png": (1086, 1448),
    "07_top_head.png": (1087, 1447),
    "08_front_closeup.png": (1087, 1446),
}

# View definitions for the eight main views: file -> (view_id, azimuth, pitch).
# Azimuths/pitches are KNOWN_ASSUMED from the capture prompts, not measured.
MAIN_VIEW_GEOMETRY: Dict[str, Tuple[str, float, float]] = {
    "01_subject_front.png": ("01", 0.0, 0.0),
    "02_subject_left_45.png": ("02", 45.0, 0.0),
    "03_subject_right_45.png": ("03", -45.0, 0.0),
    "04_left_profile.png": ("04", 90.0, 0.0),
    "05_right_profile.png": ("05", -90.0, 0.0),
    "06_back_head.png": ("06", 180.0, 0.0),
    "07_top_head.png": ("07", 0.0, -90.0),          # azimuth irrelevant when pitch = -90
    "08_front_closeup.png": ("08", 0.0, 0.0),        # tighter crop, same 0 deg axis
}

# Close-ups (ears/eyes/iris/skin/lips/hair) are detail references, NOT orbit
# views; they are deliberately excluded from the reconstruction camera circle.
DETAIL_VIEW_FILES: Tuple[str, ...] = (
    "09_left_ear.png",
    "10_right_ear.png",
    "11_eyes_closeup.png",
    "12_iris_macro.png",
    "13_skin_macro.png",
    "14_lips_closeup.png",
    "15_hair_closeup.png",
)


class CalibrationError(ValueError):
    """Raised when calibration data fails validation or (de)serialization."""


def compute_sha256(path: str | Path, chunk_bytes: int = 1 << 20) -> str:
    """Return the hex SHA-256 of a file. MEASURED, deterministic."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_bytes), b""):
            h.update(chunk)
    return h.hexdigest()


def mm_per_pixel_from_interocular(interocular_px: float,
                                  interocular_mm: float = DEFAULT_INTEROCULAR_MM
                                  ) -> float:
    """Scale prior: mm per pixel given a measured pupil/iris-centre spacing.

    interocular_mm is an ASSUMED population prior (default 63 mm) unless the
    caller overrides it with a subject-specific value. Raises CalibrationError
    on non-positive inputs (never silently divides by zero).
    """
    if interocular_px <= 0:
        raise CalibrationError(f"interocular_px must be > 0, got {interocular_px}")
    if interocular_mm <= 0:
        raise CalibrationError(f"interocular_mm must be > 0, got {interocular_mm}")
    return interocular_mm / interocular_px


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n == 0.0:
        raise CalibrationError("zero-length vector in camera basis construction")
    return v / n


def camera_position(radius_mm: float,
                    azimuth_deg: float,
                    pitch_deg: float,
                    look_at_mm: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """World-space camera position for an orbit view around the head centre.

    radius_mm  : ASSUMED camera distance (default 1500 mm, user-overridable).
    azimuth_deg: orbit angle; + toward subject's anatomical left.
    pitch_deg  : 0 = eye level, -90 = directly above the crown.

    Returns a (3,) float64 array. This is where Lane B gets its circle of
    camera positions: same radius, same look_at, per-view azimuth.
    """
    if radius_mm <= 0:
        raise CalibrationError(f"radius_mm must be > 0, got {radius_mm}")
    az = math.radians(azimuth_deg)
    pitch = math.radians(pitch_deg)
    horizontal = radius_mm * math.cos(pitch)
    offset = np.array([
        horizontal * math.sin(az),
        -radius_mm * math.sin(pitch),
        horizontal * math.cos(az),
    ], dtype=np.float64)
    look_at = np.asarray(look_at_mm, dtype=np.float64)
    if look_at.shape != (3,):
        raise CalibrationError(f"look_at_mm must be a 3-vector, got shape {look_at.shape}")
    return look_at + offset


def camera_basis(look_at_mm: Sequence[float],
                 position_mm: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (right, up, forward) orthonormal camera-basis vectors.

    forward points from the camera toward the look-at point (the direction the
    camera looks). right/up are image +x/+y axes in world coordinates.
    Degenerate case (looking straight down/up): image-up is chosen as world -z
    (occiput direction) by convention; this only affects the top view and is
    an ASSUMED framing convention, not a measurement.
    """
    look_at = np.asarray(look_at_mm, dtype=np.float64)
    forward = _unit(look_at - position_mm)
    up_ref = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    if abs(float(np.dot(forward, up_ref))) > 0.99:
        up_ref = np.array([0.0, 0.0, -1.0], dtype=np.float64)
    right = _unit(np.cross(forward, up_ref))
    up = np.cross(right, forward)
    # up is already unit-length: right ⊥ forward and both unit.
    return right, up, forward


def project_points(points_world: np.ndarray, view: "ViewCalibration") -> np.ndarray:
    """Project (N,3) world/head-centred points to (N,2) pixel coordinates.

    Points behind the camera (depth <= 0) raise CalibrationError — callers
    must cull them explicitly rather than receive garbage pixels.
    """
    pts = np.asarray(points_world, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3:
        raise CalibrationError(f"points_world must be (N,3), got {pts.shape}")
    right, up, forward = view.camera_basis()
    rel = pts - view.camera_position()
    z = rel @ forward
    if np.any(z <= 0.0):
        bad = int(np.sum(z <= 0.0))
        raise CalibrationError(f"{bad} point(s) lie at or behind the camera plane")
    x = rel @ right
    y = rel @ up
    px = view.fx * (x / z) + view.cx
    py = view.cy - view.fy * (y / z)   # image y grows downward
    return np.stack([px, py], axis=1)


def pixel_to_ray(px: float, py: float, view: "ViewCalibration") -> Tuple[np.ndarray, np.ndarray]:
    """Return (origin, unit_direction) of the world-space ray through a pixel."""
    right, up, forward = view.camera_basis()
    x = (px - view.cx) / view.fx
    y = (view.cy - py) / view.fy
    direction = _unit(x * right + y * up + forward)
    return view.camera_position(), direction


def unproject_pixel(px: float, py: float, view: "ViewCalibration",
                    depth_mm: float) -> np.ndarray:
    """Back-project a pixel to world space at a given forward depth (mm).

    depth_mm is the distance along the optical axis (i.e. the projected z),
    not the Euclidean ray length. Guarantees project_points(unproject_pixel(p))
    == p exactly.
    """
    if depth_mm <= 0:
        raise CalibrationError(f"depth_mm must be > 0, got {depth_mm}")
    right, up, forward = view.camera_basis()
    x = (px - view.cx) / view.fx
    y = (view.cy - py) / view.fy
    return view.camera_position() + depth_mm * (x * right + y * up + forward)


def _is_finite_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def intrinsics_from_focal(image_width: int,
                          image_height: int,
                          focal_equivalent_mm: float = DEFAULT_FOCAL_EQUIVALENT_MM,
                          sensor_width_mm: float = ASSUMED_SENSOR_WIDTH_MM,
                          sensor_height_mm: float = ASSUMED_SENSOR_HEIGHT_MM
                          ) -> Tuple[float, float]:
    """fx, fy from an ASSUMED long-lens portrait-crop sensor (default 90 mm).

    ASSUMED, not measured: the reference images carry no calibration target.
    Square pixels are assumed; fx and fy come out equal for a 24x32 mm crop.
    """
    if image_width <= 0 or image_height <= 0:
        raise CalibrationError("image dimensions must be > 0")
    if focal_equivalent_mm <= 0:
        raise CalibrationError("focal_equivalent_mm must be > 0")
    fx = focal_equivalent_mm * image_width / sensor_width_mm
    fy = focal_equivalent_mm * image_height / sensor_height_mm
    return float(fx), float(fy)


def _default_status(azimuth_deg: float, pitch_deg: float) -> Dict[str, str]:
    return {
        "intrinsics": "ASSUMED",        # no calibration target exists; long-lens prior only
        "azimuth_pitch": "KNOWN_ASSUMED",  # from capture prompts, never camera-verified
        "scale": "ASSUMED",             # 63 mm interocular prior; user may override
        "radius": "ASSUMED",            # 1500 mm studio-distance prior; user may override
        "principal_point": "ASSUMED",   # assumed at image centre
        "image_sha256": "MEASURED",     # file digest of the exact inputs
        "dimensions": "MEASURED",       # PIL-reported pixel size
    }


@dataclass
class ViewCalibration:
    """Calibration for one view of the Character 001 capture."""
    view_id: str
    label: str
    image_file: str
    image_sha256: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    azimuth_deg: float
    pitch_deg: float = 0.0
    radius_mm: float = DEFAULT_CAMERA_RADIUS_MM
    interocular_mm: float = DEFAULT_INTEROCULAR_MM
    focal_equivalent_mm: float = DEFAULT_FOCAL_EQUIVALENT_MM
    look_at_mm: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    # ---- geometry helpers -------------------------------------------------
    def camera_position(self) -> np.ndarray:
        return camera_position(self.radius_mm, self.azimuth_deg, self.pitch_deg,
                               self.look_at_mm)

    def camera_basis(self):
        return camera_basis(self.look_at_mm, self.camera_position())

    def project(self, points_world: np.ndarray) -> np.ndarray:
        return project_points(points_world, self)

    def unproject(self, px: float, py: float, depth_mm: float) -> np.ndarray:
        return unproject_pixel(px, py, self, depth_mm)

    def pixel_ray(self, px: float, py: float):
        return pixel_to_ray(px, py, self)

    # ---- validation --------------------------------------------------------
    def validate(self) -> List[str]:
        """Return a list of human-readable issues; empty list means valid."""
        issues: List[str] = []
        if not isinstance(self.view_id, str) or not self.view_id.strip():
            issues.append("view_id must be a non-empty string")
        if not isinstance(self.label, str) or not self.label.strip():
            issues.append(f"view {self.view_id!r}: label must be a non-empty string")
        if not isinstance(self.image_file, str) or not self.image_file.strip():
            issues.append(f"view {self.view_id!r}: image_file must be a non-empty string")
        if not isinstance(self.image_sha256, str):
            issues.append(f"view {self.view_id!r}: image_sha256 is required (string)")
        elif len(self.image_sha256) != 64 or any(
                c not in "0123456789abcdef" for c in self.image_sha256):
            issues.append(f"view {self.view_id!r}: image_sha256 must be 64 lowercase hex chars")
        if not isinstance(self.width, int) or isinstance(self.width, bool) or self.width <= 0:
            issues.append(f"view {self.view_id!r}: width must be a positive int, got {self.width!r}")
        if not isinstance(self.height, int) or isinstance(self.height, bool) or self.height <= 0:
            issues.append(f"view {self.view_id!r}: height must be a positive int, got {self.height!r}")
        for name in ("fx", "fy", "cx", "cy", "azimuth_deg", "pitch_deg",
                     "radius_mm", "interocular_mm", "focal_equivalent_mm"):
            if not _is_finite_number(getattr(self, name)):
                issues.append(f"view {self.view_id!r}: {name} must be a finite number, "
                              f"got {getattr(self, name)!r}")
        if _is_finite_number(self.fx) and self.fx <= 0:
            issues.append(f"view {self.view_id!r}: fx must be > 0, got {self.fx}")
        if _is_finite_number(self.fy) and self.fy <= 0:
            issues.append(f"view {self.view_id!r}: fy must be > 0, got {self.fy}")
        if isinstance(self.width, int) and _is_finite_number(self.cx):
            if not (0.0 <= self.cx <= float(self.width)):
                issues.append(f"view {self.view_id!r}: cx {self.cx} outside [0, {self.width}]")
        if isinstance(self.height, int) and _is_finite_number(self.cy):
            if not (0.0 <= self.cy <= float(self.height)):
                issues.append(f"view {self.view_id!r}: cy {self.cy} outside [0, {self.height}]")
        if _is_finite_number(self.azimuth_deg) and self.azimuth_deg not in ALLOWED_AZIMUTH_DEG:
            issues.append(f"view {self.view_id!r}: azimuth_deg {self.azimuth_deg} not in "
                          f"{ALLOWED_AZIMUTH_DEG}")
        if _is_finite_number(self.pitch_deg) and self.pitch_deg not in ALLOWED_PITCH_DEG:
            issues.append(f"view {self.view_id!r}: pitch_deg {self.pitch_deg} not in "
                          f"{ALLOWED_PITCH_DEG}")
        if _is_finite_number(self.radius_mm) and self.radius_mm <= 0:
            issues.append(f"view {self.view_id!r}: radius_mm must be > 0, got {self.radius_mm}")
        if _is_finite_number(self.interocular_mm) and self.interocular_mm <= 0:
            issues.append(f"view {self.view_id!r}: interocular_mm must be > 0, got {self.interocular_mm}")
        if len(self.look_at_mm) != 3 or any(not _is_finite_number(v) for v in self.look_at_mm):
            issues.append(f"view {self.view_id!r}: look_at_mm must be 3 finite numbers, "
                          f"got {self.look_at_mm!r}")
        return issues

    # ---- (de)serialization ---------------------------------------------------
    _VIEW_KEYS = ("view_id", "label", "image_file", "image_sha256", "width", "height",
                  "fx", "fy", "cx", "cy", "azimuth_deg", "pitch_deg", "radius_mm",
                  "interocular_mm", "focal_equivalent_mm", "look_at_mm", "status", "notes")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_id": self.view_id,
            "label": self.label,
            "image_file": self.image_file,
            "image_sha256": self.image_sha256,
            "width": self.width,
            "height": self.height,
            "fx": float(self.fx),
            "fy": float(self.fy),
            "cx": float(self.cx),
            "cy": float(self.cy),
            "azimuth_deg": float(self.azimuth_deg),
            "pitch_deg": float(self.pitch_deg),
            "radius_mm": float(self.radius_mm),
            "interocular_mm": float(self.interocular_mm),
            "focal_equivalent_mm": float(self.focal_equivalent_mm),
            "look_at_mm": [float(v) for v in self.look_at_mm],
            "status": dict(self.status),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ViewCalibration":
        if not isinstance(data, dict):
            raise CalibrationError(f"view must be an object, got {type(data).__name__}")
        problems = [k for k in data if k not in cls._VIEW_KEYS]
        if problems:
            raise CalibrationError(f"unknown view keys rejected: {sorted(problems)}")
        missing = [k for k in cls._VIEW_KEYS
                   if k not in data and k not in ("status", "notes")]
        if missing:
            raise CalibrationError(f"missing required view keys: {sorted(missing)}")
        look = data["look_at_mm"]
        if not (isinstance(look, (list, tuple)) and len(look) == 3):
            raise CalibrationError(f"look_at_mm must be a 3-element list, got {look!r}")
        status = data.get("status", {})
        if not isinstance(status, dict):
            raise CalibrationError(f"status must be an object, got {type(status).__name__}")
        try:
            view = cls(
                view_id=data["view_id"],
                label=data["label"],
                image_file=data["image_file"],
                image_sha256=data["image_sha256"],
                width=data["width"],
                height=data["height"],
                fx=float(data["fx"]),
                fy=float(data["fy"]),
                cx=float(data["cx"]),
                cy=float(data["cy"]),
                azimuth_deg=float(data["azimuth_deg"]),
                pitch_deg=float(data.get("pitch_deg", 0.0)),
                radius_mm=float(data.get("radius_mm", DEFAULT_CAMERA_RADIUS_MM)),
                interocular_mm=float(data.get("interocular_mm", DEFAULT_INTEROCULAR_MM)),
                focal_equivalent_mm=float(data.get("focal_equivalent_mm",
                                                   DEFAULT_FOCAL_EQUIVALENT_MM)),
                look_at_mm=tuple(float(v) for v in look),
                status=dict(status),
                notes=str(data.get("notes", "")),
            )
        except (TypeError, ValueError) as exc:
            raise CalibrationError(f"invalid view field: {exc}") from exc
        issues = view.validate()
        if issues:
            raise CalibrationError("invalid view: " + "; ".join(issues))
        return view


@dataclass
class CalibrationSet:
    """A versioned, provenance-carrying collection of view calibrations."""
    views: List[ViewCalibration]
    estimator: str
    created: str = field(default_factory=lambda: date.today().isoformat())
    schema_version: str = SCHEMA_VERSION
    tool: str = TOOL_NAME
    tool_version: str = TOOL_VERSION
    method: str = "capture-spec-azimuth+long-lens-assumption"
    notes: str = ""

    # ---- validation ----------------------------------------------------------
    _SET_KEYS = ("schema_version", "tool", "tool_version", "created", "estimator",
                 "method", "notes", "views")

    def validate(self) -> List[str]:
        issues: List[str] = []
        if self.schema_version != SCHEMA_VERSION:
            issues.append(f"schema_version {self.schema_version!r} != {SCHEMA_VERSION!r}")
        if not isinstance(self.estimator, str) or not self.estimator.strip():
            issues.append("estimator must be a non-empty string")
        if not isinstance(self.created, str) or not self.created.strip():
            issues.append("created must be an ISO date string")
        else:
            try:
                date.fromisoformat(self.created)
            except ValueError:
                issues.append(f"created {self.created!r} is not an ISO date (YYYY-MM-DD)")
        if not self.views:
            issues.append("at least one view is required")
        seen_ids = set()
        for v in self.views:
            issues.extend(v.validate())
            if v.view_id in seen_ids:
                issues.append(f"duplicate view_id {v.view_id!r}")
            seen_ids.add(v.view_id)
        return issues

    def verify_image_hashes(self, images_dir: str | Path
                            ) -> List[Tuple[str, bool, str, str]]:
        """Hash the real files and compare against the recorded digests.

        Returns (view_id, ok, expected, actual) tuples. actual == '<missing>'
        when the file does not exist under images_dir.
        """
        images_dir = Path(images_dir)
        results: List[Tuple[str, bool, str, str]] = []
        for v in self.views:
            p = images_dir / v.image_file
            if not p.is_file():
                results.append((v.view_id, False, v.image_sha256, "<missing>"))
                continue
            actual = compute_sha256(p)
            results.append((v.view_id, actual == v.image_sha256, v.image_sha256, actual))
        return results

    # ---- (de)serialization ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "created": self.created,
            "estimator": self.estimator,
            "method": self.method,
            "notes": self.notes,
            "views": [v.to_dict() for v in self.views],
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    def save_json(self, path: str | Path, indent: int = 2) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(indent=indent, sort_keys=False) + "\n",
                        encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationSet":
        if not isinstance(data, dict):
            raise CalibrationError(f"calibration set must be an object, got {type(data).__name__}")
        problems = [k for k in data if k not in cls._SET_KEYS]
        if problems:
            raise CalibrationError(f"unknown top-level keys rejected: {sorted(problems)}")
        missing = [k for k in ("schema_version", "created", "estimator", "views") if k not in data]
        if missing:
            raise CalibrationError(f"missing required top-level keys: {sorted(missing)}")
        if data["schema_version"] != SCHEMA_VERSION:
            raise CalibrationError(
                f"schema_version {data['schema_version']!r} not supported; expected {SCHEMA_VERSION!r}")
        if not isinstance(data["views"], list):
            raise CalibrationError("views must be a list")
        views = [ViewCalibration.from_dict(v) for v in data["views"]]
        cs = cls(
            views=views,
            estimator=data["estimator"],
            created=data["created"],
            schema_version=data["schema_version"],
            tool=data.get("tool", TOOL_NAME),
            tool_version=data.get("tool_version", TOOL_VERSION),
            method=data.get("method", "capture-spec-azimuth+long-lens-assumption"),
            notes=str(data.get("notes", "")),
        )
        issues = cs.validate()
        if issues:
            raise CalibrationError("invalid calibration set: " + "; ".join(issues))
        return cs

    @classmethod
    def from_json(cls, text: str) -> "CalibrationSet":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CalibrationError(f"calibration JSON is not valid JSON: {exc}") from exc
        return cls.from_dict(data)

    @classmethod
    def load_json(cls, path: str | Path) -> "CalibrationSet":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def view(self, view_id: str) -> ViewCalibration:
        for v in self.views:
            if v.view_id == view_id:
                return v
        raise CalibrationError(f"view_id {view_id!r} not in this calibration set")


def build_default_calibration_set(
        estimator: str = "assumed-capture-spec",
        created: Optional[str] = None,
        radius_mm: float = DEFAULT_CAMERA_RADIUS_MM,
        interocular_mm: float = DEFAULT_INTEROCULAR_MM,
        focal_equivalent_mm: float = DEFAULT_FOCAL_EQUIVALENT_MM,
        notes: str = "") -> CalibrationSet:
    """Construct the standard 8-orbit-view set for identity_capture_v1.

    Hashes/dimensions are MEASURED (2026-11-11, this development machine);
    azimuths/pitches/intrinsics/radius/scale are ASSUMED per the capture spec.
    Close-up views 09-15 are detail references, not orbit cameras, and are
    intentionally excluded. The 1087x1447 / 1087x1446 odd sizes of views 07/08
    are recorded as measured.
    """
    fx_by_file: Dict[str, Tuple[float, float]] = {}
    views: List[ViewCalibration] = []
    for image_file, (view_id, azimuth, pitch) in MAIN_VIEW_GEOMETRY.items():
        width, height = MAIN_VIEW_DIMENSIONS[image_file]
        if image_file not in fx_by_file:
            fx_by_file[image_file] = intrinsics_from_focal(
                width, height, focal_equivalent_mm)
        fx, fy = fx_by_file[image_file]
        label = image_file.replace("_subject", "").replace(".png", "").split("_", 1)[1]
        is_closeup = image_file.startswith("08")
        view_notes = (
            ("front close-up: same 0 deg axis, tighter crop; framing ASSUMED, "
             "camera distance NOT verified; exclude from strict silhouette fusion "
             "until iris-parallax is checked." if is_closeup else
             "orbit view; azimuth/pitch from capture prompt (KNOWN_ASSUMED).")
        )
        views.append(ViewCalibration(
            view_id=view_id,
            label=label,
            image_file=image_file,
            image_sha256=MAIN_VIEW_SHA256[image_file],
            width=width,
            height=height,
            fx=fx,
            fy=fy,
            cx=width / 2.0,
            cy=height / 2.0,
            azimuth_deg=azimuth,
            pitch_deg=pitch,
            radius_mm=radius_mm,
            interocular_mm=interocular_mm,
            focal_equivalent_mm=focal_equivalent_mm,
            look_at_mm=(0.0, 0.0, 0.0),
            status=_default_status(azimuth, pitch),
            notes=view_notes,
        ))
    return CalibrationSet(
        views=views,
        estimator=estimator,
        created=created or date.today().isoformat(),
        method="capture-spec-azimuth+long-lens-assumption",
        notes=notes or (
            "C001-GEO-03 baseline calibration. Intrinsics/extrinsics are ASSUMED "
            "(85-105 mm long-lens prior; capture prompts for azimuths); no "
            "checkerboard calibration exists. image_sha256 and dimensions are "
            "MEASURED. Detail close-ups (09-15) are excluded from the orbit set."
        ),
    )