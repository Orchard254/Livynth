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

## IDENTITY-006 owner Windows morph-signal gate: PASS (2026-11-12)

The owner pulled the development branch at 8a25fff and supplied a full Windows run:

- Application suite: 176 total, **174 PASS / 2 skipped / 0 failed**.
- Geometry suite: 174 total, **172 PASS / 2 skipped / 0 failed**.
- Combined: **346 passed / 4 skipped**, complete local_check PASS.
- Existing files demo_head_a.glb and demo_head_b.glb passed the strict exported morph-signal test:
  status PASS_NONZERO_EXPORTED_MORPH_SIGNAL_NOT_VISUAL_ANIMATION.
- Each contains 163 matching joints, 67 matching morph names, 14,517
  seam-expanded glTF vertices, nonzero eyeBlinkLeft/Right, jawOpen, mouthClose,
  mouthPucker, viseme_aa and viseme_PP vertex deltas.
- Different exported coordinates in **4,576 vertices** at >0.1mm,
  maximum A/B difference **20.8193mm**.

**Interpretation:** Two distinct GLBs preserve the same rig/morph controls,
and those seven facial controls have measurable exported deformation.
Natural visible blinking, mouth closure and speech articulation remain
UNVERIFIED. Character 001 Phase-3 likeness remains FAIL.

## IDENTITY-007 — matched rendered-expression gate (2026-11-12)

Implemented a Blender CLI for front and three-quarter images of existing
A/B GLBs, reusing Studio preview lighting and camera. A single Python command
generates **20 diagnostic stills** plus an HTML side-by-side gallery, refusing
incompatible GLBs, absent/identical rendered expressions, malformed PNG
payloads and missing images. Fifteen hermetic tests were authored for the
new pose contract, pixel detection, image integrity and runner orchestration.
The authoring environment lacks Blender; **new test suite and actual Windows
pose rendering NOT VERIFIED yet**.

Run on the owner PC without rebuilding GLBs:

    python tools/run_identity_pose_review.py --folder output\identity_ab\20261112_045945_179772

See docs/IDENTITY_RENDERED_POSE_007.md. Even a complete render manifest
means CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW, not approved likeness or animation.

## IDENTITY-007 owner Windows rendered pose A/B: capture PASS (2026-11-12)

Owner ran python tools/run_identity_pose_review.py against the **existing two GLBs**
using Blender 4.5.10 / MPFB build 20261010, after pulling commit 42c8f1b.
Both Blender processes completed normally. Each character rendered seven front
(neutral, blink, jaw_open, viseme_aa, viseme_pp, smile, pucker) and three
three-quarter (neutral, blink, jaw_open) views, producing **20 PNG stills total**.
All **16 non-neutral poses** were flagged SIGNAL_PRESENT_NOT_VISUAL_APPROVAL by
the face-crop pixel QA. Aggregate pose_review.json:
CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW, existing GLB morph signal PASS,
raster signal PASS_VISIBLE_DIFFERENCES_NOT_VISUAL_QUALITY,
expression_naturalness PENDING_HUMAN_REVIEW.

**The log is not the PNGs.** Independent checks for eye closure, clean jaw
motion, lip contact and morphological naturalness remain PENDING until the
rendered images are actually inspected; no full narrated video, hair/skin
realism or identity likeness is claimed from this numeric result.

## IDENTITY-008 — package existing pose images for visual review

New tools/package_identity_pose_review.py assembles the existing 20 PNGs,
the two Blender reports, pose_review.json, a reconstructed side-by-side
index.html and a SHA256 manifest into a portable ZIP. It validates image
payloads and report coverage, blocks symlinks, and deliberately excludes the
original GLBs and private reference photographs. Seven unit tests are
authored for missing/corrupt poses, overwrite refusal and whitelist
isolation; actual packager runtime not yet reported. The original JSON
reports retain local Windows paths for provenance, so review them before
sharing.

Command (no rerender):
python tools/package_identity_pose_review.py --folder output\identity_ab\20261112_045945_179772\pose_review\20261112_060832_140286

