"""Fail-closed readability preflight for LIVYNTH wireframe review evidence.

This checks *only* legibility of the evidence image, NOT identity, anatomy,
geometric correctness, or acceptance. Synthetic fixture thresholds require a
real Blender render smoke before any geometry gate uses them for signoff.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def audit_wireframe(path: str | Path) -> dict:
    try:
        with Image.open(path) as source:
            rgba = np.asarray(source.convert("RGBA"), dtype=np.uint8)
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": ["image_unreadable"], "detail": str(exc)}
    if rgba.ndim != 3 or rgba.shape[0] < 16 or rgba.shape[1] < 16:
        return {"ok": False, "errors": ["image_too_small"]}
    rgb = rgba[..., :3].astype(np.float32) / 255.
    alpha = rgba[..., 3]
    lum = .2126 * rgb[..., 0] + .7152 * rgb[..., 1] + .0722 * rgb[..., 2]
    opaque_fraction = float(np.mean(alpha >= 250))
    light_fraction = float(np.mean(lum >= .55))
    dark_fraction = float(np.mean(lum <= .20))
    contrast = float(np.quantile(lum, .999) - np.quantile(lum, .001))
    errors = []
    if opaque_fraction < .99:
        errors.append("transparent_or_missing_backdrop")
    if light_fraction < .10:
        errors.append("no_light_backdrop")
    if dark_fraction < .002:
        errors.append("no_visible_dark_wire_edges")
    if contrast < .35:
        errors.append("low_contrast")
    return {
        "ok": not errors,
        "errors": errors,
        "opaque_fraction": round(opaque_fraction, 6),
        "light_fraction": round(light_fraction, 6),
        "dark_fraction": round(dark_fraction, 6),
        "contrast": round(contrast, 6),
        "resolution_px": [int(rgba.shape[1]), int(rgba.shape[0])],
    }
