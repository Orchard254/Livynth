# C001-GEO-04 (B) — Morph-preserving retopology path for Character 001

**Agent:** `topology-specialist`
**Branch:** `experiment/c001-geo04-topology`
**ADR:** `docs/decisions/ADR-C001-004-phase3-repair.md`, Decision 1 + the mandatory geometry-first acceptance protocol
**Companion document:** `docs/C001_GEO04_BASEMESH_PROVENANCE.md` (the CC0 verification this path depends on)
**Date:** 2026-11-11
**Status:** **Plan, with Stage 0 already executed and measured.** Stages 1–7 are specified, not executed; every unexecuted step is marked.

---

## 0. The one architectural fact that decides the whole design

Measured on this machine, from the actual shipped asset:

> MakeHuman/MPFB `.target` files are **sparse per-vertex displacement maps over the
> basemesh's own vertex indexing**.
>
> `…\mpfb\data\targets\faceunits\browInnerUp.target`:
> ```
> 1 .001 .001 0
> 3 .001 .001 .001
> 5 .002 .002 .001
> 56 .001 .001 .001
> 59 0 .001 .001
> …
> ```
> i.e. `<basemeshVertexIndex> <dx> <dy> <dz>`.

Therefore:

* The ARKit morph targets are **already expressed on the quad basemesh**.
* If we **do not change the vertex set** of the basemesh, the morph rig survives
  *by construction* — nothing needs to be transferred.
* "Retopology" for Option B is therefore **not** "remesh the scan onto a new
  mesh". It is:

> **Make the CC0 quad basemesh the topology authority, and fit Character 001
> onto it by deforming its vertices.**

This is a fundamentally lower-risk operation than remeshing: it keeps the
vertex↔target correspondence exact, keeps the 152 vertex groups, keeps the
67-joint rig weights, and keeps the non-overlapping UV layout — all of which
are *per-vertex* properties of the basemesh.

### 0.1 Three cases, and what each costs

| Case | Vertex set | Morph targets | Weights | UV | Risk |
|---|---|---|---|---|---|
| **(a) Deform the basemesh in place** ⭐ **recommended** | unchanged | **no transfer needed** — re-apply to the deformed neutral | unchanged | unchanged | **low** |
| (b) Subdivide the basemesh for facial detail | new vertices | must be **propagated** (barycentric interpolation on base triangles) | interpolate | inherit + re-unwrap | medium |
| (c) Remesh onto a *different* quad mesh (e.g. Blender Essentials human) | new | must be **dense→base transferred** (project dense sculpt, then re-fit) | **re-fit from scratch** | re-unwrap | **high** — and it also loses the 52-target facial system |

Case (c) is the one the ADR's phrase "dense-to-base transfer" anticipates.
**This plan recommends case (a), with case (b) as the only sanctioned
escalation.** Case (c) is rejected — see §6.

---

## 1. Target pipeline (end to end)

```
                    Character 001 references (15 PNG, approved views)
                                     │
                     MediaPipe landmarks (8 views detected, calibrated=false)
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 1  Fit the CC0 quad basemesh to the measured identity       │
   │          (per-vertex deformation; topology untouched)              │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 2  Re-bake the 52 ARKit + 15 viseme targets onto the        │
   │          FITTED neutral; verify every target still moves the      │
   │          right vertices                                             │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 3  UV: keep the MakeHuman region-aware layout; add a       │
   │          dedicated face island at 2048² (ADR decision 6)          │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 4  Texture bake: 2048×2048 PBR (base colour / normal /     │
   │          roughness / AO) from the approved reference captures     │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 5  Hair: CC0 MakeHuman hair cards + auburn albedo tint      │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 6  Eyeballs + eyelids: separate eyeball mesh, UV-mapped     │
   │          sclera/iris, eyelid geometry driven by eyeBlink targets  │
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
   ┌─────────────────────────────────▼─────────────────────────────────┐
   │ STAGE 7  Final morph set + rig + export; then the ADR's           │
   │          blind geometry-first gate                                │
   └───────────────────────────────────────────────────────────────────┘
```

Stage 0 (the unmodified CC0 basemesh → rigged, morph-enabled, exported GLB)
is **already done and measured** — see §2.

---

## 2. STAGE 0 — BASELINE (EXECUTED, MEASURED, PASS)

**Command**

