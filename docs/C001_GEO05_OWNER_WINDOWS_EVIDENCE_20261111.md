# C001-GEO-05 — Owner Windows Stage-0 + template evidence (2026-11-11)

**Provenance:** user-supplied PowerShell logs from `C:\PROJECT\Livynth` on Windows, on experimental branch after fast-forward to `9084a9d`. Not an independently reproduced Blender run or a claim that a recognizable identity exists.

## Commands executed and observed outcome

```powershell
python tools/local_check.py
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/stage0.glb --json output/c001_geo05/stage0.json
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/template_control.glb --json output/c001_geo05/template_control.json --stage1-template output/c001_geo05/stage1_constraints.json
```

- `tools/local_check.py`: 58 tests PASS (1 skipped); geometry suite 157 PASS (2 skipped); all requested local checks completed.
- Runtime: Blender 4.5.10 LTS, MPFB build 20261010.
- Raw mesh: 19,158 vertices, 18,486 quad polygons; after bake: **13,380 vertices / 13,378 quads**, UVMap present, 291 vertex groups.
- Rig: 163 joints; GLB has one character mesh and skin. Exported GLB: 5,765,824 bytes; 14,517 GLB positions because seams duplicate native vertices; 26,756 triangles; nonmanifold edges reported as zero in exported primitive.
- Facial controls: 67 target names exported. `eyeBlinkLeft` and `eyeBlinkRight` each move 718 measured vertices; `jawOpen` moves 2,249 measured vertices. All ten sampled required ARKit targets are present. Morph geometry metrics do not independently verify motion visually.
- Report: no step errors; 13 export assertions PASS. No baked animation clips (`animations: []`) are authored by this baseline.
- Warning: Blender's exporter drops joint influences beyond the top four, then renormalizes. **Post-export skin behavior is not yet independently qualified.**
- Special cases: `viseme_sil` and `tongueOut` each report zero measured vertex movement; silence can be neutral but tongueOut requires separate animation QA.

## Stage-1 template facts

The template run completed, including `stage1_template: ok`, with source fingerprint:

```text
64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542
```

The emitted template has `anchors: []`, unset `region.min_m/max_m/taper_m`, `reference_calibrated: false`, and `stage1: NOT_RUN`. Its 3D anatomical constraints **have not** been specified. Never substitute seam-split GLB vertices for the pre-morph Blender mesh.

**Status:** Stage-0 structural baseline PASS; Stage-1 fitting NOT RUN; independent visual identity Phase-3 **FAIL**. Full skin-weight coverage, global self-intersection, post-fit face morph function, five-view neutral likeness, and calibrated camera assumptions remain UNVERIFIED.

**Next:** opt-in `--stage1-neutral-dump` capture of original baked-neutral vertex positions and quads, source-hash check, inspect face landmark *candidates* before any 3D constraints are accepted. Keep all generated assets under ignored `output/`.
