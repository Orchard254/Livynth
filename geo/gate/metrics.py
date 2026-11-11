"""C001-GEO-04 gate - the metrics.

Every metric here is computed from CLAY renders, DEPTH maps, NORMAL maps or
the candidate MESH.  None of them reads the candidate's texture.  The two
appearance metrics are computed as well, but they are DIAGNOSTIC ONLY: they
are the kind of metric that the previous protocol trusted, and they are kept
so that the report can show, side by side, an appearance metric that stays
satisfied while a geometry metric rejects the same candidate.

Metric tolerances
-----------------
TOLERANCES is the single source of truth for how much a metric may move
before it counts as a change.  The same numbers are used for the absolute
comparison against the reference and for the control rejection rule.

A control is REJECTED when at least one metric moves by more than its
tolerance relative to the unmodified baseline candidate.  A gate that fails
to reject a control is not a gate: the run then reports gate_valid False.
"""

import numpy as np
import trimesh
from scipy import ndimage

from . import reference as refmod
from .camera import project_point
from .controls import in_rect

TOLERANCES = {
    "silhouette_face_band_ratio": 0.08,
    "profile_depth_width_ratio": 0.15,
    "relief_shading_correlation": 0.15,
    "band_spread_ratio": 0.10,
    "surface_roughness_rel": 0.50,
    "depth_symmetry": 0.05,
    "appearance_silhouette_iou": 0.05,
    "appearance_ncc": 0.05,
}

LIMITS = {
    "surface_roughness_rel": 0.50,
    "depth_symmetry": 0.05,
}

DIRECTION = {
    "relief_shading_correlation": "min",
}


def _rel(a, b):
    if a is None or b is None:
        return None
    den = abs(b)
    if den < 1e-12:
        return None
    return float((a - b) / den)


def silhouette_face_band_ratio(prof, band, face_rows):
    seg = prof[band[0]:band[1] + 1]
    if len(seg) == 0 or seg.max() <= 0:
        return None
    rows = [r for r in face_rows if band[0] <= r <= band[1]]
    if not rows:
        return None
    vals = prof[rows]
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(np.median(vals) / seg.max())


def _profile_depth_ratio(ref, calib, renders, view_names):
    if "front" not in renders:
        return None, None
    front_c = renders["front"]["mask"]
    band_c = ref["bands"]["front"]
    prof_c = refmod.width_profile(front_c)
    w_front_c = float(prof_c[band_c[0]:band_c[1] + 1].max())
    s_front_c = calib["views"]["front"]["s"]
    front_m = w_front_c / s_front_c
    prof_side = None
    for name in ("left90", "right90"):
        if name in renders:
            m = renders[name]["mask"]
            b = ref["bands"][name]
            p = refmod.width_profile(m)
            prof_side = float(p[b[0]:b[1] + 1].max()) / calib["views"][name]["s"]
    if prof_side is None or front_m <= 0:
        return None, None
    cand = prof_side / front_m

    rf = ref["views"]["front"]
    front_m_ref = float(rf["metrics"]["head_width_px"]) / rf["reference_camera"]["s_px_per_m"]
    prof_ref = None
    for name in ("left90", "right90"):
        if name in ref["views"]:
            m = float(ref["views"][name]["metrics"]["head_width_px"]) / \
                ref["views"][name]["reference_camera"]["s_px_per_m"]
            prof_ref = m if prof_ref is None else (prof_ref + m) / 2.0
    if prof_ref is None or front_m_ref <= 0:
        return None, None
    return float(cand), float(prof_ref / front_m_ref)


def _band_pass(patch, kernel=121):
    return patch - ndimage.uniform_filter(patch, size=kernel, mode="nearest")


