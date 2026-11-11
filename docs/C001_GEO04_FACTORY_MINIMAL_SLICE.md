# C001-GEO-04 — Character Factory minimal slice (implementable now)

**Status:** PROPOSED work plan. Nothing here is implemented by this document; no application source is modified by it.
**Authority:** `docs/C001_GEO04_FACTORY_INTERFACE.md` (v1.0) and ADR-C001-004 decision 7.
**Constraint that shapes everything:** Phase-3 is **FAIL**. This slice must be landable while the geometry gate is unresolved, so it is **purely additive**: new files only, no edits to existing pipeline code, no behaviour change to any existing command.

---

## 1. Decision

**Implement a schema/validator library plus a read-only audit, and nothing else.**

New package `character_factory/` (pure-stdlib) plus one read-only audit tool. It validates the factory documents described in the interface contract; it does not run, reorder or reinterpret any geometry, and it does not touch `geo/`, `video/` or the reconstruction path.

### Rationale

1. **The contract is only useful if something can check it.** v0.1 (§7.1) already says the factory CI is "local_check + geo tests + calibration/landmark tests + a synthetic manifest/license check (to be written in F1; **UNVERIFIED, not implemented**)". A validator + synthetic fixtures is precisely that missing piece, and it is the cheapest way to make "versioned per-character asset manifests" a fact rather than a paragraph.
2. **A validator cannot make a likeness claim, so it cannot muddy the FAIL.** It reads and checks documents; it never produces geometry, never touches a GLB, never renders. Its blast radius if buggy is a red test, not a wrong candidate.
3. **The alternatives are all worse right now.** Wiring a backend adapter (§6 of the contract) would require touching the reconstruction path that is under repair (worktree `livynth-c001-geo04-repair`) and the gate path (`livynth-c001-geo04-gate`) — three lanes in flight, one geometry pipeline. A shared-character directory migration would move files that in-flight lanes depend on. Both are explicitly forbidden by v0.1 §3.3 and by the ADR's "no cross-repository refactor while Phase-3 FAIL is unresolved".

### Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Implement S3 backend adapters now | Touches the failing geometry pipeline; three lanes already in flight; ADR decision 2 authorises exactly **one** bounded repair experiment, not adapter infrastructure. |
| Migrate to `characters/<char_id>/` now | v0.1 §3.3 defers it until the Phase-3 gate passes; moving files breaks in-flight worktrees. |
| Build the Character 002 pack now | There is no Character 002 identity seed pack (ADR open decision 8); fabricating one would be a synthetic-identity claim. |
| YAML config authoring | PyYAML is not installed and installs are unauthorised; validators must be stdlib-only to run on the baseline machine. |
| A single `tools/factory_check.py` script with no library | Would not be importable by the future stage code, and would not be unit-testable per-schema. A library is the same effort and is reusable. |
| Rename the legacy schema ids now | They are written into existing artefacts; renaming breaks readers and comparability. DEFERRED (contract §11 item 5). |

---

## 2. What is explicitly EXCLUDED

Not in this slice, in any form:

- reconstruction, retopology, rigging, morph transfer, texture baking, hair, eyes, wardrobe, rendering, Blender invocation, lip-sync, phoneme alignment;
- any change to `geo/visual_hull.py`, `geo/proxy_fit.py`, `geo/morph_fit.py`, `geo/calibration_spec.py`, `geo/landmark_spec.py`, `geo/detect_landmarks.py`, `geo/detect_one.py`, `geo/audit_morph_fit.py`, `geo/setup_blender_fit_scene.py`, `geo/manual_annotations.py`, `geo/migrate_legacy_landmarks.py`, any `geo/tests*`, any `video/*.py`, `tools/gate_*.py`, `tools/build_blind_bundle.py`, `tools/landmark_gate.py`, `tools/head_iou.py`, `tools/camera_probe.py`, `tools/render_hull*.py`, `tools/score_variant.py`;
- any change to the gate semantics, the threshold set, or the blind scorecard;
- any network access, account creation, model download, licence acceptance or upload;
- any new dependency, and any import of numpy/trimesh/Pillow from the new package.

