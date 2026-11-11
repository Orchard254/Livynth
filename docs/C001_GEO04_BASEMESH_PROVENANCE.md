# C001-GEO-04 (A) — CC0 basemesh provenance verification

**Agent:** `topology-specialist`
**Branch:** `experiment/c001-geo04-topology`
**ADR:** `docs/decisions/ADR-C001-004-phase3-repair.md`, Decision 1
**Date:** 2026-11-11
**Status:** **PASS with conditions** — one verified, redistributable, quad-dominant CC0 basemesh exists **on this machine today** and is already installed into the project's Blender.

ADR Decision 1 verbatim:

> **Topology Option B: APPROVED, conditional on provenance.** Use the candidate CC0 quad base mesh for retopology after verifying source, attribution, topology suitability and the exact license. A CC0 claim in a report is not license verification.

This document performs that verification from primary sources. Every license
statement below is backed by a **file actually shipped with the asset** or by
the **upstream project's own repository/website**. Nothing is inferred from a
filename, a blog post, a third-party README, or a previous agent's report.

---

## 0. Executive summary

| Question | Answer |
|---|---|
| Is there a quad base head mesh on this machine? | **Yes** — `base.obj` (MakeHuman `hm08`), shipped inside the installed MPFB extension |
| Is its license verified from a primary source? | **Yes — CC0 1.0 Universal**, verified three independent ways (§2) |
| Is it redistributable? | **Yes** — CC0 waives all copyright and related rights; the upstream project also states MPFB *output* carries no restriction |
| Is it quad-dominant? | **Yes — 100.00 % quads** (18 486 / 18 486 faces), 0 tris, 0 ngons |
| Is it usable for face-region deformation? | **Yes** — measured 100 % quads in brow / eye-socket / nose / lips / jaw / neck regions; 97.61 % of body vertices have regular quad valence 4 |
| Does it have UVs usable for baking? | **Yes** — one full `[0,1]²`-spanning, **non-overlapping** UV layout (0 overlapping cells of 83 621 at 512²) |
| Is it rigged? | It is a raw sculpt base, but MPFB ships **152 vertex groups**, a 67-joint rig definition (incl. `Jaw`, `Head`, `Neck`, `Left/RightEye`, `Left/RightOrbicularisTop/Bottom`), and per-target rig weights |
| Does it carry the required morph targets? | **Yes** — 52 ARKit face units + 15 Meta visemes are installed on this machine and were **successfully loaded and measured** in a headless run (§4) |
| Is Blender's bundled `rig_human` present? | **No** — it does not exist in this Blender build (§1.3) |
| Anything that blocked the whole option? | **No.** Nothing needs to be downloaded, registered for, purchased, or approved before work can start |

**Bottom line:** Option B is **unblocked**. The recommended basemesh is the
MPFB/MakeHuman `hm08` basemesh already installed at
`C:\Users\orcha\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\mpfb\data\3dobjs\base.obj`.

---

## 1. Machine inventory — what basemeshes actually exist here

### 1.1 Search method (exhaustive, reproducible)

```
# every .obj on the machine
cmd /c "dir C:\*.obj /s /b 2>nul"                       -> 107 hits
# every .glb on the machine
cmd /c "dir C:\*.glb /s /b 2>nul"
# every .gltf / .fbx on the machine
cmd /c "dir C:\*.gltf /s /b 2>nul"   -> 0
cmd /c "dir C:\*.fbx  /s /b 2>nul"   -> 0
# every .blend on the machine
cmd /c "dir C:\*.blend /s /b 2>nul"  -> 1 (Blender userpref.blend) + Blender's own app templates
# every blender.exe on the machine
cmd /c "dir C:\blender.exe /s /b 2>nul" -> 1
# MPFB / MakeHuman addon directories
Get-ChildItem C:\ -Recurse -Directory  (mpfb | MPFB | makehuman | blender_mpfb)
# *.mpfb files
Get-ChildItem C:\ -Recurse -Filter *.mpfb  -> 0
```

Result: **exactly one Blender installation** (4.5.10 LTS), **exactly one**
third-party human basemesh on disk, and **no** vendor/gated assets.

### 1.2 Candidate basemesh inventory

