# IDENTITY-021 — Disposable MPFB rigged teeth seam proof

**State:** Candidate diagnostic code; owner Windows verification pending.

## Established evidence

The SHA256-pinned MPFB teeth asset has 3,868 vertices and 3,560 OBJ faces.
IDENTITY-018 found 20 cross-jaw polygons, and IDENTITY-019 proved that
excluding them would leave 3,540 single-jaw faces with no orphaned
vertices, no non-manifold edges and 33 to 34 connected components.
IDENTITY-020 then proved on Windows Blender 4.5.10 that a scratch copy
can lose those 20 faces without losing any vertex, original index,
remaining polygon or cross-jaw-edge correctness.

## Next candidate gate

The command tools/run_mpfb_rigged_seam_probe.py runs the existing native
MPFB source-human and copied-rig setup for Head A only. After installing
teeth, eyes and tongue into the source and export-copy rig, it stops
BEFORE baking target shapes, deforming detailed heads or rendering.

A further temporary copy of the rigged teeth is created. BMesh removes
the 20 cross-jaw bridge faces on that disposable copy only.
It checks that the pinned OBJ and copied face sets correspond, 3,868
vertex IDs and positions and 3,540 retained polygons survive, copied
skin weights and vertex groups have identical pre/post signatures, the
armature modifier still references the copied rig, UV and material slots
remain and no edge still spans both jaw groups.

Both original MPFB source and export-copy teeth objects remain unchanged.
Temporary Blender data blocks are destroyed after the probe. No source
asset or GLB is saved or modified.

## One new Windows check

Run only these newly added checks after pulling the diagnostic branch:

    python -m unittest discover -s tests -p "test_mhclo_rigged_seam_probe.py" -v
    python tools/run_mpfb_rigged_seam_probe.py

A status of PASS_RIGGED_COPY_STRUCTURE_NOT_JAW_MOTION_OR_VISUAL_QA proves
copied rig structural preservation only. On failure send the JSON from
output/rigged_seam_probe/<timestamp>/rigged_seam_probe.json.

Do not run the completed IDENTITY-018/019/020 checks again. Do not run
12-pose renders or merge into main.

## What is still unverified

Real jaw-open/viseme motion, tongue clearance, teeth appearance, rig
skinning under animation, Head B, eyes and eyelid visuals, Character 001
photo likeness, audible synchronized video and end-to-end product QA.
An opt-in single-character jaw-pose still is the next diagnostic
candidate only AFTER this structural copy test passes.
