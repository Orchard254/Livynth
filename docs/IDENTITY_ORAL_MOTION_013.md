# IDENTITY-012 verified, IDENTITY-013 oral motion diagnostic

**Date:** 2026-11-12. **Owner evidence:** `20261112_074842_628509.zip`
(SHA256 `68a86213bc91efaa81726760fa5df2d788548c36741375b0e327ceb5d91e8e0b`).
Baseline failed anatomy archive: `20261112_071835_969382.zip`.

## Independent new ZIP verification

All **16 manifest entries** match their SHA256 bytes in the ZIP. Both
Blender 4.5.10 scenes generated the required **12 images** and per-character
JSON reports, with `anatomy_alignment_mode=shared_identity_field`.
No new images were byte-identical to the old failure archive.

The two heads retain the same original neutral positions SHA
`64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542`
and native quad connectivity SHA
`2ed8e59ff91b3382f114a8a2a380b66a9ced585d606f7b13e3f1e69b792bdc1b`.
Each has 13,380 native body vertices, 13,378 quads, 163 bones and
67 identical named face targets. The two baked head-position SHAs remain
different. Eyes (1,064 vertices), teeth (3,868) and tongue (226) remain
bound to the copied armature without changed vertex counts.

## A/B before-and-after visual verdict

| Region | Before IDENTITY-012 | After IDENTITY-012 |
|---|---|---|
| Head A eyes | Properly seated | Still seated; no significant regression |
| Head A full blink | Fully closed | Remains fully closed |
| Head B neutral eyes | Both eyeballs bulge outside socket | **Corrected: globes seated under lids** |
| Head B full blink | Eyeballs exposed below eyelids | **Corrected: eyelids cover eyes** |
| Head B jawOpen/AA | Red fragments protrude beside nose/lips | **Corrected: detached outer fragments absent** |
| Mouth interior | Rough teeth/tongue presentation | Remains visibly artificial and needs corrective oral animation |

**Acceptance:** IDENTITY-012 static appearance alignment PASS on the two
tested shapes. This does NOT pass natural eye animation, dynamic jaw
motion, tongue contact, global collisions or realistic presentation.
Original Character 001 five-view photographic likeness remains FAIL.

## Actual measured accessory identity warp

| Copied accessory | Head A mean/max displacement | Head B mean/max displacement |
|---|---:|---:|
| Eyes | 4.18 / 5.82 mm | 5.22 / 7.28 mm |
| Teeth | 5.18 / 7.78 mm | 6.47 / 9.73 mm |
| Tongue | 3.66 / 5.45 mm | 4.58 / 6.81 mm |

Every accessory retained its vertex count and was read back from Blender.
Maximum recorded coordinate-storage error was 0.00006 mm, well below
the alignment gate. These are *identity fitting offsets* (static);
they do not measure jawOpening animation or prove correct occlusion.

## IDENTITY-013: next decisive numerical test

The existing pose rendering logic currently changes shape-key values on
the **face/body mesh**. Teeth and tongue are distinct MPFB objects bound
to an armature. An Armature modifier on the assets does not guarantee
they follow morph-only body jaw movement. This is a risk that cannot
be resolved by visual stills alone.

New `character/anatomy_motion_audit.py` measures actual evaluated
world-space positions of body, teeth and tongue for neutral, jawOpen
and viseme_aa. `tools/mpfb_anatomy_ab_blender.py` offers opt-in
`--audit-oral-motion` to snapshot the evaluated depsgraph. Its report
distinguishes body morph failure, static oral assets, partial movement
and motion signal that still requires visual review. New hermetic
tests cover both good and bad controls, invalid arrays, nonfinite
vertices and runner flag/contract. The older mode remains unchanged.

### Windows command (no changes to existing GLBs)

    cd C:\PROJECT\Livynth
    git pull --ff-only
    python -m unittest discover -s tests -p "test_anatomy_motion_audit.py" -v
    python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion

A fresh date-stamped output folder and ZIP includes the ordinary twelve
anatomy stills plus JSON motion measurements. A report of
`FAIL_ORAL_ASSETS_STATIC_WHILE_BODY_MORPHS` must trigger jaw-coupling
work, NOT be ignored. The diagnostic ZIP still packages failure evidence.

**Known limits:** this tests movement, not whether lower teeth, tongue
and lips meet naturally. Dynamic jaw/bone retargeting should be
designed only after the evaluated-motion report confirms the mismatch.
Head A/B GLBs and repo main remain untouched. The full project goal
(recognizable photo-to-3D and polished animatable humans) remains open.
