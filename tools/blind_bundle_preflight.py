#!/usr/bin/env python3
"""Fail-closed preflight and whitelist-only export for LIVYNTH Phase-3 judges.

The existing coordinator bundle may contain verdicts and ``blind_map.sealed.json``.
Never point an independent judge at that directory. Instead, build a clean,
image-only judge copy and verify it before permitting a human review.

This module checks *blinding hygiene*, not reconstruction quality or identity.
It never uploads images, runs models or alters the private source bundle.

Example::

  python tools/blind_bundle_preflight.py build \\
    --source output/qa/geo03/run42 --out output/qa/judges/run42 \\
    --labels A B
  python tools/blind_bundle_preflight.py verify \\
    --bundle output/qa/judges/run42 --labels A B \\
    --report output/qa/reports/run42_preflight.json

By default, the bundle requires photo renders plus untextured clay, depth and
normal views. ``--mode appearance-diagnostic`` permits older photo-only inputs,
but is *never* sufficient to certify geometry or facial likeness.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import tempfile
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Only visual-data chunks and limited colorimetry pass to the judge copy.
# Unrecognized ancillary chunks (including C2PA, EXIF, PNG text, ICC) are stripped.
PASS_CHUNKS = frozenset({b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"sBIT"})
VIEWS = ("front", "left45", "right45", "left90", "right90", "back")
GEOMETRY_VIEWS = ("front", "left45", "right45", "left90", "right90")
PROFILE_VIEWS = ("front", "left90", "right90")
REFERENCES = ("01_subject_front.png", "02_subject_left_45.png", "03_subject_right_45.png",
              "04_left_profile.png", "05_right_profile.png")
LABEL = re.compile(r"^[A-Z]$")
RUBRIC = """# LIVYNTH — blind geometry-first review

Judge the same anonymous head across front, +/-45 and +/-90 degrees.
The photo renders are identity *diagnostics*, never a substitute for geometry.
For each required view (front, left90, right90) inspect clay, depth and normal
images **before** the corresponding textured render. Identify actual shape
inconsistencies (eyes, brows, nose projection, cheeks, lips, chin, jaw, ears).
A good front photo over a bad 3D shell is not a reconstructed identity.

