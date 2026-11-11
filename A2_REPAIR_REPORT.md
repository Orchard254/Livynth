# C001-GEO-04 — Candidate A bounded repair (ADR-C001-004, decision 2)

**Branch:** `experiment/c001-geo04-repair` (base `b0235c1`) — local narrow commit only.
**Candidate:** `output/a2_repair/character001_visual_hull.glb` — **A2**. NOT a validated likeness,
NOT animation-ready, NOT merged anywhere. **Phase-3 remains FAIL.**

## Scope

Exactly the three authorized repairs in ADR-C001-004 decision 2 — remove the
duplicate/translucent ghost shell, re-carve the posterior cranium so the 90° views
match the clean mass that `back.png` already produces, and assign view-aware albedo
using the measured yaw convention. No FLAME, no external services, no uploads,
no gate-bundle/eval.json access. The two reference photographs and the existing
calibration machinery are the only measurement inputs.

## Prior state (what this repair started from)

The coordinator had already implemented the R1/R3 mechanism and the R2 calibration
in `geo/visual_hull.py` before this session resumed:

- `VIEWS["back"]` gained explicit `scale=3866.0, cx=555.0, cy=465.5` (the back photo
  is framed ~9% tighter than the front; inheriting the front's scale/cy shaved the
  posterior cranium and produced the smeared profile posterior).
- `view_params()` honours explicit `scale`/`cx`/`cy` overrides; `YAW_SIGNS` added;
  `cam_dir()` gained a `view_name` and applies the measured sign per view; the texture
  path was rewritten from front/back-atlas sampling to `vertex_colours()` (per-face
  assignment over ALL seven views with sign-corrected `cam_dir`, bilinear sampling,
  +0.35 front/back pole bias) and `export_glb()` welded by POSITION ALONE and emits
  COLOR_0 vertex colours, asserting one connected component and position-weld
  watertightness.

This session verified those edits compile and pass, found and fixed one defect
introduced by the new path (COLOR_0 washed-out renders — sRGB bytes were stored
where glTF COLOR_0 is linear), reinforced the export's report with a
reload-and-verify artifact QA, added regression tests, rebuilt A2, rendered the
comparison package, and wrote this record.

## REPAIR 1 — eliminate the duplicate / translucent ghost shell

**Hypothesis.** The A1 GLB contains one closed carve — not two nested heads —
split by the `(position, uv)` weld into two large index-connected shells plus
tiny shards; a reviewer sees a pale "ghost head" offset from the real one where the
two shells meet (front-photo albedo on one side, back-photo albedo on the other,
with the back sample misregistered).

**What was changed.**
- `texture_face_soup`/`build_atlas` replaced by `vertex_colours()` +
  `export_glb()`, which welded by position ONLY (one indexed shell — the old
  `(position, uv)` weld guaranteed a split at every texture seam).
- Albedo moved from an embedded 4096×2048 UV-atlas `PBRMaterial` to COLOR_0
  vertex colours (bilinear-sampled per face from the chosen view). No image is
  embedded; index connectivity is universal.
- A colour-space defect in the new COLOR_0 path was found and fixed: raw sRGB
  bytes were stored in COLOR_0 (importer treats it as linear) → washed-out pale
  renders. `srgb_to_linear()` now converts to linear 0..1 before export.

**Before (A1, measured on `output/a1_baseline/character001_visual_hull.glb`,**
regenerated from the default v8 config; it reproduces the coordinator's stated
baseline exactly):

| metric | A1 |
|---|---|
| faces / verts | 31,152 / 16,263 |
| connected components (as loaded) | **50** |
| largest component volume share | 58.3% |
| watertight (as loaded) | **False** |
| position-weld watertight | True |
| euler (as loaded) | −56 |
| degenerate faces | 0 |
| GLB size | 11.6 MB |
| carve volume | 0.00585 m³ |

**After (A2, measured on `output/a2_repair/character001_visual_hull.glb`):**

| metric | A2 |
|---|---|
| faces / verts | **30,920 / 15,446** |
| connected components (as loaded) | **1** |
| largest component volume share | **100%** |
| watertight (as loaded) | **True** |
| position-weld watertight | True |
| euler (as loaded / position-weld) | −14 / −14 |
| degenerate faces | 0 |
| GLB size | **804 KB** (~14.5× smaller) |
| carve volume | 0.00582 m³ |

**Verdict for REPAIR 1: PASS** at the artifact level (single welded shell, one
component, closed, no second layer). Note: the two reviewers' "offset ghost"
could not be re-reviewed by the renderer that exposed it (the v9/v8 review was
based on the old atlas renders; these were rebuilt for both candidates — see
`output/comparison_a1_vs_a2/`). The reviewers' reading is preserved as evidence;
it is now mechanically inconsistent with the exported geometry.

## REPAIR 2 — re-carve the posterior cranium to match `back.png`

**Hypothesis.** The back view silently inherited the FRONT view's scale
(3546.9 px/m) and a centre derived from the crown row only; the back photo is
framed ~9% tighter. So the back cone shaved the posterior cranium and the back
albedo sample landed on the back photo's grey studio backdrop.