| # | Path | Size (bytes) | Class | License |
|---|---|---|---|---|
| **C1** | `C:\Users\orcha\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\mpfb\data\3dobjs\base.obj` | 1 749 303 | **quad base mesh (MakeHuman `hm08`)** | **CC0 1.0 — VERIFIED** |
| C2 | `…\extensions\user_default\mpfb\data\proxymeshes\*\*.obj` (7 proxies) | 0.3–0.6 MB ea. | quad *proxy* meshes (region masks, not base meshes) | CC0 — VERIFIED (§2.3) |
| C3 | `…\extensions\.user\user_default\mpfb\data\targets\faceunits\*.target` (52) | 4.9–40 KB ea. | ARKit face-unit morph targets | CC0 — VERIFIED (§2.4) |
| C4 | `…\extensions\.user\user_default\mpfb\data\targets\visemes\*.target` (15) | 30–53 KB ea. | Meta/ARKit-v2 viseme morph targets | CC0 — VERIFIED (§2.4) |
| C5 | `C:\Program Files\Blender Foundation\Blender 4.5\4.5\datafiles\assets\` | — | Blender bundled asset library: **brushes + geometry nodes only** | CC0 — VERIFIED (§2.5). **Contains no human mesh** |
| C6 | `C:\Users\orcha\OneDrive\Documents\Default Project\our_avatar\assets\ours-photoreal.glb` | 26 735 904 | MPFB/MakeHuman-derived avatar ("Blue"), **retired** by ADR decision 5 | MPFB-output → unrestricted (§2.6) — but *not a basemesh* |
| C7 | `C:\Users\orcha\AppData\Local\Temp\opencode\face_lab\assets\mpfb.glb` | 36 815 920 | MPFB export with 67-joint rig + 66 morph targets | as C6 — and it lives in a **temp dir** (fragile) |
| C8 | `C:\Users\orcha\OneDrive\Documents\Default Project\our_avatar\assets\packs\*.zip` | 45–281 MB | downloaded asset packs (`makehuman_system_assets`, `faceunits01`, `visemes02`, mpfb) | CC0 — VERIFIED (§2.4) |

Everything else the `.obj` sweep found is irrelevant: Visual Studio CRT
stub objects (`chkstk.obj`, `binmode.obj`, …) and `greenlet` MASM stubs.

### 1.3 Blender's bundled `rig_human` — **not present**

The task brief suggested Blender 4.5.10 LTS might ship `rig_human` under
`datafiles/assets/`. **It does not.** Measured:

```
Get-ChildItem 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\datafiles\assets' -Recurse
  -> brushes/            (10 .blend brush libraries)
  -> geometry_nodes/     (2 .blend node-group libraries)
  -> blender_assets.cats.txt
  -> LICENSE
Get-ChildItem <blender> -Recurse -Filter 'rig_human*'   -> 0 results
```

`blender_assets.cats.txt` contains catalogs for `Brushes/...`, `Hair/...` and
`Normals` only — **there is no "Human Base Meshes" catalog**. Blender 4.5 does
not ship a human base mesh in `datafiles/assets`; the human base meshes live in
the separately-downloadable Essentials asset library, which is **not installed
on this machine** (no `blender_assets` directory under `%APPDATA%`, no
`essentials` asset library on disk).

Therefore the brief's "most likely locally-available option" is **not**
available, and the Blender-bundled-asset license question (§2.5) is
moot for base meshes — though the bundled `datafiles/assets/LICENSE` *is*
CC0 and is recorded for completeness.

---

## 2. License verification, per asset, from primary sources

### 2.1 C1 — the MakeHuman `hm08` basemesh: **CC0 1.0 Universal — VERIFIED**

**Primary source A — the header of the actual file on disk.**
`C:\Users\orcha\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\mpfb\data\3dobjs\base.obj`, lines 1–16:

```
# This is a mesh file for MakeHuman
#
# This asset was explicitly released as CC0 in september 2020. The license
# text for CC0 can be found in the root of this repository.
#
# The copyright holders at the point of the release to CC0 were:
#
# Copyright (C) 2020 Data Collection AB, https://www.datacollection.se
# Copyright (C) 2020 Joel Palmius
# Copyright (C) 2020 Jonas Hauquier
#
# The primary legal contact for MakeHuman is Data Collection AB.
#
# For more information, see homepage at http://www.makehumancommunity.org
#
# basemesh hm08
```

**Primary source B — the upstream project's root `LICENSE.md`.**
`https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md`, section C:

> ### C. The license for the bundled assets
>
> The assets are defined as any data contributing to the output from MPFB.
> This includes:
>
> * **The base mesh and proxies**
> * Targets and modifiers
> * Textures
> * Clothes (any MHCLO-based asset)
> * Rigs, poses and expressions
> * JSON data with mesh information
>
> These assets have been released under **CC0 1.0 Universal**. In summary this means
> that to the fullest extent possible, it is the intention of the MakeHuman
> team that anyone can do whatever they want with it.
>
> For the full text of the legal statement regarding the assets, see
> [LICENSE.ASSETS.md](LICENSE.ASSETS.md)

**Primary source C — the full legal text.**
`https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.ASSETS.md` is the
verbatim **Creative Commons CC0 1.0 Universal** legal code (Waiver +
Public License Fallback + Limitations and Disclaimers).

**Primary source D — the file is the upstream file.** The upstream raw file
`https://raw.githubusercontent.com/makehumancommunity/mpfb2/master/src/mpfb/data/3dobjs/base.obj`
has a byte-identical header, including the same `basemesh hm08` marker.
Local file hash: `sha256 = 8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c`.

