# C001-GEO-04 — Attribution / notice draft

**Status: DRAFT. Requires owner sign-off before any of this text ships.**
**Author:** reconstruction-research (subagent) · **Date:** 2026-11-11
**Scope:** notices for the components LIVYNTH C001 actually uses today, plus conditional blocks for components that may be adopted. Every entry is traceable to `docs/C001_GEO04_LICENCE_MATRIX.md`.

**How to use this file**
- §1 is the aggregated **NOTICE** text for the shipped distribution and the repository.
- §2 is the per-component attribution register, with the exact wording to use for each.
- §3 is the **user-facing** disclosure for a shipped product (About / credits screen).
- §4 is the conditional FLAME 2023 Open block — **only if that model is adopted.**
- §5 is the character/asset disclosure.
- §6 is the sign-off checklist.

**House rules**
- Every licence that requires a notice gets a *verbatim* notice, not a paraphrase.
- "Indicate if changes were made" is honoured explicitly wherever CC BY applies.
- Nothing in this file asserts a licence that the matrix marks UNVERIFIED. Those entries are listed in §7 and must be resolved before this draft is finalised.

---

## 1. Aggregated NOTICE (ship in the distribution root and at `docs/THIRD_PARTY_NOTICES.md`)

```
LIVYNTH — third-party notices
==============================

This product and its source repository use the following third-party software.
The full, authoritative licence texts are distributed with each component or are
available at the URLs listed.

--------------------------------------------------------------------------------
TripoSR  (used for experimental single-image 3D reconstruction)
Copyright (c) 2024 Tripo AI & Stability AI
Licensed under the MIT License.
https://github.com/stabilityai/TripoSR
Technical report: "TripoSR: Fast Feed-Forward 3D Reconstruction with a Single
Image", arXiv:2403.02151.

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

--------------------------------------------------------------------------------
MediaPipe  (face landmark detection)
Copyright (c) The MediaPipe Authors
Licensed under the Apache License, Version 2.0.
https://github.com/google-ai-edge/mediapipe

The MediaPipe Face Landmarker model bundle (BlazeFace short-range face
detector, Face Mesh V2, Blendshape prediction) is licensed under the Apache
License, Version 2.0. See the model cards linked from
https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker

A copy of the Apache License, Version 2.0 is available at
https://www.apache.org/licenses/LICENSE-2.0
The MediaPipe NOTICE file (including bundled third-party notices) must be
reproduced in full and shipped with this product.

--------------------------------------------------------------------------------
OpenCV, ONNX Runtime, Hugging Face Hub, tokenizers, Transformers
Licensed under the Apache License, Version 2.0 (OpenCV, ONNX Runtime, Hugging
Face Hub, tokenizers) and the MIT License (ONNX Runtime).
https://github.com/opencv/opencv · https://github.com/microsoft/onnxruntime ·
https://github.com/huggingface/huggingface_hub · https://github.com/huggingface/tokenizers ·
https://github.com/huggingface/transformers

--------------------------------------------------------------------------------
NumPy, SciPy, scikit-image, fast-simplification, imageio, imageio-ffmpeg,
tifffile, numba/llvmlite, omegaconf
Licensed under the BSD 3-Clause / BSD 2-Clause licences.
https://numpy.org · https://scipy.org · https://scikit-image.org ·
https://github.com/pyvista/fast-simplification · https://github.com/imageio/imageio ·
https://gitlab.com/twosigma/tifffile · https://numba.pydata.org ·
https://github.com/omry/omegaconf

--------------------------------------------------------------------------------
trimesh, Pillow, einops, moderngl, xatlas, rembg, torchmcubes, stable-ts,
faster-whisper, Montreal Forced Aligner
Licensed under the MIT License (trimesh, Pillow, einops, moderngl, xatlas,
rembg, stable-ts, faster-whisper, Montreal Forced Aligner).
torchmcubes is licensed under the Mozilla Public License, Version 2.0 (MPL-2.0)
— file-level copyleft. https://github.com/tatsy/torchmcubes
https://github.com/mikedh/trimesh · https://github.com/python-pillow/Pillow ·
https://github.com/arogozhnikov/einops · https://github.com/moderngl/moderngl ·
https://github.com/jpcy/xatlas · https://github.com/danielgatis/rembg ·
https://github.com/jianfch/stable-ts · https://github.com/SYSTRAN/faster-whisper ·
https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner

--------------------------------------------------------------------------------
PyTorch
Copyright (c) 2016- Facebook, Inc. (Adam Paszke)
Copyright (c) 2014- Facebook, Inc. (Soumith Chintala)
Copyright (c) 2011-2014 Idiap Research Institute (Ronan Collobert)
Copyright (c) 2012-2014 Deepmind Technologies (Koray Kavukcuoglu)
Copyright (c) 2011-2012 NEC Laboratories America (Koray Kavukcuoglu)
Copyright (c) 2011-2013 NYU (Clement Farabet)
Copyright (c) 2006-2010 NEC Laboratories America (Ronan Collobert, Loran Hughes)
Licensed under the BSD-style licence included with the distribution.
https://github.com/pytorch/pytorch

--------------------------------------------------------------------------------
Blender
Used as an external rendering tool; not redistributed as part of this product.
Copyright (c) Blender Foundation and contributors. Licensed under the GNU General
Public License. https://www.blender.org/about/license/
```

