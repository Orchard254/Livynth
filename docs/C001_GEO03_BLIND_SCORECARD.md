# C001-GEO-03 — Blind scorecard & acceptance protocol (independent-regression-qa, Task D)

**Status:** protocol only — **no candidate exists yet; nothing is judged; no render exists.**
**Worktree:** `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo03-qa-scorecard` (detached HEAD `31a9b19ad36ab611fc03f9cec1bc3565da56466b`)
**Author role:** independent-regression-qa (Task D, `docs/C001_GEO03_DISPATCH.md`)
**Inputs:** `AGENTS.md`, `docs/C001_GEO03_DISPATCH.md`, `docs/C001_GEO03_STRATEGY.md` (main checkout only — absent from this worktree at HEAD), reference pack `assets/characters/character_001/identity_capture_v1/` (15 PNGs; **gitignored → absent from this worktree; any evaluation must run where the assets exist**)
**Scope:** defines HOW a future candidate is accepted/rejected. It does not and cannot bless any candidate today.

## 0. Hard rules for this protocol

1. No candidate from any backend is "recognizable Character 001", "photoreal", or "complete" until every required check below passes on actual renders + actual GLB. A valid GLB alone is never sufficient (AGENTS.md, source-of-truth gate 6).
2. Judges (identity-auditor, multiview-auditor) never see fitting code, backend names, commit messages, lane names, file sizes, paths, or timing.
3. Status vocabulary stays distinct: planned → implemented → unit-tested → rendered → visually approved. This protocol gates the rendered → visually-approved step only.
4. Unrun checks are reported as UNVERIFIED, never inferred from syntax or from another agent's claim. Negative results are preserved.
5. No network, no external API submission, no upload of reference images, ever, in this protocol.

## 1. Blinding rules (enforced before any judge sees anything)

**B-1 Sealed map.** The coordinating agent (not QA, not a judge, not the candidate generator) renames every candidate deliverable before judging: `output/qa/geo03/<gate_run_id>/A/`, `.../B/`, … with `A/B/….glb`, `A/front.png`, `A/pm45.png`, `A/nm45.png`, `A/left_profile.png`, `A/right_profile.png`, `A/back.png`. The label↔backend map is sealed to `output/qa/geo03/<gate_run_id>/blind_map.sealed.json` and released only after all sign-offs are recorded. Judges receive a judge-facing bundle only: this protocol, the reference images, candidate renders, and a blinded rubric sheet.
**B-2 Metadata hygiene.** Candidate file sizes, paths containing backend hints ("triposr", "visual_hull", "lane_b"…), git hashes, and generation logs are excluded from the judge bundle. The harness must copy exactly the whitelisted files listed in §6.
**B-3 Independence.** identity-auditor and multiview-auditor review the same bundle independently. Neither may read candidate source code, the fitting repo paths, or another judge's notes before filing their own verdict.
**B-4 Leak handling.** Any accidental exposure (path, size, message, overheard) invalidates that judge's session; re-copy the bundle under fresh labels and re-judge. The leak and the invalidated session are recorded in the report JSON (`blinding.leak_events`), never deleted.
**B-5 Self-test.** After sign-off the map is revealed. If any judge correctly guessed the backend for every candidate, flag `blinding.guess_flag = true` in the report (diagnostic only; does not auto-fail, does flag that blinding may be insufficient for the next run).
**B-6 Cross-check controls.** Every gate run MUST include, reported alongside candidates: (i) reference self-IoU control (01 vs 01 = 1.000 required — a lower value means a broken segmenter/harness, abort the run); (ii) an intentional-failure control (§8.2) which MUST fail; (iii) the GEO-02 candidate renders if available, recorded as an expected-fail canary (documented in `docs/characters/C001-GEO-02.md`: visual identity FAILED). Controls use the same code path as candidates.
**B-7 Judges never edit candidates.** No judge may request "a small fix and re-render"; any change produces a new blinded label (`A′`) and a fresh judge round.

## 2. Primary user-mandated gate — "recognizable Character 001"

**Rule (user mandate):** a candidate is recognizable Character 001 only if it passes front **and** both profiles (`01_subject_front.png`, `04_left_profile.png`, `05_right_profile.png`) on visual AND numeric sub-gates. The 45° views, back, and macros are advisory — they can block only via multiview-auditor's geometry-impossibility veto (impossible anatomy/lighting/identity), not via independent numeric thresholds.