**Conclusion for C1.** Identifier: **CC0 1.0 Universal**.
Attribution requirement: **none** (CC0 waives copyright and related rights;
the MakeHuman team asks for courtesy credit only). Redistribution of the
file itself: **permitted**. Commercial use: **permitted**.

### 2.2 MPFB addon code — GPL-3.0-or-later (not a blocker)

`…\extensions\user_default\mpfb\blender_manifest.toml`:

```toml
license = [
  "SPDX:GPL-3.0-or-later",
]
```

and `https://extensions.blender.org/add-ons/mpfb/` → *License: GNU General
Public License v3.0 or later*.

This governs the **addon's Python code only**. The basemesh and all bundled
assets are CC0 per §2.1. The GPL is **not** a constraint on the asset, and
the addon is not vendored into this repository.

**Critically, the upstream project also states what happens to *output*:**

> ### D. Concerning the output from MPFB
>
> It is the opinion of the MakeHuman team that no output from MPFB
> contains any trace of program logic. … As the assets have been released
> under CC0, there is no limitation on what you can do with this combined output.
>
> To make it clear, the MakeHuman team makes no claim whatsoever over output
> such as:
> * Exports to files (FBX, OBJ, DAE, MHX2...)
> * Graphical data generated via scripting or plugins
> * Renderings
> * Screenshots
> * Saved model files
>
> We regard these things as your data, which is yours to handle as you see fit.

⇒ **A Character 001 model built on this basemesh is ours to ship.** This is the
licence chain that makes Option B commercially safe.

### 2.3 C2 — MakeHuman proxy meshes: **CC0 — VERIFIED**

`…\extensions\.user\user_default\mpfb\data\proxymeshes\male_generic\male_generic.proxy`,
lines 1–14 carry the **identical CC0 header** as `base.obj` (same 2020-09
release, same copyright holders). Upstream page
`https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html`
lists every proxy (`female1605`, `female_generic`, `male1591`, `male_generic`,
`male_muscle_13290`, `proxy741`, `female_muscle_13442`) with
**License = CC0, Author = makehuman_system, Source = asset repo**.

These are *not* base meshes (they are region/topology masks used to drive
deformation), but they are part of the same CC0 release.

### 2.4 C3/C4/C8 — ARKit face units, Meta visemes, MakeHuman system assets: **CC0 — VERIFIED**

The pack metadata shipped on this machine,
`…\extensions\.user\user_default\mpfb\data\packs\makehuman_system_assets.json`,
contains 94 entries. Measured over all 94:

```
licenses : [('CC0', 94)]
authors  : [('makehuman_system', 94)]
types    : skins 23, clothes 20, eyebrows 12, eyes 11, hair 10,
           proxymeshes 7, teeth 6, eyelashes 4, tongue 1
```

The ARKit pack metadata `…\data\packs\faceunits01.json` declares, per target:

```json
"browInnerUp": {
    "author": "Mika Suominen",
    "category": "Faceunit",
    "description": "Autogenerated ARKit faceunit",
    "license": "CC0",
    "type": "target"
}
```

(all 52 entries carry `"license": "CC0"`).

**Upstream project website — primary source.**
`https://static.makehumancommunity.org/assets/assetpacks.html`:

