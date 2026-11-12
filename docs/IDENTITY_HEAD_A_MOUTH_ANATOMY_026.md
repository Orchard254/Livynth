# LIVYNTH IDENTITY-026 — Head A mouth anatomy, second pass (pink surface, dental size, lip contour, cavity mismatch)

**Date:** 2026-11-12 · **Branch:** `fix/head-a-mouth-anatomy` (stacked on
`diagnostic/identity-024-dental-arch-isolation`, tip `2105a59`) ·
**Blender:** 4.5.10 LTS (Windows) · **MPFB build:** 20261010 ·
**Status:** fixes implemented and measured; visual quality still
`PENDING_INDEPENDENT_REVIEW`. No likeness or photorealism is claimed.

## Objective (from the review of PR #31 / IDENTITY-025)

1. Fix the remaining unnatural pink mouth surface.
2. Fix the oversized dental appearance.
3. Fix the sharp lower-lip contour.
4. Correct the evaluated-mesh cavity-selection mismatch.
5. Demonstrate natural neutral, jaw-open and speech poses with collision
   checks, passing tests and independently reviewable renders — without
   modifying source assets.

All fixes are in the same opt-in `--oral-anatomy` path as IDENTITY-025
(disposable copied scene assets only). No installed MPFB asset, no source
human, no previously exported GLB and no prior evidence artefact is
modified. Topology, vertex groups, skin weights, UVs and shape-key counts
are unchanged everywhere.

## Verdict up front (visual — owner/independent review required)

- **Pink surface:** the tongue's salmon diffuse and the teeth asset's two
  giant red gum slabs — the two remaining pink masses — are both muted on
  the *copied* assets. The mouth interior now reads as dark brick tissue
  behind a white incisor row, in open and speech poses.
- **Oversized dental appearance:** the copied teeth are uniformly scaled
  0.85 about their body-space centroid. The arch no longer fills the
  opening corner-to-corner.
- **Sharp lower-lip contour:** a mentolabial-sulcus forward lift
  (quartic falloff, 101 vertices, ≤ 10 mm at band centre) softens the hard
  under-lip crease. Improvement is real but subtle; the lip rim itself is
  deliberately untouched.
- **Cavity mismatch:** the selector now runs entirely in the evaluated
  jaw-open pose and the evaluated↔base index mapping is *validated*
  (13,378 polygon loop-vertex tuples), never assumed.
- **Collision checks:** new exact Möller transversal-crossing audit
  (below) in addition to the point-to-triangle clearance audit. Fixed
  configuration: **12 upper↔lower arch facet-crossings** at the occlusal
  plane (the untouched asset has 0; see the trade-off section before
  judging) and **46 (jaw-open) / 82 (neutral) tongue↔teeth crossings**
  (untouched asset: 168/201 — improved by the seats).

Renders (this pass):
`output/mouth_anatomy/20261112_170216_285718/
 front_neutral.png, front_jaw_open.png, front_viseme_aa.png,
 front_viseme_pp.png, three_quarter_viseme_aa.png`
(400×600 mouth closeup; + `anatomy_pose_report.json`,
`identity025_head_a_mouth_anatomy.zip`).

## 1. The four fixes in detail

### 1a. Unnatural pink surface → two-target mute (copied assets only)

**Tongue** (`Human.tongue01`, the 20261010 MPFB diffuse, a
litspheres/mhmat with the salmon tongue01_diffuse.png): an
`ShaderNodeHueSaturation` node is inserted between the image node and
the Principled BSDF Base Color — saturation × 0.55, value × 0.72.
The installed `tongue01.mhmat`/`.png` are never opened for writing; the
edit lives in the copied node tree. Report field
`tongue_material: [{material: Human.tongue01, mode: HSV_NODE_INSERTED,
saturation: 0.55, value: 0.72}]`.

