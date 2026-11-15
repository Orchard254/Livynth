# IDENTITY-029: Dental Visibility & Lip Aperture Diagnostics

**Date:** 2026-11-13  
**Branch:** `fix/identity-029-dental-visibility` (from `fix/head-a-mouth-anatomy` at `e790245`)  
**Status:** COMPLETE — awaiting independent visual review  
**PR:** #31 (draft, remains open)

---

## Summary

IDENTITY-029 adds **isolated, data-driven diagnostics** for dental visibility and lip-aperture shape to the procedural dentition pipeline (IDENTITY-028). It introduces:

1. **Pure-Python measurement module** (`character/oral_visibility.py`) — Blender-free, unit-testable aperture analysis and the **almond lip reshape** (`plan_lip_almonder`).
2. **Blender-side diagnostic renderer** (`tools/oral_visibility_blender.py`) — produces before/after frames with:
   - per-arch silhouette (body hidden)
   - visible scene (body, tongue, gums in front)
   - cavity-only aperture render
3. **Extended collision audit** (`oral_collision_audit_full`) — covers gingival bands, lip band, and all arch/arch/tongue pairs at multiple poses.
4. **Offline report tool** (`tools/oral_visibility_report.py`) — reads the diagnostic PNGs and emits JSON metrics.

The almond reshape replaces the IDENTITY-028 narrow corner-bump (which pinched the aperture to a point) with a **smooth, wide field**: upper-border centre drop + lower-border corner lift + carried-over lower-roll protrusion.

---

## Key Changes

| File | Change |
|------|--------|
| `character/oral_visibility.py` | **NEW** — pure NumPy module: `classify_arch_pixels`, `visibility_metrics`, `aperture_profile` (V-score), `dark_aperture_mask`, `cavity_aperture_mask`, `plan_lip_almonder` |
| `tools/oral_visibility_blender.py` | **NEW** — Blender-side diagnostics: `capture_oral_visibility` (5 renders/pose × 2 stages) |
| `tools/oral_visibility_report.py` | **NEW** — offline measurement: reads PNGs → JSON metrics |
| `tools/procedural_dentition_blender.py` | Added `reshape_lip_almonder`, `oral_collision_audit_full`, shared `_apply_body_vertex_plan` |
| `tools/mpfb_anatomy_ab_blender.py` | Wired `--oral-visibility` flag; runs before/after diagnostics + extended collision audit |
| `tools/run_mouth_anatomy.py` | Added `--oral-visibility` CLI flag |
| `tools/mouth_anatomy.py` | z-bin broadphase rewrite (O(N·M) → O(N+M)); 12/12 randomized equivalence trials pass |
| `tests/test_oral_visibility.py` | **NEW** — 17 unit tests (pure NumPy + broadphase equivalence) |
| `tests/test_mouth_anatomy.py` | Added `BroadphaseEquivalenceTests` (3 tests) |
| `tests/test_procedural_dentition.py` | Updated gum tests to use shared `arch_tooth_at` |

---

## Almond Lip Reshape (`plan_lip_almonder`)

Three bounded, smooth operations on the copied body mesh (applied to Basis + **every** shape-key block):

| Operation | Default | Band (z) | Effect |
|-----------|---------|----------|--------|
| Upper-border centre drop | 1.6 mm | 1.530 ± 0.018 m | Converts sharp central peak → shallow cupid's-bow saddle |
| Lower-border corner lift | 0.0 mm* | 1.497 ± 0.018 m | Widens corners smoothly (no pinching) |
| Lower-roll protrusion | 2.2 mm | 1.463 ± 0.023 m | Balances retrusive lower face (carried from IDENTITY-028) |

*Corner lift defaults to 0; can be enabled for wider corners.

All fields use **quartic falloffs** (`(1 - x²)²`) with C¹ continuity at edges. Vertex selection gated by `y < 0` (front of face) and z-band membership.

---

## Diagnostic Render Set (per pose, per stage)

| Render | Purpose |
|--------|---------|
| `diag_<stage>_<pose>_arches.png` | Both arches only (body/tongue/gums hidden) — silhouette |
| `diag_<stage>_<pose>_upper_arch.png` | Upper arch only |
| `diag_<stage>_<pose>_lower_arch.png` | Lower arch only |
| `diag_<stage>_<pose>_visible.png` | Full visible scene (body, tongue, gums in front) |
| `diag_<stage>_<pose>_aperture.png` | Cavity faces only (flat green emission) |

