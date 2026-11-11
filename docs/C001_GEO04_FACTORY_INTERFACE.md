# C001-GEO-04 — Character Factory interface contract (v1.0)

**Status:** PROPOSED — refines `docs/CHARACTER_FACTORY_SPEC.md` (v0.1) into a machine-checkable, versioned interface contract under ADR-C001-004 decision 7.
**Authority:** `AGENTS.md` > `docs/decisions/ADR-C001-004-phase3-repair.md` > `docs/C001_GEO03_STRATEGY.md` > this document > `docs/CHARACTER_FACTORY_SPEC.md`.
**Scope:** interface only. No reconstruction, rigging, rendering or lip-sync behaviour is defined or changed here.
**Phase-3 status:** FAIL. Nothing in this document asserts a likeness, and no clause here may be cited as evidence about any candidate.
**Author:** architecture agent (read-only design), branch `experiment/c001-geo04-factory`, base commit `b0235c152ff18162428d2e8ae8d7fe893f4f591a`.

---

## 0. Relationship to the existing v0.1 spec (what is kept, what changes)

`docs/CHARACTER_FACTORY_SPEC.md` is **not** replaced. It already specifies the right skeleton, and this contract keeps it:

| v0.1 section | Verdict in this contract |
|---|---|
| §3 per-character directory layout (`characters/<char_id>/`) | **KEPT.** Path layout is unchanged; only the file *format* is pinned below. |
| §4 stage envelope `{schema, schema_version, run_id, char_id, stage, inputs[], config_sha256, command, exit_code, started_utc, finished_utc, status, artifacts[], failures[]}` | **KEPT**, and given a strict schema id + status vocabulary (§4.1). |
| §4 S0–S8 stage table | **KEPT**, extended with per-stage failure codes, degraded-but-admissible rules and downstream blocking (§7). |
| §5 `CandidateManifest` + backend registry | **KEPT as the response side** of the adapter contract; the *input* side, capability declaration and decline protocol are **ADDED** (§6). |
| §6 `config/character.yaml` | **KEPT as the authoring intent**, but the machine-checkable form is JSON (§5.1, D-SCHEMA-7). |
| §7 automation / local CI | **KEPT**; the factory slice is wired into the repo gate as a separately-gated step (minimal-slice doc, W9). |
| §8 runtime tiers | **KEPT** and used verbatim as the adapter `execution_tier` enum (§6.2). |
| §9 video integration contract | **KEPT, unchanged, OUT OF SCOPE** for this lane. |
| §11 Character 002 acceptance test | **KEPT and restated** against this contract in §9. |
| §3.1/§6 YAML file extensions | **CHANGED** — see D-SCHEMA-7. |
| §3.1 `"schema":"livynth.factory.refpack/1"` id form | **CHANGED** — see D-SCHEMA-1/D-SCHEMA-3. |

**Deltas introduced by this contract (7):** D-SCHEMA-1..7 (§4.1), D-BACKEND (§6.3), D-FAIL (§7.2), D-QA (§6.5), D-PROV (§6.4), D-MIG (§8), D-AUDIT (§10).

---

## 1. What this contract is, and what it is not

It is a **set of JSON documents with validated shapes** plus the rules for versioning them. A validator is the enforcement mechanism: a document that does not validate is not a factory artefact, and no downstream stage may consume it.

It is **not**:
- a pipeline implementation (no stage is implemented by this contract);
- a claim that any backend exists, runs, or produces a likeness;
- a licence verification (see `docs/C001_GEO04_LICENCE_MATRIX.md` §6, 18 unresolved items);
- a relaxation of the Phase-3 gate. Where this contract and ADR-C001-004 disagree, **ADR-C001-004 wins** and the disagreement is recorded here, not silently resolved.

---

## 2. Vocabulary

| Term | Meaning |
|---|---|
| **factory document** | Any JSON file validated against one of the schemas in §4. |
| **semantic subset** | The keys of a document that participate in its content digest (§4.1, D-SCHEMA-5). |
| **admissible** | A stage output that may be consumed by the next stage despite a recorded degradation (§7.3). |
| **diagnostic-only** | A metric that is measured and reported but may never contribute to a PASS (§6.5). |
| **refpack** | The per-character reference-capture manifest (§4.2). |
| **backend** | A pluggable reconstruction implementation behind the adapter contract (§6). |

### 2.1 Canonical view-id vocabulary

Three partial vocabularies already exist in the repo. This contract declares **one canonical set** — the one already enforced by a validator with 32 tests — and requires explicit translation at each boundary.

| Source | Vocabulary | Status |
|---|---|---|
| `geo/landmark_spec.py` `KNOWN_VIEW_IDS` | `front, left_45, right_45, profile_left, profile_right, back, top, front_closeup, left_ear, right_ear, eyes_closeup, iris_macro, skin_macro, lips_closeup, hair_closeup` | **CANONICAL** |
| `geo/detect_landmarks.py` `VIEW_MANIFEST` | filename → canonical view id | **CANONICAL** (filename→id map; the filenames move into the refpack) |
| `geo/calibration_spec.py` `MAIN_VIEW_GEOMETRY` | `"01".."08"` ids + labels derived from the filename | **LEGACY** — translate via §2.2 |
| `geo/visual_hull.py` `VIEWS` | `front, left45, right45, left90, right90, back, top` | **LEGACY** — translate via §2.2 |
| `geo/proxy_fit.py` `VIEWS` / `FRAMES` | `front, left, right` | **LEGACY** — translate via §2.2 |

**Why this set:** `geo/landmark_spec.py` is the only one of the three that is a *validated schema* (strict unknown-point rejection, per-view `image_sha256` pinning, `unmapped_points`). A factory manifest must be able to carry the same guarantees, so it must speak the same ids.

### 2.2 Translation table (mandatory at every boundary)