---

## 2. Per-component attribution register

| # | Component | Exact text to use | Where it must appear |
|---|---|---|---|
| 1 | **TripoSR** (source + `model.ckpt`) | "TripoSR — Copyright (c) 2024 Tripo AI & Stability AI. MIT License. https://github.com/stabilityai/TripoSR. Technical report: arXiv:2403.02151." | NOTICE + About screen + the character sheet of any character whose mesh derives from TripoSR output |
| 2 | **torchmcubes** (if TripoSR source is redistributed) | "torchmcubes — Mozilla Public License, v. 2.0. https://github.com/tatsy/torchmcubes" — retain the MPL-2.0 header in every redistributed/modified source file | Source headers + NOTICE |
| 3 | **MediaPipe runtime** | "MediaPipe — Copyright (c) The MediaPipe Authors. Apache License 2.0. https://github.com/google-ai-edge/mediapipe" + the full MediaPipe `NOTICE` file (which includes the MediaPipe Tasks Privacy Notice and all bundled third-party notices) | NOTICE (verbatim) + licence copy |
| 4 | **MediaPipe Face Landmarker model bundle** | "Face Landmarker model bundle (BlazeFace short-range detector, Face Mesh V2, Blendshape prediction) — Apache License 2.0. Model cards: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker" | NOTICE + About screen |
| 5 | **OpenCV / ONNX Runtime / HF Hub / tokenizers** | "Licensed under the Apache License, Version 2.0 — https://www.apache.org/licenses/LICENSE-2.0" (ONNX Runtime is MIT — give its own line) | NOTICE |
| 6 | **Transformers** | "Transformers — Copyright 2018- The Hugging Face team. Apache License 2.0." | NOTICE |
| 7 | **PyTorch** | The copyright block + "Licensed under the BSD-style licence included with the distribution." | NOTICE |
| 8 | **scikit-image** | "scikit-image — Copyright 2009-2022 the scikit-image team. BSD 3-Clause (some files BSD 2-Clause). https://scikit-image.org" | NOTICE |
| 9 | **trimesh** | "trimesh — Copyright (c) 2023 Michael Dawson-Haggerty. MIT License. https://github.com/mikedh/trimesh" | NOTICE |
| 10 | **fast-simplification** | "fast-simplification — Copyright (c) 2017-2021 The PyVista Developers. MIT License. https://github.com/pyvista/fast-simplification" | NOTICE |
| 11 | **NumPy / SciPy / Pillow / imageio / numba / omegaconf** | "Licensed under the BSD 3-Clause / BSD 2-Clause / MIT-CMU licences as applicable — see the project sites listed in §1." | NOTICE (aggregated OK) |
| 12 | **Montreal Forced Aligner** *(if adopted)* | "Montreal Forced Aligner — MIT License. https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner. Acoustic model and pronunciation dictionary: English (US) ARPA, © Montreal Forced Aligner, licensed under CC BY 4.0. Citation: McAuliffe, M. and Sonderegger, M. English (US) ARPA acoustic model v3.3.0. https://huggingface.co/MontrealCorpusTools/english_us_arpa" | NOTICE + About screen |
| 13 | **faster-whisper / Whisper models** *(if adopted)* | "faster-whisper — MIT License. https://github.com/SYSTRAN/faster-whisper. Whisper models: OpenAI Whisper and Systran faster-whisper conversions, MIT License." | NOTICE (courtesy; MIT requires the notice if redistributed) |
| 14 | **Blender** *(tool only)* | "Rendered with Blender (https://www.blender.org), Copyright (c) Blender Foundation and contributors, licensed under the GNU General Public License. Blender is used as an external rendering tool and is not redistributed with this product." | About screen only |

---

## 3. User-facing credits screen (shipped product)

```
CREDITS

LIVYNTH is built with the following open-source software.

Geometry & reconstruction
  TripoSR — Tripo AI & Stability AI — MIT License
  scikit-image — the scikit-image team — BSD 3-Clause
  trimesh — Michael Dawson-Haggerty — MIT License
  fast-simplification — The PyVista Developers — MIT License
  PyTorch — the PyTorch team — BSD-style licence
  Transformers — The Hugging Face team — Apache 2.0
  MediaPipe & the Face Landmarker model bundle — The MediaPipe Authors & Google — Apache 2.0
  OpenCV — the OpenCV team — Apache 2.0
  ONNX Runtime — Microsoft — MIT License
  NumPy, SciPy, Pillow, imageio — BSD / MIT licences

Rendering
  Blender — Blender Foundation and contributors — GNU GPL
  (Blender is used as an external rendering tool and is not redistributed here.)

Speech alignment  [include only the block actually used]
  Montreal Forced Aligner — MIT License; English (US) ARPA acoustic model and
    dictionary — CC BY 4.0
  faster-whisper — MIT License; Whisper models — MIT License

Full licence texts: see the THIRD-PARTY-NOTICES file shipped with this product
and the notices/ directory in the source repository.
```