### 2a. Image-space landmark error (px @ 1086×1448)

**Canonical front landmark set (10 points), annotated on the rendered candidate at identical framing:**
L/R eye centers (mean of medial+lateral canthi, or MediaPipe iris centers 468/473 with `refine_landmarks=True`), L/R brow peaks, nose tip (pronasale), L/R mouth corners, chin pogonion, L/R gonion (jaw angles).

**Canonical profile landmark set (7 points, diagnostic until annotated):** nasion, pronasale, subnasale, labiale superius + inferius (one upper/lower lip silhouette point each), pogonion, tragion. **No profile landmark annotations exist in the repo today** (`geo/character001_landmarks.json` covers the front only, manual estimates from `01`, eyes (444,526)/(656,525), chin (549,925), mouth corners (466,762)/(630,762)) — profile sets are BLOCKED until landmark-engineer lands them; until then profile numbers are diagnostics and may not auto-pass the gate.

**IPD normalization (justification anchor).** Front-reference interpupillary distance from `geo/character001_landmarks.json`: √((656−444)² + (525−526)²) ≈ **212.0 px**. All front thresholds are expressed in px and as IPD fractions. Face crown→chin anchors in `geo/proxy_fit.py` (`VIEWS`, front crown y=55, chin y=924) give face height ≈ 869 px; eyes→pogonion ≈ 399 px; mouth-line y=762. These are uncalibrated AI-portrait estimates, not scan metrology — IPD is used only as a scale-free ruler.

**Alignment before measuring.** Similarity transform (translation + uniform scale + rotation) fitted on ≥6 of the 10 points, full-image canvas 1086×1448, identical camera framing injected by the renderer (§6). Record the fitted transform and residual RMS in the report. A residual > 20 px invalidates the alignment → BLOCKED (fix camera/framing), not FAIL.

**Front thresholds (mean / P95 / max over the 10 points):**

| Verdict | mean | P95 | max single point | IPD-relative | Tag |
|---|---|---|---|---|---|
| PASS | ≤ 16 px | ≤ 26 px | ≤ 42 px | ≤ 0.075 / 0.125 / 0.20 IPD | placeholder-needs-calibration |
| WARN (visual sign-off mandatory, no auto-pass) | ≤ 21 px | ≤ 42 px | ≤ 64 px | ≤ 0.10 / 0.20 / 0.30 IPD | placeholder-needs-calibration |
| FAIL | > 21 px or P95 > 42 px or max > 64 px | | | | placeholder-needs-calibration |

Justification: 0.05–0.10 IPD (NME ≈ 0.05–0.10) is the customary "acceptable–good" band in facial-landmark evaluation for controlled frontal views; AI-generated references (not scans) forbid tighter claims. PASS ≈ "human-auditor-verifiable same person", not "photoreal". **Placeholders:** no candidate has been measured; must be recalibrated against (i) the GEO-02 candidate (expected FAIL), (ii) an intentionally jittered render canary (expected FAIL), (iii) a reference-vs-reference alignment simulation. Recalibrate after the first candidate batch; keep tightening, never loosen silently — loosening requires a documented user decision.
**Also required to PASS:** median error ≤ 0.075 IPD (one outlier cannot dominate), and a per-landmark breakdown is emitted so systematic drift (e.g., nose too projected, gonion too wide) is visible.

**Profile thresholds (diagnostic-only until profile annotations exist):** PASS ≤ 25 px mean, WARN ≤ 40 px, FAIL > 40 px. Tag: placeholder-needs-calibration + blocked-until-annotation.

### 2b. Silhouette IoU (render vs segmented reference)

**Renderer:** Blender 4.5 headless, five standardized angles (front / ±45 / ±90 / back — per strategy Phase 3, rendered by blender-render-specialist), neutral gray background, camera framing identical to `geo/proxy_fit.py` conventions and locked across candidates. Identity stills rendered at exactly **1086×1448** so IoU is measured on the same canvas as the references.

**Segmentation (identical code path for reference and candidate render):** reuse the `geo/proxy_fit.py::read_profile` rule — border-median background estimate, foreground = `(distance_from_bg > 26 & chroma > 12) | distance_from_bg > 54` — run row-agnostic to produce a full mask; do NOT erode curly-hair strands (hair is part of the accepted silhouette, per C001-GEO-01 interpretation and Lane B design). Calibrate the segmenter once before gate use: on `01_subject_front.png` its mask must agree with two independent human masks at IoU ≥ 0.95, else fix or BLOCKED. Report the achieved agreement.

