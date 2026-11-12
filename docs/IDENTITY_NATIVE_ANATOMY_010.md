# IDENTITY-010 — Native fitted eyes / teeth / tongue experiment

**Status: inventory accepted; candidate fitting code implemented; actual Blender attachment and render NOT RUN.**
Date: 2026-11-12.

## Real owner's Windows MPFB inventory

Owner uploaded `mpfb_asset_inventory.json` from Blender 4.5.10 LTS.
`ASSETS_AVAILABLE_FOR_FITTING_TESTS`, `system_assets_pack_installed=true`,
`missing_required_for_anatomy=[]`. Total **78 assets**:
eyes 2, teeth 6, tongue 1, eyebrows 12, eyelashes 4,
hair 10, clothes 20 and skin material presets 23.

The inventory says assets exist; it is **not** an attachment, exported
skin-rig or visual realism certificate.

Selected pinning in `character/appearance/native_anatomy_demo.json`:
- eyes: `high-poly/high-poly.mhclo`; SHA256 `b183cfe37120ab726f9b3f2ea6cd3a64c44ce7b4bd91a77c841cf70c04f83a0d`
- teeth: `teeth_base/teeth_base.mhclo`; SHA256 `9edc3deff3bb97a95c791878064dd069a74a38f95ea6d9707a9ba68d888b3b5c`
- tongue: `tongue01/tongue01.mhclo`; SHA256 `61d825899cd78ff3146fa1324118060cb44b095fae1427d408c199ade74e3c9e`

These are owner-machine source file fingerprints, **not a license to
redistribute the asset binaries**. The licensed terms of asset sources
remain to be verified before any commercial release.

## Engineering lane

To preserve the proven 163-bone / 67-target two-character export, this
test does not change `tools/mpfb_headless_probe.py` or the existing GLBs.

1. `character/native_anatomy.py` strictly validates the data-driven
   selection and confirms that the actual files resolved by MPFB's
   `AssetService.find_asset_absolute_path` match the inventoried hashes.
   Invalid/missing files abort before modifying the Blender scene.
2. `tools/mpfb_native_anatomy_probe_blender.py` creates a fresh disposable
   MPFB human using demo Head A's **broad macro settings only**, adds the
   known built-in rig, and invokes the official
   `HumanService.add_mhclo_asset` for high-poly eyes with
   `PROCEDURAL_EYES` material and for the teeth/tongue with
   `MAKESKIN`. The probe records each real mesh, materials,
   armature binding, parent and vertex groups.
3. Render two 480x720 diagnostic neutral PNGs, front and three-quarter,
   and save `anatomy_probe.json`. The Windows wrapper validates all
   three objects and the saved PNG payloads with the same PNG QA used
   in prior pose review.
4. No GLB export or animation occurs, and **the detailed six-coefficient
   head deformation is not yet applied**. A successful probe means the
   native assets fit an MPFB human in the owner's installation, **not**
   that they stay aligned with two detailed face variants, close eyes,
   move with jawOpen, or look photorealistic.

## Windows run: one command, no GLB rebuild

```powershell
cd C:\PROJECT\Livynth
git pull --ff-only
python -m unittest tests.test_native_anatomy -v
python tools/run_native_anatomy_probe.py
```

A fresh `output/anatomy_probe/<timestamp>/` directory will contain
`anatomy_probe.json`, `neutral_front.png` and
`neutral_three_quarter.png`. A failed Blender run leaves partial
files/log evidence and will not claim success.

Review the images before advancing. The eyes must have recognizable
eyeball surfaces and plausible placement; teeth and tongue must be
present in the scene, although neutral closed lips may occlude them.

## Next acceptance after this passes

- Integrate fitted objects into a **new opt-in identity exporter mode**
  while preserving the original neutral mesh, its 163-joint skin and
  67 target names; update the GLB auditor to distinguish the single
  *character body* mesh from legitimately attached anatomical meshes.
- Prove the native assets follow **both** demo Head A/B deformations
  rather than fitting only the unchanged broad-macro neutral human.
- Render matched neutral/blink/jawOpen/AA/PP for A/B, including oral
  visibility and collision checks. Reject any eye or tooth motion not
  bound to the correct rig.
- Independent five-view Character 001 photo likeness remains
  **Phase-3 FAIL** and is not superseded by improved materials.

## Official API references

- https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/humanservice.md
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/assetservice.md