def relief_shading_correlation(ref, renders, rect, max_shift=24):
    """Correlation between the candidate's geometric relief and the
    reference photograph's photographic shading (a PLAUSIBILITY gate)."""
    if "front" not in renders:
        return None, None
    detail = ref.get("reference_face_detail")
    if detail is None:
        return None, None
    x0, y0, x1, y1 = detail["rect"]
    depth = renders["front"]["depth"]
    h, w = depth.shape
    x1 = min(x1, w - 1)
    y1 = min(y1, h - 1)
    if x1 <= x0 or y1 <= y0:
        return None, None
    rd = detail["detail"]
    best = None
    best_shift = None
    relief_full = -depth
    for dy in range(-max_shift, max_shift + 1, 4):
        for dx in range(-max_shift, max_shift + 1, 4):
            ys = slice(max(0, y0 + dy), min(h, y1 + dy + 1))
            xs = slice(max(0, x0 + dx), min(w, x1 + dx + 1))
            ys0 = max(0, -dy)
            xs0 = max(0, -dx)
            r = rd[ys0:ys0 + (ys.stop - ys.start), xs0:xs0 + (xs.stop - xs.start)]
            g = relief_full[ys, xs]
            if r.shape != g.shape or r.size < 100:
                continue
            ok = np.isfinite(g)
            if ok.sum() < 100:
                continue
            a = r[ok].ravel()
            b = g[ok].ravel()
            if np.std(a) < 1e-9 or np.std(b) < 1e-9:
                continue
            c = float(np.corrcoef(a, b)[0, 1])
            if best is None or abs(c) > abs(best):
                best = c
                best_shift = (dx, dy)
    return best, best_shift


def band_spread_ratio(cand, calib, renders, rects, band):
    """Lateral spread of the surface the reference eye band designates."""
    if "front" not in renders:
        return None, None, None
    view = calib["views"]["front"]
    u = []
    v = []
    for p in cand["verts"]:
        a, b = project_point(p, view)
        u.append(a)
        v.append(b)
    u = np.asarray(u)
    v = np.asarray(v)
    out = {}
    for key in ("eye", "mouth"):
        sel = in_rect(u, v, rects[key])
        if sel.sum() < 10:
            out[key] = None
            continue
        out[key] = float(u[sel].max() - u[sel].min())
    mask = renders["front"]["mask"]
    prof = refmod.width_profile(mask)
    head_w = float(prof[band[0]:band[1] + 1].max())
    ratio = None
    if out.get("eye") is not None and head_w > 0:
        ratio = out["eye"] / head_w
    return ratio, out, head_w


def surface_roughness(cand):
    """Laplacian RMS of the surface, relative to the median edge length.

    For a smooth head surface the residual of every vertex against the mean
    of its one-ring neighbours is small compared with the edge length.  A
    jitter canary adds noise of a fixed amplitude to every vertex, which
    shows up directly in this residual.
    """
    import scipy.sparse as sparse
    mesh = trimesh.Trimesh(vertices=cand["verts"], faces=cand["faces"], process=False)
    V = np.asarray(mesh.vertices, dtype=np.float64)
    n = len(V)
    rows = []
    cols = []
    for i, arr in enumerate(mesh.vertex_neighbors):
        for j in np.asarray(arr, dtype=np.int64).ravel():
            rows.append(i)
            cols.append(int(j))
    if rows:
        A = sparse.coo_matrix((np.ones(len(rows)), (rows, cols)),
                              shape=(n, n)).tocsr()
        deg = np.asarray(A.sum(axis=1)).ravel()
        deg[deg == 0] = 1.0
        lap = V - (A @ V) / deg[:, None]
    else:
        lap = np.zeros_like(V)
    rms = float(np.sqrt(np.mean(np.sum(lap ** 2, axis=1)))) if n else None
    edges = mesh.edges_unique
    med_edge = float(np.median(np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1))) if len(edges) else None
    return {"laplacian_rms_m": rms, "median_edge_length_m": med_edge,
            "relative": (rms / med_edge) if (rms and med_edge) else None}


