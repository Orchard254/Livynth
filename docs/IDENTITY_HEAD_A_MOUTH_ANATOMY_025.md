# LIVYNTH IDENTITY-025 — Head A mouth anatomy fix (experiment; owner review required)

**Date:** 2026-11-12 · **Branch:** `fix/head-a-mouth-anatomy` (stacked on
`diagnostic/identity-024-dental-arch-isolation`, tip `2105a59`, which is the
newest branch on `origin` and was verified byte-identical to a fresh clone
made at the start of this work) · **Blender:** 4.5.10 LTS (Windows) ·
**MPFB build:** 20261010 · **Status:** fix implemented and measured; visual
quality still `PENDING_INDEPENDENT_REVIEW` — no likeness or photorealism is
claimed.

## Objective

Fix Head A's mouth anatomy so the upper and lower teeth, gums, tongue and
lips look natural in **neutral, jaw-open and speech poses**, without
distortion or exposed internal geometry — preserving existing functionality
and the original assets — and deliver automated test results, before/after
renders and this report.

## Verdict up front (visual)

The mouth is now an anatomically plausible open mouth: upper arch erupts
behind the upper lip with a natural gum line, lower arch fills the lower
half of the opening, the tongue rests behind the lower arch, and the
previously grey-speckled interior is replaced by a dark oral-cavity throat.
Neutral lips still close naturally; speech poses (`viseme_aa` open vowel,
`viseme_PP` pressed bilabial) read correctly. The teeth remain the MPFB
`teeth_base` photo-projected asset (uniform, slightly blocky — inherent to
the asset, not distorted by the fix).

## Evidence of the defect (before — measured, not eyeballed)

All measurements are evaluated world-space, `demo_head_a` recipe, identity
field, 163-joint copied rig, seam-cut seamed teeth copy, MPFB accessory
fit (`2026-11-12`, head-probe logs in `output/probe_*.log`):

| Quantity (world, metres) | Neutral | jawOpen 0.85 | viseme_aa 0.90 |
|---|---|---|---|
| Lower arch (MHCLO mask == 1) | z 1.5390–1.5781 | z 1.5278–1.5669 | z 1.5322–1.5712 |
| Upper arch (MHCLO mask == 0) | z 1.5682–1.5892 | z 1.5682–1.5892 (static) | z 1.5682–1.5892 (static) |
| Tongue | z 1.5518–1.5788 | z 1.5406–1.5676 | z 1.5449–1.5719 |
| Mouth opening at x≈0 (surface gap) | sealed | z ≈ 1.540–1.565 | partly closed |
| Body mouth bulge front surface | z 1.51–1.58 (max protrusion y≈−0.170 @ z≈1.58) | — | — |

Interpretation: the lips seam sits at z≈1.51–1.58 with the opening at
z≈1.54–1.565, but the **upper arch sits entirely above the opening**
(z≥1.568), i.e. embedded in the maxilla behind the upper lip and never
visible. The lower arch filled the whole opening (the noisy "grille"), its
pink photo-textured gum slab occupying the lower half. The tongue domed
into the upper mouth. The mouth interior surface rendered as a grey
speckled shell (the body mesh's inner/back-facing quads; 749 quads face
+Y in |x|<0.055, z 1.41–1.70).

Before-renders used as evidence:
`output/identity022_jaw_stills/20261112_104220_901389/front_neutral.png`,
`front_jaw_open.png`; `output/identity023_oral_isolation/`;
`output/identity024_dental_arch_isolation/20261112_111442_628397/`.
(`jaw_upper_only.png` from IDENTITY-024 is byte-identical to a
no-teeth render — direct proof the upper arch was invisible.)

## Root causes

1. **Teeth placement.** The MPFB accessory fit (and the whole body) is
   consistent with the 1.747 m baked body, but the teeth assets sit
   ~1.5–3 cm above the lip line for this parameter set (verified in the
   unbaked source human too: teeth z≈1.54–1.59 vs lip bulge z≈1.43–1.525).
   The identity-field alignment moves teeth ≤7.8 mm and the jawOpen
   corrective translates the lower arch down 17.8 mm, but nothing ever
   re-seated the upper arch.
2. **Exposed interior.** The baked body has an inner-mouth surface
   (closed singular mesh) with no dedicated oral material; its
   back/front-facing faces rendered as grey/speckle noise through the
   opening ("exposed internal geometry").
3. **Blender 4.5 shape-key absolutism (found during this fix).**
   Once a mesh carries shape keys, `mesh.vertices[i].co = …` does **not**
   move the evaluated mesh — only the shape-key blocks drive evaluation.
   Any vertex-write approach must translate every key block (Basis +
   correctives) by the same delta.
4. **Body morph keyframes at frame 1 override bare `.value` writes**
   (found during this fix) — the jaw-open selection pose must be
   keyframed and restored, not assigned.

## The fix (all in-memory on the pipeline's disposable copy)

