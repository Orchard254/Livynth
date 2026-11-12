# IDENTITY-006 — Facial morph-signal quality gate for existing A/B GLBs

**Status: IMPLEMENTED / new dedicated synthetic tests authored; actual owner GLB bytes not yet reviewed.**

The owner has already produced two Blender 4.5.10 rigged GLBs in output/identity_ab/20261112_045945_179772. Do NOT regenerate them merely to assess exported blendshape signal. Instead, inspect their actual GLB data.

## One quick command on Windows (no Blender)

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python tools/glb_morph_qa.py --folder output\identity_ab\20261112_045945_179772

Output if successful: morph_signal_qa.json inside the same folder. Upload this small JSON for independent review. The tool refuses to overwrite an existing JSON report.

## Measured contracts

- Exactly one character mesh with 67 uniquely named exported targets and a 163-joint GLB skin actually bound to that mesh.
- Compatible morph-target and bone names between Head A and Head B; compatible exported vertex counts.
- Nonzero, finite position deltas for both eyelid blink targets, jawOpen, mouthClose, mouthPucker, viseme_aa and viseme_PP. Each required target must move at least 20 exported vertices with displacement at least 0.1 mm and at most 200 mm.
- Different exported neutral vertex positions for at least 100 vertices, with maximum A/B difference at least 1 mm. This is only a geometry distinctness check, not recognizable identity.
- Actual JOINTS_0, WEIGHTS_0 and TEXCOORD_0 glTF attribute types and counts must be consistent with a skinned mesh.

## Important parser correction

The earlier tools/measure_glb_topology.py treated glTF morph-target POSITION as if it contained absolute vertex coordinates, comparing it to the neutral POSITION. According to glTF, it is a displacement delta. A zero-delta target could therefore be falsely reported as active. IDENTITY-006 fixes this and adds support for glTF sparse accessors instead of discarding sparse morph displacements.

## What remains unknown

The checker establishes that facial controls contain exported deformation signal, not that the exported shapes produce good-looking, collision-free or natural animations. For that next gate, render a controlled pose grid for both character GLBs: neutral, full blink, jaw open, mouth closed, speech vowel and smile from front and profile. Images and videos must be judged independently. Rig weights truncated from more than 4 to 4 influences during glTF export remain a motion-quality concern. This work does NOT repair Character 001 likeness, which remains FAIL.

No new GLBs or user images are committed.
