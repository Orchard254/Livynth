# LIVYNTH — engineering and agent rules

**Product:** "Give Imagination Life" — original digital humans, multi-angle likeness, facial animation and scripted portrait video.

## Current verified history and limits

- Repository: `Orchard254/Livynth`, development PR #1 on `feat/m001-talking-human-pipeline` (draft). Do not change main or merge without approval.
- M001 has a working experimental GLB import and test still pipeline, but full lip-synchronized final-quality video remains unverified. `video/make_timeline.py` uses text and energy heuristics, not phoneme-accurate sync.
- C001-GEO-01 silhouette envelope was watertight but **not** a 3D face. Do not animate it as if it were one.
- C001-GEO-02 fitted the baseline avatar conservatively while preserving structural GLB features, but the old avatar's identity/hair are still visibly wrong.
- Canonical identity: original auburn-haired adult man in `01_subject_front.png`. Approved comparison views: `02_subject_left_45.png`, `03_subject_right_45.png`, `04_left_profile.png`, `05_right_profile.png`. These are independently generated photographs, not camera-calibrated scans.

## Commands and dependencies

- Python local checks: `python tools/local_check.py`
- Geometry tests: `python -m unittest discover -s geo/tests -v` after `python -m pip install -r requirements-geometry.txt`
- Model input typically `assets/ours-photoreal.glb`, photos in `assets/characters/character_001/identity_capture_v1/`; generated GLBs remain under `output/` and are ignored by Git. Never modify the original GLB.
- Blender renderer requires Blender installed and is validated **only** by actual Blender logs and rendered images; do not infer success from Python syntax checks.

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