New opt-in flags `--oral-anatomy [--upper-seat M] [--tongue-seat M]` in
`tools/mpfb_anatomy_ab_blender.py`; new pure-math module
`tools/mouth_anatomy.py`; new runner `tools/run_mouth_anatomy.py`; new
tests `tests/test_mouth_anatomy.py`.

1. **Upper-arch seat:** rigid translation of the upper arch (MHCLO
   helper-group mask == 0, pinned 1,984 vertices / 1,818 faces) down by
   **0.022 m** in body space. No topology, skin weight, UV, mask or
   shape-key *count* changes; only a shared translation delta applied to
   every shape-key block (Basis/jawOpen/viseme_aa). Evaluated upper arch
   now z 1.5462–1.5672 in every pose (cusps behind/just below the
   upper-lip roll).
2. **Tongue seat:** rigid translation of all 226 tongue vertices down by
   **0.016 m** (same all-key-block delta). Tongue now rests behind the
   lower arch (jawOpen z 1.5246–1.5516) instead of doming into the upper
   mouth.
3. **Oral-cavity material:** the body gets two material slots —
   `livynth_oral_exterior_clay` (warm neutral, all outer faces) and
   `livynth_oral_cavity` (dark red-brown, base 0.135/0.035/0.030,
   roughness 0.92) assigned by polygon index to the polygons visible
   through the front openings.
   Selection is *principled*, not normal-guessed:
   - select candidates on the **evaluated jawOpen=0.85** body mesh (lips
     actually parted) via a **BVH first-hit ray grid** (48×48 rays,
     |x|<0.06, z in mouth band): an interior wall is a first hit through
     the opening; the rear of the head/neck is occluded and never a first
     hit; skin is a first hit too, handled next;
   - refine with the pure `plan_cavity_faces` filter: |x| ≤ 0.046
     (mouth-opening half width — receding cheek/neck skin plugs the
     opening corners), z in band (1.520–1.599 world), centre depth
     y ≥ −0.10 (chin/neck envelope is shallower); strongly side-facing
     polygons (|nx|>0.5) must face the mouth centre
     (sign(nx) == −sign(x)).
   Result: **16 polygons** (index list 386 … 7107, logged in the report) —
   exactly the back wall + upper dome base behind the teeth. The naive
   `n.y>0` selection used first was rejected because it painted exterior
   rear-jaw/neck skin brick red (visible as red strips beyond the
   three-quarter silhouette).
4. **Post-fix integrity gate:** after the fix, evaluated teeth are
   re-audited — lower arch 1,884 verts move 17.76 mm, upper arch 1,984
   verts stationary, `PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA`.
5. **Existing gates preserved:** seam cut (20 bridge faces removed,
   3,868 retained verts/3,540 faces), MHCLO upper/lower helper mapping,
   oral correctives, alignment, rigged-copy proofs — all unchanged and
   re-verified by the standard report contract.

Seats default: upper 0.022 m, tongue 0.016 m (max bound 0.045 m enforced).
No installed MPFB asset, no source human, no exported GLB, no existing
still/report path changed; the whole fix is opt-in behind `--oral-anatomy`
and never runs unless requested.

## After-render measurements (this run, `output/mouth_anatomy/20261112_144208_181158/`)

- Upper arch: z 1.5462–1.5672 (neutral, jawOpen, viseme_aa) — stationary.
- Lower arch unchanged relative to the corrected pipeline: 1,884 verts
  move 17.762 mm at jawOpen.
- Tongue: z 1.5358–1.5628 neutral; z 1.5246–1.5516 jawOpen.
- Contact distances (point-to-triangle, world):
  tongue↔teeth min 0.001–0.118 mm (median 5.7 mm);
  upper↔lower arch min 0.001–0.003 mm — the oral assets **touch but do
  not interpenetrate**.
- Cavity faces: 16 (candidates 527 → filtered), total faces 13,378,
  2 material slots, body/teeth/tongue topology unchanged.
- Motion gates: `seamed_jaw_motion_audit` and
  `mouth_anatomy_audit.seamed_jaw_motion_after_fix` both
  `PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA`.
- Existing GLBs modified: `False` (untouched); source assets untouched;
  installed MHCLO untouched.

## Automated tests (Windows, 2026-11-12)

| Suite | Result |
|---|---|
| `python -m unittest discover -s tests -p "test_mouth_anatomy.py" -v` | **30 tests OK** (seat validation, masked/global translation, cavity selection incl. side-facing rule, z-window) |
| `python -m unittest discover -s tests` | **391 tests OK** (skipped 5, pre-existing skips) |
| `python tools/local_check.py` | **PASS** (all local checks; exit 0) |
| `python tools/branch_audit.py --run-tests` | exit 0; `geo/tests` passed, `local_check` passed; `main` untouched (`0db7a7d`) |
| `python tools/run_mouth_anatomy.py` | `CAPTURED_HEAD_A_MOUTH_ANATOMY_PENDING_VISUAL_REVIEW`; report contract validated; 5 PNGs (400×600) + JSON + `identity025_head_a_mouth_anatomy.zip` |

