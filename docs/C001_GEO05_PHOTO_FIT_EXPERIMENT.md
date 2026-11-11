# LIVYNTH C001-GEO-05 — First photo-to-mesh experiment (non-certifying)

**Date:** 12 November 2026. **Status:** Exploratory numeric geometry feasibility only; **Phase-3 identity remains FAIL** and Stage-1 rigged Blender fitting is **NOT RUN**.

## Source audits
- Unchanged native mesh: **13,380 vertices / 13,378 quads** and SHA `64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542`. The numeric deformation does not alter source vertices or topology indices.
- Character 001 ZIP: **16 nested images** (original + 15 other views). All are AI-generated references, not calibrated photography.
- **Image packaging conflict:** root paths `09_left_ear.png`, `11_eyes_closeup.png`, `13_skin_macro.png`, `15_hair_closeup.png` are lower-resolution, different files than their nested counterparts. Use nested originals; see `reference_manifest.json`.
- `07_top_head.png` is an elevated view of a bowed head, not a true top-down orthographic skull capture. Do not use as a 3D depth constraint.
- Development 2D cues: frontal `01_subject_front.png` and left/right profiles `04_left_profile.png`, `05_right_profile.png`. **Reserved holdouts:** `00_original_portrait.png`, `02_subject_left_45.png`, `03_subject_right_45.png`.

## Hand-estimated image measurements (not precision landmarks)
These were read visually from actual high-resolution source images. Estimated precision **±5–20 px** plus much larger systematic camera/identity uncertainty.

- Frontal pupil spacing ≈ **210 px**; mouth-corner width ≈ **171 px**; nasal width ≈ **107 px**.
- Left profile nose–chin silhouette difference ≈ **66 px**, eye–ear horizontal gap ≈ **407 px**.
- Right profile nose–chin difference ≈ **64 px**, eye–ear gap ≈ **406 px**. The two observed profile ratios are close, but do not prove calibrated consistency.
- Neutral mesh eye center **approximated from midpoint of eye-corner candidates** (not an iris mesh measurement), with F04 nose tip, F09 chin, F16 alar, F18 mouth corner and F24 ear candidates. Semantic mappings are provisional.

| Image-normalized measurement | Generic neutral | Reference approximate | Conservative hypothesis |
|---|---:|---:|---:|
| Mouth width / eye span | 1.010 | 0.814 | 0.896 |
| Nose width / eye span | 0.695 | 0.510 | 0.583 |
| Nose-chin / eye-ear profile depth | 0.218 | 0.160 | 0.182 |

## Numerical method and gate
A mirror-symmetric Gaussian radial basis field, radius **25 mm**, restricted to a tapered head Z region **1.50–1.72 m**, with an absolute displacement limit of **12 mm**. Three source anchors and their mirrored controls are used. The conservative model applies **65%** of a ratio-derived adjustment; there is also an undamped direct-ratio model **for numeric comparison only**.

| Proof case | Max vertex motion | Vertices moving >0.1 mm | Minimum local triangle area ratio | Face folding |
|---|---:|---:|---:|---|
| Control | 0 mm | 0 | 1.000 | None detected |
| Conservative | 4.71 mm | 2,666 | 0.728 | None detected |
| Direct-ratio | 7.25 mm | 2,720 | 0.597 | None detected |

These local tests **do not prove global self-intersection-free geometry**, working postfit morphs/rig, or Character 001 identity. The NPZ outputs are explicitly geometry-only and not GLBs.

## Decision
**Do not promote a candidate to Stage-1 identity acceptance yet.** The trends support an exploratory nose/mouth adjustment, but the reference images are not calibrated. In the side-by-side diagnostic, the generic MPFB head is still visibly different from the photographed reference in skull/forehead, jaw, ears, lower-face shape and hair. The adjusted geometry changes are subtle; there is no demonstrated improvement on the untouched ±45° holdouts.

### Next concrete engineering experiments
1. Independently review the 3 native anchor labels and 2D pixel locations. Build a camera-registration model for all five primary views, treating camera yaw, scale, framing and 2D pixel uncertainty as estimated—not known. Compare predicted points with measured holdouts.
2. Add face silhouette/jawline correspondences, with a robust loss and left/right profile disagreement penalty. Keep hair excluded from the geometry silhouette until hair geometry is modeled independently.
3. Only then generate an **owner-reviewed** `livynth.c001.stage1.constraints.v1` document; rerun actual Windows Blender post-fit audit for 67 morphs, 163 joints, UV, weights and motion.
4. Add independent global intersection test and blind five-view gate, with canaries. If any profile receives REGENERATE, reject candidate; no texture rescue.


## Additional independent-camera diagnostic (weak perspective, not calibrated)

After the initial ratio-only test, a bounded camera fit was performed on each of the 3 development images. **Each geometry variant's camera was optimized independently**, so the following are *in-sample, noncomparable to a blind holdout score*, and camera settings may absorb geometry error. Frontal yaw bound ±3°, side yaw ±8°, pitch ±16°, roll ±6°. Approximate photo pixel landmarks were those in the public measurement JSON; source 3D eye centers were still provisional canthus midpoints.

| Hypothesis | Frontal reprojection RMSE | Left-profile RMSE | Right-profile RMSE |
|---|---:|---:|---:|
| Source neutral | 30.2 px | 7.1 px | 5.3 px |
| Conservative | 23.5 px | 9.8 px | 5.2 px |
| Direct-ratio | 20.8 px | 12.3 px | 7.5 px |

The front solver reaches +3° yaw bound for all models. The conservative adjustment improves the in-sample front but worsens one side profile, and full direct-ratio scaling worsens both side profiles. That is **not** sufficient to claim improved identity. The untouched ±45° images remain genuinely held out from these numerical experiments.

**Next technical step:** use a joint five-view camera/geometry model and explicit semantic image-to-vertex correspondence with uncertainty and holdout, rather than optimizing each camera independently to make deformations look good. The current source is the recommended return point.

Numeric script `c001_camera_diagnostic.py` and output `weak_perspective_camera_diagnostics.json` are included as additional diagnostics. Four camera-basis tests pass locally. This calculation uses SciPy; it is optional for the original NumPy-only fit feasibility.

## Files
- `LIVYNTH_C001_GEO05_photo_mesh_feasibility.png`: three-column reference/neutral/conservative diagnostic (not aligned camera calibration).
- `LIVYNTH_C001_photo_landmark_measurements.png`: manual, uncertain 2D feature marks.
- `reference_manifest.json`: exact selected source copies and SHA hashes.
- `uncalibrated_fit_feasibility.json`: input pixels, 3D source metrics, all numeric results.
- `unapproved_anchor_proposal.json`: **not runnable**, requires manual/camera verification before production use.
- `uncalibrated_fit_feasibility_geometry_only.npz`: source + conservative + direct-ratio vertices and unchanged quads.
- `c001_photo_to_mesh_feasibility.py` + `test_c001_geo05_feasibility.py`: reproducible numeric prototype and 10 numeric regressions. This is not a replacement for the repository MPFB Blender bridge.

**No GitHub branch, PR, or baseline GLB was changed during this experiment.**