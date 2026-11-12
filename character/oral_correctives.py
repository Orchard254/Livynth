"""Opt-in oral corrective shapes derived from the native body's existing jaw morphs.

Body shape targets and 163-joint skeleton remain unchanged. Attachments get
independent shape keys with the SAME facial-control names, so the diagnostic
runner can drive body and oral anatomy together. GLB export is NOT established.
"""
from __future__ import annotations

import math
import numpy as np

SCHEMA = 'livynth.oral-correctives.v1'
POSE_TO_KEY = {'jaw_open': 'jawOpen', 'viseme_aa': 'viseme_aa'}
MAX_CORRECTIVE_M = 0.030


class OralCorrectiveError(ValueError):
    pass


def _vertices(points, label):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4 or not np.isfinite(p).all():
        raise OralCorrectiveError('E_' + label + '_VERTICES')
    return p


def derive_lower_jaw_translation(body_neutral, body_pose):
    """Estimate coherent lower-mouth displacement from the original BODY morph.

    Uses the verified MPFB human convention (front is -Y, Z is up);
    refuses unfamiliar anatomy or implausible movement instead of guessing.
    """
    original = _vertices(body_neutral, 'BODY')
    after = _vertices(body_pose, 'BODY_POSE')
    if original.shape != after.shape:
        raise OralCorrectiveError('E_BODY_MORPH_LAYOUT')
    crown = float(original[:, 2].max())
    h = float(np.ptp(original[:, 2]))
    if not 1.0 <= h <= 2.5:
        raise OralCorrectiveError('E_BODY_HEIGHT')
    depth = (crown - original[:, 2]) / h
    mask = ((depth > 0.106) & (depth < 0.147) &
            (np.abs(original[:, 0]) / h < 0.039) &
            (original[:, 1] / h < -0.035))
    delta = after - original
    moving = mask & (np.linalg.norm(delta, axis=1) > 0.001)
    if np.count_nonzero(moving) < 12:
        raise OralCorrectiveError('E_JAW_ANCHORS_INERT')
    translation = np.median(delta[moving], axis=0)
    distance = float(np.linalg.norm(translation))
    if (not math.isfinite(distance) or distance < 0.001 or
        distance > MAX_CORRECTIVE_M or translation[2] >= -0.0005):
        raise OralCorrectiveError('E_JAW_TRANSLATION_UNSAFE')
    return translation, {
        'schema': SCHEMA,
        'source': 'MEDIAN_MOVING_LOWER_MOUTH_NATIVE_BODY_MORPH',
        'anchor_count': int(np.count_nonzero(moving)),
        'translation_body_m': [round(float(t), 9) for t in translation],
        'translation_magnitude_m': round(distance, 9),
        'coherent_downward_motion': True,
        'photorealistic_oral_contact': 'NOT_TESTED',
    }


def dental_influence(points_in_body_space, *, category):
    """Tongue follows the lower jaw; primarily lower half of teeth follows.

    Dental segmentation is deliberately conservative and unapproved until
    visual inspection. Upper teeth should remain at neutral position.
    """
    p = _vertices(points_in_body_space, 'ASSET')
    if category == 'tongue':
        return np.ones(len(p), dtype=np.float64)
    if category != 'teeth':
        raise OralCorrectiveError('E_UNSUPPORTED_ORAL_CATEGORY')
    z = p[:, 2]
    span = float(np.ptp(z))
    if span < 0.006 or span > 0.15:
        raise OralCorrectiveError('E_TEETH_SPAN_INVALID')
    median = float(np.median(z))
    t = np.clip((median - z) / 0.003 + 0.5, 0.0, 1.0)
    weights = t * t * (3.0 - 2.0 * t)
    if (np.count_nonzero(weights > 0.8) < len(weights) * 0.10 or
        np.count_nonzero(weights < 0.2) < len(weights) * 0.10):
        raise OralCorrectiveError('E_TEETH_NOT_SEGMENTABLE')
    return weights