**Metrics per view:** IoU = |ref ∩ cand| / |ref ∪ cand|.

| View | PASS | WARN | FAIL | Tag |
|---|---|---|---|---|
| Front (vs `01`) | ≥ 0.80 | 0.70–0.80 | < 0.70 | placeholder-needs-calibration |
| Left profile (vs `04`) | ≥ 0.75 | 0.65–0.75 | < 0.65 | placeholder-needs-calibration |
| Right profile (vs `05`) | ≥ 0.75 | 0.65–0.75 | < 0.65 | placeholder-needs-calibration |
| 45° L/R (advisory) | ≥ 0.70 | 0.60–0.70 | < 0.60 | placeholder, advisory |
| LR asymmetry `|IoU04 − IoU05|` | ≤ 0.10 | 0.10–0.15 | > 0.15 (flag, not auto-fail) | placeholder-needs-calibration |
| Self-control (01 vs 01) | = 1.000 (harness sanity; anything less ⇒ abort run) | — | — | justified (invariant) |
| Ceiling diagnostic (04 vs 05 true cameras) | report, never gate | — | — | diagnostic |

Justification for the numeric bounds (uncalibrated AI portraits; network disabled — no citations fetched, treat as rationale not specification): weak-perspective multi-view silhouette fitting literature reports IoU ≈ 0.75–0.85 for good-but-imperfect fusion; curly hair defeats pixel masks (edge strands), so demanding >0.90 is fiction. 0.80/0.75 = "shape consistent with reference"; anything below ≈ neck/shoulder or pose mismatch. GEO-01's documented median LR profile-width disagreement of **1.33%** (C001-GEO-01 doc) shows the references themselves agree on depth only coarsely — profile IoU must be looser than front. **All IoU bounds are placeholders until measured on (a) the first real candidate renders, (b) the 04/05 ceiling control, (c) a segmentation-noise study. Tighten after calibration; never loosen without user approval.**

### 2c. Human visual rubric (ACCEPT / REFERENCE_ONLY / REGENERATE)

Independent of the numbers: identity-auditor + multiview-auditor apply the vocabulary of `character_001_identity_capture.md` (§ Review labels) view-by-view. Aggregation for the user-mandated gate:

- **ACCEPT on ALL THREE** (01, 04, 05) → eligible (still requires §2a/§2b PASS and §3/§4).
- **REFERENCE_ONLY on any required view** → NOT "recognizable" (gate FAIL for this claim; result preserved as data).
- **REGENERATE on any required view** → FAIL.
- Advisory views: REGENERATE anywhere ⇒ multiview-auditor geometry-impossibility veto (unfixable anatomy, impossible lighting/occlusion, broken identity) ⇒ FAIL; otherwise recorded as warnings.
- Identity vs multiview disagreement ⇒ **stricter label wins**; unresolved ⇒ user arbitrates. Both labels and the resolution are recorded.

**Mandatory rubric checklist (each judge ticks each item with one line of observable evidence — no bare verdicts):**
1. **Eye spacing** — interocular distance vs reference (~212 px front); gross drift ⇒ REGENERATE.
2. **Brow line** — height/angle vs reference; heavy asymmetry artifact ⇒ REGENERATE.
3. **Nose projection** — pronasale→subnasale projection vs profiles; snub/pointed drift ⇒ REGENERATE (user gate is front+profiles precisely because of this).
4. **Lip shape** — medium lips, fuller lower lip, natural width; over-filled/inverted ⇒ REGENERATE.
5. **Chin/jaw** — modest angular jaw, oval face; gonion width vs reference.
6. **Hair mass** — short curly auburn with clear hairline; wrong color/straight/long hair ⇒ REGENERATE (old-avatar ponytail failure of GEO-02 is the precedent).
7. **Ear placement** — vertical center ≈ nose-to-brow band, position vs profile views; pinned/misplaced ⇒ REFERENCE_ONLY at best.
8. **Skin/freckle tone & lighting** — natural fair skin with freckles; waxy/airbrushed/colored light ⇒ REGENERATE per capture spec.
9. **Shirt/framing** — navy crew-neck consistency (advisory; mismatch = warning, not gate).
10. **Cross-view impossibility** — any feature consistent in one view but anatomically impossible in another (e.g., mirrored profile anatomy) ⇒ multiview-auditor veto ⇒ REGENERATE/FAIL.

