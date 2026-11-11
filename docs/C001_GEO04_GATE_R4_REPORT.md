# C001-GEO-04 — gate run r4 report (A1/A2 blind review) and lead-developer handoff

**Date:** 2026-11-11 · **Branch:** `feat/m001-talking-human-pipeline` · **Base:** `b0235c1` → HEAD at the commit that adds this file
**Phase-3 status: FAIL — unchanged. No likeness may be claimed for any candidate.**
This report documents what landed, what was measured, and what the sealed blind review found.

---

## 1. What landed on the feature branch (since the FLAME/retopo/factory checkpoint)

| commit | what |
|---|---|
| `eddc617` | test(c001-gate): make the landed gate suite discoverable (26 tests) |
| `284b5a1` | feat(c001-gate): add clean-room blinded geometry evaluation gate for C001-GEO-04 |
| `17c8a84` | fix(c001-geo04): ship the facial rig in the exported GLB and drop stray scene objects |
| `a122f55` | feat(c001-geo04): verify CC0 quad basemesh provenance and define morph-preserving retopology path |
| `59f4628` | chore(c001-geo03): add hull rendering, gate and blind bundle tooling, TripoSR harness |
| `41fedc0` | docs(c001-geo04): land FLAME, aligner and licence-hygiene research |
| `12232fd` | docs(c001-geo04): Character Factory v1.0 interface contract and minimal slice |
| `32f6077` | fix(c001-geo04): repair candidate A duplicate shell, posterior cranium and view-aware albedo |
| `a60d689` | fix(c001-gate): keep candidate visible after the wireframe pass; fail loudly on empty renders |

Earlier in the session: `f1d8df9`…`a1e40ee` (branch audit, CI fixes, AGENTS.md Phase-3 FAIL record, blind scorecard, hull lane, landmark tooling, basemesh provenance) — see `git log`.

Nothing was pushed, merged or released. `main` is untouched at `0db7a7d`. PR #1 remains a draft.
The untracked/deleted user files (`assets/README.md` deleted, `assets/voice_transcript.txt`) were never staged.

## 2. The A2 repair (bounded, ADR-C001-004 decision 2) — what it did and did not buy

Candidate A2 (`output/a2_repair/character001_visual_hull.glb`, SHA-256 `CC2538698FFF9EA2589D7104700E64068DFC04688B8AF1965CA374591526A6FF`, 804 KB):

| metric | A1 (v8, regenerated) | A2 |
|---|---|---|
| faces / verts | 31,152 / 16,263 | 30,920 / 15,446 |
| connected components (as loaded) | **50** | **1** |
| position-weld watertight | True | True |
| watertight (as loaded) | **False** | **True** |
| euler (as loaded / position-weld) | −56 / −14 | −14 / −14 |
| boundary / non-manifold / degenerate faces | 1486 / — / 0 | 0 / 0 / 0 |
| back-view IoU (construction mask) | 0.782 | **0.913** (in-sample fit, flagged) |
| left90 / right90 IoU | 0.920 / 0.927 | 0.916 / 0.923 |
| front IoU | 0.909 | 0.899 (−0.010 trade, disclosed) |
| GLB albedo | embedded UV atlas, sRGB-washed COLOR_0 bug fixed en route | COLOR_0 vertex colours (linear) |
| artifact QA verdict | multiple_connected_components:50, overlapping_large_components:1, boundary_edges:1486, not_watertight | duplicate_opposite_faces:1 (1 pair), **no_uv** (by design — COLOR_0 albedo needs no UV) |

R1 (single welded shell), R2 (back-view calibration) and R3 (view-aware albedo with measured yaw signs) are all implemented and machine-verified. A2 is a **construction-quality** improvement, not an identity improvement.

**What A2 is not:** it carries no likeness claim, is not animation-ready, and is not evidence that the visual-hull approach can produce a recognizable Character 001. It cannot — it contains no facial anatomy at all.

## 3. The gate tooling defect (found, reproduced, fixed) — read this before citing any earlier run

`geo/gate/blender_render.py` `set_wire_visible(False)` after the wireframe pass set `hide_render=True` on the real meshes **as well as** the wire twins. Every view rendered after front was all-transparent. Blender's exit code stayed 0, so `blender rc=0` was printed while the session had produced no geometry evidence beyond front. The run crashed later in the manifest step (zero-size reduction), and the bundle was built from the partial evidence anyway.

**Consequences (all preserved, none hidden):**
- Gate runs r1 (2026-11-11 13:00), the 2026-11-11 run2 re-review, and r3 (14:03) all shipped bundles with only front + a black left45. The independent reviews of those bundles (run1, run2, and the r3 identity-auditor review, verdict "REGENERATE everywhere, fail-closed") were honest **but are not valid evidence about either candidate**. They are invalidated, not merely "mixed".
- The r3 bundle and its sealed map are preserved unmodified at `output/qa/c001-geo04-r3-invalidated/` with an `INVALIDATED` banner; the r3 identity verdict is preserved verbatim at `output/qa/c001-geo04-r3-invalidated/verdicts/identity-auditor_verdict_r3_INVALIDATED.md`.
- Fixed in `a60d689` (this branch): wire twins only hidden during the wireframe pass; view-named RuntimeError on empty alpha masks; `render_candidate()` now verifies `render_manifest.json` exists, covers all requested views and that every pass produced its files; `run_gate.py` refuses to build a bundle from an incomplete candidate or control. Gate suite 26 tests OK; `local_check` PASS.

