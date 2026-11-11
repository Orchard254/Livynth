# C001-GEO-03 — experiment log and integration plan (2026-11-11)

Coordinator-maintained. Every entry states what was **executed**, with commands/evidence, and keeps
statuses distinct (planned → implemented → unit-tested → rendered → visually approved).
No merge to `main`; no push; no external upload; binaries stay under ignored `output/`.

## A. Baseline (re-verified after the TripoSR dependency changes)

| Check | Command | Result |
|---|---|---|
| Unit tests | `python -m unittest discover -s geo/tests` | **21/21 OK**, exit 0 |
| Local check | `python tools/local_check.py` | **PASS**, exit 0 |
| Reference pack | 15 PNGs in `assets/characters/character_001/identity_capture_v1/` | present, gitignored, C2PA `gpt-image` |
| Shared env after Lane A installs | `pip list` | torch 2.15.0+cpu, transformers 4.35.0, huggingface-hub **0.17.3** (downgraded from 1.30.0 by TripoSR's pin) — baseline re-verified green |

## B. Verified successes

| # | Result | Evidence |
|---|---|---|
| S1 | **Multi-view visual hull (Lane B) implemented and rendered.** Deterministic CPU carve of 7 views (front/±45/±90/back/top), 536k voxels @3.3 mm, marching cubes + Laplacian smoothing, per-face planar texture atlas embedded (4096²). | `geo/visual_hull.py`, `geo/tests_hull/test_visual_hull.py` **9/9 OK**; report `output/character001_visual_hull/visual_hull_report.json` |
| S2 | **Export defect found and fixed by the coordinator.** The exporter emitted a per-face triangle soup (97,356 verts / 32,452 faces), which independently measured **not watertight** (14,642 boundary edges, euler −135) despite the lane report claiming watertight. Patched to weld by (position, uv) with a position-weld watertightness assert before export. | coordinator check: trimesh edge-usage histogram `{1: 14642, 2: 41357}`; after fix: **21,383 verts / 31,152 faces, position-weld watertight True, euler −14, 0 degenerate faces**, 11.79 MB (was 14.24 MB) |
| S3 | **Calibration spec delivered** (orbit cameras, real SHA-256 of all 15 refs, ASSUMED/MEASURED labels, projection helpers). | worktree `livynth-c001-geo03-calibration`, commit `da5ccc1`, **33/33 tests OK** |
| S4 | **Landmark spec delivered + real detection restored.** The lane's mediapipe install succeeded (mediapipe 1.2.2, opencv 5.0.0) but `mp.solutions.face_mesh` no longer exists in 1.2.2 and the Tasks API needs an unbundled asset. Coordinator downloaded `face_landmarker.task` (3.58 MB, Apache-2.0 model) and added a Tasks-API adapter (`geo/detect_landmarks.py`, `--model-path`). | **15 views processed, 7 detected** (front, both 45°, both profiles, front_closeup, right_ear) at 31 points each; honest failures: back, top, left_ear, eyes_closeup, iris/skin/lips/hair macros. Overlays visually verified: front + profile mappings land correctly on iris centres, canthi, brows, nose, lips, chin, gonion. 32/32 schema tests OK |
| S5 | **Blind scorecard persisted** (the QA agent had no write tools). | `livynth-c001-geo03-qa-scorecard/docs/C001_GEO03_BLIND_SCORECARD.md` — blinding rules, front gate (≤16 px mean / IoU ≥0.80 front, ≥0.75 profiles, all *placeholders*), GLB absolute invariants, required controls (self-IoU 1.000, jitter canary MUST fail, GEO-02 expected-fail canary), eval.json schema, sign-off roles |
| S6 | **Character Factory spec + research packet** delivered and persisted (all 30 agents mapped; Character 002 acceptance test). | `docs/CHARACTER_FACTORY_SPEC.md`, `docs/CHARACTER_FACTORY_INPUTS.md` |
| S7 | **Hull render camera matched to the carve cameras.** New `tools/render_hull_calibrated.py` renders the GLB with the same orthographic model (per-view s, cx, cy, yaw φ) at the scorecard's 1086×1448, probing both yaw signs. | 12 probe renders + `render_manifest.json` (camera params per view) |

## C. Verified failures / negative results (preserved)

| # | Failure | Evidence | Consequence |
|---|---|---|---|
| F1 | **TripoSR inference aborted** — `MemoryError` while streaming the 1.68 GB `model.ckpt` (708 kB/s; pinned huggingface-hub 0.17.3 on py3.14 buffers in memory; ~4 GB RAM free at the time). | `output/triposr_candidate/logs/run_attempt1_default256.log` (download stopped at 377 MB/1.68 GB) | Lane A produced **no mesh**. Mitigation in flight: resumable `curl` download to a local weights dir (no HF streaming) + local-path load, then rerun |
| F2 | **Reference pack cannot be registered.** AI-generated portraits disagree across views (nose, chin, hair, ear scale, freckle/mole maps, iris anchor) and split into two white-balance clusters. | multiview-auditor (visual, all 15 views) + asset-curator (C2PA, hashes, dims) | SfM/COLMAP **FAIL**; silhouette hull **CONDITIONAL**; multi-view photometric fusion invalid |
| F3 | **GEO-02 fallback is unrunnable**: no source GLB anywhere on the machine. | `python -m geo.morph_fit ...` → `FileNotFoundError: assets\our-avatar-v32-clean-blink.glb` (exit 1) | Fallback stays documented-only; image-first is the only path to likeness |
| F4 | ~~Hull render vs reference IoU far below the scorecard placeholders~~ — **RESOLVED this turn (see G3)**: the geometry was fine; the Blender render camera had an inverted `shift_y` (~400 px vertical error) and a fragile 7-view texture assignment. After the fixes the calibrated renders score **front 0.911 / left45 0.919 / right45 0.957 / left90 0.919 / right90 0.923 / back 0.778** at 1086×1448. | `output/render_v8_calib/` + `tools/camera_probe.py`, `tools/align_diag.py` | Cause was the render harness, not the candidate |
| F5 | **Lane B output is a photo-plastered mask, not a face**: no eyes/lids/sockets/nostrils/ear interior; nose tip sits ~10–15 px inside the true profile silhouette; hair is a blob; terracing bands at 3.3 mm cell; hard texture seams at the front/side hemisphere junction. | lane's own experiment record + coordinator visual inspection of `render_front.png` (hair-coloured blob at wrong framing) | Fails the user-mandated "recognizable head" gate; usable only as a silhouette envelope / IoU scaffold |
| F6 | **No phoneme alignment possible locally**: ffmpeg/ffprobe/espeak-ng absent; no aligner installed. | phoneme-aligner probe (commands + exit codes) | M001 lip-sync remains heuristic; exact unblock commands documented (MFA 3.4.3 or whisper+stable-ts, ~1–2 GB) |
| F7 | **Provider daily rate limit** hit the release-integrator subagent mid-task. | harness error `limit_rpd/thinkingmachines/inkling-2-small` | Integration plan executed by the coordinator instead (this document) |

## D. Integration / branch hygiene plan (coordinator, replacing the rate-limited agent)

**Current state**
- Branch `feat/m001-talking-human-pipeline` @ `31a9b19` (draft PR #1). Main untouched by every lane.
- Working tree carries pre-existing user changes (`assets/README.md` deleted, `assets/voice_transcript.txt` untracked) — **never touched**, must not be committed by agents.
- Untracked coordinator docs: `docs/C001_GEO03_STRATEGY.md`, `docs/CHARACTER_FACTORY_INPUTS.md`, `docs/CHARACTER_FACTORY_SPEC.md`.
- Worktrees (all detached @`31a9b19`, none pushed): `visual-hull` (Lane B code + outputs), `triposr` (clone + logs; no mesh), `calibration` (commit `da5ccc1`), `landmarks` (schema + detector + venv), `qa-scorecard` (scorecard), `character-factory` (unused).
- Gitignored and must stay untracked: `assets/characters/**`, `assets/*.png|wav|glb`, `output/**`, worktree `models/`, `.venv*`, `tools/triposr/`.

**Landing order (each step = its own reviewable commit on the feature branch; no `main` merge)**
1. `docs/`: C001_GEO03_STRATEGY.md, CHARACTER_FACTORY_SPEC.md, CHARACTER_FACTORY_INPUTS.md, this log. (Docs only, no behaviour change.)
2. `geo/calibration_spec.py` + `geo/tests_calibration/` + `docs/C001_GEO03_CALIBRATION.md` (from `da5ccc1`, re-based; 33 tests green).
3. `geo/landmark_spec.py`, `geo/detect_landmarks.py`, `geo/migrate_legacy_landmarks.py`, `geo/manual_annotations.py`, `geo/tests_landmarks/` + `docs/C001_GEO03_LANDMARKS.md` (32 tests green; record the mediapipe 1.2.2 Tasks-API adapter + the `face_landmarker.task` fetch step; the venv must NOT be committed).
4. `docs/C001_GEO03_BLIND_SCORECARD.md` (from the QA worktree).
5. `geo/visual_hull.py` (+ tests) and the Lane B experiment record **only after** the re-centred re-export lands and its report is regenerated. Do not land a candidate whose report contradicts the artifact.
6. `geo/export/audit_candidate.py` (absolute-mode GLB audit) once implemented; it must not change `geo/audit_morph_fit.py` or `video/model_check.py` semantics.

**Rules:** no binary in Git; every merge proposal carries command/exit-code/hash evidence; the blind map stays sealed until both judges sign off; the calibration/landmark/QA artifacts may land as *code + docs* now, but no lane may claim identity until the Phase 3 gate runs.

**Character 002 minimal diff (factory check):** only `characters/<id>/config/character.yaml`, `references/manifest.json`, voice asset and QA overrides — no changes in `geo/`, `video/` or the stage contracts. Hardcoding audit pending: grep for `character_001|character001|ours-photoreal|identity_capture_v1` across tracked files must return zero in *algorithm* code (config and docs are allowed).

## G. Coordinator fixes executed this turn (all re-verified)

| # | Fix | Verification |
|---|---|---|
| G1 | **Hull export welded** (position+uv weld + pre-export watertightness assert). | v8: 16,263 verts / 31,152 faces, position-weld **watertight True**, euler −14, 0 degenerate, 11.63 MB (was 14.24 MB with a non-watertight soup) |
| G2 | **MediaPipe 1.2.2 Tasks-API adapter** + `face_landmarker.task` asset fetch (3.58 MB). | 15 views processed → **7 detected** (front, ±45, both profiles, front_closeup, right_ear) at 31 points; overlays visually verified correct on front and profile; honest failures: back, top, left_ear, eyes/iris/skin/lips/hair macros |
| G3 | **Render camera calibrated to the carve's own projection** (`tools/render_hull_calibrated.py`, 1086×1448, per-view s/cx/cy/yaw, both yaw signs probed; `tools/camera_probe.py` diagnoses against the projection; `tools/pick_render_signs.py` resolves the yaw sign). | fixed `shift_y` sign (was ~400 px off) → **front IoU 0.911**, left45 0.919, right45 0.957, left90 0.919, right90 0.923, back 0.778 at the scorecard's resolution |
| G4 | **Texture double-exposure removed**: albedo now comes only from the two identity anchors (front + back photos); geometry still uses all 7 views. | v8 front render shows a **single** correctly framed face (previously two overlapping faces) |
| G5 | **TripoSR weights obtained without the failing HF streaming path**: resumable `curl` → local `weights/` dir; `run.py --pretrained-model-name-or-path <dir>` loads locally (no code patch needed). | model.ckpt 1,677,246,742 B downloaded (37 min @ ~730 kB/s); attempt 2 then failed **inside rembg** (`bria-rmbg-2.0.onnx`, 1.02 GB, read timeout at 596 MB after 21 min) |
| G6 | **rembg bypassed**: `tools/prepare_input.py` composites the subject over neutral 0.5 gray using LIVYNTH's own validated segmentation (`geo.visual_hull.segment_head`), then TripoSR runs with `--no-remove-bg` — no second 1 GB download, no extra model license. | foreground 600,756 px = 38.2 % of frame, **identical** to the carve's front mask; attempt 3 launched (background) |
| G7 | **Blind Phase-3 bundle built** (coordinator-side blinding per the scorecard): candidates exposed only as labels `A` and `B`, five standardized renders + references + rubric sheet, label→backend map sealed in `blind_map.sealed.json`. | `output/qa/geo03/2026-11-11-run1/` (A/A.glb, B/B.glb, renders, references, RUBRIC.md, blind_map.sealed.json) |
| G8 | **Lane A (TripoSR) candidate produced on CPU**: rembg bypassed with our own segmentation, weights loaded locally, inference 22 s + mesh extraction 35 s = **68.8 s total**. Mesh: 80,873 v / 161,488 f, 3.23 MB, vertex colours, **not watertight** (euler −117), no UVs. Aligned into the reference frame by measured silhouette IoU (front 0.632); yaw resolved by a 4-variant probe (yaw270 = front-facing). | `output/triposr_candidate/0/{mesh.glb,mesh_aligned.glb,yaw/}`; renders in `output/render_laneA_yaw270/` |
| G9 | **Gate controls executed — and they FAILED, which is the honest result**: reference self-IoU = 1.000000 (pass); the jitter canary (4,878 verts, σ = 8 px) was **not rejected** by silhouette IoU (0.9036 ≥ 0.80) **nor** by the landmark gate (mean 8.92 px ≤ 16 px). | `output/qa/geo03/2026-11-11-run1/controls.json`, `controls/canary.landmark_gate.json` |
| G10 | **Numeric sub-gates measured and interpreted**: candidate A front IoU 0.911, landmark mean **3.67 px** (max 10.8); candidate B front IoU 0.649, landmark mean **33.97 px** (max 62.9). | `A/front.landmark_gate.json`, `B/front.landmark_gate.json` |

### Interpretation of G9/G10 (important — this is not a pass)

- **The gate is BLOCKED, not passed.** The scorecard requires the intentional-failure control to fail; it did not, so no PASS/FAIL may be issued from these metrics (scorecard §7). Recorded in `output/qa/geo03/2026-11-11-run1/eval.json` with `status: BLOCKED`, `gate_valid: false`.
- **Candidate A's excellent numbers are an artefact, not evidence.** A's facial pixels *are* the reference photograph projected onto a carved envelope, so a 3.67 px landmark error proves appearance correspondence only; the jitter canary proves the metric does not constrain surface fidelity.
- **Candidate B has real 3D structure** (nose projection, eyelids, lips, ears, hair volume — see `yaw/render_270/probe_front_n.png`) but reads as a generic male head; its landmark error (33.97 px) fails the front gate outright.
- **Gate repair required before the next run**: replace the jitter canary with one the metrics are designed to catch (e.g. a wrong-identity canary — the reference face with a displaced/scaled landmark set) and/or add a metric that constrains 3D consistency (multi-view photo-consistency, or normal/depth consistency across views). Until then the decisive criterion is the human rubric from the blinded judges (now running on the sealed bundle).

## G2. Known limitation of the v8 candidate (honest)

- **Profile albedo is wrong**: the front photo is projected onto the profile-facing surface (so the 90° renders show a stretched front view of the face), and the rear of the profile is untextured (gray) with hard jagged seams where the front/back assignment switches.
- Cause hypothesis (next experiment): the 45°/90° photos have a yaw **sign** convention that may not match the carve's projection (`u = cx + s(cosψ·x + sinψ·z)`); sampling a photo with the opposite yaw yields a shifted copy of the face — which is what the earlier 7-view albedo double-exposed. The render harness resolved the yaw sign empirically per view (`tools/pick_render_signs.py`), and that resolution should be fed back into the *texture* projection (per-view sign), not only the render.
- Geometry itself is unaffected by this: per-view carve IoU 0.91–0.96 (front/45s/profiles) and calibrated render IoU 0.911 front / 0.919–0.923 profiles.

## G3. Phase-3 gate run 1 — result and the lessons it produced

**Verdict: FAIL. No candidate is a recognizable Character 001.** Blind identity judgement
(independent judge, sealed bundle, sealed map):

| Candidate | front | left profile | right profile | structure | identity |
|---|---|---|---|---|---|
| A (visual hull) | REFERENCE_ONLY | REGENERATE | REGENERATE | not a modelled face — identity is a flat photographic projection on a coarse shell; no lid/lip/nasal depth; rear cranium bounded by a photo seam; untextured ghost geometry across view seams | front/45° sector carries Character 001's own freckle map, iris colour, brow arch, lip proportions — but the likeness is **borrowed** from the photograph, not reconstructed |
| B (TripoSR) | REGENERATE | REGENERATE | REGENERATE | **real 3D facial structure** (modelled nose with tip and nostrils, eyelids with crease and eyeball form, lips with volume and vermilion border, ear helix, jaw and neck) but terraced/stair-stepped, untextured bleached skin, blocky hair | **NO** — a different, generic individual: broader skull, heavier mandible, different nose/lip/eye geometry, no freckles |

**Lessons (all negative results, preserved):**
1. **The numeric sub-gates are inadmissible** (G9): the jitter canary was not rejected by silhouette IoU (0.9036) nor by landmark error (8.92 px). Fix before run 2: a canary the metrics are designed to catch (e.g. wrong-identity) plus a 3D-consistency metric.
2. **Silhouette IoU is not a proxy for identity.** TripoSR on a tighter head crop *improved* head IoU from 0.632 → 0.764 while the rendered face visibly **degraded** (vertically compressed head, misaligned eyes, displaced ear, crusty hair). Optimising the wrong objective made the candidate worse. The closeup-reference input variant was also negative (0.650).
3. **Photo projection can borrow identity without reconstructing it** — candidate A scores 3.67 px landmark error because its facial pixels *are* the reference photo. Any metric built on image correspondence inherits this and must be paired with a structural/3D criterion.
4. **The gap is now precisely located**: the blocker is *3D facial structure with correct identity*, not silhouettes, framing, cameras, or plumbing. Lane A has structure but not identity; Lane B has identity but not structure. The next candidate must combine them — i.e. **drive a structured face mesh with the reference's identity**, not photo-project or generatively hallucinate one.

## G4. Phase-3 gate — both runs, and why the numeric metrics had to be retired

**Run 1** (`2026-11-11-run1`): identity judge — A: front REFERENCE_ONLY, profiles REGENERATE; B: all REGENERATE.
The multiview judge **self-disclosed a blinding leak** (it read `eval.json` inside the bundle, which already held the identity judge's sign-off) → per scorecard B-4 that session was invalidated, and its labels were not counted as independent.

**Run 2** (`2026-11-11-run2`): clean bundle, fresh labels, no prior verdicts present. Multiview judge —
A: front **ACCEPT (likeness only; geometry FAIL)**, profiles REGENERATE/REGENERATE; B: front REFERENCE_ONLY, profiles REGENERATE/REGENERATE.
Orientation check **PASS** for both candidates (no mirrored or swapped profiles → all failures are genuine, not an orientation artefact).

**Aggregated verdict (stricter label wins): FAIL. No candidate reaches ACCEPT on any required view.**

**Why the numeric sub-gates had to be retired (measured, not asserted):**

| Canary | Construction | Silhouette IoU | Landmark mean | Ratio metric | Rejected? |
|---|---|---|---|---|---|
| jitter | 4,878 verts, σ = 8 px | 0.9036 | 8.92 px | — | **NO** |
| wrong identity | face band scaled ×1.18 laterally (3,801 verts) | ≈unchanged | 13.0 px | 0.0062 | **NO** |

- The similarity-aligned landmark metric is **invariant to uniform scaling**, so a 18 % wider face survives it.
- Worse: because candidate A's facial pixels *are* the reference photograph projected onto the shell, stretching the shell stretches the photo with it — so even scale-normalised ratios barely move.
- **Consequence: any metric computed on the rendered appearance of a photo-projected candidate measures the photograph, not the geometry.** The Phase-3 gate must rest on geometry-level evidence (multi-view surface / normal / depth consistency) plus the human rubric. Appearance metrics are demoted to diagnostics.
- Multi-view ratio consistency on candidate A: front 0.019, left profile 0.055 (within the 0.08 threshold); right profile **UNVERIFIED** (landmark detection failed on that render — recorded, not counted as a pass).

**Clean judge's prescribed repairs (next build):**
1. Eliminate the duplicate/translucent shell (a carve-tolerance/dilation artefact: the hull carries a second offset layer).
2. Re-carve the posterior cranium so the 90° renders match the clean mass already produced in `back.png` (profile silhouettes carry hair wisps that tear the carve).
3. Replace the front/back-only albedo assignment with a per-view assignment whose yaw sign matches each photo (the render harness already resolves that sign empirically) so profiles stop showing a stretched front view.
4. Drop candidate B for likeness failure (no freckles, cubic hair, pale skin, generic geometry) rather than iterating it.

## H. Open user decisions (SUPERSEDED by ADR-C001-004 on 2026-11-11)

All seven decisions below were answered by the lead developer's ADR
`docs/decisions/ADR-C001-004-phase3-repair.md` (APPROVED FOR IMPLEMENTATION, NOT A RECONSTRUCTION PASS).
The ADR's seven decisions are now authoritative; this list is retained as the original question set.

1. **FLAME 2023 Open registration** (CC-BY-4.0) — approve/deny (Lane C).
2. **Tripo API trial** (~US$1–20, 4-view multiview) — approve/deny (Lane D).
3. **Aligner install** (MFA 3.4.3 or whisper+stable-ts; ~1–2 GB) — approve/deny (M001 phoneme timing).
4. **Topology Option B** (designed quad head on MPFB/CC0 basemesh, fitted to the winner) — approve/deny.
5. **V32 source GLB** — supply it or formally retire the GEO-02 fallback.
6. **Texture budget** — 2K gate vs 4K; KTX2 vs PNG; Reallusion Headshot 3 (~$329 desktop, only non-upload paid path).
7. **Character Factory spec** — accept / edit.

### ADR-C001-004 answers (authoritative, 2026-11-11)

| # | Decision | Effect on this plan |
|---|---|---|
| 1 | Topology Option B **APPROVED, conditional on provenance** | CC0 claim must be verified from primary sources; topology lane assigned |
| 2 | Candidate A: **ONE bounded repair experiment** | three named repairs; B dropped for likeness failure |
| 3 | FLAME 2023 Open: **evaluation approved, import NOT authorised** | research + attribution only; no account, no terms, no download |
| 4 | Phoneme aligner: **installation DEFERRED** | research only; existing WAV/timeline behaviour must keep passing |
| 5 | V32/MakeHuman GLB: **retired from the C001 critical path** | optional baseline if located; old tests and renderer compatibility preserved |
| 6 | **2048×2048** PBR texture target for the prototype | 4K only after identity/topology/UV/material tests pass; no upscaled detail |
| 7 | Character Factory: **provisionally approved as an interface contract** | versioned manifests, backend adapter interface, provenance, QA schema; isolated low-risk components only |

The ADR also imposes the **geometry-first acceptance protocol** (mandatory): blind bundles with
sealed candidate IDs and no verdict files inside; neutral clay renders + wireframes + orthographic
depth/normal maps with an explicit camera convention so the face can be judged with photo-projection
materials switched off; artifact QA (manifoldness, duplicate shells, self-intersection/offsets,
topology class, normal consistency, camera assumptions, rig/blendshape function); wrong-identity
controls that **must** be rejected without relying solely on 2D similarity-aligned metrics; and a
clean blinded human rubric where **a rejected profile cannot be overridden by a good-looking front
texture** and the stricter aggregate label wins.

**Phase-3 remains FAIL. No passed reconstruction candidate exists and none may be claimed until a
clean geometry-based gate AND a rejected wrong-identity canary both pass.**

## H2. Phase-4 dispatch (2026-11-11, six isolated worktrees)

All lanes branched from `b0235c1` (the ADR commit, fast-forwarded from `origin/feat/m001-talking-human-pipeline`).
No push, no merge, `main` untouched, user changes (`assets/README.md` deletion, `assets/voice_transcript.txt`) untouched.

| Lane | Worktree / branch | Owner | Scope |
|---|---|---|---|
| R — Candidate A repair | `livynth-c001-geo04-repair` / `experiment/c001-geo04-repair` | cg-builder | the three authorized repairs → exactly one candidate A2 + A1-vs-A2 comparison package |
| T — Topology | `livynth-c001-geo04-topology` / `experiment/c001-geo04-topology` | topology-specialist | verify CC0 basemesh provenance/license from primary sources; outline morph-preserving retopology |
| G — Gate | `livynth-c001-geo04-gate` / `experiment/c001-geo04-gate` | multiview-auditor | clean-room geometry gate: clay/wireframe/depth/normal, artifact QA, identity controls, sealed bundles |
| F — Factory | `livynth-c001-geo04-factory` / `experiment/c001-geo04-factory` | cg-architect | refined versioned interface contract + minimal implementable slice |
| R5 — Research/licence | `livynth-c001-geo04-research` / `experiment/c001-geo04-research` | reconstruction-research | FLAME 2023 Open evaluation, CPU aligner research, full licence matrix |
| REL — Release | read-only | release-integrator | propose organized commits for the untracked reports + lane source; no writes |

Coordinator baseline re-verified after the fast-forward: `python -m unittest discover -s geo/tests` → **21/21 OK** (exit 0);
`python tools/local_check.py` → **PASS** (exit 0).

## H3. Open owner actions (carried forward from the ADR)

These remain **owner-only** and are not performed by any agent:
1. FLAME 2023 Open — account creation / terms acceptance at `https://flame.is.tue.mpg.de/modellicense.html` (only if the evaluation recommends it).
2. Aligner install (MFA 3.4.3 or whisper + stable-ts) — deferred; command + acceptance test documented by the research lane.
3. Any paid/external service (Tripo API trial, Reallusion Headshot 3, cloud reconstruction backends) — not started.
4. Any upload of a user portrait to a third-party service — not performed.
5. Review and approval of every local commit SHA before any push or merge; PR #1 stays draft.

## F. Next engineering milestones (ordered)

- **M1 (this turn, done):** asset truth + cross-view audit + calibration + landmarks + blind scorecard + factory spec + first candidate + export fix.
- **M2:** re-centre the hull world origin, re-derive `s` per view, re-render at 1086×1448, re-measure render-vs-reference IoU (target ≥0.80 front / ≥0.75 profiles) — *still an envelope, not a face*.
- **M3:** Lane A completion — local-weights TripoSR run → second candidate → both candidates into the blind bundle (labels A/B, sealed map).
- **M4:** Phase 3 gate execution: 5-angle calibrated renders → identity-auditor + multiview-auditor (blinded) → scorecard eval.json. **First moment "recognizable Character 001" may be claimed.**
- **M5:** retopo (MPFB quad head fitted to the winner) → UV → texture bake → hair cards → eyeball/lids → 6 morph targets → blink/jaw/smile/lip-closure QA.
- **M6:** phoneme alignment (pending approval) → real viseme timeline → M001 1080×1920 MP4 with captions.
- **M7:** Character 002 dry run through the same pipeline (factory acceptance).