See docs/IDENTITY_REVIEW_PACK_008.md. Character 001 five-view likeness
Phase-3 remains **FAIL**.

## Independent 20-image two-character visual review (2026-11-12)

Owner uploaded the 5,161,863-byte `20261112_060832_140286.zip`, containing
20 original 400×600 PNGs, two Blender reports, the run summary, a gallery
and SHA256 manifest. All 24 manifest entries independently matched their
actual ZIP content hashes and sizes.

**BASIC REUSABLE STATIC FACE POSES PASS**: both manually configured heads
show closed eyelids on full blink, attached lips/chin in jaw-open and AA
poses, distinct lip closure/pucker/smile, and broadly coherent neutral/blink
and jaw-open three-quarter views. The A/B jaw silhouettes differ. The
original 16/16 raster-signal checks therefore have visual support.
**Human appearance FAIL**: eye openings lack finished eyeballs/irises/pupils;
open oral cavity shows stippled interior without credible tongue/teeth;
hair and photoreal skin are absent and torso lacks visibly separated navy
garment. Natural temporal animation/lip-sync UNVERIFIED because only static
poses were reviewed. Character 001 source-image likeness Phase-3 remains FAIL.

See `docs/IDENTITY_VISUAL_REVIEW_008.md` for detailed evidence and
the explicit presentation vs reusable-control decision. Source render ZIP
and user reference photos remain outside the repository.

## IDENTITY-009 — MPFB native fitted-anatomy asset availability (2026-11-12)

Official MPFB supports fitted eyes, teeth, tongue, eyebrows/eyelashes,
hair and clothing via its native MHClO asset system. Rather than invent
unverified procedural eye spheres or hand-paint an oral opening, a new
**read-only** Blender asset inventory identifies the installed bodypart
files and whether the required eyes, teeth and tongue assets exist. It
does not install assets, modify the characters, download weights, or claim
that native assets are rigged into either GLB.

One command on the existing Windows environment:
`python tools/probe_mpfb_assets.py`

The report records category availability, file hashes and relative paths
(without absolute local asset directories). If assets are missing it
reports MISSING_REQUIRED_ANATOMY_ASSETS; if present it reports
ASSETS_AVAILABLE_FOR_FITTING_TESTS, not rendering quality PASS.
**11/11 focused local pure-Python and simulated runner tests passed.**
Actual MPFB installed-library probe on owner's Windows remains UNVERIFIED.

**Next:** after the inventory identifies available assets, attach fitted
eyes/teeth/tongue as an optional appearance layer, then repeat the A/B
neutral/blink/jaw/AA/PP still checks. Preserve the 163-joint/67-morph
base-contract and treat all asset licenses as review-before-commercial-use.
Image-to-identity reconstruction remains a separate unsolved gate.

## IDENTITY-009 owner-installed anatomy inventory: PASS (2026-11-12)

Owner uploaded the real Blender 4.5.10 LTS `mpfb_asset_inventory.json`
after the read-only probe. **ASSETS_AVAILABLE_FOR_FITTING_TESTS**,
system_assets_pack_installed=true, no missing required eyes/teeth/tongue.
Installed options: **2 eyes, 6 teeth, 1 tongue, 12 eyebrows,
4 eyelashes, 10 hair, 20 clothing, 23 skin presets = 78 total**.

The inventory reports **assets_fitted_to_body NOT_TESTED** and
**exported_rig_compatibility NOT_TESTED**. It does NOT prove the
eye, oral or garment surfaces actually work on either deformed GLB,
and their asset licenses still require commercial-use review.

## IDENTITY-010 — isolated native MPFB fitted-anatomy prototype

Implemented a pinned, SHA256-verified selection of high-poly eyes,
teeth_base and tongue01 based on owner's installed file inventory.
New `tools/run_native_anatomy_probe.py` starts Blender with fresh
disposable MPFB human + built-in rig, uses documented
`HumanService.add_mhclo_asset`, checks the three real scene objects
and saves 480x720 front and three-quarter PNG previews and an audit JSON.
This does not modify existing A/B GLBs or the production renderer.

