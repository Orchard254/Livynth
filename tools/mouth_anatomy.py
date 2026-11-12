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
TONGUE_SEAT_M = 0.024
MAX_SEAT_M = 0.045
MIN_SEAT_M = 0.0
TOOTH_SCALE = 0.85
MIN_TOOTH_SCALE = 0.60
MAX_TOOTH_SCALE = 1.30
TONGUE_SATURATION = 0.55
TONGUE_VALUE = 0.72
TEETH_GUM_TONE = (0.30, 0.16, 0.14)
TEETH_GUM_MUTE_STRENGTH = 0.80
LIP_Z_CENTER = 1.492
LIP_Z_HALF_SPAN = 0.030
LIP_X_HALF_SPAN = 0.034
LIP_MAX_PUSH_M = 0.010
MAX_LIP_PUSH_M = 0.020
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


def validate_tooth_scale(value, label='TOOTH_SCALE'):
    try:
        scale = float(value)
    except (TypeError, ValueError) as exc:
        raise MouthAnatomyError('E_SCALE_TYPE_' + label) from exc
    if isinstance(value, bool) or not math.isfinite(scale):
        raise MouthAnatomyError('E_SCALE_VALUE_' + label)
    if not (MIN_TOOTH_SCALE <= scale <= MAX_TOOTH_SCALE):
        raise MouthAnatomyError('E_SCALE_RANGE_' + label)
    return scale


def validate_lip_push(value, label='LIP_PUSH'):
    try:
        push = float(value)
    except (TypeError, ValueError) as exc:
        raise MouthAnatomyError('E_LIP_TYPE_' + label) from exc
    if isinstance(value, bool) or not math.isfinite(push):
        raise MouthAnatomyError('E_LIP_VALUE_' + label)
    if not (0.0 <= push <= MAX_LIP_PUSH_M):
        raise MouthAnatomyError('E_LIP_RANGE_' + label)
    return push


def _points(points, label):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 1 or not np.isfinite(p).all():
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


def plan_uniform_scale(points, scale, pivot, *, label='ASSET',
                       min_scale=MIN_TOOTH_SCALE,
                       max_scale=MAX_TOOTH_SCALE):
    """Scale every vertex about a fixed pivot by a uniform factor.

    The pivot and factor are constant for the whole asset, so the caller
    (a Blender shape-key-aware writer) can apply the identical similarity
    to Basis and every corrective key block, keeping poses consistent.
    """
    p = _points(points, label)
    piv = np.asarray(pivot, dtype=np.float64)
    if piv.shape != (3,) or not np.isfinite(piv).all():
        raise MouthAnatomyError('E_PIVOT_' + label)
    scale = validate_tooth_scale(scale, label)
    if not (MIN_TOOTH_SCALE <= min_scale <= max_scale <= MAX_TOOTH_SCALE):
        raise MouthAnatomyError('E_SCALE_BOUNDS_' + label)
    if not (min_scale <= scale <= max_scale):
        raise MouthAnatomyError('E_SCALE_RANGE_' + label)
    moved = piv + (p - piv) * scale
    displacements = np.linalg.norm(moved - p, axis=1)
    return moved, {
        'schema': SCHEMA,
        'operation': 'UNIFORM_SCALE_ABOUT_PIVOT',
        'selected_vertices': len(p),
        'stationary_vertices': 0,
        'scale': round(float(scale), 9),
        'pivot_body_m': [round(float(v), 9) for v in piv],
        'max_displacement_m': round(float(displacements.max()), 9),
        'label': label,
    }