> ### Functional asset packs
>
> These are asset packs which are related to specific functionality rather than
> being collections of assets from the asset repository. **The assets are shared under CC0.**
>
> * Hair editor: Fur/hair styles for the hair editor
> * Visemes 01: Microsoft style visemes
> * **Visemes 02: Meta/Oculus style visemes**
> * **Faceunits 01: ARKit style face units**

and, in the same page, the MakeHuman system assets are listed under
*"System assets, shared under CC0"*.

⇒ **All inputs required by Option B are CC0 1.0, redistributable, commercially
usable, with no attribution obligation.**

### 2.5 C5 — Blender bundled assets: **CC0 — VERIFIED (but irrelevant: no human mesh)**

`C:\Program Files\Blender Foundation\Blender 4.5\4.5\datafiles\assets\LICENSE`
is the **verbatim Creative Commons CC0 1.0 Universal** legal code
(lines 1–121 read in full; `CC0 1.0 Universal` on line 3).

This license covers Blender's bundled **brushes** and **geometry-node** assets.
It does **not** cover a human base mesh, because this Blender build contains
none (§1.3). The brief's warning that "Blender's asset licenses have
historically been CC-BY" is **not applicable here** and is **not** what the
shipped file says for these assets — but since there is no Blender human mesh
on this machine, the point is moot. **No CC-BY Blender asset is used by this
plan.**

### 2.6 C6/C7 — the pre-existing MPFB exports

`ours-photoreal.glb` and `mpfb.glb` are **outputs** of MPFB (their generator
string is `Khronos glTF Blender I/O`, and their mesh/node names are MPFB's
export-copy convention). Per §2.2 (upstream `LICENSE.md` §D) MPFB output
carries no MakeHuman/owner claim.

Their `asset.copyright` field is `None` in the glTF JSON — i.e. no third-party
copyright notice is asserted in the file.

They are nevertheless **rejected as basemeshes** for C001:
* `ours-photoreal.glb` is the character **"Blue"** — a *young caucasian female* MPFB preset with copper-chestnut `short01` hair — i.e. **wrong identity and wrong gender** for Character 001 (an adult auburn-haired man), and it is **explicitly retired from the C001 critical path** by ADR decision 5.
* Both are **triangulated** GLB containers (glTF cannot store quads), so they no longer carry the quad topology that Option B exists to obtain.

### 2.7 License summary table

| Asset | Identifier | Primary source | Attribution required? | Redistributable? | Commercial use? |
|---|---|---|---|---|---|
| `base.obj` (hm08 basemesh) | **CC0 1.0** | file header + upstream `LICENSE.md` §C + `LICENSE.ASSETS.md` | No | **Yes** | **Yes** |
| MakeHuman proxies | **CC0 1.0** | `.proxy` header + upstream asset page | No | Yes | Yes |
| ARKit face units (52) | **CC0 1.0** | `faceunits01.json` + upstream assetpacks page | No | Yes | Yes |
| Meta visemes (15) | **CC0 1.0** | upstream assetpacks page | No | Yes | Yes |
| MakeHuman system assets (94) | **CC0 1.0** | `makehuman_system_assets.json` + upstream asset page | No | Yes | Yes |
| Blender bundled brushes/node assets | **CC0 1.0** | `datafiles/assets/LICENSE` | No | Yes | Yes |
| MPFB addon code | GPL-3.0-or-later | `blender_manifest.toml` | n/a (not vendored) | n/a | n/a |
| MPFB **output** | unrestricted | upstream `LICENSE.md` §D | No | **Yes** | **Yes** |