**12 regression tests authored**, covering plan validation, real asset
hash mismatch, path traversal, file absence, missing attached meshes,
PNG corruption and overwrite controls. These tests and the new Blender
probe have not yet been run against owner's Windows installation;
do not claim fitting success until the output is reviewed.

The probe intentionally uses the reference human's **broad MPFB macros**,
not the six detailed head-shape coefficients. Passing this first gate
would demonstrate installed asset integration only; attachment to both
deformed identities, 163-joint/67-target GLB preservation, jaw movement
and eye alignment are subsequent measured gates. Source documentation:
`docs/IDENTITY_NATIVE_ANATOMY_010.md`.

Next one-command Windows check:
`python tools/run_native_anatomy_probe.py`
after pulling the development branch. **Character 001 image-reconstruction
Phase-3 remains FAIL.**

## IDENTITY-010 owner Windows native anatomy attachment: PASS (2026-11-12)

The owner supplied anatomy_probe.json and actual 480×720 neutral front and
three-quarter images. All three selected native MPFB assets are present,
fitted and armature-bound to Human.rig: high-poly blue eyes (1,064 vertices,
1,020 faces), teeth_base (3,868 vertices, 3,560 faces) and tongue01
(226 vertices, 224 faces). Rig has 163 bones. Iris/eyeball surfaces are
visibly present and roughly aligned. Teeth and tongue remain hidden by
closed lips and have NOT been evaluated during jaw/lip motion.

The raw unbaked source body has 19,158 vertices; the existing detailed
baked Head A/B GLBs have 13,380 native body vertices. This is expected
staging, not proof of compatible detailed identity or export.
IDENTITY-010 attachment success does NOT test body head_shape variation,
facial morphs, GLB export or independent photographic likeness.

## IDENTITY-011 — fitted native anatomy across BOTH detailed facial identities

A new isolated experimental runner constructs a fresh rigged human with
the exact SHA-pinned eyes/teeth/tongue, duplicates through ExportService,
bakes the body, applies each detailed head_shape, builds the 67 familiar
facial targets and captures matched neutral, blink, jaw and viseme stills
for demo_head_a and demo_head_b. It verifies the native body topology,
source/fitted fingerprints, copied asset armature binding and 163/67
contracts. On success it packages twelve PNGs plus reports/gallery into
a portable ZIP. The existing successful GLBs are never modified.

**Status: newly authored code and ten focused tests; Windows Blender
integration and new unit suite NOT RUN yet.** The tool intentionally
does not call a pose sequence an expression quality PASS. Visual inspection
is needed to see whether rigged tongue/teeth follow morph-only jaw movement.
Original Character 001 five-angle likeness Phase-3 remains FAIL.

Owner next one-command gate after pull:
python tools/run_anatomy_ab_review.py
See docs/IDENTITY_ANATOMY_AB_011.md.
## IDENTITY-011 owner Windows A/B anatomy poses: visual FAIL (2026-11-12)

Owner uploaded 20261112_071835_969382.zip (3,161,955 bytes); all
16 SHA256-manifested ZIP files independently verified. Both different
heads have unchanged source body hash/topology, 13,380 native vertices,
13,378 quads, 163 joints and 67 morphs, plus three rig-bound MPFB assets.
Blender rendered all 12 requested front and three-quarter pose stills.

**INDEPENDENT VISUAL VERDICT:** Head A's eyes are roughly seated and blink
closes; Head B's eyeballs visibly protrude, failing eyelid alignment
and blink. Head B also shows detached red/oral artifacts near nose and
mouth during jawOpen/AA. Eye/teeth/tongue bone attachment being present
does NOT prove alignment when facial identity changes. Production anatomy
approval = FAIL. Actual red artifact object identity remains unverified.
See docs/IDENTITY_ANATOMY_ALIGNMENT_012.md.

## IDENTITY-012 — shared body identity deformation on copied anatomy

Added opt-in --align-accessories for the existing isolated
tools/run_anatomy_ab_review.py. The same six facial shape fields are
evaluated on copied eye, teeth and tongue vertices using fixed native
body bounds and body-local transforms. No original files, rig weights
or GLBs are edited. Blender will record per-asset displacement and
float32 re-read checks and render the same 12 pose images for objective
comparison. Added 11 focused regression tests for the shared spatial
reference, opt-in separation, and invalid/missing audit controls.