**Gum slabs** (the two large red UV islands baked into `teeth.png`, which
rendered as a bright "dinner plate" behind the tooth row): the copied
TexImage node is reassigned to an **in-memory copy** (`image.copy()` +
`pack()`, named `livynth_oral_gum_muted`) whose gum-classified texels are
blended 80 % toward a dark brick tone (0.30, 0.16, 0.14). Classification
is a pure function (`tools/mouth_anatomy.classify_gum_pixels`):
`R > G + 45/255 AND R > B + 35/255 AND R < 190/255`
— measured **27.81 %** of 2048×2048 texels, matching the offline
independent check (27.6 %–29.7 %). Tooth texels (near-neutral grey,
mean (71, 68, 67)) are bit-identical. The installed `teeth.png` is
untouched (`installed_file_untouched: true` in the report).

### 1b. Oversized dental appearance → uniform scale of the copied asset

`plan_uniform_scale` (pure, validated, bounded 0.60–1.30): the copied
teeth asset is scaled **0.85** about the asset's body-space Basis
centroid ([−1e-09, −0.1324, 1.5725]) in every shape-key block
(Basis/jawOpen/viseme_aa — the same shape-key-safe affine pattern as the
seat fix; storage error 6.4e-08 m). Arch extents before → after:

| Arch (evaluated world) | Before | After (scale only) |
|---|---|---|
| Upper arch x-span | 0.0630 m | ≈ 0.0536 m |
| Lower arch x-span | 0.0565 m | ≈ 0.0480 m |
| Arch max displacement | — | ≤ 9.63 mm |

A dedicated seat sweep (table below) showed 0.85 reads naturally without
folding the cusps into the chin silhouette.

### 1c. Sharp lower-lip contour → mentolabial-sulcus forward lift

`plan_lip_soften` (pure): front vertices (y < 0) with |x| ≤ 0.034 whose
z is within 0.030 m of 1.492 receive a −Y displacement following a
quartic falloff, peaking at 0.010 m at the band centre. **101 vertices
moved** (of 13,380), max displacement 9.86 mm, applied identically to all
**68 shape-key blocks** (Basis + 67 morphs) so pose evaluation is
consistent. Topology, vertex order and morph deltas are preserved.

Safety invariant (hard error): the lifted sulcus must stay behind the
front envelope — measured `sulcus_behind_lip_margin_m = 0.0395 m`
(band z ≥ 1.515 never moves because its falloff weight is ~0 and the
python check fires if the invariant is ever violated).

**Honest note:** the thin dark line visible under the lower lip in
IDENTITY-025 remains faintly visible — the lift fills the sulcus but the
lip rim itself (body-morph geometry, unchanged by design) is what the
shadow traces. The improvement is moderate, not a transformation; it is
reported as such.

### 1d. Evaluated-mesh cavity-selection mismatch → same-pose selection + validated mapping

What was wrong (IDENTITY-025): BVH candidates were cast against the
**evaluated jawOpen=0.85** body mesh, but the depth/z/normal filter
(`plan_cavity_faces`) consumed centres and normals from the **base (Basis)
polygons** — a different pose (the lower jaw moved ~17.8 mm across the
mouth band). Additionally, the evaluated↔base polygon index correspondence
was *assumed* (correct without modifiers, but never checked).

What is done now (`tools/mpfb_anatomy_ab_blender.py`):

1. The filter consumes centres/normals from the **same evaluated temp
   mesh** used for the BVH hit-finding (same pose, same index space).
2. The z window is derived from the **evaluated** world bounds
   (`cavity_z_window_evaluated_m = [1.520143, 1.598771]`, identical to the
   base-derived window here because the crown does not move; both are
   reported).
3. Before any material assignment, the evaluated↔base index mapping is
   **validated explicitly** by `validate_polygon_correspondence`: identical
   polygon count and identical loop-vertex tuples
   (**13,378/13,378 validated**) — hard error on any mismatch; no silent
   wrong-slot assignment is possible.
4. `cavity_method` is now
   `BVH_FIRST_HIT_FRONT_OPENINGS_JAWOPEN_SAME_POSE_FILTER`.

The re-run selection returns the same 16 face indices as before
(386, 459, …, 7107), but now by a proven mapping instead of an assumed
one. Materials (`livynth_oral_exterior_clay` / `livynth_oral_cavity`)
are unchanged.

