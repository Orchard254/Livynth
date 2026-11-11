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
