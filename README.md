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
tools/local_check.py      Zero-credit local tests, GLB and WAV checks
```

### Quick start (PowerShell)

For Windows PowerShell with Blender installed but not on PATH, first run:

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\\tools\\create_demo_voice.ps1
$script = (Get-Content .\\assets\\voice_transcript.txt -Raw).Trim()
python tools/local_check.py --glb .\\assets\\ours-photoreal.glb --audio .\\assets\\voice.wav --text $script --preview
```

The demo-voice helper uses Windows System.Speech, creates a matching transcript and WAV, and reports the actual duration. The local test command auto-detects Blender in `C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe`; alternatively specify `--blender "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe"`.

**If the demo voice is unavailable:** copy `livynth_demo_voice.wav` from the previously distributed smoke kit to `assets\\voice.wav` and use that kit's transcript. The demo is synthetic speech for pipeline testing, not final-quality narration.


Copy `our_avatar/assets/ours-photoreal.glb` to `assets/ours-photoreal.glb`. Prepare a **real spoken PCM WAV** at `assets/voice.wav`; match the text below to the audio.

```powershell
python tools/local_check.py --glb assets/ours-photoreal.glb --audio assets/voice.wav --text "Welcome to Livynth. Imagination comes alive here."
# Optional: run Python checks alone with `python tools/local_check.py`
python video/build_video.py --glb assets/ours-photoreal.glb --audio assets/voice.wav --text "Welcome to Livynth. Imagination comes alive here." --preview
# If output/livynth_m001.png looks correct, render the video:
python video/build_video.py --glb assets/ours-photoreal.glb --audio assets/voice.wav --text "Welcome to Livynth. Imagination comes alive here."
```

If Blender is not on PATH, provide `--blender "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe"`. If the face is oriented away from the camera, pass `--front positive-y`.

### M001.1: fast portrait and expression checks

The first real Blender 4.5 still succeeded but was overexposed and showed too much uncovered torso. The new **studio** preset crops toward the face, reduces light levels, includes a dark slate background and overlays a temporary navy shirt *material* on the existing torso mesh (no geometry or rig edits). Four diagnostic previews render in a single Blender process using 50% size and 16 EEVEE samples:

```powershell
git pull --ff-only
$script = (Get-Content .\assets\voice_transcript.txt -Raw).Trim()
python tools/local_check.py --glb .\assets\ours-photoreal.glb --audio .\assets\voice.wav --text "$script" --preview-set
```

Inspect `output/livynth_m001_neutral.png`, `_half_blink.png`, `_full_blink.png` and `_smile.png`. This is **local QA**, not yet photoreal or final video quality. See [the M001 checklist](docs/M001.md) for a one-second MP4 smoke test before rendering the entire 14-second clip.

### No GitHub Actions required

GitHub Actions was disabled because the account has no runner credits. Run `python tools/local_check.py` on Windows or Linux to compile, run unit tests, inspect an optional GLB, and check an optional WAV-to-timeline run. Add `--preview` to invoke Blender when installed. None of these checks use GitHub-hosted runners.

### Current validation status

- Python syntax and 11 unit tests passed in the code-authoring environment using a local equivalent implementation.
- A previously supplied **V32 GLB** was inspected and found to have the required facial shapes. The actual local `our_avatar/assets/ours-photoreal.glb` was **not** available in this environment.
- Blender is not installed in this code-authoring environment, so the complete skin/render/audio result is **unverified**.
- Mouth animation is **spelling + WAV energy guided**, not phoneme-accurate. Subtitles and real lip-sync alignment are acceptance tasks still to complete.

See [M001 milestone details](docs/M001.md).

## Development principles

Build end-to-end capabilities before feature sprawl. Keep assets and provenance records. Separate facial geometry, animation, speech and rendering. Do not claim photoreal or synchronized final output until inspected.