**NEW BLENDER RUN AND THESE TESTS NOT EXECUTED YET ON WINDOWS.**
No guarantee this correction succeeds: it could worsen Head A or
leave teeth/tongue fixed relative to jawOpen, since jaw is a morph.
After verification, request the resulting ZIP for review. Keep
Character 001 five-view likeness Phase-3 FAIL and main untouched.
## IDENTITY-012 independent static anatomy alignment PASS — 2026-11-12

Owner submitted 20261112_074842_628509.zip, SHA256
`68a86213bc91efaa81726760fa5df2d788548c36741375b0e327ceb5d91e8e0b`.
All 16 manifest files independently matched actual ZIP contents. Twelve
rendered poses were compared to the previous failing archive
`20261112_071835_969382.zip`: Head B's protruding neutral eyes are
corrected, its full-blink now covers the eyeballs, and the detached red
fragments beside the nose/mouth are no longer visible in jawOpen/AA.
Head A's previously good neutral eyes and full blink remain intact.

Both identities remain structurally compatible: identical source neutral
SHA and 13,378-quad topology, 13,380 baked body vertices, 163 bones,
67 identical named facial targets, distinct detailed head shape hashes.
All attached anatomy vertex counts/armature bindings are preserved.
**Verdict: PASS for static detailed-face anatomy alignment ONLY.**
Realistic oral appearance, bone/shape morph jaw coordination, temporal
animation and photographic Character 001 likeness remain unapproved.
Full before/after review in docs/IDENTITY_ORAL_MOTION_013.md.

## IDENTITY-013 — evaluated teeth/tongue jaw-follow diagnostic

The body receives jawOpen/AA morph targets whereas teeth/tongue are
separate armature-bound meshes. Existing success proves static positioning,
not that the oral meshes move when only body morph weights change.
Added opt-in `--audit-oral-motion` to the working A/B anatomy review.
Blender snapshots dependency-graph evaluated world-space vertices for
body, teeth and tongue in neutral, jawOpen and AA poses. Reports
separate body-morph-inert, oral-assets-static, partial and motion-present
outcomes, with exact per-mesh displacement metrics and consistency gates.

Fourteen focused regression tests are authored but have NOT been run
on the owner's Windows checkout. Blender motion audit is also NOT RUN.
The original no-flag run and existing GLBs are unchanged. On Windows:

    python -m unittest discover -s tests -p "test_anatomy_motion_audit.py" -v
    python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion

The new ZIP contains the same 12 diagnostic stills and numerical
body/teeth/tongue motion evidence. If the body morphs but oral meshes
stay still, implement jaw/corrective retargeting with a separate gate.
Do not weaken the strict 163/67, shape and static alignment checks.
Image-driven five-view likeness remains Phase-3 FAIL.
## IDENTITY-013 owner Windows jaw/tongue motion: FAIL (2026-11-12)

Uploaded `20261112_081501_619229.zip` SHA256
`3d5da86c4b927f71f06c29b80f877359ab8556948848498b595861e58c765aad`.
All 16 manifest-listed ZIP files were independently verified.
The real Blender evaluated-mesh motion reports show for BOTH heads:

- `jawOpen`: 2,121 BODY vertices moved, maximum 32.927631mm;
  teeth and tongue moved **0.0mm**.
- `viseme_aa`: 1,967 BODY vertices moved, maximum 16.340069mm;
  teeth and tongue moved **0.0mm**.
- Four separate `FAIL_ORAL_ASSETS_STATIC_WHILE_BODY_MORPHS` outcomes.

**Confirmed root cause:** attached oral assets receive the
static identity alignment from IDENTITY-012 but are not driven
by the BODY's jawOpen/AA shape-key values. Bone attachment alone
cannot propagate another mesh's morph channel. The 163-bone
and 67-body-morph contracts remain intact. Do not count this
as successful lip-sync or natural mouth motion.

## IDENTITY-014 — opt-in oral corrective morph experiment

