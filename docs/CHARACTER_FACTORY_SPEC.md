# LIVYNTH Character Factory — Specification (proposed, v0.1)

**Status:** Proposed. Drafted read-only by the architecture specialist (cg-architect) from `docs/CHARACTER_FACTORY_INPUTS.md`; persisted by the coordinator 2026-11-11. No code is authorized by this document.
Authority order: `AGENTS.md` > `docs/C001_GEO03_STRATEGY.md` + addendum > this spec. Source anchors: repository `Orchard254/Livynth`, branch `feat/m001-talking-human-pipeline`, worktrees detached @ `31a9b19` (qa-scorecard, calibration `da5ccc1`, landmarks, visual-hull, triposr). Packet citations are to `docs/CHARACTER_FACTORY_INPUTS.md` (§n) and `docs/C001_GEO03_BLIND_SCORECARD.md` (§n, qa-scorecard worktree). Claims marked **UNVERIFIED** have not been executed or measured.

## 1. Design principles → user directives

| # | Directive | How satisfied |
|---|---|---|
| 1 | Reusable components | Existing `geo/` (proxy_fit silhouette rule, morph_fit, audit), calibration/landmark specs, `video/` path, blind scorecard are reused as-is; new code only at stage boundaries. Packet §4. |
| 2 | Factory interfaces | Stage JSON schemas (§4) + `CandidateManifest` (§5); each stage is a named file/config contract, not a process coupling. |
| 3 | Pluggable AI models | Backends are registry entries behind one manifest schema (§5); TripoSR/visual-hull/FLAME-Open/hosted APIs never imported by core code. |
| 4 | Automation first | Deterministic CPU baseline; `tools/local_check.py` + `geo/tests` become the factory smoke gate (§7); AI calls only inside gated stages. |
| 5 | Character independence | `characters/<char_id>/` contract (§3); no character-specific constants in code; all priors in per-character config (§6). |
| 6 | Preserve research | Packet + strategy + scorecard + calibration/landmark reports referenced, never overwritten; negative results preserved (scorecard §11). |
| 7 | Hardware flexibility | Runtime tiers + config-driven device selection (§8); never assume CUDA; this machine (no GPU compute, 16 GB RAM, i7-10510U) is the baseline tier. Packet §2. |
| 8 | Future video integration | Rigged GLB + voice contract to `video/` (§9); lip-sync/blink/jaw gates retained. |
| 9 | Evidence-based progress | Statuses stay distinct planned → implemented → unit-tested → rendered → visually approved; per-run provenance record (§7.3, scorecard §9 `eval.json`). Packet §5. |
| 10 | Controlled integration | Release-integrator review-only flow; feature branch only; no merges to `main` without user approval; GEO-03 Phase 3 gate precedes any layout migration (§3.3). |

## 2. Scope and truthfulness

The references are AI-generated (C2PA OpenAI `gpt-image`, `trainedAlgorithmicMedia`, 2026-11-11), not scans: no EXIF/lens/seed; pack FAILS SfM, is CONDITIONAL for a loose hair/ears-excluded silhouette hull, reference-only for TripoSR, PASS-as-appearance-reference (packet §3). Nothing in this factory "certifies" identity (scorecard §10). This spec authorizes **no rewrite** of `geo/` or `video/` before GEO-03 Phase 3 passes (packet §7).

## 3. Repository layout

