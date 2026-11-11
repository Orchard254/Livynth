# C001-GEO-03 Lane B — visual hull — experimental record (2026-11-11)

**Status:** implemented, unit-tested, render-verified visually. NOT a validated likeness,
NOT animation-ready, NOT photoreal. The Phase-3 blind gate **rejected** this candidate
(see `docs/C001_GEO03_EXPERIMENT_LOG.md`): the front reads as Character 001's appearance
but only because the reference photograph is projected onto a carved shell, and both
90-degree profiles are torn ghost geometry. Retained as the generator of candidate A1
and as the basis of the bounded A2 repair experiment (ADR-C001-004 decision 2).

**Scope:** isolated worktree `livynth-c001-geo03-visual-hull` (detached at 31a9b19).
Main repo `C:\PROJECT\Livynth` read-only (images read from it; nothing written).
Code landed on the feature branch at `geo/visual_hull.py`; the worktree copy is retained.

**Co-editing disclosure:** during this session, `geo/visual_hull.py` lineage was edited by
a second process in this worktree (the position-weld GLB export in `export_glb` +
a `render_v7_calibrated` probe campaign + `character001_visual_hull_v7` output dirs,
timestamps 8:34–8:39). My 8:36 edit (front/back texture-assignment bias) was retained by
that process. The shipped GLB therefore reflects a co-written `export_glb` I verified
empirically (see below), not only my code. `geo/calibrate_sweep.py` is mine. Nothing of
mine was deleted by that process; `render_v7_calibrated/` and `character001_visual_hull_v7/`
are left untouched. My other contributions: `tools/render_hull.py`, `geo/tests_hull/`,
segmentation/calibration/carving/texture-bias code in `geo/visual_hull.py`.

**Hypothesis.** Multi-view visual hull from the approved 7 silhouette views (front, ±45°,
±90°, back, top) reproduces Character 001's head volume well enough to serve as the
deterministic candidate for C001 reconstruction, with photo texture projected onto
hemispheres — recovering silhouette-limited geometry only (no eyes/lips/sockets).

**Environment (measured).** Windows; Python 3.14.7; numpy 2.5.3; scipy 1.18.1; Pillow 12.3.0;
trimesh 5.2.0; scikit-image 0.26.0 (installed this session); fast-simplification 0.2.0
(installed this session); imageio 2.38.1, lazy-loader 0.2.x, tifffile 2026.11.8 (installed
this session as sckikit-image deps); Blender 4.5 EEVEE Next headless for renders (binary at
C:\Program Files\Blender Foundation\Blender 4.5\blender.exe; only for local renders, no upload).
`open3d` NOT installed (skimage marching_cubes used instead). `pyvista` NOT installed →
`fast_simplification.simplify_mesh` unusable → **decimation skipped**, kept 52,822 faces
(fine for a candidate). No CUDA/torch used.

**Commands.**
```
pip install scikit-image fast-simplification
python -m geo.visual_hull --images C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1 \
  --out output/character001_visual_hull --views front,left45,right45,left90,right90,back,top \
  --calib output/calib_sweep/fitted_calib.json --dilate45 12 --cell 0.0033 --smooth 4
python -m geo.calibrate_sweep --images <dir> --out output/calib_sweep --views left45,right45,back,top --rounds 2
python -m unittest discover -s geo/tests_hull -v        # 9 tests, all PASS
python tools/local_check.py                             # 21 tests PASS (unchanged baseline)
blender --background --python tools/render_hull.py -- --glb output/lane_b_snapshot/character001_visual_hull.glb --out output/lane_b_snapshot/renders
```

**Inputs & provenance.** The 7 identity_capture_v1 PNGs used for carving (hashes in
`output/character001_visual_hull/visual_hull_report.json` → `provenance`). Front/profile
crown/chin anchors reused from `geo/proxy_fit.py` VIEWS (same image set & pixel dims, verified
1086×1448; 07_top_head is 1087×1447). Scale prior HEAD_HEIGHT_M=0.245 m (illustrative, as
GEO-01). Head-center at world y=0; extents ~0.193 × 0.300 × 0.236 m (hair-to-hair incl. neck stub).

**Segmentation.** Warm-hue dominance: `(R−B) > 15` keeps skin+auburn hair; gray backdrop
(R≈B) rejected; navy shirt (R<B) rejected; near-neutral specular skin rescued by
distance-from-border test; holes filled; CCs ≥ 400 px kept (hair wisps). Verified visually
on all 7 views (`output/seg_check/seg_*.png`); shirt excluded everywhere; counts: front
600,756 fg px … top 794,839.

