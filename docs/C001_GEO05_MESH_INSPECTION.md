# C001-GEO-05 — inspect the Blender-side neutral mesh offline

**Status:** Owner Windows capture PASS (2026-11-11), 13,380 Blender-native vertices / 13,378 quad faces, fingerprint **64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542**. No Stage-1 identity fit has run. Phase-3 identity remains FAIL.

**Purpose:** The NPZ archive contains actual Blender-side topology and native vertex IDs, unlike the seam-split GLB. Inspect it locally and do not invent 3D landmarks from the logs.

## Windows command (no hosted Actions, Blender or CUDA required here)

From C:\PROJECT\Livynth on the experiment branch, after git pull --ff-only:

~~~powershell
python -m unittest discover -s geo/tests_stage1 -p 'test_mesh_inspect.py' -v
python tools/stage1_mesh_inspect.py output/c001_geo05/neutral_mesh.npz --out output/c001_geo05/neutral_inspection --expect-sha 64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542
if ($LASTEXITCODE -ne 0) { throw 'Native mesh inspection blocked' }
Start-Process output/c001_geo05/neutral_inspection.html
~~~

The inspector generates:

- **neutral_inspection.json:** archive SHA, vertex/face counts, full-body topology components, boundaries, nonmanifold edges and a height-based diagnostic crop, with unknown identities clearly marked.
- **neutral_inspection.html:** four camera-axis orthographic views of the upper-Z crop, without external scripts/services. Click a point to collect candidate Blender vertex IDs and mesh-local coordinates. The views are labelled +Y, -Y, +X, -X, not guaranteed anatomical front/back. No camera or portrait relationship has been established.

The crop defaults to the top 35 cm, configurable with --head-height-m. It is a starting viewport, **not a validated head mask**. Bounds in the owner capture: X [-0.567862, 0.567862], Y [-0.377317, 0.097678], Z [0, 1.747290] metres.

Do not treat selected vertices as fitted identity landmarks. An anatomical front convention must be established visually, and 2D photo landmarks must be reconciled using reviewed camera assumptions and independent multi-view evidence before the 3D target_m values are entered.

## Next experiment requirements

1. Verify the JSON's source fingerprint, face/vertex counts, boundary edges, nonmanifold edges and components. If unexpected topology appears, stop and investigate.
2. Review four orthographic panels to determine anatomical forward, nose/eye/mouth/chin regions and native index candidates. Keep the first pass sparse (10–20 locations), label uncertainty and preserve neutral geometry.
3. **Upload neutral_mesh.npz and neutral_inspection.json directly to ChatGPT**, not to any third-party image-processing service. Log text alone cannot provide vertex coordinates.
4. Review data and candidate region map before attempting actual fit. Use 5-view identity references only with explicit camera assumptions and independently held-out geometry assessment. Do not pretend the images are a depth scan.

**Known limitations:** Inspector checks adjacency/topology but not global self-intersections, rig response, resemblance, calibrated projection or visibility-correct vertex picking. Its HTML uses painter's-order approximate clay shading; candidates clicked near overlapping surfaces require independent 3D checking. Stage-0 export's >4-joint-weight truncation and zero-motion tongueOut remain unqualified. Generated archives and HTML/JSON remain under ignored output/ and must not be committed.