### 3.1 Proposed per-character contract (NOT yet migrated)
```
characters/<char_id>/
  references/            # gitignored binaries: identity capture set (e.g. identity_capture_v1/)
  references/manifest.json  # tracked: SHA-256, dims, C2PA/license truth, view tags
  config/character.yaml  # tracked: per §6
  config/qa_overrides.yaml # tracked: threshold overrides, each with justification
  models/                # gitignored: backends' weights, caches
  candidates/             # gitignored: backend outputs pre-retopo (GLB/OBJ)
  output/                 # gitignored: renders, exports, QA bundles (gate_run_id/)
  provenance/            # tracked small files: run manifests, eval.json copies, licenses.json
```
Example `references/manifest.json`: `{"schema":"livynth.factory.refpack/1","char_id":"character_001","images":[{"file":"01_subject_front.png","sha256":"9d84f485…eaed2dd","dimensions_px":[1086,1448],"view":"front","c2pa":{"generator":"OpenAI gpt-image","ai_generated":true,"timestamp_utc":"2026-11-11T01:25Z"}}],"voice":{"file":"assets/voice.wav","sha256":"98FDFCDB…","sample_rate_hz":22050,"duration_s":13.997},"consistency_audit":"CONDITIONAL_hull / REFERENCE_ONLY_triposr / NOT_calibrated / NOT_scanned"}`. Full SHA set in packet §3.

### 3.2 Tracked vs gitignored (current .gitignore already covers `assets/characters/**`, `output/`, `assets/*.png|wav|glb`)
Tracked: specs, configs, manifests, license chain files, `eval.json` copies (small), landmark JSONs. Ignored: reference PNGs, voice.wav, GLBs, renders, weights. No binaries in Git. No credentials ever.

### 3.3 Migration plan (do NOT move files before GEO-03 Phase 3 gate passes)
F0/F1: none. After blind gate PASS for one GEO-03 candidate: (a) create `characters/character_001/{config,provenance}` with tracked files; (b) `git mv` pointers or leave `assets/characters/character_001/` in place with a tracked `characters/character_001/references/manifest.json` referencing the legacy path, or symlink-free copy list; (c) update `.gitignore` to cover `characters/*/{references,models,candidates,output}/`; (d) keep `assets/` path working (read-only legacy shim) until Character 002 dry run passes; (e) delete nothing. Any earlier migration invalidates in-flight lanes and is out of scope.

## 4. Pipeline stages (JSON-schema'd interfaces)

All stage outputs are JSON with `schema` + `schema_version`. Common envelope: `{schema, schema_version, run_id, char_id, stage, inputs[], config_sha256, command, exit_code, started_utc, finished_utc, status: planned|implemented|unit-tested|rendered|visual-approved|FAIL|BLOCKED|UNVERIFIED, artifacts[], failures[]}`. Stage files land in `characters/<char_id>/provenance/<stage>.json` (and `eval.json` per scorecard §9 for QA).

