# LIVYNTH STUDIO-005 smoke — independent MP4 review (2026-11-12)

**Inputs:** owner-uploaded `livynth_smoke.mp4` (56,920 bytes), `studio_run.json` after Windows Blender 4.5.10 smoke. The video and private user assets stay outside Git.

## Evidence tested independently

Command-line inspection with FFprobe, FFmpeg and OpenCV of the **actual uploaded media**, not only the Studio log:

| Test | Evidence |
|---|---|
| Decode | FFmpeg decoded all video/audio streams without errors |
| Video | H.264 High, YUV420p, BT.709; **540x960** portrait, **30/30 frames**, **30 fps**, **1.000 s** |
| Audio | AAC LC, stereo, 48 kHz, **1.002 s** track |
| Audio signal | Decoded mono RMS **-22.69 dBFS**, peak **0.636**, nearly silent first 100 ms followed by substantial signal |
| Mouth motion | Human-visible opening/closing; mean absolute change in central mouth ROI versus frame 1 approximately 8–10 grayscale steps in multiple sampled frames (not a phoneme score) |
| Frame integrity | No decode failures in the 30-frame sequence |
| Narration source | Studio run reports generated 10.7476-second PCM WAV with 7.7965 seconds active signal; it was rendered only over first second in smoke |
| Export status | Studio returned `PASS_ARTIFACTS_NOT_IDENTITY` and included both MP4 audio/video tracks |

**Limitations:** Codec and signal checks do not prove intelligible speech, audio-video phoneme alignment, real material quality or the original Character 001 identity. No full 10.75-second video has been reviewed. The fixed timeline does not blink until 2.15 seconds; a blink cannot appear in a 1-second smoke.

## Visual findings from uploaded frames

- **Identity: NOT ACCEPTED.** The neutral MPFB model is a different generic adult, bald and without realistic hair/eyes/skin. Existing C001 Phase-3 gate remains **FAIL**.
- **Portrait crop: FAIL presentation.** At 540x960, the face is small relative to the upper torso; the shot is not a facial-performance close-up.
- **Look development: FAIL presentation.** The neutral face and shirt are similarly blue-gray, underlit, difficult to read, and there is no convincing independent fabric/skin separation.
- **Facial motion: BASIC PASS.** Jaw/lips open and move, but timing, viseme quality, and blinking beyond the first second need separate review.
- **Audio: SIGNAL PASS, speech quality UNVERIFIED.** AAC audio is non-silent and decodes; no human listening certification or phoneme error scored.

## STUDIO-006 reversible proposed correction

Keep the original GLB, rig, 163 bones, 67 facial morph targets and camera front axis unchanged. Only in Blender's imported preview scene:
1. Aim higher and narrow the orthographic framing (`camera_drop` 0.11 -> 0.06 and `ortho_scale` 0.29 -> 0.215).
2. Apply separate warm **neutral clay** (not identity-colored skin) and navy shirt materials per imported polygon; ensure both categories exist.
3. Raise Studio-only light intensities and exposure moderately, leaving the legacy preset unchanged.
4. Review one cheap still (CLI `python livynth_studio.py --cli --mode preview`) **before** attempting another 30-frame render or full-length output.

**Not a quality pass:** the correction is source-level and pure-Python QA; it requires actual Windows Blender preview review to accept framing, lighting, expression appearance and saved media.
