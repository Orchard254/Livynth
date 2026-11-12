# IDENTITY-008 independent image review → IDENTITY-009 appearance decision

**Date:** 2026-11-12. **Evidence:** owner-uploaded 20261112_060832_140286.zip
(5,161,863 bytes), containing all 20 400×600 RGBA PNG renders, 2 per-character
render reports, pose_review.json, index.html, and SHA256 bundle_manifest.json.

## Data integrity

All 24 file entries in the manifest independently matched their actual ZIP
bytes (SHA256 and size). There were no missing or corrupt images.

Both GLB source SHA values are different:
- A: 275fa696bea980be8efcfe870868e1306e3235c3c2f195d256d73efaecf594ca
- B: 5182ffe4ba88c13ee46ef4b89bab074e997f932fb2752415c7bbecb9580f4ffa

Each character has front neutral, blink, jaw-open, AA-vowel, PP-lip closure,
smile, pucker, and three-quarter neutral, blink, jaw-open frames (10 per human).
All 16 non-neutral poses have measurable pixel changes. The original
aggregate status is CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW.

## Independent visual verdict

| Subsystem | Observed result | Gate |
|---|---|---|
| Reusable facial controls | Both neutral heads visibly change to all requested poses | BASIC STATIC POSE PASS |
| Blink | Both eyelids visibly meet in front and three-quarter views | BASIC STATIC POSE PASS; closing animation untested |
| Jaw and vowel | Both mouths open; lip and chin surfaces remain attached | BASIC STATIC POSE PASS |
| PP, pucker and smile | Distinct visible lip shapes on both heads | BASIC STATIC POSE PASS |
| A/B identity separation | Jaw/chin silhouettes are different, although faces remain similar | SHAPE DIFFERENCE PASS, NOT RECOGNIZABLE IDENTITY |
| Eyeballs/iris | Opening appears patterned with no finished eyeball, pupil or iris | PRESENTATION FAIL |
| Mouth interior | Exposes a stippled/grainy, flat-looking inner surface; no convincing teeth, tongue or oral cavity | PRESENTATION FAIL |
| Hair/skin | Both bald, uniform diagnostic clay | PRESENTATION FAIL |
| Clothing | Torso still appears clay-colored, not a clearly separated navy shirt | PRESENTATION FAIL |
| Five-angle source likeness | Not evaluated by these manually configured demonstration identities | NOT ACCEPTED (Character 001 Phase-3 remains FAIL) |
| Motion timing and lip-sync | Still images only; no sequence-level validation | NOT TESTED |

The current eye and mouth defects cannot be fixed by more lip-sync timing or
by increasing the number of morph targets. The geometry/morph control interface
is sufficiently functional to move to attached bodypart and appearance assets.

## Engineering decision

**Use MPFB's own fitted bodypart assets**, not guessed procedural eyeballs
or a painted oral opening. MPFB natively supports mhclo eyes, eyelashes,
eyebrows, teeth, tongue, hair and clothes through HumanService.add_mhclo_asset.
Documented asset folders and library discovery are available through
AssetService.get_asset_roots. The official system-asset pack typically supplies
eyes and oral assets, but we do NOT know which packs the owner has installed.

IDENTITY-009 therefore adds a *read-only, zero-model-export inventory*:
  python tools/probe_mpfb_assets.py

A Windows Blender report must identify at least eyes, teeth and tongue before
a fitted-anatomy prototype proceeds. If unavailable, report missing categories
without claiming assets attached or automatically installing anything.
Installed asset licensing must be checked before commercial distribution.

Do NOT change the working 163-joint / 67-morph rig at this stage. After the
inventory, prototype assets on both characters and re-test neutral/blink,
AA/PP and jaw expression renders for occlusion and rig compatibility.

**This is not complete photo-to-3D.** Image-to-identity camera/correspondence
and five-view blind reconstruction gates remain independent and unfinished.

## Official technical references
- https://static.makehumancommunity.org/mpfb/docs/characters/bodyparts.html
- https://static.makehumancommunity.org/mpfb/docs/getting_started.html
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/humanservice.md
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/assetservice.md