| Stage | In → Out | Config | Exit criteria | Evidence | Owners |
|---|---|---|---|---|---|
| S0 Ingest | ref pack dir → `references/manifest.json` | `config/character.yaml` | All files hashed, dims match manifest, C2PA/license recorded; mismatch ⇒ BLOCKED | manifest + `sha256sum` log | asset-curator |
| S1 Validate (Phase 0 gate) | manifest → `validate.json` (verdict) | same | Cross-view consistency audit done; annotate ASSUMED vs MEASURED; FAIL ⇒ no reconstruction | audit report (multiview-auditor) | asset-curator + multiview-auditor |
| S2 Calibrate + landmarks (Phase 1) | manifest → `calibration.json` (orbit camera model, ASSUMED intrinsics; calibration_spec.py, 33/33 tests, commit `da5ccc1`) + `landmarks/<view>.json` (landmark_spec 2.0.0; 32/32 tests) | `config/calibration_overrides.yaml` (optional) | Hashes verify via `verify_image_hashes()`; per-view detection or manual annotation; profile annotations REQUIRED for gate (currently MISSING ⇒ gate stays diagnostic) | calibration.json, landmark JSONs, test logs | camera-calibrator, landmark-engineer |
| S3 Reconstruct (Phase 2, parallel backends, blind to each other) | refs+calib+landmarks → `candidates/<backend>/` + one `CandidateManifest` per candidate | `config/backends.yaml` | Backend exits 0 or blocker report, never a fabricated mesh; each candidate independent | manifest (§5), backend logs, hashes | neural-reconstruction (A/TripoSR), parametric-reconstruction (B/visual-hull), external-api-reconstruction (D, gated), morph-fitting-engineer (fallback, blocked) |
| S4 Blind gate (Phase 3) | candidates + renders → `output/qa/<gate_run_id>/<label>/eval.json` | `config/qa_overrides.yaml` | Front landmark mean ≤16 px, IoU front ≥0.80 / profiles ≥0.75 (**placeholders, calibration pending**), GLB invariants, controls (self-IoU=1.000; jitter canary MUST fail), blinded ACCEPT×3 (01/04/05) | eval.json + overlays + sealed blind_map | independent-regression-qa (gate), blender-render-specialist (renders), identity-auditor + multiview-auditor (judges), release-integrator (summarize) |
| S5 Retopo + rig | winning candidate → quad-face GLB + shapes | topology Option B (open) | Retopo loops eyes/lips/jaw; morph essentials or mapped | audit report, Blender logs | topology-specialist, facial-rig-engineer |
| S6 Texture/hair/eyes | retopo GLB → textured GLB | `config/texture.yaml` | UV on all primitives; bake-not-project; hair shell/card hybrid; iris/naevus per macro | render deltas, albedo stats | uv-texture-engineer, skin-albedo-engineer, skin-microdetail-engineer, hair-specialist, eye-specialist, wardrobe-lookdev |
| S7 GLB export + audit | textured GLB → final GLB | — | Scorecard §3 absolute invariants; `audit_morph_fit.py` only for GEO-02 fallback | GLB + invariant JSON | glb-interoperability-engineer |
| S8 Render/video | final GLB + voice → MP4 | `config/video.yaml` | 1080×1920 MP4 when M001 gate attempted; ffmpeg ABSENT today ⇒ blocker until installed/approved | render logs, ffprobe output | blender-render-specialist, video-finishing-specialist, phoneme-aligner, lipsync-engineer |

No stage may consume output of a later stage. S3 backends are mutually blind; S4 judges never see backend labels.

## 5. Backend registry and CandidateManifest

`config/backends.yaml` selects per run; core code never hardcodes a backend:
```yaml
run: character_001_geo03
backends:
  - id: triposr_cpu        # MIT (verified); expected weak likeness
    enabled: true
    device: cpu
    weights_cache: models/triposr/
  - id: visual_hull        # deterministic, local
    enabled: true
    device: cpu
  - id: flame_2023_open     # CC-BY-4.0, REGISTRATION-GATED — disabled pending user decision
    enabled: false
    license_gate: user_approval_required
  - id: hosted_tripo        # research-only; no submissions without approval
    enabled: false
    license_gate: user_approval_required
    upload_denied_by_default: true
selection: auto
```
`CandidateManifest` (`candidates/<backend>/manifest.json`, schema `livynth.factory.candidate/1`): `{char_id, backend:{id,name,version,git_commit_or_hash,license,license_url}, model_weights:[...], inputs:[{path,sha256}], commands:[{cmd,exit_code}], outputs:[{path,sha256,role}], measured_metrics:{...}, blind:{gate_run_id,label}, license_chain:[...], known_failure_modes:[...], status}`. License is tracked per artifact; outputs inherit the strictest input license. Hosted outputs additionally carry vendor ToS + biometric clauses — recorded, never auto-approved.

## 6. Character config schema (`characters/<char_id>/config/character.yaml`)