## 3. GLB invariants (absolute mode — no source GLB required)

Applies to any candidate GLB. GEO-02-class source-comparison audits (see §5) may be ADDED for the fallback lane, never replace this.

| # | Invariant | Pass criterion | Tag |
|---|---|---|---|
| G-1 | Triangle count | 1,000 ≤ tris ≤ 2,000,000; outside ⇒ flag (not auto-fail; document per-lane target: visual-hull ≈10k–500k, retopo goal < 100k) | placeholder-needs-calibration |
| G-2 | Watertightness | `trimesh.load(f, force='scene')` → each mesh watertight, winding consistent, **zero zero-area faces**; rigged candidates may list documented intentional openings (eye/mouth interiors) in manifest, else FAIL | justified (AGENTS gate 6; GEO-01/02 both required watertight — necessary, never sufficient) |
| G-3 | Single body | one connected component per mesh unless eyes/hair shells are declared in manifest; else FAIL | placeholder-needs-calibration (exception list untested) |
| G-4 | UVs | `TEXCOORD_0` present on every primitive; no UV island collapsed to a point (diagnostic flag) | justified (structural-compat gate) |
| G-5 | Normals | if `NORMAL` present: max ‖len(n)−1‖₂ ≤ 1e-3; else manifest declares absent and renderer recomputes | justified (technical) |
| G-6 | Finite values | no NaN/Inf in POSITION/NORMAL/TARGETS | justified (technical) |
| G-7 | Embedded textures | if candidate claims textured/photoreal: ≥1 embedded image, materials bound, zero external URIs (or externals listed with SHA-256 in manifest) | justified (self-contained evidence) |
| G-8 | Morphs — **only if claimed** (a visual hull will not have them and is not failed for lacking them) | if claimed: `mesh.extras.targetNames` length == target count per primitive; essential set {`eyeBlinkLeft`,`eyeBlinkRight`,`jawOpen`,`viseme_aa`} present **or** a manifest name-mapping to ARKit-equivalent blink/jaw shapes (name table required); morph POSITION/NORMAL finite; for source-warped (GEO-02) candidates additionally: no collapsed morph (‖Δnew‖ ≥ 0.5·‖Δold‖) and Jacobian det > 0 | justified for fallback path (`geo/audit_morph_fit.py`); **untested as absolute audit — placeholder-needs-calibration** |
| G-9 | Head/neck/shoulder coherence | five standardized renders show: neck joins skull without gap/stump; bust/shoulder framing consistent with reference framing; no floating head; hair does not intersect face/skin | justified (visual-checklist gate; mandatory attached images) |
| G-10 | No intersecting self-geometry | visual at all five angles (hair-vs-skin, brow-vs-lid); optional probes: eyeball/eyelid clearance ≥ 0 in blink poses (Phase 4); co-planar-face detection is **UNVERIFIED tooling** (trimesh does not expose it natively) | placeholder-needs-calibration |
| G-11 | Scene scale sanity | if units are meters: head height ∈ [0.16, 0.34] m (reuses `geo/proxy_fit.py` bound) | justified (technical, reuses repo bound) |
| G-12 | Scene hygiene | node/mesh counts documented; skins count documented (0 visual-hull / >0 rigged); no rigs referencing missing joints (rigged only) | placeholder-needs-calibration |

## 4. Motion QA — PLACEHOLDERS (Phase 4 only, after a candidate wins Phase 3)

Not executable pre-Phase-4; listed so candidates are not "approved" without them. Each pose × five angles = minimum 30 renders; blink left/right separately and combined.

| # | Check | Criterion | Tag |
|---|---|---|---|
| M-1 | Blink 0 / 0.5 / 1.0 | full blink: measured eye-opening height ≤ 10% of rest; no lid–eyeball interpenetration visible; L/R blink displacement symmetry: ratio within 10% (WARN), > 20% (FAIL) | placeholder-needs-calibration |
| M-2 | Jaw open 0.25 / 0.5 / 1.0 | full open: vertical inter-labial gap ≥ 35% of mouth-corner separation; no lip inversion; chin/gonion don't fold the jawline U-shape | placeholder-needs-calibration |
| M-3 | Smile 0.5 / 1.0 | mouth corners displace laterally ≥ 15% of mouth width; lips don't invert; no clown artifact | placeholder-needs-calibration |
| M-4 | Lip closure | viseme at rest: inter-labial gap ≤ 2 px @1086×1448; closure viseme: gap = 0 px ± 1 | placeholder-needs-calibration |
| M-5 | Fold/penetration detection | (a) if morph path: no negative-Jacobian triangles in the deforming region (reuse GEO-02 method); (b) else visual fold check on mandated 4× zoom crops of eye/mouth corners; (c) local normal-inversion in deformed region ⇒ FAIL | placeholder-needs-calibration |

