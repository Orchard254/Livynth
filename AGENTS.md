# LIVYNTH — engineering and agent rules

**Product:** "Give Imagination Life" — original digital humans, multi-angle likeness, facial animation and scripted portrait video.

## Current verified history and limits

- Repository: `Orchard254/Livynth`, development PR #1 on `feat/m001-talking-human-pipeline` (draft). Do not change main or merge without approval.
- M001 has a working experimental GLB import and test still pipeline, but full lip-synchronized final-quality video remains unverified. `video/make_timeline.py` uses text and energy heuristics, not phoneme-accurate sync.
- C001-GEO-01 silhouette envelope was watertight but **not** a 3D face. Do not animate it as if it were one.
- C001-GEO-02 fitted the baseline avatar conservatively while preserving structural GLB features, but the old avatar's identity/hair are still visibly wrong. Per ADR-C001-004 decision 5 the V32/MakeHuman source GLB is **retired from the C001 critical path** — optional baseline only, never a prerequisite.
- Canonical identity: original auburn-haired adult man in `01_subject_front.png`. Approved comparison views: `02_subject_left_45.png`, `03_subject_right_45.png`, `04_left_profile.png`, `05_right_profile.png`. These are independently generated photographs, not camera-calibrated scans.

## Authoritative decision record

`docs/decisions/ADR-C001-004-phase3-repair.md` is the current owner-approved decision record (2026-11-11): seven decisions, a mandatory geometry-first acceptance protocol, and the agent dispatch map. Read it before planning reconstruction work. In short: Topology Option B approved conditional on verified provenance; **one** bounded Candidate A repair experiment; FLAME 2023 Open evaluation only (no account, no terms, no import); aligner installation deferred; V32 GLB retired from the critical path; 2048×2048 PBR texture target for the prototype; Character Factory spec provisionally approved as an interface contract.

## Phase-3 status: FAIL

- The Phase-3 blind gate **failed**. No candidate is a recognizable Character 001 and no likeness may be claimed. Candidate A (visual hull) reads as the reference's appearance in front but is a flat photographic projection on a shell with a torn posterior cranium; Candidate B (TripoSR) has real 3D structure but is a different, generic person.
- **A photo projected onto a shell is not a likeness.** Rendered-image metrics (silhouette IoU, similarity-aligned landmark error) measured the *photograph* on such a candidate: a jitter canary (σ = 8 px) and a wrong-identity canary (face widened 1.18×) both **passed** those metrics. Appearance metrics are diagnostic only and can never certify identity.
- The decisive gate is geometry-level: neutral clay renders + wireframes + orthographic depth/normal maps with an explicit camera convention, artifact QA (manifoldness, duplicate shells, self-intersection/offsets, topology class, normal consistency, camera assumptions, rig/blendshape function), and wrong-identity controls that the gate **must reject**. A rejected profile can never be overridden by a good-looking front texture; the stricter per-view label wins.
- A gate run whose controls are not rejected is **BLOCKED** (`gate_valid: false`), not passed.
- Local review evidence: `python tools/branch_audit.py --run-tests` (worktrees, commit SHAs, tracked-binary check, `main`-untouched check, protected user-change state).

## Commands and dependencies

- Python local checks: `python tools/local_check.py`
- Geometry tests: `python -m unittest discover -s geo/tests -v` after `python -m pip install -r requirements-geometry.txt`
- Repo test suite: `python -m unittest discover -s tests -v`
- Model input typically `assets/ours-photoreal.glb`, photos in `assets/characters/character_001/identity_capture_v1/`; generated GLBs remain under `output/` and are ignored by Git. Never modify the original GLB.
- Blender renderer requires Blender installed and is validated **only** by actual Blender logs and rendered images; do not infer success from Python syntax checks.
- This machine: no CUDA, 16 GB RAM, Python 3.14.7, Blender 4.5.10 LTS at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` (not on PATH). No ffmpeg/espeak, so phoneme alignment stays heuristic until an aligner is installed.


## Source-of-truth and quality gates

1. Every result carries source commit, commands, environment, input hashes, artifact path, execution status and known failure modes.
2. Multi-angle neutral likeness: compare front, left/right 45°, left/right 90° at controlled camera framing; use measured landmarks and independent human visual inspection.
3. Structural compatibility: scene meshes, UVs, skin, morph target names/counts, animation and textures survive reconstruction/export unless explicitly changed and audited.
4. Motion QA: neutral, half blink, full blink, jaw open, smile and lip closure; detect penetrations, mesh folds and asymmetry.
5. Audio/video QA: audible voice, timing, captions, 1080×1920 MP4 when M001 production gate is attempted.
6. A watertight GLB is **necessary but insufficient** evidence; never call identity or photorealism successful without visual comparison.

## Collaboration rules

- One coordinating primary agent dispatches work to specialists. Specialists receive narrowly scoped ownership and return evidence; do not concurrently mutate the same files.
- Use **isolated Git worktrees** for editing agents, e.g. `git worktree add ../livynth-c001-08 -b experiment/c001-08 feat/m001-talking-human-pipeline`. Coordination and merge into feature branch happen only after review; never direct-write from many agents to a single checkout.
- Start with 4–8 independent running tasks, not all 30 on one GPU. A defined role does not mean always-on compute.
- No repo push/merge/delete, no paid API submission, and no uploading a user's portrait to third-party services unless explicit approval is obtained.
- No credentials in prompts, code, output files or commits. Keep generated binaries outside Git unless specifically requested.
- If a test is unrun, say **UNVERIFIED** rather than guessing. Preserve negative results.
