#!/usr/bin/env python3
"""IDENTITY-029: oral visibility and lip-aperture analysis (pure NumPy).

This module is deliberately free of Blender so every measurement is
unit-testable on any host. It answers two questions from rendered
images:

1. **Dental visibility** - how much of each dental arch is actually
   visible to the camera once the lips are in front of it. The caller
   renders the arches in a diagnostic colour and provides an
   "arch-only" silhouette render (body hidden); the intersection of the
   two masks is the visible area and the ratio to the silhouette area is
   the visibility fraction.

2. **Lip-aperture shape** - the outline of the dark oral opening in the
   render. The upper and lower boundary curves are extracted per image
   column and a dimensionless *V-shape* score is computed: how far the
   corners sit relative to the aperture centre, normalised by the
   aperture height. A natural relaxed mouth reads close to 0 (the
   corners are level with the centre of the opening); a sharp inverted
   "V" (apex at the centre) reads strongly negative, a frown reads
   strongly positive.

Nothing here reads or writes an asset file.
"""
from __future__ import annotations

import math

import numpy as np

SCHEMA = 'livynth.oral-visibility.v1'

# IDENTITY-029 lip-correction defaults. The two z bands bracket the two
# borders of the oral fissure measured on the copied body (the upper
# lip's lower edge and the lower lip's upper edge); every field is a
# smooth, bounded function so the skin never folds.
UPPER_BORDER_Z_CENTER_M = 1.5300
UPPER_BORDER_Z_HALF_SPAN_M = 0.0180
LOWER_BORDER_Z_CENTER_M = 1.4970
LOWER_BORDER_Z_HALF_SPAN_M = 0.0180
CORNER_X_PEAK_M = 0.0405
CORNER_X_HALF_SPAN_M = 0.0160
CENTRE_X_HALF_SPAN_M = 0.0160
MAX_LIP_RESHAPE_M = 0.0100


class OralVisibilityError(ValueError):
    pass


def _rgb(image):
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] not in (3, 4):
        raise OralVisibilityError('E_IMAGE_LAYOUT')
    if a.shape[2] == 4:
        a = a[:, :, :3]
    if not np.isfinite(a).all():
        raise OralVisibilityError('E_IMAGE_FINITE')
    return a


def alpha_mask(image):
    """Foreground mask of an RGBA render (transparent film -> alpha 0)."""
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 4:
        raise OralVisibilityError('E_ALPHA_LAYOUT')
    if not np.isfinite(a).all():
        raise OralVisibilityError('E_ALPHA_FINITE')
    return a[:, :, 3] > 0.5


def _color_mask(rgb, color, tolerance):
    c = np.asarray(color, dtype=np.float64)
    if c.shape != (3,) or not np.isfinite(c).all():
        raise OralVisibilityError('E_COLOR')
    t = float(tolerance)
    if not math.isfinite(t) or t <= 0.0 or t > 1.0:
        raise OralVisibilityError('E_TOLERANCE')
    return (np.abs(rgb - c.reshape(1, 1, 3)).max(axis=2) <= t)


def classify_arch_pixels(rgb, *, upper_color, lower_color,
                         tolerance=0.06):
    """Boolean masks for the upper arch, the lower arch and everything else.

    The diagnostic renders tint the two arches with distinct saturated
    colours; a pixel belongs to an arch when it is within ``tolerance``
    of that colour in the widest RGB channel.
    """
    a = _rgb(rgb)
    upper = _color_mask(a, upper_color, tolerance)
    lower = _color_mask(a, lower_color, tolerance)
    overlap = upper & lower
    if overlap.any():
        # a pixel cannot be both arches: assign to the closer colour
        du = np.abs(a - np.asarray(upper_color, dtype=np.float64)
                    .reshape(1, 1, 3)).max(axis=2)
        dl = np.abs(a - np.asarray(lower_color, dtype=np.float64)
                    .reshape(1, 1, 3)).max(axis=2)
        upper = upper & ~(overlap & (dl < du))
        lower = lower & ~(overlap & (du <= dl))
    return {'upper': upper, 'lower': lower, 'other': ~(upper | lower)}