Note: the **wrong-identity controls** in r1/r3 were evaluated before the crash per control (controls re-render fresh; front is rendered first, and control passes are clay,textured — they never triggered the bug), so control rejection results stand. The **bundle** (and any judged review of it) did not stand.

## 4. Gate run r4 (2026-11-11, valid) — the first complete blind bundle

Command (exactly as run):

```
python -m geo.gate.run_gate --run-id c001-geo04-r4 --out output/qa/c001-geo04-r4 \
  --candidate A1=.../character001_visual_hull_v8/character001_visual_hull.glb \
  --candidate A2=.../a2_repair/character001_visual_hull.glb
```

Machine results (both candidates, all five views, `views_done: [front, left45, right45, left90, right90]`, manifests written):

- raster-vs-Blender mask IoU: front 0.971 / 0.971 (A1/A2), left45 0.735 / 0.735, right45 0.735 / 0.735, left90 0.976 / 0.976, right90 0.962 / 0.962.
- artifact QA: A1 — `multiple_connected_components:50, overlapping_large_components:1, boundary_edges:1486, not_watertight` (FAIL). A2 — `duplicate_opposite_faces:1, no_uv` (passes everything except one face pair and the no-UV expectation).
- All six wrong-identity controls rejected for **both** candidates (face_band_widen, ipd_widen, eye_shrink, nose_lengthen, jitter, photo_plane).
- Bundle verified (87 files, manifest sha256 match; sealed manifest matches). `gate_valid: true`. **`gate_valid` means the gate can reject deliberately wrong identities — nothing else. It does not certify likeness.**

### 4.1 The blinded reviewers (independent, parallel, sealed)

Verbatim verdict files committed at `docs/gate_runs/2026-11-11-c001-geo04-r4/*.md`.
The mapping was sealed outside the bundle at `output/qa/c001-geo04-r4/sealed/blind_map.json` (bundle manifest sha256 `8d9271c421fba45c579f835b9f32f1e2aa84e29ce75e5f0b8c489bfdf24db3d4`) and is unsealed only here for the lead developer:

| blinded id | candidate |
|---|---|
| C7SB3E | A1 (v8) |
| CBSMMB | A2 (repaired) |

**identity-auditor** (sealed verdict, read only the r4 bundle): **REFERENCE_ONLY on all five views for both candidates** — no facial anatomy; the face read is a projected photograph; wireframe renders were near-black/illegible and are reported as unverifiable, not as clearance.
**multiview-auditor** (sealed verdict, read only the r4 bundle): front / left45 / right45 = **REFERENCE_ONLY**, left90 / right90 = **REGENERATE** for both candidates (no nasal projection, no brow–nose–lips–chin profile).

**Aggregate per the stricter-label-wins rule (a rejected profile can never be overridden by front texture):**

| candidate | front | left45 | right45 | left90 | right90 | aggregate |
|---|---|---|---|---|---|---|
| A1 (C7SB3E) | REFERENCE_ONLY | REFERENCE_ONLY | REFERENCE_ONLY | REGENERATE | REGENERATE | **REGENERATE** |
| A2 (CBSMMB) | REFERENCE_ONLY | REFERENCE_ONLY | REFERENCE_ONLY | REGENERATE | REGENERATE | **REGENERATE** |

**Phase-3 remains FAIL. Neither candidate is a likeness. No view of either candidate reaches ACCEPT.**

## 5. What this means (honest read)

