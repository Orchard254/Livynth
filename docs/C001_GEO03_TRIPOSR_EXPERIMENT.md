# C001-GEO-03 Lane A — TripoSR neural reconstruction experiment record

**Date:** 2026-11-11
**Agent:** neural-reconstruction (subagent, LIVYNTH C001-GEO-03 Lane A)
**Worktree:** `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo03-triposr` (detached at `31a9b19`, branch base `feat/m001-talking-human-pipeline` history)
**Status:** IN PROGRESS — see "Results" section. Items marked UNVERIFIED were not executed.

## Hypothesis

A feed-forward single-image neural reconstructor (TripoSR, LRM-based) can produce a
watertight candidate mesh of Character 001 from the approved front reference
(`01_subject_front.png`) on CPU, within interactive-but-long runtime, without any
external upload of the reference image. Success = a loadable GLB candidate +
provenance/audit, **not** identity/photorealism approval (identity-auditor gates that).

## Environment (verified 2026-11-11)

- Windows 11, Python 3.14.7, pip 26.2.1, 16 GB RAM, single CPU, NO CUDA (Radeon 530 + Intel UHD)
- Blender 4.5 present (not needed for this lane's mesh stats)
- Reference image (READ-ONLY, main checkout): `C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1\01_subject_front.png`
  - 1086×1448, 2,302,219 bytes
  - SHA256 `9D84F485883CE613D12D02D9F8F85E338EBE950D7248D522BF3117901EAED2DD`
- Input was **never** uploaded to any external service. TripoSR runs 100% locally.

## License chain (hard gate: PASS)

- **TripoSR code:** MIT License, Copyright (c) 2024 Tripo AI & Stability AI
  (`tools/triposr/LICENSE`, verbatim read).
- **TripoSR pretrained weights (`stabilityai/TripoSR` on HuggingFace):** repo metadata
  tags `license:mit`, `cardData.license = "mit"`, not gated, repo sha
  `5b521936b01fbe1890f6f9baed0254ab6351c04a`, lastModified 2024-08-09. README of the
  official repo states: "The model is released under the MIT license, which includes
  the source code, pretrained models, and an interactive online demo."
  → MIT-compatible for internal evaluation; no registration/terms acceptance required.
- **torchmcubes** (github.com/tatsy/torchmcubes): MIT (built from source, commit
  `a9ac95aa329957ba646e7bb057f825f5dfa77f38`).
- Reference image: LIVYNTH-owned approved asset; used locally only.

## Clone

- `git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git tools/triposr`
- Commit: `107cefdc244c39106fa830359024f6a2f1c78871` ("Update README.md")
- Location: inside this worktree only (`tools/triposr`), not committed.

## Install log (exact commands, exit codes)

All commands run from the worktree root unless noted. "exit 1" in PowerShell below is
the shell's stderr-as-error artifact; pip's own success line is quoted.

| # | Command | Result |
|---|---------|--------|
| 1 | `python -m pip install torch --index-url https://download.pytorch.org/whl/cpu` | OK — `torch-2.15.0+cpu-cp314-cp314-win_amd64.whl (128.6 MB)`; installed 2.15.0+cpu |
| 2 | `pip install omegaconf==2.3.0 einops==0.7.0 "imageio[ffmpeg]" huggingface-hub` | OK — omegaconf 2.3.0, einops 0.7.0, imageio 2.38.1, imageio-ffmpeg 0.8.1 |
| 3 | `pip install transformers==4.35.0` | OK with warning — pulls `huggingface-hub 0.17.3`, `tokenizers 0.14.1`, `safetensors 0.8.0`; **conflict:** pre-existing `fastembed 0.8.0` wants `huggingface-hub>=0.20` and `tokenizers>=0.15` (fastembed is not used by TripoSR; left as-is, recorded) |
| 4 | `pip install rembg` | OK — rembg 2.0.87, numba 0.68.1, llvmlite 0.50.0, pymatting 1.1.16, pooch 1.9.0 (onnxruntime 1.29.0 already present) |
| 5 | `pip install "git+https://github.com/tatsy/torchmcubes.git"` | **FAIL** — build isolation lacks torch: `RuntimeError: torchmcubes must be built against an installed PyTorch... pip install --no-build-isolation .` |
| 6 | `pip install --no-build-isolation "git+https://github.com/tatsy/torchmcubes.git"` | **FAIL** — `Cannot import 'scikit_build_core.build'` |
| 7 | `pip install scikit-build-core cmake ninja` | OK — scikit-build-core 1.1.2, cmake 4.4.4, ninja 1.13.2 |
| 8 | `pip install --no-build-isolation "git+https://github.com/tatsy/torchmcubes.git"` | **FAIL** — CMake could not find pybind11 (`pybind11Config.cmake`) |
| 9 | `pip install pybind11` | OK |
| 10 | `pip install --no-build-isolation "git+https://github.com/tatsy/torchmcubes.git"` | **OK** — built `torchmcubes-0.1.0-cp314-cp314-win_amd64.whl (117426 bytes, sha256 8fec393f…f4fd74691…)`; CPU build; commit `a9ac95a` |
| 11 | `pip install xatlas==0.0.9` (pinned) | **FAIL** — bundled pybind11's `cmake_minimum_required` too old for CMake 4.4.4 (`extern/pybind11/CMakeLists.txt:8`) |
| 12 | `pip install xatlas` (0.0.11) | **OK** — built & installed `xatlas-0.0.11` (pin deviation, required for py3.14/CMake 4) |
| 13 | `pip install moderngl==5.10.0` | OK — moderngl 5.10.0, glcontext 2.5.0 |
| 14 | `pip install gradio` (from requirements.txt) | **SKIPPED** — not imported by `run.py`; heavy; not needed for candidate generation |
| 15 | `trimesh==4.0.5` / `Pillow==10.1.0` pins | **NOT APPLIED** — environment already has trimesh 5.2.0 and Pillow 12.3.0; pins predate cp314 wheels and would risk the green `geo/tests` baseline |

Import smoke test: `import rembg, xatlas, moderngl, torchmcubes, transformers, omegaconf, einops, trimesh; from tsr.system import TSR` → **OK** (only a transformers FutureWarning about `torch.utils._pytree`).

## Commands run (inference)

See `output/triposr_candidate/logs/` for full logs.

| Attempt | Command | Exit | Notes |
|---------|---------|------|-------|
| 1 | `python run.py <abs path to 01_subject_front.png> --output-dir <worktree>/output/triposr_candidate --device cpu --model-save-format glb` | see logs | default `--mc-resolution 256`, `--chunk-size 8192` |

## Weights download record

- Source: HuggingFace `stabilityai/TripoSR` (public, not gated), files `config.yaml` + `model.ckpt`
- Downloaded on first run via `hf_hub_download` into the HF cache (`%USERPROFILE%\.cache\huggingface\hub`)
- Sizes/hashes: recorded below after download completes (UNVERIFIED until then)

## Results

UNVERIFIED — fill in after run(s) complete.

## Quality notes (trimesh stats only)

UNVERIFIED — identity-auditor performs visual approval; we report geometry stats only.

## Known failure modes / deviations

- Environment is shared Python 3.14.7 site-packages: installing TripoSR deps mutates it
  (transformers pin downgraded huggingface-hub). `python tools/local_check.py` and
  `geo/tests` should be re-run to confirm the baseline is still green.
- xatlas 0.0.11 instead of pinned 0.0.9 (build failure on CMake 4).
- trimesh/Pillow pins not applied (no cp314 wheels; environment already newer).
- gradio not installed.

## UNVERIFIED / not executed

- Visual identity quality (identity-auditor gates this; not attempted here)
- `--bake-texture` path (requires moderngl headless GL context; not attempted)
- `--render` NeRF video path (not attempted)
- local_check.py / geo tests re-run after dependency changes — UNVERIFIED unless noted in Results
