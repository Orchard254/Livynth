# LIVYNTH Studio 0.1 — local Windows character-to-video alpha

**Release status: local desktop integration alpha, NOT the final photorealistic digital-human product.** The original Character 001 likeness gate is **FAIL**. The neutral character is an explicitly generic MPFB placeholder, not an approved likeness. No full Blender video render has been verified in the author's environment.

## What the owner can do

After updating the experimental LIVYNTH branch, **double-click `Start_LIVYNTH_Studio.bat`** in the repository folder. The Studio provides a basic Windows window with a text script, optional files for an existing GLB and WAV, an optional Blender path, and three actions:

1. **Preview portrait** — generate a local neutral MPFB rigged character if no GLB was selected, generate Windows test narration if no WAV was selected, build a timeline and render one 50%-scale PNG preview.
2. **Test 1-sec video** — produce one 30-frame MP4 smoke artifact, to avoid spending time on a full 420-frame run before the renderer is proven.
3. **Export full MP4** — Blender renders the whole timeline (default 1080x1920, 30 fps) and attempts to embed the narration. This requires the preview/smoke to be visually and audibly checked first. The runner checks MP4 container integrity, presence of separate video and audio tracks, and recorded video dimensions. This is NOT a listening, lip-sync, or image-quality test.

The existing `video/build_video.py` and `video/render_talk.py` remain the production back end. Assets are created in `output/studio/YYYYMMDD_HHMMSS_microseconds/` and are ignored by Git. The desktop interface doesn't upload files or call paid services. Creating a neutral human requires Blender 4.5 + MPFB extension installed in the user's Blender profile; built-in Windows voice requires Windows PowerShell 5.1 and System.Speech. An existing GLB/WAV can bypass either generation step.

A production run writes `studio_run.json` that says `PASS_ARTIFACTS_NOT_IDENTITY` only if expected artifacts pass basic format/structural checks. The report marks `identity_likeness` as **UNVERIFIED** and `video_audio_stream` as **TRACKS_PRESENT_UNVERIFIED_PLAYBACK** only after structural audio and video track checks pass. Actual speech audibility and lip-sync remain manual/product QA gates.

## Testing and acceptance

- `python -m unittest tests.test_studio -v` — pure Python orchestration negative/control tests (headless, no Blender necessary).
- `python tools/local_check.py` — full local suites (no GitHub Actions credits).
- `python -m unittest tests.test_mp4_probe -v` — MP4 structural failure-injection tests.
- A locally generated FFmpeg H.264/AAC sample was independently verified by the MP4 parser in the authoring environment. This is **not** a Blender smoke-test result.
- On owner's Windows PC: open the Studio; create a neutral character, visually review the portrait and 1-second MP4 with audio. Do not mark M001 finished until one full 12-15-second video is produced and listened to.

CLI optional: `python livynth_studio.py --cli --mode smoke --text "Welcome to Livynth"`.

## Unfinished final-product requirements

Character 001 accurate geometry, approved five-view likeness, hair/eyes/materials and realistic wardrobe; rigorous self-intersection/skin/morph QA; phoneme-aligned lips, natural motion, subtitles, complete 1080x1920 MP4 audio QA and a reliable distribution/installer. These are **not** silently satisfied by a working button.