New `character/oral_correctives.py` extracts bounded lower-mouth
translation from existing BODY jaw/AA shape-key geometry, then
creates oral-only shape keys with matching channel names
(`jawOpen`, `viseme_aa`) on the COPIED MPFB teeth/tongue.
Tongue translates together; a conservative soft z-based mask
moves lower dentition while preserving upper teeth as much as possible.
The same weights are applied explicitly to body and oral assets.

New runner flag `--oral-correctives` requires BOTH
`--align-accessories` and `--audit-oral-motion`; the existing
source GLBs, 163-joint rig, 67 body morphs and no-flag runs
remain unchanged. A fresh 12-image ZIP and evaluated-mesh
movement report let us reject bad jaw contact rather than
claim success from nonzero numbers.

12 pure-Python focused tests passed locally, including
the original verified neutral mesh landmark-anchor case.
13th optional owner-mesh test is skipped when the private
NPZ ZIP is not present in a normal checkout.
New Windows Blender corrective render/QA **NOT RUN**.
Reference `docs/IDENTITY_ORAL_CORRECTIVES_014.md`.

Next owner command: 
`python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion --oral-correctives`.
Keep Character 001 five-angle photo-likeness Phase-3 FAIL.
## IDENTITY-014 owner Windows oral-corrective motion PASS, mouth appearance FAIL (2026-11-12)

Owner submitted real A/B Blender evidence `20261112_083529_509207.zip`
(SHA256 `24d83c24a34ea8b979088f0ca5cef4f5b0268e8a023ae8267c8d36de33def167`).
All 16 manifest-file SHA256 hashes verified. Both heads still use the
original 13,380-vertex native body, 13,378 quads, 163 joints and 67
face target names; distinct detailed head geometries remain intact.

The formerly motionless teeth and tongue NOW MOVE in both heads:

- A jawOpen: 2,201 dental + 226 tongue vertices, max 17.762mm.
- A AA vowel: 2,187 dental + 226 tongue vertices, max 8.827mm.
- B jawOpen: 2,235 dental + 226 tongue vertices, max 17.818mm.
- B AA vowel: 2,214 dental + 226 tongue vertices, max 9.284mm.

**Result:** the original IDENTITY-013 oral-motion disconnect is
resolved in the experimental Blender scene. **Visual FAIL:** the mouth
shows dense, unnatural upper/lower dental surfaces and exposed pink
oral tissue. The continuous tooth Z-height mask can split individual
tooth/gum surfaces during motion; numerical movement alone does not
approve oral realism. See docs/IDENTITY_DENTITION_015.md.

## IDENTITY-015 — source-proven upper/lower tooth assignments

The documented MakeHuman HM08 basemesh provides explicit lower-teeth
helper vertices 14992..15059 and upper-teeth helpers 15060..15127.
The native teeth_base MHCLO stores each tooth vertex's original
basemesh reference indices/weights. New opt-in segmentation reads
those original assignments, validates an exact source-to-copy
vertex order, requires disjoint upper/lower tooth faces and assigns
**rigid, binary** whole-jaw movement rather than interpolating each
tooth vertex by its final 3D height.

Code: character/mhclo_dentition.py, optional lower-teeth mask in
character/oral_correctives.py, and `--mhclo-dentition` in
tools/run_anatomy_ab_review.py. The new flag requires all existing
alignment, oral-corrective and world-space motion checks. Both A/B
reports must show identical source mapping SHA, stable rig/morph
contracts, 12 image poses and matching dental movement counts.

**10 pure local mapping/negative tests passed; four more repository
tests authored.** New Blender installed-asset mapping and rendering
NOT YET RUN, and visual outcome NOT VERIFIED. If actual MHCLO
references differ or mesh topology bridges upper/lower jaws, the
tool deliberately reports failure rather than guessing. Next:

    python -m unittest discover -s tests -p "test_mhclo_dentition.py" -v
    python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion --oral-correctives --mhclo-dentition

Character 001 photographic identity likeness remains Phase-3 FAIL.
## IDENTITY-015 owner Windows signed/weight mapping integration: FAIL (2026-11-12)