```yaml
schema: livynth.factory.character/1
identity_id: character_001
display_name: "Character 001 (auburn-haired adult man)"
reference_manifest: characters/character_001/references/manifest.json
references_root: assets/characters/character_001/identity_capture_v1/   # legacy path until migration
truth:
  ai_generated: true
  c2pa: {generator: "OpenAI gpt-image", trained_algorithmic_media: true, timestamps: "2026-11-11T01:25–02:29Z"}
  calibrated: false
  scan: false
  statement: "Independent AI portraits; not camera-calibrated; never 'scanned'."
scale_priors:   # ASSUMED, not measured
  interpupillary_px: 212.0
  ipd_mm: 63.0
  focal_mm_equiv: 90
  camera_radius_mm: 1500
  head_height_m: [0.16, 0.34]
caps:
  texture_max_px: 2048            # 2K gate; 4K optional upgrade
  tris_max: 100000                # retopo goal; flag band 1k–2M per scorecard G-1
  face_mesh_scope: head-and-shoulders   # shirt-off geometrically rejected
voice:
  path: assets/voice.wav          # gitignored
  sha256: 98FDFCDBD371D848B4846A17820D0F62E398EECEE7C51079CF3056824D4EDD0A
  sample_rate_hz: 22050
  duration_s: 13.997
  peak: 0.936
  rms_dbfs: -21
  speech_active_s: 9.9
  transcript: assets/voice_transcript.txt
  alignment: UNVERIFIED
target_deliverables:
  - retopo_rigged_glb
  - five_angle_renders_1086x1448
  - m001_portrait_video_1080x1920   # only when M001 gate attempted
qa_threshold_overrides: {}          # empty = scorecard placeholders; never loosen silently
export_targets:
  glb: {units: meters, draco: false, textures_embedded: true, ktx2: UNDECIDED}
  video: {width: 1080, height: 1920, codec: h264, container: mp4}
gates:
  recognizable_character: {front_and_profiles_required: true, blinded: true}
  phase3_blocks_migration: true
```
Character 002 starts from this file as a diff, not from code.

## 7. Automation and testing

### 7.1 Factory CI (local, no GitHub Actions)
- `python tools/local_check.py` — PASS 21/21 (2026-11-11). Note: it does **not** run `geo/tests`.
- `python -m unittest discover -s geo/tests -v` — 21/21 OK (after `pip install trimesh`).
- calibration lane 33/33 (worktree commit `da5ccc1`); landmark lane 32/32.
- Factory CI = local_check + geo tests + calibration/landmark tests + a synthetic manifest/license check (to be written in F1; **UNVERIFIED, not implemented**).

### 7.2 Unit/synthetic vs gated live stages
Unit/synthetic (always CI): segmentation rule, manifest schema validation, config parse, blind-map seal/reveal, eval.json schema validator, jitter canary generator. Gated live (never CI; require approvals and human gates): TripoSR run, any FLAME use, any hosted API, all QA sign-off stages. Unrun ⇒ status `UNVERIFIED`, never inferred.

### 7.3 Provenance/evidence record (per run)
`provenance/run.json` per factory run + `eval.json` per candidate: commit, commands with exit codes, environment (Python 3.14.7, OS, Blender 4.5.10 LTS @ `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`, torch 2.15.0+cpu), input SHA-256s, artifact paths + hashes, license chain, failures, and `status`. Tracked `provenance/` (small JSON); binaries stay gitignored. Extends scorecard §9; never replaces it.

### 7.4 Render/QA scheduling
Renders/QA sessions explicitly scheduled: S3 in parallel; S4 only after a candidate exists; ≥3 independent measurement sessions per candidate; worst-session FAIL ⇒ candidate FAIL; segmenter-vs-human calibration (IoU ≥ 0.95 on `01`) must pass before the gate is meaningful — **not yet measured**.

## 8. Hardware flexibility (runtime tiers)

