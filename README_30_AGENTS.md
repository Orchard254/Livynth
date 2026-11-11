# LIVYNTH OpenCode 30-agent crew (V2 project configuration)

**Contains:** 1 primary coordinator (`livynth-director`) + 29 specialized subagents, one `AGENTS.md`, a V2 `opencode.jsonc`, and a task/dependency charter.

## Install in your local Git checkout

Unzip the contents **into the root of your LIVYNTH repository**, preserving the `.opencode/agents/` directory. If you already have an `opencode.jsonc` or `AGENTS.md`, **merge** these files instead of overwriting your existing settings. All agents use your selected model; no API credentials or model IDs are hardcoded.

OpenCode V2 currently discovers project agent markdown files at `.opencode/agents/<name>.md`, uses `agents`/`permissions` (plural) in JSONC, and supports background subagents from a primary session. This bundle is **schema-oriented and statically validated**, but has not been launched inside your specific OpenCode version. The local CLI version matters, particularly if using pre-V2 OpenCode.

The orchestrator agent is the default. Try:

> Inventory the current LIVYNTH code and milestones. Do not edit anything yet. Delegate separate read-only assessments to reconstruction-research, identity-auditor and independent-regression-qa; then propose the first C001-GEO-03 batch with input paths, tests and individual worktree ownership. Do not merge or push.

## Execution model

- **Registered roles:** 30. **Active at once:** typically 4–8 independent analysis/code tasks, fewer for GPU-heavy experiments.
- Primary delegates directly to child subagents; do not assume deeper delegation is available.
- **Read-only** research/review specialists cannot edit or execute arbitrary shell commands; they can inspect workspace sources and existing logs. Implementers get coding tools but must work in separate worktrees.
- Built-in shell permission prompts are helpful safeguards, **not a filesystem isolation/security sandbox**. Enforce real git branch protection and review outside agent prompts.
- A human approves external portrait uploads, paid APIs, merges/pushes and releases.

## Team roster

| # | ID | Team | Focus |
|---|---|---|---|
| 01 | `livynth-director` | Leadership | Coordinate C001 engineering; assign scoped tasks; enforce evidence gates; integrate by review only; maintain decision log. |
| 02 | `asset-curator` | Identity | Validate supplied source images, preserve native resolution and provenance, detect duplicate/thumbnails, prepare hash manifests. |
| 03 | `identity-auditor` | Identity | Compare candidate renders against Character 001 canonical front/45/profile references; flag drift, asymmetry and unrealistic likeness. |
| 04 | `camera-calibrator` | Identity | Estimate image camera assumptions and normalization; separate identifiable geometry from AI-generated perspective contradictions. |
| 05 | `landmark-engineer` | Identity | Build reliable repeatable facial landmark annotations, projection and multi-view consistency tools with manual correction support. |
| 06 | `multiview-auditor` | Identity | Review front/3/4/profile consistency, detect impossible geometry and score cross-view candidate renders. |
| 07 | `reconstruction-research` | Reconstruction | Benchmark existing portrait-to-head methods, constraints, weights, commercial APIs, licensing and hardware realistically. |
| 08 | `neural-reconstruction` | Reconstruction | Prototype a neural-image-to-3D head backend; record environment, inference inputs and raw outputs. |
| 09 | `parametric-reconstruction` | Reconstruction | Prototype a FLAME/MICA-style parametric face-fitting approach using the same canonical references. |
| 10 | `external-api-reconstruction` | Reconstruction | Prototype adapter for an external head reconstruction service; start with mocked tests, no uploads or charges without user authorization. |
| 11 | `morph-fitting-engineer` | Reconstruction | Improve conservative deformation of an existing morph-capable GLB, preserving original topology, skins and facial targets. |
| 12 | `topology-specialist` | Reconstruction | Build face retopology and non-destructive base-mesh adaptation; preserve good loops around eyes and mouth. |
| 13 | `uv-texture-engineer` | Appearance | Prepare stable face UVs, texture baking and correspondence diagnostics; avoid direct projection of shaded photo as albedo. |
| 14 | `skin-albedo-engineer` | Appearance | Derive physically plausible skin base color, pigmentation and freckles from references while separating lighting/shadows. |
| 15 | `skin-microdetail-engineer` | Appearance | Design pore/fine-normal/roughness pipeline, calibrated scale and frequency, inspect macro artifacts. |
| 16 | `eye-specialist` | Appearance | Create realistic cornea, iris, sclera, tearline, eyelash and eyebrow geometry/material and prevent clipping. |
| 17 | `hair-specialist` | Appearance | Replace baseline ponytail with Character 001 short curly auburn hairstyle and match crown, profile and rear volume. |
| 18 | `wardrobe-lookdev` | Appearance | Replace fake navy-shirt material mask with real garment geometry and stable studio materials/lighting. |
| 19 | `facial-rig-engineer` | Animation | Map imported blendshapes to shared semantic rig and preserve shape deltas through reconstruction/retopology. |
| 20 | `blink-specialist` | Animation | Resolve eyelid/lash artifacts at 0%, 50%, 100% blink, gaze combinations and asymmetric blinks. |
| 21 | `expression-specialist` | Animation | Implement robust smile, frown, brow, jaw and emotion blendshape combinations without facial collapse. |
| 22 | `phoneme-aligner` | Animation | Build real speech phoneme/word timing from audio, record confidence and timings, reject text-only guesses for quality gates. |
| 23 | `lipsync-engineer` | Animation | Map phoneme timing to target visemes/ARKit facial controls with coarticulation and lip closure. |
| 24 | `natural-motion-engineer` | Animation | Add subtle head, gaze, breathing and speaking behavior using motion controls separate from speech. |
| 25 | `blender-render-specialist` | Production | Optimize headless Blender rendering, multi-angle thumbnails, lighting settings and platform fallbacks. |
| 26 | `video-finishing-specialist` | Production | Build audio mixing, subtitle burn-in, framing, export and final MP4 validation. |
| 27 | `glb-interoperability-engineer` | Production | Audit/repair glTF/GLB metadata, materials, skins, morph targets, animations, compatibility and export. |
| 28 | `performance-benchmarker` | Production | Measure memory, GPU VRAM, render time, provider calls, candidate cost and pipeline throughput. |
| 29 | `independent-regression-qa` | Production | Review test integrity, try intentional failures, compare outputs and refuse unsupported success claims. |
| 30 | `release-integrator` | Production | Examine completed isolated worktrees/patches; propose conflict-free integration order, never auto-merge or push. |

## Success measures

- C001-GEO-03 first: at least two independently tested reconstruction candidates plus the existing morph-fit baseline, with five-angle visual comparisons and GLB/morph audits.
- Reject methods that only produce a volume or lose functional eyelids/visemes.
- Do not spend GPU on final-grade textures, 12–15s video, or full-body character until a face likeness candidate passes first.

## Notes

- The separate ZIP does not install or launch OpenCode. It adds files to your repo; you run OpenCode yourself.
- The agent descriptions are job contracts, not 30 processes autonomously running 24/7.