## 5. What existing repo code covers vs what is missing

| Repo artifact | Already covers | Missing vs this gate |
|---|---|---|
| `geo/audit_morph_fit.py` | Source→candidate GLB comparison for the V32/GEO-02 fallback: scene tables, skins/animations/materials/textures/images/samplers/cameras equality, primitive descriptors + morph name/target-count equality, accessor-count equality, topology/indices/JOINTS_0/WEIGHTS_0/TEXCOORD_0 equality, max vertex displacement > 1e-4 (else "no substantive change"), morph collapse check, finite check, **essential set {eyeBlinkLeft, eyeBlinkRight, jawOpen, viseme_aa} presence**, trimesh re-import mesh-count match. Its report self-labels identity/Blender-sync as NOT VERIFIED. | Absolute invariants for from-scratch (image-first visual-hull) candidates — it requires a source GLB and V32-like scene distribution, and hard-codes V32 essential names; no watertightness/manifold/degenerate-face checks, no triangle-count band, no normals unit-length check, no self-intersection check, no UV-content audit (compares TEXCOORD only), no silhouette or landmark metrics, no blink/jaw pose renders, no blind protocol. **Do not run it on a visual hull and call it a pass.** |
| `geo/proxy_fit.py` (silhouette part) | Reusable segmentation rule (border-median bg, distance>26 & chroma>12 \| distance>54); crown/chin manual anchors for exactly three views (front y 55→924, left y 40→980 + ear x=627, right y 34→940 + ear x=425) at 1086×1448 only; 73-sample height profile; median smoothing; LR depth-disagreement metric (documented median 1.33% on the reference set); watertight envelope build; sha256 manifest. Tests in `geo/tests/test_proxy_fit.py` cover synthetic background extraction, thumbnail rejection, sample-count mismatch rejection, closed-hull + repeatability, sides validation, LR-disagreement reporting. | No IoU computation at all (span ratios only); no 45°/back/top anchors; no candidate-render comparison; no segmentation-vs-human calibration; hard-coded anchors invalid for other crops; no hair-strand handling guidance; no scorecard/gate logic; **no mediapipe/manual landmark measurement code**; its `VIEWS` constants are annotation-bound to these exact PNGs (never widen without re-annotation) |
| `tools/local_check.py` | compileall of video/tests/tools; unittest discovery of `tests/` (timeline + portrait preset only); optional `--glb` via `video/model_check.py` (trimesh), `--audio` timeline sanity; pass/fail exit code. Documented as 21/21 PASS (2026-11-11, see strategy doc). | **Does not run `geo/tests`**; no reference-image presence check; no landmark/IoU measurement; no blink/jaw/smile/lip-closure QA; no silhouette or profile analysis; no blind-map enforcement; knows nothing of this gate — it is a smoke test, never evidence of likeness |
| `geo/character001_landmarks.json` | Front-view anchor estimates (used to derive IPD above). | No brow/nose/jaw-angle points beyond eyes/mouth/chin; **no profile annotations; no rig for 10-point canonical set; method is manual-estimate** |
| `geo/tests/` | 21 test functions (3 files): proxy_fit silhouette/topology, morph_fit GLB round-trip/Jacobian/transport/safety, blender_setup **config parsing only** — GEO-01 doc: Blender run "not yet performed"; Blender-JSON/scene logic not validated by an actual Blender process | Real Blender render validation; real GLB invariant audit of a from-scratch candidate; mediapipe-vs-manual landmark agreement harness; controls (self-IoU, jitter canary); blinding/leak tests |
| `docs/characters/C001-GEO-02.md` | Documented: 21/21 geo tests pass (reported), max displacement 6.94 mm, min Jacobian 0.9558, 122 morphs, visual identity **FAILED** | Anything on image-first candidates |