```powershell
$w = 'C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-topology'
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background `
    --python tools\mpfb_headless_probe.py -- `
    --out output\c001_geo04\probe.glb --json output\c001_geo04\probe.json
```

**Measured result** (`tools/mpfb_headless_probe.py`, all steps `ok`, `errors: []`;
37.52 s wall clock on the first run, 20.3 s on a warm re-run)

```
create_human                  = ok     -> 19158 verts / 18486 polys / 100.00 % quads
                                            uv ["UVMap"] / 152 vertex groups
                                            shape keys [Basis, $md-$ca-$ma-$yn,
                                            $md-universal-$ma-$yn-$av$mu-$av$wg]
create_character_copy         = ok
bake_targets                  = ok     -> bakes the macro modelling shape keys
bake_modifiers_remove_helpers = ok     -> 13380 verts / 13378 polys / 100.00 % quads
load_face_targets             = ok     -> 52 ARKit face units + 15 Meta visemes
interpolate_targets           = ok
export_glb                    = ok     -> 15090388 bytes
```

**Stage 0 exit criteria — all met**

| Criterion | Measured | Status |
|---|---|---|
| Quad-dominant base | 100.00 % quads (13 378/13 378 baked) | PASS |
| Single connected body shell | 1 component for the `body` group | PASS |
| Non-manifold edges | 0 | PASS |
| Loose vertices | 0 | PASS |
| UV layer present | `UVMap`, non-overlapping (0 overlapping cells @512²) | PASS |
| Vertex groups | 152 | PASS |
| ARKit morph targets load | 67 shape keys | PASS |
| ADR-required ARKit names present | 10/10 `true` | PASS |
| Targets actually displace geometry | yes — e.g. `jawOpen` 2 249 verts / 3.87 mm, `eyeBlinkLeft` 718 verts / 1.26 mm | PASS |

**This is the acceptance gate for my own task**: quad topology inspection ✅
and a working neutral/blink/jaw morph rig ✅. What is *not* yet proven is that
the rig still works **after** the identity fit — that is Stage 2.

---

## 3. STAGE 1 — Fit the basemesh to Character 001 (identity fit)

**Goal:** move the neutral basemesh vertices so the face matches the reference
photographs, **without changing one vertex index, one face, one UV, or one
vertex group**.

### 3.1 Inputs available right now (read-only)