Return ACCEPT / REFERENCE_ONLY / REGENERATE per required view, with specific
anatomical evidence. Stricter per-view label controls the overall outcome.
Write your verdict OUTSIDE this input directory and do not read any previous
verdict, backend identity or evaluator summary. The gate additionally requires
independent geometry and wrong-identity canary testing; this review alone is
not a pass. In appearance-diagnostic mode, never award geometry ACCEPT.
"""


class BlindBundleError(ValueError):
    """Judge input is unsafe or incomplete. Review must not start."""


def required_candidate_files(mode: str) -> frozenset[str]:
    if mode not in ("geometry", "appearance-diagnostic"):
        raise BlindBundleError("Invalid review mode")
    names = {f"{v}.png" for v in VIEWS}
    if mode == "geometry":
        names |= {f"clay_{v}.png" for v in GEOMETRY_VIEWS}
        names |= {f"depth_{v}.png" for v in PROFILE_VIEWS}
        names |= {f"normal_{v}.png" for v in PROFILE_VIEWS}
    return frozenset(names)


def validate_labels(labels: list[str]) -> tuple[str, ...]:
    if not labels or len(set(labels)) != len(labels) or any(not LABEL.fullmatch(v) for v in labels):
        raise BlindBundleError("Labels must be distinct single uppercase letters (A, B, ...)")
    return tuple(labels)


def inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def no_overlaps(source: Path, dest: Path) -> None:
    if inside(dest, source) or inside(source, dest):
        raise BlindBundleError("Source and judge bundle locations must not overlap")


def png_clean_bytes(content: bytes) -> bytes:
    """Verify PNG CRC and strip ancillary metadata without recompressing pixels."""
    if not content.startswith(PNG_SIGNATURE):
        raise BlindBundleError("Not a PNG")
    pos, out, types = len(PNG_SIGNATURE), bytearray(PNG_SIGNATURE), []
    while pos < len(content):
        if pos + 12 > len(content):
            raise BlindBundleError("Truncated PNG chunk")
        length = int.from_bytes(content[pos:pos + 4], "big")
        if length > (64 << 20) or pos + 12 + length > len(content):
            raise BlindBundleError("Oversized or truncated PNG chunk")
        chunk_type = content[pos + 4:pos + 8]
        data = content[pos + 8:pos + 8 + length]
        crc = int.from_bytes(content[pos + 8 + length:pos + 12 + length], "big")
        if (zlib.crc32(chunk_type + data) & 0xffffffff) != crc:
            raise BlindBundleError("PNG CRC mismatch")
        if len(types) == 0 and (chunk_type != b"IHDR" or length != 13):
            raise BlindBundleError("Missing PNG header")
        if chunk_type == b"IHDR":
            if len(types) != 0:
                raise BlindBundleError("Repeated PNG header")
            width, height = struct.unpack(">II", data[:8])
            if width == 0 or height == 0 or width > 16384 or height > 16384:
                raise BlindBundleError("Invalid PNG image dimensions")
        # Unknown critical chunks are unsafe to drop: reject instead.
        if chunk_type not in PASS_CHUNKS and (chunk_type[0] & 32) == 0:
            raise BlindBundleError("Unknown critical PNG chunk")
        if chunk_type in PASS_CHUNKS:
            out.extend(content[pos:pos + 12 + length])
        types.append(chunk_type)
        pos += 12 + length
        if chunk_type == b"IEND":
            if length or pos != len(content):
                raise BlindBundleError("Invalid PNG terminator or trailing content")
            break
    if not types or types[-1] != b"IEND" or b"IDAT" not in types:
        raise BlindBundleError("Incomplete PNG image")
    return bytes(out)


def input_file(source: Path, relative: str) -> Path:
    p = source / relative
    # Reject even intermediate symlinks in the source path hierarchy.
    if not p.is_file() or p.is_symlink() or any(parent.is_symlink() for parent in p.parents if inside(parent, source)):
        raise BlindBundleError(f"Missing file or unsafe symlink: {relative}")
    if not inside(p, source):
        raise BlindBundleError(f"Escaping path: {relative}")
    return p


def _write_clean_image(source: Path, relative: str, out: Path) -> None:
    raw = input_file(source, relative).read_bytes()
    clean = png_clean_bytes(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(clean)


def build(source: Path, destination: Path, labels: list[str], mode: str = "geometry") -> dict:
    labels = validate_labels(labels)
    source, destination = source.resolve(), destination.resolve()
    no_overlaps(source, destination)
    if not source.is_dir() or source.is_symlink():
        raise BlindBundleError("Private source bundle does not exist")
    if destination.exists() or destination.is_symlink():
        raise BlindBundleError("Destination already exists; use a fresh judge run ID")
    files = required_candidate_files(mode)
    # Check all inputs BEFORE creating any output folder.
    for relative in (f"references/{name}" for name in REFERENCES):
        input_file(source, relative)
    for label in labels:
        for name in files:
            input_file(source, f"{label}/{name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=str(destination.parent)))
    try:
        (temp / "RUBRIC.md").write_text(RUBRIC, encoding="utf-8")
        for name in REFERENCES:
            _write_clean_image(source, f"references/{name}", temp / "references" / name)
        for label in labels:
            for name in sorted(files):
                _write_clean_image(source, f"{label}/{name}", temp / label / name)
        check = verify(temp, list(labels), mode)
        # No name, backend mapping, prior verdict or source report copied.
        temp.rename(destination)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return {**check, "judge_bundle": str(destination)}


def verify(bundle: Path, labels: list[str], mode: str = "geometry") -> dict:
    labels = validate_labels(labels)
    bundle = bundle.resolve()
    if not bundle.is_dir() or bundle.is_symlink():
        raise BlindBundleError("Judge bundle directory missing or symlinked")
    allowed = {"RUBRIC.md", *(f"references/{name}" for name in REFERENCES)}
    files = required_candidate_files(mode)
    for label in labels:
        allowed.update(f"{label}/{name}" for name in files)
    actual = set()
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise BlindBundleError("Symbolic link in judge bundle")
        if path.is_file():
            relative = path.relative_to(bundle).as_posix()
            actual.add(relative)
            if relative.endswith(".png"):
                content = path.read_bytes()
                if png_clean_bytes(content) != content:
                    raise BlindBundleError(f"Metadata-bearing image must be scrubbed: {relative}")
            elif relative == "RUBRIC.md":
                if path.read_text(encoding="utf-8") != RUBRIC:
                    raise BlindBundleError("Reviewer instructions differ from vetted rubric")
            else:
                raise BlindBundleError(f"Prohibited judge file: {relative}")
        elif not path.is_dir():
            raise BlindBundleError("Unsupported filesystem entry in judge bundle")
    missing, extra = allowed - actual, actual - allowed
    if missing or extra:
        raise BlindBundleError(f"Bundle contract violation; missing={sorted(missing)}, extra={sorted(extra)}")
    return {"status": "SAFE_TO_JUDGE_ONLY", "mode": mode, "labels": list(labels),
            "review_files": len(actual), "geometry_accepted": False,
            "note": "Blinding preflight only; negative controls and geometry QA still required"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    for action in ("build", "verify"):
        p = sub.add_parser(action)
        p.add_argument("--labels", nargs="+", required=True)
        p.add_argument("--mode", choices=("geometry", "appearance-diagnostic"), default="geometry")
        if action == "build":
            p.add_argument("--source", required=True, type=Path)
            p.add_argument("--out", required=True, type=Path)
        else:
            p.add_argument("--bundle", required=True, type=Path)
            p.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.action == "build":
            result = build(args.source, args.out, args.labels, args.mode)
        else:
            if args.report and inside(args.report, args.bundle):
                raise BlindBundleError("Review report cannot be written inside judge input")
            result = verify(args.bundle, args.labels, args.mode)
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, UnicodeError, BlindBundleError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())