def corrected_asset_points(points_in_body_space, translation_body, *, category):
    p = _vertices(points_in_body_space, 'ASSET')
    shift = np.asarray(translation_body, dtype=np.float64)
    if shift.shape != (3,) or not np.isfinite(shift).all():
        raise OralCorrectiveError('E_JAW_TRANSLATION_INVALID')
    magnitude = float(np.linalg.norm(shift))
    if magnitude < 0.001 or magnitude > MAX_CORRECTIVE_M:
        raise OralCorrectiveError('E_JAW_TRANSLATION_UNSAFE')
    weights = dental_influence(p, category=category)
    moved = p + weights[:, None] * shift[None, :]
    distance = np.linalg.norm(moved - p, axis=1)
    return moved, {
        'category': category,
        'vertex_count': len(p),
        'moved_vertices_gt_0_1_mm': int(np.count_nonzero(distance > 0.0001)),
        'stationary_vertices_lt_0_1_mm': int(np.count_nonzero(distance <= 0.0001)),
        'max_displacement_m': round(float(distance.max()), 9),
        'morph_name_contract': 'SAME_FACE_MORPH_NAMES_ON_ACCESSORY',
        'visual_anatomy': 'PENDING_REVIEW',
    }


def add_oral_shape_keys(body, assets):
    """Build accessory-only corrective shapes on a copied Blender scene.

    No jaw bone, source body, or already-exported GLB is modified. Each
    accessory receives the same jawOpen and viseme_aa key names as the body.
    """
    from mathutils import Vector
    if set(assets) != {'teeth', 'tongue'}:
        raise OralCorrectiveError('E_REQUIRES_TEETH_AND_TONGUE')
    keys = body.data.shape_keys
    if keys is None or not all(name in keys.key_blocks for name in POSE_TO_KEY.values()):
        raise OralCorrectiveError('E_BODY_FACIAL_TARGETS_MISSING')
    neutral = np.asarray([tuple(x.co) for x in keys.key_blocks['Basis'].data],
                         dtype=np.float64)
    translations = {}
    audits = {}
    for pose, key_name in POSE_TO_KEY.items():
        posed = np.asarray([tuple(x.co) for x in keys.key_blocks[key_name].data],
                           dtype=np.float64)
        translations[pose], audits[pose] = derive_lower_jaw_translation(neutral, posed)

    # Validate both assets and every pose before adding any Blender keys.
    pending = {}
    for category, asset in assets.items():
        if asset.type != 'MESH' or len(asset.data.vertices) < 4:
            raise OralCorrectiveError('E_ACCESSORY_NOT_MESH_' + category)
        existing = asset.data.shape_keys
        if existing is not None and any(x in existing.key_blocks
                                        for x in POSE_TO_KEY.values()):
            raise OralCorrectiveError('E_ORAL_KEY_ALREADY_EXISTS_' + category)
        to_body = body.matrix_world.inverted() @ asset.matrix_world
        original = np.asarray([tuple(to_body @ v.co) for v in asset.data.vertices],
                              dtype=np.float64)
        planned = {}
        for pose in POSE_TO_KEY:
            dest, metrics = corrected_asset_points(
                original, translations[pose], category=category)
            planned[pose] = (dest, metrics)
        pending[category] = (asset, planned)

    for category, (asset, planned) in pending.items():
        if asset.data.shape_keys is None:
            asset.shape_key_add(name='Basis', from_mix=False)
        for pose, key_name in POSE_TO_KEY.items():
            shape = asset.shape_key_add(name=key_name, from_mix=False)
            body_targets, metrics = planned[pose]
            asset_from_world = asset.matrix_world.inverted()
            for i, target_body in enumerate(body_targets):
                world = body.matrix_world @ Vector(tuple(float(v) for v in target_body))
                shape.data[i].co = asset_from_world @ world
            shape.value = 0.0
            audits[pose][category] = metrics
        asset.data.update()
    return audits
