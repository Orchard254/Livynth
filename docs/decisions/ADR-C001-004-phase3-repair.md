# ADR-C001-004 — Phase-3 FAIL, geometry-first reconstruction and bounded repair

**Date:** 2026-11-11
**Decision owner:** LIVYNTH lead developer
**State:** APPROVED FOR IMPLEMENTATION, NOT A RECONSTRUCTION PASS
**Branch:** `feat/m001-talking-human-pipeline` (draft PR #1)
**Basis:** OpenCode Phase-3 report supplied 2026-11-11; raw local experiments / sealed evaluation files remain on the owner's Windows machine and were not independently fetched into this repository.

## Observed results — preserve the failure

- Phase-3 final verdict: **FAIL**. The first multiview judgment leaked identity-signoff information by reading an `eval.json` from inside the evaluation bundle; it was invalidated. The second, clean blind judgment still rejected all required views under the aggregate gate.
- Candidate A: frontal *likeness-only* ACCEPT, but frontal geometry FAIL and both 90-degree profiles REGENERATE. Candidate B: frontal REFERENCE_ONLY, both profiles REGENERATE.
- Profile orientation passed; the failures are **not attributable to a left/right mirroring issue**.
- An intentionally wrong-identity face-width canary (1.18×) was not rejected by existing similarity-aligned landmark and silhouette metrics. Projected photographs can cause rendered-image metrics to evaluate the *photograph*, not the geometry.
- **No passed reconstruction candidate exists. Never claim otherwise.**

## Decisions (7/7)

1. **Topology Option B: APPROVED, conditional on provenance.** Use the candidate CC0 quad base mesh for retopology after verifying source, attribution, topology suitability and the exact license. A CC0 claim in a report is not license verification.
2. **Candidate A: ONE BOUNDED REPAIR EXPERIMENT APPROVED.** Remove duplicate/translucent shell; correctly carve posterior cranium; assign view-aware material/albedo using measured yaw convention. Keep A as a diagnostic candidate until it passes clean gates. Do not try to salvage B's likeness in this round.
3. **FLAME 2023 Open: EVALUATION APPROVED, registration/dependency import NOT AUTOMATICALLY AUTHORIZED.** Investigate the **FLAME 2023 Open** CC BY 4.0 model as an optional geometry prior. Do not substitute the non-commercial FLAME 2023 academic model, the non-commercial FLAME texture model or restricted FLAME datasets. Record attribution and terms. No agent creates an account, accepts terms, buys services, or uploads images without user approval.
4. **Phoneme aligner: INSTALLATION DEFERRED.** Keep M001's existing WAV/timeline behavior passing. Research a CPU-capable aligner independently; don't install 1–2 GB of dependencies or attempt a major lip-sync refactor during the geometry repair gate.
5. **Old V32/MakeHuman GLB: RETIRED FROM C001 CRITICAL PATH.** It remains an optional engineering baseline if located, not a prerequisite for newly reconstructed Character 001. Preserve old tests and renderer compatibility.
6. **2K PBR texture target for prototype.** Use 2048×2048 as the default budget where appropriate. Upgrade selectively to 4K only after identity, topology, UV quality and material tests pass. No inflated texture detail from image upscaling.
7. **Character Factory spec: PROVISIONALLY APPROVED AS AN INTERFACE CONTRACT.** Define versioned per-character asset manifests, backend adapter interface, artifact provenance, QA report schema and failures. Implement only isolated low-risk components now; no cross-repository refactor while Phase-3 FAIL is unresolved.

## Geometry-first acceptance protocol (mandatory)

A repaired candidate is **not** accepted merely because the front view resembles a photograph.

- **Blind evaluation:** Seal candidate IDs and task data before asking independent reviewers. No `eval.json`, previous verdict, identity judge notes or author hints inside reviewer input. Place new verdicts outside the input bundle. Record bundle hash and reviewer access rules; invalidate and rerun if blinding fails.
- **Photo-independent geometry evidence:** Provide neutral untextured/clay renders and wireframes from front, left 45°, right 45°, left 90°, right 90°, plus orthographic depth/normal maps with an explicit camera convention. The geometry reviewer must be able to evaluate the head with the photo-projection materials switched off.
- **Artifact QA:** Report manifoldness, duplicate shells/layers, self-intersections or offsets, topology class (tri/quad), face-normal consistency, camera calibration/scale assumptions, and whether any facial rig or blendshapes actually work.
- **Wrong-identity controls:** Retest deliberate width/shape canaries *without relying solely on 2D similarity-aligned metrics*. The gate must reject the intentionally wrong 1.18× face-width control. A false acceptance means **the evaluation gate fails**, not just the model.
- **Human evaluation:** Require an independent, clean blinded profile and facial anatomy rubric. Rejected profiles cannot be overridden by good-looking front textures. Report per-view labels and the stricter aggregate label. When true 3D ground truth is unavailable, explicitly note that depth/normal consistency is a plausibility gate, not measured scan accuracy.
- **No quality claim from a photograph projected onto a shell.** Albedo and similarity numbers remain diagnostic until the face passes geometry, identity and negative-control gates.

## Agent dispatch — next permitted actions

**Owner: livynth-director**
- Ask the A-repair implementation agent for the three concrete repairs above in an **isolated worktree**. Produce exactly one labeled candidate and comparison package. Preserve the original A and all evidence.
- Ask `topology-specialist` / `parametric-reconstruction` to verify CC0 base topology license/provenance and outline a morph-preserving retopology path. No unverified vendor assets or account actions.
- Ask `multiview-auditor` and `independent-regression-qa` to implement the blind protocol, negative control, geometry-free material toggles and independent results in **separate worktrees**, with no access to prior verdicts.
- Ask `release-integrator` to review the untracked local reports and propose organized commits, **without overwriting**, renaming, deleting or staging pre-existing user changes (`assets/README.md` deletion and `assets/voice_transcript.txt`).
- Ask architecture specialists to refine the Character Factory interface only. Do not launch heavyweight installs, external account registrations or paid API jobs.
- Report the A-repair actual geometry QA and blind gate; if it fails, close this approach as unproven and favor retopology/parametric reconstruction instead of repeated material-only revisions.

## Source/versioning and collaboration rules

- Keep `main` untouched; leave PR #1 **draft**.
- Agent code/doc changes may be committed locally in narrowly scoped commits, but **no push or merge without explicit owner review**. Do not rewrite history or use `git reset --hard`.
- This ADR is a small remote-only addition. Agents working at `31a9b19` must sync the new feature-branch commit safely and preserve their untracked documents.
- Do not close the Phase-3 failure until a clean geometry-based gate and wrong-identity canary **both** pass. Passing unit tests alone is not sufficient.

## License references (checked 2026-11-11)

- [FLAME model license — FLAME 2023 Open versus academic models](https://flame.is.tue.mpg.de/modellicense.html)
- [FLAME texture license — separate non-commercial terms](https://flame.is.tue.mpg.de/texturelicense.html)
- [Montreal Forced Aligner docs, for later optional CPU-alignment evaluation](https://montreal-forced-aligner.readthedocs.io/en/stable/getting_started.html)

**Next release gate:** C001-GEO-03 Phase-3 remains **FAIL**, repair experiment **AUTHORIZED**, no completed likeness/rigging outcome claimed.
