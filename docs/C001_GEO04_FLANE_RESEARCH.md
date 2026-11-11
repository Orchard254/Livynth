# C001-GEO-04 — Lane research: FLAME 2023 Open, CPU phoneme aligner, licence hygiene

**Author:** reconstruction-research (subagent) · **Date:** 2026-11-11
**Authority:** ADR-C001-004 decisions 3 (FLAME), 4 (aligner), 1 (topology provenance)
**Worktree:** `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-research`
**Branch:** `experiment/c001-geo04-research` (based on `b0235c1`)

## 0. Method, scope and honesty statement

- **Read-only investigation.** Nothing was installed, registered for, purchased, accepted, downloaded or uploaded. No model file was fetched. No account was created. No terms were accepted.
- All licence statements below are quoted from the primary source named in each entry, with the URL and the date checked (2026-11-11), or from a licence file physically present on this machine.
- Anything that could not be confirmed from a primary source is marked **UNVERIFIED** and listed in `docs/C001_GEO04_LICENCE_MATRIX.md` §6.
- **No executable result is claimed in this document.** Every runtime statement below is an *engineering estimate* unless it is quoted from a primary source or measured elsewhere in the repo. Estimates are labelled as estimates.
- **Correction to the task brief:** the brief asks about "fitting **502** FLAME vertices". FLAME 2023 is **5,023 vertices / 9,976 triangles**, not 502. Sources: EMOCA (CVPR 2022) "FLAME … a mesh with n_v = 5023 vertices"; TEMPEH (ICCV 2023) "n_v = 5023 vertices and n_f = 9976 faces"; Medusa API docs `get_template_flame` → `v.shape (5023, 3)`, `f.shape (9976, 3)`. The correction matters because it changes the CPU budget by ~10×, in FLAME's favour.

**Machine used for the assessment:** Windows 11, Python 3.14.7, 16 GB RAM, no CUDA, ~9 GB free disk, Blender 4.5.10 LTS.

---

# Q1 — FLAME 2023 Open as an OPTIONAL geometry prior (ADR decision 3)

## Q1.1 Current official terms, quoted

### Q1.1.1 The Model License page — it carries TWO licences

Source: <https://flame.is.tue.mpg.de/modellicense.html>, checked **2026-11-11**. The page body contains both an "Academic Model License" section and an "Open Model License" section.

**(a) Academic Model License** — applies to everything except the Open model:

> "Academic Model License
> The following license applies to these models only: FLAME 2017, FLAME 2019, FLAME 2020, FLAME 2023, FLAME Blender Add-on (FLAME 2020)
> **Software Copyright License for non-commercial scientific research purposes**"

> "To use the Data & Software for the sole purpose of performing non-commercial scientific research, non-commercial education, or non-commercial artistic projects;
> Any other use, in particular any use for commercial, pornographic, military, or surveillance, purposes is prohibited. This includes, without limitation, incorporation in a commercial product, use in a commercial service, or production of other artifacts for commercial purposes."

> "**No Distribution**
> The Data & Software and the license herein granted shall not be copied, shared, distributed, re-sold, offered for re-sale, transferred or sub-licensed in whole or in part except that you may make one copy for archive purposes only."

> "Commercial licensing opportunities
> For commercial uses of the Data & Software, please send email to ps-license@tue.mpg.de"

**(b) Open Model License** — the only part relevant to ADR decision 3:

> "Open Model License
> The following license applies **ONLY** to the FLAME 2023 Open model**; all other models are covered by the non-commercial license above.
> **Creative Commons Attribution license**"

On the rendered page the words "Creative Commons Attribution license" hyperlink to `https://creativecommons.org/licenses/by/4.0/`, and the FLAME home page News block states:

> "11/25: Released **FLAME 2023 Open Model with the Open Source License (CC-BY-4.0)**; previous versions are only available for non-commercial research purposes."

→ **Identifier: CC BY 4.0.** Confirmed from two independent primary pages.

**(c) The Open Model License grant — quoted:**

> "The FLAME model is under a Creative Commons Attribution license. Hence, Max-Planck grants you the right to **share and adapt the model for any purpose, including commercial use** under following terms:
> - You must give appropriate credit, provide a link to the license, and indicate if changes were made;
> - You may not apply legal terms of technological measures that legally restrict others from doing anything the license permits."

**(d) TWO RESTRICTIONS IN THE OPEN LICENCE THAT ARE NOT IN STOCK CC BY 4.0 — read this carefully:**

> "The model may not be used for pornographic purposes or to generate pornographic material whether commercial or not. **The Model may further not be used to create fake, libelous, misleading, or defamatory content of any kind excluding analyses in peer-reviewed scientific research.**"

This is a **use restriction bolted onto a CC BY grant**, and it is the single most consequential legal finding in this investigation.

- The ADR calls FLAME 2023 Open "CC BY 4.0" and treats it as freely usable with attribution. **That characterisation is incomplete.**
- LIVYNTH's stated product purpose is "Give Imagination Life — original digital humans, multi-angle likeness, facial animation and scripted portrait video". A synthetic, non-photographic person is, on the plainest reading, "fake … content". The same clause appears on the Texture and Data licences.
- The carve-out is "analyses in peer-reviewed scientific research" — which does **not** describe a commercial digital-human product.
- **This is a textual reading of the licence, not legal advice.** The correct resolution is a **written clarification from Max-Planck** (the model licence itself gives the commercial channel: `ps-license@tue.mpg.de`). Until that clarification is in hand, **FLAME 2023 Open must be treated as licence-gated for commercial use** — i.e. it fails the same "conditional on provenance" test as everything else, and it fails it harder than the ADR assumed.

