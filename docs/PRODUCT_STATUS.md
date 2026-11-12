# LIVYNTH product status — 2026-11-12

**Product goal:** original recognizable digital humans that can speak, blink and move in a reproducible portrait-video studio. This is a development project; it is not yet a finished photorealistic production application.

## Verified, reproducible evidence

| Workstream | Status | Evidence |
|---|---|---|
| M001 timeline + studio orchestration | LOCAL PYTHON PASS | Windows local-check on prior experiment head: 58 application tests, 1 skip, and 174 geometry tests, 2 skips; all requested local checks PASS (229 passed, 3 skipped, no failures). |
| STUDIO-003 complete-demo sequencing | LOCAL SYNTHETIC PASS / WINDOWS UNVERIFIED | 21 focused Studio+MP4 tests passed in the code execution environment. New demo mode generates character/voice once, orders preview then smoke then full video. |
| Stage-0 neutral MPFB character | OWNER WINDOWS PASS | Blender 4.5.10 / MPFB 20261010 reported 13,380 baked vertices, 13,378 quads, 163 joints, 67 morph targets; 13/13 GLB assertions pass. |
| Stage-1 native mesh capture and analysis | OWNER WINDOWS + OFFLINE ANALYSIS PASS | Source fingerprint `64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542`; one connected closed quad component; provisional landmark candidates only. |
| Character 001 likeness | FAIL | Existing Phase-3 blind gate rejects geometry. The photo-mesh hypotheses improve front fit but degrade at least one profile. No approved replacement. |
| Full narrated MP4 | UNVERIFIED | Studio source exists but no owner Windows end-to-end full render, human playback, visual identity or audible sync gate completed. |
| Release installer/distribution | NOT STARTED | Windows script launcher is developer alpha, not installer. |

## Current development release: Studio 0.1 Alpha + STUDIO-003

The **Build complete demo** mode runs:
1. Optional MPFB neutral character generation and GLB audit.
2. Optional Windows-local synthetic voice generation.
3. A portrait preview PNG.
4. A one-second 30-frame smoke MP4; require separate video/audio tracks and **540×960** dimensions.
5. A complete 1080×1920 portrait MP4; only after smoke structural QA succeeds.

The same generated character and narration files are reused across stages of a single demo run. The `studio_run.json` manifest records completed steps, elapsed time, and MP4 structural checks. An error records the failed stage. A structurally valid MP4 is **not** an endorsement of audible speech, expression naturalness, timing or likeness.

CLI:

```powershell
python livynth_studio.py --cli --mode demo --text "Welcome to LIVYNTH."
```

Windows GUI: `Start_LIVYNTH_Studio.bat` then **Build complete demo (recommended)**.

## STUDIO-004 narrator strip compatibility fix (2026-11-12)

Found a Blender 4.5 Python API hazard in `video/render_talk.py`: the first `Scene.sequence_editor.strips` collection is valid but empty, so treating it with `x or editor.sequences` can wrongly report that sound strips are unavailable. Patched with explicit `None` detection and a legacy fallback. Four synthetic tests reproduce the original failure and verify the corrected collection handling. **Actual Blender 4.5 integration and audible exported MP4 remain UNVERIFIED.**

## STUDIO-005 narration signal QA (2026-11-12)

A pre-render blocker was identified: previously a supplied PCM WAV containing complete silence was accepted merely because it existed, and a generated WAV was checked only for its frame count. The new `video/wav_qa.py` refuses effectively silent or malformed files before any Blender rendering starts; generated WAV checks and previously supplied WAV checks share the same implementation. The studio run manifest records measurable audio signal QA. The equivalent local standard-library Studio/MP4/WAV test harness passes **38/38** synthetic tests, including failure injection that proves no render subprocess starts for silence. The **real owner Windows Blender MP4 and audible speech gate remain UNVERIFIED**. Audio activity does not prove phoneme correctness or playback.

## STUDIO-005 owner Windows MP4 smoke result (2026-11-12)

**First real integrated smoke render: PASS_ARTIFACTS_NOT_IDENTITY.** Owner supplied Windows PowerShell/Blender 4.5.10 log for `python livynth_studio.py --cli --mode smoke` on development commit `35da149` (2026-11-12 about 02:29 Africa/Nairobi).