---

## 3. Work units

Every unit below is **new files only**. Effort is engineer-days and excludes review.

### W1 — `character_factory/` package skeleton and canonical JSON

- **Files (new):** `character_factory/__init__.py`, `character_factory/canonical.py`
- **Interface:** `canonical_bytes(obj) -> bytes` (sorted keys, compact separators, UTF-8, no trailing newline); `content_sha256(obj, semantic_keys) -> str` (digest over the semantic subset only, contract D-SCHEMA-5); `sha256_file(path) -> str`.
- **Tests:** `character_factory/tests/test_canonical.py` — key order independence; whitespace independence; the semantic subset excludes `created_utc`/`generator`/`notes`; a note-only edit does **not** change the digest; a field change does; the digest is 64 lowercase hex.
- **Risk:** none. No I/O beyond reading a file to hash; no imports beyond `hashlib`/`json`.
- **Safe now because:** it cannot influence any existing command; a bug is a failing unit test in a new package.

### W2 — schema registry and versioning rules

- **Files (new):** `character_factory/registry.py`
- **Interface:** the registry of families → current version; `read_document(path) -> (schema, schema_version, payload)` with the D-SCHEMA-3 legacy-alias handling for the v0.1 slash form; `check_compatibility(family, version) -> list[str]` implementing D-SCHEMA-2 (same-major + MINOR ≤ reader ⇒ ok; different major ⇒ `E_SCHEMA_MAJOR`; higher minor ⇒ `E_SCHEMA_MINOR_AHEAD`).
- **Tests:** `character_factory/tests/test_registry.py` — alias `livynth.factory.refpack/1` resolves to v1.0.0; a different major is rejected with the right code; a higher minor is rejected with the right code; a lower minor is accepted; an unknown family is rejected; an emitted document never uses the slash form.
- **Risk:** low. The risk is *choosing* a family name that later has to change — mitigated by keeping the family list to the four in the contract and by the registry being the single place a name is written.
- **Safe now because:** pure data + pure functions.

### W3 — refpack validator

- **Files (new):** `character_factory/refpack.py`
- **Interface:** `validate_refpack(doc) -> list[str]` returning error codes from the §7.2 taxonomy (never raising for data errors; raising only on a non-object input). Enforces: const `schema`/`schema_version`; required keys present; unknown keys rejected except `x_*`; exactly one `role=="front"`; unique `view_id`/`file`; `file` contains no path separator and no character identifier; every `view_id` in the canonical §2.1 set; camera labels in the four-label set; **`label_intrinsics != "MEASURED"` while `truth.calibrated == false`**; landmark `calibrated == false`; `consistency_audit.inadmissible_for` contains `"identity_claim"` unless the verdict is `PASS_as_appearance_reference`.
- **Tests:** `character_factory/tests/test_refpack.py` — a valid synthetic Character-001-shaped pack passes; each rule has a negative fixture (two fronts; a duplicated view id; a path separator in a filename; `character_001` in a filename; `label_intrinsics="MEASURED"` with `calibrated=false`; an unknown key; a missing key; a wrong schema_version; a verdict of `FAIL_SfM` without `"identity_claim"` in `inadmissible_for`; a landmark file with `calibrated: true`).
- **Risk:** medium-low — this is the schema most likely to be wrong about the real pack. Mitigation: the fixtures are **synthetic**; the real Character 001 pack is used only as an *optional* integration fixture that skips when the assets are absent (the same skip pattern `geo/tests_calibration/test_calibration_spec.py` already uses via `LIVYNTH_MAIN_REPO`). A real-pack failure must not be papered over with an exception.
- **Safe now because:** reads a JSON document; writes nothing; runs no geometry.

### W4 — character config validator

