#!/usr/bin/env python3
"""C001-GEO-01: coarse silhouette-volume constraint from AI identity references.

NOT a face scan, a likeness solution, or production-ready expression topology.
Retopologize and fit a facial base mesh after studying the image-derived envelope.

Dependencies: numpy, Pillow, trimesh (see requirements-geometry.txt).
Usage:
  python -m geo.proxy_fit --images assets/characters/character_001/identity_capture_v1 \
       --out output/character001_geo01
"""
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Crown/chin and ear pixel positions were annotated on the *original* captures.
# Do not use with resized/reframed images without recalibrating these anchors.
VIEWS = {
    "front": ("01_subject_front.png", 55, 924, None),
    "left": ("04_left_profile.png", 40, 980, 627),
    "right": ("05_right_profile.png", 34, 940, 425),
}
FRAMES = ("02_subject_left_45.png", "03_subject_right_45.png", "06_back_head.png")


@dataclass(frozen=True)
class Profile:
    name: str
    image: Path
    width: int
    height: int
    crown: int
    chin: int
    uleft: np.ndarray
    uright: np.ndarray
    sha256: str


def median_smooth(arr: np.ndarray, width: int) -> np.ndarray:
    if width % 2 != 1 or width < 1:
        raise ValueError("Median filter width must be odd and positive")
    k = width // 2
    padded = np.pad(arr, (k, k), mode="edge")
    return np.array([np.median(padded[i:i + width]) for i in range(len(arr))])


