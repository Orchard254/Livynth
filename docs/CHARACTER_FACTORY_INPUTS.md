# Character Factory — verified research packet (2026-11-11)

Compiled by the coordinating architect from executed checks and completed specialist reports.
Everything here is evidence-grade: commands were run or reports are quoted as summaries.
Use this as the input brief for `docs/CHARACTER_FACTORY_SPEC.md`.

## 1. Mission frame

- Long-term goal: modular, automated digital-human creation + AI video-production engine; thousands of unique characters; automated filmmaking; interactive virtual worlds.
- C001-GEO-03 (Character 001) is the first factory run. Next validation goal: Character 002 through the same pipeline with minimal character-specific code changes.
- No disruptive rewrite of working code; no merges to `main` without approval; binaries stay under ignored `output/`; per-character data must be separable.

## 2. Verified machine/environment (measured 2026-11-11)

- OS: Windows 11 (HP Laptop 14-cf2xxx), i7-10510U (4C/8T), 16 GB RAM (3.9 GB free at measurement), disk C: 25.7 GB free, G: 47.5 GB free.
- GPUs: Radeon 530 + Intel UHD; **no CUDA**; no nvidia-smi; all GPU-compute treated as unavailable.
- Blender 4.5.10 LTS at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` (not on PATH); headless works; Cycles CPU sphere render passed; MPFB (MakeHuman CC0 base) auto-loads.
- Python 3.14.7 at `python`. Installed: numpy 2.5.3, scipy 1.18.1, trimesh 5.2.0, pillow 12.3.0, scikit-learn, onnxruntime 1.29.0, huggingface_hub, psutil. **torch 2.15.0+cpu now installed** (by neural lane via download.pytorch.org/whl/cpu). NOT installed: opencv, mediapipe, open3d, scikit-image.
- `python tools/local_check.py` → PASS (21/21). `python -m unittest discover -s geo/tests -v` → 21/21 OK (after `pip install trimesh`).
- ffmpeg / ffprobe / espeak-ng: NOT on PATH. choco 2.7.4 and winget available (not invoked).
- Node.js present (npx usable for gltf-validator, unverified).

## 3. Reference pack truth (measured by asset-curator + multiview-auditor + calibration lane)

- 15 PNGs in `assets/characters/character_001/identity_capture_v1/` (gitignored; never committed; all local).
- All carry **C2PA manifests signed OpenAI** (`gpt-image`, `trainedAlgorithmicMedia`), timestamps 2026-11-11T01:25–02:29Z. **AI-generated, not camera captures; no EXIF, no lens data, no seed, no checkerboard; spec "≥2048 native" unmet except 11_eyes_closeup (a 3:1 macro crop).**
- Sizes: face views 1086×1448; 07/08 ≈ 1087×1447/46; 09_left_ear 1199×1312; 11_eyes_closeup 2172×724; macros 1536×1024 / 1774×887.
- Consistency audit (visual, uncalibrated): two white-balance clusters; **nose/chin/hair/ear/freckle/iris-anchor contradictions across views; pack FAILS SfM, is CONDITIONAL for a loose silhouette hull (hair/ears excluded), reference-only for TripoSR, PASS-as-appearance-reference.** Must never be called "calibrated" or "scanned".
- SHA-256 (main views; full set in QA/asset docs): 01 `9d84f485…eaed2dd`, 02 `86243d7e…30a9`, 03 `0f0c748a…37a3a`, 04 `702eb69b…97d1cd`, 05 `65101246…863eba`, 06 `8339543d…bfd684`, 07 `219cba0e…755f0b4a`, 08 `af8e3a85…b832cd`.
- `assets/voice.wav`: PCM mono 16-bit 22050 Hz, 308,638 frames = **13.997 s**, peak 0.936, RMS −21 dBFS; ≈9.9 s speech-active; SHA256 `98FDFCDBD371D848B4846A17820D0F62E398EECEE7C51079CF3056824D4EDD0A`. Transcript (29 words, untracked `assets/voice_transcript.txt`) begins "Welcome to Livynth…". Word pace ≈2.07 words/s (forced-alignment friendly).

## 4. What EXISTS and works (verified or reported)

- `geo/`: `proxy_fit.py` (single-view silhouette loft; reusable segmentation rule: border-median bg, distance>26 & chroma>12 | >54), `morph_fit.py` (GLB2 reader/editor, Gaussian RBF warp, Jacobian/normal transport; V32-morph-rich-source specific; GEO-02 fallback only), `audit_morph_fit.py` (source↔candidate differential GLB audit; not an absolute audit), 21 green tests, `character001_landmarks.json` (legacy manual front estimates: eyes (444,526)/(656,525), mouth (466,762)/(630,762), chin (549,925); IPD ≈ 212 px).
- `video/`: `make_timeline.py` (spelling+energy viseme heuristics; NOT phoneme-accurate; hardcoded blink centers), `render_talk.py` (Blender headless GLB→1080×1920 MP4/PNG path; shape-key drivers; ORTHO studio preset; 49 tests green overall), `build_video.py`, `model_check.py`.
- Worktrees (detached @31a9b19, unmerged, none pushed):
  - `livynth-c001-geo03-visual-hull` — Lane B (multi-view voxel visual hull + MCubes + photometric texture) **implementing**.
  - `livynth-c001-geo03-triposr` — Lane A TripoSR CPU attempt **running** (torch CPU installed; clone+deps+1.68 GB weights step pending; license MIT verified by research; expected poor likeness — experiment, not promise).
  - `livynth-c001-geo03-calibration` — calibration spec DONE: `geo/calibration_spec.py`, 33/33 tests pass, committed locally as `da5ccc1` (branch `experiment/c001-geo03-calibration`); orbit-camera model, real SHA-256s, ASSUMED intrinsics (90 mm eq, 1500 mm radius, 63 mm interocular scale prior), verify_image_hashes().
  - `livynth-c001-geo03-landmarks` — landmark schema DONE: `geo/landmark_spec.py`, 32/32 tests pass, legacy migration done; mediapipe/opencv install in flight (per-view detection NOT yet reported; install outcome UNVERIFIED).
  - `livynth-c001-geo03-qa-scorecard` — blind scorecard PERSISTED at `docs/C001_GEO03_BLIND_SCORECARD.md` (verbatim from independent-regression-qa): blinding rules, front gate (landmark mean ≤16 px placeholder; IoU front ≥0.80 / profiles ≥0.75 placeholders), GLB absolute invariants (watertight, UV on primitives, normals ≤1e-3, finite data, embedded textures), required controls (self-IoU=1.000, jitter canary MUST fail, GEO-02 expected-fail canary), JSON report schema, signoff roles.
- Reports completed (conversation-only unless persisted): benchmark; morph-fitting fallback (blocked — no source GLB); blink (6-target min set, retopo-first, hard gates G-B1..B7); facial-rig (option (a) retopo+shapes recommended; (b) transfer infeasible today; options (c) supplement, (d) preview-only); expression (10 combo tests T01–T10 with pass criteria); lipsync (19/21-viseme inventory, 80 ms attack/release envelope policy, closure gate C1/C2); natural-motion (lane separation, blink-gaze coherence protocol); hair (shell/card hybrid over haired hull, staged; strands rejected; baked-hull = fallback); eye (analytic anterior segment recommended; macro measurements: iris Ø ≈ 230 px ≈11.5 mm ASSUMPTION, pupil/iris ≈ 0.26, naevus at ~4:30); uv-texture (bake-not-project, delighted atlas, 2K gate + 4K upgrade); skin-albedo (de-light + photometric-vs-unlit A/B); skin-microdetail (macro only ~20 px/mm, pores sub-texel at 4K unless 8K; stats-not-source); wardrobe (navy measured median RGB ≈ (22,27,46) #161b2e lower frame; collar neckline y≈0.87 center; shirt-off rejected; head-and-shoulders only); video-finishing (0% verified end-to-end; ffmpeg absent; highest-value next artifact = real phoneme alignment); reconstruction-research (FLAME 2023 Open = CC-BY-4.0 but registration-gated user approval; TripoSR MIT but weak likeness prior; MiDaS/DA-V2-Small safe; InstantMesh/TRELLIS infeasible+NC; 3DDFA_V2 BFM academic-only; depth fusion = soft prior only); external-api (no submissions; Tripo Pro $20/mo / API $0.20–0.30 per image-to-3D — only plausible probe with written user approval; Reallusion Headshot 3 ~$329 desktop = only aligned non-upload paid path; Ready Player Me and Meshcapade SHUT DOWN; Hyper3D §7 biometric clause problematic; Avaturn vests IP in vendor; Hunyuan = PIPL/Tencent Cloud gate).
- Topology plan: retopology to a designed quad head (MPFB CC0 basemesh via installed Blender) fitted to candidate; candidate as silhouette/displacement reference only (not retopo substrate); animation loops per eye/lip/jaw; decision needed from user (Option B).

## 5. Hard constraints / gates

- Success (per user mandate) = recognizable Character 001 vs front AND side refs (blind, blinded judges) — never a bare GLB. Statuses stay distinct (planned/implemented/unit-tested/rendered/visually approved).
- No push/merge to `main`; no external uploads; no paid APIs without explicit user approval; FLAME registration gated; binaries ignored; no credentials in files.
- Licenses: MakeHuman CC0 (models/assets); MPFB addon GPL (tool, OK); Blender GPL; FLAME classic non-commercial; DA-V2-Base/Large/Giant CC-BY-NC; mediapipe Apache-2.0; trimesh/open3d MIT; torch BSD-style.
- Both candidate lanes likely produce UNRIGGED, UNTEXTURED-ish meshes; retopo + textures + blink/jaw/smile shapes required for M001 gates regardless of lane.

## 6. Open user decisions

1. FLAME 2023 Open registration (CC-BY-4.0): approve/deny (Lane C).
2. External API trial (Tripo multiview, ~$1–20): approve/deny.
3. Aligner installs (montreal-forced-aligner or whisper+stable-ts, ~1–2 GB): approve/deny (phoneme timing for voice.wav).
4. Face-mesh install completion (mediapipe/opencv cp314): in flight, no decision needed unless it fails.
5. Topology Option B (designed quad head, MPFB base): approve/deny.
6. V32 source GLB (`our-avatar-v32-clean-blink.glb`): supply or formally retire the fallback.
7. 4K vs 2K texture budget; KTX2 vs PNG; Reallusion purchase (separable decision).
8. Character 002 identity seed pack (when factory spec is accepted).

## 7. Non-goals for the factory spec (avoid scope creep)

- No rewrite of `video/` or `geo/` before Phase 3 gate of GEO-03.
- No claim that Character 002 will be photoreal before Character 001 passes its gate.
- No commitment to any single vendor; backends must be swappable; license metadata must be tracked per artifact.
