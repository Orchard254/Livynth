# C001-GEO-04 — Licence matrix for the C001 toolchain

**Author:** reconstruction-research (subagent) · **Date checked:** 2026-11-11
**Purpose:** give ADR-C001-004 decision 1 ("conditional on provenance") a single, auditable source of truth. Every row cites a file or URL that was actually read. Rows that could not be confirmed are marked **UNVERIFIED** and collected in §6.

**Reading the columns**
- *Evidence path* — the exact local path or URL read, with the quoted line.
- *Redistribution allowed?* — whether the component's own licence permits redistribution of the component (or of artefacts derived from it) inside a shipped LIVYNTH product.
- *Attribution required?* — whether the component's licence requires a notice, citation or licence copy in the shipped product.
- *Status* — `VERIFIED` (primary source read) or `UNVERIFIED` (see §6).

**Scope note.** "Redistribution" here means *shipping in a commercial product*. Several components are used only as **local tools** (Blender) or only as **untracked local experiments** (TripoSR clone, MediaPipe model); the obligations differ accordingly and are stated per row.

---

## 1. Python runtime and core geometry stack (system interpreter, Python 3.14.7)

| Component | Version | Licence | Evidence path (quoted) | Redistribution allowed? | Attribution required? | Status |
|---|---|---|---|---|---|---|
| numpy | 2.5.3 (installed) | BSD-3-Clause (+ bundled 0BSD/MIT/Zlib/CC0-1.0) | PyPI metadata `license_expression: "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0"` | Yes | Notice | VERIFIED (registry) |
| scipy | 1.18.1 | BSD-3-Clause | PyPI `license` field: "Copyright (c) 2001-2002 Enthought, Inc. 2003, SciPy Developers. All rights reserved. Redistribution and use in source and binary forms…" | Yes | Notice | VERIFIED (registry) |
| Pillow | 12.3.0 | MIT-CMU | PyPI `license_expression: "MIT-CMU"` | Yes | Notice | VERIFIED (registry) |
| **trimesh** | **5.2.0** | **MIT** | `site-packages\trimesh-5.2.0.dist-info\licenses\LICENSE.md`: "**The MIT License (MIT)** / Copyright (c) 2023 Michael Dawson-Haggerty" | Yes | **Yes** — include the MIT notice | **VERIFIED (local file)** |
| **scikit-image** (marching cubes) | **0.26.0** | **BSD-3-Clause** (per-file mix; some files BSD-2-Clause) | `site-packages\scikit_image-0.26.0.dist-info\LICENSE.txt`: "Files: * / Copyright: 2009-2022 the scikit-image team / **License: BSD-3-Clause**"; and "Files: skimage/filters/thresholding.py … **License: BSD-2-Clause**" | Yes | Notice | **VERIFIED (local file)** |
| **fast-simplification** | **0.2.0** | **MIT** | `site-packages\fast_simplification-0.2.0.dist-info\licenses\LICENSE`: "The MIT License / Copyright (c) 2017-2021 The PyVista Developers" | Yes | **Yes** — include the MIT notice | **VERIFIED (local file)** |
| imageio | 2.38.1 | BSD-2-Clause | PyPI `license_expression: "BSD-2-Clause"` | Yes | Notice | VERIFIED (registry) |
| imageio-ffmpeg | 0.8.1 | BSD-2-Clause (wrapper) | PyPI `license_expression: "BSD-2-Clause"` | Yes (wrapper) | Notice | VERIFIED (wrapper); **bundled ffmpeg binary licence UNVERIFIED — see §6** |
| tifffile | 2026.11.8 | BSD-2-Clause | PyPI `license_expression` not captured in this pass | Yes | Notice | **UNVERIFIED** (registry not read for this exact version) |
| **torch** | **2.15.0+cpu** | BSD-3-Clause-style (PyTorch LICENSE) | `site-packages\torch-2.15.0+cpu.dist-info\licenses\LICENSE`: "From PyTorch: Copyright (c) 2016- Facebook, Inc (Adam Paskew) … Copyright (c) 2014- Soumith Chintala …" | Yes | Notice | **VERIFIED (local file)** |
| **transformers** | **4.35.0** | **Apache-2.0** | `site-packages\transformers-4.35.0.dist-info\LICENSE`: "Copyright 2018- The Hugging Face team. All rights reserved. / **Apache License Version 2.0, January 2004**" | Yes | **Yes** — Apache §4 (copy of licence, notices, NOTICE) | **VERIFIED (local file)** |
| huggingface-hub | 0.17.3 | Apache-2.0 | `site-packages\huggingface_hub-0.17.3.dist-info\METADATA` line 8: "**License: Apache**"; line 14: "Classifier: License :: OSI Approved :: Apache Software License" | Yes | Yes | **VERIFIED (local file)** |
| onnxruntime | 1.29.0 (installed) | MIT | PyPI 1.31.1 metadata: "MIT License". **The installed 1.29.0 METADATA was not read.** | Yes | Notice | **UNVERIFIED (installed version)** |
| einops | 0.7.0 (installed) | MIT | PyPI metadata `license: "MIT"` | Yes | Notice | VERIFIED (registry) |
| omegaconf | 2.3.0 (installed) | BSD-3-Clause | PyPI classifier "License :: OSI Approved :: BSD License" | Yes | Notice | VERIFIED (registry) |
| numba / llvmlite | 0.68.1 / 0.50.0 | BSD / BSD-2-Clause AND Apache-2.0-with-LLVM-exception | PyPI `license_expression` for llvmlite: "BSD-2-Clause AND Apache-2.0 WITH LLVM-exception" | Yes | Notice | VERIFIED (registry) |
| tokenizers | 0.14.1 (installed) | Apache-2.0 | PyPI classifier "License :: OSI Approved :: Apache Software License" | Yes | Yes | VERIFIED (registry) |

