# IDENTITY-012 — Correcting anatomy alignment after identity deformation

**Date:** 2026-11-12. **Result of independent IDENTITY-011 visual review: FAIL for anatomy alignment on Head B.**

## Verified Windows A/B evidence

Owner uploaded 20261112_071835_969382.zip (3,161,955 bytes; SHA256
`4678b71bf34d6846d58a8866bd5ff24b01918703c5ac5d9c4a34618aaa8686e8`).
All **16 manifest-listed files** matched their SHA256 digests. The ZIP contains
12 400×600 PNGs plus two per-character JSON reports, an A/B summary and gallery.
Both independent Blender 4.5.10 scenes finished successfully.

Both characters retain identical native source SHA256
`64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542`,
native quad-topology SHA, **13,380 native body vertices / 13,378 quads**,
**163 joints, 67 facial targets** and fitted eyes/teeth/tongue bound to the
copied armature. The two fitted head position SHAs differ as intended.

### Independent visual verdict

| Pose | Head A | Head B |
|---|---|---|
| Neutral eyes | Eyeballs seated plausibly | **FAIL: bulging, exposed eyeballs** |
| Full blink | Eyelids visibly close | **FAIL: exposed/misaligned eyeballs beneath lids** |
| Jaw open | Oral parts inside open mouth, refinement needed | **FAIL: reddish artifacts outside oral opening** |
| AA vowel | Visible oral surfaces | **FAIL: detached-looking red geometry near cheeks/nose** |
| PP closure | Relatively coherent | Eye mismatch persists |
| Three-quarter jaw | Face and mouth broadly attached | Severe eye and mouth alignment defects |

**Do not approve IDENTITY-011 for anatomy production.** The structural
body/rigger contract is good, but it is not evidence of correct fitted
anatomy for different head shapes. Specific identification of the red
artifact's object mesh still needs material/object-isolation rendering.

## Probable cause

Head-shape controls alter the *baked body* after the MHClO accessories
are fitted on an unmodified source human. The attached meshes retain
their original binding-space shape/placement; an Armature modifier alone
does not transfer the new facial identity offsets. Opposite A/B
cranial-width, cheek-fullness and jaw coefficients expose this mismatch.
Testing this hypothesis requires new rendered evidence.

## IDENTITY-012 fix experiment

The original `character/head_shape.displacement_field` can now evaluate
at accessory mesh points using a **fixed reference native body** for its
crown/height normalization. `character/anatomy_alignment.py` applies
this same identity field in body-local bind space to copies of MPFB
eyes, teeth and tongue, then converts coordinates back to each mesh's
original local space. Its topology, bone weights, vertex groups, and
Armature binding remain unchanged. The feature is **opt in**, not an
automatic production patch.

Windows command after merging development:

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python -m unittest tests.test_anatomy_alignment -v
    python tools/run_anatomy_ab_review.py --align-accessories

Outputs go to a NEW dated output/anatomy_ab_review directory and ZIP.
Upload the ZIP for same-pose A/B visual comparison to the failed archive.
Report distinguishes `shared_identity_field` alignment from original
`original_mpfb_fit`. It records each asset's alignment displacement and
checks source/body topology and rig unchanged.

## Still-unproven behavior

Changing bind-space accessory vertices may not perfectly fit eyeball
surface curvature. Both head variants must be reviewed, as fixing B
could worsen A. Eyes should stay spherical and eyelids close naturally.
**Mouth morph targets may not drive jaw bones**: even aligned teeth and
tongue could fail to follow jawOpen/visemes. If still incorrect, next
change is explicit jaw/asset retargeting and object-specific diagnostics,
not deleting tests or reducing identity variation until a picture looks
acceptable.

No photorealism or Character 001 five-view likeness is claimed.
Existing source GLBs remain untouched; main remains unchanged.