* **Photographs** — `C:\PROJECT\Livynth\assets\characters\character_001\identity_capture_v1\`
  (15 PNGs; canonical front `01_subject_front.png` 1086×1448).
* **Auto-detected landmarks** (C001-GEO-03, MediaPipe FaceMesh 1.2.2, `refine_landmarks=True`),
  schema `livynth.c001.landmarks` v2.0.0, in
  `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo03-landmarks\output\landmarks_tasks\`.
  **Detected (31 points each):** `front`, `front_closeup`, `left_45`, `right_45`,
  `profile_left`, `profile_right`, `right_ear`.
  **Not detected (no face in frame):** `back`, `top`, `eyes_closeup`, `iris_macro`,
  `skin_macro`, `lips_closeup`, `hair_closeup`, `left_ear`.
  Point vocabulary: `canthus_outer/inner_{r,l}`, `upper/lower_eyelid_{r,l}`,
  `brow_{inner,mid,outer}_{r,l}`, `nose_bridge_top/bottom`, `nose_tip`,
  `nostril_{r,l}`, `mouth_corner_{r,l}`, `upper/lower_lip_mid`, `chin`,
  `jaw_angle_{r,l}` (confidence 0.6), `hairline_center` (confidence 0.6),
  `iris_center_{r,l}`, `pupil_center_{r,l}`.
  **Unmapped in every view:** `ear_top_{r,l}`, `ear_bottom_{r,l}`, `tragus_{r,l}`.
* **Manual anchors from C001-GEO-02** — `geo/character001_landmarks.json`
  (eyes, chin, mouth corners) and the crown/chin/ear pixel annotations in
  `geo/proxy_fit.py` (`VIEWS`: front `01_subject_front.png` crown 55 chin 924;
  left `04_left_profile.png` crown 40 chin 980; right `05_right_profile.png`
  crown 34 chin 940).
* **The basemesh's own anatomical anchors** — the `joint-*` cube centroids in
  `base.obj` (measured in `docs/C001_GEO04_BASEMESH_PROVENANCE.md` §3.2):
  `joint-l-eye` = (0.3077, 7.2842, 1.2453), `joint-mouth` = (0, 6.8848, 0.6414),
  `joint-jaw` = (0, 6.1907, 1.4248), `joint-neck` = (0, 5.8902, 0.068),
  `joint-head` = (0, 6.9749, 0.1608), `joint-head-2` = (0, 8.4044, 0.0824).

### 3.2 The method: a constrained, landmark-anchored, smooth warp

Do **not** use a free-form warp — the ADR explicitly recorded that a
"jitter canary (σ = 8 px)" and a "wrong-identity canary (face widened 1.18×)"
both *passed* similarity-aligned 2D metrics. The gate must be geometry-level.

Proposed fitting operator (all local, no external service):

1. **Camera solve per view.** For each of the 5 gate views (front, L45, R45,
   L90, R90) solve a weak-perspective camera from the *reference* landmarks
   plus the basemesh's own projected landmark set, using a rigid + uniform
   scale + translation model. The `calibrated: false` flag on the C001-GEO-03
   landmark JSONs means this solve is **required**, not optional.
2. **Correspondence.** Establish basemesh-vertex ↔ reference-landmark
   correspondence using the basemesh's own joint anchors for the coarse level
   and the detected landmarks for the fine level (eyes, brows, nose, mouth,
   jaw, chin).
3. **Warp.** Apply a *smooth, partition-of-unity* displacement field
   (moving-least-squares / as-rigid-as-possible style, with a distance
   falloff and a stiffness weight per region) to the neutral basemesh
   vertices. Constraints:
   * anchors (eye corners, brows, nose tip, nostrils, mouth corners, chin,
     jaw angles) move **exactly** to their target;
   * non-anchor vertices move as little as possible (ARAP/rigid as possible);
   * the deformation is **volume-preserving enough** to avoid eyeball
     interpenetration and eyelid inversion.
4. **Symmetry.** The basemesh is **100.000 % mirror-symmetric** (measured).
   Fit the **left half** and mirror it, so asymmetry in the reference (which is
   mostly lighting/camera, not anatomy) cannot leak in as geometry.
5. **Scale/position.** Fix the world transform so the model faces the same way
   as the existing pipeline expects (the repo already has a documented camera
   convention in `geo/setup_blender_fit_scene.py`).

**Reuse of existing repo code.** `geo/morph_fit.py` (C001-GEO-02) already
implements exactly this kind of operation — "conservative, reversible fitting
of an existing morph-enabled GLB … preserving scene, skin, animation and
texture tables" — with a required-morph-name check
(`{'eyeBlinkLeft','eyeBlinkRight','mouthSmileLeft','mouthSmileRight','jawOpen'}`)
and `geo/audit_morph_fit.py` as the auditor. **Stage 1 should reuse
`geo/morph_fit.py`'s fitting core** rather than write a second implementation,
but pointed at the MPFB-produced GLB instead of the retired V32 GLB.

### 3.3 Stage 1 failure modes

| Failure mode | Detection | Mitigation |
|---|---|---|
| Reference landmarks mis-detected on a 45°/90° view | `calibrated: false`; compare front vs 45° eye-spacing ratio | Re-solve the camera; if a landmark is unreliable (confidence 0.6 group: `jaw_angle_*`, `hairline_center`), down-weight it or exclude it |
| **Camera not calibrated** — the same 2D metric trap the ADR caught | reproject fitted landmarks and compare *3D* residuals, not 2D similarity | Solve the camera in Stage 1 step 1; report residual in millimetres |
| Over-fit → identity "solves" but the mesh self-intersects | self-intersection test on the fitted mesh (trimesh `is_watertight`, `is_winding_consistent`, plus a BVH self-overlap test) | reduce anchor weight, increase falloff radius |
| Under-fit → generic MPFB face | the gate's *wrong-identity canary* (1.18× width) must be **rejected**; if the fitted face is near-generic, the canary will also pass ⇒ gate invalid | increase landmark weight; if it still can't separate identity from generic, **the basemesh alone cannot carry Character 001's identity and the ADR's Option B needs a different topology source** — report that rather than forcing it |
| Eyeball interpenetration | compare eyeball radius vs eyelid aperture after fit | exclude eyeball region from the warp; move the eyeball socket instead |
| Deforming past the basemesh's authored intent (e.g. tearing the lip corners) | per-region displacement magnitude report; compare against the joint-anchor ranges | clamp per-region max displacement; log the clamp |
| **A fitted identity that only exists because the camera was fudged** | run the canary with a *deliberately wrong* camera and confirm the gate still rejects | this is the ADR's `gate_valid: false` condition — never ship a result from a gate whose controls were not rejected |

---

## 4. STAGE 2 — Re-bake the morph rig onto the FITTED neutral (the crux)

### 4.1 Why this is the crux and why it is tractable

The naive worry: "retopology destroys the blendshape rig". With the MakeHuman
target format that worry is unfounded in case (a):

* A `.target` file is a **displacement field over basemesh vertex indices**.
* After Stage 1 the vertex indices are **identical** — only their positions
  changed.
* MPFB's own machinery does the re-application: `TargetService.bake_targets()`
  + `FaceService.load_targets()` + `FaceService.interpolate_targets()` are
  applied **after** the base has been deformed, in exactly that order in the
  proven pipeline (`build_photoreal.py` lines 379–397, mirrored in
  `tools/mpfb_headless_probe.py`).
* Consequently the ARKit targets are **re-evaluated against the fitted
  neutral**, i.e. the blink closes the *fitted* eyelids, the jaw opens the
  *fitted* mouth.

### 4.2 The actual procedure

```
1. MPFB human (macro chosen for Character 001: male, adult, caucasian)
2. Stage-1 neutral fit  ->  write the fitted neutral back into the basemesh
                            (same vertex order!)
