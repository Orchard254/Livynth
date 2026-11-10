# LIVYNTH

**Give Imagination Life.**

LIVYNTH is a long-term digital-human and AI video creation project. Our ambition is to build original, expressive 3D characters and a reproducible video-production engine.

## M001 — First Living Human

The first goal is a **12–15 second vertical (1080×1920, 30 fps) talking-human MP4**. Reuse the existing `our_avatar` photoreal character: the external audit confirms it has 52 ARKit face shapes and 15 Meta speech visemes, but **no bones, skins or embedded animation clips**. A skeleton is *not* required for a stationary talking portrait.

This branch contains the first implementation; it is **not yet a finished rendered video**.

### Repository layout

```text
assets/                  Local GLB and WAV assets (ignored by Git)
video/model_check.py     Read-only GLB facial-morph contract test
video/make_timeline.py   PCM WAV + transcript → face-animation JSON
video/render_talk.py     Blender 4.5 batch portrait + narration renderer
video/build_video.py    WAV → timeline → Blender single-command driver
tests/test_timeline.py   Deterministic Python tests
docs/M001.md             Detailed setup, limitations and acceptance gates
.github/workflows/       Python checks on every pull request
```

### Quick start (PowerShell)

Copy `our_avatar/assets/ours-photoreal.glb` to `assets/ours-photoreal.glb`. Prepare a **real spoken PCM WAV** at `assets/voice.wav`; match the text below to the audio.

```powershell
python -m unittest discover -s tests -v
python video/model_check.py --glb assets/ours-photoreal.glb
python video/build_video.py --glb assets/ours-photoreal.glb --audio assets/voice.wav --text "Welcome to Livynth. Imagination comes alive here." --preview
# If output/livynth_m001.png looks correct, render the video:
python video/build_video.py --glb assets/ours-photoreal.glb --audio assets/voice.wav --text "Welcome to Livynth. Imagination comes alive here."
```

If Blender is not on PATH, provide `--blender "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe"`. If the face is oriented away from the camera, pass `--front positive-y`.

### Current validation status

- Python syntax and 11 unit tests passed in the code-authoring environment using a local equivalent implementation.
- A previously supplied **V32 GLB** was inspected and found to have the required facial shapes. The actual local `our_avatar/assets/ours-photoreal.glb` was **not** available in this environment.
- Blender is not installed in this code-authoring environment, so the complete skin/render/audio result is **unverified**.
- Mouth animation is **spelling + WAV energy guided**, not phoneme-accurate. Subtitles and real lip-sync alignment are acceptance tasks still to complete.

See [M001 milestone details](docs/M001.md).

## Development principles

Build end-to-end capabilities before feature sprawl. Keep assets and provenance records. Separate facial geometry, animation, speech and rendering. Do not claim photoreal or synchronized final output until inspected.
