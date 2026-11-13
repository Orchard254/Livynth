# IDENTITY-028 — Head A permanent dentition rebuilt, lip opening corrected (2026-11-13)

Branch: `fix/head-a-mouth-anatomy` (stacked on `diagnostic/identity-024-dental-arch-isolation`).
Runner: `python tools/run_mouth_anatomy.py --procedural-dentition` (opt-in IDENTITY-028 path;
builds on the IDENTITY-025/026/027 fix; original assets and GLBs untouched).

## Goal addressed

> Rebuild Head A’s upper and lower dental geometry and correct the lip-opening shape to
> achieve natural human mouth anatomy across neutral, jaw-open and speech poses,
> eliminating significant tooth intersections without hiding the teeth or masking defects
> with textures, while preserving original assets and existing functionality.

## What was built (all in-memory, on the disposable copy)

1. **Parametric permanent dentition replaces the MPFB photo slab.**
   New module `character/procedural_dentition.py` (pure NumPy, deterministic):
   - complete adult permanent dentition, **FDI two-digit numbering — 32 teeth**
     (11–18, 21–28, 31–38, 41–48), 7 per side per arch plus third molars
     (8 per quadrant).
   - adult-average anthropometry per class (central/lateral incisor, canine,
     first/second premolar, first/second/third molar): mesiodistal width,
     crown height, buccolingual depth, superellipse exponent, cusp field
     (gaussian cusps: 1 canine, 2 premolars, 4 molars; incisors get a shallow
     edge saddle), central-fossa depression 0.4–2.4 mm by class.
   - teeth are placed by an **arc-length walk along a half-cosine arch curve**
     (upper: y −0.1464→−0.090, half width 0.030; lower: y −0.1439→−0.0874,
     half width 0.0295, 2.5 mm lingual overjet built in) with the curve of
     Spee (1.2–1.4 mm posterior drop) and the rest-pose freeway gap
     (1.5 mm vertical) — zero volumetric overlap **by construction**.
   - sub-millimetre interdental gaps (0.4 mm) so individual crowns read in renders.
   - matching horseshoe gingival bands, scalloped gingival margins (each margin
     dips at the tooth centre and lifts toward the contacts, amplitude 1.8 mm),
     inner edge guaranteed to sit beyond the cap plane (never knifes a crown).
   - Blender assembly lives in `tools/procedural_dentition_blender.py`:
     two merged meshes (upper/lower 7 712 vertices, 15 360 triangles each),
     two gingiva bands (288 vertices, 382 tris), one posterior/anterior
     enamel pair (ant whiter, post slightly darker/rougher) + one gingiva
     material — all datablocks created fresh. Basis+jawOpen+viseme_aa shape
     keys: **upper frozen, lower rides the native body morph** (the same
     `derive_lower_jaw_translation` used by the MPFB oral correctives —
     1.6 cm (jawOpen) and 0.76 cm (viseme_aa) median moving lower-face delta),
     so both arches open coherently with the face. The MPFB slab is **hidden
     from renders** and otherwise untouched (kept in scene for reference).
   - Storage validated: evaluated world verts of every created object match
     the planned arrays to ≤ 2e-6 m (hard error otherwise).

2. **Lip-opening shape correction** (`plan_lip_opening` + `reshape_lip_opening`,
   same Basis-plus-all-key-blocks pattern as the sulcus lift; 68 blocks moved,
   max storage error 5.8e-8 m):
   - mouth corners lifted +1.6 mm with a quartic falloff peaked at |x| = 0.0405 m
     (de-stern the downturned corners toward a calmer almond);
   - lower lip/chin band pushed forward 2.2 mm with a quartic falloff centred
     z = 1.463, |x| ≤ 0.044 (balances the strongly retrusive lower face —
     measured 1–2 cm recessive chin band vs upper lip protrusion).
   - 65 of 13 380 vertices move; nothing else in the body changes.

3. **Detector, material isolation, and previous fix unchanged** (IDENTITY-027):
   tongue seat 0.036 m / posterior 0.010 m / scale 0.80; collision predicate
   relative-tolerance Möller; single-user material copies; cavity selection
   validated polygon-loop correspondence (13 378 tuples).

## Collision evidence — procedural arches (official run `id028_20261112_4`)

The numbers below are from the IDENTITY-028 official run
`output/mouth_anatomy/id028_20261112_4` (evaluated world space, poses applied with
correctives):

| Pose | Arch↔arch pairs (min clearance) | Tongue↔teeth pairs (min) |
|---|---|---|
| neutral | **0** (2.40 mm) | **0** (4.69 mm) |
| jaw_open 0.85 | **0** (13.86 mm) | **0** (2.52 mm) |
| viseme_aa 0.90 | **0** (9.47 mm) | **0** (3.45 mm) |
| viseme_pp 0.90 | **0** (2.40 mm) | **0** (4.69 mm) |