**What was changed.** `VIEWS["back"]` gained explicit `scale=3866.0, cx=555.0,
cy=465.5`, resolved by a joint carve-metric sweep against the BACK PHOTO's own
segmentation mask (`output/scratch/repair2_sweep.json`, key `sweep`, best
candidate (3866.0, 555.0, 465.5)). It is an in-sample fit — the back mask was
used as its own target — and no independent validation exists; flagged as an
assumption everywhere it appears. No other view's calibration changed.
A wisp-pruning variant (morphological opening on the profile masks) was measured
and rejected: the two 90° masks are 99.9%/100.0% solid under a 5×5 opening and
the carve is insensitive (≤0.1% voxel change) — the "hair wisps tear the carve"
sub-hypothesis is REFUTED by measurement.

**Before / after (construction IoU vs reference masks, unoptimized polygon rasterisation):**

| view | A1 | A2 | Δ |
|---|---|---|---|
| front | 0.9092 | 0.8990 | −0.010 |
| left45 | 0.9449 | 0.9416 | −0.003 |
| right45 | 0.9578 | 0.9561 | −0.002 |
| **left90** | **0.9198** | **0.9156** | −0.004 |
| **right90** | **0.9268** | **0.9227** | −0.004 |
| **back** | **0.7820** | **0.9127** | **+0.131** |
| top | 0.8324 | 0.8324 | ±0.000 |

Calibrated render IoU (same harness both candidates): back 0.7784 → **0.8792**;
left90 0.9191 → 0.9154; right90 0.9233 → 0.9207.

Also measured (failure-mode cross-check): the exported-STL/GLB posterior
silhouettes at φ = −90 and φ = +90 are essentially unchanged (same 90° view
calibration); the gain comes from the back cone no longer carving the bottom of
the hair mass and the albedo now sampling the back photo's dark curly mass
(not the studio grey backdrop). The reviewers' "horizontally combed smear / grey
untextured bands / sawtooth seam" is not present in the rebuilt A2 renders at the
same framing (`output/comparison_a1_vs_a2/a2_left90.png` vs `a1_left90.png`).

**A trade, stated honestly:** A2's front silhouette IoU dropped 0.010 (the back
cone is wider, the head slightly narrower overall). An alternative sweep point
(s=3866, cx=543, cy=477.5) yields back 0.906 / front 0.902 — front ≥ 0.90 with
nearly all of the back gain — but the coordinator-selected point (maximising the
back metric) was kept. If the coordinator prefers front ≥ 0.90, the back view
can be re-pinned to that alternative in one edit.

**Verdict for REPAIR 2: PASS at the metric level** (back IoU ≥ 0.88 achieved;
90° profiles within 0.004 of A1). This treats the carve geometry only; even with
the back cone fixed, the profile renders still show the known residual defect of
a smooth-hulled face (see "Residual failure modes").

## REPAIR 3 — view-aware albedo with the MEASURED yaw sign

**Hypothesis.** `TEXTURE_VIEWS = ("front", "back")` sampled the front photo onto
the profile surfaces and the back photo onto whatever faces qualified, so the
profiles showed a stretched front face and a grey rear. Profile photos were
assigned the wrong yaw sign (or none), and the back view's handedness had to be
resolved empirically.

**What was changed.**
- `build_atlas`/`texture_face_soup` replaced by `vertex_colours()`: every face is
  assigned to the best-scoring of ALL SEVEN views (front, back, left45, right45,
  left90, right90, top) by sign-corrected `cam_dir`, with a +0.35 score bias for
  the front/back views so the identity anchors do not split into a
  double-exposure-torn face.
- `cam_dir()` applies `YAW_SIGNS` (from `tools/pick_render_signs.py`, run on the
  unmodified candidate: front +, left45 +, right45 +, left90 +, right90 +,
  back − (degenerate: both signs project identically at φ = ±180°, so back's
  measured sign does not change sampling)).
- The albedo is now COLOR_0 vertex colours, bilinear-sampled per face — no UV
  atlas exists, so no seam can split the indexed shell.
