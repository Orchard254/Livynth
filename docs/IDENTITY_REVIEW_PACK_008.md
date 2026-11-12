# IDENTITY-008 — Portable expression-review evidence

**Status: IDENTiTY-007 owner Blender render completed; imagery itself not yet inspected.** Date: 2026-11-12.

The owner ran the pose-render driver on Blender 4.5.10 + MPFB 20261010
after pulling the development branch at commit 42c8f1b.
The log confirms both existing GLBs were imported and 10 matched diagnostic
poses per character were rendered without crashes: **20/20 400×600 PNGs**,
**16/16 non-neutral poses with raster change signal**. The review manifest
returned CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW with existing GLB morph
signal PASS and expression naturalness PENDING_HUMAN_REVIEW.

**This is a rendered-expression presence pass, not a visual anatomy pass.**
No PNG images were in the uploaded log, so no independent eyelid, jaw,
lip closure or distortion quality judgment was made.

## Prepare one portable upload — do not rerender

From the user's existing LIVYNTH development checkout:

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python tools/package_identity_pose_review.py --folder output\identity_ab\20261112_045945_179772\pose_review\20261112_060832_140286

This packages the **existing** 20 pose PNGs, their two render JSONs,
the original pose_review.json, a regenerated local HTML gallery, and
a SHA256 verification manifest into this sibling ZIP:

    output\identity_ab\20261112_045945_179772\pose_review\20261112_060832_140286.zip

Upload that ZIP for the independent visual review. It is not necessary
to upload original GLB geometry, original photos, WAV files or model weights.
The packager uses a fixed whitelist of expected paths, verifies the actual
PNG CRC/deflate/format/dimensions, checks the original render reports,
refuses symlinks, refuses to overwrite existing ZIPs and does not modify
the source images. The HTML gallery is regenerated from fixed names, not
copied blindly from a potentially edited local HTML file.

The package contains original reports, which include local Windows file
paths for provenance; users should review those paths before sharing.

## Acceptance after visual inspection

Evaluate each identity's neutral, full blink, jaw-open, vowel, bilabial,
smile and pucker front views plus three-quarter blink/jaw. Reject torn lids,
false jaw hinge, unnatural lip seals, facial intersections, silhouette
implausibility and deforming identity features. Keep identical camera
conditions and the same shape-key names. A changed pixel region is not
an anatomically credible expression.

If both are visually acceptable, the reusable *expression* milestone can
advance. Character 001's image-derived five-view likeness Phase-3 stays FAIL,
and realistic eyes/hair/skin, full narrated character-specific video and
automatic image reconstruction remain unfinished.

Unit tests for the new ZIP packager are included in tests/test_identity_review_bundle.py;
Windows real archive creation remains UNVERIFIED until the owner runs it.