- **Files (new):** `character_factory/character.py`
- **Interface:** `validate_character(doc) -> list[str]`. Enforces: const schema/version; `caps.texture_max_px == 2048` unless a justification block naming the four ADR decision-6 gates is present; `scale_priors.label != "MEASURED"` while `truth.calibrated == false`; `head_height_m` a 2-element ascending range inside [0.16, 0.34]; every `qa_overrides` entry carries non-empty `justification` and `approved_by`; `truth` matches the referenced refpack (when both documents are supplied); a widened threshold requires the justification, otherwise `E_OVERRIDE_UNJUSTIFIED`.
- **Tests:** `character_factory/tests/test_character.py` — the contract's own example config passes; texture 4096 without justification is rejected; texture 4096 with the four gates named passes; a scale prior labelled MEASURED with `calibrated=false` is rejected; an out-of-range head height is rejected; an override without justification is rejected; an override with justification passes; truth mismatch between config and refpack is rejected.
- **Risk:** low-medium. The 4096 exception is a judgement call; it is implemented as "a named four-gate list must be present", not as a free-text escape.
- **Safe now because:** document-only.

### W5 — backend adapter contract types + decline semantics

- **Files (new):** `character_factory/backend.py`
- **Interface:** pure-stdlib dataclasses + validators for `livynth.factory.backend.request` / `.response` / `.capabilities`; closed enums for status, decline reasons, failure codes, execution tiers, device names; `classify_backend_outcome(responses) -> str` implementing D-BACKEND: `ok` if ≥1 candidate; `degraded` if all responded but ≥1 declined; `blocked` if every enabled backend declined and ≥1 was required; never `failed` for a decline.
- **Tests:** `character_factory/tests/test_backend.py` — one ok + one declined ⇒ `degraded`, not failed; all declined ⇒ `blocked`; a failed backend is distinct from a declined one; an unknown decline reason is rejected; an unknown execution tier is rejected; a request whose image sha256 does not match the refpack is rejected; a request with `license_acceptance.required && !granted` is rejected.
- **Risk:** medium — this is the most "spec-like" unit and is the one most likely to be re-shaped once a backend exists. Mitigation: it is a *contract type*, not an execution harness; no backend is implemented or invoked.
- **Safe now because:** it validates documents and classifies outcomes. No backend is called.

### W6 — provenance record + diffable canonical form

- **Files (new):** `character_factory/provenance.py`
- **Interface:** `validate_provenance(doc) -> list[str]`; `diff_provenance(a, b) -> list[dict]` returning field-level differences between two records so two runs can be compared without a human diff.
- **Tests:** `character_factory/tests/test_provenance.py` — a valid record passes; `commands` empty with a non-`planned` status is rejected; a command missing its exit code is rejected; `source.commit` not 40 hex is rejected; `known_failure_modes` empty with status FAIL is rejected; `inputs` missing the refpack digest is rejected; two records differing only in ordering compare equal; `diff_provenance` reports a changed artifact sha256.
- **Risk:** low.
- **Safe now because:** document-only.

### W7 — QA report validator and the gate arithmetic

- **Files (new):** `character_factory/qa.py`
- **Interface:** `validate_qa(doc) -> list[str]`; `compute_gate_valid(doc) -> (bool, list[str])` implementing D-QA-1 exactly; `admissibility_map(doc) -> dict`; a check that a PASS verdict requires `gate_valid` **and** every `admissible_for_acceptance` metric passing **and** rubric ACCEPT on front/profile_left/profile_right (D-QA-2, D-QA-3).
- **Tests:** `character_factory/tests/test_qa.py` — the Phase-3 run-1 shape (self-IoU ok, jitter canary **accepted**, wrong-identity canary not rejected) yields `gate_valid == false` and `status == "BLOCKED"`, never PASS; a report whose `admissibility` marks a gate-view appearance metric as admissible is rejected; a PASS with a missing sign-off is rejected; a FAIL with a rejected profile is accepted as a FAIL verdict; a rubric disagreement resolves to the stricter label.
- **Risk:** medium — this encodes the central rule of the whole programme. Mitigation: the tests are written **from the measured Phase-3 run-1 numbers** (self-IoU 1.000000; jitter canary IoU 0.9036 / landmark 8.92 px — not rejected; wrong-identity 1.18× canary — not rejected), so the validator demonstrably reproduces the historical BLOCKED outcome rather than asserting it abstractly.
- **Safe now because:** it reads a report and computes a boolean. It cannot pass a candidate.