def depth_symmetry(renders, calib, face_rows):
    """Left/right symmetry of the front depth profile."""
    if "front" not in renders:
        return None
    depth = renders["front"]["depth"]
    mask = renders["front"]["mask"]
    rows = [r for r in face_rows if 0 <= r < depth.shape[0]]
    if not rows:
        return None
    prof = []
    for r in rows:
        seg = depth[r]
        m = mask[r]
        if m.any():
            prof.append(np.where(m, -seg, np.nan))
    if not prof:
        return None
    arr = np.vstack(prof)
    with np.errstate(invalid="ignore"):
        p = np.nanmax(arr, axis=0)
    valid = np.isfinite(p)
    if valid.sum() < 10:
        return None
    idx = np.nonzero(valid)[0]
    centre = (idx.min() + idx.max()) / 2.0
    mirror = np.interp(2 * centre - idx, idx, p[idx])
    diff = np.abs(p[idx] - mirror)
    span = float(np.nanmax(p) - np.nanmin(p))
    if span <= 0:
        return None
    return float(np.mean(diff) / span)


def appearance_metrics(ref, renders, ref_rect):
    """DIAGNOSTIC ONLY.  The kind of metric the previous protocol used."""
    out = {}
    if "front" not in renders:
        return out
    band = ref["bands"]["front"]
    rfg = ref["views"]["front"]["foreground"].copy()
    rfg[:band[0]] = False
    rfg[band[1] + 1:] = False
    x0, y0, x1, y1 = ref_rect
    cm = renders["front"]["mask"].copy()
    cm[:band[0]] = False
    cm[band[1] + 1:] = False
    h = min(rfg.shape[0], cm.shape[0])
    w = min(rfg.shape[1], cm.shape[1])
    a = rfg[:h, :w]
    b = cm[:h, :w]
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    out["appearance_silhouette_iou"] = float(inter) / float(union) if union else None
    lum_ref = refmod.luminance(ref["views"]["front"]["rgb"])[:h, :w]
    return out


def appearance_ncc(ref, textured_rgb, rect):
    """DIAGNOSTIC ONLY: normalised cross correlation of the FACE CROPS."""
    if textured_rgb is None:
        return None
    x0, y0, x1, y1 = rect
    lum_ref = refmod.luminance(ref["views"]["front"]["rgb"])
    lum_cand = refmod.luminance(textured_rgb)
    h = min(lum_ref.shape[0], lum_cand.shape[0])
    w = min(lum_ref.shape[1], lum_cand.shape[1])
    x1 = min(x1, w - 1)
    y1 = min(y1, h - 1)
    if x1 <= x0 or y1 <= y0:
        return None
    a = lum_ref[y0:y1 + 1, x0:x1 + 1].ravel()
    b = lum_cand[y0:y1 + 1, x0:x1 + 1].ravel()
    if a.std() < 1e-9 or b.std() < 1e-9:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def compute_all(cand, ref, calib, renders, rects, textured_rgb=None):
    """All metrics for one candidate."""
    lm = ref["landmarks"]
    face_rows = [int(lm["eye_row"]), int(lm["mouth_row"])]
    rf = ref["views"]["front"]
    band_r = rf["band"]
    prof_r = rf["width_profile"]

    m = {}
    m["silhouette_face_band_ratio"] = {
        "reference": silhouette_face_band_ratio(prof_r, band_r, face_rows),
        "candidate": silhouette_face_band_ratio(
            refmod.width_profile(renders["front"]["mask"]),
            refmod.head_band(renders["front"]["mask"]), face_rows),
    }
    cand_dwr, ref_dwr = _profile_depth_ratio(ref, calib, renders, list(renders.keys()))
    m["profile_depth_width_ratio"] = {"reference": ref_dwr, "candidate": cand_dwr}
    corr, shift = relief_shading_correlation(ref, renders, ref["eye_band_rect"])
    m["relief_shading_correlation"] = {"reference": 1.0, "candidate": corr, "shift_px": shift}
    ratio, spreads, head_w = band_spread_ratio(cand, calib, renders, rects,
                                                     ref["bands"]["front"])
    fb = ref.get("reference_face_band", {}).get("eye")
    ref_ratio = None
    if fb and rf["metrics"].get("head_width_px"):
        ref_ratio = fb["span_px"] / float(rf["metrics"]["head_width_px"])
    m["band_spread_ratio"] = {"reference": ref_ratio, "candidate": ratio,
                              "spread_px": spreads, "head_width_px": head_w}
    m["surface_roughness_rel"] = {"reference": None,
                                  "candidate": surface_roughness(cand).get("relative"),
                                  "detail": surface_roughness(cand)}
    m["depth_symmetry"] = {"reference": None,
                           "candidate": depth_symmetry(renders, calib, face_rows)}
    app = appearance_metrics(ref, renders, ref["eye_band_rect"])
    app["appearance_ncc"] = appearance_ncc(ref, textured_rgb, ref["eye_band_rect"])
    m["appearance_silhouette_iou"] = {"reference": 1.0,
                                      "candidate": app.get("appearance_silhouette_iou")}
    m["appearance_ncc"] = {"reference": 1.0, "candidate": app.get("appearance_ncc")}
    m["_tolerances"] = dict(TOLERANCES)
    return m


