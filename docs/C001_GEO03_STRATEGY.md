# LIVYNTH C001-GEO-03 — development strategy (2026-11-11)

**Directive (user, 2026-11-11):** Stop treating the MakeHuman GLB as the critical path.
Build Character 001 directly from the 15 reference images in
`assets/characters/character_001/identity_capture_v1/` using image-to-3D methods.
Keep the GLB adaptation (`geo/morph_fit.py`) as a **documented fallback only**.

**Directive addendum (2026-11-11):** LIVYNTH's goal is a modular, automated digital-human creation and AI video-production engine for many unique characters — not a single Character 001. C001-GEO-03 is the **first factory run**. A parallel track develops the lightweight Character Factory specification (`docs/CHARACTER_FACTORY_SPEC.md`) with the architecture and integration specialists. No disruptive rewrite; successful C001-GEO-03 components must become reusable by future characters (Character 002 next). No merges to `main` without approval.

## Verified asset inventory (2026-11-11)

- `identity_capture_v1/` — 15 PNGs, all ≈1086×1448 (closeups larger), RGB, ~2.1–3.0 MB each:
  front; left/right 45°; left/right profile; back; top; front closeup; both ears; eyes
  closeup; iris macro; skin macro; lips closeup; hair closeup.
- No source GLB exists on this machine (`ours-photoreal.glb`, `our-avatar-v32-clean-blink.glb` absent).
  GEO-02 code remains in-repo as the fallback path, not runnable until a source GLB is supplied.
- `assets/voice.wav` exists (617,322 bytes) — usable for phoneme-timing work.
- Blender 4.5 at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` (not on PATH).
- No CUDA; 16 GB RAM; single CPU; Radeon 530 + Intel UHD.
- Python 3.14.7 — `torch 2.15.0`, `opencv-python(-headless) 5.0.0.93`, `mediapipe 1.2.2`,
  `open3d 0.20.0`, `scikit-image 0.26.0` are all listed by pip for this interpreter.
  None of opencv/mediapipe/torch are installed yet.
- Local checks: `python tools/local_check.py` → 21/21 PASS. `geo/tests` → 21/21 PASS (after
  installing `trimesh`). Baseline is green; keep it green.

## Strategy (image-first)

**Phase 0 — Asset validation (no reconstruction before this passes)**
- asset-curator: validate all 15 images (dimensions, hashes, provenance manifest).
- multiview-auditor: cross-view consistency audit (identity, pose, lighting, hairline, ear shape).
  AI-generated "photographs" are not calibrated scans; multi-view consistency decides whether
  SfM/NEUS-style fusion is viable or only silhouette-constrained fitting is.

**Phase 1 — Calibration & landmarks (feeds every later gate)**
- camera-calibrator: common projection/calibration format; azimuths known from shot definitions
  (0/±45/±90/back/top); weak-perspective long-lens assumption (85–105 mm equivalent); subject
  scale from an eye-separation prior, labeled as an assumption. Synthetic-tested; real-image
  values labeled measured/assumed.
- landmark-engineer: canonical landmark schema; MediaPipe FaceMesh detection on the 15 images if
  it installs on Python 3.14; legacy `geo/character001_landmarks.json` migration (labeled legacy).

**Phase 2 — Independent reconstruction candidates (parallel, blind to each other)**
- Lane A — neural-reconstruction: attempt TripoSR (CPU) on the approved front reference;
  weights download permitted if license verified MIT-compatible; record exact commit, license,
  command, exit code, output path. Any failure → blocker report, never a fabricated mesh.
- Lane B — parametric-reconstruction: classical CPU candidate — multi-view visual hull from the
  segmented silhouettes (front/±45/±90/back/top) + photometric texture projection; extends the
  GEO-01 silhouette theory with multiple calibrated views; watertight GLB out. This lane is
  deterministic and local.
- Lane C — parametric face-model fitting (FLAME/MICA/DECA): evaluate only; FLAME is
  registration-gated — **do not register or accept terms without user approval**; report blocker.
- Lane D — external-api-reconstruction: paid/hosted APIs (Tripo, Kaedim, Meshcapade, Ready Player
  Me, Rodin) — research and pricing only; **no submission of any reference image without explicit
  user approval**.
- reconstruction-research: independent methods + licensing + feasibility report (read-only).

**Phase 3 — Blind validation gate (no "success" without this)**
- independent-regression-qa: blind scorecard (silhouette IoU, landmark error px, GLB invariants,
  blink/jaw checks, visual rubric). Candidates judged without backend labels.
- blender-render-specialist: five standardized angles per candidate (front/±45/profile/back),
  CPU headless Blender 4.5.
- identity-auditor + multiview-auditor: compare candidates vs `01_subject_front` + profiles.
- **Gate (user-mandated):** a candidate is "recognizable Character 001" only if it passes
  front **and** side visual + landmark/IoU thresholds. Until then status stays
  planned/implemented/unit-tested/rendered — never "reconstructed" or "photoreal".

**Phase 4 — Rigging & facial animation evaluation (after a candidate wins Phase 3)**
- facial-rig-engineer: how to attach facial animation to a reconstructed mesh (morph-target
  transfer from a licensed template vs bone/corrective shapes vs retopology to a quad face mesh);
  blink, jaw open, smile, lip closure QA on the winner.
- blink-specialist / expression-specialist / lipsync-engineer / phoneme-aligner (voice.wav) /
  natural-motion-engineer / eye-specialist / hair-specialist (short curly auburn replacement) /
  uv-texture-engineer / skin-albedo-engineer / skin-microdetail-engineer / wardrobe-lookdev:
  targeted experiments on the winning candidate only.
- topology-specialist: retopology plan for animation-grade edge flow (eyes/lips/jaw loops).
- glb-interoperability-engineer: exported-GLB invariant audit of each candidate.
- phoneme-aligner: real phoneme timing from `assets/voice.wav` or blocker (no guessed timings).

**Phase 5 — Integration**
- release-integrator: proposes integration order and branch hygiene. No merges to `main`
  without user approval. Feature branch `feat/m001-talking-human-pipeline` only.

## Fallback policy

`geo/morph_fit.py` + the GEO-02 audit remain runnable and are kept green. They are the fallback
*only* if image-first reconstruction produces no usable topology. They must not block, and must
not be preferred for, new work. GEO-01 silhouette-loft code may be reused by Lane B.

## Hard rules (unchanged)

No pushes/merges to main; no paid API submissions; no uploading reference images or voice
to any third-party service without explicit approval; no credentials in files; generated binaries
stay under ignored `output/`; statuses stay distinct (planned → implemented → unit-tested →
rendered → visually approved); unrun checks are labeled UNVERIFIED.

## Current dispatch state

See `docs/C001_GEO03_DISPATCH.md` (first batch) and this document for the updated
image-first strategy. Worktrees:
`livynth-c001-geo03-visual-hull` (Lane B), `livynth-c001-geo03-triposr` (Lane A),
`livynth-c001-geo03-calibration`, `livynth-c001-geo03-landmarks`, `livynth-c001-geo03-qa-scorecard`.
