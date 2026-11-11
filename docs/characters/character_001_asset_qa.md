# Character 001 — Image Asset QA (2026-11-11)

**Verdict:** Proceed to first geometry-fitting prototype **C001-GEO-01**. Reference-only images are not proof of a camera-calibrated or exact 3D identity.

## Canonical asset selection

The uploaded `LIVYNTH_Character_001_all_images(1).zip` holds 16 usable originals in the nested `LIVYNTH_Character_001_all_images/` folder, plus duplicate root-level images. Four root-level copies (`09_left_ear`, `11_eyes_closeup`, `13_skin_macro`, `15_hair_closeup`) are tiny thumbnail versions (~352–356 px). **Use only the nested originals.**

Earlier accepted `01_subject_front.png`, `02_subject_left_45.png`, and `03_subject_right_45.png` are pixel-identical to the previously shared portrait files, despite changed PNG byte encoding.

## Review table

| Image | Review | Role |
| --- | --- | --- |
| 00_original_portrait | ARCHIVE | Historical portrait; not the master |
| 01_subject_front | ACCEPT | **Canonical frontal identity**, 1086×1448 |
| 02_subject_left_45 | ACCEPT | Left three-quarter shape, 1086×1448 |
| 03_subject_right_45 | ACCEPT | Right three-quarter shape, 1086×1448 |
| 04_left_profile | ACCEPT | Left silhouette and nose/ear, 1086×1448 |
| 05_right_profile | ACCEPT | Right silhouette and nose/ear, 1086×1448 |
| 06_back_head | ACCEPT | Rear hair volume/neck, 1086×1448 |
| 07_top_head | REFERENCE ONLY | Head is bowed forward; **not true overhead geometry** |
| 08_front_closeup | REFERENCE ONLY | A bust portrait, not a tight face close-up; some identity drift |
| 09_left_ear | ACCEPT | Detailed ear anatomy; nested full-resolution version |
| 10_right_ear | ACCEPT | Detailed ear anatomy |
| 11_eyes_closeup | ACCEPT | Eyes/lashes/eyelids; nested full-resolution version |
| 12_iris_macro | REFERENCE ONLY | One eye with visible iris; illustrative, not measured iris texture |
| 13_skin_macro | REFERENCE ONLY | Angled partial face; not color-neutral albedo |
| 14_lips_closeup | ACCEPT | Lip shape/material appearance, not UV texture |
| 15_hair_closeup | REFERENCE ONLY | Hairline and curls, not true strand macro |

10 ACCEPT, 5 REFERENCE ONLY, 1 ARCHIVE.

## Constraints and cautions

- Generated independently with unknown/uncalibrated camera parameters; appearance consistency is encouraging but **cannot prove the same 3D skull**.
- Do **not** directly project these shaded photographs as final UV-ready albedo, normal, roughness or hair textures.
- The top and front-closeup variants are **nonblocking** for initial mesh fitting. Do not ask for more images before the geometry checkpoint.

## C001-GEO-01 acceptance gate

1. Obtain an animation-friendly neutral base head mesh with stable quad topology.
2. Fit head width/height, nose projection, chin, jaw and ear placement to `01` plus `04`/`05`; use `02`/`03` as soft three-quarter cross-checks.
3. Render comparison images of the same mesh from front, two three-quarter and both profile viewpoints on a neutral gray background.
4. Document mismatches and iterate anatomy **before** high-detail materials, complex hair and expression targets.
5. Only after identity/geometry passes, develop UV-matched skin/eye materials and facial-rig morphs.

**Asset location (local, not committed):** `assets/characters/character_001/identity_capture_v1/`. Store original high-resolution images plus a SHA-256 manifest. The clean archive and contact sheet from the QA session are supplied separately to the user.