`config/runtime.yaml`: `tier: cpu-baseline | local-gpu | cloud-gpu`; `device: auto|cpu|cuda|rocm`; `max_memory_gb: 12` (3.9 GB free measured! — treat 4 GB as the binding constraint).
- **Tier 1 CPU-baseline (default, this machine):** visual hull, morph_fit fallback, numpy paths, Blender CPU Cycles, local_check. TripoSR-CPU is an experiment, never a promise.
- **Tier 2 local-gpu:** none available (Radeon 530 + Intel UHD; no CUDA/ROCm assumed). Config must not request CUDA; GPU detection advisory only.
- **Tier 3 optional cloud-gpu:** only with explicit user approval and budget cap; artifacts SHA-256 re-verified; same manifest schema; same license gate. No upload of references without written approval.
Fallbacks: GPU unavailable ⇒ CPU tier; Blender absent ⇒ render stages BLOCKED; ffmpeg absent ⇒ video stages BLOCKED.

## 9. Video integration (M001 path and future)

Input contract from factory to `video/`: GLB with (a) head/neck/shoulders coherence at 1086×1448; (b) UV on all primitives; (c) embedded textures; (d) **morph targets** named or mapped (min: blink L/R, `jawOpen`, one closure viseme); (e) meters, head height ∈ [0.16, 0.34] m; (f) skeleton OPTIONAL — M001 `render_talk.py` drives shape keys, not bones. `video/make_timeline.py` remains deterministic fallback; **not phoneme sync** — M001 requires real alignment (pending approval). Factory output → `assets/` copy only via explicit coordinator step; factory never writes into `video/`. Future multi-character scenes consume the same contract and are out of scope.

## 10. Alignment table — 30 specialists → factory roles

Legend: **G** = gate/blinded (never also implementation on the same candidate); **I** = implementation; **R** = read-only research; **C** = coordination.

| # | Agent | Role | GEO-03 | Future |
|---|---|---|---|---|
| 01 | livynth-director | C | yes | yes |
| 02 | asset-curator | I/R — S0 | yes | yes |
| 03 | identity-auditor | **G** — S4 | yes | yes |
| 04 | camera-calibrator | I — S2 | yes | yes |
| 05 | landmark-engineer | I — S2 | yes | yes |
| 06 | multiview-auditor | **G** — S1+S4 | yes | yes |
| 07 | reconstruction-research | R | yes | yes |
| 08 | neural-reconstruction | I — S3A | yes | per config |
| 09 | parametric-reconstruction | I — S3B | yes | per config |
| 10 | external-api-reconstruction | I(gated) | blocked | per approval |
| 11 | morph-fitting-engineer | I — fallback | fallback only | fallback only |
| 12 | topology-specialist | I — S5 | post-gate | yes |
| 13 | uv-texture-engineer | I — S6 | post-gate | yes |
| 14 | skin-albedo-engineer | I — S6 | post-gate | yes |
| 15 | skin-microdetail-engineer | I — S6 | post-gate | yes |
| 16 | eye-specialist | I — S6 | post-gate | yes |
| 17 | hair-specialist | I — S6 | post-gate | yes |
| 18 | wardrobe-lookdev | I — S6 | post-gate | yes |
| 19 | facial-rig-engineer | I — S5 | post-gate | yes |
| 20 | blink-specialist | I/QA — S5/M-1 | post-gate | yes |
| 21 | expression-specialist | I/QA — S5/T01–T10 | post-gate | yes |
| 22 | phoneme-aligner | I — S8 | blocked | yes |
| 23 | lipsync-engineer | I — S8 | post-gate | yes |
| 24 | natural-motion-engineer | I — future motion | future | yes |
| 25 | blender-render-specialist | I — S3/S4/S8 | yes | yes |
| 26 | video-finishing-specialist | I — S8 | M001 gate | yes |
| 27 | glb-interoperability-engineer | I/QA — S7 | yes | yes |
| 28 | performance-benchmarker | R/I | yes | yes |
| 29 | independent-regression-qa | **G** — S4 | yes | yes |
| 30 | release-integrator | **G** (summarize-only) | yes | yes |