def plan_lip_soften(points, *, z_center=LIP_Z_CENTER,
                    z_half_span=LIP_Z_HALF_SPAN,
                    x_half_span=LIP_X_HALF_SPAN,
                    max_push=LIP_MAX_PUSH_M,
                    front_y_gate=0.0,
                    label='LIP_SULCUS'):
    """Push front-facing mentolabial-sulcus vertices toward the lip.

    Pure falloff plan: vertices in front of the y gate (front of the
    head) whose z is within ``z_half_span`` of ``z_center`` and |x| within
    ``x_half_span`` receive a forward (-Y) displacement that peaks at the
    band centre and falls off quartically in both axes. Returns the same
    number of vertices; topology and morph deltas are preserved because
    callers apply the identical per-vertex delta to every key block.
    """
    p = _points(points, label)
    if not (math.isfinite(z_center) and math.isfinite(front_y_gate)):
        raise MouthAnatomyError('E_LIP_INPUT_' + label)
    if not (math.isfinite(z_half_span) and z_half_span > 0.0):
        raise MouthAnatomyError('E_LIP_Z_SPAN_' + label)
    if not (math.isfinite(x_half_span) and x_half_span > 0.0):
        raise MouthAnatomyError('E_LIP_X_SPAN_' + label)
    if not (0.0 <= max_push <= MAX_LIP_PUSH_M):
        raise MouthAnatomyError('E_LIP_PUSH_' + label)
    wz = np.clip(1.0 - ((p[:, 2] - z_center) / z_half_span) ** 2, 0.0, 1.0) ** 2
    wx = np.clip(1.0 - (p[:, 0] / x_half_span) ** 2, 0.0, 1.0) ** 2
    front = p[:, 1] < front_y_gate
    weight = np.where(front, wz * wx, 0.0)
    moved = p.copy()
    moved[:, 1] = p[:, 1] - max_push * weight
    displacements = np.linalg.norm(moved - p, axis=1)
    selected = int((weight > 0.0).sum())
    return moved, {
        'schema': SCHEMA,
        'operation': 'FRONT_SULCUS_FORWARD_LIFT',
        'selected_vertices': selected,
        'stationary_vertices': int((weight == 0.0).sum()),
        'max_displacement_m': round(float(displacements.max()), 9),
        'z_center_m': round(float(z_center), 6),
        'z_half_span_m': round(float(z_half_span), 6),
        'x_half_span_m': round(float(x_half_span), 6),
        'front_y_gate_m': round(float(front_y_gate), 6),
        'max_push_m': round(float(max_push), 9),
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


def classify_gum_pixels(rgb):
    """Boolean mask of gum-like texels in an RGB float image array.

    The MPFB teeth texture paints gum slabs as large saturated red regions
    (R clearly dominant over G and B, and not near-white) while tooth
    shells stay near-neutral grey. Hue-independent, no absolute brightness
    assumptions, works on float pixels in [0, 1].
    """
    a = np.asarray(rgb, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 3 or not np.isfinite(a).all():
        raise MouthAnatomyError('E_GUM_PIXELS_LAYOUT')
    if a.size == 0:
        raise MouthAnatomyError('E_GUM_PIXELS_EMPTY')
    r = a[..., 0]
    g = a[..., 1]
    b = a[..., 2]
    return (r > g + 45.0 / 255.0) & (r > b + 35.0 / 255.0) & (r < 190.0 / 255.0)


def mute_gum_pixels(rgb, *, tone=TEETH_GUM_TONE,
                    strength=TEETH_GUM_MUTE_STRENGTH):
    """Return a gum-muted copy of an RGB float image array.

    Only texels classified as gum are moved toward ``tone``; tooth texels
    are returned bit-identical. Operates on copies, never on the input.
    """
    a = np.asarray(rgb, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 3 or not np.isfinite(a).all():
        raise MouthAnatomyError('E_GUM_PIXELS_LAYOUT')
    try:
        tone_v = np.asarray(tone, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise MouthAnatomyError('E_GUM_TONE') from exc
    if tone_v.shape != (3,) or not np.isfinite(tone_v).all():
        raise MouthAnatomyError('E_GUM_TONE')
    if not (math.isfinite(strength) and 0.0 <= strength <= 1.0):
        raise MouthAnatomyError('E_GUM_STRENGTH')
    mask = classify_gum_pixels(a)
    out = a.copy()
    tinted = a * (1.0 - strength) + tone_v.reshape(1, 1, 3) * strength
    out[mask] = tinted[mask]
    return out, mask


def _edge_pierces_triangle(p0, p1, t0, t1, t2, *, epsilon=1e-9):
    """Möller segment-triangle piercing test (exact predicate, no barycentric
    allocation). Returns True iff the open segment (p0, p1) crosses the
    closed triangle (t0, t1, t2) transversally.
    """
    n = np.cross(t1 - t0, t2 - t0)
    d = p1 - p0
    denom = float(n @ d)
    if abs(denom) < epsilon:
        return False
    t = float(n @ (t0 - p0)) / denom
    if t <= 0.0 or t >= 1.0:  # endpoints on the surface do not count
        return False
    q = p0 + t * d
    e0 = t1 - t0
    e2 = t2 - t0
    vp = q - t0
    d00 = float(e0 @ e0)
    d01 = float(e0 @ e2)
    d11 = float(e2 @ e2)
    d02 = float(e0 @ vp)
    d12 = float(e2 @ vp)
    den = d00 * d11 - d01 * d01
    if abs(den) < epsilon:
        return False
    u = (d11 * d02 - d01 * d12) / den
    v = (d00 * d12 - d01 * d02) / den
    return u >= -1e-9 and v >= -1e-9 and u + v <= 1.0 + 1e-9


def _triangles_intersect(a0, a1, a2, b0, b1, b2, *, epsilon=1e-9):
    """Exact Möller triangle-triangle intersection predicate.

    Counts only transversal crossings: six edge-pierce tests. Tangential
    touches (coplanar contact, shared ridges) are reported as not
    intersecting - callers get a conservative interpenetration signal.
    """
    for p0, p1 in ((a0, a1), (a1, a2), (a2, a0)):
        if _edge_pierces_triangle(p0, p1, b0, b1, b2, epsilon=epsilon):
            return True
    for p0, p1 in ((b0, b1), (b1, b2), (b2, b0)):
        if _edge_pierces_triangle(p0, p1, a0, a1, a2, epsilon=epsilon):
            return True
    return False


def count_intersecting_triangle_pairs(tris_a, tris_b, *,
                                      aabb_margin=1e-6,
                                      max_report_pairs=16):
    """Broadphase AABB prefilter + exact Möller predicate per pair.

    Returns {'total_a', 'total_b', 'pairs', 'sample_pairs',
             'method', 'aabb_margin_m'}.
    """
    A = np.asarray(tris_a, dtype=np.float64)
    B = np.asarray(tris_b, dtype=np.float64)
    if A.ndim != 3 or A.shape[1:] != (3, 3) or not np.isfinite(A).all():
        raise MouthAnatomyError('E_INTERSECT_A')
    if B.ndim != 3 or B.shape[1:] != (3, 3) or not np.isfinite(B).all():
        raise MouthAnatomyError('E_INTERSECT_B')
    if len(A) < 1 or len(B) < 1:
        raise MouthAnatomyError('E_INTERSECT_EMPTY')
    if not math.isfinite(aabb_margin) or aabb_margin < 0.0:
        raise MouthAnatomyError('E_INTERSECT_MARGIN')
    a_min = A.min(axis=1)
    a_max = A.max(axis=1)
    b_min = B.min(axis=1)
    b_max = B.max(axis=1)
    order = np.argsort(b_min[:, 2])
    b_min = b_min[order]
    b_max = b_max[order]
    B = B[order]
    pairs = 0
    samples = []
    for i in range(len(A)):
        a0, a1, a2 = A[i]
        zlo, zhi = a_min[i, 2] - aabb_margin, a_max[i, 2] + aabb_margin
        left = np.searchsorted(b_min[:, 2], zhi, side='right')
        for j in range(left):
            if b_max[j, 2] < zlo:
                continue
            if b_max[j, 1] < a_min[i, 1] - aabb_margin:
                continue
            if b_min[j, 1] > a_max[i, 1] + aabb_margin:
                continue
            if b_max[j, 0] < a_min[i, 0] - aabb_margin:
                continue
            if b_min[j, 0] > a_max[i, 0] + aabb_margin:
                continue
            if _triangles_intersect(a0, a1, a2, B[j, 0], B[j, 1], B[j, 2]):
                pairs += 1
                if len(samples) < max_report_pairs:
                    samples.append((int(i), int(order[j])))
    return {
        'method': 'MOLLER_TRIANGLE_PIERCE',
        'total_a': int(len(A)),
        'total_b': int(len(B)),
        'pairs': int(pairs),
        'sample_pairs': samples,
        'aabb_margin_m': float(aabb_margin),
    }


def validate_polygon_correspondence(base_loops, evaluated_loops,
                                    *, label='CAVITY'):
    """Require identical polygon-loop vertex indices in two meshes.

    The cavity selector casts BVH rays at an *evaluated* jaw-open mesh
    (shape keys baked by Blender's depsgraph) but assigns materials on the
    *base* mesh polygons. That index mapping is only valid when both
    meshes carry the same polygon count in the same order with identical
    winding. This function enforces the mapping instead of assuming it;
    any mismatch is a hard error, never a silent wrong-slot assignment.
    Returns the validated polygon count.
    """
    base = [tuple(int(i) for i in loop) for loop in base_loops]
    evaluated = [tuple(int(i) for i in loop) for loop in evaluated_loops]
    if len(base) != len(evaluated):
        raise MouthAnatomyError(
            'E_' + label + '_POLYGON_COUNT_' + str(len(base)) + '_VS_' +
            str(len(evaluated)))
    for index, (a, b) in enumerate(zip(base, evaluated)):
        if a != b:
            raise MouthAnatomyError(
                'E_' + label + '_LOOP_MISMATCH_' + str(index))
    return len(base)


def _closest_point_segment(points, a, b):
    ab = b - a
    denom = float(ab @ ab)
    if denom <= 0.0:
        return np.broadcast_to(a, points.shape).copy()
    t = np.clip(((points - a) @ ab) / denom, 0.0, 1.0)
    return a + np.outer(t, ab)


def _closest_point_triangle(points, a, b, c):
    # Exact closest point: barycentric test for interior points, edge
    # candidates for everything else (an outside point's closest point on a
    # triangle always lies on its boundary).
    ab = b - a
    ac = c - a
    ap = points - a
    v00 = float(ab @ ab)
    v01 = float(ab @ ac)
    v11 = float(ac @ ac)
    den = v00 * v11 - v01 * v01
    vp = ap @ ab
    wp = ap @ ac
    q = np.empty_like(points)
    inside = np.zeros(len(points), dtype=bool)
    if den > 1e-30:
        v = (vp * v11 - wp * v01) / den
        w = (wp * v00 - vp * v01) / den
        u = 1.0 - v - w
        inside = (u >= 0.0) & (v >= 0.0) & (w >= 0.0)
        q[inside] = (a + v[inside, None] * ab + w[inside, None] * ac)
    if not inside.all():
        rest = ~inside
        qsegs = [_closest_point_segment(points, a, b),
                 _closest_point_segment(points, b, c),
                 _closest_point_segment(points, c, a)]
        distances = np.stack(
            [np.linalg.norm(points - qseg, axis=1) for qseg in qsegs],
            axis=0)
        best = distances.argmin(axis=0)
        chosen = np.where((best == 0)[:, None], qsegs[0],
                np.where((best == 1)[:, None], qsegs[1], qsegs[2]))
        q[rest] = chosen[rest]
    return q


def nearest_triangle_distances(points, triangle_vertices, *,
                               chunk_size=128):
    """Distance from each point to the nearest of M triangles.

    points: (N, 3) float array; triangle_vertices: (M, 3, 3) float array.
    Returns (N,) min distances. Chunked to bound peak memory.
    """
    p = np.asarray(points, dtype=np.float64)
    t = np.asarray(triangle_vertices, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise MouthAnatomyError('E_DISTANCE_POINTS')
    if t.ndim != 3 or t.shape[1:] != (3, 3) or not np.isfinite(t).all():
        raise MouthAnatomyError('E_DISTANCE_TRIANGLES')
    if len(t) < 1:
        raise MouthAnatomyError('E_DISTANCE_TRIANGLES_EMPTY')
    if chunk_size < 1:
        raise MouthAnatomyError('E_DISTANCE_CHUNK')
    out = np.empty(len(p), dtype=np.float64)
    for start in range(0, len(p), chunk_size):
        chunk = p[start:start + chunk_size]
        best = np.full(len(chunk), np.inf, dtype=np.float64)
        for tri in t:
            a, b, c = tri
            q = _closest_point_triangle(chunk, a, b, c)
            d = np.linalg.norm(chunk - q, axis=1)
            best = np.minimum(best, d)
        out[start:start + chunk_size] = best
    return out


def distance_summary(distances):
    """Summarise nearest-neighbour distances for audit reports."""
    d = np.asarray(distances, dtype=np.float64)
    if d.ndim != 1 or len(d) < 1 or not np.isfinite(d).all():
        raise MouthAnatomyError('E_DISTANCE_SUMMARY')
    return {
        'min_m': round(float(d.min()), 9),
        'median_m': round(float(np.median(d)), 9),
        'max_m': round(float(d.max()), 9),
        'touching_count_lt_1e-4': int((d < 1e-4).sum()),
        'sample_count': len(d),
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