| Canonical view id | calibration_spec id / label | visual_hull key | proxy_fit key | asset_qa role |
|---|---|---|---|---|
| `front` | 01 / front | front | front | ACCEPT — canonical identity anchor |
| `left_45` | 02 / left45 | left45 | — | ACCEPT |
| `right_45` | 03 / right45 | right45 | — | ACCEPT |
| `profile_left` | 04 / left_profile | left90 | left | ACCEPT |
| `profile_right` | 05 / right_profile | right90 | right | ACCEPT |
| `back` | 06 / back | back | — | ACCEPT |
| `top` | 07 / top | top | — | REFERENCE ONLY (head bowed; not true overhead) |
| `front_closeup` | 08 / front_closeup | — | — | REFERENCE ONLY (bust portrait; identity drift) |
| `left_ear` | — | — | — | ACCEPT |
| `right_ear` | — | — | — | ACCEPT |
| `eyes_closeup` | — | — | — | ACCEPT |
| `iris_macro` | — | — | — | REFERENCE ONLY |
| `skin_macro` | — | — | — | REFERENCE ONLY |
| `lips_closeup` | — | — | — | ACCEPT |
| `hair_closeup` | — | — | — | REFERENCE ONLY |

Not in the table ⇒ the legacy module has no equivalent. A refpack image whose canonical view id has no legacy mapping is **additive** and must not break any legacy consumer.

---

## 3. Roles required of a refpack

| Role set | Members | Used by |
|---|---|---|
| **identity_anchor** | exactly one, `front` | identity claim; the *only* view allowed to anchor a likeness claim |
| **required_for_reconstruction** | front, left_45, right_45, profile_left, profile_right, back, top | S3 backends; a pack missing any of these is **incomplete** |
| **optional_detail** | front_closeup, left_ear, right_ear, eyes_closeup, iris_macro, skin_macro, lips_closeup, hair_closeup | S6 material/hair/eye work only |
| **gate_views** | front, profile_left, profile_right | S4 blind gate (per scorecard §2) |
| **advisory_views** | left_45, right_45, back, top, + all detail | S4 advisory; may only veto via geometry-impossibility |

---

## 4. Versioning, compatibility and invalidation

### 4.1 Rules

**D-SCHEMA-1 — identity vs version.** Every factory document carries two fields:
- `schema`: stable dotted identifier, never carries a version. Form: `livynth.factory.<family>`.
- `schema_version`: semver `MAJOR.MINOR.PATCH` of the *payload*.

This follows the newest convention already in the repo (`geo/landmark_spec.py`: `schema="livynth.c001.landmarks"` + `schema_version="2.0.0"`; `geo/calibration_spec.py`: `schema_version="1.0.0"`). It supersedes the v0.1 slash form.