**No asset in this plan is UNVERIFIED.** The only UNVERIFIED items in the
broader environment are (a) `ours-photoreal.glb`'s *authoring pipeline* beyond
MPFB (its skin/hair textures are CC0 MakeHuman system assets, so the asset
chain is verified) and (b) the *content* of `C:\PROJECT\Livynth-artifacts\`
GLBs produced by other agents — those are out of scope for this task and are
not used here.

---

## 3. Topology suitability — measured, not asserted

All numbers below come from the tools in this branch, run against the actual
file. Commands are reproducible (§5).

### 3.1 Headline topology of the recommended basemesh (`base.obj`)

```
sha256            : 8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c
size_bytes        : 1749303
vertices          : 19158
texture_vertices  : 21334
faces             : 18486
edges             : 37364
vertex groups     : 139  (OBJ 'g' groups)  /  152 vertex groups after MPFB import
polygon size histogram : {4: 18486}
quads=18486  tris=0  ngons(>4)=0  quad_dominance=100.00%
edges: total=37364  boundary(open)=784  manifold(2-face)=36580  non-manifold(>2)=0
euler V-E+F       : 280
connected shells  : 154  (largest holds 72.37% of faces)
body-group shells : 1     (sizes [13378])          <- the body+head is ONE shell
loose vertices    : 0
UV layer          : True  faces_with_uv=18486  invalid_uv_faces=0  uv_area=0.6379
uv bounds         : [[0.009208, 0.009607], [0.993515, 0.992225]]
mirror symmetry   : 100.000 % of vertices have an exact mirror partner at X=0
```

### 3.2 Answers to the specific questions asked

**Is it quad-dominant?** — **Yes, exactly 100.00 %.** 18 486 of 18 486 faces
are quads; zero triangles, zero n-gons. Not "mostly quads" — all quads.

**Does the head form a single connected shell?** — **Yes.** The `body` OBJ
group (13 378 faces) is **exactly one connected component**. The other 153
shells are helper geometry (eyes 2×70, eyelashes 4×44/48, teeth 2×48, tongue
224, tights 2 650, skirt 684, hair helper 198, genital 182) and 122 joint
cubes. The head is *continuous with the neck* inside the single body shell,
i.e. there is no separate "head object" that would need boolean/weld surgery
before retopology.

> Measured head continuity: faces above `joint-neck` (y = 5.8902) = 5 159, of
> which the largest connected component is **4 256** — the remainder are the
> helper shells listed above.

**Does it have a clean edge-loop structure for face-region deformation?**
Region probes are anchored to the **measured joint-cube centroids** shipped
in the file (`joint-l-eye`, `joint-mouth`, `joint-jaw`, `joint-neck`,
`joint-head-2`), not to hand-guessed coordinates:

```
face-region census:
   eye_socket   verts=2018  faces=1854  quads=1854  quad%=100.0
   lips         verts=179   faces=98    quads=98    quad%=100.0
   jaw          verts=1402  faces=1238  quads=1238  quad%=100.0
   neck         verts=394   faces=272   quads=272   quad%=100.0
   brow         verts=97    faces=64    quads=64    quad%=100.0
   forehead     verts=106   faces=54    quads=54    quad%=100.0
   nose         verts=160   faces=82    quads=82    quad%=100.0
```

Global, unbiased regularity measure over the whole body shell:

```
body-group valence histogram : {3: 164, 4: 13060, 5: 156}
regular quad valence-4 vertices : 97.608 %
```

⇒ 97.6 % of body vertices sit in a regular quad grid (valence 4); the 320
remaining are designed poles (164 tri-poles, 156 penta-poles) plus boundary
vertices. That is a *normal, healthy* quad base — not a "needs retopo"
mesh. **Caveat, stated honestly:** the per-region "poles" figure in the JSON
report is biased upward because an axis-aligned probe box cuts the surface;
the unbiased number to use is the 97.608 % body-wide figure above.

**Does it have UVs usable for baking?** — **Yes.**
* One UV layer, `UVMap`, 21 334 texture vertices, **all 18 486 faces carry
  valid texture indices**, 0 invalid.
* UV bounds span `[0.0092, 0.9935] × [0.0096, 0.9922]` — essentially the full
  `[0,1]²` square.
* Rasterised overlap test at 512²: 83 621 cells covered (31.9 % of the
  square), **0 overlapping cells** ⇒ the layout is **non-overlapping**, so a
  bake will not smear between unrelated regions.
* This is the MakeHuman UV layout, which is region-aware (separate islands for
  face / lips / eyelids / scalp), so a 2048² or 4096² bake has usable texel
  density in the face.

**Does it have an armature / weight groups, or is it a raw sculpt-only base?**
It is a **raw sculpt base** in the file itself, but the machine ships
everything needed to rig it:
* 139 OBJ vertex groups; **152 vertex groups** after MPFB import
  (includes `Head`, `Neck`, `Jaw`, `LeftEye`, `RightEye`,
  `LeftOrbicularisTop`, `LeftOrbicularisBottom`, `RightOrbicularisTop`,
  `RightOrbicularisBottom`, and the full 122-joint skeleton set as `joint-*`
  cubes).
* `…\mpfb\data\rigs\standard\rig.default.json` (126 355 B) and
  `weights.default.json` (5 034 981 B) — a 67-joint facial rig with weights.
* `…\mpfb\data\rigs\rigify\rig.human.json` + `weights.human_toes.json` — a
  Rigify variant.

**Does it carry morph targets / an ARKit rig?** — The base OBJ does not, but
the machine ships the **morph-target library**, already installed and already
proven to load (§4).

### 3.3 Comparison with the alternatives

| Candidate | Quad % | Shells | UV | Verdict |
|---|---|---|---|---|
| **C1 `base.obj`** | **100.00 %** | body = 1 shell | yes, non-overlapping | **RECOMMENDED** |
| C2 `male_generic.obj` (proxy) | 100.00 % | 1 | yes | Rejected: a *region mask*, not a base mesh — it drives deformation of C1, it is not a body |
| C6 `ours-photoreal.glb` | triangulated on export (26 756 tris for the body) | 9 | yes | Rejected: wrong identity/gender, retired by ADR decision 5, no quads |
| C7 `mpfb.glb` | triangulated (21 380 tris) | 13 | yes | Rejected: lives in `%TEMP%` (fragile), is a *female* default, not Character 001; also no quads |
| C5 Blender bundled | n/a | n/a | n/a | Rejected: **no human mesh exists in this Blender build** |

---

## 4. Sparse proof — the basemesh is operationally usable, end to end

A plan is not evidence. This was actually executed.

### 4.1 Headless Blender import of the raw basemesh

```
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background \
    --factory-startup --python tools/blender_audit_basemesh.py -- <base.obj> --json out.json