- Output folder: `output/studio/20261112_022923_287399/`.
- Neutral MPFB rigged character built/exported: 13,380 baked vertices, 13,378 native quad faces, 163 joints and 67 exported face targets; 13/13 export assertions PASS. 5,765,824-byte GLB created; glTF exporter warns that vertices with more than four influences are reduced to top four.
- Windows speech generated and Studio WAV-signal preflight accepted; `timeline.json` contains 323 frames using the approximate spelling-and-energy method (not phoneme alignment).
- Blender imported the GLB, animated one facial shape-key group (17 named shapes across timeline), selected `Human_export_copy` for temporary dark-shirt material, and rendered **all 30/30 smoke frames** without a crash. Rendered file: `livynth_smoke.mp4`.
- Studio's checks returned `PASS_ARTIFACTS_NOT_IDENTITY`, which implies the MP4 structure and required track presence/dimensions were accepted by current CLI checks. **Neither the MP4 bytes nor `studio_run.json` were uploaded in this evidence batch**, so independent visual/audio playback review remains **PENDING**.
- The 30-frame smoke video is only one second at 30 fps; existing fixed blinks begin at t=2.15 s, so a missing blink in this one-second video would be expected rather than a regression.
- Production-grade hair, eyes, skin, real wardrobe, accurate Character 001 likeness, phoneme alignment and full video acceptance remain unmet.

**Next owner evidence needed:** the **existing** `livynth_smoke.mp4` and `studio_run.json` from that output folder. Do not ask to rerun the completed smoke. If playback is acceptable, use a separate mid-speech/mid-blink diagnostic render before spending hours on a full 1080×1920 sequence.

## Independent owner MP4 review + STUDIO-006 candidate (2026-11-12)

The owner uploaded the actual `livynth_smoke.mp4` and `studio_run.json`. The 56,920-byte MP4 was independently decoded: 30/30 540x960 H.264 frames at 30 fps, 1.000-second video, AAC stereo audio 1.002 seconds, signal RMS -22.69 dBFS, no decoding errors. Mouth movement is visibly present. **First production smoke: technical PASS**. No human-listened transcript/sync acceptance is claimed.

**Visual quality: FAIL.** The face is too small in the portrait and uniformly blue-gray and underlit; no visible hair and no credible wardrobe distinction. Character 001 likeness remains FAIL. See `docs/gate_runs/2026-11-12-studio-smoke/INDEPENDENT_MP4_REVIEW.md`.

**STUDIO-006 corrective action:** reversible diagnostic-only framing, clay face vs navy placeholder shirt, moderately brighter lights. Original GLB geometry and rig remain unchanged. The change requires a new **one-frame Windows portrait preview** for acceptance; do not render a costly full video until appearance is reviewed.

## STUDIO-006 owner preview: partial visual improvement, wardrobe FAIL (2026-11-12)

Owner uploaded the real 540×960 `livynth_preview.png` after the STUDIO-006 preview changes.

- **Framing and lighting improve:** face is larger, visibly readable, normal geometry features discernible.
- **Wardrobe still FAIL:** a sampled forehead region has median RGB approximately (188,173,165), while the center chest sample is approximately (199,186,178), both warm clay; no dark navy garment visibly appears. Counting assigned material polygons is insufficient to prove rendered visibility.
- **Finished eyes absent:** the eye apertures appear pale and patterned, with no readable pupils/irises. Bald/generic skull and missing realistic skin/wardrobe persist. Identity likeness Phase-3 remains FAIL.
- **STUDIO-007 proposed patch:** raise the center shirt neckline threshold from 0.22 to 0.17 of total height below the crown (shoulder profile from 0.055 to 0.045), explicitly attach skin/shirt materials to imported mesh DATA slots, refresh mesh after material-index assignment, and compare actual rendered forehead-vs-torso RGB. A one-frame Studio preview now fails clearly if navy clothing is not visible. Old baseline geometry and GLB are unchanged. Numerical equivalence tests pass, but new Blender visual QA **UNVERIFIED** until next owner preview.
- **Product priority:** this is a reversible diagnostic garment only, not real cloth. Next real look-development efforts must integrate recognizable eyeballs/iris, hair, skin PBR and validated Character 001 anatomy. Do not imply diagnostic clay is photorealistic.

## IDENTITY-001 reusable parametric human foundation — 2026-11-12

**Source implemented, native Blender two-identity gate NOT RUN.** Added `character/identity_recipe.py` and two manually authored demonstration recipes; the original MPFB exporter now accepts `--identity-recipe` and applies validated parameters before geometry bake and ARKit shape creation. The resulting native baked vertex and quad connectivity hashes are recorded, together with recipe SHA. This retains one consistent base topology and existing animation interface as the *design contract*, subject to real exports.

`tools/identity_compare.py` rejects identical geometry, topology drift, 163-joint/67-morph incompatibility, different morph or joint names, missing skin or UV, and failed GLB audits. Studio GUI/CLI can select an optional identity recipe, mutually exclusive with an existing GLB. No existing baseline inputs are changed.