def read_profile(image: Path, label: str, crown: int, chin: int,
                 steps: int = 73) -> Profile:
    """Return foreground bounds at normalized crown-to-chin heights."""
    if not image.is_file():
        raise FileNotFoundError(image)
    rgb = np.asarray(Image.open(image).convert("RGB"), dtype=np.float32)
    h, w, _ = rgb.shape
    if not (0 <= crown < chin < h):
        raise ValueError(f"Invalid crown/chin anchors for {image.name}")
    if min(w, h) < 600:
        raise ValueError(f"Reference looks like thumbnail: {image.name} {w}x{h}")
    if steps < 20:
        raise ValueError("Need >= 20 silhouette samples")
    border = max(15, w // 16)
    bg = np.median(np.concatenate([rgb[:, :border], rgb[:, -border:]], axis=1), axis=1)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    distance = np.max(np.abs(rgb - bg[:, None, :]), axis=2)
    fg = ((distance > 26) & (chroma > 12)) | (distance > 54)
    t = np.linspace(.025, .965, steps)
    lower, upper = [], []
    for f in t:
        yy = int(round(crown + f * (chin - crown)))
        band = fg[max(0, yy - 2):min(h, yy + 3)].sum(axis=0)
        hits = np.flatnonzero(band >= 2)
        if len(hits) < 22:
            raise ValueError(f"Cannot segment {image.name} at normalized height {f:.3f}")
        lower.append(np.quantile(hits, .01))
        upper.append(np.quantile(hits, .99))
    lower = median_smooth(np.asarray(lower), width=5)
    upper = median_smooth(np.asarray(upper), width=5)
    if np.any((upper - lower) < 10):
        raise ValueError(f"Degenerate silhouette from {image.name}")
    scale = float(chin - crown)
    return Profile(label, image, w, h, crown, chin, lower / scale,
                   upper / scale, hashlib.sha256(image.read_bytes()).hexdigest())


def mesh_from_profiles(front: Profile, left: Profile, right: Profile,
                       head_height_m: float = .245, sides: int = 72):
    """Create a watertight *envelope*; never use as animatable facial topology.

    Dimensions are illustrative. The source views were AI-generated and their
    cameras were not calibrated. Geometry includes hair and cannot solve eyes,
    nostrils, mouth, eyelids, ears, or facial identity.
    """
    if sides < 12 or sides % 4:
        raise ValueError("sides must be divisible by 4 and >= 12")
    if not .16 <= head_height_m <= .34:
        raise ValueError("Illustrative head height must be 0.16–0.34 m")
    n = len(front.uleft)
    if len(left.uleft) != n or len(right.uleft) != n:
        raise ValueError("Silhouette sample counts differ")
    left_depth = left.uright - left.uleft
    right_depth = right.uright - right.uleft
    left_ear = VIEWS["left"][3] / float(left.chin - left.crown)
    right_ear = VIEWS["right"][3] / float(right.chin - right.crown)
    forward = np.maximum(0., ((left_ear - left.uleft) +
                              (right.uright - right_ear)) * .5 * head_height_m)
    rear = np.minimum(0., ((left_ear - left.uright) +
                           (right.uleft - right_ear)) * .5 * head_height_m)
    half_width = np.maximum((front.uright - front.uleft) * .5 * head_height_m, .006)
    t = np.linspace(.025, .965, n)
    vertices = []
    for k, f in enumerate(t):
        z = (1 - f) * head_height_m
        # Lower source silhouette includes neck; approximate tapered chin.
        taper = float(np.clip((f - .86) / .14, 0, 1))
        taper = taper * taper * (3 - 2 * taper)
        xx = float(half_width[k] * (1 - .60 * taper))
        yfront = float(forward[k] * (1 - .20 * taper))
        yrear = float(rear[k] * (1 - .20 * taper))
        for j in range(sides):
            theta = 2 * np.pi * j / sides
            sn = np.sin(theta)
            y = yfront * (sn ** 2.3) if sn >= 0 else yrear * (-sn)
            vertices.append((float(xx * np.cos(theta)), float(y), float(z)))
    top = len(vertices)
    vertices.append((0, 0, head_height_m))
    bottom = len(vertices)
    vertices.append((0, 0, 0))
    faces = []
    for row in range(n - 1):
        for j in range(sides):
            a = row * sides + j
            b = row * sides + (j + 1) % sides
            c = (row + 1) * sides + j
            d = (row + 1) * sides + (j + 1) % sides
            faces.extend(((a, b, c), (b, d, c)))
    for j in range(sides):
        faces.append((top, j, (j + 1) % sides))
        a = (n - 1) * sides + j
        b = (n - 1) * sides + (j + 1) % sides
        faces.append((bottom, b, a))
    mismatch = np.abs(left_depth - right_depth) / np.maximum(
        (left_depth + right_depth) * .5, 1e-6)
    metrics = {
        "head_height_m_illustrative": round(head_height_m, 5),
        "max_front_span_to_height_ratio": round(
            float(np.max(2 * half_width) / head_height_m), 4),
        "max_mean_profile_span_to_height_ratio": round(
            float(np.max(forward - rear) / head_height_m), 4),
        "median_LR_profile_depth_disagreement_fraction": round(
            float(np.median(mismatch)), 4),
        "p90_LR_profile_depth_disagreement_fraction": round(
            float(np.quantile(mismatch, .9)), 4),
        "number_of_vertical_samples": n,
        "ear_depth_anchors_pixels": {"left": VIEWS["left"][3],
                                      "right": VIEWS["right"][3]},
        "radial_segments": sides,
        "vertices": len(vertices),
        "triangles": len(faces),
        "interpretation": "AI-generated uncalibrated multi-view, silhouette/hair volume only. NOT animation-ready.",
    }
    return np.asarray(vertices, np.float32), np.asarray(faces, np.int64), metrics


def overlays(profiles: dict, out_dir: Path):
    """Save image-space silhouettes used as coarse geometric constraints."""
    for key in ("front", "left", "right"):
        profile = profiles[key]
        im = Image.open(profile.image).convert("RGB")
        draw = ImageDraw.Draw(im)
        ts = np.linspace(.025, .965, len(profile.uleft))
        scale = profile.chin - profile.crown
        a = [(float(profile.uleft[i] * scale),
              float(profile.crown + ts[i] * scale)) for i in range(len(ts))]
        b = [(float(profile.uright[i] * scale),
              float(profile.crown + ts[i] * scale)) for i in range(len(ts))]
        draw.line(a, fill=(255, 230, 0), width=4)
        draw.line(b, fill=(0, 230, 255), width=4)
        draw.text((12, 18), f"{key.upper()} / geometry constraints only",
                  fill=(255, 255, 255))
        im.save(out_dir / f"{key}_silhouette_overlay.png", optimize=True)


def run(image_dir: Path, out_dir: Path):
    import trimesh
    profiles = {}
    for label, (filename, crown, chin, _ear) in VIEWS.items():
        profile = read_profile(image_dir / filename, label, crown, chin)
        if (profile.width, profile.height) != (1086, 1448):
            raise ValueError(f"{filename} changed dimensions; re-annotate anchors")
        profiles[label] = profile
    for filename in FRAMES:
        if not (image_dir / filename).is_file():
            raise FileNotFoundError(image_dir / filename)
    vertices, faces, metrics = mesh_from_profiles(
        profiles["front"], profiles["left"], profiles["right"])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.fix_normals()
    if not mesh.is_watertight:
        raise RuntimeError("Proxy topology is not watertight")
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh.export(out_dir / "character001_silhouette_proxy.glb")
    mesh.export(out_dir / "character001_silhouette_proxy.obj")
    overlays(profiles, out_dir)
    manifest = {
        "schema": "livynth.character001.proxy.v1",
        "status": "diagnostic-only; not a face or validated likeness",
        "sources": {
            name: {"file": p.image.name, "sha256": p.sha256,
                   "px": [p.width, p.height], "crown_y_px": p.crown,
                   "chin_y_px": p.chin}
            for name, p in profiles.items()},
        "metrics": metrics,
        "glb_file": "character001_silhouette_proxy.glb",
        "known_limitations": [
            "AI-generated, uncalibrated cameras and independent images",
            "No face features or animation-friendly topology; includes hair",
            "Not a UV texture, final head or identity likeness",
            "Absolute dimensions are illustrative, not measured"],
        "next": "Fit morph-capable anatomical head against front/profile references",
    }
    (out_dir / "fit_report.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf8")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", required=True, type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("output/character001_geo01"))
    args = p.parse_args()
    result = run(args.images, args.out)
    print(json.dumps(result["metrics"], indent=2))
    print("[C001-GEO-01] Diagnostic outputs:", args.out.resolve())


if __name__ == "__main__":
    main()
