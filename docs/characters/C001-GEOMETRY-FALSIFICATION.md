# C001 geometry falsification — texture-independent check

**Status (2026-11-11):** implemented and locally tested as a **necessary negative-control check**. This is **not** a completed Character 001 reconstruction, a verified identity score, or a substitute for the independent blinded multi-view gate. Phase 3 **remains FAIL**.

## Why this exists

The previous Phase-3 canary with a 1.18× widened face was not rejected by silhouette IoU and similarity-aligned 2D landmark distance. Texture projection hid geometry errors. This new check reads **only GLB mesh vertex positions and triangle indices**, never images, UVs, texture files, material colors or previous judgments. It uses rigid alignment only (rotation and translation), **never similarity-scale alignment**.

The canary deforms the selected face mesh 18% laterally over a broad cheek band. A no-change control and a second test that moves interior surface depth while **preserving front X/Y silhouette bounds** prevent the exact earlier failure from silently recurring. The report also measures fixed-height head cross-section widths normalized by the original head height.

## Local verification and commands

Install the existing optional geometry dependencies: `python -m pip install -r requirements-geometry.txt`.

```powershell
python -m unittest discover -s geo/tests -v
# Show mesh/node names first: a multi-mesh GLB must have an explicit selection
python -m geo.geometry_falsification --source .\assets\my_character.glb --list-meshes
# For the old V32 skinned body mesh, Y is up and the measured facial height is ~1.50–1.77m
python -m geo.geometry_falsification --source .\assets\my_character.glb --mesh GLTF_4 --axis y --head-range 1.50 1.77 --out .\output\geometry_falsification.json
# Add --candidate path\to\candidate.glb when a same-topology fitting variant exists
```

For **new Character 001 reconstruction candidates** use their actual mesh ID, coordinate system and measured head-region height. Do **not** blindly reuse the V32-specific `GLTF_4` or `1.50 1.77` values. If no candidate/base correspondence exists, run the candidate as `--source` to test whether the wrong-identity canary is detectable. Do not compare independently retopologized meshes vertex-by-vertex.

## Tested results

The new module's standalone suite passed **10/10** tests on the available Python/NumPy/Trimesh environment (not Blender). One test modifies **interior depth geometry while the frontal X/Y silhouette extrema remain identical**, and the geometry-only test still rejects it.

An actual archived avatar was used as the source and the archived C001-GEO-02 fitting GLB as the candidate, selecting `GLTF_4`, Y-up, range `1.50–1.77`:

| Observation | Value | Meaning |
| --- | ---: | --- |
| Source head-region vertices | 4,463 | Measured actual GLB subset |
| Known wrong-identity canary: p95 normalized deformation | 0.0555375 | Wrong canary detected |
| Known wrong-identity canary: max width delta / head height | 0.115298 | Detectable shape distortion |
| Existing C001-GEO-02 fitted candidate: p95 normalized change | 0.0098948 | Candidate differs from V32; **not** evidence of likeness |
| Existing C001-GEO-02 fitted candidate: width delta / head height | 0.007708 | Small width change; **not** an identity score |
| Canary falsification control | PASS | Known distorted geometry rejected |
| Character 001 likeness / anatomical correctness | **NOT EVALUATED** | Requires blind, untextured front/profile QA |

## Hard limitations

1. This tool requires **the same vertex/face correspondence** to compare two models. For new retopologized heads, use a separately implemented 3D surface-distance, normal/depth or camera-calibrated profile test plus independent human geometry review.
2. Camera orientation is not inferred from a photograph. Head-range and axis must be specified explicitly. A wrong mesh or whole-body range invalidates results.
3. Surface geometry can change while preserving 2D appearance, but detecting *change* does not tell us which geometry is correct. Neither the original model nor reference photographs are verified ground-truth 3D scans.
4. The tool does not detect all duplicate-layer/shell artifacts; a dedicated mesh connectivity and near-overlap audit is still required.
5. No claim is made about FLAME fitting, 3D likeness, eyelid animation, full 360° reconstructions or real-time render performance.

## Instructions to OpenCode

Use the new test to guard the approved **Candidate A repair**. Require a positive wrong-identity canary rejection and unchanged control before handing off to independent multiview geometry judges. Do not replace the clean blind gate with this diagnostic, do not read sealed judges' records when implementing, and do not change the thresholds to force an acceptance. Keep PR #1 draft and the old locally untracked agent reports intact.