**Evidence:** 18/18 pure-Python recipe/comparator tests passed in the authoring environment; seven additional exporter/Studio integration tests are authored but not executed against a full repo checkout here. Actual MPFB Blender builds of demo A and B and revalidation of both facial expressions remain **UNVERIFIED**. Reference-photo fitting is **NOT IMPLEMENTED**: no project image is mapped to a recipe, and Character 001's five-angle identity gate remains **FAIL**. See `docs/IDENTITY_FOUNDATION_001.md` for exact acceptance commands.

**Next decisive experiment:** Windows Blender produce two GLBs and JSON reports from one template, run `identity_compare.py`, then inspect cheap front/profile and blink/jaw stills for both characters. If topology or animation changes, investigate MPFB macro/target compatibility before writing an image-fitting optimizer.

## IDENTITY-002 — repeatable A/B Windows acceptance runner

Added `tools/run_identity_ab.py`, a one-command local Blender A/B production+comparison driver. It uses the two validated manual recipes, finds Blender via Studio, creates a fresh timestamped directory without overwriting user files, exports both GLB/report pairs, and runs the strict geometry/topology/rig comparison. It stops on any failed subprocess or missing report.

**Evidence:** 5/5 focused A/B orchestration tests passed in the authoring environment (distinct commands, duplicate recipe refusal, overwrite refusal, first-error stop, missing-report negative test). The combined local identity module+runner check passed **23/23** here. Full LIVYNTH suite and actual Windows Blender A/B two-export run remain **UNVERIFIED**. This does not fit reference images, and Character 001 likeness Phase-3 is still FAIL. Exact command: `python tools/run_identity_ab.py`.

## IDENTITY-003 — native head-shape identity variation (2026-11-12)

**Real source mesh geometric variation PASS; animated GLB A/B still NOT RUN.** Using owner's original 13,380-vertex, 13,378-quad neutral NPZ (native positions SHA 64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542), two detailed 6-control identity recipes with *identical broad MPFB macro values* generated numerically different faces with unchanged quad connectivity. Maximum A/B position difference 20.82 mm, 4,318 vertices different by more than 1 mm, and no local triangle fold detected (area minima 0.502 and 0.772). Global self-intersections, eye collisions and visual likeness are UNVERIFIED.

Feature branch adds recipe v2 (backwards compatible v1), bounded native head deformation before FaceService loads ARKit/Meta targets, same-source audit comparison, and OBJ-only numeric proof CLI. Default Blender A/B runner now uses these two same-macro variants. **42/42 combined local unit/negative/real-neutral tests passed** in the authoring environment. Full project suite and both MPFB Blender exports are UNVERIFIED. Refer to docs/IDENTITY_HEAD_SHAPE_003.md for the exact commands and acceptance criteria.

**This is a significant reusable-geometry milestone, NOT automatic reconstruction from photos.** Photo landmark/camera fitting has not yet been implemented, and Character 001 Phase-3 likeness remains FAIL.

## IDENTITY-004 — uncalibrated image-landmark-to-head-parameter fitting (2026-11-12)

Implemented a bounded weighted least-squares map from manually measured 2D landmarks plus estimated camera projection to the six detailed identity controls from IDENTITY-003. Tests on synthetic multi-view correspondences recover deliberately injected coefficients. The tool rejects missing camera/view evidence, rank deficiency, and unsafe folding. It uses native geometry-backoff if the raw fit is locally unsafe, but **never creates an approved image-derived Blender recipe**.

**Actual Character 001 diagnostic:** using owner C001 source neutral mesh and manually measured front/left/right profile evidence (camera geometry assumed), full-strength fitted geometry failed local quad collapse. Backoff to 0.60 gave min area ratio 0.432 and combined sigma-normalized residual 1.3573→0.9661, but the **right profile regressed** 0.2992→0.3579. Result is **REJECTED_PROFILE_REGRESSION**, heldout five-view evaluation NOT RUN, likeness Phase-3 remains FAIL. The CLI returns a nonzero exit code on rejection. Full details in docs/IDENTITY_IMAGE_FIT_004.md.

**Limitations:** image landmark detector and proper correspondence mapping are not connected to the solver, cameras are separately estimated from source, and the current six coefficients cannot represent full human identity. This is a diagnostic fit component, not the final image-to-3D system.

## IDENTITY-005 — first real Windows two-character export; fingerprint repair (2026-11-12)

**Owner Windows Blender 4.5.10 / MPFB 20261010 A/B export: BOTH SUCCESSFUL.** After pulling development head 6887866, the owner ran python tools/local_check.py and python tools/run_identity_ab.py. The Python suite completed 164 tests, **one failure** (test_studio expected E_RECIPE_FIELDS for an invalid schema, while the validator correctly raised E_RECIPE_SCHEMA), **two skipped**; local_check stopped before geometry discovery. The test expectation is corrected in this change and a missing-fields regression is added; the entire Windows suite still needs rerun.