## 6. Measurement protocol (executable)

1. **Preconditions:** evaluation runs in a checkout/worktree containing `assets/characters/character_001/identity_capture_v1/` (gitignored — currently absent from the QA worktree) and the candidate GLB + Blender renders; assert image dimensions are exactly 1086×1448 (or the documented closeup sizes) and recompute reference SHA-256s; compare against the manifest/asset_qa doc; mismatch ⇒ BLOCKED (asset integrity), never proceed.
2. **Tools.** Primary: MediaPipe FaceMesh 1.2.2 (listed by pip for Python 3.14.7 per strategy doc; **NOT installed; install on 3.14.7 UNVERIFIED** — if it installs cleanly, use `refine_landmarks=True` for iris centers; record `mediapipe.__version__`). Fallback / required second method: manual double-click annotation by two independent annotators using any point-picker (matplotlib `ginput`, GIMP measure tool, or a simple HTML canvas labeler); record tool + version + click coordinates; inter-annotator agreement mean ≤ 8 px per point, else flag the point, take the mean, and note it. **Both methods recorded; results cross-reported; disagreement > 10 px mean between methods ⇒ BLOCKED for that candidate pending tooling fix.**
3. **Renders:** blender-render-specialist supplies five angles per candidate (front/±45/±90/back) + the three match views for the gate; resolution exactly 1086×1448; neutral gray; locked lens/framing from `geo/proxy_fit.py` conventions; render paths, Blender version (`C:\Program Files\Blender Foundation\Blender 4.5`, v4.5.x), and camera parameters recorded. QA does not re-render; mismatch between render spec and this protocol ⇒ BLOCKED.
4. **Repetitions.** ≥ 3 independent measurement sessions per candidate (two manual annotators + one mediapipe/manual session on another day, or three manual sessions). Gate evaluates the **pooled** errors and also reports **worst-session**; worst-session FAIL ⇒ candidate FAIL (no cherry-picking the good run). Reference self-segmentation control repeated each session.
5. **Overlays & diffs.** For every required view, save: reference with red ref-points + blue candidate-points overlay; silhouette diff (ref-only in red, cand-only in blue); 4× zoom crops of nose/lips/eyes. Human-auditable evidence is mandatory; numbers without overlays are not accepted by judges.
6. **Report JSON.** Every run writes `output/qa/geo03/<gate_run_id>/<label>/eval.json` (gitignored `output/`) validating against the schema in §9, plus overlays beside it. `gate_run_id` = `<date>-<run>` (e.g. `2026-11-11-geo03-run1`).
7. **Sign-off.** Required for a PASS verdict, recorded in the JSON with role + ISO-8601 UTC timestamp + one-line evidence: (i) identity-auditor — rubric ACCEPT×3 for recognizable claim; (ii) multiview-auditor — cross-view consistency + impossibility veto; (iii) geometry-specialist — GLB invariants §3; (iv) independent-regression-qa — gate arithmetic, controls, blind protocol. Judges and QA must not be the same session that generated the candidate. **Release-integrator only summarizes; never merges.**
8. **Logging.** Every command executed, with exit codes, is copied into the report under `audit_log` (or referenced by path if huge). Anything not actually run is written as `"status": "UNVERIFIED"`.

## 7. Required controls (every gate run)

- **Clean control:** self-IoU(01) = 1.000; self-landmark-control (synthetic 3-px shift ⇒ measured shift ≈ 3 px ± 1) — validates the measurement chain end-to-end.
- **Failure control:** jitter canary — GEO-02 candidate or (if unavailable) a copy of any GLB with 30% of vertices randomly perturbed by ≥5 px-equivalent scale ⇒ landmark gate MUST FAIL it. If the gate passes the canary, the gate is broken ⇒ fix harness, discard all verdicts from the run.
- **Canary:** GEO-02 candidate renders recorded as expected-FAIL canary (identity FAILED per its doc). Recorded as data; a pass here is not a promotion of GEO-02.
- **Label-swap blinding self-test** (§B-5).

## 8. Thresholds — justification & calibration status (consolidated)

**Anchors:** IPD_ref ≈ 212.0 px (§2a); face height anchors (proxy_fit): crown y=55 / chin y=924 ≈ 869 px; eyes y≈526; mouth y≈762; chin ≈ y=924–925. References are uncalibrated AI portraits — **nothing here is scan metrology**; every derived number inherits that caveat.

