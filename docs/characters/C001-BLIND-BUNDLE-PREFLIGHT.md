# C001-GEO-03 — Blind review data hygiene preflight (2026-11-11)

**Status:** tools and synthetic tests implemented. **No real Phase-3 candidate has passed.**

## Why this exists

The first Phase-3 judge accidentally saw prior evaluation content and was invalidated. The older `tools/build_blind_bundle.py` still writes `blind_map.sealed.json` into its combined coordinator output directory. A reviewer must not be directed to that directory. This utility creates a **separate whitelisted, image-only judge copy**, strips image metadata, and refuses any unexpected files before judging.

This is a blinding-hygiene control only: it does not prove the judge is truly independent, that a 3D head matches Character 001, or that wrong-identity controls pass. It does not compare candidate geometry to ground truth.

## Commands (run from repo root)

```powershell
# The coordinator's source must have a `references/` directory and the six
# photo renders, five clay renders and front+profile depth/normal renders per
# opaque candidate label. Never point a judge at this private source directory.
python tools/blind_bundle_preflight.py build `
  --source .\output\qa\geo03\RUN_ID `
  --out .\output\qa\judge_inputs\RUN_ID `
  --labels A B

# A separate coordinator/QA agent runs the preflight before the judge session.
python tools/blind_bundle_preflight.py verify `
  --bundle .\output\qa\judge_inputs\RUN_ID `
  --labels A B `
  --report .\output\qa\preflight_results\RUN_ID.json

# Smoke test for earlier photo-only experiments; **NOT** a geometry pass.
python tools/blind_bundle_preflight.py build `
  --source .\output\qa\geo03\RUN_ID `
  --out .\output\qa\judge_inputs\RUN_ID_DIAGNOSTIC `
  --labels A B --mode appearance-diagnostic

python -m unittest discover -s tests -p 'test_blind_bundle_preflight.py' -v
```

**Expected input layout:** `RUN_ID/references/01_subject_front.png`, `02_subject_left_45.png`, `03_subject_right_45.png`, `04_left_profile.png`, `05_right_profile.png`. Each label `A/`, `B/` contains `front.png`, `left45.png`, `right45.png`, `left90.png`, `right90.png`, `back.png`, plus `clay_{front,left45,right45,left90,right90}.png`, `depth_{front,left90,right90}.png`, and `normal_{front,left90,right90}.png` for geometry-mode. The utility copies exactly these PNGs. It deliberately does **not** expose raw GLBs, logs, model identity, prior verdicts, sealed maps, timestamps, file hashes or coordinator notes. A separate unblinded structural QA worker audits the GLB.

**Safety gates:** distinct short labels, fresh output folder, disjoint source/destination, no source or output symlinks, no injected files or prior verdicts, PNG CRC and structural checks, metadata-stripped images, fixed judge rubric, and an independent `--report` destination outside the judge input. The original source directory is not modified. **Exit code 2 / status BLOCKED** means no judge can proceed. **`SAFE_TO_JUDGE_ONLY` does not mean quality or reconstruction PASS.** The images are not redacted against readable text drawn into pixels; the human review coordinator must visually check for watermarks or embedded markings. Real render consistency, geo quality, negative canaries, judge independence and final acceptance remain separate mandatory gates under ADR-C001-004.

**Technical evidence:** 15 local synthetic tests passed. A sanitized synthetic PNG was successfully decoded by Pillow. Actual OpenCode judge bundles have not been evaluated by this tool; candidate files may be missing required clay/depth/normal renders until the agents create them. No Blender run or real Character 001 likeness assessment is claimed.

**Integration:** keep the older coordinator's metadata and prior results in its private directory, then export a *new* clean judge input directory for every attempt. The independent QA specialist verifies that directory and records its verdict separately. Do not replace or delete the failed historical gate records.