**(e) Attribution obligation that would ship (from the Open licence itself):**

> "Publication with FLAME
> You agree to cite the **FLAME paper** when reporting results with the Model."

BibTeX given by Max-Planck:

```bibtex
@article{FLAME:SiggraphAsia2017,
  title = {Learning a model of facial shape and expression from {4D} scans},
  author = {Li, Tianye and Bolkart, Timo and Black, Michael J. and Li, Hao and Romero, Javier},
  journal = {ACM Transactions on Graphics, (Proc. SIGGRAPH Asia)},
  volume = {36}, number = {6}, year = {2017}, pages = {194:1--17},
  url = {https://doi.org/10.1145/3130800.3130813}
}
```

### Q1.1.2 The Texture License page — separate, non-commercial

Source: <https://flame.is.tue.mpg.de/texturelicense.html>, checked **2026-11-11**.

> "**Creative Commons BY-NC-SA 4.0 license**"

> "The Texture is under a Creative Commons BY-NC-SA 4.0 license. Hence, Max-Planck grants you the right to redistribute, and adapt it for **non-commercial** purposes, as long as you (a) give appropriate credit by citing the relevant papers, (b) indicate any changes that you've made, and (c) distribute any derivative works under the same license."

> "If you use the Texture, you agree to cite the **FFHQ dataset** which was used to build the texture space, and the GitHub repository that describes how the texture space was obtained."

→ **The FLAME texture model (AlbedoMM/FFHQ-derived texture space) is NC-SA and therefore OUT of any commercial LIVYNTH path.** It also carries the same "fake content" clause.

### Q1.1.3 The Data License page — restricted dataset

Source: <https://flame.is.tue.mpg.de/datalicense.html>, checked **2026-11-11**.

> "For non-commercial and scientific research purposes"

> "To use the data for the sole purpose of performing non-commercial scientific research. Any other use, in particular any use for commercial purposes, is prohibited."

> "**No Distribution** … except that you may make one copy for archive purposes only."

> "The Data may further not be used to create fake, libelous, misleading, or defamatory content of any kind excluding analyses in peer-reviewed scientific research."

Applies to the **registered D3DFACS registrations**; requires citing the FLAME paper and Cosker et al. 2011. → **OUT of any commercial path.**

## Q1.2 What is actually "FLAME 2023 Open", and what each artefact would cost us

| Artefact | Distribution channel | Licence | Obligation if used commercially |
|---|---|---|---|
| `flame2023_Open.pkl` — FLAME 2023 Open geometry: template mesh (5,023 v / 9,976 f), shape PCA (300), expression PCA (100), pose correctives, skinning weights | `FLAME2023Open.zip` from `download.is.tue.mpg.de` (registration-gated) | **CC BY 4.0 + no-pornographic + no-"fake content"** | Attribution + link + "changes made" + FLAME paper citation; **plus a use restriction that likely bites** |
| FLAME **texture model** / texture space | separate download | **CC BY-NC-SA 4.0** | **Non-commercial. Share-alike. EXCLUDE.** |
| FLAME **academic** models: `flame2023.pkl`, 2017/2019/2020, Blender Add-on (FLAME 2020) | registration-gated download | Academic non-commercial + No Distribution | **EXCLUDE from commercial product.** Commercial route = `ps-license@tue.mpg.de` |
| **D3DFACS** registrations | registration-gated download | Academic non-commercial + No Distribution + no-fake-content | **EXCLUDE** |
| `FLAME_masks.pkl` (vertex-region masks) | registration-gated download | **UNVERIFIED** — the masks are a separate release ("02/21: FLAME vertex masks available for download"); the Open Model Licence text does not name them | Do not use until Max-Planck confirms the Open terms cover the masks |
| FLAME **landmark embeddings** (static / dynamic / 3D68 / mediapipe-105) | registration-gated download (historically the "RingNet Project" embeddings) | **UNVERIFIED** — the Open Model Licence text names only "the FLAME 2023 Open model" | **Material gap.** Without embeddings you cannot compute FLAME's own landmark subset, which is exactly what a landmark-driven fit needs. This must be resolved before any FLAME work starts. |
| FLAME **code** (`soubhiksanyal/FLAME_PyTorch`, MIT) | GitHub | MIT (GitHub API `spdx_id: MIT`) | Attribution — copy the MIT notice |
| `flame_to_flame_open_converter` | GitHub | **No licence declared** (GitHub API `license: null`) | Reference only; do not vendor |

**Obligation summary if we shipped a FLAME-2023-Open-derived head today:**
attribution + licence link + "indicate if changes were made" + FLAME paper citation + a **written answer from Max-Planck about the "fake content" clause** + a **written answer about the landmark embeddings' terms**. Nothing else in the FLAME family is usable commercially.

## Q1.3 Obtaining FLAME 2023 Open requires an OWNER action — verified, not assumed

**Verified 2026-11-11 by fetching the pages anonymously:**

