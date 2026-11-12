# IDENTITY-007 — Rendered expression comparison for two reusable humans

**Status: new source and 15 focused tests authored. Actual Blender pose renders NOT YET RUN.**
Date: 2026-11-12.

## Why this gate matters

Owner Windows evidence confirms that both exported A/B characters share
163 joint names, 67 facial target names, skin and UV data, and nonzero glTF
morph displacements for seven key controls. Those measurements cannot tell
whether the eyes close naturally, the jaw moves cleanly or speech shapes
distort anatomy. IDENTITY-007 renders the exact same controlled poses on
both EXISTING GLBs for direct visual comparison.

## Existing Windows evidence (2026-11-12)

- Windows application suite: 176 tests run, **174 passed, 2 skipped**, 0 failed.
- Geometry suites: 174 tests run, **172 passed, 2 skipped**, 0 failed.
- Combined completed: **346 passed, 4 skipped**, 0 failures.
- Strict glTF morph QA: PASS_NONZERO_EXPORTED_MORPH_SIGNAL_NOT_VISUAL_ANIMATION.
- Each GLB: 163 joints, 67 matching facial targets, 14,517 seam-expanded glTF
  vertices, nonzero eyeBlinkLeft, eyeBlinkRight, jawOpen, mouthClose,
  mouthPucker, viseme_aa and viseme_PP displacements.
- Different exported positions in 4,576 vertices over 0.1 mm; maximum A/B
  displacement 20.8193 mm. Original Blender native mesh is still 13,380
  vertices and 13,378 quads; UV seam expansion is NOT a topology change.

## Windows acceptance command (existing GLBs only)

From repository root after pulling the development branch:

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python tools/run_identity_pose_review.py --folder output\identity_ab\20261112_045945_179772

Outputs go to a fresh timestamped pose_review directory inside the original
identity_ab folder. The driver first verifies the existing A/B morph data,
then runs Blender once per character to render **10 small images each**:
front neutral, blink, jaw_open, viseme_aa, viseme_pp, smile and pucker;
three-quarter (38°) neutral, blink and jaw_open.

Output: 20 diagnostic 400×600 PNGs, two individual render_report.json files,
a pose_review.json manifest and a self-contained index.html showing A and B
side by side. Open index.html with a browser.

The driver refuses overwrites, invalid or corrupt PNGs, absent frames,
missing actual pose pixel differences and incompatible imported morphs.
The pixel comparison samples a fixed face crop: it can show that something
changed, NOT that it changed naturally.

## Independent visual-review criteria

Both humans must show intact eyelids and no tearing on full blink; credible
jaw open and chin motion; different mouth closure, vowel and pucker poses;
no visible broken polygons or unnatural face distortions; plausible front
and three-quarter shapes with the SAME morph interface. Evaluators must
inspect the images. The output status remains
CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW until that step is complete.

This is **not** a Character 001 likeness test. The five-view identity gate
still FAILS and image-to-identity fitting remains incomplete. Eye geometry,
hair, skin realism, human perception and speech timing require separate work.

Only share the small review JSON and selected images or a pose_review archive.
Neither source GLB nor user images are modified or committed in this change.