- Export `srgb_to_linear()`: photo bytes are converted to LINEAR before being
  written as COLOR_0 (glTF COLOR_0 is linear; a raw byte upload washes out —
  caught in this session's first render and corrected).

**Per-view texture assignment** (faces, this A2 build) and calibrated render IoU:

| view | A1 (photo used) | A1 render IoU | A2 (photo used) | A2 render IoU |
|---|---|---|---|---|
| front | front 100% | 0.9109 | front (face) | 0.8983 |
| left45 | front/back | 0.9190 | left45 dominant | 0.9422 |
| right45 | front/back | 0.9569 | right45 dominant | 0.9576 |
| left90 | **front** | 0.9191 | **left90** (side) | 0.9154 |
| right90 | **front** | 0.9233 | **right90** (side) | 0.9207 |
| back | back | 0.7784 | back | 0.8792 |

(Assignment counts per view are identical in structure to A1's: A1 assigned
all faces to front or back only — front face got the front photo; profile
surfaces got the stretched front photo. A2: the face and the profile surfaces
are view-local.)

- **Front face is double-exposure-safe**: the frontal face |n·z| ≥ ~55° is always
  assigned the front photo (pole bias); the 45° photos own the temples and the
  90° the profile sides. The nose reads as a single projection, not two offsets.
- **Profiles carry the profile photos**: sampling on the profile surfaces now
  comes from `04_left_profile.png` / `05_right_profile.png` (see
  `a2_left90.png` vs `a1_left90.png`).
- **No hard seam tearing through the face**: the carve is face-local by sign
  correction and the face is a single-view region.
- **No grey "untextured" rear**: every surface point samples a photo, not the
  studio backdrop (the previous 8.84% of front-assigned corners landing on the
  backdrop are gone; the back view's own mask is used).

**Verdict for REPAIR 3: PASS at the mechanism level** (view-aware albedo, sign
applied, front anchor preserved, profiles sample profile photos). The profile
renders in the comparison package are still visibly "mask-like" — the model has
no nose/eye/lip geometry; the profile photos provide texture only.

## Verification (exact commands, exit codes)

All commands run in `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-repair`
(worktree based on `b0235c1`). | exit code |
- `python -m py_compile geo/visual_hull.py` | 0
- `python -m unittest discover -s geo/tests_hull -v` → **Ran 13 tests in ~1.9 s;
  OK (skipped=2 before A2 existed, 0 skipped after)** | 0
- `python -m geo.visual_hull --images <identity_capture_v1> --out output/a2_repair
  --views front,left45,right45,left90,right90,back,top` | 0
- artifact QA reload (`output/scratch/a2_qa.py`) | 0
- sign pick (`tools/pick_render_signs.py`) on the A2 probes | 0
- Blender calibrated renders (both candidates, all 6 views) | 0 each
- `python output/scratch/collect_numbers.py` | 0

The two skipUnless-gated tests (A2 candidate GLB, render manifest) now run and pass;
all original segment/carv/projection/export tests still pass.

## A1 regeneration (honesty of the comparison)

The coordinator had not copied an official A1 artifact into this worktree; A1 was
regenerated from the **default, unmodified v8 configuration**
(`--views front,left45,right45,left90,right90,back,top`, cell 0.0042 m, smooth ×3,
`dilate45` unset ⇒ dilate 2 everywhere) into `output/a1_baseline/`. It reproduces
the coordinator's stated A1 baseline exactly (faces 31,152; euler −14; 16,263
verts; front 0.909 / left45 0.945 / right45 0.958 / left90 0.920 / right90 0.927 /
back 0.782 / top 0.832). `output/a1_renders_tmp/` holds its renders and
`signs.json` (front/left45/right45/left90/right90 `+`, back `-`, degenerate).

## Known residual failure modes (preserved, not papered over)

- Voxel terracing remains everywhere; hair detail is smeared photo content.
- The model has no eyes/nose/lips — the face is a smooth mask with projected photo on it.
- The back-view calibration is in-sample (fitted against the candidate's own back
  mask; there is no independent ground truth).
- The exported mesh inherits genus ~8 from marching-cubes wisps (euler −14) — a
  closed but not simple manifold.
- Front-vs-back pole bias (+0.35) means the forehead/temple split between front
  and 45° photos can leave a subtle tone step at extreme oblique angle (see the
  A2 front render, which is flatter than A1's but not perfectly even).
- A2 front silhouette IoU is 0.010 below A1 (the cost of the back repair).
- The Phase-3 blind gate remains FAIL; A2 must not be treated as likeness.
- `build_atlas` and `ATLAS_CELL/COLS/ROWS` are now dead code (left in place to
  minimize the diff; not wired into any path).
- `tools/render_hull_calibrated.py` gained a `--signs`/`--prefix` option for the
  comparison package (the comparison uses ONE locked `"+"` convention for both
  candidates; A1's back probe was a numerical tie).

## Artifacts & provenance

- Candidate: `output/a2_repair/character001_visual_hull.glb` (SHA-not-committed;
  output/ is gitignored by design). Reload-verified QA:
  v=15,446 f=30,920 watertight=True components=1 position-weld watertight=True
  euler=−14 degenerate=0.
- Report (generated): `output/a2_repair/visual_hull_report.json`
- A1 baseline: `output/a1_baseline/` (regenerated; `visual_hull_report.json`)
- Comparison package: `output/comparison_a1_vs_a2/` (12 renders + `README.md` +
  `signs_allplus.json` + `render_manifest.json`)
- Sign evidence: `output/a2_renders/signs.json` (A2), `output/a1_renders_tmp/signs.json` (A1)

## Phase-3 gate

FAIL. This candidate demonstrates exactly the three authorized repairs and nothing
more. It is a diagnostic geometry, not a likeness, not animation-ready, and not
committed to any branch other than the local experiment branch. The blind gate,
not this report, decides likeness.
