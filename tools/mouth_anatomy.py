#!/usr/bin/env python3
"""Head A mouth anatomy fix — opt-in, in-memory copy only.

Moves the MPFB-fitted teeth/tongue on a DISPOSABLE copied character (the
pipeline already mutates that copy: bake, head shape, accessory alignment).
Installed MPFB assets, the MPFB source human, the original export copy
topology and every previously exported GLB are never modified.

Fix components (all material/geometry-only on the copy):

1. Upper dental arch seat: translate the upper-arch (MHCLO-mask == 0) teeth
   vertices DOWN along +Z by a bounded seat so the arch hangs behind the
   upper lip instead of being embedded above the mouth opening.
2. Tongue seat: translate the whole tongue DOWN by a bounded amount so it
   rests on the lower dental arch instead of doming into the upper mouth.
3. Oral cavity material: assign a dark non-reflective material to the
   inner-facing body faces in the mouth band (backfaces facing the camera
   through the opened lips), replacing the exposed grey speckled interior.
   The outer body faces get a plain warm-clay material.
"""
from __future__ import annotations

import math
import numpy as np

SCHEMA = 'livynth.oral-anatomy.v1'
UPPER_SEAT_M = 0.022
TONGUE_SEAT_M = 0.016
MAX_SEAT_M = 0.045
MIN_SEAT_M = 0.0
CAVITY_HALF_WIDTH = 0.060
CAVITY_OPENING_HALF_WIDTH = 0.046
CAVITY_Z_MIN_FRACTION = 0.870
CAVITY_Z_MAX_FRACTION = 0.915
CAVITY_MIN_DEPTH_Y = -0.10
CAVITY_SIDE_NORMAL_THRESHOLD = 0.5
CAVITY_BASE_COLOR = (0.135, 0.035, 0.030, 1.0)
EXTERIOR_BASE_COLOR = (0.760, 0.745, 0.720, 1.0)
CAVITY_ROUGHNESS = 0.92
EXTERIOR_ROUGHNESS = 0.62


class MouthAnatomyError(ValueError):
    pass


def validate_seat(value, label):
    try:
        seat = float(value)
    except (TypeError, ValueError) as exc:
        raise MouthAnatomyError('E_SEAT_TYPE_' + label) from exc
    if isinstance(value, bool) or not math.isfinite(seat):
        raise MouthAnatomyError('E_SEAT_VALUE_' + label)
    if not (MIN_SEAT_M <= seat <= MAX_SEAT_M):
        raise MouthAnatomyError('E_SEAT_RANGE_' + label)
    return seat


def _points(points, label):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4 or not np.isfinite(p).all():
        raise MouthAnatomyError('E_POINTS_' + label)
    return p


def plan_masked_translation(points, mask, *, dx=0.0, dy=0.0, dz=0.0,
                            select_value=0, label='MASKED'):
    """Translate the vertices where mask == select_value by (dx,dy,dz)."""
    p = _points(points, label)
    m = np.asarray(mask, dtype=np.float64)
    if m.shape != (len(p),) or not np.isfinite(m).all():
        raise MouthAnatomyError('E_MASK_SHAPE_' + label)
    if not np.isin(m, [0.0, 1.0]).all():
        raise MouthAnatomyError('E_MASK_VALUES_' + label)
    shift = np.array([dx, dy, dz], dtype=np.float64)
    if not np.isfinite(shift).all() or float(np.linalg.norm(shift)) > MAX_SEAT_M:
        raise MouthAnatomyError('E_MASKED_SHIFT_' + label)
    sel = m == float(select_value)
    if int(sel.sum()) < 20:
        raise MouthAnatomyError('E_MASKED_SELECTION_TOO_SMALL_' + label)
    offsets = np.zeros_like(p)
    offsets[sel] = shift
    moved = p + offsets
    distances = np.linalg.norm(offsets, axis=1)
    return moved, {
        'schema': SCHEMA,
        'operation': 'MASKED_AXIS_TRANSLATION',
        'selected_vertices': int(sel.sum()),
        'stationary_vertices': int((~sel).sum()),
        'translation_body_m': [round(float(v), 9) for v in shift],
        'translation_magnitude_m': round(float(np.linalg.norm(shift)), 9),
        'max_displacement_m': round(float(distances.max()), 9),
        'label': label,
    }


def plan_translation(points, *, dx=0.0, dy=0.0, dz=0.0, label='ALL'):
    """Translate every vertex by (dx,dy,dz)."""
    p = _points(points, label)
    shift = np.array([dx, dy, dz], dtype=np.float64)
    if not np.isfinite(shift).all() or float(np.linalg.norm(shift)) > MAX_SEAT_M:
        raise MouthAnatomyError('E_TRANSLATION_' + label)
    offsets = np.tile(shift, (len(p), 1))
    moved = p + offsets
    return moved, {
        'schema': SCHEMA,
        'operation': 'GLOBAL_AXIS_TRANSLATION',
        'selected_vertices': len(p),
        'stationary_vertices': 0,
        'translation_body_m': [round(float(v), 9) for v in shift],
        'translation_magnitude_m': round(float(np.linalg.norm(shift)), 9),
        'max_displacement_m': round(float(np.linalg.norm(shift)), 9),
        'label': label,
    }


