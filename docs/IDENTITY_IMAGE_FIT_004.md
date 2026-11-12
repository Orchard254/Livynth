# IDENTITY-004 — Image landmark to head parameters, bounded diagnostic

**Status: IMPLEMENTED DIAGNOSTIC, not automatic photorealistic reconstruction.**
Character 001 identity Phase-3 is **FAIL**.

## Purpose

Convert manually reviewed 2D landmark measurements across front, left profile
and right profile images to six continuous parametric identity controls using
an explicit weak-perspective camera estimate for each view.

The solver consumes:
- The verified native MPFB neutral mesh and optional native quads.
- 2D image points in pixels with named vertex index correspondences and a
  per-point pixel uncertainty (sigma).
- Per-view estimated yaw, pitch, roll, scale and raster translation.

It deliberately does NOT:
- Infer cameras from photos on its own.
- Infer image-to-mesh anatomical correspondences or hair geometry.
- Claim that AI-generated independent views are calibrated scans.
- Export or approve an image-derived identity recipe into Blender.

The same six native head controls are used here and in IDENTITY-003. Camera
parameters are kept fixed during this diagnostic, so camera uncertainty is
not absorbed by a claim of successful 3D reconstruction.

## Algorithm and safety gates

The head-shape displacement field is linear in its six coefficients.
The solver builds a two-coordinate reprojection equation for each observed
landmark, weights it by the observed pixel uncertainty, adds an L2 prior
and solves bounded [-1,+1] least squares. It rejects insufficient view
coverage, invalid observations, non-finite camera measurements and a
rank-deficient correspondence system.

When native quad topology is available, the raw solution is independently
checked against native geometry. If it flips/collapses local triangles, a
deterministic trust-region backoff tries lower shape intensity. The candidate
cannot be exported as an identity; the output records original parameters,
safe parameters, backoff factor, numeric geometry QA and per-view errors.

If either side profile becomes worse by the diagnostic threshold, the report
status is REJECTED_PROFILE_REGRESSION and the CLI exits 2 after saving the
report. Even if no profile regresses, the status remains
DIAGNOSTIC_ONLY_UNAPPROVED because neutral geometry, perspective and
held-out views have not passed blind review.

## First real Character 001 experiment — results

Inputs: manual pixel annotations and provisional native vertex IDs from the
previous C001-GEO05 feasibility work, with three source-optimized weak-
perspective camera guesses. The images are independently AI-generated.
Original neutral fingerprint:
64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542.

- Numerically identifiable matrix rank: 6 of 6.
- Design matrix condition number: 25.921.
- Full unconstrained-by-geometry fitted parameters reduced the combined
  weighted residual but **FAILED the local quad-collapse threshold**.
- Geometry-safe backoff factor: **0.60**; remaining max head vertex displacement
  approximately **6.32 mm**, minimum triangle area ratio **0.432**.
- Combined uncertainty-normalized RMSE before: **1.3573**, after: **0.9661**.
- Front-view weighted RMSE: 1.8850 -> 1.3130.
- Left-profile weighted RMSE: 0.4157 -> 0.3968.
- Right-profile weighted RMSE: **0.2992 -> 0.3579 (WORSE)**.
- Held-out ±45-degree independent review: **NOT RUN**.
- Final status: **REJECTED_PROFILE_REGRESSION**, approved_identity false.

The improvement of the aggregate pixel error cannot override the worse
right profile, missing holdouts, uncertain landmark semantics or imperfect
camera model. This candidate MUST NOT be treated as a successful identity
or passed as a recipe to the Blender exporter.

## Reproduce

The owner can supply a 3-view observation JSON with the interface
livynth.image-landmark-fit.v1 (see unit tests for the exact machine-readable
layout). The pre-existing C001 manually annotated observations are *private
analysis artifacts* and were not committed as photos.

From repository root:

    python -m unittest tests.test_image_landmark_fit -v
    python tools/run_image_landmark_fit.py --neutral output/c001_geo05/stage1_review.zip --observations PATH_TO_OBSERVATIONS.json --out output/c001_image_proposal.json

The diagnostic writes its output even when a proposed fit is rejected;
the process returns exit code 2 on rejected profile/geometry or unidentifiable
correspondences. No GLB is built.

## What must change before automatic image-to-3D is real

1. Automatically detect and map image landmarks to **verified matching
   anatomical vertices** on the base mesh, not provisional indices.
2. Estimate image cameras jointly with identity coefficients and quantify
   uncertainty; guard against contradictory independently generated views.
3. Fit many more facial shape degrees of freedom, silhouettes and depth,
   with geometry-first constraints and self-intersection QA.
4. Reserve the two ±45-degree references for untouched holdout comparisons.
5. Verify both identity likeness and postfit blinking/jaw/viseme motion in
   actual Blender GLBs, and only then add skin, eyes, hair and materials.

This experiment is an engineering stepping stone, not the full user goal.