### W8 — hardcoding audit tool (read-only) + baseline

- **Files (new):** `tools/character_audit.py`, `character_factory/tests/test_character_audit.py`, and a baseline data file `character_factory/audit_baseline.json` (tracked; lists the currently accepted offending identifiers per file).
- **Interface:** `python tools/character_audit.py [--json out.json] [--base <sha>]`; exit 0 if the offending set did not grow, exit 1 if it grew or if a baseline entry disappeared without acknowledgement. Uses `git grep`-equivalent behaviour over **tracked** files only.
- **Pattern:** the audit MUST use the full three-class pattern from the interface contract §10.4 (identifiers + emitted schema ids + hardcoded reference filenames). A pattern that omits the filename class under-reports by roughly half (measured: 47 vs 95 lines in `geo`).
- **Baseline to record (measured 2026-11-11 at feature-branch tip `59f4628`, matching lines):** `geo/**/*.py` = 95, `tools/*.py` = 9, `video/*.py` = 0, `tests/**/*.py` = 0. The ADR-canonical identifier subset alone gives `geo` = 35, `tools` = 4. **Re-measure on the rebased tree before recording the baseline** — the counts move with the feature branch.
- **Tests:** a synthetic repo fixture with one new offender ⇒ exit 1; with the same offenders as the baseline ⇒ exit 0; with one baseline entry removed ⇒ exit 1 (progress must be acknowledged). Follows the `tests/test_branch_audit.py` precedent exactly.
- **Risk:** medium — a false "clean" would be dangerous, and a false "dirty" would be noisy. Mitigation: it is an **audit report**, not a correctness gate; it is not wired into `tools/local_check.py` in this slice (that is W9); the baseline is generated from the measured working tree and reviewed.
- **Safe now because:** it is read-only and writes only its own report file.

### W9 — (optional, separately gated) repo test-suite discovery

- **Files (new):** none. **Edit (exactly one line) to an existing file:** `tools/local_check.py` — add a discovery run for the new package's tests.
- **Rationale:** the repo already fixed exactly this gap once ("make every geometry suite discoverable", commit `6e7e2e7`), and `tests/test_local_check_discovery.py` asserts that a single discovery command reaches every suite directory. Leaving the new tests unreachable would repeat the defect that commit closed.
- **Why it is separated:** it is the only edit to an existing file in the whole slice, so it is isolated for review and can be dropped without affecting W1–W8.
- **Risk:** low — additive discovery only; no existing command changes behaviour. The discovery command must use the same form as the existing one (`discover -s <dir> -t . -p "test_*.py"`) so the new suite is found exactly like the geo suites.

---

## 4. Dependency DAG

`@
        W1 canonical
             |
        W2 registry
           /     \
    W3 refpack   W4 character
          \      /
           W5 backend      (needs W2 only)
             |
        W6 provenance      (needs W1 only)
             |
          W7 qa            (needs W1, W2; reads the same canonical form)
             |
        W8 audit           (needs W1 only)

        W9 discovery       (needs W1-W8 all landed)
`@

**Parallel-safe groups** (no shared file, no shared contract):
- **{W3, W4, W6, W8}** after W2 — four independent modules.
- **{W5, W7}** after W2 — independent of each other.
- **W9** only after everything else.

**Serialization constraints:** W1 → W2 is absolute (everything imports the canonical form). W3 must land before W4 if the truth-consistency check is to be exercised against a real refpack fixture (it can be developed in parallel with a stub).

---

## 5. Module ownership and collision risk