1. `https://flame.is.tue.mpg.de/download.php` renders a login form. Stripped page text:
   > "**Sign in** … Login Password **Not Registered? Register**"
   The site chrome on every page also carries "**Register / Sign In**".

2. `https://flame.is.tue.mpg.de/index.html` states:
   > "**Please sign up and agree to the license for access to the model or registered D3DFACS data.**"

3. The direct archive URL `https://download.is.tue.mpg.de/download.php?domain=flame&sfile=FLAME2023Open.zip` returned **HTTP 200 with `content-type: text/html; charset=UTF-8`** and a `set-cookie: PHPSESSID=…`, i.e. the **login page, not a ZIP**. No bytes of the model were transferred. The archive is behind the login.

4. The upstream FLAME_PyTorch README (MIT-licensed code) says the same:
   > "Download FLAME model from here. **You need to sign up and agree to the model license for access to the model.**"

**So: yes — registration + explicit licence acceptance is required. That is an owner action. No agent may perform it (ADR decision 3).**

**What the download entails — and what is UNVERIFIED:**
- File: `FLAME2023Open.zip`, containing `flame2023_Open.pkl` (a Python pickle of the model: `v_template`, `shapedirs`, `posedirs`, `weights`, `J_regressor`, `kintree_table`, `f`) and possibly the landmark embeddings and `FLAME_masks.pkl`.
- **Size: UNVERIFIED** — the archive was not downloaded, so no measured size exists. Do not state a number.
- **Format:** a `.pkl`, **not** a mesh file, **not** a glTF/GLB, and **not** a texture. It is a **parametric PCA model**, not a mesh asset. It has **no runtime dependency of its own** — it is read by `pickle.load(path, encoding="latin1")` and evaluated with NumPy/SciPy/Torch.
- **No UV map, no texture, no hair, no rig, no blendshapes.** FLAME gives a triangle mesh with shape/expression/pose parameters; it is *not* an ARKit-rigged asset.

## Q1.4 Feasibility on THIS machine (no CUDA)

### Q1.4.1 Python 3.14.7 package risk — the real blocker is `chumpy`, not FLAME

| Package | Licence | `requires_python` | 3.14 status |
|---|---|---|---|
| `flame-model` 0.0.3 (PyPI) | PyPI metadata "Apache 2.0" | `>=3.8.0` | ⚠ **risky** — `requires_dist: numpy, smplx, elias, scipy, **chumpy-fix**` |
| `chumpy-fix` 0.0.1 | PyPI metadata "Apache 2.0" | `>=3.8.0` | ⚠ **UNVERIFIED, high risk.** `chumpy` 0.70 is a 2018-era package that does not import on Python ≥3.11; `chumpy-fix` is an unmaintained fork. On 3.14.7 this is very likely broken. **Cannot be verified without installing — which is out of scope here.** |
| `smplx` 0.1.28 | PyPI `license` field **empty** → **UNVERIFIED** | `>=3.6.0` | ✓ `py3-none-any`, deps numpy + torch only |
| `flame_lib` (nmfisher) 0.1.0 | PyPI licence field **empty**; its README says "The repository does not declare a single permissive license covering all files." → **UNVERIFIED** | not declared | ✓ NumPy/SciPy core, no torch required |

**Recommendation: do NOT take a PyPI FLAME wrapper as a dependency.** Instead implement the ~150-line forward pass **in-repo with NumPy** (numpy and scipy are already in `requirements-geometry.txt`), reading the pickle directly. That gives **zero new dependencies**, zero licence ambiguity, and full control. `flame_lib` is a good *reference implementation* to read (it explicitly documents "FLAME 2023 (Open) is released under CC BY 4.0 (attribution required)") but must not be vendored without a licence answer.

### Q1.4.2 CPU cost — FLAME itself is essentially free; the *fitting* is the cost

The model tensors are small: `shapedirs` ≈ 5,023 × 3 × 400 floats ≈ 6.03 M float32 ≈ **24.1 MB**; `posedirs` ≈ 5,023 × 3 × 207 ≈ 3.12 M ≈ **12.5 MB**.

- **Forward evaluation** (shape + expression + pose → 5,023 vertices): one `(1×400) @ (400×15069)` matmul ≈ 6.0 M MAC, plus linear-blend skinning over 5 joints (neck, jaw, 2 eyeballs, global). **Estimate: ~1–3 ms per instance on this CPU.** The model is a linear blend — it is *not* a neural network and does not benefit from a GPU.
- **Landmark extraction**: barycentric interpolation on 5023/9976 topology — sub-millisecond.
- **The fitting** is where the time goes, and the cost is the loss/rasteriser, not FLAME. A DECA-style coarse fit (landmark reprojection + silhouette term, ~300–500 Adam iterations, 5 views, 256×256) with a **pure-PyTorch CPU z-buffer or point-splat rasteriser**: **estimate 30–120 ms/iteration → ~15–60 s per view → ~1.5–5 min for 5 views**. Adding a photometric term roughly triples it.
- **The standard differentiable renderers are the problem, not FLAME:** `nvdiffrast` **requires CUDA** (unavailable here). PyTorch3D runs on CPU but is slow and needs a build. Plan on a small in-repo CPU rasteriser, or a non-differentiable silhouette term optimised with `scipy.optimize`/CMA-ES.
- **Verdict: CPU-only FLAME fitting for Character 001 is realistic.** Estimated cost is minutes, not hours, and memory is trivial (tens of MB).