| Metric | PASS | WARN | FAIL | Justified? |
|---|---|---|---|---|
| Front landmark mean | ≤ 16 px (0.075 IPD) | ≤ 21 px (0.10 IPD) | > 21 px | **placeholder-needs-calibration** (NME-0.05–0.10 rationale; uncalibrated references) |
| Front landmark P95 | ≤ 26 px (0.125 IPD) | ≤ 42 px (0.20 IPD) | > 42 px | placeholder-needs-calibration |
| Front landmark max | ≤ 42 px (0.20 IPD) | ≤ 64 px (0.30 IPD) | > 64 px | placeholder-needs-calibration |
| Front landmark median | ≤ 16 px | ≤ 21 px | > 21 px | placeholder-needs-calibration |
| Profile landmark mean | ≤ 25 px (diagnostic) | ≤ 40 px | > 40 px | placeholder + blocked-until-annotation |
| IoU front | ≥ 0.80 | 0.70–0.80 | < 0.70 | **placeholder-needs-calibration** (lit. ≈0.75–0.85 for weak-perspective multi-view fits; seg noise; no citations fetched — network disabled) |
| IoU profiles (L/R) | ≥ 0.75 | 0.65–0.75 | < 0.65 | placeholder-needs-calibration (references LR depth disagreement ~1.33% documented) |
| IoU 45° advisory | ≥ 0.70 | 0.60–0.70 | < 0.60 | placeholder |
| |IoU_L − IoU_R| | ≤ 0.10 | 0.10–0.15 | > 0.15 flag | placeholder-needs-calibration |
| Segmenter-vs-human mask agreement | ≥ 0.95 | — | < 0.95 ⇒ segmenter fix/BLOCKED | justified-as-method-prerequisite |
| Self-IoU control | = 1.000 | — | < 1.000 ⇒ abort run | **justified (invariant)** |
| Inter-annotator agreement | ≤ 8 px mean | 8–10 px | > 10 px ⇒ BLOCKED | justified (annotation QC practice) |
| Alignment residual RMS | ≤ 20 px | — | > 20 px ⇒ BLOCKED (framing/camera bug) | justified (harness sanity) |
| Tris count | 1k–2M band | — | outside ⇒ flag | placeholder-needs-calibration |
| Watertight / degenerate faces | true / 0 | — | fail | **justified** (AGENTS/GEO-01/02; necessary-not-sufficient) |
| Single body | 1 component (or declared) | — | fail | placeholder-needs-calibration (exceptions untested) |
| UV present / normals ≤1e-3 / finite | pass | — | fail | justified (technical) |
| Morphs (if claimed): names=targets, essentials present or mapped, finite, no collapse | pass | — | fail | justified for GEO-02 fallback (`audit_morph_fit.py`); **placeholder as absolute audit** |
| Head/neck/shoulder coherence | ACCEPT | REFERENCE_ONLY | REGENERATE | justified (visual checklist §2c) |
| M-1…M-5 (blink/jaw/smile/lip/folds) | — | — | — | **all placeholder-needs-calibration; Phase-4-only** |

## 9. Required JSON report schema (every future candidate evaluation)

File: `output/qa/geo03/<gate_run_id>/<label>/eval.json`. Minimal required keys (extra keys allowed; missing required keys ⇒ report invalid ⇒ no verdict):