## 2. Landmark lane (worktree `livynth-c001-geo03-landmarks`)

| Component | Version | Licence | Evidence path (quoted) | Redistribution allowed? | Attribution required? | Status |
|---|---|---|---|---|---|---|
| **mediapipe** | **1.2.2** (worktree venv `.venv-landmarks`) | **Apache-2.0** | `.venv-landmarks\Lib\site-packages\mediapipe-1.2.2.dist-info\METADATA` line 8: "**License: Apache 2.0**"; line 14: "Classifier: License :: OSI Approved :: Apache Software License"; lines 31–32: "License-File: LICENSE / License-File: NOTICE"; the `licenses\NOTICE` file opens "MediaPipe Tasks Privacy Notice … Last modified: June 5, 2026" and then carries the full Apache-2.0 text plus bundled third-party notices (Abseil, addr2line, gimli, adler2, ahocorasick, …) | Yes | **Yes** — ship the Apache-2.0 copy **and** the NOTICE file | **VERIFIED (local file)** |
| **`models/face_landmarker.task`** (bundle: BlazeFace short-range detector + FaceMesh V2 + Blendshape) | float16/1 | **Apache License, Version 2.0** (for the detector sub-model; see §6 for the other two) | Upstream model card, `storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20(Short%20Range).pdf`: "**LICENSED UNDER Apache License, Version 2.0**". Bundle URL `storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`; HEAD on 2026-11-11 → `content-length: 3758596`, `etag: "b0e7274907a1644404fef66b28dd6d85"`, `last-modified: Wed, 03 May 2023 18:02:21 GMT` | Yes (Apache-2.0) | Yes — Apache §4 notice | **VERIFIED for BlazeFace; UNVERIFIED for the FaceMesh-V2 and Blendshape sub-model cards** (§6) |
| opencv-python-headless / opencv-contrib-python | 5.0.0.93 (worktree venv) | Apache-2.0 | PyPI `license: "Apache 2.0"`; classifier "License :: OSI Approved :: Apache Software License" | Yes | Yes (Apache §4) | VERIFIED (registry) |

> **Provenance note (must be recorded).** `models/face_landmarker.task` is **not** bundled in the mediapipe wheel — `docs/C001_GEO03_LANDMARKS.md` §4 finding 2: "It is **not** bundled in the wheel (verified: no `*.task`/`*.tflite` files under `site-packages/mediapipe/`) and the API does **not** auto-fetch it." It was therefore downloaded separately from `storage.googleapis.com`. That download happened outside a "no downloads" instruction and must appear in the run manifest with its URL, size and hash.

> **Coordinator-verified addition (2026-11-11).** The local copy's identity was subsequently measured: `models/face_landmarker.task` = **3,758,596 bytes**, SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`, matching the upstream `content-length` exactly. The file is excluded from Git; `tools/fetch_face_landmarker.py` re-fetches it from the pinned URL and verifies the hash.