Same poses measured the slab at 369–1039 transversal crossings before the rebuild;
the rebuilt arches report **zero by measurement**, not by suppression (teeth are
fully visible behind the lips). `tangential_contact_not_counted` and the
onto-other-plane extent proxy are unchanged; tangential/coplanar sliding stays
out of scope. Depth proxies for the proc arches are `null` since no crossings exist.

`procedural_jaw_motion`: `PASS_PROCEDURAL_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA`
(upper max displacement exactly 0.0 m; lower 7 712/7 712 vertices moved by the
native jaw morph, median 20.9 mm ≤ 30 mm bound, max 20.9 mm ≤ 35 mm bound).
`seamed_jaw_motion_after_fix`: `PASS_…_NOT_VISUAL_QA` (slab reference).
`oral_motion_visible_lower_arch`: `ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED` in
both audited poses (visible teeth + tongue both move).

## Lip-opening and render evidence

Official IDENTITY-028 run `20261112_20261112_4`: five mouth-focused stills
`front_neutral.png`, `front_jaw_open.png`, `front_viseme_aa.png`,
`front_viseme_pp.png`, `three_quarter_viseme_aa.png` (400×600, AgX, 16-sample EEVEE,
verified by `check_png_dimensions` in the runner) + `anatomy_pose_report.json`
(zip `identity025_head_a_mouth_anatomy.zip`, `testzip` clean, 1.31 MB).

- neutral / viseme_pp: calmer closed almond, corners less downturned; no teeth leak.
- jaw_open / viseme_aa: both dental arches visible across the slit; scalloped
  gingival margins; individual crowns read (interdental shade separators).
- three_quarter_viseme_aa: arch visible from 38°; lower row peeks under the upper row.

**Appearance was reviewed by the author only; independent review is required.**
The upper arch occludes most direct view of the lower; the lower row shows
clearly in viseme_aa. The lower lip still sits recessive (the lip correction
moves the whole lower band 2.2 mm, bounded by render review). The rest gap
(1.5 mm freeway space) means closed-mouth poses show no contact; an upper
overbite would read more naturally but forces slab-arch lateral overlap and
was rejected. Both trade-offs are documented here rather than hidden.

## Preservation guarantees

- Installed MPFB assets (eyes/teeth/tongue `.mhclo` + images) re-hashed after
  the run: `installed_mhclo_reverified` → all three `unchanged: true`.
- `existing_glbs_modified: false`, `source_assets_modified: false`,
  `installed_mhclo_obj_modified: false`, `source_human_modified: false`.
- `material_isolation_verified: true`; `installed_image_files_checked: 2`
  (both unchanged); single-user material copies proven per slot;
  cavity faces 16, validated polygons 13 378.
- Slab hidden from renders (`slab_hidden_from_renders: true`), never edited,
  never exported; `existing_glbs` untouched; `main` untouched; user files
  (`assets/README.md`, `assets/voice_transcript.txt`) untouched.
- The pre-IDENTITY-027 and IDENTITY-027 collision audits remain referenced
  under `slab_collision_audits_reference`.

## Tests and checks (2026-11-13)

| Check | Result |
|---|---|
| `python -m unittest discover -s tests` | **488/488 OK** (skipped 5 pre-existing) — includes 18 `test_procedural_dentition.py` (FDI completeness, anthropometry, topology, winding, arch symmetry/curve, scallop, gum geometry, Möller predicate zero crossings, determinant 1) and new `LipOpeningTests` in test_mouth_anatomy.py (5) + MillimetreScale/Tongue/TONGUE validators |
| `python tools/local_check.py` | exit 0 |
| `python tools/branch_audit.py --run-tests` | exit 0 |

## Explicit non-claims / limitations

- **Visual quality = PENDING_INDEPENDENT_REVIEW.** No likeness or photorealism claim.
  The crown forms are parametric (superellipse + gaussian cusps), not measured
  from any human; the anthropometry is adult averages, not this head’s skull.
- The upper/lower arch is a continuous adult set; no third-molar pathology checks,
  no wear, no tilt asymmetries.
- Occlusal `spee` and freeway parameters are design constants, not measurements.
- Coplanar/tangential sliding remains out of scope of the predicate; depth proxies
  are not MTV/SAT. Volumetric SAT and GLB export remain **NOT_TESTED**.
- The teeth\_geometry repair does not address the face’s strong lower-face retrusion
  (face shape is out of scope for the mouth fix; noted by the reviewer as advice
  for a future identity pass, bounded by this task).
- Runner output folder pattern is timestamp-based; `anatomy_pose_report.json` still
  carries `CAPTURED_HEAD_A_MOUTH_ANATOMY_PENDING_VISUAL_REVIEW` and the
  IDENTITY-025-era section names (`ID025_*` error strings) for compatibility.