def visibility_metrics(silhouette, visible):
    """Visibility fraction of a silhouette that survived occlusion."""
    s = np.asarray(silhouette, dtype=bool)
    v = np.asarray(visible, dtype=bool)
    if s.shape != v.shape:
        raise OralVisibilityError('E_VISIBILITY_SHAPE')
    total = int(s.sum())
    if total == 0:
        raise OralVisibilityError('E_VISIBILITY_EMPTY')
    seen = int((s & v).sum())
    return {
        'silhouette_pixels': total,
        'visible_pixels': seen,
        'occluded_pixels': total - seen,
        'visible_fraction': round(float(seen) / float(total), 6),
        'occluded_fraction': round(1.0 - float(seen) / float(total), 6),
    }


def aperture_profile(mask):
    """Upper and lower boundary of a binary oral-aperture mask.

    Returns, per occupied image column, the top-most and bottom-most
    masked row, plus the aggregate shape metrics.
    """
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2:
        raise OralVisibilityError('E_APERTURE_LAYOUT')
    height, width = m.shape
    rows = np.arange(height, dtype=np.int64)
    columns = []
    for x in range(width):
        col = np.nonzero(m[:, x])[0]
        if len(col) == 0:
            continue
        columns.append((x, int(col[0]), int(col[-1]), int(len(col))))
    if not columns:
        raise OralVisibilityError('E_APERTURE_EMPTY')
    arr = np.asarray(columns, dtype=np.int64)
    xs = arr[:, 0]
    top = arr[:, 1].astype(np.float64)
    bottom = arr[:, 2].astype(np.float64)
    fill = arr[:, 3].astype(np.float64)
    span = bottom - top
    width_px = int(xs.max() - xs.min() + 1)
    area = int(fill.sum())
    # centre column = the occupied column closest to the mask centre
    centre_x = int(round((xs.min() + xs.max()) / 2.0))
    centre_index = int(np.argmin(np.abs(xs - centre_x)))
    centre_top = float(top[centre_index])
    centre_bottom = float(bottom[centre_index])
    centre_height = max(centre_bottom - centre_top, 1.0)
    # corners: the extreme occupied columns
    left_index = 0
    right_index = len(xs) - 1
    left_top = float(top[left_index])
    left_bottom = float(bottom[left_index])
    right_top = float(top[right_index])
    right_bottom = float(bottom[right_index])
    corner_top = 0.5 * (left_top + right_top)
    corner_bottom = 0.5 * (left_bottom + right_bottom)
    corner_mid = 0.5 * (corner_top + corner_bottom)
    centre_mid = 0.5 * (centre_top + centre_bottom)
    # V score: negative when the centre of the opening sits ABOVE the
    # corners (the inverted-V / "peak" defect), positive for a frown.
    MIN_VIABLE_HEIGHT_PX = 3.0
    MIN_VIABLE_AREA_PX = 20
    degenerate = bool(centre_height < MIN_VIABLE_HEIGHT_PX or
                      area < MIN_VIABLE_AREA_PX)
    if degenerate:
        v_score = 0.0
    else:
        v_score = (centre_mid - corner_mid) / centre_height
        v_score = max(-5.0, min(5.0, float(v_score)))
    return {
        'columns': int(len(xs)),
        'x_min': int(xs.min()),
        'x_max': int(xs.max()),
        'width_px': width_px,
        'area_px': area,
        'centre_column_x': centre_x,
        'centre_top_px': round(centre_top, 3),
        'centre_bottom_px': round(centre_bottom, 3),
        'centre_height_px': round(centre_height, 3),
        'left_top_px': round(left_top, 3),
        'left_bottom_px': round(left_bottom, 3),
        'right_top_px': round(right_top, 3),
        'right_bottom_px': round(right_bottom, 3),
        'corner_mid_px': round(corner_mid, 3),
        'centre_mid_px': round(centre_mid, 3),
        'v_score': round(float(v_score), 6),
        'degenerate': bool(degenerate),
        'mean_aperture_height_px': round(float(span.mean()), 3),
        'max_aperture_height_px': round(float(span.max()), 3),
        'fill_ratio': round(float(area) / float(width_px * centre_height), 6)
        if width_px and centre_height else 0.0,
    }