```json
{
  "protocol_version": "C001_GEO03_BLIND_SCORECARD v1",
  "gate_run_id": "2026-11-11-geo03-run1",
  "candidate_label": "A",
  "git_commit_of_qa_harness": "…",
  "timestamp_utc": "…",
  "status": "PASS|FAIL|BLOCKED|NOT_RUN",
  "recognizable_character_001": false,
  "provenance": {"blinded": true, "glb_sha256": "…", "render_sha256": {"front":"…","…":"…"}, "reference_sha256": {"01_subject_front.png":"…","…":"…"}, "revealed_after_signoff": false},
  "references": {"dimensions_px": {"01_subject_front.png":[1086,1448],"…":[0,0]}},
  "environment": {"python": "…", "os": "…", "blender": "…", "mediapipe": "…|not_installed", "manual_tool": "…"},
  "renders": {"front": "A/front.png", "left_45": "…", "right_45": "…", "profile_left": "…", "profile_right": "…", "back": "…", "resolution_px": [1086,1448], "camera": "…"},
  "alignment": {"method": "similarity", "transform": [[0,0,0],[0,0,0],[0,0,0]], "residual_rms_px": 0.0},
  "landmarks": {
    "front": {"method": "mediapipe|manual|both", "sessions": 3, "points": [{"name":"eye_L","ref_xy":[0,0],"cand_xy":[0,0],"err_px":0.0}], "mean_px":0.0, "median_px":0.0, "p95_px":0.0, "max_px":0.0, "worst_session_mean_px":0.0},
    "profile_left": {"status": "NOT_RUN|MEASURED", "…": "…"},
    "profile_right": {"status": "NOT_RUN|MEASURED", "…": "…"}
  },
  "silhouette": {"segmenter": "border-median distance>26&chroma>12|distance>54", "segmenter_human_agreement": 0.0, "iou": {"front":0.0,"left_profile":0.0,"right_profile":0.0,"left_45_advisory":0.0,"right_45_advisory":0.0}, "lr_asymmetry": 0.0, "controls": {"self_iou_01": 1.0, "reference_04_05_ceiling": 0.0}},
  "glb_invariants": {"triangles": 0, "watertight": true, "winding_consistent": true, "degenerate_faces": 0, "connected_components": 1, "uv_present_all_primitives": true, "normals_max_unit_dev": 0.0, "finite": true, "embedded_images": 0, "external_uris": [], "morph_claim": false, "morph_audit": {"status":"N_A|PASS|FAIL","…":"…"}},
  "motion_qa": {"status": "NOT_RUN", "poses": null},
  "controls": {"jitter_canary": "FAIL|UNEXPECTED_PASS", "geo02_canary": "EXPECTED_FAIL_RECORDED", "label_swap_guess_flag": false},
  "blinding": {"sealed_map_sha256": "…", "bundle_whitelist_ok": true, "leak_events": [], "judges": [{"role":"identity-auditor","label_front":"ACCEPT","label_left_profile":"ACCEPT","label_right_profile":"ACCEPT","checklist_evidence": ["…"], "signed_utc": "…"}, {"role":"multiview-auditor","…":"…"}], "disagreement_resolution": "stricter-label|user-arbitrated|n_a"},
  "signoffs": {"identity_auditor": "ACCEPT|…", "multiview_auditor": "ACCEPT|…", "geometry_specialist": "PASS|FAIL", "independent_regression_qa": "PASS|FAIL|BLOCKED"},
  "verdict": {"status": "PASS|FAIL|BLOCKED", "failures": ["…"], "warnings": ["…"]},
  "audit_log": [ {"cmd": "…", "exit_code": 0} ]
}
```

## 10. Explicit non-claims

- This document never certifies likeness. A PASS means only "within the calibrated tolerances of §2 and all §3 invariants, with blinded human sign-off"; it is not a scan, not identity proof, not "photoreal", and never a merge authorization.
- Watertightness/single-body/UV/finite checks are necessary hygiene; they say nothing about identity.
- GEO-01's envelope and GEO-02's fitted V32 remain fallback-only; neither is evidence for GEO-03 likeness. GEO-02's documented visual-identity FAILURE stands until a calibrated gate run says otherwise.
- Statuses stay distinct: a candidate may be `rendered` and `unit-tested` while `visually_approved = false` forever. Do not promote.

## 11. Provenance of this document / environment honesty

- Authored 2026-11-11 by independent-regression-qa in the QA worktree (agent lacked write tools; coordinator persisted this file verbatim). detached HEAD 31a9b19.
- **UNVERIFIED (not executed by the QA agent — no shell in its environment):** `python -m unittest discover -s geo/tests -v` (docs report 21/21 PASS; coordinator independently ran it 2026-11-11 after `pip install trimesh` → **21/21 OK**); `python tools/local_check.py` (coordinator ran it 2026-11-11 → **PASS, 21/21**); MediaPipe install on Python 3.14.7; any Blender render; reference-image pixel-dimension re-measure (documented 1086×1448 trusted; asset-curator independently measured all 15 on 2026-11-11); any candidate (none exists); any IoU/landmark measurement; any control run.
- **Blockers for the first gate run:** profile landmark annotations missing; mediapipe install unverified; segmenter-vs-human calibration unmeasured; candidate-render camera spec not yet locked by blender-render-specialist; blind bundle tooling not built; jitter canary not implemented.
