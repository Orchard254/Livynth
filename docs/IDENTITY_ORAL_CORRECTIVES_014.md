# IDENTITY-013 evidence and IDENTITY-014 source-driven oral correction

Date: 2026-11-12.
Source: owner-uploaded `20261112_081501_619229.zip`, SHA256
`3d5da86c4b927f71f06c29b80f877359ab8556948848498b595861e58c765aad`.
All **16/16** source manifest entries verified byte-for-byte (SHA256).
The ZIP contains 12 matching Blender pose images, two per-character
report JSONs, A/B summary, gallery, manifest. No data were invented.

## Verified root cause — four identical oral-motion failures

| Identity | Body jawOpen max | Body AA max | Teeth movement | Tongue movement |
|---|---:|---:|---:|---:|
| demo_head_a | 32.927631 mm | 16.340069 mm | 0.0 mm | 0.0 mm |
| demo_head_b | 32.927631 mm | 16.340069 mm | 0.0 mm | 0.0 mm |

Body jawOpen moved **2,121 vertices**, AA moved **1,967 vertices**.
Both cases on BOTH identities returned
`FAIL_ORAL_ASSETS_STATIC_WHILE_BODY_MORPHS`. The measurements are from
evaluated Blender dependency-graph mesh *world positions*, so they
account for modifiers and rigging. This is stronger evidence than
the existence of a jaw bone or an attached Armature modifier.

## Root-cause distinction

IDENTITY-012 fixed **static** anatomical fitting of eyes, teeth and
tongue when facial geometry changes, but the face opens via BODY
morph keys. No animation mapping currently drives separate teeth/tongue
geometry when jawOpen and viseme_aa change. Morph channel names on
the 67-key body do not automatically propagate to other meshes.

## Experimental fix — IDENTITY-014

Adds a new optional `--oral-correctives` mode to the existing
`tools/run_anatomy_ab_review.py`. Existing GLB exports and normal
studio behavior remain untouched.

Algorithm: sample the lower anterior mouth **body shape-key delta**
for the existing jawOpen and AA morphs, derive a robust bounded
median translation. Fit new, separately keyed `jawOpen` and
`viseme_aa` corrective morphs to the copied MPFB teeth/tongue.
The tongue moves as a rigid translated mesh, preserving its surface.
For a combined upper/lower tooth mesh, a smoothed height segmentation
moves mainly the lower dental region while leaving the upper teeth
mostly neutral. This is an approximation, not verified jaw rotation
or individual-tooth anatomical segmentation. It may fail visual QA.

The same pose weights are explicitly applied to BODY and oral
accessory shape keys. The original 163-joint skeleton, body's
67 facial targets, material assets and detailed facial identity
controls are not modified. Newly generated accessory keys do NOT
yet constitute an exported or production-safe GLB animation contract.

### Strict acceptance

- Only enabled with `--align-accessories --audit-oral-motion`.
- Require 12 existing matched A/B static PNGs and independent
  jaw/AA world-coordinate motion reports on both identities.
- Fail if body morph missing, sampled lower-mouth motion absent,
  translation unreasonably large or upward, or teeth cannot be
  reasonably split into lower and upper regions.
- Oral metric status must show movement for teeth AND tongue in
  both jawOpen and AA, but numerical movement is **not** final QA.
- Human review must confirm upper teeth remain near upper jaw,
  lower teeth/tongue fit the opening, no collision/tearing,
  and previously accepted Head A/B eye alignment remains sound.

## Run only on the owner's Windows Blender workstation

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python -m unittest discover -s tests -p "test_oral_correctives.py" -v
    python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion --oral-correctives

The wrapper will create a new timestamped output folder and portable
ZIP with the twelve poses and numeric movement audit. If Blender
fails, preserve the exact console log and partial folder; do not
repeatedly rerun or bypass the gate.

## Evidence limitations

Original Character 001 five-view photographic likeness Phase-3
remains FAIL. Actual Blender IDENTITY-014 corrective render,
temporal lip-sync, eye/hair/skin realism and GLB export with
accessory morph animation are **NOT TESTED**.

Blender shape keys and glTF morph exports are documented by:
https://docs.blender.org/api/current/bpy.types.Object.html
https://github.com/KhronosGroup/glTF-Blender-IO/blob/main/docs/blender_docs/scene_gltf2.rst