## Renders (before → after, identical framing 400×600 mouth-closeup)

After images (this fix):
`output/mouth_anatomy/20261112_144208_181158/front_neutral.png`,
`front_jaw_open.png`, `front_viseme_aa.png`, `front_viseme_pp.png`,
`three_quarter_viseme_aa.png` (+ `anatomy_pose_report.json`,
`identity025_head_a_mouth_anatomy.zip`).

Before images (same pipeline, fix disabled):
`output/identity022_jaw_stills/20261112_104220_901389/front_neutral.png`,
`front_jaw_open.png`; cross-checked with IDENTITY-023/024 outputs.

Side-by-side mouth crop: `output/identity025_before_after_mouth.png`
(before: grey dome + packed grille + red gum wedge; after: upper arch with
gum line, dark oral depth, lower arch + tongue tip; before == after
neutral pose almost identical, as expected — teeth hidden by closed lips in
both).

Visual notes (independent review pending):
- `front_neutral`: closed lips natural; no tooth exposure or artefact.
- `front_jaw_open`: full upper arch with natural gum line; lower arch;
  dark throat; tongue tip behind the lower arch; lips frame the opening.
- `front_viseme_aa`: speech open vowel — arches and gums visible; vowel
  shape taken from the unmodified body morph.
- `front_viseme_pp`: pressed bilabial — lips fully closed, no teeth/gum
  exposure (correct for /p, b, m/).
- `three_quarter_viseme_aa`: no neck/jaw silhouette artefacts; mouth
  reads naturally from 38°.

## Known limits and non-claims

- **No likeness claim.** `character_001_likeness: NOT_TESTED`;
  likeness gates remain FAIL (this fix does not touch identity).
- Visual quality is `PENDING_INDEPENDENT_REVIEW` — no owner sign-off yet.
  The MPFB `teeth_base` asset is inherently photo-projected and slightly
  blocky; gum texture is saturated red; no likeness/photorealism is
  claimed for either.
- The cavity selection is **pinned to jawOpen = 0.85** at selection time
  (materials are static afterwards). At intermediate jaw positions most of
  the interior remains occluded by lips/teeth; verify continuously in
  animation review.
- The 16 cavity faces cover the front view cone; extreme opening corners
  at oblique angles may still show a sliver of unlit interior (no render
  evidence of failure at the tested angles).
- The lip corners/lips themselves are unchanged (no body-morph edits) by
  design — "preserving existing functionality".
- GLB export of the corrected anatomy is **not** performed;
  `full_character_glb_export: NOT_TESTED`. The correction lives in the
  same in-memory copied pipeline as all IDENTITY-01x diagnostics.
- Pre-existing render noise (EEVEE, 16 samples) in the throat-shadow area
  of the white clay is unchanged from before; consider ≥32 samples for
  final stills.
- Face is deliberately untextured clay (this pipeline has never applied
  skin/facial textures to the body).
- Windows-only evidence; no Blender build-cross-checks performed.

## Commands to reproduce

    git clone https://github.com/Orchard254/Livynth.git <tmp>   # verified == 2105a59
    git checkout -b fix/head-a-mouth-anatomy diagnostic/identity-024-dental-arch-isolation
    python -m unittest discover -s tests -p "test_mouth_anatomy.py" -v
    python -m unittest discover -s tests -v
    python tools/local_check.py
    python tools/run_mouth_anatomy.py

(The runner always uses the owner's Blender 4.5.10 via
`livynth_studio.find_blender()`; outputs land under
`output/mouth_anatomy/<timestamp>/`, never in Git.)

## Rollback / scope

- All changes additive; existing paths untouched. Roll back by deleting
  the branch; nothing outside the opt-in path is affected.
- No installed MPFB asset, no MPFB source human, no previously exported
  GLB, no prior identity branch artefact is modified or deleted. The
  working tree still carries the user's pre-existing untracked/modified
  files (`assets/README.md` deletion, `assets/voice_transcript.txt`) —
  untouched by this fix.

## Next gates before call this "done"

1. Owner (or an independent blinded reviewer) judges the five after-stills
   against this report; any fail → iterate seats (`--upper-seat`,
   `--tongue-seat`) or cavity window constants.
2. If approved, a separate export experiment may carry the corrected
   geometry into a GLB (own gate; needs sign-off; nothing done here).
3. Keep the likeness gate FAIL until independent identity evidence exists.

---

**IDENTITY-026 (2026-11-12) supersedes parts of this report.** A second
pass fixed the unnatural pink surface (muted copied tongue/teeth
diffuses), the oversized dental appearance (copied teeth scaled 0.85),
the sharp lower-lip contour (101-vertex sulcus lift), and corrected the
cavity-selection mismatch (same-pose evaluated selection + validated
evaluated↔base polygon correspondence). New collision evidence (Möller
transversal-crossing counts) is included there:
`docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_026.md`