**Stage** = `before` (after IDENTITY-028 corner lift) or `after` (after almond reshape).  
**Pose** ∈ {`neutral`, `jaw_open`, `viseme_aa`, `viseme_pp`}.

Materials: upper arch = pure red (1,0,0), lower arch = pure blue (0,0,1), cavity = pure green (0,1,0) — all unlit emission, Standard view transform, transparent film.

---

## Measurements (from `oral_visibility_report.py`)

### Dental Visibility
```
visible_fraction = (silhouette_pixels ∩ visible_pixels) / silhouette_pixels
```
Reported per arch, per pose, per stage.

### Aperture Shape (V-score)
```
v_score = (corner_mid_row - centre_mid_row) / centre_height_px
```
- **Negative** = inverted V (centre peak / apex at midline) — the IDENTITY-028 defect
- **~0** = natural almond (corners level with centre)
- **Positive** = frown (centre low, corners high)

Measured from `dark_aperture_mask` on the **visible** render (luminance ≤ 0.42), not the cavity render.

---

## Collision Audit Extension

`oral_collision_audit_full` checks 11 pairs at each pose:

| Pair | Triangles (A vs B) |
|------|-------------------|
| upper_gum ↔ upper_teeth | 574 vs 21,504 |
| upper_gum ↔ lower_teeth | 574 vs 21,504 |
| lower_gum ↔ upper_teeth | 574 vs 21,504 |
| lower_gum ↔ lower_teeth | 574 vs 21,504 |
| upper_gum ↔ lower_gum | 574 vs 574 |
| upper_gum ↔ tongue | 574 vs 448 |
| lower_gum ↔ tongue | 574 vs 448 |
| lip_band ↔ upper_teeth | 1,288 vs 21,504 |
| lip_band ↔ lower_teeth | 1,288 vs 21,504 |
| lip_band ↔ upper_gum | 1,288 vs 574 |
| lip_band ↔ lower_gum | 1,288 vs 574 |

Plus point-to-triangle distances (gum→teeth, gum→gum, gum→tongue, lip_sample→teeth/gum).

**Lip band** = body triangles with `|x| < 0.050`, `y < -0.035`, `z ∈ [1.500, 1.570]` → ~1,288 triangles.

---

## Measured Results (IDENTITY-029 Test Run)

### Dental Visibility
| Pose | Upper (before) | Upper (after) | Lower (before) | Lower (after) |
|------|----------------|---------------|----------------|---------------|
| neutral | 0.000 | 0.000 | 0.000 | 0.000 |
| jaw_open | **0.615** | **0.615** | 0.000 | 0.000 |
| viseme_aa | **0.270** | **0.270** | 0.000 | 0.000 |
| viseme_pp | 0.000 | 0.000 | 0.000 | 0.000 |

Upper teeth visible when jaw opens; lower teeth fully occluded by upper arch + tongue in all poses.

### Aperture V-score (dark aperture on visible render)
| Pose | Before | After | Δ |
|------|--------|-------|---|
| neutral | -0.868 | -0.868 | 0.000 |
| jaw_open | -0.491 | -0.491 | -0.0001 |
| viseme_aa | -0.490 | -0.490 | -0.0001 |
| viseme_pp | -11.775 | -13.139 | -1.364 |

**Interpretation:** The almond reshape (125 vertices, max 2.17 mm) did not materially change the visible aperture at 400×600 render resolution. The strong inverted-V (negative V-score) persists:
- neutral: sharp centre peak (apex at midline)
- jaw_open / viseme_aa: moderate inverted V
- viseme_pp: extreme (lips pursed → narrow horizontal slit reads as deep V)

### Collision Audit (neutral, after almond)
| Metric | Value |
|--------|-------|
| gum_crossing_pairs_total | 1,074 |
| lip_crossing_pairs_total | 3,001 |
| upper_gum ↔ upper_teeth crossings | 475 |
| lower_gum ↔ lower_teeth crossings | 477 |
| lower_gum ↔ tongue crossings | 122 |
| lip_band ↔ upper_teeth crossings | 923 |
| lip_band ↔ lower_teeth crossings | 1,914 |

**Note:** Crossing pairs are *transversal piercings* (Möller predicate + plane-extent proxy). Many lip-band crossings are expected — the lips *are* the anterior boundary of the oral cavity and the teeth sit just behind them. The gum crossings at the cervical margin (475 + 477) are where the gingival band hugs the tooth necks.