def plan_cavity_faces(centers, normals, *, half_width=CAVITY_OPENING_HALF_WIDTH,
                      z_min=1.36, z_max=1.62,
                      min_depth_y=CAVITY_MIN_DEPTH_Y,
                      side_normal_threshold=CAVITY_SIDE_NORMAL_THRESHOLD):
    """Return the indices of exposed mouth-cavity polygons.

    Pure function: centers/normals are world-space arrays shaped (N,3).

    A polygon qualifies when all hold:
    - |x| inside the mouth opening (skin plugs the corners, receding
      cheek faces never belong to the cavity);
    - z inside the mouth band (chin and nose bridge excluded);
    - deep enough behind the front skin envelope (y >= min_depth_y);
    - if strongly side-facing (|nx| > side_normal_threshold), the normal
      must point toward the mouth centre (sign(nx) == -sign(x)).
    """
    c = _points(centers, 'CAVITY_CENTERS')
    n = _points(normals, 'CAVITY_NORMALS')
    if c.shape != n.shape:
        raise MouthAnatomyError('E_CAVITY_FACE_LAYOUT')
    if not (0.0 < half_width <= 0.30):
        raise MouthAnatomyError('E_CAVITY_HALF_WIDTH')
    if not (math.isfinite(z_min) and math.isfinite(z_max) and z_min < z_max):
        raise MouthAnatomyError('E_CAVITY_Z_WINDOW')
    if not math.isfinite(min_depth_y):
        raise MouthAnatomyError('E_CAVITY_DEPTH')
    if not (0.0 <= side_normal_threshold < 1.0):
        raise MouthAnatomyError('E_CAVITY_SIDE_THRESHOLD')
    sel = []
    for i in range(len(c)):
        if abs(c[i, 0]) > half_width:
            continue
        if not (z_min <= c[i, 2] <= z_max):
            continue
        if c[i, 1] < min_depth_y:
            continue
        nx = n[i, 0]
        cx = c[i, 0]
        if abs(nx) > side_normal_threshold:
            if abs(cx) < 1e-6:
                continue
            if (nx > 0.0) == (cx > 0.0):
                continue  # strongly side-facing but pointing away from centre
        sel.append(i)
    return sel


def cavity_z_window(crown_z, height, *, z_min_fraction=CAVITY_Z_MIN_FRACTION,
                    z_max_fraction=CAVITY_Z_MAX_FRACTION):
    if not (math.isfinite(crown_z) and math.isfinite(height)):
        raise MouthAnatomyError('E_Z_WINDOW_INPUT')
    if not (1.0 <= height <= 2.5):
        raise MouthAnatomyError('E_Z_WINDOW_HEIGHT')
    z_min = float(crown_z - (1.0 - z_min_fraction) * height)
    z_max = float(crown_z - (1.0 - z_max_fraction) * height)
    if not z_min < z_max:
        raise MouthAnatomyError('E_Z_WINDOW_FRACTION')
    return z_min, z_max


def plan_cavity_faces_bvh(body_object, *, z_min=1.36, z_max=1.62,
                          rays_x=48, rays_z=48, max_faces=4000):
    """Return indices of body polygons hit by front rays through the band.

    Cast a front-to-back ray grid through the mouth band. Interior mouth
    walls are the FIRST surface a ray through the opening meets; skin and
    the rear of the head are excluded later by the depth filter in
    ``plan_cavity_faces`` (skin is shallower, rear faces are occluded and
    never survive as first hits either).

    Requires bpy/mathutils; called only by the Blender pipeline on the
    jaw-open EVALUATED mesh (where the opening actually exists).
    """
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import bmesh
    import numpy as np

    if not (math.isfinite(z_min) and math.isfinite(z_max) and z_min < z_max):
        raise MouthAnatomyError('E_CAVITY_Z_WINDOW')
    if rays_x < 4 or rays_z < 4 or max_faces < 1:
        raise MouthAnatomyError('E_CAVITY_RAY_GRID')

    bm = bmesh.new()
    try:
        bm.from_mesh(body_object.data)
        matrix = np.array(body_object.matrix_world,
                          dtype=np.float64).reshape(4, 4)
        coords = [tuple((matrix @ np.array([v.co.x, v.co.y, v.co.z, 1.0]))[:3])
                  for v in bm.verts]
        tris = []
        tri_to_polygon = []
        for face in bm.faces:
            verts = list(face.verts)
            for i in range(1, len(verts) - 1):
                tris.append((verts[0].index, verts[i].index, verts[i + 1].index))
                tri_to_polygon.append(face.index)
    finally:
        bm.free()
    tree = BVHTree.FromPolygons(coords, tris, all_triangles=True)
    if tree is None:
        raise MouthAnatomyError('E_CAVITY_BVH_BUILD')

    origin_y = float(min(c[1] for c in coords)) - 2.0
    hit_polygons = set()
    for ix in range(rays_x):
        x = -CAVITY_HALF_WIDTH + (2.0 * CAVITY_HALF_WIDTH) * ix / (rays_x - 1)
        for iz in range(rays_z):
            z = z_min + (z_max - z_min) * iz / (rays_z - 1)
            origin = Vector((x, origin_y, z))
            hit = tree.ray_cast(origin, Vector((0.0, 1.0, 0.0)), 10.0)
            if hit is None:
                continue
            location, _normal, index, _dist = hit
            if index is None:
                continue
            polygon = tri_to_polygon[index]
            hit_polygons.add(polygon)
            if len(hit_polygons) >= max_faces:
                break
    if not hit_polygons:
        raise MouthAnatomyError('E_CAVITY_NO_OPENING_FACES')
    return sorted(hit_polygons)