def compare_to_reference(metrics):
    """Absolute verdict of every metric against the reference."""
    out = {}
    for key, val in metrics.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        cand = val.get("candidate")
        refv = val.get("reference")
        tol = TOLERANCES.get(key)
        if key in LIMITS:
            if cand is None:
                out[key] = {"status": "NOT_MEASURABLE", "candidate": cand,
                            "reference": refv, "limit": LIMITS[key]}
            else:
                lim = LIMITS[key]
                out[key] = {"status": "PASS" if cand <= lim else "FAIL",
                            "candidate": cand, "reference": refv, "limit": lim,
                            "relative_deviation": (cand / lim if lim else None),
                            "tolerance": tol}
            continue
        if cand is None or refv is None or tol is None:
            out[key] = {"status": "NOT_MEASURABLE", "candidate": cand, "reference": refv}
            continue
        if key in DIRECTION:
            ok = cand >= refv - tol
            delta = cand - refv
        else:
            delta = (cand - refv) / max(abs(refv), 1e-12)
            ok = abs(delta) <= tol
        out[key] = {"status": "PASS" if ok else "FAIL", "candidate": cand,
                    "reference": refv, "relative_deviation": delta, "tolerance": tol}
    return out


def control_rejected(baseline_metrics, control_metrics, tol_scale=1.0):
    """Was this control rejected by at least one metric?

    A metric rejects the control when it moves by more than its tolerance
    relative to the baseline candidate.  The appearance metrics are included
    in the comparison as well, but they are reported separately so the report
    can show whether an appearance metric stayed satisfied.
    """
    rejected_by = []
    appearance_moved = []
    for key, base in baseline_metrics.items():
        if key.startswith("_") or not isinstance(base, dict):
            continue
        tol = TOLERANCES.get(key)
        if tol is None:
            continue
        b = base.get("candidate")
        c = control_metrics.get(key, {}).get("candidate")
        if b is None or c is None:
            continue
        if key in DIRECTION:
            delta = abs(c - b)
            scale = max(abs(b), 1e-9)
        else:
            delta = abs(c - b) / max(abs(b), 1e-12)
            scale = 1.0
        moved = delta > tol * tol_scale
        if moved:
            rejected_by.append({"metric": key, "baseline": b, "control": c,
                                 "relative_change": delta, "tolerance": tol})
        elif key.startswith("appearance"):
            appearance_moved.append({"metric": key, "baseline": b, "control": c,
                                     "relative_change": delta, "tolerance": tol})
    return {"rejected": bool(rejected_by), "rejected_by": rejected_by,
            "appearance_metrics_that_did_not_move": appearance_moved}
