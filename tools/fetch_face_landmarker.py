#!/usr/bin/env python3
"""Fetch the MediaPipe FaceLandmarker model bundle used by `geo/detect_landmarks.py`.

The bundle is an upstream artefact, not project source, so it is excluded from
Git (see `.gitignore`: `models/`, `*.task`) and re-fetched from a pinned URL.
Pinning the SHA-256 means a corrupted or substituted download fails loudly
instead of silently changing every landmark measurement.

Usage:
    python tools/fetch_face_landmarker.py                 # fetch into ./models
    python tools/fetch_face_landmarker.py --dest <dir>   # fetch elsewhere
    python tools/fetch_face_landmarker.py --verify-only   # check an existing copy

Model: MediaPipe FaceLandmarker, float16, task bundle 1.
Licence: Apache License 2.0 (the MediaPipe model card lists the models as
Apache-2.0). See https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
       "face_landmarker/float16/1/face_landmarker.task")
SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
SIZE_BYTES = 3758596
FILENAME = "face_landmarker.task"
ROOT = Path(__file__).resolve().parents[1]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default=str(ROOT / "models"),
                    help="destination directory (default: <repo>/models)")
    ap.add_argument("--verify-only", action="store_true",
                    help="only verify an existing file; never download")
    args = ap.parse_args(argv)

    dest = Path(args.dest)
    target = dest / FILENAME

    if args.verify_only:
        if not target.is_file():
            print(f"missing: {target}", file=sys.stderr)
            return 2
        digest = sha256_of(target)
        ok = digest == SHA256
        print(f"{target}: sha256={digest} expected={SHA256} -> {'OK' if ok else 'MISMATCH'}")
        return 0 if ok else 1

    if target.is_file():
        digest = sha256_of(target)
        if digest == SHA256:
            print(f"already present and verified: {target}")
            return 0
        print(f"present but hash mismatch ({digest}); re-downloading", file=sys.stderr)
        target.unlink()

    dest.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    tmp = target.with_suffix(".part")
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, tmp.open("wb") as out:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as error:  # noqa: BLE001 - report any transport failure clearly
        print(f"download failed: {error}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return 1

    digest = sha256_of(tmp)
    if digest != SHA256:
        print(f"hash mismatch: got {digest}, expected {SHA256}; discarding", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return 1
    size = tmp.stat().st_size
    tmp.replace(target)
    print(f"wrote {target} ({size} bytes, sha256 verified)")
    if size != SIZE_BYTES:
        print(f"note: size {size} differs from the recorded {SIZE_BYTES} but the hash matched",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