## 2. Collision checks (this pass, evaluated world space)

Two complementary audits run on **jawOpen=0.85 with teeth/tongue
correctives engaged** (before this pass the contact numbers were recorded
with the correctives disengaged — both poses looked byte-identical; fixed)
and on **neutral**.

**(a) Point-to-triangle distances** (`contact_method:
POINT_TO_TRIANGLE_EVALUATED_WORLD`):

| Pair | Jaw-open 0.85 | Neutral |
|---|---|---|
| tongue→teeth min / median | 1.86 mm / 16.9 mm | 0.34 mm / 9.9 mm |
| upper↔lower arch min | 0.0004 mm | 0.068 mm |
| lower↔upper arch min | 0.006 mm | 0.0009 mm |

Tongue-teeth "touching at occlusion" at rest (< 0.1 mm) is the resting
contact pose, not a defect.

**(b) Exact transversal crossings — new** (`upper_lower_arch_intersections`,
`tongue_teeth_intersections`; Möller predicate, tangential touches
excluded, AABB broadphase):

| Configuration | Upper↔lower pairs (open / neutral) | Tongue↔teeth pairs (open / neutral) |
|---|---|---|
| Untouched asset (seats 0, scale 1.0) | 0 / 0 | 168 / 201 |
| upper 0.012, tongue 0.024, scale 0.85 | 0 / 10 | 46 / 50 |
| upper 0.016, tongue 0.024, scale 0.85 | 20 / 6 | n/r |
| **default: upper 0.022, tongue 0.024, scale 0.85** | **12 / 12** | **46 / 82** |

Attribution: the upper-arch seat (the fix for the invisible arch) moves
the upper cusps 22 mm into the designed occlusal interlock, adding the
12 crossings (2 upper facets — incisal ridge facets — in both poses).
The untouched asset's 0 results from the arches simply never meeting.
Tongue↔teeth crossings are **reduced** from 168/201 to 46/82 by the
tongue seat.

**Trade-off (owner decision):** `--upper-seat 0.012` yields 0/10 crossings
but renders the cusps as detached photo-projection bulbs and was rejected
visually. 12/12 facet crossings at the occlusal plane are the asset's
designed bite interlock (photographic MPFB slabs), not gross
interpenetration — the renders show a clean tooth row with a dark gap to
the lower arch. `--upper-seat 0.012` remains one flag away if the owner
prefers zero crossings over the current render.

**(c) Anti-collision invariant** for the sulcus lift: margin 0.0395 m
against the band z ≥ 1.515 front envelope (hard error otherwise).

**(d) Post-fix motion gate preserved:** `seamed_jaw_motion_after_fix:
PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA` — lower arch 1,884
vertices move 15.10 mm (0.85 × the unscaled 17.76 mm), upper 1,984 remain
stationary. `seamed_jaw_motion_audit` also PASS. Mixed jaw faces skipped:
0.

**Not tested, honestly:** volumetric non-interpenetration in the strict
sense (signed distance volumes), tongue self-fold, lip-seal tearing under
maximum viseme weights, triangle–triangle SAT edge cases (the Möller test
covers transversal crossings only, not coplanar overlap), self-intersections
(`NOT_TESTED`).

## 3. Renders and crops (independently reviewable)

Official run for this pass:
`output/mouth_anatomy/20261112_170216_285718/`

| File | Content |
|---|---|
| front_neutral.png | closed lips, no exposure; soft under-lip crease |
| front_jaw_open.png | full upper arch + muted gum line, dark cavity, tongue low |
| front_viseme_aa.png | speech open vowel — incisors peek above muted brick dome |
| front_viseme_pp.png | pressed bilabial — lips closed, no teeth/gum exposure |
| three_quarter_viseme_aa.png | 38° view — no silhouette artefacts |

Before/after comparisons (git-ignored `output/`):
`output/compare_seat_front_jaw_open.png` (0.022 vs 0.012 upper seat),
`output/compare_neutral_v25_v26.png`, `output/compare_viseme_aa_lip_edge.png`
(three passes), `output/final_before_jaw_open.png`,
`output/final_after_*.png`.