```

Result (`import_ok: true`, 49.77 ms):

```json
{ "blender_version": "4.5.10 LTS",
  "vertices": 19158, "edges": 37364, "polygons": 18486,
  "polygon_size_histogram": { "4": 18486 }, "quad_dominance_pct": 100.0,
  "uv_layers": ["UVMap"], "has_uv_layer": true,
  "loose_vertices": 0, "material_slots": [], "modifiers": [],
  "bmesh_edges": { "non_manifold": 784, "boundary": 784, "wire": 0 } }
```

Note: Blender's `non_manifold` count (784) is exactly its `boundary` count —
there is **no** edge shared by 3+ faces. The 784 boundary edges are the open
limb/torso rims and helper shells, inherent to the MakeHuman basemesh.

### 4.2 Headless MPFB build — full character + ARKit morph rig

```
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background \
    --python tools/mpfb_headless_probe.py -- \
    --out output/c001_geo04/probe.glb --json output/c001_geo04/probe.json
```

**Every step reported `ok`; `errors: []`; 37.52 s wall clock.**

```
steps:
  create_human                    = ok
  create_character_copy           = ok
  bake_targets                    = ok
  bake_modifiers_remove_helpers   = ok
  load_face_targets               = ok
  interpolate_targets             = ok
  export_glb                      = ok

basemesh_raw  : verts 19158  polys 18486  poly_hist {4:18486}  quad% 100.0
                uv_layers ["UVMap"]  vertex_groups 152
                shape_keys ["Basis","$md-$ca-$ma-$yn","$md-universal-$ma-$yn-$av$mu-$av$wg"]
basemesh_baked: verts 13380  polys 13378  poly_hist {4:13378}  quad% 100.0
                uv_layers ["UVMap"]  vertex_groups 152