**D-SCHEMA-2 — compatibility window.** A reader of family *F* at version *V*:
- MUST accept `schema_version` with the same MAJOR and MINOR ≤ V.MINOR;
- MUST accept any PATCH;
- MUST **reject** a different MAJOR with error code `E_SCHEMA_MAJOR`;
- MAY reject a higher MINOR (this repo's validators reject unknown keys, so a newer MINOR can add keys the older reader would reject) with `E_SCHEMA_MINOR_AHEAD`.

Semver obligations on the writer: MINOR = additive (new optional key only); MAJOR = any removed/renamed/retyped key, or changed meaning of an existing key, or a changed enum domain that existing consumers may not tolerate.

**D-SCHEMA-3 — legacy alias (read only).** The v0.1 draft form `livynth.factory.<family>/1` is accepted on read as an alias for `livynth.factory.<family>` v1.0.0. It is **never emitted**. Alias handling is confined to one function per family so it cannot leak.

**D-SCHEMA-4 — strictness.** Validators reject unknown top-level keys (`E_SCHEMA_UNKNOWN_FIELD`), matching `geo/landmark_spec.py` behaviour. Keys beginning `x_` are reserved for extensions and are ignored by validators, so a future experimental key never breaks an old reader.

**D-SCHEMA-5 — canonical form and content digest.**
- Canonical JSON: `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)`, UTF-8, no trailing newline.
- `content_sha256` = SHA-256 of the canonical bytes of the **semantic subset** only.
- Semantic subset excludes: `created_utc`, `generator`, `notes`, `x_*`. Re-serialising a manifest without changing its meaning therefore does **not** invalidate it.

**D-SCHEMA-6 — what invalidates a refpack.** The refpack is *invalidated* (must be regenerated and re-validated; downstream artefacts pinned to the old digest become detectably stale) when any of these change:
1. any image `sha256`;
2. any image `width_px` / `height_px`;
3. the view-id set or the view-id→role mapping;
4. any camera-assumption **status label** (an ASSUMED→MEASURED promotion invalidates);
5. the pinned landmark set reference (path or sha256);
6. any `truth` field (`calibrated`, `scan`, `ai_generated`) or the licence/consistency-audit verdict;
7. `char_id`.
Not invalidating: key order, whitespace, `notes`, `created_utc`, addition of a detail view that no role set requires, or a re-ordering of the image array.

**D-SCHEMA-7 — format.** The machine-checkable form of every factory document is **JSON**. The v0.1 spec names YAML files (`character.yaml`, `qa_overrides.yaml`, `backends.yaml`). **PyYAML is not installed on this machine** (measured package list: numpy 2.5.3, scipy 1.18.1, trimesh 5.2.0, Pillow 12.3.0, scikit-learn, onnxruntime 1.29.0, huggingface_hub, psutil, torch 2.15.0+cpu, opencv 5.0.0, mediapipe 1.2.2, open3d 0.20.0, scikit-image 0.26.0) and installs are not authorised. Therefore the **JSON** form is normative; the YAML authoring form is **DEFERRED** (§8, D-MIG-3). A YAML file may be *authored* for humans and *converted* to JSON before validation, but only the JSON is a factory document.

### 4.2 Refpack — `livynth.factory.refpack` v1.0.0

The per-character asset manifest: what references exist, what they are, and what may be claimed from them.

Required top-level keys:

`@
schema                  "livynth.factory.refpack"   (const)
schema_version          "1.0.0"                     (const)
char_id                 string, matches ^[a-z0-9][a-z0-9_]*$
content_sha256          64 lowercase hex; digest of the semantic subset (D-SCHEMA-5)
created_utc             RFC3339 UTC string
generator               { name: str, ai_generated: bool, c2pa_present: bool, c2pa_manifest_sha256?: 64hex, notes?: str }
license                 { spdx_or_text: str, redistribution_allowed: "yes"|"no"|"unknown", evidence_path: str }
truth                   { calibrated: bool, scan: bool, statement: str }
consistency_audit       { verdict: str, assessed_utc: str, auditor: str, report_path: str,
                          admissible_for: [str], inadmissible_for: [str] }
images                  array of image records (§4.2.1), ≥ 1
camera_assumptions      object (§4.2.2)
landmarks               object (§4.2.3)
`@

`consistency_audit.verdict` is a **closed enum**:
`FAIL_SfM | CONDITIONAL_hull | REFERENCE_ONLY_triposr | PASS_as_appearance_reference`
(these are the four verdicts recorded in `docs/CHARACTER_FACTORY_INPUTS.md` §3 and `docs/characters/character_001_asset_qa.md`).

`consistency_audit.inadmissible_for` MUST contain `"identity_claim"` whenever the verdict is not `PASS_as_appearance_reference`, and MUST contain `"texture_albedo"` whenever the verdict is `FAIL_SfM` (projecting these photographs as albedo is prohibited by the asset QA doc).

#### 4.2.1 Image record

`@
view_id        canonical id from §2.1 (closed set)
role           "front"|"left_45"|"right_45"|"left_profile"|"right_profile"|"back"|"top"|
               "closeup"|"macro"|"ear"|"eyes"|"lips"|"hair"
file           basename only, no directory separator
sha256         64 lowercase hex
width_px       int > 0
height_px      int > 0
source_kind    "ai_generated"|"photograph"|"scan"|"unknown"
c2pa_present   bool
notes          str, optional
`@

Constraints:
- exactly one image must have `role == "front"` (the identity anchor);
- `file` must be unique; `view_id` must be unique;
- `file` MUST NOT contain `/` or `\` and MUST NOT contain `character_001`, `character001`, `identity_capture_v1` or `ours-photoreal` — the refpack is the only place a filename is allowed to be character-specific, and even there the *file name* is data, not code;
- the set of `view_id` values MUST cover the **required_for_reconstruction** role set for the pack to be `complete`; a pack missing one is `incomplete` and S3 MAY run but MUST record the gap.

#### 4.2.2 Camera assumptions (ASSUMED vs MEASURED)

`@
source              "livynth.factory.calibration" | "livynth.factory.calibration.legacy"
status_labels       { intrinsics, azimuth_pitch, scale, radius, principal_point, image_sha256, dimensions }
views[]             { view_id, azimuth_deg, pitch_deg, radius_mm, focal_equivalent_mm, interocular_mm,
                      label_intrinsics, label_azimuth_pitch, label_scale, label_radius,
                      label_principal_point }
`@

Every label value MUST be one of the four labels already used by `geo/calibration_spec.py`:
`MEASURED | ASSUMED | KNOWN_ASSUMED | USER_OVERRIDDEN`.

The **MEASURED** label is permitted **only** for `image_sha256` and `dimensions` until a real calibration exists. Every geometric quantity (intrinsics, azimuth/pitch, scale, radius, principal point) MUST carry a non-MEASURED label for a pack whose `truth.calibrated == false`. A validator MUST reject `label_intrinsics == "MEASURED"` when `truth.calibrated == false` — this is the machine form of the calibration doc's §1 prohibition.

#### 4.2.3 Landmark set reference

`@
schema             "livynth.c001.landmarks"
schema_version     "2.0.0"
per_view           { view_id: { path, sha256, point_count, unmapped_count, calibrated: false } }
`@

`calibrated MUST be false` for these packs (the landmark schema itself fixes this). `point_count` must equal the number of mapped points in the referenced file; a mismatch is `E_LANDMARK_ABSENT` / `E_HASH_MISMATCH`.

### 4.3 Character config — `livynth.factory.character` v1.0.0

Per-character configuration. All character-specific *values* live here; no character-specific *value* may appear in algorithm code (§10).

`@
schema               "livynth.factory.character"
schema_version       "1.0.0"
char_id              string
display_name         str
refpack              { path: str, content_sha256: 64hex }
truth                { ai_generated: bool, calibrated: bool, scan: bool, statement: str }
scale_priors         { interocular_px: number, ipd_mm: number, focal_mm_equiv: number,
                       camera_radius_mm: number, head_height_m: [number, number],
                       label: "ASSUMED"|"MEASURED"|"KNOWN_ASSUMED"|"USER_OVERRIDDEN" }
caps                 { texture_max_px: int, tris_max: int, face_mesh_scope: str }
voice                { path, sha256, sample_rate_hhz, duration_s, alignment: "UNVERIFIED"|... }
qa_overrides         { <metric>: { value, justification: str, approved_by: str, approved_utc: str } }
export_targets       { glb: {...}, video: {...} }
gates                { recognizable_character: {...}, phase3_blocks_migration: bool }
`@

Hard rules:
- `caps.texture_max_px MUST be 2048` for a prototype (ADR-C001-004 decision 6). A value of 4096 requires an explicit justification block naming the four gates that passed (identity, topology, UV quality, material).
- `scale_priors.label MUST NOT be "MEASURED"` while `truth.calibrated == false`.
- `scale_priors.head_height_m` MUST be a 2-element ascending range within [0.16, 0.34] (the bound already enforced by `geo/proxy_fit.py`).
- **every** entry in `qa_overrides` MUST carry a non-empty `justification` and `approved_by`. An override without justification is `E_OVERRIDE_UNJUSTIFIED` — this mechanises the v0.1 rule "never loosen silently".
- `truth` MUST equal the refpack's `truth`; disagreement is `E_TRUTH_MISMATCH`.

---

## 5. Machine-checkable form

### 5.1 File layout (unchanged from v0.1 §3)

`@
characters/<char_id>/
  references/manifest.json      <- livynth.factory.refpack v1.0.0   (tracked)
  config/character.json         <- livynth.factory.character v1.0.0 (tracked)
  references/                   <- binaries, gitignored
  models/ candidates/ output/   <- gitignored
  provenance/                   <- small tracked JSON, §6.4
`@

**D-MIG-1.** v0.1 kept `qa_overrides.yaml` as a separate file; v1.0 folds overrides into `character.json` under `qa_overrides` so that "config" is a single validated document and an override cannot exist without the config that it overrides. The separate file remains a legal *input* to the fold, not a factory document.

---

## 6. Backend adapter contract

### 6.1 Scope and shape

Language-agnostic: it is defined by JSON documents, not by a Python ABC or an in-process interface, so a cloud backend, a Blender script, or a Rust binary can satisfy it. Three backends are named as *targets*, not as implementations:

| Backend id | Shape | Tier | Current reality |
|---|---|---|---|
| `local_visual_hull` | multi-view silhouette hull + marching cubes | cpu-local | exists in `geo/visual_hull.py`; produced a candidate the Phase-3 gate rejected |
| `local_neural_single_image` | one image → mesh, no multi-view constraint | cpu-local | TripoSR on CPU: produced a mesh (80,873 v / 161,488 f, not watertight, no UVs) the Phase-3 gate rejected as a different person |
| `cloud_or_parametric` | hosted API or parametric fit (e.g. FLAME 2023 Open) | cloud-gpu / cpu-local | **not authorised**: FLAME 2023 Open is registration-gated and evaluation-only (ADR decision 3); hosted APIs need written approval |

No backend is enabled by default. Enabling one is a config act recorded in the provenance record.

### 6.2 Request — `livynth.factory.backend.request` v1.0.0

`@
schema            "livynth.factory.backend.request"
schema_version    "1.0.0"
request_id        str
char_id           str
backend_id        str
backend_version   str
refpack           { path, content_sha256 }
images[]          { view_id, role, path, sha256, width_px, height_px }
calibration       { path, sha256, assumption_labels }
landmarks[]       { view_id, path, sha256 }
config            { path, sha256, caps: { texture_max_px, tris_max, face_mesh_scope } }
execution         { tier: "cpu-local"|"gpu-local"|"cloud", device: "auto"|"cpu"|"cuda"|"rocm",
                    max_memory_gb: number, timeout_s: number, seed: int }
output_dir        str
license_acceptance { required: bool, granted: bool, token_ref?: str }
`@

Rules:
- every `images[].sha256` MUST equal the refpack's; a backend that receives bytes other than the pinned ones invalidates the run;
- `execution.tier` MUST come from the v0.1 §8 tier enum unchanged;
- `execution.device` MUST NOT be `cuda`/`rocm` on a machine without CUDA (this machine: no CUDA, Radeon 530 + Intel UHD);
- `license_acceptance.granted MUST be false` when `required` is true and no approval token exists — the backend MUST then decline (§6.3), not attempt the work.

### 6.3 Response, capabilities and decline

Response — `livynth.factory.backend.response` v1.0.0:

`@
schema            "livynth.factory.backend.response"
schema_version    "1.0.0"
request_id        str
backend_id        str
status            "ok" | "declined" | "failed"
candidates[]      { path, sha256, format, role: "candidate" }
capabilities_echo object (§6.3)
metrics           object
provenance_ref    str          (path to a livynth.factory.provenance document)
failures[]        { code, message, stage, retryable: bool }
decline           { reason, detail, blocked_on }   (present iff status == "declined")
`@

Capabilities — `livynth.factory.backend.capabilities` v1.0.0:

`@
emits_uvs                 bool
emits_textures            bool
emits_watertight          bool
emits_morph_targets       bool
emits_rig                 bool
requires_gpu              bool
requires_network          bool
requires_user_approval    bool
execution_tier            "cpu-local"|"gpu-local"|"cloud"
license                   { spdx_or_text, redistribution_allowed: "yes"|"no"|"unknown", evidence_path }
`@

**Decline reasons (closed enum):**
`license_not_permitted | user_approval_required | hardware_unavailable | tier_not_available | dependency_missing | scope_out_of_contract | input_insufficient`

**D-BACKEND — decline is not failure.** A backend that cannot or must not run returns `status="declined"` with a reason; this is a *first-class, non-error* outcome and is recorded as such. Rationale, from evidence: ADR decision 3 requires FLAME to be *evaluated, not imported*; the correct machine behaviour for "not authorised" is a decline, and an error would wrongly mark the whole run as broken. Consequences:
- a declined backend produces no candidate and does not set the stage to FAIL;
- the stage is `degraded` (still admissible, §7.3) if at least one other backend produced a candidate;
- the stage is `BLOCKED` only if **every** enabled backend declined and at least one backend was *required* by the config;
- decline reasons are counted in the run summary so a fleet that silently declines everything is visible.

**Failure codes (closed):** `E_BACKEND_EXEC`, `E_BACKEND_TIMEOUT`, `E_BACKEND_OOM`, `E_BACKEND_NONZERO_EXIT`, `E_BACKEND_OUTPUT_MISSING`, `E_BACKEND_OUTPUT_INVALID`, `E_BACKEND_LICENSE`, `E_BACKEND_DECLINED`, `E_INTERNAL`.

### 6.4 Provenance — `livynth.factory.provenance` v1.0.0

One record per candidate. Machine-readable and diffable: the canonical form (§4.1 D-SCHEMA-5) is what gets diffed.

`@
schema            "livynth.factory.provenance"
schema_version    "1.0.0"
record_id         str
stage             "S0".."S8"
char_id           str
status            "planned"|"implemented"|"unit-tested"|"rendered"|"visually-approved"|"FAIL"|"BLOCKED"|"UNVERIFIED"
source            { commit: 40hex, branch: str, dirty: bool }
commands[]        { argv: [str], cwd: str, exit_code: int, started_utc: str, finished_utc: str }
environment       { python: str, os: str, packages: { name: version }, blender: { version, path }|null,
                    cuda_available: bool }
inputs[]          { path, sha256, role }
outputs[]         { path, sha256, role, bytes: int }
known_failure_modes[]  str
failures[]        { code, message, stage }
created_utc       str
`@

Rules:
- `commands[]` MUST be present and non-empty for any status other than `planned`; each entry MUST carry its exit code (an unrun command is `UNVERIFIED`, never an omitted field);
- `source.commit` MUST be a real commit of the repo that produced the artefact;
- `known_failure_modes` MUST be non-empty when `status` is `FAIL`;
- `inputs[]` MUST include the refpack `content_sha256` and the config digest;
- ordering of `commands[]`, `inputs[]`, `outputs[]` is **by role then path** so two runs of the same stage produce byte-identical records when they genuinely produced the same thing.

### 6.5 QA report — `livynth.factory.qa` v1.0.0

A **superset** of the scorecard §9 `eval.json`: every key of that schema is retained with the same meaning, so existing bundles remain readable, and new keys are added for the geometry-first protocol.

Retained (scorecard §9): `protocol_version, gate_run_id, candidate_label, timestamp_utc, status, provenance, references, environment, renders, alignment, landmarks, silhouette, glb_invariants, motion_qa, controls, blinding, signoffs, verdict, audit_log`.

Added:

`@
geometry_evidence {
  clay_renders[]   { view_id, path, sha256 }      # neutral untextured renders
  wireframes[]     { view_id, path, sha256 }
  depth_maps[]     { view_id, path, sha256 }      # orthographic
  normal_maps[]    { view_id, path, sha256 }      # orthographic
  camera_convention { azimuth_sign, projection, focal_equivalent_mm, up_axis, note }
}
artifact_qa {
  manifold, duplicate_shells, self_intersections, offsets, topology_class,
  face_normal_consistency, camera_scale_assumptions, rig_functional, blendshapes_functional
}
admissibility { <metric_name>: "admissible_for_acceptance" | "diagnostic_only" }
`@

**D-QA-1 — the control rule (mandatory).** `gate_valid` is **computed**, not asserted:

`@
gate_valid = self_iou.pass
          AND wrong_identity_canary.gate_verdict == "REJECTED"
          AND geo02_expected_fail
          AND NOT blinding.leak_present
          AND no control in an un-rejected state
`@

Consequences, all taken from ADR-C001-004 and the Phase-3 result:
- a control that is **not rejected** makes the whole run `gate_valid = false` and the run `status = "BLOCKED"` — never PASS, never FAIL;
- the wrong-identity canary (the 1.18× lateral face-band widening) MUST be evaluated and MUST be **rejected** by the gate; if it is accepted, the *gate* has failed, and that is recorded as such;
- the jitter canary (σ = 8 px) is retained for continuity but MUST be labelled `diagnostic_only`, because it was measured to pass IoU 0.9036 and landmark 8.92 px;
- the self-IoU control MUST equal 1.000 within 1e-6; anything less aborts the run.

**D-QA-2 — appearance metrics are diagnostic-only.** `silhouette` (IoU) and the appearance landmark error MUST be listed in `admissibility` as `"diagnostic_only"`. They may be reported and they may inform a human reviewer, but **no PASS may depend on them**. This is the machine form of "a photo projected onto a shell is not a likeness". A validator MUST reject a report whose `verdict.status == "PASS"` while any `admissible_for_acceptance` metric is unmet, and MUST reject a report whose `admissibility` labels a gate-view appearance metric as `admissible_for_acceptance`.

**D-QA-3 — verdict.**
`@
PASS    iff gate_valid AND every admissible metric passes AND the rubric is ACCEPT on
        front, profile_left and profile_right (stricter label wins on disagreement)
FAIL    iff gate_valid AND an admissible metric or a required rubric view fails
BLOCKED iff NOT gate_valid
NOT_RUN iff the report was never produced
`@
A rejected profile can never be overridden by a good-looking front texture.

---

## 7. Failure taxonomy and stage contracts

### 7.1 Status vocabulary (repo-wide, unchanged)

`planned → implemented → unit-tested → rendered → visually-approved`, plus the terminal states `FAIL`, `BLOCKED`, `UNVERIFIED`. Statuses are never collapsed and never skipped forward. An unrun check is `UNVERIFIED`, never inferred.

### 7.2 D-FAIL — closed failure-code taxonomy

| Group | Codes |
|---|---|
| schema | `E_SCHEMA_MAJOR`, `E_SCHEMA_MINOR_AHEAD`, `E_SCHEMA_UNKNOWN_FIELD`, `E_SCHEMA_INVALID` |
| input | `E_INPUT_MISSING`, `E_HASH_MISMATCH`, `E_DIMENSION_MISMATCH`, `E_INPUT_INSUFFICIENT` |
| reference truth | `E_TRUTH_MISMATCH`, `E_LICENSE_UNKNOWN`, `E_CONSISTENCY_UNVERIFIED` |
| calibration | `E_CALIBRATION_ABSENT`, `E_CALIBRATION_LABEL_INVALID`, `E_CALIBRATION_ASSUMED_PROMOTED` |
| landmark | `E_LANDMARK_ABSENT`, `E_LANDMARK_HASH_MISMATCH`, `E_LANDMARK_COUNT_MISMATCH` |
| config | `E_OVERRIDE_UNJUSTIFIED`, `E_CAP_EXCEEDED`, `E_CONFIG_INVALID` |
| backend | §6.3 failure codes |
| gate | `E_GATE_CONTROL_NOT_REJECTED`, `E_GATE_SELF_IOU`, `E_GATE_JUDGE_REJECT`, `E_GATE_BLINDING_LEAK`, `E_GATE_SIGNATURE_MISSING` |
| geometry | `E_GEOM_NOT_MANIFOLD`, `E_GEOM_DUPLICATE_SHELL`, `E_GEOM_SELF_INTERSECTION`, `E_GEOM_NORMAL_INCONSISTENT`, `E_GEOM_SCALE_INVALID` |
| internal | `E_INTERNAL`, `E_TIMEOUT`, `E_OOM` |

Each code maps to exactly one of: **BLOCKING** (the stage cannot produce an admissible output), **DEGRADING** (the stage may produce an admissible output with the degradation recorded), **DIAGNOSTIC** (recorded, never changes the outcome).

### 7.3 S0–S8 stage contracts

Carried from v0.1 §4 and extended. `required_for` = the stage a failure blocks.

| Stage | In → Out | Exit criteria | Failure codes | Degraded-but-admissible | Blocks |
|---|---|---|---|---|---|
| **S0** Ingest | refpack dir → refpack manifest | all files hashed; dims match; C2PA + licence recorded; required role set covered | `E_INPUT_MISSING`, `E_HASH_MISMATCH`, `E_DIMENSION_MISMATCH`, `E_LICENSE_UNKNOWN` | pack `incomplete` (a detail view missing) → admissible for S1/S2, NOT for S3 | S1 |
| **S1** Validate | manifest → consistency verdict | cross-view audit done; ASSUMED/MEASURED annotated | `E_CONSISTENCY_UNVERIFIED` | verdict `CONDITIONAL_hull` → admissible for silhouette backends only; inadmissible for identity | S2 |
| **S2** Calibrate + landmarks | manifest → calibration set + per-view landmarks | hashes verify; ≥1 detection or manual annotation per required view | `E_CALIBRATION_ABSENT`, `E_LANDMARK_ABSENT`, `E_LANDMARK_COUNT_MISMATCH` | profile landmark annotations absent → profile landmark gate stays `NOT_RUN`/diagnostic | S3 |
| **S3** Reconstruct | refs+calib+landmarks → candidate + provenance | backend ok **or** declined; never a fabricated mesh | backend codes (§6.3) | backend declined → admissible if ≥1 candidate from another backend | S4 |
| **S4** Blind gate | candidates + renders → QA report | D-QA-1 gate_valid computed; controls rejected; rubric signed | gate codes | appearance metrics diagnostic-only (D-QA-2); a non-rejected control → **BLOCKED**, not degraded | S5 |
| **S5** Retopo + rig | winner → quad GLB + shapes | topology Option B provenance verified; morph essentials present | geometry codes, `E_LICENSE_UNKNOWN` | — | S6 |
| **S6** Texture / hair / eyes | retopo GLB → textured GLB | UV on all primitives; bake not project | `E_CAP_EXCEEDED` | — | S7 |
| **S7** Export + audit | textured GLB → final GLB | scorecard §3 absolute invariants | geometry codes | — | S8 |
| **S8** Render / video | final GLB + voice → MP4 | 1080×1920 MP4; audible; captions | `E_TIMEOUT`, `E_INTERNAL` | ffmpeg absent → **BLOCKED**, never a silent skip | — |

**Propagation rule.** A stage's output is admissible iff its own exit criteria are met. A failure in S_k blocks S_{k+1} and everything downstream, except where the table says "admissible". S4 may never be entered with a non-admissible S3 output: this prevents the exact failure mode in which an envelope-shaped but visually wrong candidate reaches the gate and produces a meaningless metric.

**Ordering rule.** No stage may consume a later stage's output. S3 backends are mutually blind to each other. S4 judges never see backend labels.

---

## 8. Migration and back-compat

**D-MIG-1** (layout) — the v0.1 directory layout is unchanged. Migration of existing files into it is **DEFERRED** until the Phase-3 gate passes (v0.1 §3.3 already said so; this contract does not relax it). Until then `assets/characters/character_001/identity_capture_v1/` remains the live path and the refpack's `file` entries are basenames resolved against that root.

**D-MIG-2** (legacy readers) — every legacy module in §2.1 continues to read its own hardcoded structures. The canonical view-id vocabulary is introduced in *new* documents only; translation happens in the adapter (§2.2), not by editing the legacy modules. Editing them is DEFERRED (§11).

**D-MIG-3** (format) — JSON is normative; YAML authoring is DEFERRED because PyYAML is absent and installs are unauthorised. When/if a YAML front end is approved, it must *fold* to JSON and the YAML file must never be read by a validator.

**D-MIG-4** (existing Character 002 test) — restated in §9 so it remains valid against this contract.

**D-MIG-5** (no cross-repo refactor) — consistent with ADR decision 7: no refactor of `geo/`, `video/` or `tools/` is authorised by this contract. The only permitted touch to an existing file is the single-line discovery addition in the minimal-slice doc (W9), and that is separately gated.

---

## 9. Character 002 acceptance test, restated against this contract

Same intent as v0.1 §11, now machine-checkable. The pipeline is the artefact; Character 002 is the test.

| ID | Requirement | Machine check |
|---|---|---|
| **A2-01** | A fresh refpack for Character 002 is produced by the **same** S0 code path, with no code change | `character_factory.refpack` validates; `git diff --name-only <base>..<002-branch> -- character_factory/ geo/ video/ tools/` is empty except allowlisted config/manifest files |
| **A2-02** | The Character 002 config differs from Character 001's **only** in allowlisted keys: `char_id`, `display_name`, `refpack.path`, `refpack.content_sha256`, `truth`, `voice`, `qa_overrides`, `scale_priors`, `caps` | key-level diff computed by the factory validator must contain **no** key outside the allowlist |
| **A2-03** | Zero factory-source edits | the same diff check, plus the §10 audit must report **no new** character-specific identifier in algorithm code (the offender count must not increase) |
| **A2-04** | S0–S4 run unchanged; S5–S8 may consume Character 001 placeholders | each stage's output validates against the stage contract in §7.3; `status` values are from the §7.1 vocabulary |
| **A2-05** | Per-character deviations only through `qa_overrides`, each justified | every override carries non-empty `justification` + `approved_by` (+ timestamp); validator rejects otherwise |
| **A2-06** | Character 002 passes the **same** blind gate: D-QA-1, D-QA-2, D-QA-3 | QA report validates; `gate_valid == true`; rubric ACCEPT on front, profile_left, profile_right; stricter label wins |
| **A2-07** | Independent human sign-off, no generator session judging | `signoffs` contains the three required roles with ISO-8601 UTC timestamps and one-line evidence; the generating session is not among them |
| **A2-08** | Back-compat: the Character 001 artefacts and the legacy readers still work | legacy modules' own suites stay green; the refpack for Character 001 still validates |

**Non-goals (unchanged):** no photorealism claim for 002 before 001 passes; no claim beyond "a second recognisable character through the identical pipeline".
**Prerequisites:** GEO-03 Phase-3 PASS, then the F2 dry run.

---

## 10. Hardcoding audit

### 10.1 What must be true

**Zero** character-specific identifiers in the *algorithm code* of `geo/`, `video/` and `tools/`. Config, data and documentation may contain them — they are where they belong.

### 10.2 The identifier set

Three classes, all of which are character-specific:

`@
(a) identity / pack identifiers
    character_001            character001              character00N        character[0-9]{3}
    ours-photoreal           ours_photoreal            our-avatar          ours_avatar
    identity_capture_v1
(b) emitted schema identifiers
    livynth.c001              livynth.character001
(c) hardcoded reference filenames
    0[1-9]_<name>.png   e.g. 01_subject_front.png, 04_left_profile.png, 07_top_head.png
`@

Class (c) matters: it is the **largest** class and a pattern that omits it under-reports badly (§10.3). A module that hardcodes the reference filenames is character-coupled even when no other token appears.

### 10.3 Measured baseline (2026-11-11, tracked `*.py`, this repo)

Measured with ripgrep over the working tree at feature-branch tip `59f4628`. Counts are **matching lines**, not occurrences.

| Scope | (a)+(b) only | (a)+(b)+(c) |
|---|---|---|
| `geo/**/*.py` | **47** | **95** |
| `video/**/*.py` | **0** | **0** |
| `tools/*.py` | **4** | **9** |
| `tests/**/*.py` | **0** | **0** |

The ADR-canonical subset (a) alone (`character_001|character001|ours-photoreal|identity_capture_v1`) gives `geo` = **35**, `tools` = **4**.

Breakdown of the (a)+(b) = 47 geo hits by kind, determined by reading each hit:

| Kind | geo hits | files |
|---|---|---|
| **executable logic** | **16** | `visual_hull.py` (6), `proxy_fit.py` (5), `migrate_legacy_landmarks.py` (1), `morph_fit.py` (3), `setup_blender_fit_scene.py` (1) |
| docstring / usage-comment text | 14 | `calibration_spec.py` (3), `detect_landmarks.py` (2), `manual_annotations.py` (1), `visual_hull.py` (2), `proxy_fit.py` (2), `migrate_legacy_landmarks.py` (3), `setup_blender_fit_scene.py` (1), `morph_fit.py` (0), `detect_one.py` (0), `landmark_spec.py` (0) |
| in test files (allowed fixtures) | 7 | `geo/tests_*` |
| in the data file `geo/character001_landmarks.json` (allowed) | — | — |

Adding class (c) takes geo from 47 to 95 because the hardcoded filename tables are dense: `calibration_spec.py` (25: three 8-entry tables + one detail list), `detect_landmarks.py` (9), `visual_hull.py` (7), `proxy_fit.py` (4), `setup_blender_fit_scene.py` (5), plus `migrate_legacy_landmarks.py`, `detect_one.py`, `landmark_spec.py`.

**Consequence:** removing the executable ones is a *refactor of the failing geometry pipeline*. ADR-C001-004 forbids that while Phase-3 is FAIL. The audit is therefore defined as a **ratchet**, not a one-shot gate (§10.5), and the burn-down is **DEFERRED** (§11).

### 10.4 Exact commands the owner can run

Windows, in the repository root. `rg` is present at `C:\Users\orcha\.cache\opencode\bin\rg.exe`; `git grep` is an equivalent that only sees tracked files. In git, `:(exclude)` pathspecs apply to tracked-file searches.

**T0 — full algorithm-code sweep (all three classes; must reach zero):**

`@
git grep -n -E "character_00[0-9]|character[0-9]{3}|ours[-_]photoreal|ours[-_]avatar|our-avatar|identity_capture_v1|livynth.c001|livynth.character001|0[1-9]_[a-z0-9_]+.png" -- "geo/*.py" "video/*.py" "tools/*.py"
`@

**T0 — the same sweep excluding test files (the executable-code view):**

`@
git grep -n -E "character_00[0-9]|character[0-9]{3}|ours[-_]photoreal|ours[-_]avatar|our-avatar|identity_capture_v1|livynth.c001|livynth.character001|0[1-9]_[a-z0-9_]+.png" -- "geo/*.py" "video/*.py" "tools/*.py" ":!*test_*.py"
`@

**T0a — identifier sweep only (the ADR-canonical subset, for tracking against the ADR wording):**

`@
git grep -n -E "character_001|character001|ours-photoreal|identity_capture_v1" -- "geo/*.py" "video/*.py" "tools/*.py"
`@

**T0b — argparse/path defaults specifically (the highest-risk class):**

`@
git grep -n -E "default=.*(character_00[0-9]|character[0-9]{3}|ours[-_]photoreal|identity_capture_v1|0[1-9]_[a-z0-9_]+.png)" -- "geo/*.py" "video/*.py" "tools/*.py"
`@

**T1 — emitted schema ids (a separate class: these are *outputs*, not inputs):**

`@
git grep -n -E "livynth.(c001|character001).[a-z-]+.v[0-9]+" -- "*.py"
`@

**T2 — allowed scopes (must be non-empty; these are the *expected* homes):**

`@
git grep -l -E "character_00[0-9]|identity_capture_v1|livynth.c001" -- "docs/*.md" "docs/**/*.md" "characters/**" "geo/*.json"
`@

**T3 — the repo's own binary/no-secrets audit (unchanged, still required):**

`@
python tools/branch_audit.py --base b0235c1 --run-tests
`@

### 10.5 Ratchet semantics (the gate that can land now)

Because the baseline is non-zero, a hard "zero" gate would fail immediately and could not be landed. The gate that can be landed **now** is:

- the machine check computes the **set** of offending identifiers in algorithm code;
- a checked-in **baseline** file records the accepted set (by file + identifier), with the current measured content;
- the check fails only if the set **grows** (a new offender) or if a baseline entry is removed without being replaced (progress must be acknowledged);
- shrinking the baseline is a normal, reviewable change — the ratchet is the mechanism that lets the geometry refactor happen later, in small reviewed steps, without a big-bang rewrite.

This follows the shape of the repo's existing `tools/branch_audit.py` (a review aid that must never report a clean repository as unsafe, and must catch the two failure modes it exists to catch) and `tests/test_branch_audit.py`, rather than inventing a new one.

---

## 11. Explicitly DEFERRED

| # | Item | Why deferred | Unblocked when |
|---|---|---|---|
| 1 | Removing the ~16 executable character-specific identifiers (and the ~79 hardcoded filename references) from `geo/`/`tools/` | touching the failing geometry pipeline | Phase-3 gate PASSES (ADR decision 2 outcome) |
| 2 | Migrating Character 001 into `characters/character_001/` | v0.1 §3.3; in-flight worktrees | Phase-3 gate PASSES |
| 3 | YAML authoring front end for the config | PyYAML not installed; installs unauthorised | owner approves an install |
| 4 | Unifying the three legacy view vocabularies inside the legacy modules | same as #1 | #1 lands |
| 5 | Renaming emitted schema ids (`livynth.c001.*`, `livynth.character001.*`) | they are written into existing artefacts; renaming breaks readers and comparability | #1 lands, and a migration is approved |
| 6 | Any S3–S8 implementation | the gate is FAIL | Phase-3 gate PASSES |
| 7 | Cloud/parametric backend enablement | FLAME registration-gated; hosted APIs need approval | explicit user approval |

---

## 12. Uncertainties (unverified, must not be assumed)

1. **Whether any backend can produce a likeness** is unknown. Both existing candidates were rejected; the geometry-first gap is located at "3D facial structure with correct identity".
2. **The §10.3 counts were measured with ripgrep over the working tree**, not by the AST-based checker the minimal slice will implement, and they count matching *lines*. The AST checker will classify comments/docstrings/strings differently, so the executable subset it reports will differ from the 16 estimated here. Treat 16 as an estimate derived by reading the 47 hits, not as a machine count.
3. **The three legacy view vocabularies** are reconciled here by reading the source. No test currently asserts that the mapping in §2.2 is complete; a translation test in the slice must assert it.
4. **PyYAML absence** was inferred from the recorded package list in `docs/CHARACTER_FACTORY_INPUTS.md` §2, not by running `pip list` in this session.
5. **Whether the repo's own CI runs the geometry suites** is asserted by `tests/test_local_check_discovery.py` (which asserts the discovery command) and by the file's current content; the *result* of that command was not executed in this session.
6. **The Phase-3 verdict is FAIL and this document does not change that.** No clause here may be cited as evidence that a candidate is recognisable.

---

## 13. Source anchors

| Anchor | Value |
|---|---|
| ADR | `docs/decisions/ADR-C001-004-phase3-repair.md` (7 decisions; geometry-first protocol; decision 7 = this contract) |
| Base spec refined | `docs/CHARACTER_FACTORY_SPEC.md` v0.1 |
| Evidence packet | `docs/CHARACTER_FACTORY_INPUTS.md` |
| Experiment log | `docs/C001_GEO03_EXPERIMENT_LOG.md` (§G9/G10 controls; G3 measurements) |
| Blind scorecard | `docs/C001_GEO03_BLIND_SCORECARD.md` §2, §3, §7, §9 (QA report predecessor) |
| Calibration spec | `geo/calibration_spec.py`, `docs/C001_GEO03_CALIBRATION.md` §5 (ASSUMED/MEASURED labels) |
| Landmark schema | `geo/landmark_spec.py` (canonical view ids; `schema_version` convention) |
| Licence register | `docs/C001_GEO04_LICENCE_MATRIX.md` (18 unresolved items) |
| Asset truth | `docs/characters/character_001_asset_qa.md`, `docs/characters/character_001_identity_capture.md` |
| Base commit of this branch | `b0235c152ff18162428d2e8ae8d7fe893f4f591a` |
| Feature-branch tip when written | `59f4628954893622be60d7a0428b400a0adadbaf` (`feat/m001-talking-human-pipeline`, draft PR #1) |

**Note on branch base.** This branch was created from `b0235c1`, which is **behind** the feature-branch tip `59f4628` (the tip adds the gate/blind-bundle tooling, the licence matrix and the geo04 research). This contract was written against the tip. Rebase or merge the feature branch before review, and re-run the §10 baseline measurement on the rebased tree — the counts will change.
