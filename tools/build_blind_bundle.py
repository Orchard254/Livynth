"""Build a blind Phase-3 gate bundle for a candidate (coordinator-side blinding).
SUPERSEDED BY ADR-C001-004 -- Phase-3 appearance-metric gate.

This tool measures RENDERED APPEARANCE (silhouette IoU, similarity-aligned
landmark error). ADR-C001-004 requires the decisive gate to rest on
geometry-level evidence, because the Phase-3 controls proved these metrics
cannot see identity on a photo-projected candidate: a jitter canary
(sigma = 8 px) scored 0.9036 silhouette IoU and 8.92 px landmark error, and
a wrong-identity canary (face band widened 1.18x) scored 13.0 px -- both
PASSED the thresholds that were supposed to reject them.

Retained as the evidence trail for that negative result and as the seeding
point for the geometry-level gate. Do NOT cite its output as proof that a
candidate matches Character 001.


Per docs/C001_GEO03_BLIND_SCORECARD.md:
  - candidates are exposed only under an opaque label (A, B, ...)
  - the label -> backend map is sealed in blind_map.sealed.json (NOT for judges)
  - the judge bundle contains only whitelisted files: the GLB, the five standardized
    renders, the reference views, the protocol and a rubric sheet
  - no source code, no paths, no sizes, no timings, no backend names in the bundle

Usage:
    python tools/build_blind_bundle.py --label A --glb <glb> --report <report.json> \
        --renders <dir> --signs <signs.json> --images <ref dir> --out output/qa/geo03/<run_id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

RENDER_VIEWS = ["front", "left45", "right45", "left90", "right90", "back"]
REFERENCE_VIEWS = {
    "front": "01_subject_front.png",
    "left_profile": "04_left_profile.png",
    "right_profile": "05_right_profile.png",
}

RUBRIC = """# Blind candidate review - Character 001 (Phase 3)

You are reviewing an UNLABELLED candidate head. You do not know which method produced it.
Judge it against the reference photographs in `references/` only.

Required views: front (01_subject_front.png), left profile (04_left_profile.png),
right profile (05_right_profile.png). The 45-degree and back renders are advisory.

For each required view give one label and one line of observable evidence:
  ACCEPT          - reads as the same person as the reference
  REFERENCE_ONLY  - usable as appearance reference, not a likeness
  REGENERATE      - wrong identity / anatomically impossible / artifact-ridden

Checklist (tick each with evidence): eye spacing; brow line; nose projection vs the profiles;
lip shape; chin and jaw; hair mass and hairline; ear placement; skin tone and freckles;
cross-view impossibility (a feature consistent in one view but impossible in another).

Numeric sub-gates (from the protocol): front landmark mean <= 16 px; silhouette IoU
front >= 0.80 and profiles >= 0.75. Controls: reference self-IoU must be 1.000;
a jitter canary must FAIL. If a control misbehaves, report BLOCKED instead of a verdict.

Sign-off format: role, label per required view, checklist evidence, UTC timestamp.
Do not request edits; a changed candidate comes back as a new label.
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--renders", required=True)
    ap.add_argument("--signs", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", default="", help="sealed only; never shown to judges")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    out = Path(args.out)
    label_dir = out / args.label
    refs_dir = out / "references"
    label_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    signs = json.loads(Path(args.signs).read_text(encoding="utf-8"))

    # candidate artifacts (whitelisted names only)
    shutil.copy2(args.glb, label_dir / f"{args.label}.glb")
    render_hashes = {}
    for view in RENDER_VIEWS:
        tag = "p" if signs[view]["sign"] == "+" else "n"
        src = Path(args.renders) / f"probe_{view}_{tag}.png"
        dst = label_dir / f"{view}.png"
        shutil.copy2(src, dst)
        render_hashes[view] = sha256(dst)

    # references (judges need the ground truth alongside)
    ref_hashes = {}
    for view, fname in REFERENCE_VIEWS.items():
        src = Path(args.images) / fname
        dst = refs_dir / fname
        shutil.copy2(src, dst)
        ref_hashes[fname] = sha256(dst)

    (out / "RUBRIC.md").write_text(RUBRIC, encoding="utf-8")

    sealed = {
        "sealed": True,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "labels": {
            args.label: {
                "backend": args.backend,
                "note": args.note,
                "glb_sha256": sha256(label_dir / f"{args.label}.glb"),
                "render_sha256": render_hashes,
            }
        },
        "reference_sha256": ref_hashes,
        "warning": "NOT for judges. Reveal only after every judge has signed off.",
    }
    (out / "blind_map.sealed.json").write_text(json.dumps(sealed, indent=2) + "\n", encoding="utf-8")

    print(f"bundle: {out}")
    print(f"  candidate label : {args.label}")
    print(f"  glb             : {label_dir / (args.label + '.glb')}")
    print(f"  renders         : {sorted(p.name for p in label_dir.glob('*.png'))}")
    print(f"  references      : {sorted(p.name for p in refs_dir.glob('*.png'))}")
    print("  sealed map      : blind_map.sealed.json (not for judges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
