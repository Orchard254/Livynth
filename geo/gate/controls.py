"""C001-GEO-04 gate - identity controls (canaries).

A control is a DELIBERATE corruption of a candidate's geometry that changes
the identity of the face while keeping the silhouette broadly intact.  The
gate MUST reject every control; if it does not, the gate itself is invalid
and the run is reported with gate_valid = False.

Controls implemented
--------------------
face_band_widen   the whole face band (eyes and mouth) is widened laterally
                  by a factor about the band centre.  This is the 1.18x
                  canary of the previous protocol.
ipd_widen         only the eye band is widened (inter-ocular distance).
eye_shrink        the surface around each eye centre is scaled down.
nose_lengthen     the surface around the nose tip is pushed forward.
jitter            every vertex is displaced by Gaussian noise of sigma
                  pixels (the 8 px canary of the previous protocol).
photo_plane       the face region is flattened onto a plane.  The projected
                  photograph survives, so the APPEARANCE is unchanged while
                  the geometry is destroyed: this is the control that shows
                  why an appearance metric cannot decide.

The band regions are defined by the reference landmarks projected into the
candidate through the gate camera convention, so the controls are placed on
the same anatomy the reference landmarks describe.
"""

import numpy as np
import trimesh

from .camera import project_point


def band_rects(landmarks):
    """Pixel rectangles for the eye band, mouth band, nose and each eye."""
    le = landmarks["eyes"]["left"]
    re = landmarks["eyes"]["right"]
    ipd = abs(re[0] - le[0])
    yc = 0.5 * (le[1] + re[1])
    (mlx, mly), (mrx, mry) = landmarks["mouth_corners"]
    mw = abs(mrx - mlx)
    myc = 0.5 * (mly + mry)
    nose_y = int(0.62 * yc + 0.38 * myc)
    return {
        "eye": (int(min(le[0], re[0]) - 0.30 * ipd), int(yc - 0.30 * ipd),
                int(max(le[0], re[0]) + 0.30 * ipd), int(yc + 0.30 * ipd)),
        "mouth": (int(min(mlx, mrx) - 0.30 * mw), int(myc - 0.30 * mw),
                  int(max(mlx, mrx) + 0.30 * mw), int(myc + 0.30 * mw)),
        "nose": (int((le[0] + re[0]) / 2 - 0.14 * ipd), int(nose_y - 0.14 * ipd),
                 int((le[0] + re[0]) / 2 + 0.14 * ipd), int(nose_y + 0.14 * ipd)),
        "eye_left": (int(le[0] - 0.16 * ipd), int(le[1] - 0.16 * ipd),
                     int(le[0] + 0.16 * ipd), int(le[1] + 0.16 * ipd)),
        "eye_right": (int(re[0] - 0.16 * ipd), int(re[1] - 0.16 * ipd),
                      int(re[0] + 0.16 * ipd), int(re[1] + 0.16 * ipd)),
    }


def vertex_projections(verts, view):
    u = []
    v = []
    for p in verts:
        a, b = project_point(p, view)
        u.append(a)
        v.append(b)
    return np.asarray(u), np.asarray(v)


def in_rect(u, v, rect):
    return (u >= rect[0]) & (u <= rect[2]) & (v >= rect[1]) & (v <= rect[3])


def apply_control(verts, faces, kind, params, view, rects):
    """Return the control description and the modified vertices."""
    u, v = vertex_projections(verts, view)
    info = {"kind": kind, "params": dict(params)}
    out = np.array(verts, dtype=np.float64, copy=True)
    if kind == "face_band_widen":
        rows = params.get("row_range")
        if rows is None:
            sel = in_rect(u, v, rects["eye"]) | in_rect(u, v, rects["mouth"])
        else:
            sel = (v >= float(rows[0])) & (v <= float(rows[1]))
        factor = float(params["factor"])
        if sel.any():
            centre = float(out[sel, 0].mean())
            out[sel, 0] = centre + factor * (out[sel, 0] - centre)
        info["vertices_changed"] = int(sel.sum())
        info["selection"] = "face band rows"
    elif kind == "ipd_widen":
        rows = params.get("row_range")
        if rows is None:
            sel = in_rect(u, v, rects["eye"])
        else:
            sel = (v >= float(rows[0])) & (v <= float(rows[1]))
        factor = float(params["factor"])
        if sel.any():
            centre = float(out[sel, 0].mean())
            out[sel, 0] = centre + factor * (out[sel, 0] - centre)
        info["vertices_changed"] = int(sel.sum())
        info["selection"] = "eye band rows"
    elif kind == "eye_shrink":
        factor = float(params["factor"])
        sel = in_rect(u, v, rects["eye_left"]) | in_rect(u, v, rects["eye_right"])
        if sel.any():
            for key in ("eye_left", "eye_right"):
                s = in_rect(u, v, rects[key])
                if not s.any():
                    continue
                cx = float(out[s, 0].mean())
                cy = float(out[s, 1].mean())
                cz = float(out[s, 2].mean())
                out[s, 0] = cx + factor * (out[s, 0] - cx)
                out[s, 1] = cy + factor * (out[s, 1] - cy)
                out[s, 2] = cz + factor * (out[s, 2] - cz)
        info["vertices_changed"] = int(sel.sum())
    elif kind == "nose_lengthen":
        sel = in_rect(u, v, rects["nose"])
        factor = float(params["factor"])
        ipd_m = float(params["ipd_m"])
        if sel.any():
            out[sel, 2] += (factor - 1.0) * ipd_m
        info["vertices_changed"] = int(sel.sum())
    elif kind == "jitter":
        sigma_m = float(params["sigma_m"])
        rng = np.random.default_rng(int(params.get("seed", 20261111)))
        noise = rng.normal(0.0, sigma_m, size=out.shape)
        out = out + noise
        info["vertices_changed"] = int(len(out))
        info["sigma_m"] = sigma_m
    elif kind == "photo_plane":
        sel = in_rect(u, v, rects["eye"]) | in_rect(u, v, rects["mouth"]) | in_rect(u, v, rects["nose"])
        if sel.any():
            z = float(np.median(out[sel, 2]))
            out[sel, 2] = z
        info["vertices_changed"] = int(sel.sum())
    else:
        raise ValueError("unknown control %s" % kind)
    return out, info


def write_control(base_glb, out_glb, verts, faces):
    """Write the controlled mesh as a GLB, keeping the original materials."""
    scene = trimesh.load(str(base_glb), force="scene")
    geoms = list(scene.geometry.values())
    if len(geoms) == 1:
        g = geoms[0]
        g.vertices = verts
        scene = trimesh.Scene(g)
    else:
        off = 0
        for g in geoms:
            n = len(g.vertices)
            g.vertices = verts[off:off + n]
            off += n
        scene = trimesh.Scene(geoms)
    scene.export(str(out_glb))
    return str(out_glb)
