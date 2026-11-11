# C001-GEO-03 — Camera Calibration & Projection Spec (2026-11-11)

**Owner:** camera-calibrator (identity team) · **Scope:** `geo/calibration_spec.py`,
`geo/tests_calibration/`, this document.
**Status:** implemented + unit-tested (synthetic and real-file hash checks). No
render consumption, no reconstruction consumption yet — see UNVERIFIED.
**Verdict:** calibration format and sharing contract are ready for landmark-engineer
and Lane B (visual hull). This does **not** constitute, and must not be cited as,
camera recovery from the reference images — none is possible (see below).

---

## 1. What this module is, and is not

The 15 reference images in `C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1\`
are independently AI-generated photographs, **not** camera-calibrated scans. There is
no checkerboard, no EXIF (measured: all 15 PNGs carry **zero** info/text chunks —
`info_keys=[]` for every file, 2026-11-11), no known sensor, and no known camera
position. Consequently:

> **No true camera intrinsics (fx, fy, cx, cy, distortion) or extrinsics
> (translation/rotation) can be recovered from these images by any method. Any
> pipeline that emits per-view numeric intrinsics here is emitting a prior, not a
> measurement.** This module formats and carries those priors honestly: every
> geometric quantity is labelled ASSUMED / KNOWN_ASSUMED / MEASURED /
> USER_OVERRIDDEN, and the two genuinely measurable facts (file SHA-256, pixel
> dimensions) are hash-pinned and validated.

What this module **does** provide:

1. A single pinhole projection convention (no distortion term) shared by all lanes.
2. The known-from-capture-spec azimuths/pitches, labelled KNOWN_ASSUMED.
3. A 63 mm interocular scale prior, labelled ASSUMED, overridable by the user.
4. A radius prior for the near-orthographic long-lens studio assumption, overridable.
5. Validation, (de)serialization with `schema_version` + provenance (per-view image
   SHA-256, estimator, date), and strict rejection of malformed input.
6. Hash verification against the real files (8 main views pinned).

## 2. Files created (this worktree only)

| File | SHA-256 |
| --- | --- |
| `geo/calibration_spec.py` | `8d8463d8caade0374cbef0b58945c137e65fb3b7de6ff90a301e7d4c1ff37ba4` |
| `geo/tests_calibration/test_calibration_spec.py` | `788a9af2976da25fbead7e67853f1d82f1bf2dac401e2cb6ba8d49f6d6d8c325` |
| `docs/C001_GEO03_CALIBRATION.md` | this file |

No main-checkout files were modified. Worktree lane: calibration only; no overlap
with landmark-engineer's files.

## 3. Environment and commands (with exit codes)

Machine: Windows 32 (development box), Python **3.14.7**, numpy **2.5.3**,
Pillow **12.3.0**, no CUDA. No downloads, no network installs performed.

```text
# In the worktree root, with reference images reachable at C:\PROJECT\Livynth (read-only):
$ set LIVYNTH_MAIN_REPO=C:\PROJECT\Livynth
$ python -m unittest discover -s geo/tests_calibration -v
... (33 tests, all "ok")
Ran 33 tests in 0.207s
OK                                            → exit code 0

$ python -m unittest discover -s geo/tests    # baseline, must stay green
Ran 21 tests in 1.258s
OK                                            → exit code 0

# SHA-256 measurement of the 15 reference images:
$ python -c "import hashlib,os; [print(f, hashlib.sha256(open(os.path.join(d,f),'rb').read()).hexdigest()) for f in sorted(os.listdir(d))]"
... (all 15 digests printed, listed in §5)    → exit code 0

