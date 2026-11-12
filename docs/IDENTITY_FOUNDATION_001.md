# IDENTITY-001 — Reusable 3D human foundation

**Status: IMPLEMENTED + 15 standard-library local tests PASS; owner Windows Blender A/B run NOT YET RUN.**

## Purpose

One MPFB base topology and one rig/morph system should generate **different manually configured humans**, without reimplementing animation. This is the control interface that a future image-to-identity solver can drive.

**It is not yet photo reconstruction.** `source` currently accepts only `manual_parameters`. Independently AI-generated reference photographs have uncertain camera geometry and inconsistent facial measurements. We must later estimate a jointly-consistent parameter set from multi-view evidence, preserve uncertainty, and pass the blind geometry/identity gate. No photo-derived likeness is claimed here.

## Architecture

1. `character/identity_recipe.py`: strict JSON recipe schema `livynth.identity.recipe.v1`, finite [0,1] MPFB macro bounds, normalized MPFB `race` dictionary (API names, not inferred traits), stable SHA256 and no mutation of MPFB defaults.
2. `tools/mpfb_headless_probe.py --identity-recipe path.json`: apply per-character MPFB macro parameters during `HumanService.create_human()`, **before rig export copy / baking / ARKit**. Existing no-flag Character 001 test baseline stays unchanged.
3. Bake and record native neutral position SHA256 in `neutral_identity_geometry` prior to loading 67 expression targets. Do not confuse seam-split GLB vertex indices with Blender native indices.
4. Export one GLB per character, preserving the 163-joint + 67-target contract if Blender actually succeeds. JSON audit includes recipe identity and source SHA.
5. `tools/identity_compare.py`: fail if geometry is identical, native vertex count changes, either GLB lacks skin/163 joints/67 morphs, recipe fingerprint is the same, or exports failed. A PASS is **shape difference + structural compatibility only**, not likeness or expression quality.
6. `tests/test_identity_recipe.py`: strict validation + positive/negative structural controls.

## Windows acceptance commands

From the repo checkout on the **development branch** (after merge):

```powershell
cd C:\PROJECT\Livynth
git pull --ff-only
python -m unittest tests.test_identity_recipe -v
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

& $blender --background --python tools/mpfb_headless_probe.py -- --identity-recipe character/recipes/demo_a.json --out output/identity/demo_a.glb --json output/identity/demo_a.json
if ($LASTEXITCODE -ne 0) { throw "Character A GLB build failed" }
& $blender --background --python tools/mpfb_headless_probe.py -- --identity-recipe character/recipes/demo_b.json --out output/identity/demo_b.glb --json output/identity/demo_b.json
if ($LASTEXITCODE -ne 0) { throw "Character B GLB build failed" }

python tools/identity_compare.py --a output/identity/demo_a.json --b output/identity/demo_b.json --out output/identity/identity_comparison.json
if ($LASTEXITCODE -ne 0) { throw "Character identity A/B gate failed" }
```

Do not run full 1080x1920 video exports at this stage. The test produces GLBs and small JSONs only; outputs are gitignored.

To review appearance and animation later, render two cheap portrait stills with the same `video/build_video.py` renderer and a **single common voice WAV**, then inspect neutral/blink/jaw. Structural morph count is not proof that the controls look correct on both identities.

## Explicit quality gates

| Gate | Current status |
|---|---|
| Two valid manual recipes / different parameter hashes | PASS — pure Python |
| Two actual different baked native meshes | NOT RUN — Windows Blender |
| Same native topology / 163 joints / 67 facial targets | NOT RUN — Windows Blender |
| Both identities blink/jaw/mouth correctly | NOT RUN |
| Independent recognition from each image set, 5 views, wrong-identity controls rejected | NOT IMPLEMENTED |
| Character 001 original likeness | FAIL (unchanged) |
| Hair, eyes, realistic skin and wardrobe | INCOMPLETE |

## Next identity step after successful A/B

Build a **reference-image-to-parameter adapter** that first audits provenance/view consistency, then estimates camera pose and anatomical landmarks, optimizes continuous parameters against multiple held-out views, and emits a provisional, uncertainty-tagged recipe. MPFB macro parameters alone are too low-dimensional to reproduce a specific face: later detailed nose, eye, jaw and forehead shape coefficients or a properly licensed parametric head will be needed. Such controls must be measured and validated rather than invented from images.

**Licensing:** This prototype uses the already verified MPFB base and avoids adding third-party model weights. The repository's FLAME 2023 Open research documents unresolved commercial licensing caveats; no FLAME material is downloaded or shipped by IDENTITY-001.

**Do not merge Character 001 likeness PR #2 to `main` just because the identity-template infrastructure works.** This is a dev-foundation milestone.
