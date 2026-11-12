# LIVYNTH IDENTITY-022 — Head A jaw closeups (experiment only)

**Status:** Candidate code, Windows Blender result pending. Main and earlier GLBs unchanged.

## Evidence inherited from Windows IDENTITY-021

The owner verified on 2026-11-12:
- 10/10 IDENTITY-021 tests passed.
- `PASS_RIGGED_COPY_STRUCTURE_NOT_JAW_MOTION_OR_VISUAL_QA` on real
  Blender 4.5.10 LTS / MPFB build 20261010.
- Removing 20 mixed-jaw bridge faces from the disposable copied teeth mesh
  retained 3,868 vertices, 3,540 faces, UV layer, material slots, armature,
  vertex groups and all 3,868 per-vertex skin-weight assignments.
- Upper 1,984 and lower 1,884 vertices; no cross-jaw edges.
- No movement or visual appearance approved by that proof.

## Next gated experiment

One opt-in Head A (demo_head_a) renderer:
`python tools/run_mpfb_seam_jaw_stills.py`

It builds the MPFB human and rig in an ephemeral Blender process, verifies
the real rigged-copy seam proof again **inside that one process** to guard
integration, and cuts the 20 bridge polygons on a separate in-memory
export-copy dental mesh. The source MPFB OBJ/MHCLO, original source human,
previous GLBs and main are not modified. It uses the established A/B
identity shape and inherited alignment and oral-corrective pipeline.
A post-body-bake check verifies no lost tooth vertices or seam polygons.
It then checks evaluated world-space neutral-to-jawOpen motion separately
for upper and lower teeth. The required gate is:
`PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA` with 1,884 lower
vertices moving, 1,984 upper vertices stable, and a whole-mouth motion
signal. Failures stop before rendering whenever possible.

If the motion checks pass, the script renders **only two 400x600 RGBA
mouth-focused stills**: `front_neutral.png`, `front_jaw_open.png`.
It writes `anatomy_pose_report.json`, validates all three,
then packages `identity022_head_a_jaw_review.zip`.

Output folder (fresh every run):
`output/identity022_jaw_stills/<timestamp>/`

The owner should upload the ZIP file after a successful run, or the
PowerShell/Blender failure output if it fails. Review must independently
inspect teeth alignment, gums, tongue, tooth count/shape, mouth contact
and undesirable exposed grilles. Numeric jaw motion is not an anatomy
or photo-likeness certificate.

## New focused tests

`python -m unittest discover -s tests -p "test_mhclo_seam_jaw_stills.py" -v`

The command above is the only newly required unit-test suite.
Do NOT repeat prior IDENTITY-018/019/020/021 tests, and do not run Head B
or the 12-pose A/B review yet.

Review and merge experimental branches only after their evidence gates.
No manual edits to installed source assets or previously generated GLBs.