Both rigged GLBs exported and **all 13 export assertions passed** individually: demo_head_a.glb 5,734,608 bytes and demo_head_b.glb 5,747,536 bytes; both contain skin, UV, 163 joints and 67 facial shape targets, one character mesh, 13,380 baked-native vertices, 13,378 quads, matching native topology SHA 2ed8e59f... Both geometry SHA fingerprints differ.

The original combined comparator exited E_HEAD_SHAPE_AUDIT_a because the exporter hashed a **planned float64 shape** before assigning positions to Blender's **float32 mesh**. An independent recomputation from the original owner-supplied neutral NPZ (source SHA 64b001da...) with the same six controls, explicitly quantizing to float32, exactly reproduces **both stored hashes**:
- A: 3c27640ea147aaa0fbe906c9010f492afe806b35280f824463f1edfb6c38db69
- B: 94a16d3a94143b2513b9b310da9ba7cd0413ab74dd07d6d0b93f5975fdb04936

**Fix:** after assigning Blender vertices, read them back; check they match the float32-quantized proposal within 0.2 micrometres, independently rerun local fold/area tests on the stored positions, and hash those stored positions. The compiler, numeric and negative-injection tests pass in the authoring environment. This preserves the strict comparison instead of disabling it.

**Result:** forensically reconstructed logs satisfy the full structural comparator after accounting for deterministic precision, but the user's original run genuinely returned FAILURE and neither raw GLB was independently opened here. **Animation behavior (blink/jaw/visemes), image likeness, five-view approval and photorealism still UNVERIFIED/FAIL where applicable.** The Blender warning of >4 skin influences truncated on glTF export remains an independent motion-quality risk.

## IDENTITY-006 — existing GLB facial morph-signal inspector (2026-11-12)

After the owner Windows A/B exporter produced two rigged GLBs, the next decisive question is whether both actually contain **nonzero exported facial shape deltas** with identical bone/shape interfaces. New tools/glb_morph_qa.py inspects the existing demo_head_a.glb and demo_head_b.glb without running Blender, and checks the seven important blink/jaw/mouth/viseme control deltas, 163-joint skin attachment, 67 uniquely named targets, valid attribute formats, compatible target and bone names, and different actual exported base positions.

Also fixed the old tools/measure_glb_topology.py morph-motion measurement: in glTF, morph target POSITION is a **delta**, not an absolute position. The previous calculation could report motion for a zero delta. Sparse accessor support and synthetic zero/active/sparse controls were added.

**Evidence:** source and seven synthetic tests implemented in development branch, but not yet executed against the owner's existing GLB bytes. Do not report facial animation PASS until morph_signal_qa.json is produced, and do not interpret it as visual animation QA. Command: python tools/glb_morph_qa.py --folder output/identity_ab/20261112_045945_179772. See docs/IDENTITY_MORPH_SIGNAL_006.md. Character 001 likeness Phase-3 remains FAIL.

## Explicit next acceptance gates

1. **Owner Windows integrated smoke**: open the Studio, inspect actual neutral PNG, render a 30-frame MP4 and confirm it visually plays with audible speech; save `studio_run.json` and Blender diagnostics. Fail any stage that is black, visually incorrect, silent, or crashes. Repeat with `--mode demo` before release.
2. **M001 release candidate**: one full output with 1080×1920 video track, audio track, correct transcript, credible blink/jaw, and human-reviewed motion and sound. Preserve report, run ID and render timings.
3. **C001 geometric identity**: fit the baked neutral using reviewed **3D** and multi-angle camera constraints; validate rig/shape keys and independent global self-intersection checks; judge front, 45° and 90° clay/depth/normal views, rejecting wrong-identity controls. Current Phase-3 gate is FAIL.
4. **Appearance**: add hair, eyes, PBR skin and wardrobe on approved geometry; no image-on-shell identity shortcuts.
5. **Production**: phoneme-timed speech, subtitles, expressive motion, reproducible asset imports, reliable Windows packaging and diagnostic support.

## Engineering decisions

- Do **not** merge experimental Character 001 likeness into `main` while the Phase-3 gate is FAIL. The Studio alpha changes target the feature/experimental development branch.
- Avoid GitHub Actions while hosted-runner credits are unavailable. Prefer deterministic Python tests and the owner's actual Blender 4.5.10 measurements.
- Keep generated videos, GLBs, references and user image data outside Git.
- Never claim that 67 targets existing means the subject is photorealistic or that a soundtrack's MP4 track proves it is audible.

**Status interpretation:** LOCAL PYTHON PASS means synthetic/tooling tests ran, OWNER WINDOWS PASS means evidence was provided from the owner's machine; UNVERIFIED means no acceptable measured output is available. They are not interchangeable.