Owner pulled development commit c44f6c1 and ran 14/14 focused
`test_mhclo_dentition.py` cases successfully. The first actual
Blender 4.5.10 / MPFB 20261010 Head A run then failed
at `character/mhclo_dentition.py:E_MHCLO_BAD_WEIGHTS`
before rendering. The follow-on anatomy_pose_report.json
FileNotFoundError is consequential: Blender exited without output.
Earlier MPFB procedural eye material node socket warnings did not
stop object import and are tracked separately.

**No IDENTITY-015 jaw segmentation PASS / visual result exists.**
The installed teeth_base MHCLO's actual numerical coefficients were
not included in the console log. Synthetic weight-positive unit
tests therefore did not model this real asset.

## IDENTITY-016 — source-weight attribution fix and cheap asset preflight

Previous validation wrongly combined two separate requirements:
MHCLO interpolation coefficients were required to be nonnegative
and sum to one, even though our jaw classification only requires
the **significant source vertices** to come from one helper group.
New mapping assigns upper/lower by absolute coefficient contribution
from documented HM08 helper references. It still rejects mixed
jaws, non-dental source contribution, all-zero/invalid weights
and mixed-jaw faces. It records signed and nonunit-weight counts.

Added an MPFB metadata-only installed-teeth preflight that checks the
pinned source SHA, parses its referenced OBJ topology and MHCLO
weights, and writes a small diagnostic JSON even on mapping failure.
Does not construct a human, render, or change GLB files.
Five new jaw-mapping negative/positive tests and eleven
metadata/runner tests authored, **not yet run on Windows**.

First owner action after pulling development:

    python -m unittest discover -s tests -p "test_mhclo_dentition.py" -v
    python -m unittest discover -s tests -p "test_mhclo_dental_preflight.py" -v
    python tools/run_mpfb_dental_preflight.py

Only if status is PASS_REAL_MHCLO_JAW_GROUP_MAPPING_NOT_VISUAL_QA
proceed with the original IDENTITY-015 Blender A/B render.
On failure upload `dentition_probe.json` and do not repeatedly
rebuild the two characters. See docs/IDENTITY_DENTAL_PREFLIGHT_016.md.
Character 001 source-photo five-view gate remains FAIL.
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

## IDENTITY-025 — Head A mouth anatomy (2026-11-12)

Opt-in fix behind `--oral-anatomy`: upper-arch seat -0.022 m, tongue seat -0.016 m (rigid translations, all Blender 4.5 shape-key blocks translated together), and a BVH first-hit front-opening selection that gives the exposed mouth interior a dark oral-cavity material (16 polygons). Measured after fix: upper arch z 1.546-1.567 in all poses (was entirely above the opening), oral assets touch without interpenetrating (min 0.001-0.118 mm), jaw-open/neutral/speech stills render an anatomically plausible mouth with no neck-edge artefacts, `PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA` preserved after the fix, 391/391 repo tests pass. Original GLBs/assets untouched. Visual quality still PENDING_INDEPENDENT_REVIEW; no likeness claim. Detailed evidence: `docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_025.md`.

## IDENTITY-026 — Head A mouth anatomy, second pass (2026-11-12)

Opt-in follow-up on the same branch/`--oral-anatomy` path covering the four review findings. (1) Unnatural pink surface: tongue diffuse desaturated/darkened on the copied node tree (HSV ×0.55/×0.72) and the copied teeth diffuse's gum texels (27.81% of pixels, texel-mask R≫G,B) reblended 80% toward a dark brick tone in an in-memory image copy — tooth texels bit-identical; installed MPFB files untouched. (2) Oversized dental appearance: copied teeth asset uniformly scaled 0.85 about its body-space centroid (all 3 key blocks). (3) Sharp lower-lip contour: 101 front sulcus vertices lifted ≤10 mm toward the lip (quartic falloff, z∈[1.462,1.522]) with a hard anti-collision invariant (margin 0.0395 m). (4) Cavity-selection mismatch: BVH candidates AND the depth/z/normal filter now run in the same evaluated jawOpen=0.85 pose, and the evaluated↔base polygon mapping is validated (13,378 loop-vertex tuples) — never assumed. New exact Möller transversal-crossing audit (with world-space locations and onto-other-plane depth proxies, across neutral/jaw-open/viseme_aa/viseme_pp): 12 arch-arch facet crossings in rest poses (6 in viseme_aa; designed occlusal interlock, untouched asset had 0 — see trade-off in the doc; locations ±0.0137 m, depth 2.6–4.3 mm) and tongue↔teeth crossings reduced from 168/201 to 46 (jaw-open/viseme_aa) / 82 (rest) with 1.6–8.2 mm depths. `PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA` preserved (lower 15.10 mm post-scale, upper stationary). 454/454 repo tests pass; local_check and branch_audit exit 0; `main` untouched. Visual quality still PENDING_INDEPENDENT_REVIEW; no likeness claim; GLB export NOT_TESTED. Detailed evidence: `docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_026.md`.

