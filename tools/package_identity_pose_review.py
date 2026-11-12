#!/usr/bin/env python3
"""Bundle the existing IDENTITY-007 pose renders for independent visual review.

Does NOT run Blender, regenerate characters, include GLBs, or approve likeness.
Only fixed, validated JSON/HTML/PNG evidence enters the portable ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.identity_pose_review import (
    CHARACTERS, SCHEMA, render_jobs, validate_character_report,
    gallery_html, check_png_dimensions,
)

BUNDLE_SCHEMA = "livynth.identity.pose-review-bundle.v1"
IMAGE_WIDTH, IMAGE_HEIGHT = 400, 600


class ReviewBundleError(ValueError):
    pass


def evidence_paths(directory):
    """Only these fixed relative filenames may appear in an export."""
    names = [Path("index.html"), Path("pose_review.json")]
    for char in CHARACTERS:
        names.append(Path(char) / "render_report.json")
        for view, pose, _ in render_jobs():
            names.append(Path(char) / f"{view}_{pose}.png")
    return names


def _safe_source(root, rel):
    root = Path(root)
    current = root
    if root.is_symlink() or not root.is_dir():
        raise ReviewBundleError("E_SOURCE_DIRECTORY")
    for segment in rel.parts:
        current = current / segment
        if current.is_symlink():
            raise ReviewBundleError("E_SYMLINK_BLOCKED: " + str(rel))
    if not current.is_file():
        raise ReviewBundleError("E_MISSING_EVIDENCE: " + str(rel))
    if not current.resolve().is_relative_to(root.resolve()):
        raise ReviewBundleError("E_PATH_ESCAPE")
    return current


def prepare_review_bundle(directory):
    """Validate real on-disk poses and return read-only packaging contents."""
    root = Path(directory).resolve()
    summary = json.loads(_safe_source(root, Path("pose_review.json")).read_text(encoding="utf-8"))
    if (summary.get("schema") != SCHEMA or
        summary.get("status") != "CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW" or
        summary.get("character_count") != 2 or
        summary.get("existing_glb_morph_signal") != "PASS" or
        summary.get("raster_signal") != "PASS_VISIBLE_DIFFERENCES_NOT_VISUAL_QUALITY" or
        summary.get("expression_naturalness") != "PENDING_HUMAN_REVIEW"):
        raise ReviewBundleError("E_REVIEW_SUMMARY")
    contents = {}
    # Rebuild the gallery rather than trusting an HTML file that could contain
    # local/private links or arbitrary scripts.
    contents["index.html"] = gallery_html(summary).encode("utf-8")
    contents["pose_review.json"] = _safe_source(
        root, Path("pose_review.json")).read_bytes()
    for char in CHARACTERS:
        rel = Path(char) / "render_report.json"
        report = json.loads(_safe_source(root, rel).read_text(encoding="utf-8"))
        validate_character_report(report, root, char, width=IMAGE_WIDTH, height=IMAGE_HEIGHT)
        contents[rel.as_posix()] = _safe_source(root, rel).read_bytes()
        for view, pose, _ in render_jobs():
            rel = Path(char) / f"{view}_{pose}.png"
            src = _safe_source(root, rel)
            check_png_dimensions(src, IMAGE_WIDTH, IMAGE_HEIGHT)
            if src.stat().st_size > 20_000_000:
                raise ReviewBundleError("E_PNG_TOO_LARGE")
            contents[rel.as_posix()] = src.read_bytes()
    if len(contents) != 24:  # 20 PNG, 2 character JSON, 1 summary, 1 gallery
        raise ReviewBundleError("E_BUNDLE_ENTRIES")
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "status": "PORTABLE_EVIDENCE_NOT_HUMAN_VISUAL_APPROVAL",
        "character_count": 2,
        "png_count": 20,
        "included_files": {
            name: {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(contents.items())
        },
        "excluded": ["GLB geometry", "reference photographs", "audio", "model weights"],
        "identity_likeness": "UNVERIFIED",
        "expression_naturalness": "PENDING_HUMAN_REVIEW",
    }
    contents["bundle_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    return contents, manifest


def create_bundle(directory, out=None):
    directory = Path(directory)
    destination = Path(out) if out else directory.with_suffix(".zip")
    # Refuse even a failed overwrite attempt before reading untrusted inputs.
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Refusing to overwrite existing review ZIP: " + str(destination))
    content, manifest = prepare_review_bundle(directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(destination, mode="x", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            for name, raw in sorted(content.items()):
                archive.writestr(name, raw)
    except BaseException:
        # Never leave a misleading partial review bundle on failure.
        destination.unlink(missing_ok=True)
        raise
    return destination, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True,
                        help="Existing pose_review/<timestamp> containing the 20 PNGs")
    parser.add_argument("--out", type=Path,
                        help="Optional unused ZIP path; defaults to <folder>.zip")
    args = parser.parse_args(argv)
    try:
        dest, report = create_bundle(args.folder, args.out)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        parser.exit(2, "LIVYNTH review bundle FAILED: " + str(exc) + "\n")
    print(json.dumps({"status": report["status"], "archive": str(dest.resolve()),
                      "png_count": report["png_count"], "character_count": 2,
                      "human_visual_review": "PENDING"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
