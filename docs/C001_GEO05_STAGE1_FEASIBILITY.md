# LIVYNTH C001-GEO-05 — bounded Stage-1 neutral fit (experimental)

**2026-11-11. Phase-3: FAIL, unchanged.** The C001-GEO-04 r4 gate rejected both visual-hull candidates. This branch develops a geometry-first, topology-preserving MPFB alternative. No recognisable Character 001 candidate has been produced by this commit.

## Why this is the next experiment

- The previous photo-on-shell reconstruction lacks eye sockets, nose, mouth and jaw geometry. More projection/texture repair cannot supply that anatomy.
- The verified MPFB Stage-0 baseline has a quad body, UVs, 163 rig joints, 67 facial targets and functional blink/jaw motion. Preserve that neutral topology.
- The **Blender-side, baked-neutral mesh** is the only safe Stage-1 insertion point in this prototype. MPFB target loading follows the fit; do not fit the glTF export's seam-split vertices and assume MPFB vertex indices still match.
- The 15 AI-generated reference views are not calibrated photographs of a real scan. Image landmarks are **2D**, not measured 3D anatomical targets. A manually reviewed 3D anchor/camera model is a prerequisite, not an output of these tools.

## Code in this experiment branch

- `geo/stage1_fit.py`: pure-NumPy guarded local deformation field (symmetric x-axis RBF, explicit fit zone, anchor pins, bounded displacement, source-mesh fingerprint and local face-flip checks).
- `tools/stage1_blender_bridge.py`: reads the baked MPFB mesh and writes an **incomplete template** or applies a validated fit. Refuses an already morph-loaded mesh.
- `tools/mpfb_headless_probe.py`: adds two **optional flags**; without either flag the previous Stage-0 path is left untouched. It stops before GLB export if the Stage-1 request fails.
- `geo/tests_stage1/test_stage1_fit.py`: synthetic negative and control cases.

### Command A — retain the verified baseline

From the Windows checkout with the MPFB Blender extension installed (do **not** use `--factory-startup`):

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
& $blender --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/stage0.glb --json output/c001_geo05/stage0.json
```

### Command B — fingerprint the neutral mesh and generate an incomplete template

```powershell
& $blender --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/template_control.glb --json output/c001_geo05/template_control.json --stage1-template output/c001_geo05/stage1_constraints.json
```

The template intentionally contains `anchors: []` and `null` bounds and **will not execute as a fit**. Inspect actual basemesh coordinates, determine the face/head Z bounds in metres, manually pin anatomical vertices, and specify justified `target_m` coordinates based on reviewed multi-angle camera assumptions. Preserve the emitted source hash and vertex count. Each anchor has `vertex_index`, `name`, `target_m:[x,y,z]`, and `basis:"MANUAL_3D_ESTIMATE"`.

**Do not guess 3D anchor targets from one 2D photograph.** Use the approved five-view evidence and record fitted-camera uncertainty. Reserve independently generated profiles/45-degree views for hold-out visual assessment. The numerical prototype is not a triangulator or camera solver.

### Command C — attempt a fit (only after anchors are reviewed)

```powershell
& $blender --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/stage1_candidate.glb --json output/c001_geo05/stage1_report.json --stage1-constraints output/c001_geo05/stage1_constraints.json
```

If source fingerprints change, anchors exceed the displacement bound, the fit is ill-conditioned, target residuals remain, or quads fold, the opt-in branch rejects the fit **before exporting a candidate**. The baseline can still be built without flags.

### Python checks

```powershell
python -m unittest discover -s geo/tests_stage1 -v
python -m unittest discover -s geo -t . -p 'test_*.py'
python tools/local_check.py
```

## Required post-fit evidence before progress can be claimed

1. Stage-0/Stage-1 mesh inventory: same quad count before export, exact UV and skin group memberships, unchanged joint set.
2. GLB deep audit: 67 facial targets, all required ARKit labels, 163 joints, 100% weight coverage, working eyelids and jaw on the **fitted** export. Verify moved vertex regions, not just counts.
3. Independent self-intersection checker (not provided here). `_face_safety` only detects local quad collapse and orientation reversals, not global intersections. Until the independent check runs, **self-intersection is UNVERIFIED**.
4. Five-view neutral clay and legible wireframe/depth/normal review with the C001-GEO-04 blind gate. All wrong-identity canaries must be rejected. A clean gate still does not prove likeness; blinded human judges must accept facial anatomy and 90-degree profiles.
5. If profiles remain REGENERATE, stop the attempt and reassess correspondence/camera/parametric priors. Do not try to rescue the geometry using texture.

**Known limitations:** the package does not create the reviewed 3D anchors, does not run Blender in the authoring environment, does not guarantee MPFB API/morph behavior on the owner's machine, and does not implement camera calibration, global collision checks or the final character factory. All are UNVERIFIED.

**Git discipline:** experimental branch from feature PR #1's head `89081fc`. Do not merge into `main` or mark the Phase-3 gate green on the strength of synthetic tests. Keep GLBs/reference images under ignored `output/` and `assets/`; never commit those generated binaries.
