# LIVYNTH Humans — Character 001: Identity Capture Specification v1.0

**Status:** prompts approved for generation; actual high-resolution images not yet generated/accepted.
**Goal:** acquire six separate, identity-consistent photographic reference images useful for building an original 3D face. These are reference photographs, **not** automatically geometry, UV textures, or a rig.

## Identity decision

Use the **existing Character 001 identity** from our Phase 1 concept sheets: an original adult man, approximately 25–30 in appearance, light/fair skin with natural freckles and color variation, blue-gray eyes, short textured/wavy auburn/reddish-brown hair, clean shaven, oval face with modest angular jaw, straight medium-width nose, medium natural lips, natural eyebrows, navy crew-neck shirt.

**Do not switch to the young-woman brief** from a later planning message: it conflicted with the previously generated Character 001 reference pack. A different identity can become Character 002.

## Technical capture standard

- Generate **one image per file**, not a contact sheet/collage.
- Render at native >=2048 pixels on the long side if the generator supports it; prefer 3:4 portrait for all face views. Do **not** use upscaling to claim real detail.
- Use image-to-image identity reference conditioning for all derivative views, using the **approved 01_front_master.png** as the identity anchor. Repeating a textual prompt or seed alone does not prove identity stability.
- Camera at eye height with near-orthographic/long-lens (about 85–105 mm full-frame-equivalent) perspective. Fix the lens and lighting between shots. Avoid phone selfie/perspective distortion.
- Neutral slate-gray backdrop, soft symmetrical cross-light, no dramatic shadow, no colored light, no bloom, no sharpening halos, no strong specular glints or depth-of-field blur.
- Hair kept above and away from face and ears; clothing consistent and plain navy; face unretouched with pores, asymmetry and natural pigment. No jewelry, glasses, logos, makeup, text, captions or watermark.
- Anatomical left/right are **the character's left/right**, not the viewer's.
- Eyes look along the head's forward axis: turning head is a camera-view change, not a separate wandering eye gaze.

## Global identity prompt

> A single original adult man aged approximately 25–30, light fair skin with faint freckles and visible natural pores, oval face with a naturally defined jaw, straight medium-width nose, medium natural lips with slightly fuller lower lip, blue-gray eyes with realistic irises and sclera, natural medium-thickness eyebrows, short slightly wavy auburn/reddish-brown hair with a clear hairline and ears, clean shaven, plain navy crew-neck shirt. Neutral relaxed expression, mouth softly closed, eyebrows at rest, both eyes open and looking along the head's forward axis, anatomically plausible human proportions. Unretouched technical studio identity photograph, diffuse even cross-lighting, neutral slate gray background, eye-level near-orthographic long-lens camera (85–105 mm full-frame equivalent), realistic skin and eye materials, high native resolution, zero beauty filtering. No text, collage, jewelry, glasses, logos, extreme shadows or stylization.

### Shot prompts (append exactly one of these to the global prompt)

| Filename | Camera direction |
| --- | --- |
| `01_front_master.png` | Camera directly centered at 0°, front-facing neutral head, from hair crown through upper chest; ears visible with identical scale and neutral expression. This image becomes the identity anchor after QA. |
| `02_subject_left_45.png` | Camera 45° around **subject's left** side; do not turn or deform the face independently. Keep one and the same person, skull proportions, eye spacing, nose bridge, ear geometry, hairline, shirt and illumination. |
| `03_subject_right_45.png` | Camera 45° around **subject's right** side; preserve the identity, proportions and camera distance exactly. |
| `04_subject_left_90.png` | Camera at 90° true profile on **subject's anatomical left**; nasal bridge, lips, forehead, ear, jaw and chin silhouette clearly visible. Do not generate a three-quarter view. |
| `05_subject_right_90.png` | Camera at 90° true profile on **subject's anatomical right**; same head dimensions as the left view; avoid mirror-flipping the prior image or silently changing anatomy. |
| `06_front_closeup.png` | Exact approved front identity at 0°, closely framed forehead-to-chin; both eyelids, brows, lashes, pores, nose, philtrum and lips sharp and in focus, without changing expression or improving/beautifying the face. |

**For images 02–06:** attach the approved full-resolution `01_front_master.png` as a reference/identity-conditioning input, and explicitly say the model must depict the *exact same adult*, changing only the camera position or crop.

## Generation order and gates

1. Generate only `01_front_master.png` first. Submit it for visual QA.
2. Reject front master if eyes are asymmetric from generator artifacts, ears are obscured, face is airbrushed or distorted, skin is waxy, or there is insufficient native detail. Regenerate rather than repair a bad identity anchor.
3. Lock approved front master. Then generate views `02`–`05` with identity conditioning; compare actual geometry (interocular distance, ear location, nasal projection, brow line, jaw width, hairline), not just a subjective sense that the faces are similar.
4. Generate `06_front_closeup.png` from the approved master; check fine structures without changing the identity.
5. Keep source-generation metadata (model/version, seed, reference ID, native dimensions, prompt, variation strength, date) when available.
6. **Only after consistent views pass:** reconstruct or adapt mesh; UV unwrap; generate true mesh-aligned albedo/detail maps, eyes/hair geometry, and expression targets. A single image or inconsistent set cannot promise physically accurate 3D.

## Review labels

- `ACCEPT`: useful primary geometric reference.
- `REFERENCE_ONLY`: visually useful, but not dimensionally trustworthy or texture-ready.
- `REGENERATE`: inconsistent identity, head angle, lighting, resolution or anatomically implausible feature.

## Repository destination once approved

`assets/characters/character_001/identity_capture_v1/`

Generated image bytes are added locally by the project owner; this document contains prompts and validation criteria only. Keep concept collages in a separate folder and do not confuse them with approved full-resolution captures.