morph_target_count : 67
required_arkit_all_present : true
```

Per-target measured displacement on the baked base (max Δ in Blender units,
scale 0.1 ⇒ 1 BU = 10 cm):

| target | vertices moved | max displacement (BU) | ≈ mm |
|---|---|---|---|
| `eyeBlinkLeft` | 718 | 0.012613 | 1.26 |
| `eyeBlinkRight` | 718 | 0.012613 | 1.26 |
| `browInnerUp` | 615 | 0.005200 | 0.52 |
| `mouthSmileLeft` | 1 640 | 0.018682 | 1.87 |
| `mouthFunnel` | 1 717 | 0.010933 | 1.09 |
| `mouthPucker` | 1 729 | 0.008709 | 0.87 |
| `jawOpen` | 2 249 | 0.038738 | 3.87 |
| `viseme_aa` | 2 141 | 0.018156 | 1.82 |
| `viseme_O` | 1 950 | 0.006999 | 0.70 |

All 10 ADR-required ARKit names present: `browInnerUp`, `browOuterUpLeft`,
`browOuterUpRight`, `mouthSmileLeft`, `mouthSmileRight`, `mouthFunnel`,
`mouthPucker`, `eyeBlinkLeft`, `eyeBlinkRight`, `jawOpen` — **`true` for each.**

Exported GLB: 15 090 388 bytes, `base.001` = 14 517 verts / 26 756 tris /
67 morph targets / UV present / 0 non-manifold edges.

> **Interpretation (important).** glTF stores triangles only, so a GLB can
> never *prove* quad topology. The authoritative quad measurement is the OBJ
> measurement in §3.1 (100.00 %). The "even vertex valence" metric in
> `tools/measure_glb_topology.py` is **confounded by glTF's vertex duplication
> at UV/normal seams** and is therefore reported as diagnostic only, **not**
> used as evidence of quad origin.

### 4.3 Why this is the decisive proof for Option B

The ADR's real blocker for Option B was never "is there a quad mesh" — it was
"can the ARKit morph rig survive retopology". §4.2 answers it:

> **MakeHuman/ARKit `.target` files are sparse per-vertex displacement maps
> over the basemesh's own vertex indexing.** The shipped
> `targets/faceunits/browInnerUp.target` literally begins:
> ```
> 1 .001 .001 0
> 3 .001 .001 .001
> 5 .002 .002 .001
> 56 .001 .001 .001
> …
> ```
> i.e. `<basemeshVertexIndex> <dx> <dy> <dz>`.

Consequence: the morph targets are **defined on the quad basemesh itself**.
Retopology onto that basemesh therefore does **not** require a dense-to-base
transfer — it requires only that the neutral basemesh is *deformed* (not
re-meshed) to Character 001, and the targets are then re-evaluated against the
deformed neutral. See `docs/C001_GEO04_RETOPOLOGY_PATH.md` §3.

---

## 5. Reproducing every number in this document

From the worktree root:

```powershell
$w = 'C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-topology'
$mpfb = "$env:APPDATA\Blender Foundation\Blender\4.5\extensions\user_default\mpfb"
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'

# (A1) raw topology + region census + UV overlap
python tools\measure_basemesh.py "$mpfb\data\3dobjs\base.obj" --json output\c001_geo04\base_obj_topology.json

# (A2) headless Blender import audit
& $blender --background --factory-startup --python tools\blender_audit_basemesh.py -- `
    "$mpfb\data\3dobjs\base.obj" --json output\c001_geo04\base_obj_blender_audit.json

# (A3) headless MPFB character build + ARKit morph rig  (the sparse proof)
& $blender --background --python tools\mpfb_headless_probe.py -- `
    --out output\c001_geo04\probe.glb --json output\c001_geo04\probe.json

# (A4) measure the exported GLB
python tools\measure_glb_topology.py output\c001_geo04\probe.glb --json output\c001_geo04\probe_glb_topology.json

