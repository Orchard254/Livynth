# C001-GEO-03 first batch dispatch

**Input:** approved reference ZIP extracted into `assets/characters/character_001/identity_capture_v1/`, source baseline GLB `assets/ours-photoreal.glb`, previous C001-GEO-02 candidate (if available), existing branch `feat/m001-talking-human-pipeline`.

**Task A:** `reconstruction-research` assesses 3 practical backends, dependencies, legal/licensing terms, topology, API pricing and whether model outputs have morph targets. Read-only report.

**Task B:** `camera-calibrator` + `landmark-engineer` develop one common projection/calibration and landmark input format; separate worktrees/ownership. Compare with `multiview-auditor` as challenger.

**Task C:** `parametric-reconstruction` and `neural-reconstruction` independently generate at least one candidate each on the same test images if installed weights/compute allow. Report any blocker rather than inventing a mesh. Source GLB and images remain untouched.

**Task D:** `independent-regression-qa` defines a blind scorecard, thresholds for silhouette/landmark errors, GLB invariants, full blink, jaw open and visual evaluation. This agent must not know which candidate came from which backend when judging image pairs.

**Task E:** After candidates exist, `blender-render-specialist` renders five standardized angles; `identity-auditor` and `geometry` specialists independently evaluate. `release-integrator` proposes changes but does not merge.

**Stop conditions:** missing reference assets, no model weights, insufficient GPU VRAM, external API awaiting opt-in, failed asset license, broken morph targets, missing actual render. Keep statuses distinct: planned, implemented, unit-tested, rendered, visually approved.