def aperture_top_curve(mask, columns=None):
    """Top boundary row per occupied column (list of (x, row))."""
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2:
        raise OralVisibilityError('E_APERTURE_LAYOUT')
    height, width = m.shape
    result = []
    for x in range(width):
        if columns is not None and x not in columns:
            continue
        col = np.nonzero(m[:, x])[0]
        if len(col):
            result.append((x, int(col[0])))
    return result


def aperture_bottom_curve(mask):
    """Bottom boundary row per occupied column (list of (x, row))."""
    m = np.asarray(mask, dtype=bool)
    if m.ndim != 2:
        raise OralVisibilityError('E_APERTURE_LAYOUT')
    height, width = m.shape
    result = []
    for x in range(width):
        col = np.nonzero(m[:, x])[0]
        if len(col):
            result.append((x, int(col[-1])))
    return result


def dark_aperture_mask(rgb, *, max_luma=0.42, min_luma=0.0):
    """Mask of the dark oral opening (the cavity interior) in a render.

    The cavity material is dark and non-reflective; the clay skin and the
    enamel are much brighter. The threshold is a luminance ceiling so the
    mask captures the opening, not specular highlights on teeth.
    """
    a = _rgb(rgb)
    luma = a[:, :, 0] * 0.2126 + a[:, :, 1] * 0.7152 + a[:, :, 2] * 0.0722
    if not math.isfinite(max_luma) or not 0.0 < max_luma < 1.0:
        raise OralVisibilityError('E_APERTURE_LUMA')
    return (luma <= float(max_luma)) & (luma >= float(min_luma))


def cavity_aperture_mask(rgb, *, cavity_color, tolerance=0.06):
    """Mask of the oral aperture from the flat-green cavity diagnostic.

    The diagnostic render paints the oral-cavity polygons with an
    unlit green emission material, so the aperture is recovered exactly
    instead of being guessed from a luminance threshold.
    """
    a = _rgb(rgb)
    return _color_mask(a, cavity_color, tolerance)


def _quartic(value):
    return np.clip(1.0 - value ** 2, 0.0, 1.0) ** 2


def _band(points_z, center, half_span, name, label):
    if not math.isfinite(center) or not math.isfinite(half_span) or \
            half_span <= 0.0:
        raise OralVisibilityError('E_LIP_BAND_' + name + '_' + label)
    return _quartic((points_z - center) / half_span)