## IDENTITY-027 - Head A mouth anatomy, third pass (2026-11-12)

Millimetre-scale collision detector CORRECTED (the old absolute barycentric-area epsilon 1e-9 silently rejected genuine crossings on the ~2-6 mm oral facets; now relative 1e-12 angle/area tolerances): arch-arch crossing counts re-measured (before 12/6/12 -> after 1039/768/369 jaw-open/viseme_aa/rest; depths 2.6-4.7 mm). Tongue<->teeth intersections RESOLVED TO ZERO in all four poses by pinned tongue changes (seat 0.036, posterior +0.010 m shift, scale 0.80; tongue<->teeth clearance now 4.5-5.0 mm) with no visible appearance change vs the reviewed renders. Material isolation now PROVEN per slot: single-user material copies on the copied scene, SHA-256 of TexImage pixels and on-disk image files before/after (unchanged), original node counts unchanged, installed .mhclo files re-verified against the pinned inventory digests (all unchanged); the runner contract fails the run if isolation is not proven. Arch<->arch interpenetration is the designed occlusal interlock and is UNRESOLVABLE without sacrificing the reviewed appearance (seat sweep 0.012 -> 402/2122/1727, non-monotonic; 0.022 kept); honestly documented. Five fresh renders + JSON + ZIP (output/mouth_anatomy/20261112_194331_962942/); 465/465 repo tests pass (104 mouth-anatomy); local_check/branch_audit exit 0; main untouched. GLB export NOT_TESTED; no likeness/photorealism claim; visual quality PENDING_INDEPENDENT_REVIEW; arch-arch remains by owner-facing trade-off, re-measured accurately. Detailed evidence: docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_027.md.

## IDENTITY-028 - Head A permanent dentition rebuilt (2026-11-13)

IDENTITY-025/026/027 photo-slab teeth REPLACED in renders by a parametric permanent dentition (32 teeth, FDI numbering, adult-average anthropometry, arc-length arch walk, curve of Spee, 2.5 mm lingual overjet, 1.5 mm rest freeway gap; 7 712 verts + 2 gingival bands with scalloped margins; anterior/posterior enamel pair; all materials fresh; upper arch frozen, lower arch rides the native body jaw morph; slab hidden from renders, never edited/exported). Lip-opening border corrected (corners +1.6 mm quartic, lower roll +2.2 mm; 68 key blocks moved, max storage error 5.8e-8 m). MEASURED ZERO transversal crossings (arch-arch AND tongue-teeth) in all four poses (was 1039/768/369 on the slab); tongue-teeth min clearance 2.5-4.7 mm; arch-arch min clearance 2.4-13.9 mm. PASS_PROCEDURAL_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA; ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED for the visible lower arch; installed .mhclo re-verified unchanged; material isolation verified. Five fresh renders + JSON + ZIP under output/mouth_anatomy/id028_20261112_4/. 488/488 repo tests pass (18 procedural-dentition + 5 LipOpening + prior); local_check/branch_audit exit 0; main untouched. No likeness claim; visual quality PENDING_INDEPENDENT_REVIEW. Detailed evidence: docs/IDENTITY_HEAD_A_MOUTH_ANATOMY_028.md.