---

## 4. Conditional block — FLAME 2023 Open (use ONLY if adopted)

Trigger: only after (i) Max-Planck's written confirmation on the "fake content"
clause, and (ii) confirmation that the landmark embeddings and `FLAME_masks.pkl`
are covered by the same Open Model Licence.

```
This work uses the FLAME 2023 Open model.

FLAME 2023 Open — Max-Planck-Gesellschaft zur Förderung der Wissenschaften e.V.
Licensed under the Creative Commons Attribution 4.0 International License
(CC BY 4.0). https://creativecommons.org/licenses/by/4.0/

Changes made: [describe — e.g. "the FLAME template mesh was subdivided,
retopologised to a quad base, displaced to match the Character 001 reference
views, and fitted with expression and pose parameters."] / [no changes]

Citation:
  Li, T., Bolkart, T., Black, M. J., Li, H., Romero, J. (2017).
  Learning a model of facial shape and expression from 4D scans.
  ACM Transactions on Graphics 36(6), 194:1-194:17.
  https://doi.org/10.1145/3130800.3130813

Model licence (Open Model Licence):
https://flame.is.tue.mpg.de/modellicense.html
```

**Mandatory "changes made" statement.** The CC BY 4.0 attribution must include
a link to the licence **and** indicate if changes were made. Because LIVYNTH
will retopologise and displace the template, the changes statement is **not**
optional and must be specific.

---

## 5. Character and asset disclosure

```
Character 001 (and all LIVYNTH characters) are synthetic. They are not
photographs of, and do not depict, any real person.

The reference image set used to design Character 001 was generated by an
AI image model (OpenAI gpt-image) and carries C2PA "trained algorithmic media"
provenance. It is not a camera capture, it is not calibrated, it has no lens,
EXIF or scale metadata, and it is not a scan or a photograph of a real subject.
The reference set is not redistributed with this product.

The character meshes, textures and animation in this product were produced by
LIVYNTH using the third-party software listed above.
```

**Reviewer note that must accompany any likeness evaluation** (not shipped to
end users — it is the internal gate statement):

> The reference images for Character 001 are AI-generated renders, not
> photographs. They carry no camera calibration, no scale, and no EXIF. They
> are mutually inconsistent across views (nose, chin, hair, ear scale, freckle
> and iris anchors differ between the front, ±45° and ±90° images) and they
> **fail structure-from-motion registration**. Any likeness metric computed
> against them is a measurement of the *drawing*, not of a person. The pack is
> rated `PASS-as-appearance-reference` / `CONDITIONAL hull` / `REFERENCE_ONLY
> for TripoSR` and must never be described as "calibrated", "scanned", or
> "photographic".

---

## 6. Sign-off checklist (owner)

- [ ] Every §2 row whose component is actually shipped or bundled has its text present in `NOTICE`.
- [ ] Apache-2.0 components ship the **full** Apache-2.0 text; MIT components ship the **full** MIT text.
- [ ] The MediaPipe `NOTICE` file is shipped verbatim and unedited.
- [ ] The TripoSR MIT notice is present **if and only if** TripoSR-derived output ships.
- [ ] The MPL-2.0 header is retained in every redistributed/modified `torchmcubes`-derived file.
- [ ] The FLAME 2023 Open block (§4) is present **if and only if** FLAME is adopted, with the "changes made" statement filled in and Max-Planck's written clearance attached.
- [ ] The character disclosure (§5) ships in the product.
- [ ] The reviewer note (§5) is attached to every identity/likeness gate bundle.
- [ ] All UNVERIFIED entries in `docs/C001_GEO04_LICENCE_MATRIX.md` §6 are either resolved or explicitly accepted in writing by the owner.
- [ ] `assets/ours-photoreal.glb` provenance and licence are recorded (currently missing).
- [ ] `assets/voice.wav` ownership / release is recorded (currently missing).
- [ ] The reference PNGs are confirmed excluded from any shipped artefact.

---

## 7. Items this draft deliberately does NOT assert

Because the licence matrix marks them UNVERIFIED, this draft does not state a
licence for: the Bria RMBG 2.0 model; the MediaPipe FaceMesh-V2 / Blendshape
sub-model cards; Blender's installed licence text; the MakeHuman / MPFB base
mesh; `assets/ours-photoreal.glb`; the reference PNGs' generating-account
terms; `assets/voice.wav` and `assets/voice_transcript.txt` ownership;
`onnxruntime` 1.29.0; `tifffile` 2026.11.8; `imageio-ffmpeg`'s bundled ffmpeg
build; `chumpy-fix` on Python 3.14.7; the FLAME landmark embeddings and
`FLAME_masks.pkl`; and the FLAME 2023 Open archive's size and contents.

*(The local `face_landmarker.task` size/hash was subsequently verified by the
coordinator — see `docs/C001_GEO04_LICENCE_MATRIX.md` §6 item 3 — so it is no
longer listed above.)*
