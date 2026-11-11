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
