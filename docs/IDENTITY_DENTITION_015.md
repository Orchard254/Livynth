# IDENTITY-015 — Anatomy-preserving dental assignments from native MPFB MHCLO

**Date:** 2026-11-12. **Status:** numerically tested and wired as opt-in; user Windows MPFB mapping and new renders NOT RUN.

## Evidence: IDENTITY-014 fixed oral movement but not credible teeth

Owner uploaded `20261112_083529_509207.zip`, SHA256
`24d83c24a34ea8b979088f0ca5cef4f5b0268e8a023ae8267c8d36de33def167`.
All **16/16** SHA256 manifest-listed files verified; ZIP contains 12 matched
pose images plus JSON reports and static gallery.

Identity-014 actual world-space motion results:

| Identity / pose | Teeth moved | Tongue moved | Max teeth shift |
|---|---:|---:|---:|
| Head A jawOpen | 2,201 | 226 | 17.762 mm |
| Head A viseme_aa | 2,187 | 226 | 8.827 mm |
| Head B jawOpen | 2,235 | 226 | 17.818 mm |
| Head B viseme_aa | 2,214 | 226 | 9.284 mm |

Both body/armature contracts remain intact: 13,380 native body vertices,
13,378 quads, 163 joints and 67 original facial target names. **PASS:**
oral meshes move for jawOpen and AA, reversing IDENTITY-013's four 0mm
failures. **FAIL:** open-mouth visual review shows a dense grey/white
grille-like dental block, with overly exposed red/pink oral tissue.
The existing height-based mask uses smoothed Z position on each tooth
vertex; this can deform or partially stretch the tooth/gum surfaces.
Do not accept natural speech animation or photoreal appearance from this.

## More grounded approach: original MakeHuman anatomy helper assignments

The official HM08 base mesh uses exactly 19,158 unbaked vertices,
including named helper regions `helper-lower-teeth` [14992..15059]
and `helper-upper-teeth` [15060..15127] (inclusive).
The MHCLO descriptor for a fitted accessory contains per-asset-vertex
source reference indices and barycentric weights. Together these can
distinguish actual upper/lower jaw assignments without looking at
their finished 3D Z coordinates.

References:
- https://static.makehumancommunity.org/about/concepts/basemesh.html
- https://github.com/makehumancommunity/mpfb2/blob/master/src/mpfb/data/mesh_metadata/hm08_config.json
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/entities/clothes/mhclo.md

## New isolated implementation

1. `character/mhclo_dentition.py`: classifies each installed teeth_base
   vertex using its MHCLO original HM08 helper references. Requires
   virtually all barycentric weight to map to *exactly one* jaw, at
   least 10% of vertices in each jaw, and **zero mesh polygons** joining
   upper to lower classes. Rejects unknown/nonfinite/ambiguous mappings.
2. `character/oral_correctives.py`: accepts a strict binary dental mask;
   moves whole lower-jaw dental vertices by the same corrective motion
   while leaving **every upper-jaw tooth vertex fixed**. Does not use
   the previous continuous height-based mask when this mode is selected.
   No tooth-polygon face can stretch between fixed and moving jaws.
3. `tools/mpfb_anatomy_ab_blender.py`: on opt-in, checks that the source
   human has the 19,158 native vertices and that the copied teeth retain
   the exact original vertex order. Loads the existing verified/pinned
   installed `teeth_base.mhclo` through MPFB's Mhclo API, validates the
   mapping, then builds corrective keys on the copied teeth/tongue only.
4. `tools/run_anatomy_ab_review.py`: adds `--mhclo-dentition`, requiring
   all previous `--align-accessories --audit-oral-motion --oral-correctives`
   gates; requires both heads have identical mask SHA and reports exact
   upper/lower dental vertex counts plus 12 matched PNG poses.

**Preservation:** Existing A/B exported GLBs, original 163-joint rig,
67 face/body morphs, source reference photos and main branch remain
untouched. The original height-split mode stays available without the
new flag to reproduce the visually rejected earlier experiment.

## Validation and next command

**10 focused numerical/negative tests PASS locally.** Four additional
repository-level tests for mask validation and opt-in were authored;
owner full Windows tests and the real teeth_base MHCLO mapping are
**UNVERIFIED** until the next run. If the installed asset references
helper IDs differently, or its faces connect the upper and lower jaw
components, the code deliberately FAILS without generating a false pass.

From the development branch on Windows:

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python -m unittest discover -s tests -p "test_mhclo_dentition.py" -v
    python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion --oral-correctives --mhclo-dentition

The tool creates a new ZIP under `output/anatomy_ab_review`. Review it
against the IDENTITY-014 failed dental images for **both** heads. The
numerical status is not a dental-contact or photorealism certificate.
Further improvements may need separate upper/lower gum materials, jaw
rotation/pivot rather than pure translation, and tongue articulation.
Character 001 photo-to-3D five-view likeness gate remains FAIL.