1. The visual-hull class of candidate is **not a path to a Character-001 likeness** — two independent blinded judges converge on the same failure class. The A2 repair fixed real artifacts (duplicate shell, posterior carve, albedo space); it did not and cannot create facial anatomy. This matches the standing warning: appearances can be photoreal while geometry is empty.
2. The geometry gate now works end-to-end (complete bundle, verified manifest, sealed map, two blind judges) and can distinguish "gate-valid" from "gate-fail". It has **never yet** produced an ACCEPT for any C001 candidate — every run, including r4, says REGENERATE / REFERENCE_ONLY.
3. A2 is retained as a diagnostic artifact only. Do not merge it anywhere as a "result"; it belongs in the artifact archive (backed up at `C:\PROJECT\Livynth-artifacts\2026-11-11\` with SHA-256 manifest).
4. The likely *next* experiment is the topology lane (CC0 basemesh → Character-001 fit → MPFB morph bake), which is the only current lane that could ever produce real facial anatomy — but it has no identity evidence yet and must pass the same blind geometry gate.

## 6. Provenance, artifacts, backups

- A2 GLB: SHA-256 `CC2538698FFF9EA2589D7104700E64068DFC04688B8AF1965CA374591526A6FF` — backup `C:\PROJECT\Livynth-artifacts\2026-11-11\lanes\livynth-c001-geo04-repair\a2_repair\` (+ `MANIFEST.sha256.txt`); r4 evidence: `output/qa/c001-geo04-r4/` (bundle + sealed + verdicts; output/ is gitignored).
- A1 v8 GLB: SHA-256 `C7451BDA29B2E80841FD5B4B1EE785827315A309E1D91EAC04F5375E14FB6564`.
- Artifact index: `C:\PROJECT\Livynth-artifacts\2026-11-11\MANIFEST.md` (candidates + lanes backups, hashes).
- External state: `main` @ `0db7a7d` (untouched); working tree carries user changes (`assets/README.md` deleted, `assets/voice_transcript.txt` untracked) — never staged by agents.

## 7. Verification commands and results (2026-11-11, this machine)

| command | result |
|---|---|
| `python -m py_compile geo/gate/blender_render.py geo/gate/candidate.py geo/gate/run_gate.py` | exit 0 |
| `python -m unittest discover -s geo/tests_gate` | Ran 26 tests, OK |
| `python -m unittest discover -s geo -t . -p 'test_*.py'` | Ran 125 tests, OK (skipped=2 — the two tests gated on gitignored A2 artifacts skip in the clean checkout) |
| `python -m unittest discover -s geo/tests_hull -v` | Ran 13 tests, OK (skipped=2 — same artifact gate) |
| `python tools/local_check.py` | PASS (all requested local checks completed) |
| `python -m geo.gate.run_gate --run-id c001-geo04-r4 ...` | complete; `gate_valid = True` (bundle verifies; all controls rejected) |
| Blender 4.5.10 LTS, no CUDA, Python 3.14.7 | headless renders validated by actual Blender logs in `work_*/renders/blender_render.log` |

## 8. Known residual failure modes & UNVERIFIED items

- `artifact_qa` self-intersection check **not run** — `rtree` missing (`self_intersection.error` in the report). UNVERIFIED for both candidates.
- `metrics.py:234 RuntimeWarning: All-NaN slice` during A1 evaluation (a fully-masked percentile in the appearance metrics) — metrics are diagnostic-only; flagging, not fixing silently.
- A2 front IoU is 0.010 below A1 (the back repair cost) — disclosed in `A2_REPAIR_REPORT.md`.
- Back-view calibration is an in-sample fit (flagged as an assumption everywhere it appears); no independent validation exists.
- Both candidates' wireframe renders are near-black — reviewers could not verify topology from them; reported as a limitation by both judges, not as clearance.
- Textured passes are expectedly all-zero for the COLOR_0 GLB (glTF COLOR_0 imports as a colour attribute; the GLB carries no materials) — diagnostic only.
- A2 inherits genus ~7 (euler −14) from marching-cubes wisps; closed but not simple manifold.
- The r4 judges reviewed stills, not motion/animation; rig function is entirely untested for A2 (no skin, no morphs — static hull).
- Reference photos are AI-generated, uncalibrated; the gate's camera fits are per-view normalizations, not measured camera recovery.
- FLAME 2023 Open registration is still pending an owner decision (license restriction on synthetic-human use; written Max-Planck clarification required). No FLAME models were downloaded or used.
- Phoneme aligner installation remains deferred; M001 heuristic unchanged; baseline boundary-MAE is still **unmeasured**.

## 9. Decisions requested from the lead developer

1. Accept the r4 record as the new blind-gate evidence; keep Phase-3 FAIL; do not present A1/A2 as likeness candidates in any review.
2. Confirm retirement of the visual-hull candidate class from the critical path (match ADR-C001-004 decision 5 spirit), or direct a further bounded experiment with explicit goals — understanding that two blind judges converge on REGENERATE for both.
3. Authorize (or decline) the follow-on topology experiment: MPFB/MakeHuman CC0 basemesh → Character-001 geometric fit (Stage 1) → post-fit rig/blendshape audit (Stage 2). Neither stage has started; both would feed the same blind geometry gate.
4. FLAME 2023 Open: send (or decline to send) the written licence enquiry to ps-license@tue.mpg.de (fake/libelous-content clause vs commercial synthetic-human product; landmark/mask training-output terms).
5. Aligner timing: install faster-whisper (or MFA) only when the M001 production gate is attempted, after measuring the heuristic baseline's boundary MAE.
6. Texture budget ratification for the prototype (2048² per ADR; 4K only after the identity/topology/UV/material gates pass).
7. Character Factory v1.0 interface contract sign-off (`docs/C001_GEO04_FACTORY_INTERFACE.md`) and whether to land the minimal slice (purely additive validator + read-only audit; no pipeline behaviour change).
8. Decide the fate of the temporary comparison package and A1-regeneration artifacts (keep in artifacts archive, or prune).