3. TargetService.bake_targets(basemesh)
4. ExportService.bake_modifiers_remove_helpers(basemesh, bake_masks=True,
                                               bake_subdiv=True,
                                               remove_helpers=True,
                                               also_proxy=True)
5. FaceService.load_targets(basemesh, load_microsoft_visemes=False,
                             load_meta_visemes=True,
                             load_arkit_faceunits=True)
6. FaceService.interpolate_targets(basemesh)
7. export GLB with export_morph=True, export_morph_normal=True
```

**Implementation constraint.** Step 2 must happen **inside Blender**, on the
MPFB basemesh object, *before* step 3 — because `bake_targets` bakes the
*modelling* shape keys (the macro sliders) into the base shape and the facial
targets are applied afterwards. Fitting the exported GLB and re-importing it
would break the target↔vertex correspondence (the GLB's `base.001` has
**14 517** vertices vs the basemesh's **13 380** because glTF splits vertices
at UV/normal seams — the glTF vertex index is *not* the basemesh vertex index).

⇒ **The fit must be applied to the Blender-side basemesh, not to a GLB.**

### 4.3 Verification of Stage 2 (this is the acceptance gate)

After Stage 2, re-run the same measurement as Stage 0 and require:

| Check | Stage 0 measured | Stage 2 requirement |
|---|---|---|
| Morph target count | 67 | 67 |
| ADR-required ARKit names | 10/10 present | 10/10 present |
| `eyeBlinkLeft` vertices moved | 718 | ≥ 600, and **in the eyelid region only** |
| `jawOpen` vertices moved | 2 249 | ≥ 2 000, and **in the mandible region only** |
| `mouthSmileLeft` max displacement | 0.018682 | ≥ 0.015 |
| Neutral polygon class | 100 % quads | 100 % quads |
| Neutral shell count | 1 body shell | 1 body shell |
| Non-manifold edges | 0 | 0 |
| Self-intersection after fit | n/a | 0 |

The two "region only" checks are new and matter: a target that moves the
*wrong* vertices is the classic silent failure of a transferred blendshape rig,
and it is invisible in a thumbnail.

### 4.4 Stage 2 failure modes

| Failure mode | Symptom | Mitigation |
|---|---|---|
| Fit applied to the GLB instead of the Blender mesh | morph targets missing or garbage after export | §4.2 implementation constraint; assert `len(basemesh.data.vertices) == 13380` before baking |
| Vertex order broken by a "helpful" sort/dedup | all targets apply to wrong vertices | never reorder vertices; assert the basemesh hash of the first N vertex positions before/after fit |
| Target displacement magnitude changes under the fit | blink too weak/too strong | the target's displacement is applied *on top of* the fitted neutral; if the fit shrank the eyelid region, re-tune by re-authoring the affected target, **not** by scaling the whole rig |
| Lip corner tearing | mouthFunnel/mouthPucker invert | limit Stage-1 displacement in the lip region; verify `mouthFunnel`/`mouthPucker` max displacement and visual check |
| Eyelid inversion after a large eye-region fit | blink shows the sclera above the lid | exclude the eyelid margin from the warp field; move the socket instead |
| Jaw target opens a seam | gap at the neck | keep the neck vertices rigid; the `joint-neck` anchor is a natural boundary |
| `interpolate_targets` shifts the neutral | the neutral face is subtly wrong even at weight 0 | verify the exported neutral against the fitted neutral (vertex-wise) and report max deviation |
| glTF morph-normal export artefacts | shading pops at extreme targets | `export_morph_normal=True` (already used); if artefacts persist, export `export_morph_normal=False` and recompute normals in-engine — record the choice |

---

## 5. STAGES 3–7 — asset build-out

| Stage | What | Source | Failure modes | Owner approval |
|---|---|---|---|---|
| **3. UV** | Keep the MakeHuman region-aware layout (measured: full-square, **0 overlapping cells**). If the face needs more texels, cut a dedicated face island in the face UV region and re-pack. | CC0 basemesh UVs | Non-uniform texel density; seam placement across the mouth line | none |
| **4. Texture bake** | Bake base colour / normal / roughness / AO at **2048×2048** (ADR decision 6). Source: the 15 approved PNGs, projected **only as a colour source** — the geometry must already pass the gate first. | local PNGs | **Colour bleeding from a photo projection** (the exact ADR failure mode); projection must be photo-independent for the geometry gate | none, but **no upload to any external service** |
| **5. Hair** | CC0 MakeHuman hair (`short01`/`short02`/`bob01`/`long01` — all CC0 per the upstream asset page) + auburn albedo tint. Hair *cards* for the silhouette. | CC0 | Card silhouettes read as cut-out from 90°; card orientation must be verified in the R90 view | none |
| **6. Eyeballs / eyelids** | Eyeball as a separate mesh (CC0 `high-poly` eyes), own UV for sclera + iris; eyelids driven by `eyeBlinkLeft/Right`; iris colour = hazel/amber per the reference | CC0 | Iris parallax mismatch; eyelid clipping at full blink; **eyelid geometry must be verified at 0.0, 0.5 and 1.0** | none |
| **7. Export + gate** | Export GLB with `export_morph=True`, ARKit names, rig + weights. Then run the ADR's geometry-first acceptance protocol. | — | See §8 | **the blind review itself needs the ADR's protocol**; the reviewer must be independent and sealed |

### 5.1 The ADR's 6 morph targets — name mapping

The ADR asks for "6 ARKit-style morph targets (browInnerUp, browOuterUp,
mouthSmile, mouthFunnel, mouthPucker, eyeBlinkLeft/Right equivalents)". The
installed ARKit set uses **bilateral** naming; the mapping is:

| ADR asks for | ARKit name(s) in the installed pack | Present (measured) |
|---|---|---|
| `browInnerUp` | `browInnerUp` | ✅ |
| `browOuterUp` | `browOuterUpLeft`, `browOuterUpRight` | ✅ |
| `mouthSmile` | `mouthSmileLeft`, `mouthSmileRight` | ✅ |
| `mouthFunnel` | `mouthFunnel` | ✅ |
| `mouthPucker` | `mouthPucker` | ✅ |
| `eyeBlinkLeft/Right` | `eyeBlinkLeft`, `eyeBlinkRight` | ✅ |
| (jaw, needed by the motion QA) | `jawOpen` | ✅ |

All are already in the 67 measured shape keys, so **no new morph asset is
required** — the ADR's morph requirement is met by the CC0 pack that is
already installed.

---

## 6. Alternatives explicitly rejected

| Alternative | Why rejected |
|---|---|
| **Retopo onto Blender's Essentials "Human Base Meshes"** | Not installed on this machine (§1.3 of the provenance doc) and would need a download; ships **without** MakeHuman's 67-target facial system and without the 52 ARKit face units; would force case (c) — full dense→base transfer **and** a from-scratch weight re-fit. Strictly worse on every axis. |
| **Retopo onto `ours-photoreal.glb` (the V32 avatar)** | ADR decision 5 retires it from the C001 critical path; it is the female preset "Blue" (wrong identity, wrong gender); it is triangulated, so the quad advantage is already gone; it carries no rig weights in the glTF (`skins: []` measured) — it would need rigging from scratch. |
| **Retopo onto the visual-hull Candidate A** | ADR decision 2 bounds it to *one* diagnostic repair experiment; it is a photographic projection on a shell (Phase-3 evidence), and its geometry already failed the blind gate. Using it as a topology source would re-import exactly the failure the ADR is trying to remove. |
| **Retopo onto the TripoSR Candidate B** | ADR decision 2: "Do not try to salvage B's likeness in this round"; Phase-3 found it is a different, generic person. |
| **Import FLAME 2023 Open as the topology source** | ADR decision 3: *evaluation* approved, **import not automatically authorised**; no account may be created and no terms accepted. Out of scope for this agent; FLAME was not downloaded, not imported, not evaluated. |
| **A dense→base transfer onto the MPFB basemesh** (case c) | Only needed if we changed the vertex set. Since we do not, it is pure risk: it introduces per-target transfer error, weight re-fit error and UV re-wrap error, for zero benefit. |
| **Subdividing the face for extra detail** (case b) | Permissible but **not now**: it forces target propagation and weight interpolation, and the measured base is already 100 % quads with 97.6 % regular valence-4 vertices in the body. Escalate only if Stage 1's fit cannot reach the required geometric accuracy, and then only by subdividing the **face region** with a documented propagation step. |

---

## 7. Where owner approval is required

| # | Item | Needed? |
|---|---|---|
| 1 | **Acquiring the basemesh** | **NOT NEEDED** — it is already installed and CC0-verified. Nothing to download, no account, no purchase. |
| 2 | Running Blender headlessly on this machine | Not needed — already the project's tool. |
| 3 | Using the C001 reference photographs locally | Not needed — they are the project's own approved assets and stay on this machine. |
| 4 | **Uploading any portrait to an external service** | **PROHIBITED** without explicit approval — and this plan never does it. |
| 5 | Installing an aligner / heavyweight dependency | **DEFERRED** by ADR decision 4 — not needed for the geometry gate. |
| 6 | Importing FLAME 2023 Open | **NOT AUTHORISED** by ADR decision 3. |
| 7 | Creating any account / accepting terms | **PROHIBITED** without approval; not needed here. |
| 8 | Merging this branch / pushing | **NOT AUTHORISED** — the ADR requires owner review. |
| 9 | The blind geometry review itself | Governed by the ADR's protocol; a separate independent reviewer, with sealed IDs and no `eval.json` inside the bundle. |
| 10 | Shipping the final model | Requires the ADR gate to pass, including the **wrong-identity canary being rejected**. |

---

## 8. Acceptance criteria for the whole path (ADR geometry-first protocol)

The path is **not** done when a GLB exists. It is done when:

1. **Neutral untextured clay renders + wireframes** exist for front, L45, R45,
   L90, R90, with an explicit camera convention, and the photo-projection
   materials are switched off.
2. **Artifact QA** reports: manifoldness, duplicate shells, self-intersections,
   topology class (expect 100 % quads pre-export / triangulated post-export),
   face-normal consistency, camera scale assumptions, and a **working** rig +
   blendshape inventory.
3. **The wrong-identity canary (1.18× face width) is REJECTED** by the gate.
   If it is accepted, the result is `gate_valid: false` — **BLOCKED**, not
   passed. (This is the exact control that the Phase-3 2D metrics failed.)
4. **Motion QA**: neutral, half blink, full blink, jaw open, smile, lip
   closure — no penetration, no folds, no asymmetry. The Stage-0 baseline
   already gives the morph inventory to test against; Stage 2 must reproduce
   it after the fit.
5. **An independent blinded human review** with a per-view rubric; the
   stricter aggregate label wins; a rejected profile cannot be overridden by a
   good front texture.
6. **No quality claim from a photograph projected onto a shell.** Albedo and
   2D similarity numbers remain diagnostic.

---

## 9. Risk register — the honest part

| Risk | Likelihood | Impact | Mitigation / decision |
|---|---|---|---|
| The MPFB basemesh's **authored anatomy** cannot express Character 001's specific face (e.g. a distinctive nose or jaw) within the vertex budget | **medium** | **high** — the whole identity | This is the *real* risk of Option B, and it is a **geometry-capability** risk, not a topology or licence risk. Mitigation: MakeHuman/MPFB ship **~250 facial targets** (`…\mpfb\data\targets\{nose,mouth,eye,head,neck,torso,…}\*.target.gz`) — a large, CC0 library of **anatomically meaningful** deformations (`nose-width3-incr`, `chin-prognathism-decr`, `cheek-bones-decr`, `head-oval`, `mouth-scale-horiz-incr`, …). Stage 1 should use these to *pre-shape* the neutral before the landmark warp, rather than asking a generic warp to invent anatomy. **If the targets still cannot reach the required accuracy, report that as a finding for the ADR — do not fake it.** |
| Reference photographs are **independently generated**, not camera-calibrated | **certain** (stated in AGENTS.md) | high for Stage 1 | The Stage-1 camera solve is mandatory; and the ADR's protocol demands 3D plausibility evidence, not scan accuracy. Explicitly record "plausibility gate, not measured scan accuracy". |
| C001-GEO-03 landmarks are `calibrated: false` and 6 ear points are unmapped in every view | **certain** | medium | Ears and back-of-head must be driven by the basemesh + macro targets, not by landmarks; declare the ears as "generic, from the basemesh" in the report rather than implying they were fitted. |
| The `joint-*` face controls (Orbicularis, Eye) are MakeHuman's, not ARKit's | medium | low–medium | Stage 7 should keep both: the ARKit morph targets (for the viewer's blendshape vocabulary) **and** the MPFB rig (for physical eyelid/eye control). They are complementary, not alternatives. |
| Storing the probe GLB in `output/` on a machine with 16 GB RAM | low | low | 15 MB — trivial. But the *pre-existing* `mpfb.glb` sits in `%TEMP%`; do not rely on `%TEMP%` for anything that matters. |
| `assets/characters/**` and `*.glb` are git-ignored | certain | low | No binary is committed; provenance travels in the JSON/Markdown reports, which *are* committed. |

---

## 10. Execution status of this document

| Stage | Status |
|---|---|
| STAGE 0 — CC0 basemesh → rigged, morph-enabled GLB | **EXECUTED, MEASURED, PASS** (§2; re-run confirmed reproducible) |
| STAGE 1 — identity fit | **SPECIFIED, NOT EXECUTED** |
| STAGE 2 — re-bake morph rig onto the fitted neutral | **SPECIFIED, NOT EXECUTED** |
| STAGE 3 — UV | **SPECIFIED, NOT EXECUTED** |
| STAGE 4 — texture bake | **SPECIFIED, NOT EXECUTED** |
| STAGE 5 — hair cards | **SPECIFIED, NOT EXECUTED** |
| STAGE 6 — eyeballs / eyelids | **SPECIFIED, NOT EXECUTED** |
| STAGE 7 — final export + ADR gate | **SPECIFIED, NOT EXECUTED** |

**Recommended next action:** execute **STAGE 1 + STAGE 2 together** as one
bounded experiment on the `experiment/c001-geo04-topology` branch, reusing
`geo/morph_fit.py`'s fitting core, and emit the §4.3 verification table. That
experiment answers the only question that remains: *can the CC0 quad basemesh
carry Character 001's identity while keeping a working ARKit morph rig?*

---

## 11. Provenance block

* **Source commit (branch base):** `b0235c1`
* **Branch:** `experiment/c001-geo04-topology`
* **Worktree:** `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-topology`
* **Environment:** Windows, Python 3.14.7, numpy 2.5.3, Blender 4.5.10 LTS
  (`6dc0b208d1b5`), MPFB extension 2.0.18
* **Key input hashes:**
  * `base.obj` → `sha256 8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c`
  * `01_subject_front.png` → `sha256 9d84f485883ce613d12d02d9f8f85e338ebe950d7248d522bf3117901eaed2dd`
    (as recorded in the C001-GEO-03 `front.json` landmark provenance)
* **Artifact paths:** `output/c001_geo04/{probe.json, probe.glb,
  probe_glb_topology.json, base_obj_topology.json, base_obj_blender_audit.json}`
  — **all git-ignored; no binaries committed**
* **Known failure modes:** see §3.3, §4.4, §9