| Unit | Owns (new files) | Touches existing files |
|---|---|---|
| W1 | `character_factory/canonical.py` | none |
| W2 | `character_factory/registry.py` | none |
| W3 | `character_factory/refpack.py` | none |
| W4 | `character_factory/character.py` | none |
| W5 | `character_factory/backend.py` | none |
| W6 | `character_factory/provenance.py` | none |
| W7 | `character_factory/qa.py` | none |
| W8 | `tools/character_audit.py`, baseline | none |
| W9 | — | `tools/local_check.py` (one line) |

**Collision risks with in-flight lanes.** Other GEO-04 lanes exist (worktrees `livynth-c001-geo04-repair`, `livynth-c001-geo04-gate`, `livynth-c001-geo04-gate-2`, `livynth-c001-geo04-topology`, `livynth-c001-geo04-research` / `-2`, and the earlier `livynth-character-factory`).

| Risk | Assessment | Mitigation |
|---|---|---|
| Another lane creates `character_factory/` | Low — the package name is new and unclaimed at base `b0235c1` | the coordinator assigns the name before dispatch |
| Another lane edits `tools/local_check.py` | **Real** — the gate lane may add its own discovery line | W9 is the only edit and is last; rebase before applying |
| Another lane writes `docs/C001_GEO04_*.md` | Medium — `C001_GEO04_FLANE_RESEARCH.md`, `_LICENCE_MATRIX.md`, `_ATTRIBUTION_DRAFT.md` already exist | this lane uses the distinct names `C001_GEO04_FACTORY_INTERFACE.md` / `C001_GEO04_FACTORY_MINIMAL_SLICE.md` |
| Another lane creates a refpack schema | Low — no such schema exists at base | the interface contract pins the family names first |
| The audit tool's findings are read as a Phase-3 verdict | Medium — an audit of hardcoding could be misread | the tool's output says explicitly that it is not a quality gate |
| Another lane runs the audit and disagrees with the baseline | Medium — the baseline is a snapshot of a moving branch | the baseline is regenerated on the rebased tree and reviewed; the ratchet only fails on *growth* |

---

## 6. Implementation order and effort

| # | Unit | Depends on | Effort | Parallel group |
|---|---|---|---|---|
| 1 | W1 canonical JSON + digest | — | 0.25 d | — |
| 2 | W2 registry + versioning | W1 | 0.5 d | — |
| 3 | W3 refpack validator | W2 | 1.0 d | A |
| 4 | W4 character config validator | W2 | 0.75 d | A |
| 5 | W5 backend contract types | W2 | 1.0 d | B |
| 6 | W6 provenance validator + diff | W1 | 0.75 d | A |
| 7 | W7 QA validator + gate arithmetic | W2 | 1.25 d | B |
| 8 | W8 hardcoding audit + baseline | W1 | 1.0 d | A |
| 9 | Review + regenerate baseline on the rebased tree | 1–8 | 0.5 d | — |
| 10 | W9 discovery wiring (optional, gated) | 1–8 | 0.25 d | — |

**Total ≈ 8.25 engineer-days**, of which W9 is 0.25 d and optional. Groups A and B can run concurrently, so calendar time ≈ 4.5–5 working days with two engineers, ≈ 8 days with one.

**Effort is engineering time only.** None of it may be scheduled on the GPU, none of it needs Blender, and none of it needs a free RAM margin — it is stdlib-only Python, so it runs on the baseline machine with no installs.

---

## 7. Acceptance criteria for the slice