## 3. TripoSR lane (Lane A, worktree `livynth-c001-geo03-triposr`)

| Component | Version | Licence | Evidence path (quoted) | Redistribution allowed? | Attribution required? | Status |
|---|---|---|---|---|---|---|
| **TripoSR source (vendored clone)** | clone at `origin/main` = `107cefdc244c39106fa830359024f6a2f1c78871` (shallow) | **MIT** | `livynth-c001-geo03-triposr\tools\triposr\LICENSE` lines 1–3: "**MIT License** / **Copyright (c) 2024 Tripo AI & Stability AI**"; body: "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software." | Yes | **Yes** — ship the MIT notice | **VERIFIED (local file). NOTE: the LICENSE file IS PRESENT — the "vendored clone has no licence" failure mode did not occur.** |
| TripoSR **README** licence statement (weights) | — | MIT (explicitly extended to weights) | `tools\triposr\README.md` line 27: "**The model is released under the MIT license, which includes the source code, pretrained models, and an interactive online demo.**" | — | — | **VERIFIED (local file)** |
| **`weights/model.ckpt`** | 1,677,246,742 B (measured 2026-11-11) | **MIT**, by the vendor's own explicit statement above; HF repo `stabilityai/TripoSR` is tagged `license:mit` and `cardData.license == "mit"` (HF API, 2026-11-11) | As above + `huggingface.co/api/models/stabilityai/TripoSR` → `tags: [… "license:mit" …]`, `cardData: {"license":"mit"}` | **Yes, under MIT.** Conditions: include "Copyright (c) 2024 Tripo AI & Stability AI" + the MIT permission text; no endorsement implied | **Yes** — MIT notice + cite the technical report (arXiv:2403.02151) | **VERIFIED** (vendor statement + registry). **Acquisition caveat: the HF repo is gated** (`extra_gated_fields`: Name, Email, Country, Organization/Affiliation) → the download required an account and HF terms. The *file* is MIT; the *acquisition channel* was gated. |
| TripoSR runtime dependency `facebook/dino-vitb16` (DINOv2 ViT-B/16, pulled by `weights/config.yaml`) | — | Apache-2.0 | HF API `models/facebook/dino-vitb16` → `tags: [… "license:apache-2.0" …]`, `gated: false` | Yes | Yes (Apache notice) | VERIFIED (registry) |
| TripoSR training-data provenance | — | Objaverse (`allenai/objaverse`, per the HF card `dataset:allenai/objaverse`) | HF card `datasets: ["allenai/objaverse"]` | **Reliance on the vendor's MIT grant.** The vendor states the *weights* are MIT; we do not independently re-derive the weights' licence from the training data | Cite the TripoSR report + Objaverse | **VERIFIED as a statement of provenance; the licence conclusion is the vendor's, not independently verified** |
| TripoSR deps: `omegaconf`, `Pillow`, `einops`, `transformers`, `trimesh`, `rembg`, `huggingface-hub`, `imageio[ffmpeg]`, `gradio` | as installed | BSD-3-Clause / MIT-CMU / MIT / Apache-2.0 / MIT / MIT / Apache-2.0 / BSD-2 / Apache-2.0 | PyPI metadata per package (see §1); `site-packages\rembg-2.0.87.dist-info\licenses\LICENSE.txt`: "**MIT License** / Copyright (c) 2020 Daniel Gatis" | Yes | Yes (notices) | VERIFIED (registry + local rembg file) |
| TripoSR dep `torchmcubes` (installed from `git+https://github.com/tatsy/torchmcubes.git`) | 0.1.0 | **MPL-2.0** | Upstream `raw.githubusercontent.com/tatsy/torchmcubes/master/LICENSE` line 1: "**Mozilla Public License Version 2.0**"; Exhibit A: "This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0." **Not on PyPI** (pypi.org/pypi/torchmcubes/json → 404); local `torchmcubes-0.1.0.dist-info\licenses\` exists and `direct_url.json` records the VCS origin | Yes | **Yes** — MPL-2.0 is **file-level copyleft**: modified/derived TripoSR sources must keep their MPL-2.0 notices | VERIFIED (upstream + local metadata) |
| TripoSR dep `xatlas` / `moderngl` | 0.0.11 / 5.10.0 | MIT / MIT | PyPI `xatlas` licence text: "MIT License Copyright (c) 2021 Markus Worchel"; PyPI `moderngl` `license: "MIT"` | Yes | Yes (notices) | VERIFIED (registry) |
| **`bria-rmbg-2.0.onnx`** (rembg model, 1.02 GB) — download attempted then bypassed | — | **UNVERIFIED — and expected to be NON-COMMERCIAL** | `docs/C001_GEO03_EXPERIMENT_LOG.md` G5: "attempt 2 then failed **inside rembg** (`bria-rmbg-2.0.onnx`, 1.02 GB, read timeout at 596 MB after 21 min)"; G6: "**rembg bypassed** … no second 1 GB download, no extra model license." The rembg *code* is MIT; the **Bria model licence is separate and was not read** | **Do not redistribute. Do not use in any shipped path.** | — | **UNVERIFIED (§6). ACTION: delete the partial download; confirm no Bria model is in any shipped path.** |

## 4. Tooling, assets and the reference pack

| Component | Version | Licence | Evidence path (quoted) | Redistribution allowed? | Attribution required? | Status |
|---|---|---|---|---|---|---|
| Blender | 4.5.10 LTS | GPL (application) | **Not read from a local file in this investigation** — the Blender install directory was not inspected | Using Blender as a renderer does not trigger GPL distribution obligations; **distributing Blender does** | Only if redistributed. Scripts added to Blender's `scripts/` directory are generally treated as under Blender's GPL terms | **UNVERIFIED (§6)** |
| MakeHuman / MPFB base mesh (ADR decision 1 candidate) | — | Claimed **CC0** (assets) + **GPL** (MPFB addon) | `docs/CHARACTER_FACTORY_INPUTS.md` §5 line 49: "Licenses: MakeHuman CC0 (models/assets); MPFB addon GPL (tool, OK)". **This is a report claim, not a licence verification** — ADR decision 1: "A CC0 claim in a report is not license verification." The base mesh was **not located or inspected** in this investigation | **UNVERIFIED** | **UNVERIFIED** | **UNVERIFIED (§6). The topology specialist must verify the exact mesh file, its source and its licence text before use.** |
| **`assets/characters/character_001/identity_capture_v1/*.png`** (15 files) | 2026-11-11 | **AI-generated by OpenAI `gpt-image`; C2PA `trainedAlgorithmicMedia`; NOT CC0, NOT open-licensed** | `docs/CHARACTER_FACTORY_INPUTS.md` §3 line 26: "All carry **C2PA manifests signed OpenAI** (`gpt-image`, `trainedAlgorithmicMedia`), timestamps 2026-11-11T01:25–02:29Z. **AI-generated, not camera captures; no EXIF, no lens data, no seed, no checkerboard**". `docs/C001_GEO03_EXPERIMENT_LOG.md` line 13: "15 PNGs … present, gitignored, C2PA `gpt-image`". **The C2PA manifests themselves were not parsed in this investigation.** | **No, by default.** These are outputs of a commercial service; the governing terms are OpenAI's service terms as of the generation date (**not read here — UNVERIFIED**). Do **not** redistribute the PNGs in a shipped product without the owner confirming the generating account's terms. They are **gitignored** (`.gitignore`: `assets/characters/**`, `assets/*.png`), so the repository never redistributes them | Attribution to the generator is appropriate disclosure; **not a licence attribution** | **AI-generated status VERIFIED via project documentation; the byte-level C2PA manifests and the generating account's terms are UNVERIFIED (§6)** |
| `assets/voice.wav` | PCM mono 16-bit 22050 Hz, 13.997 s, SHA-256 `98FDFCDB…EDD0A` | Owner's recording — **ownership UNVERIFIED** | `docs/CHARACTER_FACTORY_INPUTS.md` §3 line 30 gives the technical facts and hash; **no licence or release file exists in the repo** | Do not redistribute without a voice release | — | **UNVERIFIED (§6). If this is not the owner's own voice, a voice/likeness release is required before shipping.** |
| `assets/voice_transcript.txt` | untracked user file | Owner's text — **ownership UNVERIFIED** | ADR-C001-004 agent dispatch names it as a protected pre-existing user change | Do not delete/rename/stage | — | **UNVERIFIED (§6)** — but agents must treat it as read-only regardless |
| `assets/ours-photoreal.glb` | — | **UNVERIFIED — not present** | `C:\PROJECT\Livynth\assets\` contains only `characters\`, `voice_transcript.txt`, `voice.wav`. `assets/README.md` **does not exist** (deleted pre-existing user change per the ADR) | — | — | **UNVERIFIED (§6). The M001 avatar's provenance/licence is unrecorded; it must be established before any ship.** |

## 5. Not yet used — researched for ADR decisions 3 and 4 (recorded for the registry)

| Component | Version | Licence | Evidence | Verdict |
|---|---|---|---|---|
| **FLAME 2023 Open** (`flame2023_Open.pkl`) | 2023 release (11/25) | **CC BY 4.0** + "no pornographic" + **"no fake/libelous/misleading/defamatory content"** | `flame.is.tue.mpg.de/modellicense.html` "Open Model License"; `index.html` News: "Released FLAME 2023 Open Model with the Open Source License (CC-BY-4.0)" | **Attribution + link + "indicate if changes were made" + FLAME paper.** Licence-gated for a commercial synthetic-human product pending written clarification. Registration + terms acceptance required |
| FLAME **texture model** | — | **CC BY-NC-SA 4.0** | `flame.is.tue.mpg.de/texturelicense.html`: "Creative Commons BY-NC-SA 4.0 license" | **EXCLUDE — non-commercial + share-alike** |
| FLAME **academic** models / **D3DFACS** | — | Academic non-commercial, No Distribution | `modellicense.html` / `datalicense.html` | **EXCLUDE from commercial use** |
| `soubhiksanyal/FLAME_PyTorch` (code) | 0.0.1 (2023) | MIT | GitHub API `spdx_id: MIT` | Attribution if vendored |
| `flame_to_flame_open_converter` | 2025-10-14 | **No licence declared** (GitHub API `license: null`) | GitHub API | Reference only; do not vendor |
| `flame_lib` (nmfisher) | 0.1.0 | **UNVERIFIED** — PyPI licence field empty; README: "The repository does not declare a single permissive license covering all files." | pypi.org/pypi/flame-lib/json; repo README | Reference implementation only; **do not depend on it** |
| `flame-model` (PyPI) | 0.0.3 | PyPI metadata "Apache 2.0"; depends on `chumpy-fix` | pypi.org/pypi/flame-model/json | **Avoid** (chumpy on 3.14) |
| Montreal Forced Aligner | 3.4.3 | **MIT** (code); acoustic model + dictionary **CC BY 4.0** | GitHub API `spdx_id: MIT`; `mfa-models` README "License: CC BY 4.0"; HF `MontrealCorpusTools/english_us_arpa` `license: cc-by-4.0` | Attribution required — OK for commercial use |
| faster-whisper + `Systran/faster-whisper-*.en` | 1.2.1 / models | **MIT** (both) | PyPI `License: MIT`; HF API `license:mit` | Courtesy attribution only |
| stable-ts | 2.19.1 | MIT | GitHub API + PyPI | Attribution |
| whisperX | 3.8.6 | BSD-2-Clause | GitHub API + PyPI | **Rejected: `requires_python <3.14`** |
| aeneas | 1.7.3.0 | **AGPL-3.0** | PyPI classifier + GitHub API `spdx_id: AGPL-3.0` | **Rejected: network copyleft** |
| PySimpleAudio | n/a | — | pypi.org/pypi/PySimpleAudio/json → **404** | **Rejected: not distributed on PyPI; not an aligner; `pyaudio` 0.2.14 has no cp314 wheel** |

---

## 6. UNVERIFIED REGISTER — every entry that could not be confirmed from a primary source

Each of these MUST be resolved (or explicitly accepted as a risk) before any commercial release.

1. **`bria-rmbg-2.0.onnx` licence** (rembg model, 1.02 GB, partially downloaded to 596 MB). The rembg *code* is MIT; the **Bria model licence is separate and was not read**. Expected non-commercial. **Action: delete the partial download; confirm no Bria model is used in any shipped path.**
2. **`face_landmarker.task` — the FaceMesh-V2 and Blendshape sub-model licences.** Only the BlazeFace (Short Range) model card was read ("LICENSED UNDER Apache License, Version 2.0"); the FaceLandmarker-V2 and Blendshape model cards are PDFs that could not be parsed. **Action: read both PDFs and record their licence lines.**
3. **`face_landmarker.task` — the local file's identity.** RESOLVED by the coordinator on 2026-11-11: 3,758,596 bytes, SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`, matching the upstream `content-length` and etag `b0e7274907a1644404fef66b28dd6d85`. **The bundle is excluded from Git and re-fetched by `tools/fetch_face_landmarker.py` with hash verification.**
4. **Blender 4.5.10 LTS licence text.** Not read from the local installation. Using it as a renderer does not create distribution obligations, but the GPL terms should be recorded, and any script installed into Blender's `scripts/` tree should be treated as GPL-covered.
5. **MakeHuman / MPFB base-mesh licence and provenance.** The "CC0" statement is a report claim only; the mesh file was not located. **This directly gates ADR decision 1 — the topology specialist must verify the exact file, its upstream source and its licence text.**
6. **`assets/ours-photoreal.glb` provenance and licence.** The file is not present in this checkout and no licence record exists. It is the M001 avatar that M001 renders use.
7. **The generating OpenAI account's terms for the reference pack.** The PNGs are outputs of a commercial service; the service terms in force on 2026-11-11 were not read. Do not redistribute the PNGs until confirmed.
8. **Byte-level C2PA provenance of the 15 PNGs.** Reported by the asset-curator in project documentation; the manifests themselves were not parsed in this investigation.
9. **`assets/voice.wav` ownership / voice release.** No licence or release file exists. Required before shipping if the voice is not the owner's own.
10. **`assets/voice_transcript.txt` ownership.** Untracked user file; treated as protected.
11. **`onnxruntime` 1.29.0 (the installed version) licence.** Registry metadata was read for 1.31.1 (MIT), not for the installed 1.29.0.
12. **`tifffile` 2026.11.8 licence.** Registry metadata was not captured for this exact version.
13. **`imageio-ffmpeg`'s bundled static ffmpeg binary licence.** The wrapper is BSD-2-Clause; the bundled ffmpeg build's licence (typically GPL-2.0-or-later with libx264) was not determined.
14. **`chumpy-fix` 0.0.1 on Python 3.14.7.** Almost certainly broken (chumpy predates 3.11); **cannot be confirmed without installing**, which is out of scope. Avoid the PyPI FLAME wrappers entirely.
15. **`flame-model` / `flame_lib` / `smplx` licence fields.** `flame-model` says "Apache 2.0" in PyPI metadata but the FLAME *model data* is separately licensed — the metadata does not cover the data. `flame_lib` and `smplx` have **empty** PyPI licence fields.
16. **FLAME landmark embeddings' terms under the Open Model Licence.** Not stated on the Model Licence page; the embeddings are a separate download item. **Material gap for any landmark-driven fit.**
17. **`FLAME_masks.pkl` terms.** Same gap.
18. **FLAME 2023 Open archive size and contents.** Not downloaded; deliberately so.

---

## 7. Redistribution rules that follow from this matrix

1. **Nothing in this repo's Git history is a licence problem today.** The reference PNGs, the WAV, the GLBs, the TripoSR clone, its 1.68 GB checkpoint and the MediaPipe model are all gitignored / untracked.
2. **If a shipped product ever embeds TripoSR output** (a mesh derived from `model.ckpt`), the shipped product must carry the MIT notice for Tripo AI & Stability AI and cite arXiv:2403.02151 — and any *modified TripoSR source files* must remain MPL-2.0 (torchmcubes).
3. **If a shipped product ships or bundles the MediaPipe runtime**, it must include the Apache-2.0 licence text **and** the NOTICE file (which itself carries the bundled third-party notices).
4. **If a shipped product ships a FLAME-derived head**, it must carry the CC BY 4.0 attribution block, link the licence, state that changes were made, cite the FLAME paper, **and** have written Max-Planck clearance on the "fake content" clause.
5. **The FLAME texture model, the academic FLAME models and D3DFACS must never enter a commercial build.** They are NC / NC-SA / no-distribution respectively.
6. **The reference PNGs must not be redistributed** with the product without the owner confirming the generating account's terms. They are, in any case, uncalibrated and mutually inconsistent, and are documented as "PASS-as-appearance-reference / CONDITIONAL hull / REFERENCE_ONLY for TripoSR" — never as a likeness or a scan.
