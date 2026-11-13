# IDENTITY-027 — Head A mouth anatomy, third pass (2026-11-12)

> **Superseded by IDENTITY-028 (2026-11-13):** the dental-arch delivery was
> rebuilt as a parametric permanent dentition replacing the photo slab in
> renders (`--procedural-dentition`); arch↔arch crossings now measure
> **zero in all four poses** on the rebuilt arches and the lip-opening
> border was corrected. Detector-correction, material-isolation proof,
> tongue fix, upper-seat pin and cavity validation from this report remain
> valid and unchanged. See `docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_028.md`.

Branch: `fix/head-a-mouth-anatomy` (stacked on `diagnostic/identity-024-dental-arch-isolation`, tip `48302a1`).
Runner: `python tools/run_mouth_anatomy.py` (opt-in `--oral-anatomy` path, same five-pose mouth closeup).

## What this pass changed

1. **Millimetre-scale collision detector corrected.** The transversal-crossing
   predicate (`_edge_pierces_triangle`, the core of both
   `count_intersecting_triangle_pairs` and `describe_intersecting_triangle_pairs`)
   used **absolute** tolerances: `abs(den) < 1e-9` on the barycentric area
   determinant `d00*d11 − d01*d01` (units m⁴) and `abs(denom) < 1e-9` on `n·d`
   (units m³). The determinant scales with the **square** of the edge length,
   so every triangle smaller than ~5.6 mm (circumradius) had `den ≈ 4.7e-10 < 1e-9`
   and was classified as "degenerate — never piercing". The MPFB oral
   facets are ~2–6 mm across: the detector was **blind to almost every genuine
   crossing on the assets it was certifying**. Tolerances are now **relative**
   (`abs(den) <= 1e-12 * d00 * d11`; `abs(denom) <= 1e-12 * n_norm * d_norm`),
   and the segment endpoint test tightened to `1e-12` so that an endpoint
   lying exactly on the surface is never scored as a crossing from
   floating-point noise. The two public entry points now share one iterator
   (`_iter_transversal_crossings`) and cannot drift apart.
   Regression tests: `MillimetreScaleDetectorTests` (mm-scale pierce detection,
   coplanar exclusion, collinear degeneracy, count/describe agreement,
   t=0 endpoint-on-surface excluded).

   **Measured effect (same geometry, seat 0.022, corrected predicate):**

   | Configuration | jaw_open 0.85 | viseme_aa 0.90 | neutral / viseme_pp 0.90 |
   |---|---|---|---|
   | before (absolute eps) | 12 | 6 | 12 |
   | after (relative eps) | **1039** | **768** | **369** |

   The previously reported "12 facet crossings" was an undercount artifact
   (~97 % of the crossings on this asset pair were below the old epsilon
   floor). Crossing locations are unchanged in kind: the bite band
   y ≈ −0.104…−0.145, z ≈ 1.554–1.563, two symmetric anterior facet clusters,
   depth estimates 2.6–4.7 mm.

2. **Tongue↔teeth intersections RESOLVED to zero in all four poses.**
   Measurement arc with the corrected predicate (untouched-seat baseline →
   IDENTITY-025/026 configuration had 47/47/86 jaw-open/viseme_aa/rest; the
   previous 46/46/82 figures were near-identical geometry under the old,
   lossy predicate):

   | Config | jaw_open | viseme_aa | viseme_pp | neutral | max depth |
   |---|---|---|---|---|---|
   | seat 0.024, scale 1.00, shift 0.000 | 47 | 47 | 86 | 86 | 8.2 mm |
   | seat 0.024, scale 0.92, shift 0.004 | 47 | 47 | 80 | 80 | 7.6 mm |
   | seat 0.030, scale 0.88, shift 0.008 | 31 | 31 | 23 | 23 | 5.3 mm |
   | seat 0.030, scale 0.82, shift 0.010 | 29 | 21 | 21 | 21 | 5.3 mm |
   | **seat 0.036, scale 0.80, shift 0.010 (new pins)** | **0** | **0** | **0** | **0** | **—** |

   With the pinned configuration, tongue→teeth minimum clearance is
   **4.51 mm (jaw_open), 4.69 mm (viseme_aa), 5.01 mm (neutral/viseme_pp)**.
   The new defaults (`TONGUE_SEAT_M=0.036`, `TONGUE_SCALE=0.80`,
   `TONGUE_SHIFT_Y_M=0.010`, cap `MAX_TONGUE_SHIFT_Y_M=0.010`) are validated
   in `validate_tongue_scale` / `validate_tongue_shift_y`, applied as one
   combined rigid translation (dz=−0.036, dy=+0.010, ‖t‖=0.0374 ≤ 0.045) and
   one uniform centroid scale (0.80) with identical treatment of Basis and
   all corrective key blocks. **Appearance is unchanged from the reviewed
   renders**: the byte-level pixels differ (TAA sampling), but the five
   stills are visually identical to the prior set at full review resolution
   (the tongue sits below the incisal ridge; resting posture against the
   lower teeth is a normal closed-mouth anatomy).

3. **Material isolation is now proven, not just asserted.** Every
   material/image mutation happens on a **single-user copy** of the copied
   scene's material datablock (the originals — which feed the source human
   and would be shared by the source object and the copy — are never
   edited). Evidence recorded per slot in the report
   (`mouth_anatomy_audit.material_isolation`):
   - tongue slot isolation: per-slot entries with original node counts
     before/after (must be equal), users before/after, and SHA-256 of every
     TexImage image's pixels **and** of the on-disk image files backing
     them, before and after the pass (both must be unchanged).
   - teeth slot isolation: same guarantees for the teeth diffuse; the
     installed `teeth.png` is never read for writing (in-memory copy
     re-packed), `original_image_sha256_before == after`.
   - body cavity/exterior materials are `bpy.data.materials.new` fresh
     datablocks by construction (recorded).
   - `material_isolation_verified: true` and the runner contract
     re-validates it (method string, ≥2 copies, originals unchanged,
     verified True) or fails the run.
   - the three installed `.mhclo` assets are re-hashed at report assembly
     (`installed_mhclo_reverified`) and must still match the SHA-256 pins
     from `character/appearance/native_anatomy_demo.json` (verified in
     the official run: all three `unchanged: true`).

