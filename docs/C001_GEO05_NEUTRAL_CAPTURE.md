# C001-GEO-05 — capture the exact baked neutral mesh (geometry-only)

After the Stage-1 template PASS, preserve its source SHA and extract the **Blender-side** rest vertices. The GLB cannot supply valid MPFB vertex indices because the exporter splits positions at UV/attribute seams (13,380 native vertices -> 14,517 exported positions in the Stage-0 report).

The `--stage1-neutral-dump` opt-in exports a compact, compressed `.npz` file with `vertices` (float64, N×3), `quads` (int32, F×4), and `metadata_utf8` (UTF-8 JSON byte array). It records the source hash and axis-aligned bounds without deforming the mesh or making any identity claims.

From the existing experimental branch on Windows, with Blender 4.5 + MPFB:

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
& $blender --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo05/neutral_dump_control.glb --json output/c001_geo05/neutral_dump_report.json --stage1-neutral-dump output/c001_geo05/neutral_mesh.npz
if ($LASTEXITCODE -ne 0) { throw 'Neutral mesh capture failed' }
Get-Content output\c001_geo05\neutral_dump_report.json | Select-String 'neutral_dump|positions_sha256|vertex_count|quad_face_count'
```

**Expected source SHA:** `64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542`. If it differs, **stop** and investigate drift before choosing anchors.

Upload only `output/c001_geo05/neutral_mesh.npz` and the concise `neutral_dump_report.json` in ChatGPT. Do **not** commit the `.npz` to Git or upload identity portraits to a third-party service. The archive contains only vertices, quad indices and metadata.

**Next:** inspect geometry, establish face/head coordinate bounds and visualized landmark candidate indices; combine with independently reviewed multi-angle correspondence and camera assumptions. Do not populate the fitting constraint template just from nearest 3D mesh vertices or one 2D photo. No fitted likeness candidate exists yet. Phase-3 remains FAIL.