# PNG metadata-chunk probe (EXIF/seed absence check):
$ python -c "from PIL import Image; import os; [print(f, list(Image.open(os.path.join(d,f)).info)) for f in sorted(os.listdir(d))]"
01_subject_front.png info_keys= []  … (empty for all 15)  → exit code 0
```

Real-file verification tests **ran against the real images** (not skipped): the run
above had `LIVYNTH_MAIN_REPO=C:\PROJECT\Livynth` set, and
`test_verify_real_files_sha256` + `test_verify_real_files_dimensions` passed.
On a machine without the images those two tests *skip* with a printed reason
(everything else is synthetic and self-contained).

Notes on prior failures (kept for honesty): the first test run failed 3/33
(`test_camera_positions_on_assumed_circle` — hand-written 1060.66 vs true
`1500/√2 = 1060.6602`, tolerance bug, fixed; `test_project_behind_camera_raises` —
test premise inverted, point was in front of the front camera, fixed to z=+10000;
`test_embedded_hashes…` not affected). After fixes: **33/33 OK**.
`geo/calibration_spec.py` also shipped with a label-derivation nit
(`"_front"` → `"front"`), fixed and re-tested.

## 4. The projection model

### 4.1 World / head-centred frame (right-handed)

| Axis | Meaning |
| --- | --- |
| `+y` | toward the crown (up) |
| `+z` | subject's facing direction (toward viewer in front view) |
| `+x` | viewer's right in the front view == subject's **anatomical left** |

Origin = head centre (the `look_at_mm` point, default `(0,0,0)`). Units are mm and
degrees throughout. Image coordinates: origin top-left, +x right, +y **down**.

### 4.2 Camera orbit

`camera_position(radius_mm, azimuth_deg, pitch_deg, look_at_mm)`:

```
az = radians(azimuth_deg);  p = radians(pitch_deg);  h = r·cos(p)
pos = look_at + ( h·sin(az),  −r·sin(p),  h·cos(az) )
```

| View | azimuth | pitch | Camera position (r=1500) |
| --- | --- | --- | --- |
| 01 front | 0 | 0 | (0, 0, +1500) |
| 02 subject left 45° | +45 | 0 | (+1060.66, 0, +1060.66) |
| 03 subject right 45° | −45 | 0 | (−1060.66, 0, +1060.66) |
| 04 left profile | +90 | 0 | (+1500, 0, 0) |
| 05 right profile | −90 | 0 | (−1500, 0, 0) |
| 06 back head | 180 | 0 | (0, 0, −1500) |
| 07 top head | 0 (irrelevant) | −90 | (0, +1500, 0) |
| 08 front close-up | 0 | 0 | same axis as 01, tighter crop |

Positive azimuth rotates the camera toward the subject's **anatomical left**.

Camera basis: `forward = normalize(look_at − pos)`; `right = normalize(cross(forward, up_ref))`
with `up_ref = (0,1,0)` (or `(0,0,−1)` when looking straight down: image-up = occiput,
face toward the bottom of the frame — a documented convention, not a measurement);
`image_up = cross(right, forward)`. Verified orthonormal to 1e-12 in tests for all views.

### 4.3 Projection / unprojection (pinhole, no distortion)

```
z = (P − pos)·forward      # depth along optical axis; depth ≤ 0 ⇒ CalibrationError
x = (P − pos)·right ;  y = (P − pos)·image_up
px = fx·x/z + cx ;      py = cy − fy·y/z
py ↔ unproject:  P = pos + depth·( ((px−cx)/fx)·right + ((cy−py)/fy)·up + forward )
```

Verified: `project(unproject(p)) == p` to <1e-9 px, and full 3-D round-trips to
<1e-13 mm in synthetic tests across all 8 default views. `pixel_ray()` returns the
unit world-space ray for Lane B's ray caster. Points behind the camera raise
`CalibrationError` — consumers must cull, never receive garbage pixels.

### 4.4 Assumption of the default intrinsics

`fx = fy = focal_equivalent_mm · pixels / sensor_mm` with a 90 mm-equivalent lens on
an assumed 24×32 mm portrait crop and square pixels ⇒ **fx = fy = 4072.5 px**
(1086/1448 px images), `cx = width/2`, `cy = height/2`. The capture spec only says
"about 85–105 mm equivalent, eye height, near-orthographic"; 90 mm is the midpoint of
that range. **These are ASSUMED values.** Every value is independently overridable;
else defaults are recorded per view in the JSON.

## 5. ASSUMED vs MEASURED — explicit inventory

### 5.1 MEASURED (2026-11-11, this machine, commands in §3)

SHA-256 and pixel dimensions of the reference images:

| File | Size (px) | SHA-256 |
| --- | --- | --- |
| `01_subject_front.png` | 1086×1448 | `9d84f485883ce613d12d02d9f8f85e338ebe950d7248d522bf3117901eaed2dd` |
| `02_subject_left_45.png` | 1086×1448 | `86243d7eeb906fa955c95fe10341451256b116857b661549b8c3a11ed78030a9` |
| `03_subject_right_45.png` | 1086×1448 | `0f0c748a582763d4d9abf66130ea6a1759fb9e5c266f07580a03dd0b98e37a3a` |
| `04_left_profile.png` | 1086×1448 | `702eb69b4e3ddd9470a64c86e6c28e5ff9795c441b41d28e262001978597d1cd` |
| `05_right_profile.png` | 1086×1448 | `65101246912c969c55596bb97a5a3622001d10fc8497539b7d86844f0d863eba` |
| `06_back_head.png` | 1086×1448 | `8339543d8b383dfd17fbdb750d4df9ad2fa7526d5738899e598ecb7ef9bfd684` |
| `07_top_head.png` | 1087×1447 | `219cba0eb70144f0c7d8e0cc9cba33e3b98c568d97f7bc0dd2553eeb755f0b4a` |
| `08_front_closeup.png` | 1087×1446 | `af8e3a85043f7eb998a653da72885f73d255d8f9d2b04138d965bf2dc6b832cd` |
| `09_left_ear.png` | 1199×1312 | `53a38557e3241764a755bb906e6efdcaee59db8933eacc43485f09def096c081` |
| `10_right_ear.png` | 1087×1447 | `69df02c1c52051c91c87329227da37a4e3b25057fa596038268bc99eab8f3b3b` |
| `11_eyes_closeup.png` | 2172×724 | `1e706afb60d8bac39fa3bcfe16fc32db2441bf6c215f6d8cd705bb98285b28f6` |
| `12_iris_macro.png` | 1536×1024 | `4bfdb292d4f7a1e44489bba9590fea57e53e82ab7e858f5461715aaf05177533` |
| `13_skin_macro.png` | 1536×1024 | `c5d85ca41947dc83c61f834c40c7238c9f7b492fe4beb18ffa6b358e2e3d8904` |
| `14_lips_closeup.png` | 1774×887 | `284ee47e446d857e39ba1e881bb1fcad0b2d7594f0ddfee3b1e5c9629f9a07df` |
| `15_hair_closeup.png` | 1536×1024 | `c29eeef2d3905c8c64d5bdb3d6e3184a0c998bcd3a5c47d06626c4882d9c71bf` |

All 15 images are RGB with **zero** PNG metadata chunks (measured; no EXIF, no
generator/seed/focal hints). Orbit views 01–08 have non-uniform dimensions
(07 is 1087×1447, 08 is 1087×1446) — recorded, not normalised. The eight main
digests are embedded as `MAIN_VIEW_SHA256` in `geo/calibration_spec.py` and pinned
by `test_embedded_hashes_match_literal_regression_guard`.

### 5.2 ASSUMED (user-overridable; carried in JSON with labels)

| Parameter | Default | Status | Basis |
| --- | --- | --- | --- |
| `fx`, `fy` | 4072.5 px | ASSUMED | 90 mm-eq., 24×32 mm assumed portrait crop, square px |
| `cx`, `cy` | image centre | ASSUMED | no distortion/principal-point estimate possible |
| Lens equivalent | 85–105 mm (90 default) | KNOWN_ASSUMED (capture spec) → focal mapping ASSUMED | spec text only |
| `azimuth_deg` | view-table | **KNOWN_ASSUMED** | capture prompts; never camera-verified |
| `pitch_deg` | 0 (top: −90) | **KNOWN_ASSUMED** | capture prompts |
| `radius_mm` | 1500 mm | ASSUMED | studio long-lens distance prior (user may override) |
| `interocular_mm` | 63.0 mm | **ASSUMED** | population-mean adult iris-to-iris distance (anthropometric convention; not this subject) |
| top-view image-up | world −z (face at bottom) | ASSUMED convention | degenerate-axis choice |
| close-up radius (08) | same 1500 mm; tighter crop | ASSUMED | framing note, not a distance measurement |
| Distortion (k1..k3) | **omitted** | not modelled | pinhole only; detect-and-review if LANE B shows residual |
| Scale from pixels | not computed | — | **no pupil/iris detector implemented**; `mm_per_pixel_from_interocular(px, mm)` helper only; pixel IOD must come from landmark-engineer |

### 5.3 KNOWN / deliberately excluded

- Close-ups 09–15 (`DETAIL_VIEW_FILES`) are detail references, not orbit cameras,
  and are **excluded** from the reconstruction camera circle.
- The capture spec never defined a back or top shot (it stopped at 06_front_closeup);
  files 06–08 exist in the folder, so their azimuth/pitch labels are inferred from
  filenames + strategy doc and marked KNOWN_ASSUMED, not from the spec tables.
- Inter-image identity/lighting/geometry consistency (possible perspective
  contradictions across AI views) is **not** evaluated here — that is
  multiview-auditor's gate (Phase 0) and gates any fusion attempt.

## 6. The calibration JSON (schema_version 1.0.0)

Top-level keys (strict; unknown keys rejected): `schema_version` (must equal
`"1.0.0"`), `tool`, `tool_version`, `created` (ISO date), `estimator`,
`method`, `notes`, `views[]`. Per view (strict; unknown keys rejected):
`view_id, label, image_file, image_sha256 (64-hex, required), width, height,
fx, fy, cx, cy, azimuth_deg, pitch_deg (default 0), radius_mm (default 1500),
interocular_mm (default 63), focal_equivalent_mm (default 90), look_at_mm (3-vec),
status{}, notes`.

Validation (`ViewCalibration.validate` / `CalibrationSet.validate`): finite numbers,
`fx,fy>0`, `cx∈[0,width]`, `cy∈[0,height]`, `azimuth ∈ {0,±45,±90,180}`,
`pitch ∈ {0,−90}`, positive radius, 3-vector finite look-at, duplicate view-id
rejection, `schema_version` pin. `CalibrationSet.from_dict` raises
`CalibrationError` on any violation; `validate()` collects all issues for reports.
`verify_image_hashes(dir)` returns `(view_id, ok, expected, actual)` per view
without raising.

Real example (generated, not hand-typed; view 01 only):

```json
{
  "schema_version": "1.0.0",
  "tool": "livynth-geo-03/calibration_spec",
  "tool_version": "1.0.0",
  "created": "2026-11-11",
  "estimator": "assumed-capture-spec",
  "method": "capture-spec-azimuth+long-lens-assumption",
  "notes": "C001-GEO-03 baseline calibration. Intrinsics/extrinsics are ASSUMED (85-105 mm long-lens prior; capture prompts for azimuths); no checkerboard calibration exists. image_sha256 and dimensions are MEASURED. Detail close-ups (09-15) are excluded from the orbit set.",
  "views": [
    {
      "view_id": "01",
      "label": "front",
      "image_file": "01_subject_front.png",
      "image_sha256": "9d84f485883ce613d12d02d9f8f85e338ebe950d7248d522bf3117901eaed2dd",
      "width": 1086,
      "height": 1448,
      "fx": 4072.5, "fy": 4072.5,
      "cx": 543.0, "cy": 724.0,
      "azimuth_deg": 0.0, "pitch_deg": 0.0,
      "radius_mm": 1500.0,
      "interocular_mm": 63.0,
      "focal_equivalent_mm": 90.0,
      "look_at_mm": [0.0, 0.0, 0.0],
      "status": {
        "intrinsics": "ASSUMED", "azimuth_pitch": "KNOWN_ASSUMED",
        "scale": "ASSUMED", "radius": "ASSUMED",
        "principal_point": "ASSUMED",
        "image_sha256": "MEASURED", "dimensions": "MEASURED"
      },
      "notes": "orbit view; azimuth/pitch from capture prompt (KNOWN_ASSUMED)."
    }
  ]
}
```

Build a full set with:

```python
import geo.calibration_spec as cs
s = cs.build_default_calibration_set()          # 8 orbit views, hashes pinned
issues = s.validate()                            # [] when sane
path = s.save_json("output/c001_geo03/calibration_assumed.json")
back = cs.load_json(path)                        # strict round-trip
report = back.verify_image_hashes(r"C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1")
```

## 7. Integration contract — landmark-engineer

You may rely on (and must not re-derive silently):

1. **Loading.** `cs.load_json(path)` → `CalibrationSet`; enforce
   `set.schema_version == "1.0.0"`; on `CalibrationError`, stop — do not repair by
   hand-editing. Use `set.view("02")` for id lookup; unknown id raises.
2. **Frame.** All 3-D quantities are head-centred mm (`§4.1`). If your landmark
   exports use a different frame (e.g. normalised face space), you must convert at
   your boundary and record the transform; the contract does not do it for you.
3. **Pixel convention.** Origin top-left, +y down. If MediaPipe/other tools emit
   normalised or y-up coordinates, convert before mixing; the test suite pins the
   y-down behaviour.
4. **Projection.** `view.project((N,3) points) -> (N,2) px`; raises on depth ≤ 0.
   `view.unproject(px, py, depth_mm) -> 3-D point`; `px,py` round-trip exactly.
   `view.pixel_ray(px, py) -> (origin, unit_dir)`.
5. **Per-measurement provenance.** Each stored 2-D landmark must carry
   `view_id`, `schema_version`, and the `image_sha256` of the image it was measured
   on. Reject mixed-version or mixed-hash landmark files.
6. **Scale / mm conversion.** This module ships **no** pupil/iris detector. Obtain
   per-view pupil/iris-centre pixel coordinates yourself (MediaPipe FaceMesh irises
   are the obvious candidate; offline CPU), then
   `mm_per_px = cs.mm_per_pixel_from_interocular(measured_iod_px, interocular_mm)`
   with `interocular_mm` defaulting to the 63 mm ASSUMED prior (or a subject value
   if the user supplies one — record provenance either way). Population spread is
   large; do not treat 63 mm as identity truth.
7. **Uncertainty.** Attach a per-landmark pixel uncertainty (e.g. reprojection spread
   across the views that see the point); the calibration itself has no error model.
8. **Status labels.** Your landmark report must distinguish: coordinates from files
   whose `image_sha256` matches this set (MEASURED input), geometry from this
   assumed calibration (ASSUMED), and any fitted refinement (call it e.g.
   "FITTED, not verified"). Never emit "calibrated camera" language.
9. **You must not** edit `geo/calibration_spec.py` or this doc; request changes via
   the coordinator. If you need extra views in the orbit set, that is a calibration
   task, not a landmark task.

## 8. Integration contract — visual-hull lane (Lane B)

1. **Camera circle.** Take the orbit views from `cs.build_default_calibration_set()`
   (or a serialised `calibration_assumed.json` you load with `cs.load_json`).
   Positions: same `radius_mm` (default 1500 mm), same `look_at_mm = (0,0,0)`
   (head centre), angles from the per-view `azimuth_deg`/`pitch_deg`. You get
   exactly the circle in §4.2 — do not invent your own angles; the 8 orbit views
   and only them. Views 09–15 are excluded.
2. **World frame** is head-centred (`§4.1`); place your reconstructed volume in that
   frame with head centre at the origin, y toward the crown.
3. **Consumption helpers:** `view.camera_position()`, `view.camera_basis()`
   (right, up, forward), `view.project(pts)` for vertex→pixel, `view.pixel_ray`
   for silhouette ray casts, `view.unproject` for carve-back-projection. Cull
   depth ≤ 0 explicitly via the raised `CalibrationError`.
4. **Top view (07).** `pitch=-90`; image-up = occiput (`−z`); the face appears at
   the **bottom** of the frame. Segment accordingly; do not rotate the mask.
5. **Input pinning.** Before fusing, call
   `set.verify_image_hashes(<capture_dir>)` and require `ok=True` for all 8 orbit
   views; refuse to run on anything else. This guards against silent image swaps.
6. **Assumption bookkeeping.** Radius, intrinsics, and the 63 mm scale are ASSUMED.
   The hull is therefore correct only up to an overall scale (and weakly up to the
   principal-point prior); relative shape is the deliverable. Report any absolute mm
   claim as "scaled by interocular prior (ASSUMED)".
7. **Reprojection gate.** After meshing, project hull vertices through every view,
   rasterise, and compute IoU against the segmented silhouettes; that comparison
   **is** the honest use of this calibration. A high silhouette IoU under ASSUMED
   intrinsics does not license identity claims — the Phase 3 gate still applies.
8. **Contradiction tolerance.** If view silhouettes disagree beyond what an
   uncertainty budget allows, Lane B owns the fusion policy (carve-and-flag, not
   carve-and-hide). This module is silent on that decision by design.
9. **You must not** edit `geo/calibration_spec.py`; if you need a bigger radius,
   different lens prior, or per-view overrides, override constructor arguments or
   JSON fields and record them in your output manifest — do not fork the format.

## 9. Limits, failure modes, and honest unknowns

- **No true intrinsics/extrinsics exist here.** The images' perspective (if any) can
  differ from pinhole-square-pixel in unknown ways: AI generators apply arbitrary
  effective focal lengths and may even mix them across views. Unverifiable; treat
  every reprojected measurement as ±(unknown) px error with no claimed accuracy.
- **No checkerboard ⇒ unidentifiable focal length.** The 90 mm prior is a prior.
  85 mm ⇒ fx=3846; 105 mm ⇒ fx=4751 (a ±10.5 % band) — plan for either.
- **Radius prior unidentifiable.** For near-orthographic framing, a wrong radius
  (e.g. 1200 vs 2000 mm) barely changes projections of a head-sized object, but it
  changes absolute depth scale linearly; never report mm-accurate volume from the
  default radius.
- **Interocular prior error.** Population spread ≈ ±10 % around 63 mm; individual
  variation will dominate any "measurement" you could extract cheaply.
- **Azimuths are prompts, not measurements.** If the 04 "left profile" image drifts
  toward 80° or mirrors anatomy (capture spec warns generators mirror), this
  calibration will faithfully project a wrong camera. Silhouette IoU per view will
  expose it; fix the view labelling, not the hash.
- **Hash pinning guards bytes, not geometry or identity.** A pinned file can still
  depict inconsistent anatomy; that is why Phase 0 (asset validation +
  multiview audit) precedes any fusion.
- **Detail views excluded** on purpose; using them as orbit cameras would corrupt the
  hull.
- **08 front close-up** shares the 01 axis; tighter crop ⇒ do not use it to tighten
  intrinsics by brute force; it adds nothing geometric over 01 that this module
  could exploit.
- **Asymmetric views / specular inconsistency / hair vs skin silhouette merges** are
  out of scope for calibration; escalate to multiview-auditor.
- **What success looks like later:** all 8 orbit views' silhouettes IoU > agreed
  threshold under these priors **and** independent visual approval. Until then every
  consumer must label outputs as planned/implemented/unit-tested/rendered, never
  "calibrated" or "reconstructed".

## 10. UNVERIFIED / not executed here

- No checkerboard or ChArUco calibration exists or was possible (no target in any
  image; no external capture session has been authorised).
- No pupil/iris detection implemented or run; per-view pixel IOD measurements do not
  exist yet. `mm_per_pixel_from_interocular` is provided as the integration point.
- No Blender render, reconstruction, or fusion has consumed this spec; the camera
  math is verified only on synthetic round-trips.
- No reprojection residual against the real images has been computed (no masks, no
  mesh yet) — UNVERIFIED.
- Lens identity (85–105 mm) comes from the capture spec text only; nothing in the
  files confirms it — KNOWN_ASSUMED, not MEASURED.
- Back view (06) and top view (07) geometry labels are filename/strategy-derived,
  not capture-spec-table-derived — KNOWN_ASSUMED with that caveat.
- The named modules' lane boundaries (landmark-engineer, Lane B) are untested
  integrations; contracts here are proposals until those lanes load a real JSON.

## 11. Test evidence (commands + results)

```text
$ python -m unittest discover -s geo/tests_calibration -v     (worktree root,
                                                              LIVYNTH_MAIN_REPO=C:\PROJECT\Livynth)