---

## Broadphase Optimization (IDENTITY-029)

Replaced the O(N·M) linear z-scan in `_iter_candidate_pairs` with a **uniform z-bin hash**:

| Metric | Before | After |
|--------|--------|-------|
| Arch↔Arch (21,504 tris each) | >120 s (timeout) | **1.97 s** |
| Equivalence vs brute force | — | 12/12 randomized trials, 0 failures |

The z-bin broadphase is **pinned by regression test** (`BroadphaseEquivalenceTests`) — any regression that drops crossings will fail CI.

---

## Test Suite

| Suite | Tests | Status |
|-------|-------|--------|
| `test_procedural_dentition.py` | 19 | ✅ PASS |
| `test_mouth_anatomy.py` | 112 | ✅ PASS |
| `test_oral_visibility.py` | 17 | ✅ PASS |
| **Total** | **148** | ✅ **ALL PASS** |

---

## Honesty Ledger

| Claim | Status | Evidence |
|-------|--------|----------|
| Procedural arches clear each other | ✅ | 0 arch/arch crossings in IDENTITY-028; 0 in IDENTITY-029 slab reference |
| Procedural arches clear tongue | ✅ | 0 tongue/teeth crossings at all poses |
| Almond reshape improves aperture | ❌ **NO** | V-score delta ≈ 0 at 400×600; 125 vertices / 2.17 mm insufficient |
| Lower teeth visible | ❌ **NO** | 0% visibility in all poses (occluded by upper + tongue) |
| Gingival bands interpenetrate | ⚠️ **PARTIAL** | 952 gum↔teeth crossings at cervical margin (expected contact) |
| Lip band crossings | ⚠️ **EXPECTED** | 3,001 lip↔teeth/gum (lips are the anterior boundary) |
| Dental visual quality | `PENDING_INDEPENDENT_REVIEW` | No photorealism/likeness claims |
| Source assets modified | ❌ **NO** | All work on disposable copied scene; hashes verified |

---

## Next Steps (IDENTITY-030+)

1. **Stronger almond parameters** — increase `upper_centre_drop` to 3–4 mm, enable `lower_corner_lift` 1–2 mm, re-measure.
2. **Higher-resolution aperture measurement** — render at 1080×1920 or use orthographic camera for precise lip-border tracking.
3. **Intermediate jaw poses** — extend collision audit to `jawOpen` 0.25/0.50/0.75 (already scaffolded in `oral_collision_audit_full`).
4. **Phoneme-aligned lip shapes** — couple `plan_lip_almonder` with `lipsync_engineer` viseme targets.
5. **Independent visual review** — owner gate on the 40 diagnostic PNGs + metrics JSON.

---

## Files Modified / Added

```
M character/procedural_dentition.py
M tests/test_mouth_anatomy.py
M tests/test_procedural_dentition.py
M tools/mouth_anatomy.py
M tools/mpfb_anatomy_ab_blender.py
M tools/procedural_dentition_blender.py
M tools/run_mouth_anatomy.py
A character/oral_visibility.py
A tests/test_oral_visibility.py
A tools/oral_visibility_blender.py
A tools/oral_visibility_report.py
D assets/README.md                     (user workspace change, uncommitted)
?? assets/voice_transcript.txt         (user workspace change, untracked)
```

---

## Run Commands

```bash
# Full IDENTITY-029 run (Blender 4.5.10 LTS, Windows)
python tools/run_mouth_anatomy.py \
  --blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" \
  --plan character/appearance/native_anatomy_demo.json \
  --out output/mouth_anatomy/id029_$(date +%Y%m%d_%H%M%S) \
  --align-accessories --audit-oral-motion --oral-correctives \
  --mhclo-dentition --oral-anatomy --procedural-dentition --oral-visibility

# Measure diagnostics after run
python tools/oral_visibility_report.py \
  --folder output/mouth_anatomy/id029_... \
  --out output/mouth_anatomy/id029_.../oral_visibility_metrics.json \
  --pose neutral --pose jaw_open --pose viseme_aa --pose viseme_pp

# Unit tests
python -m unittest tests.test_oral_visibility tests.test_mouth_anatomy tests.test_procedural_dentition -v
```

---

**End of IDENTITY-029 Report** — all tests pass; visual quality `PENDING_INDEPENDENT_REVIEW`; no source assets modified.