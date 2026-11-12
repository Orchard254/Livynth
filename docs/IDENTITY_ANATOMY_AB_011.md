# IDENTITY-011 — Fit MPFB anatomy to BOTH reusable detailed faces

**Status: prototype implemented; Windows Blender A/B anatomy renders NOT RUN.**
Date: 2026-11-12.

## Owner-provided evidence (IDENTITY-010)

The owner uploaded anatomy_probe.json, neutral_front.png and neutral_three_quarter.png.
Windows Blender 4.5.10 shows fitted high-poly eyes (1,064 vertices), teeth_base
(3,868) and tongue01 (226), all parented to Human.rig with Armature modifiers.
The rig has 163 bones; both 480×720 images show recognizable blue irises and
reasonable socket placement. The teeth/tongue are obscured by closed lips.
The unbaked native body has 19,158 vertices, not directly comparable to the
13,380-vertex baked Head A/B GLBs. No detailed facial parameters were applied
and neither existing GLB was changed.

## New experiment

The same three SHA-pinned installed MPFB assets are attached to a fresh human
for EACH detailed identity. Each scene uses identical broad macro parameters
and the standard 163-joint rig. Attachments are added BEFORE ExportService's
documented character copy/bake, while the native MHClO vertex mappings work.
After baking only the copied body, apply the correct six head_shape controls,
read the real float32 positions back and perform the local geometry fold audit.
Load the same 67 ARKit + Meta targets. Require all three copied assets to be
rigged to the COPIED armature; reject silently orphaned objects.

Render six 400×600 stills per identity: front neutral, full blink, jawOpen,
viseme_aa, viseme_PP, and three-quarter jawOpen. Validate the reports for
same source neutral SHA/topology and same 67 names, different fitted geometry,
163 joints and the expected native assets. A complete run packages 12 PNGs,
the JSON reports and static HTML gallery into a ZIP.

## One command on Windows

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python -m unittest tests.test_anatomy_ab_review -v
    python tools/run_anatomy_ab_review.py

The ZIP appears under output/anatomy_ab_review; upload that ZIP rather than
either of the existing working GLBs. If the command fails, save the exact
console error and partial output folder. Do NOT rerun the original neutral
probe, and do NOT modify the proven demo_head_*.glb source files.

## What this test does NOT prove

Even a complete 12-image run requires independent visual review. JawOpen and
viseme_aa are BODY MORPH TARGETS, whereas teeth/tongue are ARMATURE-SKINNED
assets; they might not follow jaw or lip movement. That synchronization risk
is exactly what the static comparison should reveal. No GLB-with-assets export,
image-to-identity fitting, photorealism or natural temporal lip-sync is claimed.
Character 001 five-view likeness Phase-3 remains FAIL. Commercial asset
redistribution rights require separate verification.

Technical basis: MPFB official HumanService.add_mhclo_asset and
ExportService.create_character_copy, including the official full-character
export sample.