… 33 tests listed, every line "ok" …
Ran 33 tests in 0.207s
OK                                                        exit 0
Real-file checks that ran (not skipped): test_verify_real_files_sha256,
test_verify_real_files_dimensions (dimensions + RGB mode of all 8 main views).

$ python -m unittest discover -s geo/tests                (baseline)
Ran 21 tests in 1.258s
OK                                                        exit 0
```

Synthetic coverage: projection round-trips (<1e-13 mm), unproject→project identity
(<1e-9 px), behind-camera rejection, circle positions vs analytic 1500·(1/√2),
orthonormal bases for all 8 views, default-set build/shape/labels, strict schema
accept/reject (wrong version, missing/unknown keys, fx≤0, fy<0, cx/cy out of bounds,
azimuth/pitch outside allowed sets, missing/malformed/short hash, duplicate view ids,
bad JSON), JSON round-trip + save/load, synthetic hash verify/tamper/missing, 63 mm
helper behaviour, intrinsics-from-focal (90 mm → 4072.5 px).

## 12. Recommended next steps

1. **landmark-engineer**: implement MediaPipe iris detection on orbit views 01–05
   (8 not needed for IOD; front + profiles preferred), emit per-view pixel IOD +
   uncertainty, and pass measurements to `mm_per_pixel_from_interocular` with the
   63 mm prior recorded as ASSUMED (user may override per §5.2).
2. **Lane B**: build `calibration_assumed.json` via `cs.save_json`, verify hashes,
   consume the §4.2 circle, report silhouette IoU per view.
3. **multiview-auditor**: remain the gate on cross-view consistency before any
   fusion; flag any view whose azimuth label is inconsistent with its silhouette.
4. **user**: if a checkerboard session (or a measured interocular distance for this
   specific synthetic subject, e.g. from a licensed asset) is ever available, drop
   it into `build_default_calibration_set(...)` overrides; everything downstream
   (JSON pinning, verification) then works unchanged.

*This document records an experiment, not a success claim. The reference images are
AI-generated; no geometric trust should be placed in them beyond what the evidence
above supports.*