**Calibration (weak-perspective, orthographic).** World: subject neutral pose (nose +z,
anatomical-left +x), camera fixed at +z; each photo = head yawed by ψ. u = cx + s(cosψ·x +
sinψ·z), v = cy − s·y. Front scale 3547 px/m (869 px crown→chin, anchors 55/924); profile
views use annotated scales (04: 3837 px/m, 40→980; 05: 3698 px/m, 34→940) — profiles are
framed tighter (~8%) — all other views use front scale. cx = w/2 everywhere (framing centered
to ±1.5%). Back view **fitted** (s=3760, cx=558, cy=483.5; point-raster sweep, IoU 0.50→0.78→0.88).
Top view **fitted** (s=4135, cx=558.5, cy=663.5) — ASSUMED framing (head looking down; face at
bottom of frame); treat top as unverified; it carved only ~450 voxels vs the 6 horizontal views.
±45° views carve with 12 px tolerance (AI framing inconsistent between nose and hairline —
they cannot share one scale; raw-state would erase the nose). Profiles used 2 px.

**Results.**
- GLB: `output/character001_visual_hull/character001_visual_hull.glb` (12,304,872 B; also
  byte-identical snapshot `output/lane_b_snapshot/`). 52,822 faces / 29,211 welded verts.
  Extents 0.193×0.300×0.236 m. Watertight **hull** verified at export (position weld,
  closed 2-manifold; euler −26 → genus ~14 from thin hair wisps). GLB reload: uv range
  [0.036, 0.918]×[0.091, 0.991]; atlas 4096×2048 embedded; material PBR metallic 0 roughness 0.85.
- **Silhouette IoU (unoptimized, vs raw masks): front 0.911 · left45 0.907 · right45 0.921 ·
  left90 0.930 · right90 0.939 · back 0.878 · top 0.731.**
- Blender EEVEE renders (`output/lane_b_snapshot/renders/`): recognizable curly-red-haired
  head with eyes/lips/ears placed approximately correctly; heavy voxel terracing bands and
  hard texture seams remain; hair = stretched photo texture on a smooth blob.
- Volume 0.00634 m³. Laplacian smooth ×4 used.

**Per-variant comparison (documented, all outputs in `output/`):**
| variant | views carved | patch | IoU front/left45/right45/left90/right90/back/top |
|---|---|---|---|
| v2 | 6h | none (broken-yaw fix) | .909/.944/.958/.922/.928/.782/.766 |
| v3 | 6h + back calib | back fitted | .908/.944/.958/.922/.928/.877/.711 |
| v4 | 4 (no 45s) | — | .908/.628/.610/.958/.963/.878/.770 |
| v5 | 6h dilate45=12 | — | .909/.908/.919/.933/.940/.878/.729 |
| v6 | 6h+top dilate45=12 | top carved | .908/.908/.919/.933/.940/.878/.741 |
| **final** | **6h+top dilate45=12** | **cell 3.3 mm + laplacian ×4 + front/back tex bias** | **.911/.907/.921/.930/.939/.878/.731** |

**Known failure modes (honest).**
- Voxel terracing bands; hair curls unrecoverable; hull is head+hair volume, NOT a skull.
- Eyes, tear line, eye sockets, lid folds, lips detail, nose profile detail (tip is ~10–15 px
  flat/inside), nostrils, ears' canal anatomy, skin microdetail, stubble — all NOT recovered.
- Texture = planar photo projection; hard seams (front/side hemisphere junction); grazing-angle
  texel stretch; neck bottom shows photo rows as banding; terrace minification stripes.
- AI references uncalibrated & mutually inconsistent (per-view scale differs ~8%); all
  calibration except the 3 annotated views is fitted to the candidate itself (sweep,
  in-sample) — treat fitted views (back/top) as optimistically aligned; IoU not independent.
- Back silhouette IoU 0.878 is the weakest horizontal view (hair wisps); top 0.731 weakest overall.
- euler=−26 (genus ~14) — closed manifold, but thin tunnels exist (wispy hair artifacts).
- Geometry contains NO eyes → EEVEE renders show photo eyes floating on a smooth mask.
- This is a deterministic local candidate for gate review only; identity approval is out of scope.

**Next steps.**
1. identity-auditor + multiview-auditor gate (front AND side) before any "likeness" claim.
2. Replace projected-photo neck/jaw texture with sampled skin albedo + proper delit.
3. Separate head hull (here) from hair volume: dedicated hair mesh needed; hull hairline
   should be clipped at the true hairline for blending with a scalp/hair system.
4. Reduce terracing: 0.0025 m cell + anti-alias carving (soft mask), or SDF-based iso.
5. Texture seam fix: per-vertex view weights (cos² falloff) baked as vertex colors, or
   poisson-blend cells; or project only the front and side-profile views, drop 45/back from texture.
6. nose tip fidelity: per-view (cx,cy) fit dominated by hairline; a nose-region weighted
   sweep would help left90/right90.
7. Splice point: gate PASS → retopology (lane topology-specialist) → photoreal texturing
   (uv-texture-engineer/skin-*) → rig; hull is not animation-ready and never will be as-is.

**Files (worktree).** geo/visual_hull.py (mine, co-edited at export) · geo/calibrate_sweep.py ·
geo/tests_hull/test_visual_hull.py (9 tests, all PASS) · tools/render_hull.py ·
output/character001_visual_hull/* (GLB, report, overlays, renders) · output/lane_b_snapshot/*
(verified snapshot incl. renders) · output/run_geo03_v2…v6 (variants) · output/calib_sweep/ ·
output/seg_check/ · output/test_out.txt.