# (A5) machine-wide inventory
cmd /c "dir C:\*.obj /s /b 2>nul"
cmd /c "dir C:\*.glb /s /b 2>nul"
cmd /c "dir C:\*.blend /s /b 2>nul"
Get-ChildItem $mpfb -Recurse -File -Include '*LICENSE*','*COPYING*','*README*'
```

Everything under `output/` is git-ignored; **no binary is committed.**

---

## 6. Recommendation

**RECOMMEND: `base.obj` — the MakeHuman `hm08` basemesh bundled with the
installed MPFB 2.0.18 extension.**

Reasons, each grounded in a measurement or a primary source above:

1. **License:** CC0 1.0 Universal, verified from the file's own header, the
   upstream repo's `LICENSE.md` §C and `LICENSE.ASSETS.md`, and the upstream
   project website. Redistribution and commercial use are unrestricted, and the
   upstream project explicitly places MPFB *output* outside any MakeHuman
   claim. → **ADR Decision 1's condition is satisfied.**
2. **Topology:** 100.00 % quads (18 486/18 486), 0 tris, 0 ngons, 0 edges with
   3+ faces, 0 loose vertices, 97.608 % regular quad valence-4 body vertices.
3. **Single shell:** the body+head is exactly one connected component — the
   prerequisite for a clean retopology target.
4. **UV:** one layer, full-square, **zero overlap** ⇒ bake-ready.
5. **Deformation readiness:** 152 vertex groups, a 67-joint rig with weights,
   `Jaw`/`Neck`/`Head`/`Eye`/`Orbicularis` controls, and 67 morph targets
   **already proven to load and displace** in a headless run on this machine.
6. **Availability:** already installed; **no download, no account, no paid
   service, no approval needed** to begin.

**Rejected alternatives and why:**

* **Blender bundled `rig_human` / Essentials human base meshes** — *do not
  exist on this machine* (exhaustively searched). The Blender asset library
  contains brushes and geometry nodes only. Even if downloaded, Blender's
  Essentials human base meshes ship without MakeHuman's 67-target facial
  system and without ARKit face units, so they would **not** satisfy the ADR's
  6-morph-target requirement without an extra asset pack anyway.
* **`ours-photoreal.glb` (the "V32" avatar)** — wrong identity (it is the
  female preset "Blue"), wrong gender, **explicitly retired from the C001
  critical path** by ADR decision 5, and triangulated (no quads).
* **`mpfb.glb` in `%TEMP%`** — same identity problem, lives in a temp
  directory that Windows may purge, and triangulated.
* **MakeHuman proxy meshes (`male_generic.obj` etc.)** — 100 % quads and CC0,
  but they are *region masks*, not a body; they cannot be a retopology target.
* **Any external/vendor basemesh (e.g. a purchased head bundle)** — would
  introduce an unverified licence into the critical path and is explicitly
  excluded by the ADR.

**Nothing needs owner approval for the acquisition step, because nothing needs
to be acquired.** The only approvals this plan still needs are the ones the
ADR already requires downstream (blinding protocol, blind review) and the
ordinary "do not upload the user's portrait to a third-party service" rule —
which this plan never does: all fitting happens locally in Blender.

---

## 7. What could NOT be verified, and why

| Item | Status | Reason |
|---|---|---|
| Quad-ness of any **GLB** on this machine | **UNVERIFIED by construction** | glTF has no polygon-class concept; it stores triangles. Only the OBJ measurement is authoritative. The `even_valence` metric is confounded by glTF vertex duplication and is reported as diagnostic only. |
| Whether MPFB's `base.obj` is **byte-identical** to the upstream `master` file | **NOT FULLY VERIFIED** | The upstream raw file was fetched and its header + `basemesh hm08` marker matched byte-for-byte, but a full-file SHA comparison was not performed (the upstream file is fetched as text through the tool, not as bytes). The local file's own CC0 header is independent evidence and does not depend on this. |
| `C:\PROJECT\Livynth-artifacts\*.glb` (other agents' candidates) | **OUT OF SCOPE / UNVERIFIED** | Produced by other specialists under other briefs; not used by this plan and not licence-audited here. |
| The **exact skin/hair texture licences** embedded in `ours-photoreal.glb` | **PARTIAL** | Its skin is the CC0 MakeHuman system skin `young_caucasian_female`; its hair texture is a locally tinted copy of the CC0 `short01` diffuse (tinting is a derived work of a CC0 asset). The asset-level chain is CC0, but the file is retired from the C001 path regardless, so this was not pursued further. |
| Blender "Essentials" human base mesh licence | **NOT APPLICABLE** | Not present on this machine, so no such asset is used. (Had it been present, the correct action would have been to read *its* shipped LICENSE file, not to rely on recollection.) |
| FLAME / FLAME 2023 Open | **NOT TOUCHED** | Explicitly out of scope for this agent; owned by another specialist. Not downloaded, not imported, not evaluated. |

---

## 8. Provenance block

* **Source commit (branch base):** `b0235c1` — *docs(c001): record phase-3 FAIL, seven owner decisions and geometry-first repair gate*
* **Branch:** `experiment/c001-geo04-topology`
* **Worktree:** `C:\Users\orcha\.local\share\opencode\worktree\3e7201\livynth-c001-geo04-topology`
* **Environment:** Windows, Python 3.14.7, numpy 2.5.3, Blender 4.5.10 LTS
  (`6dc0b208d1b5`, build 2026-05-19), MPFB extension 2.0.18 (extensions platform)
* **Input hashes:**
  * `base.obj` → `sha256 8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c` (1 749 303 B)
  * `makehuman_system_assets.json` → 94/94 entries `license: CC0`
  * `faceunits01.json` → 52/52 entries `license: CC0`
* **Artifacts produced:** `output/c001_geo04/{base_obj_topology.json, base_obj_blender_audit.json, probe.json, probe.glb, probe_glb_topology.json}` — **all git-ignored, no binaries committed**
* **Execution status:** all commands above executed successfully; no UNVERIFIED result is presented as verified.
