# IDENTITY-003 — Native parametric head-shape foundation

**Status: real native geometry A/B proof PASS (offline); Blender GLB + rig/morph A/B UNVERIFIED; Character 001 likeness FAIL.**
Date: 2026-11-12.

## Purpose and implementation

The broad MPFB macro parameters cannot represent a specific face. Added a second, bounded geometric identity layer operating on the original baked-native vertex ordering, **before** FaceService builds the 67 ARKit/Meta facial targets. No new topology is built for each identity.

The new JSON recipe schema livynth.identity.recipe.v2 adds head_shape alongside the original macros; old livynth.identity.recipe.v1 files are unchanged and remain supported. Source remains manual_parameters: this is **not yet photo fitting**.

Six independently adjustable continuous coefficients (each -1 to +1): cranial_width, jaw_width, cheek_fullness, nose_projection, mouth_width and chin_length. Smooth symmetric spatial fields alter identity regions only. Inputs and outputs are numerically checked for non-finite positions, excessive displacements and local quad folding. No original source mesh is modified.

## Verified real neutral mesh results

Source: owner-supplied stage1_review.zip/neutral_mesh.npz (SHA256 native positions 64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542). The full baked native mesh has 13,380 vertices and 13,378 quads.

Both demonstration recipes use **identical broad MPFB macros**, varying only the six detailed head coefficients.

| Metric | Demo Head A | Demo Head B |
|---|---:|---:|
| Max displacement from neutral | 9.25 mm | 11.57 mm |
| Vertices moving over 0.1 mm | 4,381 | 4,391 |
| Minimum local triangle area ratio | 0.502 | 0.772 |
| Local triangle flip check | PASS | PASS |

Maximum direct A/B vertex difference is **20.82 mm**, with **4,318 vertices** differing by more than 1 mm. The two outputs preserve exact face connectivity and native vertex ordering. This is a numeric geometry proof only; both OBJ exports are UNRIGGED.

The local checks do not establish no global self-intersections, no eye collision, verified rigging, natural animation or resemblance to the Character 001 reference. The independent Phase-3 likeness gate remains FAIL.

## Windows next test

From the active development checkout:

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python tools/local_check.py
    python tools/run_identity_ab.py

The A/B runner now defaults to the two same-macro/different-head recipes. For each, Blender must generate a GLB that passes all existing export audits (skin, 163 joints, 67 facial targets, UV and no unexpected mesh). Comparison rejects changed native quad topology, absent/mismatched morph or bone names, identical deformed shape, missing head-shape audit, unsafe local folding or differing unmodified source SHA.

The optional numeric OBJ-only proof can be repeated with:

    python tools/run_head_shape_offline.py --neutral output/c001_geo05/stage1_review.zip --out output/head_shape_ab/first_proof

The output directory must be new (no overwrites).

## Next image-driven step

Add a reference-photo manifest with camera uncertainty and image landmark uncertainty. Jointly fit a parametric shape to front/±45/±90 views with held-out controls. AI-generated independent views are not calibrated scans, so inconsistent geometry must fail a confidence/acceptance gate. The six coefficients are a first controlled prior, not enough to guarantee recognizable identity. Future geometry can be richer without replacing the animation contract.

Before declaring success, independently check five controlled neutral clay/depth/normal views and blink/jaw/viseme motion on both new GLBs. Add eyes, hair, PBR skin and clothing only after structural and identity constraints are met.

No private photo, geometry archive or binary GLB is committed in this PR.