| ID | Criterion | How it is checked |
|---|---|---|
| **AS-1** | All new tests pass | `python -m unittest discover -s character_factory -t . -p "test_*.py" -v` exit 0 |
| **AS-2** | The existing repo suites are untouched and still green | `python -m unittest discover -s tests -v` and `python -m unittest discover -s geo -t . -p "test_*.py"` exit 0; no existing test file modified (`git diff --name-only` over `tests/` and `geo/` is empty) |
| **AS-3** | No existing pipeline file is modified except the optional one-line discovery | `git diff --stat <base>..HEAD` lists only new files under `character_factory/`, `tools/character_audit.py`, and (if W9 is approved) `tools/local_check.py` |
| **AS-4** | No new dependency | the new package imports only the stdlib; `grep -n "^import |^from " character_factory/*.py` shows no third-party module |
| **AS-5** | The validators reject bad documents | the negative fixtures above; each rule has at least one failing case |
| **AS-6** | The QA validator reproduces the historical Phase-3 outcome | the run-1 fixture yields `gate_valid == false` and `status == "BLOCKED"` |
| **AS-7** | The audit does not report growth | `python tools/character_audit.py` exit 0 on the current tree; exit 1 on the synthetic fixture |
| **AS-8** | No likeness, geometry or quality claim is made | grep of the new package + docs for `recognisable`/`recognizable`/`photoreal`/`PASS` returns only the D-QA-3 rule text and the verdict enum |
| **AS-9** | No network, account, download or upload | the new package has no `urllib`/`requests`/`socket`/`subprocess` import |
| **AS-10** | Documentation matches the code | the interface contract's §4–§7 field lists are cross-checked against the validators' required-key sets by a test that reads the contract's example JSON |

---

## 8. Rollback

- Every unit is additive. Rollback = `git revert <commit>` per unit, or `git rm -r character_factory/` + `git rm tools/character_audit.py` + revert the one-line `local_check.py` change. No existing behaviour depends on any of it, so revert order does not matter.
- The baseline file `character_factory/audit_baseline.json` is tracked and versioned; reverting W8 restores the previous baseline exactly.
- **Rollback risk:** a revert of W9 alone leaves the new tests unreachable (harmless); a revert of W8 alone leaves the baseline orphaned (harmless). No revert can affect a running gate, because the slice adds no runtime dependency to any existing command.

---

## 9. Open questions for the owner

1. **Package name.** `character_factory/` is proposed. `factory/` collides with the installed PyPI package of the same name; `livynth_factory/` is the alternative. The name appears in every import path, so it should be chosen once, now.
2. **YAML authoring.** Deferring it (contract D-SCHEMA-7) is a scope reduction relative to v0.1 §3.1/§6. Approving a PyYAML install would restore it; the alternative is a JSON-only authoring convention with an editor-side fold.
3. **Discovery wiring (W9).** Approve the one-line edit to `tools/local_check.py`, or leave the new suite reachable only by an explicit command?
4. **Audit baseline acceptance.** The baseline must be reviewed and signed, since it encodes "these offenders are tolerated for now". Should the owner set the baseline, or should the tool's first output be committed as a proposal?
5. **Whether the audit should also cover `video/` and `tests/`.** Measured: `video/` is clean (0) and `tests/` is clean (0) today. Covering them costs nothing and prevents regression, so the recommendation is yes.
6. **Character 002 seed pack** (ADR open decision 8) is still required before A2-01 can run; the slice does not depend on it.

---

## 10. Source anchors

Interface contract: `docs/C001_GEO04_FACTORY_INTERFACE.md` (this branch).
ADR: `docs/decisions/ADR-C001-004-phase3-repair.md`.
Base spec: `docs/CHARACTER_FACTORY_SPEC.md` v0.1 §7.1 (the "synthetic manifest/license check … UNVERIFIED, not implemented" gap this slice closes).
Precedent for W8/W9: `tools/branch_audit.py`, `tests/test_branch_audit.py`, commit `6e7e2e7` ("make every geometry suite discoverable"), `tests/test_local_check_discovery.py`.
Phase-3 numbers used by the W7 fixtures: `docs/C001_GEO03_EXPERIMENT_LOG.md` §G9/G10; `docs/C001_GEO03_BLIND_SCORECARD.md` §7/§9.
Hardcoding baseline: measured 2026-11-11 over tracked `*.py` at feature-branch tip `59f4628` — geo 95, tools 9, video 0, tests 0 (see interface contract §10.3).
Branch base: `b0235c152ff18162428d2e8ae8d7fe893f4f591a`. Feature-branch tip when written: `59f4628954893622be60d7a0428b400a0adadbaf` — **behind**: rebase and re-measure the audit baseline before review.
