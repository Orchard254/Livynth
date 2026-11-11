"""C001-GEO-04 gate - reference-side evidence.

Everything the gate knows about the reference subject is derived here, from
the photographs themselves plus the manual landmark annotation that already
exists in the repository.  No photo-trained face detector is used: the gate
must not be able to "see" the reference's photographic cues.

Measured reference quantities
-----------------------------
* head silhouette per view (foreground vs the studio backdrop)
* the head band: rows from the top of the subject down to the last row whose
  width is at least 55 percent of the maximum width.  The SAME rule is
  applied to the candidate clay renders, so the two are comparable.
* head width profile W(v) - the horizontal extent of the silhouette per row
* the face band span: the lateral extent of SKIN inside a rectangle around
  the eye landmarks.  This is the reference-side counterpart of the
  candidate-side band geometry measured on the mesh.
* the luminance detail profile of the face region, used as the
  photographic-shading estimate of facial relief

ASSUMPTIONS
-----------
A1. The photographs are AI-generated, uncalibrated, with no EXIF.
A2. The studio backdrop is a near-uniform grey; the subject is separated from
    it by colour distance.  A segmentation overlay PNG is written for every
    run so the assumption can be inspected.
A3. The manual landmark annotation is approximate; it is used for ratios and
    band placement only, never as ground truth.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

GATE_DIR = Path(__file__).resolve().parent
VIEW_JSON = GATE_DIR / "reference_views.json"
HEAD_BAND_FRACTION = 0.62


def load_rgb(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im, dtype=np.float64) / 255.0


def luminance(rgb):
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def foreground_mask(rgb, tol=0.06):
    border = np.concatenate([
        rgb[:12].reshape(-1, 3), rgb[-12:].reshape(-1, 3),
        rgb[:, :12].reshape(-1, 3), rgb[:, -12:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.linalg.norm(rgb - bg[None, None, :], axis=2)
    mask = dist > tol
    mask = ndimage.binary_closing(mask, structure=np.ones((7, 7)))
    mask = ndimage.binary_fill_holes(mask)
    lab, n = ndimage.label(mask)
    if n > 1:
        sizes = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
        mask = lab == (int(np.argmax(sizes)) + 1)
        mask = ndimage.binary_fill_holes(mask)
    return mask, bg


def width_profile(mask):
    any_row = mask.any(axis=1)
    prof = np.zeros(mask.shape[0], dtype=np.float64)
    idx = np.nonzero(any_row)[0]
    if len(idx) == 0:
        return prof
    sub = mask[idx]
    left = np.argmax(sub, axis=1)
    right = sub.shape[1] - 1 - np.argmax(sub[:, ::-1], axis=1)
    prof[idx] = right - left + 1
    return prof


def head_band(mask, fraction=HEAD_BAND_FRACTION):
    """Rows from the top of the subject down to the chin (neck cut).

    The head is the WIDE upper part of the silhouette; the neck is a narrow
    waist and the shoulders are a second, lower wide part.  The maximum
    width is therefore taken from the UPPER 60 percent of the subject only,
    and the band ends at the last row that is still at least
    HEAD_BAND_FRACTION of that maximum.  The identical rule is applied to
    the candidate clay renders, so the two sides are comparable even though
    the photograph contains shoulders and the render usually does not.
    """
    prof = width_profile(mask)
    rows = np.nonzero(prof > 0)[0]
    if len(rows) == 0:
        return None
    top = int(rows.min())
    last = int(rows.max())
    upper_end = top + int(0.60 * (last - top))
    upper = prof[top:max(upper_end, top + 1)]
    head_max = float(upper.max())
    if head_max <= 0:
        return None
    wide = np.nonzero(prof[:last + 1] >= fraction * head_max)[0]
    bottom = int(wide.max()) if len(wide) else last
    return (top, bottom)


def band_widths(mask, band):
    prof = width_profile(mask)
    return prof[band[0]:band[1] + 1]


def head_metrics(mask, band):
    prof = width_profile(mask)
    if band is None:
        return {"measurable": False}
    seg = prof[band[0]:band[1] + 1]
    if len(seg) == 0 or seg.max() <= 0:
        return {"measurable": False}
    wmax = float(seg.max())
    rows = np.nonzero(seg > 0)[0]
    wprof = prof
    left = np.full(len(prof), np.nan)
    right = np.full(len(prof), np.nan)
    idx = np.nonzero(prof > 0)[0]
    sub = mask[idx]
    left[idx] = np.argmax(sub, axis=1)
    right[idx] = sub.shape[1] - 1 - np.argmax(sub[:, ::-1], axis=1)
    return {
        "measurable": True,
        "head_width_px": wmax,
        "head_height_px": float(band[1] - band[0] + 1),
        "aspect": float(band[1] - band[0] + 1) / wmax,
        "band_rows": [int(band[0]), int(band[1])],
        "centre_u_px": float((left[idx].min() + right[idx].max()) / 2.0),
        "centre_v_px": float((band[0] + band[1]) / 2.0),
        "width_profile": wprof,
        "left_edge": left,
        "right_edge": right,
    }


def otsu(values):
    values = np.asarray(values, dtype=np.float64).ravel()
    if values.size == 0:
        return 0.0
    if values.max() == values.min():
        return float(values.mean())
    hist, edges = np.histogram(values, bins=64)
    centres = (edges[:-1] + edges[1:]) / 2.0
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centres)
    total = m0[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        mu0 = m0 / w0
        mu1 = (total - m0) / w1
        var_between = w0 * w1 * (mu0 - mu1) ** 2
    var_between[~np.isfinite(var_between)] = 0.0
    return float(centres[int(np.argmax(var_between))])


def skin_span(rgb, rect):
    """Lateral extent of SKIN inside a pixel rectangle."""
    x0, y0, x1, y1 = [int(v) for v in rect]
    h, w = rgb.shape[:2]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(w - 1, x1)
    y1 = min(h - 1, y1)
    patch = rgb[y0:y1 + 1, x0:x1 + 1]
    if patch.size == 0:
        return None
    lum = luminance(patch)
    thr = otsu(lum)
    bright = lum > thr
    if not bright.any():
        return None
    cols = np.nonzero(bright.any(axis=0))[0]
    if len(cols) == 0:
        return None
    return {"rect": [x0, y0, x1, y1], "otsu_threshold": float(thr),
            "x_min": int(x0 + cols.min()), "x_max": int(x0 + cols.max()),
            "span_px": int(cols.max() - cols.min() + 1)}


def band_pass(patch, kernel=121):
    low = ndimage.uniform_filter(patch, size=kernel, mode="nearest")
    return patch - low


def face_detail(rgb, rect, kernel=121):
    x0, y0, x1, y1 = [int(v) for v in rect]
    lum = luminance(rgb)
    patch = lum[y0:y1 + 1, x0:x1 + 1]
    if patch.size == 0:
        return None
    return {"rect": [x0, y0, x1, y1], "detail": band_pass(patch, kernel)}


def eye_band_rect(landmarks, pad_x=0.30, pad_y=0.30):
    le = landmarks["eyes"]["left"]
    re = landmarks["eyes"]["right"]
    ipd = abs(re[0] - le[0])
    yc = 0.5 * (le[1] + re[1])
    return (int(min(le[0], re[0]) - pad_x * ipd),
            int(yc - pad_y * ipd),
            int(max(le[0], re[0]) + pad_x * ipd),
            int(yc + pad_y * ipd))


def mouth_band_rect(landmarks, pad_x=0.30, pad_y=0.30):
    (lx, ly), (rx, ry) = landmarks["mouth_corners"]
    w = abs(rx - lx)
    yc = 0.5 * (ly + ry)
    return (int(min(lx, rx) - pad_x * w),
            int(yc - pad_y * w),
            int(max(lx, rx) + pad_x * w),
            int(yc + pad_y * w))


def load_reference(view_names=("front", "left45", "right45", "left90", "right90")):
    cfg = json.loads(VIEW_JSON.read_text(encoding="utf-8"))
    ref_dir = Path(cfg["reference_dir"])
    out = {"config": cfg, "views": {}}
    bands = {}
    front_head_h = None
    for name, v in cfg["views"].items():
        crown = v.get("crown_row")
        chin = v.get("chin_row")
        if crown is None:
            continue
        if chin is None:
            if front_head_h is None:
                f = cfg["views"]["front"]
                front_head_h = (f["chin_row"] - f["crown_row"]) * (v["s"] / cfg["views"]["front"]["s"])
            chin = int(round(crown + front_head_h))
        bands[name] = (int(crown), int(chin))
    out["bands"] = bands
    for name in view_names:
        v = cfg["views"][name]
        rgb = load_rgb(ref_dir / v["file"])
        fg, bg = foreground_mask(rgb)
        band = out["bands"].get(name)
        met = head_metrics(fg, band)
        out["views"][name] = {
            "file": v["file"],
            "rgb": rgb,
            "foreground": fg,
            "band": band,
            "metrics": {k: val for k, val in met.items()
                        if k not in ("width_profile", "left_edge", "right_edge")},
            "width_profile": met.get("width_profile"),
            "reference_camera": {
                "phi": float(v["phi"]),
                "s_px_per_m": float(v["s"]),
                "head_width_px": float(met.get("head_width_px", 0.0)),
                "centre_u_px": float(met.get("centre_u_px", 0.0)),
                "centre_v_px": float(met.get("centre_v_px", 0.0)),
            },
        }
    lm = cfg["reference_landmarks_front_px"]
    out["landmarks"] = {
        "eyes": lm["eyes"],
        "chin": lm["chin"],
        "mouth_corners": lm["mouth_corners"],
        "ipd_px": abs(lm["eyes"]["right"][0] - lm["eyes"]["left"][0]),
        "eye_row": 0.5 * (lm["eyes"]["left"][1] + lm["eyes"]["right"][1]),
        "mouth_row": 0.5 * (lm["mouth_corners"][0][1] + lm["mouth_corners"][1][1]),
        "chin_row": lm["chin"][1],
        "mouth_width_px": abs(lm["mouth_corners"][1][0] - lm["mouth_corners"][0][0]),
    }
    out["landmarks"]["mouth_width_px"] = abs(
        lm["mouth_corners"][1][0] - lm["mouth_corners"][0][0])
    out["eye_band_rect"] = eye_band_rect(lm)
    out["mouth_band_rect"] = mouth_band_rect(lm)
    front = out["views"]["front"]
    out["reference_face_band"] = {
        "eye": skin_span(front["rgb"], out["eye_band_rect"]),
        "mouth": skin_span(front["rgb"], out["mouth_band_rect"]),
    }
    out["reference_face_detail"] = face_detail(front["rgb"], out["eye_band_rect"])
    return out