## Collision evidence (official run `20261112_194331_962942`, evaluated world space)

| Pose | Arch↔arch pairs (max depth) | Tongue↔teeth pairs | tongue→teeth min |
|---|---|---|---|
| neutral | 369 (4.43 mm) | **0** | 5.01 mm |
| jaw_open 0.85 | 1039 (4.13 mm) | **0** | 4.51 mm |
| viseme_aa 0.90 | 768 (4.68 mm) | **0** | 4.69 mm |
| viseme_pp 0.90 | 369 (4.43 mm) | **0** | 5.01 mm |

Depth proxy = the smaller of the two onto-other-plane extents; this is an
overlap measure, **not** a minimal-translation penetration depth (MTV/SAT).
Tangential and coplanar sliding configurations are explicitly out of scope
(the predicate is transversal-only, by design; for two thin solids, genuine
volumetric interference always yields transversal face pairs).

### Arch↔arch (unresolvable without sacrificing the reviewed appearance)

With the corrected predicate, the photographic MPFB teeth slabs interpenetrate
at the bite in **every** configuration that keeps the upper row visible.
Measured across two seat values (tongue fixed at the new pins):

| Upper seat | jaw_open | viseme_aa | neutral / viseme_pp | depth range |
|---|---|---|---|---|
| 0.012 | 402 | 2122 | 1727 | 2.94–4.12 mm |
| **0.022 (kept, reviewed)** | **1039** | **768** | **369** | **4.13–4.68 mm** |

The crossing count is non-monotonic in seat (it tracks which facet angles
slide from near-parallel, uncounted, to transversal, counted) and the
penetration depth is ~3–4.7 mm everywhere. Eliminating the class entirely
requires the upper arch to stop engaging the lower slab — i.e. the teeth are
not visible (rejected long before this pass; the 0.012 configuration produced
the "detached photo-projection bulbs" review failure). No seat in between
resolves it (0.016 was measured under the old predicate; the class persists).
**The designed occlusal interlock is retained by owner-facing trade-off
decision; this is documented here so the trade-off is no longer hidden behind
a detector undercount.** The depths are at the incisal-edge/canine slab
boundary; the renders show the row with a clean dark gap (the interpenetration
is internal to the slab solids). If the owner wants the slabs de-interleaved,
the only asset-preserving options are (a) upper row hidden/embedded (rejected),
(b) a genuinely non-photographic tooth asset outside this fix's scope, or
(c) topology surgery — explicitly excluded (`teeth_topology_modified: False`).

## Material-isolation evidence (from the same official run)

```json
"material_isolation": {
  "method": "SINGLE_USER_MATERIAL_COPIES_AND_IN_MEMORY_IMAGE_COPIES",
  "copies_created": 2,
  "original_materials_unchanged": true,
  "original_images_unchanged": true,
  "installed_image_files_checked": 2,
  "installed_image_files_unchanged": true
},
"material_isolation_verified": true,
"installed_mhclo_reverified": {
  "eyes": {"unchanged": true}, "teeth": {"unchanged": true}, "tongue": {"unchanged": true}
}
```

`source_assets_modified: false`, `installed_mhclo_obj_modified: false`,
`source_human_modified: false`, `existing_glbs_modified: false`.

## Renders and archive (this pass)

`output/mouth_anatomy/20261112_194331_962942/` — `front_neutral.png`,
`front_jaw_open.png`, `front_viseme_aa.png`, `front_viseme_pp.png`,
`three_quarter_viseme_aa.png` + `anatomy_pose_report.json`
(viewer approval still **PENDING_INDEPENDENT_REVIEW**); ZIP
`identity025_head_a_mouth_anatomy.zip` (6 entries, `testzip` clean, 1.3 MB).

## Tests and checks

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -p "test_mouth_anatomy.py" -v` | **104 tests OK** (detector regression, mm-scale predicates, tongue scale/shift validators, array hash) |
| `python -m unittest discover -s tests` | **465 tests OK** (skipped 5, pre-existing) |
| `python tools/local_check.py` | exit 0 |
| `python tools/branch_audit.py --run-tests` | exit 0 |

## Explicit non-claims / limitations

- Visual quality is **PENDING_INDEPENDENT_REVIEW**; no likeness or photorealism claim (Phase-3 gate still FAIL).
- Depth estimates are onto-other-plane extent proxies, not MTV/SAT; coplanar area overlap is out of scope; tangential touches excluded by design.
- Arch↔arch interpenetration (369–1039 transversal face pairs, ≤4.7 mm) remains by designed-occlusal-interlock trade-off, re-measured correctly here.
- Cavity selection remains pinned to jawOpen=0.85 at selection time (BVH first-hit); index correspondence validated (13,378/13,378 tuples), never assumed.
- Tongue posture: pinned deeper (+36 mm seat) and recessed (+10 mm posterior) vs IDENTITY-026; five renders confirm no visible appearance change, still PENDING review.
- GLB export: NOT_TESTED. Volumetric SAT/self-intersection: NOT_TESTED (Möller transversal predicate + point-to-triangle clearances only).
- `viseme_pp == neutral` by construction (PP does not engage teeth/tongue correctives).