**Gaps (honest):** no human-subjects/likeness-consent reviewer; no legal/provenance officer; no security/secrets reviewer; no data-retention/deletion owner (moot while uploads denied); no subtitle/caption reviewer. Must be staffed or explicitly user-waived before external release; GEO-03 remains internal/experimental regardless.

## 11. Character 002 acceptance test (pipeline, not character)

1. Fresh `references/manifest.json` via same S0 code; config diff limited to `identity_id`, hashes, voice, threshold defaults — **no factory code changes permitted**.
2. Stages S0–S4 run unchanged; S5–S8 consume 001-calibrated placeholders; per-character overrides only via `qa_overrides.yaml` with justification.
3. Character-specific permissible in code only as config: view azimuths, scale priors, wardrobe palette, texture caps.
4. PASS = 002 passes the same blind scorecard with a **recognizable second face via the identical pipeline**, independent human sign-off, zero factory-source edits.
5. Non-goals: 002 photorealism before 001 passes; no claims beyond "second recognizable character through same pipeline". Prereq: GEO-03 Phase 3 PASS + F2.

## 12. Phased plan & approval gates

- **F0 (now):** This spec + mapping; coordinator persists; user reviews. No code motion. **Exit:** user accepts/edits.
- **F1 (after F0 + go-ahead):** Wire GEO-03 lanes as backend adapters behind `CandidateManifest` + `backends.yaml`; add manifest/license/schema validator to local CI; ffmpeg + aligner only if approved; mediapipe/opencv resolution (in flight, UNVERIFIED). **Non-merge triggers:** edits outside adapter boundaries; `geo/`/`video/` changes before Phase 3 gate; silent threshold loosening.
- **F2 (after GEO-03 Phase 3 PASS + approval + Character 002 identity seed pack):** 002 dry run per §11 end-to-end. **Exit:** §11 PASS or documented FAIL with negatives preserved.
- **F3 (after F2):** Optional cloud backends with written approval + budget cap; M001 S8 video; migration per §3.3. Non-goals: no `main` merge without approval; no vendor lock; no GEO-03 status redefinition.

**Approval gates (user):** FLAME registration; Tripo API trial; aligner install; topology Option B; V32 GLB or retire fallback; 4K/KTX2/Reallusion; runtime-tier changes. No gate auto-passes.

## 13. Risks and explicit non-goals

**Risks:** (R1) References contradict across views — reconstruction may be a plausible average, not the person. Mitigation: blind gate, never skip. (R2) Placeholder thresholds may be unachievable ⇒ FAIL is a valid, valuable outcome. (R3) CPU-only neural lane likely infeasible in practice — blockers only, never fabricated meshes. (R4) Migration breaks in-flight worktrees ⇒ migration only after Phase 3. (R5) License drift (FLAME gated; DA-V2 CC-BY-NC; InstantMesh/TRELLIS NC) ⇒ per-artifact license chain mandatory. (R6) Blinding failures ⇒ re-label; record leaks. (R7) RAM/CPU constraints — any OOM invalidates runs; record memory. (R8) Blender-sync audit self-labels NOT VERIFIED; trust only real logs/renders. (R9) `make_timeline.py` heuristics passed off as lip-sync — forbidden.

**Explicit non-goals:** no full rewrite; no `main` merges; no uploads/paid APIs without approval; no 002-quality claims before 001 passes; no vendor lock; no "photoreal" language before blind-gate PASS; no deletion of research/negatives; GEO-01/GEO-02 are not identity evidence; no CUDA assumptions.

**Uncertainties / packet insufficiency:** profile-view landmark annotations missing (gate diagnostic); segmenter-vs-human agreement unmeasured; mediapipe on py3.14 unverified; no candidate exists; scorecard thresholds are placeholders; GEO-02 fallback blocked (no V32 GLB); ffmpeg/espeak absent; visual-hull/TripoSR results unknown; blind-bundle tooling not built; jitter canary not implemented; API/Reallusion pricing is research-grade, not quotes. Where silent, `AGENTS.md` wins.