### Q1.4.3 Corrected scale

The brief's "502 FLAME vertices" understates the model by 10×, but 5,023 vertices / 9,976 triangles is still a very small mesh. The CPU conclusion is unchanged (and slightly better than the brief implied).

## Q1.5 Would a FLAME prior fix the measured failure? — **No. Be blunt about this.**

The measured blocker (ADR) is **"3D facial structure with correct identity"**. FLAME addresses the first half and cannot address the second:

1. **FLAME is a generic model family.** It is a PCA basis learned from head scans ("FLAME uses a linear shape space trained from 3800 scans of human heads"; "In total the model is trained from over 33,000 scans" — FLAME home page). Driving 300 shape coefficients does not recover *this* person unless the driving signal is a real, calibrated, identity-consistent capture. Our driving signal is the reference pack, and the pack itself is the thing that is broken: it is AI-generated, mutually inconsistent (nose/chin/hair/ear/freckle/iris contradictions across views), splits into two white-balance clusters, and **FAILS SfM** (`docs/CHARACTER_FACTORY_INPUTS.md` §3; `docs/C001_GEO03_EXPERIMENT_LOG.md` F2).
2. **We have already measured this failure mode in this project.** TripoSR Lane B produced "real 3D facial structure (modelled nose with tip and nostrils, eyelids with crease and eyeball form, lips with volume and vermilion border, ear helix, jaw and neck)" but was judged "**a different, generic individual: broader skull, heavier mandible, different nose/lip/eye geometry, no freckles**". A FLAME fit driven by the same broken references will produce the *same* outcome: structurally excellent face, wrong person.
3. **FLAME's texture space is NC-SA**, so FLAME cannot supply the appearance either — it would only supply shape, and appearance would still have to come from the projected AI photographs, which is exactly the "photo projected onto a shell" that the ADR forbids as likeness evidence.
4. **Topology mismatch with ADR decision 1.** FLAME is a **triangle** mesh; ADR decision 1 wants a verified **CC0 quad** base for retopology. Adopting FLAME creates a second topology track and a second licence track.
5. **Scope mismatch.** FLAME models a *face*: no hair (Character 001's identity is defined by auburn curly hair), no full cranium, stub neck. The reference pack includes back-of-head and top views — FLAME cannot constrain those, so a FLAME-based head would still need our hull for the cranium, i.e. we would be **merging** two pipelines, not replacing one.
6. **The "fake content" clause** (§Q1.1.1(d)) may prohibit the commercial use case outright.

**Plain statement: FLAME alone would not fix identity, and would not be permitted for a commercial synthetic-human product without a written answer from Max-Planck.**

What FLAME *would* legitimately buy us: a **plausible, watertight, well-conditioned 3D face prior** (nose with tip and nostrils, eyelid/eye-socket form, lips with volume, ear helix, jaw) on which our *own* retopology, rig and texturing could be built — i.e. it is a **structural prior for the retopology track**, not a likeness solver.

## Q1.6 Recommendation

**(a) Pursue?** — **NOT for C001-GEO-04. CONDITIONAL-NO, defer.**

Rationale: the measured blocker is identity; FLAME cannot supply identity; it introduces a live licence question ("fake content") that the ADR's "CC BY 4.0" summary does not capture; it requires a registration+terms action only the owner may perform; it adds a topology and licence track in parallel with ADR decision 1.

**Recommended disposition: keep FLAME 2023 Open as a *documented, licence-cleared candidate backend* in the Character Factory registry (`docs/CHARACTER_FACTORY_SPEC.md` §5 `backends.yaml`), with `license: CC-BY-4.0` + `license_gate: user_approval_required` + `notes: "Open Model Licence additionally forbids use to create fake/libelous/misleading/defamatory content — commercial synthetic-human use requires written clarification from ps-license@tue.mpg.de"`. Do not spend the GEO-04 window on it.**

Revisit FLAME only if **all** of: (i) the owner has written confirmation from Max-Planck that the Open Model Licence permits a commercial synthetic digital-human product; (ii) the landmark embeddings' terms are confirmed open; (iii) the identity problem has been solved independently — at which point FLAME becomes a plausible *structural prior* for the retopology track.

**(b) Exact owner actions required (in order).** No agent may do any of these.

1. Register at `https://flame.is.tue.mpg.de/` (the "Register" link on every page; note the site's own notice "Website moved to new content management system. Please register again if you have previously registered on the old website"). **This creates an account tied to a person — it must be the owner, not an agent.**
2. Log in and **explicitly agree to the model licence** on the download page ("Please sign up and agree to the license for access to the model…").
3. Download `FLAME2023Open.zip` from `https://flame.is.tue.mpg.de/download.php`.
4. Record: SHA-256 of the ZIP, the exact file list, and **which of {landmark embeddings, FLAME_masks.pkl} are inside** — because their terms are UNVERIFIED (§Q1.2).
5. **Email `ps-license@tue.mpg.de`** and get a **written** answer to: *"Does the FLAME 2023 Open Model Licence permit use of the model to create synthetic (non-photographic) digital human characters for a commercial product, given the clause 'may further not be used to create fake, libelous, misleading, or defamatory content of any kind'? Do the landmark embeddings and FLAME_masks.pkl carry the same Open Model Licence terms? What credit text do you require in a shipped product?"*
6. Only after 1–5: authorise a bounded experiment (register the backend in `backends.yaml`, implement the NumPy forward pass, fit to the landmarks, and render clay-only geometry for the blind gate).

**(c) Attribution text that would have to ship** — drafted in `docs/C001_GEO04_ATTRIBUTION_DRAFT.md` §4 (FLAME 2023 Open block). It covers: attribution + licence link + "indicate if changes were made" + the FLAME paper citation, and it is written so it is valid whether the model is used directly or embedded in a retopologised derivative.

**(d) What to do INSTEAD if the owner declines (recommended path).**

1. **Structural prior without any new licence:** build the head on a **verified CC0 quad base mesh** (MakeHuman/MPFB base, ADR decision 1) and displace it with **our own measured silhouettes** (the visual-hull lane's carve, already built and rendered) — no registration, no terms, no non-commercial clause, no "fake content" clause. This is the ADR-sanctioned track and is licence-clean.
2. **Treat identity as the actual, separate problem.** The current reference pack is "PASS-as-appearance-reference / CONDITIONAL hull / REFERENCE_ONLY for TripoSR" and FAILS SfM. A parametric prior cannot fix a broken reference pack. Options for the owner, in order of expected payoff:
   - **(i) Acquire a genuine calibrated capture** of a real consenting person (checkerboard or calibrated intrinsics + measured scale), with a written likeness/voice release — this fixes both identity *and* the licence hygiene of the reference pack;
   - **(ii) If the character must stay synthetic**, tighten the generation protocol (single identity anchor, strict per-view verification gate on landmarks/freckle maps, consistent lens/lighting), and accept that "identity" is then a *consistency* property of the render set, not a likeness of a person;
   - **(iii) If neither is possible**, accept that C001 is a *design* rather than a *likeness*, and stop describing it as one — the AGENTS.md gates already forbid that.
3. **Do not spend the geometry gate on a prior that cannot supply identity.** That is the core finding.

## Q1.7 FLAME feasibility summary table

| Question | Answer | Confidence |
|---|---|---|
| Is FLAME 2023 Open CC BY 4.0? | Yes — and **plus** a "no pornographic" and **"no fake/libelous/misleading/defamatory content"** use restriction | **Verified** (primary source) |
| Does it permit commercial use? | The licence *grants* commercial use, but the same licence *restricts* fake content → commercial synthetic-human use is **licence-gated pending written clarification** | Verified text / unresolved legal meaning |
| Does obtaining it need an account + terms acceptance? | **Yes** — "Please sign up and agree to the license for access to the model"; download URL returns the login page | **Verified** (fetched) |
| File size | **UNVERIFIED** (not downloaded) | — |
| Format | Python pickle `.pkl`; parametric PCA model; **not** a mesh/texture/UV asset; no runtime dependency of its own | Verified from upstream docs |
| Python 3.14.7 compatibility | **Do not use the PyPI wrappers** (`chumpy-fix` is very likely broken on 3.14). Implement the forward pass in-repo with NumPy/SciPy → **0 new dependencies, no 3.14 risk** | Verified for the wrapper risk; in-repo path is our own code |
| CPU-only fitting feasible? | **Yes.** Forward ≈1–3 ms; 5-view fit with a CPU rasteriser ≈ **1.5–5 min** (estimate); memory tens of MB | Estimate (not executed) |
| Would it fix identity? | **No.** Generic model family; the driving references are the broken part. Same failure mode TripoSR already demonstrated. | High confidence, by analogy + evidence |
| Overall | **Defer.** Licence-gated, registration-gated, and does not address the measured blocker | — |

---

# Q2 — CPU-capable phoneme aligner (ADR decision 4)

## Q2.1 What the CURRENT heuristic does (and must keep passing)

Source: `C:\PROJECT\Livynth\video\make_timeline.py`. Read in full.

**Pipeline**

1. `read_wav_energy(path, fps)` — opens the WAV with the stdlib `wave` module. **Raises `ValueError('Expected uncompressed PCM WAV')`** unless `compression == 'NONE'` and sample width ∈ {1,2,3,4}; raises on an empty/malformed file. Mixes channels by averaging, then computes **per-frame RMS** at `fps`.
2. `approximate_words(text, duration, energy, fps)` — tokenises with `re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", text)`. Defines "active" frames as `energy > max(0.008, ceiling*0.12)` where `ceiling = max(energy)`. The **speech-active span** is then divided among the words **in proportion to word length**, with `weight = max(2, len(word))`. This is the entire timing model.
3. `visemes_for(word)` — an **orthography** table: `VOWELS` {a,e,i,o,u,y}, `DIGRAPHS` {th,ch,sh,ph,oo,ee,ng,wh}, `CONSONANTS` {f,v,m,b,p,s,z,c,k,g,t,d,n,l,r,w,j,q,h,x}. Unmapped characters are silently dropped; a word with no mappable characters yields `['viseme_aa']`.
4. `make_timeline(audio, text, fps=30, words=None)` — per frame:
   - finds the word whose `[start, end)` contains `t`;
   - `gate = smoothstep((energy/high − 0.10)/0.45)` where `high` is the 90th-percentile frame RMS — a **global** energy gate;
   - selects the viseme by **linear position within the word**;
   - envelope `min(1, (t-start)/0.07, (end-t)/0.09)` — a **70 ms attack / 90 ms release** ramp;
   - amplitude **0.73**; `jawOpen` = `gate × 0.29` (**0.10** for `viseme_PP`); `mouthSmileLeft/Right` forced to **0.035**;
   - blink: `closed = max(blink(t, c) for c in (2.15, 5.70, 9.35, 12.60, 16.30))` — **five hard-coded centres**;
   - emits `{'frame','t','morphs'}` with every morph clamped to [0,1].
5. **Output contract:** `{'schema':'livynth.timeline.v1', 'fps', 'duration', 'sync_method', 'disclaimer', 'text', 'words', 'frames'}`.
   - `sync_method` is `'word-timed-spelling-heuristic'` when `--words-json` is supplied, else `'approximate-spelling-and-energy'`.
   - `disclaimer` is literally **`'Not phoneme-accurate: add a real aligner before production use.'`**
6. **Already-existing external input path:** `--words-json` accepts `[{'text','start','end'}]` in seconds, validated by `validate_words()` (finite, `0 ≤ start < end ≤ duration+0.05`, sorted, no overlap > 5 ms).

**Reachable viseme inventory:** the tables produce exactly **14 distinct** targets — `viseme_aa, viseme_E, viseme_I, viseme_O, viseme_U, viseme_TH, viseme_CH, viseme_FF, viseme_nn, viseme_PP, viseme_SS, viseme_kk, viseme_DD, viseme_RR`. Meta's 15-viseme set also contains `sil`, which this heuristic **never emits**.

**Known failure modes (the documented reason the deferral is a decision, not a gap)**

1. **Word boundaries are length-proportional, not phonetic.** "Welcome" (7 letters) receives 7/N of the speech span; a 3-letter word gets `max(2,3)=3`. Actual durations in connected speech vary by more than 3× for identical word lengths.
2. **No phoneme timing at all.** One viseme per *letter*, held for a slice of the word. Real speech runs ~10–15 phonemes/s; this produces ~1 viseme per letter.
3. **Viseme selection is positional, not phonetic.** The 3rd letter of a word gets the 3rd viseme regardless of what the phoneme is, so "port" and "part" can produce identical mouth shapes.
4. **The energy gate deletes stop closures.** Plosive closures (/p/ /b/ /t/ /k/ /d/ /g/) are acoustically *silent by definition*. `gate` scales the viseme toward 0 exactly there, so the lip-closure phase — the single most visible consonant cue — is systematically suppressed. This is the classic MP/FF confusion.
5. **No burst/transition phase.** There is no distinction between the closure and the release of a stop.
6. **Unvoiced fricatives are merged with their voiced twins.** `s`→SS and `z`→SS; `f`→FF and `v`→FF.
7. **Silent letters and heteronyms are wrong.** `psychology` → the `p` is silently dropped but the rule still fires; `live`/`livid` are indistinguishable.
8. **The energy threshold is global.** `high` is the 90th percentile of the *whole file*. On a quiet recording or a file with a loud transient, the gate misbehaves.
9. **No phrase/prosody structure.** The transcript is a single sentence; there is no phrase boundary, no stress, no question intonation.
10. **A blink centre lies outside the audio.** The WAV is **13.997 s**; the blink at **16.30 s** can never fire.
11. **The current heuristic's actual lip-sync error has never been measured.** There is no baseline number in the repo, so "the aligner improved sync" is currently unfalsifiable. This is why the acceptance test in §Q2.4 starts by measuring the baseline.

**What must keep passing** (verified by reading the test files): `tests/test_timeline.py` (11 test methods) and `tests/test_portrait_preset.py` (9 test methods). `tools/local_check.py` additionally asserts, when `--audio` is passed: non-empty `frames`, `schema == 'livynth.timeline.v1'`, and **all morph values in [0,1]**.

## Q2.2 Candidate comparison

| Option | Licence | Python 3.14.7 | Install size | CPU-only | Accuracy expectation | Verdict |
|---|---|---|---|---|---|---|
| **Montreal Forced Aligner 3.4.3** | **MIT** (GitHub API `spdx_id: MIT`; PyPI `License: MIT`; conda-forge `license: MIT`). Models: acoustic + dictionary **CC BY 4.0** | conda-forge build depends on `python >=3.11`, `kalpy >=0.10`, `kaldi`, `openfst`, `sox`, `ffmpeg`, `pynini`, `baumwelch`, `hdbscan`, `ngram`, `numba`, `numpy`, `praatio`, `sqlalchemy`, `huggingface_hub`, `librosa`, `scikit-learn`, … **`kalpy` 0.10.5 has win-64 `py314` builds** → **3.14 OK**. `librosa` 1.0.0 requires `>=3.12` → OK | **≈1–2 GB** (pulls PostgreSQL server, OpenFST, pynini, SoX, FFmpeg, Kaldi) — exactly what ADR decision 4 forbids *during* the geometry gate | ✅ yes | **Best in class.** HMM/GMM acoustic forced alignment; phone-boundary MAE typically 10–30 ms on clean read speech (**UNVERIFIED on this machine**) | **FALLBACK / phoneme-level** |
| **faster-whisper 1.2.1** | **MIT** (PyPI `License: MIT`). Models `Systran/faster-whisper-tiny.en` / `base.en` are `license: mit`, ungated, no account | `requires_python >=3.9`; wheel is pure-python. **Every binary dep has a cp314 win_amd64 wheel**: `ctranslate2` 4.9.0, `onnxruntime` 1.31.1, `av` 19.0.2, `tokenizers` 0.23.3 | ≈150 MB of wheels + ≈75 MB (`tiny.en`) / ≈145 MB (`base.en`) model — **well under the 1–2 GB ceiling** | ✅ yes — CTranslate2 int8 is the reference CPU ASR path | **Word/segment timestamps only — NOT an aligner.** ASR-derived word boundaries typically 20–50 ms on clean speech (**UNVERIFIED here**) | **PRIMARY** (word-level) |
| **stable-ts 2.19.1** | **MIT** | `requires_python >=3.8`; **sdist only**. Base deps pull `openai-whisper` → `torch`, `torchaudio`, `numba`, `tiktoken` | torch already installed; adds numba + tiktoken + openai-whisper (a few hundred MB) | ✅ yes | Improves Whisper timestamp stability; still **word-level** | **Optional add-on only.** Adds a torch-version coupling risk |
| **whisperX 3.8.6** | **BSD-2-Clause** | ❌ **HARD BLOCK**: PyPI `requires_python: "<3.14,>=3.10"` → pip refuses on 3.14.7. Also demands `torch~=2.8.0`, `torchaudio~=2.8.0`, `torchvision~=0.23.0`, `pyannote-audio>=4.0.0`, `torchcodec` — it would **downgrade torch 2.15.0+cpu**, breaking the TripoSR lane's pinned stack | wheel 16.5 MB + torch stack | ✅ yes | Best-in-class word alignment via wav2vec2 | **REJECTED on Python 3.14** |
| **aeneas 1.7.3.0** | ❌ **AGPL-3.0** (PyPI classifier; GitHub API `spdx_id: AGPL-3.0`) | sdist only (5.5 MB); 2018-era; needs `ffmpeg` **and `espeak`** on PATH — **both absent** | ~5 MB source + ffmpeg + espeak binaries | ✅ yes | Genuinely phoneme-level (TextGrid) | **REJECTED on licence.** AGPL-3.0 is network copyleft: linking it into LIVYNTH would require releasing the combined work under AGPL-3.0 |
| **PySimpleAudio** | ❌ **Not a PyPI package** — `pypi.org/pypi/PySimpleAudio/json` returns **HTTP 404**. Its dependency `pyaudio` 0.2.14 ships wheels **only up to cp313** | ❌ no cp314 wheel | — | — | — | **REJECTED on three grounds**: not an aligner at all, no cp314 wheel, not on PyPI |
| **The existing M001 heuristic** | Project code, no third-party component | ✅ pure stdlib | 0 | ✅ | See §Q2.1 — the baseline we are measuring against | **KEPT as the default** |

**Additional option, mentioned but explicitly UNVERIFIED:** `g2p_en` (MIT) for orthography→ARPAbet plus a CTC phoneme model such as `facebook/wav2vec2-lv-60-espeak-cv-ft` (Apache-2.0) gives genuine phone-level timestamps on CPU with a small footprint and no 1 GB install. This was **not** audited (model-revision licence, `nltk` data downloads, `tiktoken`/`espeak` availability on 3.14 unchecked). Listed for a future pass only.

## Q2.3 Recommendation

**PRIMARY — `faster-whisper` (CPU, int8), used as a *word-timing producer*, not as a lip-sync engine.**
It removes the single worst defect of the heuristic (length-proportional word boundaries) at ~150 MB of wheels plus a 75–145 MB model, with **every dependency shipping a cp314 Windows wheel**, MIT code and MIT models, no account, no terms acceptance, and no change to the timeline schema. It feeds the **existing** `--words-json` path, so `make_timeline.py` does not change.

Owner command (run later, after the geometry gate):
```powershell
python -m pip install faster-whisper
python -m faster_whisper --model tiny.en --device cpu --compute_type int8 `
  --word_timestamps True --output_format json --output_dir output\fw `
  --audio assets\voice.wav
```

**FALLBACK (and the only phone-level option that survives the licence screen) — Montreal Forced Aligner 3.4.3**, in a **separate conda env**, only after the owner approves the ≈1–2 GB install and the geometry gate is closed:
```powershell
conda config --add channels conda-forge
conda create -n aligner montreal-forced-aligner -y
conda activate aligner
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
mfa align <corpus_dir> english_us_arpa english_us_arpa output\mfa_out
```
Then convert the TextGrid to our word JSON with `praatio` (MIT, already an MFA dependency). **Licence chain is clean:** MIT code + CC BY 4.0 acoustic model and dictionary → attribution only.

**REJECTED:** whisperX (Python <3.14 pin, would downgrade torch), aeneas (AGPL-3.0), PySimpleAudio (not an aligner, no cp314 wheel, not on PyPI).

**Explicitly out of scope for both:** any aligner that would upload `assets/voice.wav` to a third-party service. `assets/voice.wav` is the owner's voice; no agent may transmit it.

## Q2.4 The exact acceptance test that would prove the timeline improved

**Test A — boundary MAE against a hand-labelled sample of the existing WAV (this is the acceptance test).**

1. **Label.** Human-label `assets/voice.wav` (PCM mono 16-bit, 22050 Hz, 13.997 s, SHA-256 `98FDFCDBD371D848B4846A17820D0F62E398EECEE7C51079CF3056824D4EDD0A`) in Praat:
   - **word level** for the whole file (the transcript is 29 words, `assets/voice_transcript.txt`);
   - **phone level** for one contiguous 3-second excerpt.
   Write `tests/data/voice_labels.json`:
   ```json
   {"audio":"assets/voice.wav","sample_rate_hz":22050,"duration_s":13.997,
    "words":[{"text":"Welcome","start":0.13,"end":0.71}, "..."],
    "phones":[{"text":"W","start":0.13,"end":0.22}, "..."],
    "phone_excerpt_start_s": 0.0, "phone_excerpt_end_s": 3.0}
   ```
2. **Baseline FIRST (mandatory).** Generate the current heuristic's timeline and score it:
   ```powershell
   python video/make_timeline.py --audio assets\voice.wav `
     --text-file assets\voice_transcript.txt --out output\timeline_heuristic.json
   python tools/align_eval.py --labels tests\data\voice_labels.json `
     --timeline output\timeline_heuristic.json --out output\align_heuristic_metrics.json
   ```
   `tools/align_eval.py` is a **new, small, dependency-free** script (numpy only) that matches labelled boundaries to timeline boundaries by text and computes absolute errors. **The heuristic's baseline MAE is UNVERIFIED today and must be measured before anything else.**
3. **Candidate.** Generate the aligner's timeline and score it with the same script and the same labels.
4. **PASS thresholds (proposed — to be ratified by the owner, and adjusted once the baseline is known):**
   - **word-boundary MAE ≤ 60 ms** and **no word boundary worse than 150 ms**;
   - **phone-boundary MAE ≤ 40 ms** and **no phone boundary worse than 100 ms** (phone criterion applies only once a phone-level aligner is in the loop);
   - **the candidate must beat the recorded heuristic baseline on word-boundary MAE by a factor ≥ 2**, otherwise it is not an improvement;
   - the timeline must still satisfy every invariant in §Q2.1.
   - Rationale: MFA's expected phone MAE (10–30 ms) and ASR word-timing MAE (20–50 ms) both sit under these thresholds; the heuristic is expected to land in the 150–400 ms band because its allocation is purely length-proportional. **These thresholds are engineering estimates, not measurements — the baseline measurement in step 2 is what makes them meaningful.**
5. **Regression guard (must stay green, unchanged):**
   ```powershell
   python -m unittest discover -s tests -v
   python -m unittest discover -s geo/tests -v
   python tools/local_check.py --glb assets\ours-photoreal.glb `
     --audio assets\voice.wav --text-file assets\voice_transcript.txt
   ```
   The following invariants are explicitly protected and must not regress:
   - `timeline['schema'] == 'livynth.timeline.v1'`;
   - every morph value ∈ [0,1]; `frames[0]['morphs']['jawOpen'] == 0`;
   - silence ⇒ every `jawOpen == 0`;
   - `fps` outside 12–60 raises `ValueError`;
   - `--words-json` timings are validated (finite, `0 ≤ start < end ≤ duration+0.05`, no overlap > 5 ms);
   - the `disclaimer` field keeps saying **"Not phoneme-accurate"** until a *phone-level* aligner is in the loop;
   - `sync_method` must be one of `approximate-spelling-and-energy` / `word-timed-spelling-heuristic` / `asr-word-timed` / `mfa-phone-timed`. **A word-level ASR result must never be labelled `mfa-phone-timed`, and neither must ever be labelled phoneme-accurate.**

**Test B — M001 gate honesty.** The unchecked acceptance box in `docs/M001.md` — *"Phoneme-aligned timing replaces the current spelling + WAV energy heuristic"* — may be ticked **only** when Test A passes **and** `sync_method` is no longer `approximate-spelling-and-energy`. A faster-whisper result alone (`asr-word-timed`) does **not** satisfy that box; it is an improvement, not phoneme alignment.

## Q2.5 Why the current heuristic keeps passing meanwhile

- The ADR defers the **installation**, not the **interface**. `make_timeline.py` already accepts externally produced word timings (`--words-json`) and already stamps `sync_method` and `disclaimer`. **An aligner is a producer of `--words-json`, not a replacement for `make_timeline.py`.** So the current code path, its outputs and its tests are untouched by any aligner decision.
- The heuristic is the correct **fail-safe default**: deterministic, stdlib-only, licence-free, zero-install, and already covered by the repo's tests plus the geometry tests. Swapping the default before the acceptance test exists would replace a known-bad-but-measurable baseline with an unmeasured one.
- The deferral is **documented as a decision**: §Q2.1 enumerates the eleven named failure modes of the current heuristic, §Q2.3 names the primary and fallback with their licences and 3.14 compatibility, and §Q2.4 fixes the metric that will lift the deferral.
- **Nothing in the geometry gate depends on the aligner.** `tools/local_check.py`, the geometry tests and the Blender render path are all unaffected by `sync_method`; the timeline is consumed downstream by `video/render_talk.py` as morph curves.