def plan_lip_almonder(points, *,
                      upper_centre_drop=0.0016,
                      lower_corner_lift=0.0000,
                      lower_roll_push=0.0022,
                      upper_band_center=UPPER_BORDER_Z_CENTER_M,
                      upper_band_half=UPPER_BORDER_Z_HALF_SPAN_M,
                      lower_band_center=LOWER_BORDER_Z_CENTER_M,
                      lower_band_half=LOWER_BORDER_Z_HALF_SPAN_M,
                      corner_x_peak=CORNER_X_PEAK_M,
                      corner_x_half=CORNER_X_HALF_SPAN_M,
                      centre_x_half=CENTRE_X_HALF_SPAN_M,
                      lower_roll_z_center=1.4630,
                      lower_roll_z_half=0.0230,
                      lower_roll_x_half=0.044,
                      label='LIP_ALMOND'):
    """Reshape the oral fissure from an inverted-V toward a natural almond.

    Three bounded, smooth operations over the copied skin. None of them
    adds or removes topology; they only move the two borders of the
    oral fissure and the lower-lip roll:

    1. **Upper-border centre drop** - the upper lip's lower edge is
       pushed DOWN around the midline, with a smooth quartic falloff in
       ``x``. This converts a sharp central peak into the shallow
       cupid's-bow saddle of a natural upper lip.
    2. **Lower-border corner lift** - the lower lip's upper edge is
       lifted around the mouth corners, again with a smooth quartic
       falloff. The IDENTITY-028 corner bump narrowed the aperture to a
       point at both corners; this field widens the corners smoothly
       instead of pinching them.
    3. **Lower-roll protrusion** - the lower lip / chin band is pushed
       forward (-Y), carried over unchanged from IDENTITY-028 so the
       strongly retrusive lower face stays balanced.

    Every operation is gated to the front of the face (``y < 0``) and
    to a z band around the corresponding lip border, so the rest of the
    face is untouched. The caller applies the identical per-vertex delta
    to Basis and every shape-key block, so the correction survives every
    facial pose.

    Returns the moved points and an audit dict.
    """
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 1 or not np.isfinite(p).all():
        raise OralVisibilityError('E_POINTS_' + label)
    for name, value in (('upper_centre_drop', upper_centre_drop),
                        ('lower_corner_lift', lower_corner_lift),
                        ('lower_roll_push', lower_roll_push)):
        if not math.isfinite(value) or value < 0.0 or \
                value > MAX_LIP_RESHAPE_M:
            raise OralVisibilityError('E_LIP_BOUND_' + name + '_' + label)
    for name, value in (('corner_x_peak', corner_x_peak),
                        ('corner_x_half', corner_x_half),
                        ('centre_x_half', centre_x_half),
                        ('lower_roll_x_half', lower_roll_x_half)):
        if not math.isfinite(value) or value <= 0.0:
            raise OralVisibilityError('E_LIP_X_' + name + '_' + label)
    if not math.isfinite(lower_roll_z_center) or \
            not math.isfinite(lower_roll_z_half) or lower_roll_z_half <= 0.0:
        raise OralVisibilityError('E_LIP_BAND_lower_roll_' + label)

    x = p[:, 0]
    y = p[:, 1]
    z = p[:, 2]
    xabs = np.abs(x)
    front = (y < 0.0).astype(np.float64)

    # 1. upper-border centre drop -------------------------------------
    upper_band = _band(z, upper_band_center, upper_band_half,
                       'upper', label)
    centre_weight = _quartic(xabs / centre_x_half)
    dz_upper = -upper_centre_drop * centre_weight * upper_band * front

    # 2. lower-border corner lift --------------------------------------
    lower_band = _band(z, lower_band_center, lower_band_half,
                       'lower', label)
    corner_weight = _quartic((xabs - corner_x_peak) / corner_x_half)
    dz_lower = lower_corner_lift * corner_weight * lower_band * front

    # 3. lower-roll protrusion -----------------------------------------
    roll_band = _band(z, lower_roll_z_center, lower_roll_z_half,
                      'lower_roll', label)
    roll_weight = _quartic(xabs / lower_roll_x_half)
    dy_roll = -lower_roll_push * roll_weight * roll_band * front

    moved = p.copy()
    moved[:, 2] = z + dz_upper + dz_lower
    moved[:, 1] = y + dy_roll
    displacement = np.linalg.norm(moved - p, axis=1)
    selected = (np.abs(dz_upper) + np.abs(dz_lower) +
                np.abs(dy_roll)) > 0.0
    return moved, {
        'schema': SCHEMA,
        'operation': 'LIP_ALMOND_RESHAPE',
        'label': label,
        'selected_vertices': int(selected.sum()),
        'stationary_vertices': int((~selected).sum()),
        'upper_centre_drop_m': round(float(upper_centre_drop), 9),
        'lower_corner_lift_m': round(float(lower_corner_lift), 9),
        'lower_roll_push_m': round(float(lower_roll_push), 9),
        'upper_band_center_m': round(float(upper_band_center), 9),
        'upper_band_half_span_m': round(float(upper_band_half), 9),
        'lower_band_center_m': round(float(lower_band_center), 9),
        'lower_band_half_span_m': round(float(lower_band_half), 9),
        'corner_x_peak_m': round(float(corner_x_peak), 9),
        'corner_x_half_span_m': round(float(corner_x_half), 9),
        'centre_x_half_span_m': round(float(centre_x_half), 9),
        'lower_roll_z_center_m': round(float(lower_roll_z_center), 9),
        'lower_roll_z_half_span_m': round(float(lower_roll_z_half), 9),
        'lower_roll_x_half_span_m': round(float(lower_roll_x_half), 9),
        'max_upper_centre_drop_applied_m': round(
            float((upper_centre_drop * centre_weight * upper_band *
                   front).max()), 9),
        'max_lower_corner_lift_applied_m': round(
            float((lower_corner_lift * corner_weight * lower_band *
                   front).max()), 9),
        'max_lower_roll_push_applied_m': round(
            float((lower_roll_push * roll_weight * roll_band *
                   front).max()), 9),
        'max_displacement_m': round(float(displacement.max()), 9),
    }
