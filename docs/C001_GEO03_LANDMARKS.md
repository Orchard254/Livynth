# C001-GEO-03 — Character 001 landmark schema and detection report

**Status:** implemented + unit-tested; detection on reference images reported below with honest success/failure per view.
**Worktree:** `livynth-c001-geo03-landmarks` (branchless @ 31a9b19), `geo/landmark_spec.py`, `geo/detect_landmarks.py`, `geo/migrate_legacy_landmarks.py`, `geo/tests_landmarks/`.
**Date:** 2026-11-11
**Author:** landmark-engineer (C001-GEO-03)

> **Hard limit:** the 15 reference images are uncalibrated AI-generated portraits. Everything measured from them is a measurement of the *drawing*, not of a real head. `calibrated` is `false` in every document produced by these tools. Do not use these landmarks as metric anatomy.

## 1. Canonical schema (`livynth.c001.landmarks` 2.0.0)

Image-space pixel coordinates (x right, y down, origin top-left). `_l`/`_r` suffixes are **subject-anatomical** (subject's left/right), *not* image-left/right. On an unmirrored frontal photo the subject's left appears on the image right. Whether the AI reference images are anatomically mirrored is **unknown**; the convention is documented, never silently flipped.

### Point registry (37 canonical points, 6 groups)

| Group | Points |
|---|---|
| brows (6) | `brow_inner_l/r`, `brow_mid_l/r`, `brow_outer_l/r` |
| eyes (12) | `upper_eyelid_l/r`, `lower_eyelid_l/r`, `canthus_inner_l/r`, `canthus_outer_l/r`, `pupil_center_l/r`, `iris_center_l/r` |
| nose (5) | `nose_bridge_top`, `nose_bridge_bottom`, `nostril_l/r`, `nose_tip` |
| mouth (4) | `mouth_corner_l/r`, `upper_lip_mid`, `lower_lip_mid` |
| face (4) | `chin`, `jaw_angle_l/r`, `hairline_center` |
| ears (6) | `ear_top_l/r`, `ear_bottom_l/r`, `tragus_l/r` |

### Document fields

`schema`, `schema_version` (`"2.0.0"`), `view_id` (one of the 15 known ids), `image_file`, `image_sha256` (64 lowercase hex), `image_dimensions_px` `[w, h]`, `annotation_method`, `calibrated` (always `false` for these images), `created_utc`, `points` (map name → `{x, y, confidence, source}`), `unmapped_points` (canonical ids with no usable detection), `provenance` (tool, versions, command context, notes), `notes`.

### Per-point confidence

- float in `[0, 1]` — detection outputs use a **constant heuristic** (`0.9` detected, `0.6` approximate stand-ins such as hairline/jaw/pupil≈iris). MediaPipe FaceMesh exports **no per-landmark confidence**; `0.9` means "detected on this drawing", nothing more.
- the literal string `"legacy-manual"` — only from the legacy `geo/character001_landmarks.json` migration.
- Unknown categorical labels are rejected by the validator.

### Validation rules (see `geo/landmark_spec.py`)

- schema name/version must match exactly;
- `view_id` must be one of the 15 known ids;
- point ids must exist in the canonical registry (unknown ids rejected);
- coordinates must be finite and inside declared `image_dimensions_px`;
- `confidence` in `[0, 1]` or an allowed categorical label;
- a point may not appear in both `points` and `unmapped_points`; duplicates in `unmapped_points` rejected;
- serialised JSON round-trips through `LandmarkDocument.load`.

## 2. View inventory and outcome

| View id | File | Annotations | Method | Points | Unmapped |
|---|---|---|---|---|---|
| front | 01_subject_front.png | yes | manual visual estimate | 37 | 0 |
| left_45 | 02_subject_left_45.png | yes | manual visual estimate | 34 | 3 (far ear) |
| right_45 | 03_subject_right_45.png | yes | manual visual estimate | 34 | 3 (far ear) |
| profile_left | 04_left_profile.png | yes | manual visual estimate | 22 | 15 (far side occluded) |
| profile_right | 05_right_profile.png | yes | manual visual estimate | 22 | 15 (far side occluded) |
| back | 06_back_head.png | partial | manual visual estimate | 4 | 33 |
| top | 07_top_head.png | partial | manual visual estimate | 6 | 31 |
| front_closeup | 08_front_closeup.png | yes | manual visual estimate | 37 | 0 |
| left_ear | 09_left_ear.png | partial | manual visual estimate | 3 | 34 |
| right_ear | 10_right_ear.png | partial | manual visual estimate | 3 | 34 |
| eyes_closeup | 11_eyes_closeup.png | partial | manual visual estimate | 19 | 18 |
| iris_macro | 12_iris_macro.png | partial | manual visual estimate | 6 | 31 |
| skin_macro | 13_skin_macro.png | partial | manual visual estimate | 10 | 27 |
| lips_closeup | 14_lips_closeup.png | partial | manual visual estimate | 5 | 32 |
| hair_closeup | 15_hair_closeup.png | partial | manual visual estimate | 21 | 16 |

MediaPipe FaceMesh detection was **attempted and blocked** — see §4. No detection-derived JSON exists; all per-view JSONs are manual visual estimates.

## 3. Legacy migration

`geo/migrate_legacy_landmarks.py` converts `geo/character001_landmarks.json` (schema `livynth.c001.reference-landmarks.v1`) **verbatim**:

- `eyes.left` → `iris_center_l`, `eyes.right` → `iris_center_r`, `chin` → `chin`,
  `mouth_corners[0]` → `mouth_corner_l`, `mouth_corners[1]` → `mouth_corner_r`;
- every migrated point carries `confidence = "legacy-manual"`;
- the legacy file does not state whether its labels mean image-left/right or anatomical left/right; labels are carried verbatim and flagged in `provenance.migration_notes` — **interpretation is the consumer's responsibility**;
- all other canonical points are listed in `unmapped_points`;
- the migrator refuses to run on any input whose schema string is not the expected legacy schema.

Output: `output/landmarks/front_legacy_manual.json` (generated, not committed).

## 4. Detection attempt and honest failure list (2026-11-11)

**Environment:** Windows, Python 3.14.7, worktree-local venv `.venv-landmarks` (pip 26.3, cache reused).
**Install command:** `python -m pip install mediapipe opencv-python-headless`
**Install result:** SUCCESS (after one 900 s foreground timeout on a ~170 kB/s link; re-run completed):
`mediapipe-1.2.2`, `opencv-contrib-python-5.0.0.93`, `opencv-python-headless-5.0.0.93`, `numpy-2.5.4`.
**Import test:** `import cv2` → 5.0.0 OK; `import mediapipe` → `__version__ = 1.2.2` OK; `from mediapipe.tasks.python import vision` → OK (`FaceLandmarker` present). **BUT** `from mediapipe.python.solutions import face_mesh` → `ModuleNotFoundError: No module named 'mediapipe.python'`.

### Findings

1. mediapipe 1.2.2 for CPython 3.14 ships **no `solutions` subpackage** — the classic `FaceMesh` (468-pt atlas + iris refine) used by `geo/detect_landmarks.py`'s reference mapping **does not exist in this build**.
2. The Tasks `FaceLandmarker` API exists but requires an external `face_landmarker.task` model asset. It is **not bundled** in the wheel (verified: no `*.task`/`*.tflite` files under `site-packages/mediapipe/`) and the API does **not** auto-fetch it. Downloading model weights was explicitly out of scope, so detection was **not executed**.
3. OpenCV 5.0.0.93 ships **no Haar/LBP cascade XMLs** in `cv2/data` (directory contains only `__init__.py`), so the obvious bundled-cascade face-rectangle fallback is also unavailable without downloads.
4. `geo/detect_landmarks.py` now probes the API up front and, on absence, writes `output/landmarks/detection_report.json` with `status: api-unavailable` for every requested view and exits with code **3** (verified: exit 3, report written, no landmark JSONs emitted, no crash).

### Per-view detection outcome

| View | MediaPipe detection | Fallback result |
|---|---|---|
| front, left_45, right_45, profile_left, profile_right, front_closeup | **NOT RUN** (API unavailable) | manual estimate written |
| back, top | **NOT RUN** | manual estimate written (partial; no facial surface) |
| left_ear, right_ear, eyes_closeup, iris_macro, skin_macro, lips_closeup, hair_closeup | **NOT RUN** | manual estimate written (partial) |
| ALL 15 VIEWS | **mediapipe FaceMesh: blocked — UNVERIFIED, never executed** | manual estimate fallback |

**Honest failure list:** every view fails MediaPipe detection *by construction* (API/model unavailable), not because a face was not found. Any earlier claim that detection "ran" on these images would be false. `MP_INDEX` in `geo/detect_landmarks.py` is an untested reference mapping — **UNVERIFIED** until a compatible mediapipe (or an approved `face_landmarker.task`) is available and wired in.

### Fallback actually applied

Manual visual estimates (`geo/manual_annotations.py`), hand-placed on each of the 15 images, labelled `annotation_method = "manual-visual-estimate (AI-generated uncalibrated image; not a detection)"`, confidence 0.3/0.2/0.15, expected error tens of pixels. Overlays were visually checked for `front`, `profile_left`, `eyes_closeup`, `lips_closeup` — points land on the intended drawn features; gross placement errors were not found, but sub-20 px placement is NOT claimed.

## 5. Visual overlays

Overlay PNGs (points drawn on the source images) are written to `output/landmarks/overlays/`. They exist to let a human verify that detected points sit where the drawing puts the features. They are QA aids, not ground truth.

Known overlay-verifiable mapping (checked on `01_subject_front.png`, 2026-11-11):

| Canonical point | MediaPipe index | Note |
|---|---|---|
| canthus_outer_r / inner_r | 33 / 133 | unmirrored frontal: image-left |
| canthus_outer_l / inner_l | 263 / 362 | image-right |
| upper/lower eyelid_r | 159 / 145 | |
| upper/lower eyelid_l | 386 / 374 | |
| brow_inner/mid/outer_r | 107 / 66 / 46 | |
| brow_inner/mid/outer_l | 336 / 296 / 276 | |
| iris_center_r / l | 468 / 473 | `refine_landmarks=True` |
| pupil_center_r / l | 468 / 473 | **approximation**: pupil not separately detectable; equals iris centre, confidence 0.6 |
| nose_bridge_top / bottom | 168 / 6 | |
| nose_tip | 1 | |
| nostril_r / l | 129 / 358 | |
| mouth_corner_r / l | 61 / 291 | |
| upper/lower_lip_mid | 13 / 14 | |
| chin | 152 | |
| jaw_angle_r / l | 172 / 397 | **stand-in** for gonion (FaceMesh has no gonion), confidence 0.6 |
| hairline_center | 10 | **stand-in** for hairline (FaceMesh top-of-oval), confidence 0.6 — true hairline not modelled |
| ears (all 6) | — | no FaceMesh topology → always `unmapped_points` in detection output |

## 6. Exact commands and results

(TO BE FILLED)

## 7. Limits

1. **AI images are not calibrated.** No metric scale, no camera model, no lens. Azimuthal angles (0/±45/±90/back/top) are shot-definition labels, not measurements.
2. **Detections measure the drawing.** Painterly/stylized regions, specular highlights, hair overlapping brows, and profile self-occlusion all shift the mesh; treat profile-view landmarks with skepticism.
3. **Left/right anatomy of the drawings is unverified.** The scheme uses subject-anatomical labels following MediaPipe's own left/right assignment; if the AI generator mirrored anatomy, labels are systematically swapped — visually indistinguishable without an identity-consistent check (e.g. mole/scar asymmetry), which does not exist for Character 001 yet.
4. **Pupil ≈ iris centre** (constant offset not modelled).
5. **Jaw angles and hairline are nearest-topology stand-ins**, not anatomical detections.
6. **Ears are never detected** by FaceMesh; ear landmarks require manual annotation (planned, not done).
7. **Per-point confidence is heuristic**, not probabilistic.
8. **Profile views:** MediaPipe FaceMesh is trained on near-frontal faces; ±90° profiles frequently produce no face or grossly elongated meshes. Report, don't trust.
9. The legacy migration preserves legacy labels verbatim; it does not resolve their left/right ambiguity.
10. No temporal or multi-view consistency of these landmarks has been established yet; cross-view fusion is the camera-calibrator/identity-auditor gate's concern.

## 8. Integration contract (camera-calibrator + identity-auditor gates)

Downstream consumers may rely on:

- `geo.landmark_spec.LandmarkDocument.load(path)` — raises `LandmarkSchemaError` listing every violation; never returns a partially valid document.
- Round-trip stability: `to_json(from_dict(x)) == x` field-for-field for valid documents.
- `points` and `unmapped_points` partition the 37 canonical ids (a point appears in exactly one).
- `image_sha256` ties a document to the exact PNG it was measured from (verify with `geo.landmark_spec.sha256_file`).
- `calibrated == false` for every document from this pipeline; consumers must not strip or ignore the flag.
- `view_id` is one of the 15 known ids; consumers needing geometry views use `GEOMETRY_VIEWS`; consumers needing plausible full-face detections use `FACE_MESH_PLAUSIBLE_VIEWS`.
- Subject-anatomical `_l`/`_r` convention (see §1). Mirroring transforms: `x' = image_width - x`, swap `_l`↔`_r` suffixes (see `mirror_point_name` / `iter_paired_points` and `tests_landmarks/test_synthetic_consistency.py`).
- `camera-calibrator` may consume `image_dimensions_px` + `view_id` + the documented view angles; it must treat `image_sha256` as the join key and must not assume metric scale.
- `identity-auditor` should compare same-view detection documents across candidates (front/±45/profiles) using `iris_center`, `canthus`, `nose_tip`, `mouth_corner` and `chin` only, and should down-weight points with `confidence == 0.6` (approximate) and reject any document where `calibrated != false` silently.
- Gate recommendation: a candidate passes the landmark gate only if (a) all geometry-view documents validate, (b) front/±45/profile detect on the *same* sign convention, and (c) landmark reprojection error across views (after calibration) is within the calibrator's threshold — **this has not been computed; UNVERIFIED until the calibrator lands**.
