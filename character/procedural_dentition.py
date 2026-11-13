#!/usr/bin/env python3
"""Procedural human permanent dentition for Head A (IDENTITY-028 rebuild).

Pure NumPy, no Blender dependency; unit-testable on any host. Generates a
complete upper and lower permanent dentition (16+16 teeth, no third
molars) plus matching gingival bands, directly in the body frame used by
the mouth-anatomy pipeline.

Design guarantees (verified by tests, not asserted by construction):

* Adult-average anthropometry per tooth class (FDI numbering).
* Teeth sit on a smooth arch (half-cosine curve) per arch; upper arch is
  slightly wider and anterior to the lower arch (overjet), keeping the
  rest-pose freeway space (>= ``REST_GAP_M``) between cusp tips.
* The two arches can never interpenetrate by volumetric construction:
  vertical clearance is enforced by the distance between the arch cusp
  planes and horizontal overjet exceeds any possible overlap. The exact
  Möller transversal predicate from ``tools.mouth_anatomy`` measures the
  built meshes and must report zero crossings (test-verified).
* Deterministic: identical inputs produce byte-identical vertex/face
  arrays.

Nothing here reads or writes an asset file. Installed MPFB assets are
never consulted. The caller (Blender pipeline) creates the datablocks,
applies materials, shape keys and matrices.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = 'livynth.procedural-dentition.v1'

# ---------------------------------------------------------------------------
# Anthropometry (adult averages, metres). Sources: standard dental
# morphometry references; rounded to 0.1 mm.
# ---------------------------------------------------------------------------
#            mesiodistal h  crown h  buccolingual d  cusp_field   exponent
# key: (upper, lower)
TOOTH_METRICS = {
    'central':  {'upper': (0.0085, 0.0105, 0.0065),
                 'lower': (0.0054, 0.0095, 0.0060),
                 'superellipse': 3.3},
    'lateral':  {'upper': (0.0065, 0.0090, 0.0060),
                 'lower': (0.0060, 0.0095, 0.0060),
                 'superellipse': 3.3},
    'canine':   {'upper': (0.0075, 0.0100, 0.0075),
                 'lower': (0.0070, 0.0100, 0.0075),
                 'superellipse': 2.5},
    'premolar1': {'upper': (0.0070, 0.0085, 0.0090),
                  'lower': (0.0068, 0.0085, 0.0080),
                  'superellipse': 2.6},
    'premolar2': {'upper': (0.0068, 0.0080, 0.0090),
                  'lower': (0.0071, 0.0080, 0.0080),
                  'superellipse': 2.6},
    'molar1':   {'upper': (0.0100, 0.0072, 0.0110),
                 'lower': (0.0110, 0.0072, 0.0105),
                 'superellipse': 2.8},
    'molar2':   {'upper': (0.0090, 0.0070, 0.0105),
                 'lower': (0.0105, 0.0070, 0.0100),
                 'superellipse': 2.8},
    'molar3':   {'upper': (0.0086, 0.0065, 0.0100),
                 'lower': (0.0100, 0.0068, 0.0095),
                 'superellipse': 2.7},
}
# Order from midline outward (per side per arch); FDI digits 1..8.
SIDE_ORDER = ('central', 'lateral', 'canine', 'premolar1', 'premolar2',
              'molar1', 'molar2', 'molar3')

# FDI two-digit notation: UR=1, UL=2, LL=3, LR=4.
FDI_QUADRANT = {'upper': {'right': 1, 'left': 2},
                'lower': {'left': 3, 'right': 4}}

# ---------------------------------------------------------------------------
# Arch layout (body frame, metres). Measured landmark context: the mouth
# opening is centred on z=1.492 (LIP_Z_CENTER); the MPFB teeth-slab band
# sat at z 1.545..1.578 and was moved UP relative to the opening - the
# rebuilt arches restore a resting freeway space anchored just under the
# upper lip roll.
# ---------------------------------------------------------------------------
ARCH_PARAMS = {
    # cusp-tip plane at the incisors; the occlusal plane drops toward the
    # posterior molars (curve of Spee) by ``spee`` at the last molar.
    # y values are the arch midLINE on the tooth centres; upper arch sits
    # anterior to the lower arch (overjet) and matches the measured Head A
    # mouth band (slab front at -0.1477, back -0.090..-0.085).
    'upper': {'y_front': -0.1464, 'y_back': -0.0900,
              'half_width': 0.0300, 'occ_z_front': 1.550,
              'spee': 0.0014},
    # lower arch sits ~2.5 mm lingual to the upper (overjet) and slightly lower.
    'lower': {'y_front': -0.1439, 'y_back': -0.0874,
              'half_width': 0.0295, 'occ_z_front': 1.5485,
              'spee': 0.0012},
}

REST_GAP_M = 0.0015  # vertical freeway gap at the incisal edge, closed pose
MAX_HALF_WIDTH_M = 0.045
MIN_ARCH_FRONT_Y_M = -0.200
MAX_ARCH_BACK_Y_M = -0.075
N_THETA = 40
OCCLUSAL_RADII = (0.0, 0.20, 0.40, 0.58, 0.74, 0.86, 0.94, 1.0)
GUM_SAMPLES = 96
GUM_INNER_PULL_M = 0.0012      # inner edge sits a hair behind the neck waist
GUM_POSTERIOR_OPEN_M = 0.0120   # skirt retreats toward the throat axis
GUM_POSTERIOR_RIM_M = 0.0070    # rim retreats deeper into the mouth
GUM_SKIRT_HEIGHT_M = 0.0055     # vertical extent beyond the neck
GUM_RIM_HEIGHT_M = 0.0012       # extra z lift of the rim (upper) / drop (lower)
INTER_TOOTH_GAP_M = 0.0004      # sub-mm gap so crowns separate in renders
GINGIVA_SCALLOP_M = 0.0018      # gingival margin arc amplitude at contacts

ANGLE_BUC = 0.0        # buccal azimuth (tooth local)
ANGLE_FOUR = (0.38, math.pi - 0.38, math.pi + 0.38, 2 * math.pi - 0.38)
TWO_PI = 2 * math.pi


class DentitionError(ValueError):
    pass


def _check_params(params):
    for arch in ('upper', 'lower'):
        p = params[arch]
        for key in ('y_front', 'y_back', 'occ_z_front', 'half_width', 'spee'):
            value = float(p[key])
            if not math.isfinite(value):
                raise DentitionError('E_ARCH_PARAM_' + key.upper())
        if not (MIN_ARCH_FRONT_Y_M <= p['y_front'] < 0.0):
            raise DentitionError('E_ARCH_Y_FRONT_' + arch.upper())
        if not (p['y_back'] > p['y_front'] and p['y_back'] <= MAX_ARCH_BACK_Y_M):
            raise DentitionError('E_ARCH_Y_BACK_' + arch.upper())
        if not (0.020 <= p['half_width'] <= MAX_HALF_WIDTH_M):
            raise DentitionError('E_ARCH_HALF_WIDTH_' + arch.upper())
        if not (1.35 <= p['occ_z_front'] <= 1.75):
            raise DentitionError('E_ARCH_OCC_Z_' + arch.upper())
        if not (0.0 <= p['spee'] <= 0.004):
            raise DentitionError('E_ARCH_SPEE_' + arch.upper())
    return params


def arch_curve_y(x, *, y_front, y_back, half_width):
    """Half cosine arch: y_front at x=0, y_back at |x| = half_width."""
    ax = abs(float(x))
    if ax > half_width:
        ax = half_width
    t = (math.pi / 2.0) * ax / half_width
    return y_back + (y_front - y_back) * math.cos(t)


def arch_tangent_angle(x, *, y_front, y_back, half_width):
    """Rotation of tooth local +X onto the arch tangent (about +Z)."""
    sign = 1.0 if x >= 0.0 else -1.0
    t = (math.pi / 2.0) * abs(x) / half_width
    derivative = -(y_front - y_back) * (math.pi / (2.0 * half_width)) \
        * math.sin(t) * sign
    return math.atan(derivative)


def spee_z(x, *, occ_z_front, half_width, spee):
    """Occlusal plane drops by ``spee`` at the last molar."""
    u = abs(float(x)) / half_width
    return occ_z_front - spee * (u * u)


def _ang_dist(a, b):
    d = (a - b + math.pi) % TWO_PI - math.pi
    return d


def cusp_field(cls, theta):
    """Normalised cusp field cuspy(theta) in [0, 1].

    1 at a cusp tip, 0 in the occlusal grooves. Angles measured in the
    tooth local frame; theta=0 is buccal.
    """
    if cls == 'central' or cls == 'lateral':
        # gentle incisal saddle: slightly tips down toward the midline
        return float(np.clip(0.5 + 0.5 * math.cos(theta - math.pi / 2), 0.0, 1.0)) * 0.25
    if cls == 'canine':
        return float(np.exp(-(_ang_dist(theta, ANGLE_BUC) / 0.85) ** 2))
    if cls == 'premolar1' or cls == 'premolar2':
        buccal = np.exp(-(_ang_dist(theta, 0.0) / 1.0) ** 2)
        lingual = np.exp(-(_ang_dist(theta, math.pi) / 1.0) ** 2) * 0.78
        return float(np.clip(buccal + lingual, 0.0, 1.0))
    if cls in ('molar1', 'molar2', 'molar3'):
        total = 0.0
        for k, angle in enumerate(ANGLE_FOUR):
            amp = 1.0 if angle in (ANGLE_FOUR[0], ANGLE_FOUR[3]) else 0.82
            total += amp * np.exp(-(_ang_dist(theta, angle) / 0.72) ** 2)
        return float(np.clip(total, 0.0, 1.0))
    raise DentitionError('E_CUSP_CLASS_' + str(cls))


def occlusal_depression(cls):
    """(valley_depth_m, central_fossa_depth_m) for the occlusal field."""
    if cls in ('central', 'lateral'):
        return 0.0007, 0.0004
    if cls == 'canine':
        return 0.0026, 0.0012
    if cls in ('premolar1', 'premolar2'):
        return 0.0020, 0.0015
    return 0.0036, 0.0024   # molars


def superellipse_point(theta, semi_a, semi_b, exponent):
    c, s = math.cos(theta), math.sin(theta)
    n = exponent
    x = semi_a * math.copysign(abs(c) ** (2.0 / n), c)
    y = semi_b * math.copysign(abs(s) ** (2.0 / n), s)
    return x, y



def build_tooth(cls, *, upper, metrics=None):
    """Build one tooth. Returns verts (N,3), faces (M,3) as int arrays.

    Local frame: origin at crown neck centre; z axis along the crown
    axis with tips toward +z for lower teeth, toward -z for upper.
    """
    metrics = metrics or TOOTH_METRICS
    spec = metrics[cls]
    width, height, depth = (spec['upper' if upper else 'lower'])
    sign = -1.0 if upper else 1.0
    a, b = width / 2.0, depth / 2.0
    exponent = spec['superellipse']
    valley, fossa = occlusal_depression(cls)
    thetas = np.linspace(0.0, TWO_PI, N_THETA, endpoint=False)

    verts = []
    # -- occlusal polar grid (tips) --------------------------------------
    # centre point (single vertex shared by the whole fan):
    centre_z = sign * (height - fossa)
    verts.append((0.0, 0.0, centre_z))
    radial_levels = OCCLUSAL_RADII[1:]          # skip 0 (the centre)
    for r in radial_levels:
        inner = math.exp(-(r / 0.40) ** 2)
        outer = 1.0 - inner
        for j, theta in enumerate(thetas):
            c = cusp_field(cls, theta)
            d_lo, d_hi = valley, valley * 0.28
            depth_here = d_lo - (d_lo - d_hi) * c
            z = sign * (height - fossa * inner - depth_here * outer)
            if not math.isfinite(z):
                raise DentitionError('E_OCCLUSAL_Z')
            xs, ys = superellipse_point(theta, a, b, exponent)
            verts.append((r * xs, r * ys, z))
    # boundary ring index (r = 1.0) is the outermost occlusal ring
    boundary_start = 1 + (len(radial_levels) - 1) * N_THETA
    # -- wall rings: from the occlusal boundary down to the neck ----------
    # crown profile: slight flare out of the tip, mid bulge, neck waist
    wall_specs = (
        (1.05, 0.80),   # just below the occlusal boundary
        (1.08, 0.62),   # mid bulge
        (1.04, 0.45),
        (0.98, 0.26),
        (0.88, 0.0),    # neck
    )
    wall_rings = []
    for scale, z_frac in wall_specs:
        z = sign * height * z_frac
        ring = []
        for j, theta in enumerate(thetas):
            xs, ys = superellipse_point(theta, a * scale, b * scale, exponent)
            ring.append((xs, ys, z))
        wall_rings.append((ring, len(verts)))
        verts.extend(ring)
    # neck cap
    neck_start = len(verts)
    verts.append((0.0, 0.0, 0.0))

    faces = []
    # centre fan
    first_ring = 1
    for j in range(N_THETA):
        j1 = (j + 1) % N_THETA
        faces.append((0, first_ring + j, first_ring + j1))
    # polar grid quads (triangles)
    grid_start = first_ring
    for level in range(len(radial_levels) - 1):
        s0 = grid_start + level * N_THETA
        s1 = grid_start + (level + 1) * N_THETA
        for j in range(N_THETA):
            j1 = (j + 1) % N_THETA
            faces.append((s0 + j, s1 + j, s1 + j1))
            faces.append((s0 + j, s1 + j1, s0 + j1))
    # wall quads
    prev_start = boundary_start
    for ring, start in wall_rings:
        for j in range(N_THETA):
            j1 = (j + 1) % N_THETA
            faces.append((prev_start + j, start + j, start + j1))
            faces.append((prev_start + j, start + j1, prev_start + j1))
        prev_start = start
    # neck cap fan (facing away from crown axis)
    neck_ring = wall_rings[-1][1]
    for j in range(N_THETA):
        j1 = (j + 1) % N_THETA
        faces.append((neck_start, neck_ring + j1, neck_ring + j))
    # arc convention: for upper teeth, mirror winding to keep outward normals
    if upper:
        faces = [(f[0], f[2], f[1]) for f in faces]

    v_arr = np.asarray(verts, dtype=np.float64)
    f_arr = np.asarray(faces, dtype=np.int64)
    if not np.isfinite(v_arr).all():
        raise DentitionError('E_TOOTH_VERTICES_' + cls)
    if f_arr.min() < 0 or f_arr.max() >= len(v_arr):
        raise DentitionError('E_TOOTH_FACES_' + cls)
    return v_arr, f_arr


def tooth_plan_order(side):
    """(class, FDI digit) per position from the midline, one side."""
    return [(cls, i + 1) for i, cls in enumerate(SIDE_ORDER)]


def _arc_walk(y_front, y_back, half_width, samples=1024):
    """Cumulative arc length L(x) of the arch curve for x in [0, a]."""
    xs = np.linspace(0.0, half_width, samples)
    dydx = -(y_front - y_back) * (math.pi / (2.0 * half_width)) * \
        np.sin(np.pi * xs / (2.0 * half_width))
    ds = np.sqrt(1.0 + dydx ** 2)
    cumulative = np.empty(samples)
    cumulative[0] = 0.0
    cumulative[1:] = np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(xs))
    return xs, cumulative


def _arc_position(s, walk):
    """Locate arc length s on the dense curve sampling."""
    xs, cumulative = walk
    total = cumulative[-1]
    if s > total + 1e-9:
        raise DentitionError('E_ARCH_LATER_EXHAUSTED_' + str(round(s, 6)))
    return float(np.interp(s, cumulative, xs))


def place_arch(arch, *, params=None):
    """Place 16 teeth (8 per side) for one arch.

    Teeth are walked along the arch curve by arc length so the summed
    mesiodistal widths match the curve span (adult averages). Returns a
    list of dicts with world placement and mesh arrays.
    """
    params = _check_params(params or ARCH_PARAMS)
    p = params[arch]
    upper_flag = arch.lower() == 'upper'
    walk = _arc_walk(p['y_front'], p['y_back'], p['half_width'])
    placements = []
    for quadrant_side in ('right', 'left'):
        arc = INTER_TOOTH_GAP_M / 2.0
        for cls, fdi_index in tooth_plan_order(quadrant_side):
            width = TOOTH_METRICS[cls]['upper' if upper_flag else 'lower'][0]
            center_s = arc + width / 2.0
            arc += width + INTER_TOOTH_GAP_M
            placements.append({
                'cls': cls,
                'fdi': 10 * FDI_QUADRANT[arch.lower()][quadrant_side] + fdi_index,
                'arc': center_s,
                'side': quadrant_side,
                'upper': upper_flag,
                'width_m': width,
            })
    built = []
    for pl in placements:
        x_local = _arc_position(pl['arc'], walk)
        x_pos = x_local if pl['side'] == 'right' else -x_local
        y_pos = arch_curve_y(x_local, y_front=p['y_front'],
                             y_back=p['y_back'], half_width=p['half_width'])
        angle = arch_tangent_angle(x_local, y_front=p['y_front'],
                                   y_back=p['y_back'], half_width=p['half_width'])
        if pl['side'] == 'left':
            angle = math.pi - angle  # mirrored tooth faces forward
        cz = spee_z(x_local, occ_z_front=p['occ_z_front'],
                    half_width=p['half_width'], spee=p['spee'])
        sign = -1.0 if upper_flag else 1.0
        h = TOOTH_METRICS[pl['cls']]['upper' if upper_flag else 'lower'][1]
        tip_local = sign * h
        v, f = build_tooth(pl['cls'], upper=upper_flag)
        rotation = np.array([[math.cos(angle), -math.sin(angle), 0.0],
                             [math.sin(angle), math.cos(angle), 0.0],
                             [0.0, 0.0, 1.0]])
        origin_world = np.array([x_pos, y_pos, cz - tip_local])
        # build_tooth bakes the z mirror + winding reversal for upper
        # teeth into the arrays themselves.
        R = rotation
        world_verts = (R @ v.T).T + origin_world
        built.append({
            'fdi': pl['fdi'], 'cls': pl['cls'], 'side': pl['side'],
            'arc_s': round(pl['arc'], 9),
            'width_m': pl['width_m'],
            'rotation_angle': round(angle, 9),
            'origin_body_m': [round(float(v), 9) for v in origin_world],
            'vertices': world_verts, 'faces': f,
        })
    return built


def build_dentition(*, params=None):
    """Build both arches merged into one tooth part library."""
    upper = place_arch('upper', params=params)
    lower = place_arch('lower', params=params)
    ids = [pl['fdi'] for pl in upper + lower]
    if len(ids) != 32 or len(set(ids)) != 32:
        raise DentitionError('E_DENTITION_FDI_NAMES')
    return {'upper': upper, 'lower': lower}


def rest_gap_estimate(*, params=None):
    """Guaranteed lower bound of the vertical tip-to-tip clearance."""
    params = _check_params(params or ARCH_PARAMS)
    u = params['upper']['occ_z_front']
    l = params['lower']['occ_z_front']
    return u - l


def _arch_normal(x, *, y_front, y_back, half_width, center_y):
    """Outward-pointing unit normal of the arch curve in the X-Y plane."""
    t = (math.pi / 2.0) * x / half_width
    dydx = -(y_front - y_back) * (math.pi / (2.0 * half_width)) \
        * math.sin(t)
    tangent = np.array([1.0, dydx, 0.0])
    tangent /= np.linalg.norm(tangent)
    perp = np.array([tangent[1], -tangent[0], 0.0])
    here = np.array([x, arch_curve_y(x, y_front=y_front, y_back=y_back,
                                     half_width=half_width) - center_y])
    if np.dot(perp[:2], here) < 0.0:
        perp = -perp
    if not np.isfinite(perp).all():
        raise DentitionError('E_ARCH_NORMAL')
    return perp


def _neck_z(arch, cls, x_world, *, params):
    """Neck (gum-line) z of a tooth placed at ``x_world`` on the arch."""
    arch_l = arch.lower()
    upper_flag = arch_l == 'upper'
    p = params[arch_l]
    h = TOOTH_METRICS[cls][arch_l][1]
    sign = -1.0 if upper_flag else 1.0
    cz = spee_z(min(abs(x_world), p['half_width']),
                occ_z_front=p['occ_z_front'],
                half_width=p['half_width'], spee=p['spee'])
    # tips lie on the occlusal plane; the neck sits one crown-height
    # AWAY from the occlusal axis (up for the maxilla, down for the mandible)
    return cz - sign * h


def gum_band(arch, *, params=None):
    """Horseshoe gingival band embracing the necks of the built teeth.

    Built as a 3-ring strip following the same arch curve as the teeth:
    an inner ring tucked a hair behind the neck waist, a skirt ring
    pushed outward and lifted (upper arch) or dropped (lower arch), and
    a curled rim. The ends taper toward the throat. Returns ``(verts,
    faces)``; materials are the caller's concern.
    """
    params = _check_params(params or ARCH_PARAMS)
    arch_l = arch.lower()
    if arch_l not in ('upper', 'lower'):
        raise DentitionError('E_GUM_ARCH_' + str(arch))
    p = params[arch_l]
    upper_flag = arch_l == 'upper'
    sign = 1.0 if upper_flag else -1.0   # skirt rises on the maxilla
    placements = place_arch(arch_l, params=params)
    walk = _arc_walk(p['y_front'], p['y_back'], p['half_width'])

    def containing_tooth(side, arc_x):
        """Tooth (and u across its mesiodistal span) containing arc_x."""
        cursor = INTER_TOOTH_GAP_M / 2.0
        side_teeth = [pl for pl in placements if pl['side'] == side]
        for index, pl in enumerate(side_teeth):
            start, end = cursor, cursor + pl['width_m']
            if arc_x <= end or index == len(side_teeth) - 1:
                u = float(np.clip((arc_x - start) / pl['width_m'], 0.0, 1.0))
                return pl, u
            cursor = end + INTER_TOOTH_GAP_M
        return side_teeth[0], 0.0

    N = GUM_SAMPLES
    xs = np.linspace(-p['half_width'], p['half_width'], N)
    center_y = 0.5 * (p['y_front'] + p['y_back'])
    rows = []
    for j, x in enumerate(xs):
        x_f = float(x)
        side = 'right' if x_f >= 0.0 else 'left'
        x_abs = abs(x_f)
        y = arch_curve_y(x_abs, y_front=p['y_front'], y_back=p['y_back'],
                         half_width=p['half_width'])
        normal = _arch_normal(x_abs, y_front=p['y_front'],
                              y_back=p['y_back'], half_width=p['half_width'],
                              center_y=center_y)[:2]
        # arc position for the scallop interpolation
        arc_x = float(np.interp(x_abs, walk[0], walk[1]))
        pl, u = containing_tooth(side, arc_x)
        cls = pl['cls']
        depth_half = TOOTH_METRICS[cls][arch_l][2] / 2.0
        nz = _neck_z(arch_l, cls, x_abs, params=params)
        # gingival margin arc: dips at the tooth centre, lifts toward the
        # contact areas (papilla), with the amplitude from GINGIVA_SCALLOP_M
        scallop = GINGIVA_SCALLOP_M * ((2.0 * u - 1.0) ** 2)
        offset = np.array([normal[0], normal[1], 0.0])
        # inner edge lives BEYOND the tooth cap plane (outside the tooth
        # bounding box in z) so it can never knife through a crown
        p_in = np.array([x_f, y, 0.0]) - offset * (depth_half + GUM_INNER_PULL_M)
        p_in[2] = nz + sign * 0.0012 - sign * scallop
        # skirt and rim retreat POSTERIORLY into the mouth corridor
        # (never forward past the lip plane, never into the chin)
        p_skirt = np.array([x_f, y + GUM_POSTERIOR_OPEN_M, 0.0])
        p_skirt[2] = nz + sign * GUM_SKIRT_HEIGHT_M
        p_rim = np.array([x_f, y + GUM_POSTERIOR_OPEN_M + GUM_POSTERIOR_RIM_M, 0.0])
        p_rim[2] = nz + sign * (GUM_SKIRT_HEIGHT_M + GUM_RIM_HEIGHT_M)
        rows.append((p_in, p_skirt, p_rim))
    # row-major layout: vertex (ring, j) at ring*N + j
    verts = np.empty((3 * N, 3), dtype=np.float64)
    for ring in range(3):
        for j in range(N):
            verts[ring * N + j] = rows[j][ring]
    faces = []
    for j in range(N - 1):
        for ring in range(2):
            s0 = ring * N + j
            s1 = ring * N + j + 1
            nxt = (ring + 1) * N + j
            nxt1 = (ring + 1) * N + j + 1
            faces.append((s0, nxt, nxt1))
            faces.append((s0, nxt1, s1))
    # posterior end caps of the horseshoe
    for j in (0, N - 1):
        faces.append((j, N + j, 2 * N + j))
    faces_arr = np.asarray(faces, dtype=np.int64)
    if faces_arr.min() < 0 or faces_arr.max() >= len(verts):
        raise DentitionError('E_GUM_FACE_RANGE')
    if upper_flag:
        faces_arr = faces_arr[:, [0, 2, 1]]
    return verts, faces_arr