Before-render reference: `output/mouth_anatomy/20261112_144208_181158/`
(same framing; before this pass's fixes).

**Lip-corner pinhole:** a ~2 px dark speck remains at the viewer-right lip
corner in all poses — the shared mouth-corner seam of the unmodified body
morph. It predates this fix, was not introduced by it, and is documented
rather than masked.

## 4. Automated tests (Windows, 2026-11-12)

| Suite | Result |
|---|---|
| `python -m unittest discover -s tests -p "test_mouth_anatomy.py" -v` | **87 tests OK** (seats, scale, sulcus falloff, gum classifier, Möller predicate, polygon correspondence, point-to-triangle distances, cavity selection) |
| `python -m unittest discover -s tests` | **448 tests OK** (skipped 5, pre-existing) |
| `python tools/local_check.py` | **PASS** (exit 0) |
| `python tools/branch_audit.py --run-tests` | exit 0; geo/tests and local_check passed; `main` untouched (`0db7a7d`) |
| `python tools/run_mouth_anatomy.py` | `CAPTURED_HEAD_A_MOUTH_ANATOMY_PENDING_VISUAL_REVIEW`; report contract validated (incl. cavity correspondence and Möller audit presence); ZIP produced |

## 5. Known limits and non-claims

- **No likeness claim.** `character_001_likeness: NOT_TESTED`; Phase-3
  likeness gate remains FAIL.
- **Visual quality `PENDING_INDEPENDENT_REVIEW`** — no owner sign-off.
  The teeth are now visibly present but retain MPFB's photo-projection
  look (slightly blocky cusps, panel gaps between tooth shells); the gum
  slab is muted, not anatomically shaped; the lip rim is unchanged.
- **Occlusal interlock:** 12 upper↔lower facet crossings (both poses) are
  the designed bite of the fitted asset, made visible by the needed upper
  seat. Not a merge blocker for a diagnostic pipeline; decision documented
  under *Trade-off*.
- **Cavity selection pinned to jawOpen = 0.85** at selection time (materials
  are static afterwards); intermediate poses are unverified — review in a
  real animation before reusing this material mask elsewhere.
- **Sulcus lift is modest** by design (max 10 mm band centre, falloff to
  zero outside); it cannot remove the knife-edge lip rim.
- **GLB export not performed** — `full_character_glb_export: NOT_TESTED`.
  The fixes live in the in-memory copied pipeline, like all IDENTITY-01x
  work. Installed MPFB assets, source human, existing GLBs, prior evidence
  — all untouched and verified by the report's `source_assets_modified:
  false` fields.
- **Windows-only evidence**; no cross-build Blender checks.

## 6. Commands to reproduce

    git checkout fix/head-a-mouth-anatomy   # after cloning origin/Orchard254/Livynth
    python -m unittest discover -s tests -p "test_mouth_anatomy.py" -v
    python -m unittest discover -s tests -v
    python tools/local_check.py
    python tools/run_mouth_anatomy.py                       # official run
    python tools/run_mouth_anatomy.py --upper-seat 0.012    # zero-open-crossing variant
    python tools/run_mouth_anatomy.py --tooth-scale 0.80    # deeper down-scale experiment

Outputs land in `output/mouth_anatomy/<timestamp>/` (git-ignored).

## 7. Rollback / scope

All changes additive behind `--oral-anatomy`. Roll back by deleting the
branch; nothing outside the opt-in path is affected. The four new/changed
source files are `tools/mouth_anatomy.py`,
`tools/mpfb_anatomy_ab_blender.py`, `tools/run_mouth_anatomy.py`,
`tests/test_mouth_anatomy.py` (+ this document and
`docs/PRODUCT_STATUS.md`).

## 8. Gates before done

1. Owner/independent blinded judge reviews the five stills; any fail →
   iterate `--upper-seat` / `--tooth-scale` / `TEETH_GUM_TONE` / sulcus
   constants.
2. If approved, a separate export experiment may carry these copies into a
   GLB (own gate; nothing done here).
3. Likeness gate stays FAIL until independent identity evidence exists.
