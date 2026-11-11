"""C001-GEO-04 gate - orthographic rasteriser (numpy only, no trimesh).

Produces exact metric depth and world-space normal maps for the gate camera
convention, so that the geometry evidence does not depend on any renderer's
pass semantics.  Used by the Blender evidence renderer and by the offline
evaluator; it is the single source of truth for the depth/normal maps.

Model frame: +x right, +y up, +z face direction.
Camera basis for a view with azimuth psi:

    right = ( cos psi, 0,  sin psi)     image right
    up    = ( 0, 1, 0)                 image up
    fwd   = ( sin psi, 0, -cos psi)     direction the camera looks along
    camera position (model frame) = (-sin psi, 0, cos psi) * D

    u = cx + s * (p . right)
    v = cy - s * (p . up)
    depth = p . fwd                    metres along the view axis

depth grows away from the camera, so "protrusion towards the camera" is
-depth (up to the additive constant of the camera plane).
"""

import numpy as np


def view_basis(view):
    psi = np.radians(float(view["phi"]))
    right = np.array([np.cos(psi), 0.0, np.sin(psi)], dtype=np.float64)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    fwd = np.array([np.sin(psi), 0.0, -np.cos(psi)], dtype=np.float64)
    return right, up, fwd


def project(verts, view):
    """Project model-frame vertices to (u, v, depth)."""
    verts = np.asarray(verts, dtype=np.float64)
    right, up, fwd = view_basis(view)
    s = float(view["s"])
    u = float(view["cx"]) + s * (verts @ right)
    v = float(view["cy"]) - s * (verts @ up)
    depth = verts @ fwd
    return u, v, depth


def vertex_normals(verts, faces):
    """Area-weighted vertex normals (numpy only)."""
    verts = np.asarray(verts, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    fn = np.zeros_like(verts)
    a = verts[faces[:, 0]]
    b = verts[faces[:, 1]]
    c = verts[faces[:, 2]]
    cross = np.cross(b - a, c - a)
    fn[faces[:, 0]] += cross
    fn[faces[:, 1]] += cross
    fn[faces[:, 2]] += cross
    n = np.linalg.norm(fn, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return fn / n


def rasterize(verts, faces, view, width, height, normal_map=True):
    """Z-buffer rasterise the mesh under the gate camera convention."""
    verts = np.asarray(verts, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    u, v, depth = project(verts, view)
    vn = vertex_normals(verts, faces) if normal_map else None

    zbuf = np.full((height, width), np.inf, dtype=np.float64)
    nbuf = np.zeros((height, width, 3), dtype=np.float64) if normal_map else None

    pu = u[faces]
    pv = v[faces]
    pd = depth[faces]

    for i in range(faces.shape[0]):
        x0, x1, x2 = pu[i]
        y0, y1, y2 = pv[i]
        minx = max(int(np.floor(min(x0, x1, x2))), 0)
        maxx = min(int(np.ceil(max(x0, x1, x2))), width - 1)
        miny = max(int(np.floor(min(y0, y1, y2))), 0)
        maxy = min(int(np.ceil(max(y0, y1, y2))), height - 1)
        if minx > maxx or miny > maxy:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        xs = np.arange(minx, maxx + 1, dtype=np.float64) + 0.5
        ys = np.arange(miny, maxy + 1, dtype=np.float64) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        if not inside.any():
            continue
        z = l0 * pd[i, 0] + l1 * pd[i, 1] + l2 * pd[i, 2]
        sub = zbuf[miny:maxy + 1, minx:maxx + 1]
        upd = inside & (z < sub)
        if not upd.any():
            continue
        sub[upd] = z[upd]
        if normal_map:
            n0 = vn[faces[i, 0]]
            n1 = vn[faces[i, 1]]
            n2 = vn[faces[i, 2]]
            nrm = l0[..., None] * n0 + l1[..., None] * n1 + l2[..., None] * n2
            ln = np.linalg.norm(nrm, axis=-1, keepdims=True)
            ln[ln == 0] = 1.0
            nrm = nrm / ln
            tgt = nbuf[miny:maxy + 1, minx:maxx + 1]
            tgt[upd] = nrm[upd]

    mask = np.isfinite(zbuf)
    right, up, fwd = view_basis(view)
    return {"mask": mask, "depth": zbuf, "normal": nbuf,
            "view_basis": {"right": right.tolist(), "up": up.tolist(), "fwd": fwd.tolist()}}
