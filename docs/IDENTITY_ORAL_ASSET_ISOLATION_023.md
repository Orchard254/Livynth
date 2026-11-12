# IDENTITY-023 — Attribution of unacceptable oral surfaces

## Grounded results from IDENTITY-022

On 2026-11-12 the owner supplied
`identity022_head_a_jaw_review.zip`, containing two PNGs and
`anatomy_pose_report.json` from Blender 4.5.10 LTS / MPFB 20261010.

Structural checks remain PASS:
- 3,868 dental mesh vertices; 3,540 remaining faces after a copy-only
  exclusion of 20 bridge faces, no cross-jaw edges and unchanged weights.
- 1,884 lower jaw dental vertices moved 0.017762342 m median in
  the Blender evaluated jaw-open pose; 1,984 upper dental vertices did not
  move at all. Tongue 226/226 vertices moved.
- 13,380 baked BODY vertices, 13,378 quads, 163 joints, 67 facial morphs.

**Visual appearance: FAIL.** Independent review of the two PNGs found
an unnatural pink textured surface above the visible teeth, an excessive
red surface below, and a dense grille-like row of exposed teeth, without
an anatomically convincing separation of upper/lower arches. The neutral
mouth line also looks dark and ill-defined. No photorealism, oral contact,
teeth appearance or likeness approval is implied by the numerical tests.

The actual source of the pink/red material cannot be confidently assigned
to a specific Blender object from the composite image alone. Do not
speculate that hidden bone weights or an invalid MHCLO mapping caused
these visual defects. Do not attempt yet another unverified jaw translation
or return to the older height-only split.

## Next isolated diagnostic

`tools/run_mpfb_oral_isolation.py` runs **one** Head A Blender process
with the previously proven seam and jaw-open motion integration and
four 400x600 RGBA mouth-closeup renders at the same pose, framing and
lighting:

1. `jaw_full.png` — both teeth and tongue visible
2. `jaw_no_tongue.png` — teeth visible, tongue hidden
3. `jaw_no_teeth.png` — tongue visible, teeth hidden
4. `jaw_no_teeth_no_tongue.png` — neither oral asset visible

The toggles are only `hide_render` on the copied in-memory objects.
Original MPFB assets and previously produced GLBs stay untouched.
The rendering helper uses `try/finally` to restore visibility even on
an exception. The strict body and jaw-motion gate executes first. A
validated `anatomy_pose_report.json` records which asset was visible
in each view; the images and report are compressed as
`identity023_oral_isolation.zip` inside a fresh
`output/identity023_oral_isolation/<timestamp>/` folder.

The entire comparison is evidence for asset attribution, **not a fix**.
Inspect and classify which mesh creates each unnatural red/pink surface
and exposed grille. The next engineering change must be a targeted
anatomy/material/pose correction supported by those image contrasts.

## New tests and owner call

Run **only**:
`python -m unittest discover -s tests -p "test_mhclo_oral_asset_isolation.py" -v`

Then:
`python tools/run_mpfb_oral_isolation.py`

Share the ZIP for independent review, or full command output if it fails.
Do not rerun completed IDENTITY-018 through IDENTITY-022 jobs.
Do not run A/B 12-pose, merge to main, or edit user-installed MPFB assets.

State: draft stacked PR on top of IDENTITY-022. Windows tests and
new images **not yet executed**. IDENTITY-022 is **visual FAIL**.
