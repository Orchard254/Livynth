"""Topology-preserving parametric identity controls for the baked native MPFB head.

Controls are geometric *identity hypotheses*, not image-to-3D reconstructions.
They operate on the baked 13,380-vertex mesh BEFORE ARKit face targets load.
No mesh topology, UV index, rig bone or shape key is created here.
"""
from __future__ import annotations

import hashlib
import math
import numpy as np

CONTROLS = (
    'cranial_width', 'jaw_width', 'cheek_fullness',
    'nose_projection', 'mouth_width', 'chin_length',
)
MAX_TOTAL_DISPLACEMENT_M = 0.025


class InvalidHeadShape(ValueError):
    """Fail-closed invalid controls or non-credible resulting mesh."""


def validate_controls(controls):
    if not isinstance(controls, dict) or not controls or not set(controls).issubset(CONTROLS):
        raise InvalidHeadShape('E_HEAD_CONTROL_KEYS')
    result = {}
    for key in sorted(controls):
        value = controls[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise InvalidHeadShape('E_HEAD_CONTROL_VALUE')
        if abs(value) > 1.0:
            raise InvalidHeadShape('E_HEAD_CONTROL_RANGE')
        result[key] = float(value)
    return result


def _gaussian(x, location, sigma):
    return np.exp(-0.5 * ((x - location) / sigma)**2)


def _smoothstep(x):
    t = np.clip(x, 0.0, 1.0)
    return t*t*(3-2*t)


def displacement_field(points, controls):
    """Return Nx3 deformation deltas in metres; never change the input.

    Normalized reference is based on the source mesh height. Localized deformations
    retain the same vertex indices and are mirror-symmetric across the x=0 plane.
    The face points -Y in the verified MPFB neutral (not a universal convention).
    """
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4 or not np.isfinite(p).all():
        raise InvalidHeadShape('E_HEAD_MESH_INPUT')
    c = validate_controls(controls)
    lo = p.min(axis=0)
    hi = p.max(axis=0)
    h = float(hi[2] - lo[2])
    if not 1.0 <= h <= 2.5:
        raise InvalidHeadShape('E_HEAD_BODY_HEIGHT')
    crown = hi[2]
    x, y, z = p.T
    dz = (crown-z)/h
    ax = np.abs(x)/h
    front = _smoothstep((-y/h - 0.015)/0.06)
    above_neck = _smoothstep((0.174-dz)/0.026)
    delta = np.zeros_like(p)
    if 'cranial_width' in c:
        env = _gaussian(dz,0.078,0.052) * above_neck
        delta[:,0] += (0.16*c['cranial_width']*env) * x
    if 'jaw_width' in c:
        env = (_gaussian(dz,0.133,0.024) * above_neck *
               _smoothstep((ax-0.006)/0.016))
        delta[:,0] += 0.010*c['jaw_width'] * np.sign(x)*env
    if 'cheek_fullness' in c:
        env = (_gaussian(dz,0.087,0.018) *
               _gaussian(ax,0.033,0.021) * front * above_neck)
        delta[:,1] -= 0.007*c['cheek_fullness']*env
    if 'nose_projection' in c:
        env = (_gaussian(dz,0.085,0.014) *
               _gaussian(ax,0.008,0.013) * front * above_neck)
        delta[:,1] -= 0.009*c['nose_projection']*env
    if 'mouth_width' in c:
        env = (_gaussian(dz,0.103,0.012) *
               _gaussian(ax,0.025,0.015) * front * above_neck)
        delta[:,0] += 0.006*c['mouth_width']*np.sign(x)*env
    if 'chin_length' in c:
        env = (_gaussian(dz,0.135,0.022) *
               _gaussian(ax,0.013,0.028) * front * above_neck)
        delta[:,2] -= 0.008*c['chin_length']*env
    norms = np.linalg.norm(delta,axis=1)
    if norms.max() > MAX_TOTAL_DISPLACEMENT_M:
        raise InvalidHeadShape('E_HEAD_DISPLACEMENT_LIMIT')
    return delta


def _face_vectors(points, quads):
    tri = points[quads[:,1]]-points[quads[:,0]]
    tri2 = points[quads[:,2]]-points[quads[:,0]]
    tri3 = points[quads[:,3]]-points[quads[:,0]]
    return np.cross(tri,tri2),np.cross(tri2,tri3)


def check_deformation(source, proposed, quads, *, min_local_area_ratio=0.40):
    """Reject flipped or collapsed quads; global self-intersections unverified."""
    source = np.asarray(source,dtype=np.float64)
    proposed = np.asarray(proposed,dtype=np.float64)
    faces = np.asarray(quads)
    if source.shape != proposed.shape or source.ndim != 2 or source.shape[1] != 3 or not np.isfinite(proposed).all():
        raise InvalidHeadShape('E_HEAD_DEFORMED_SHAPE')
    if faces.ndim != 2 or faces.shape[1] != 4 or not np.issubdtype(faces.dtype,np.integer) or len(faces) < 4:
        raise InvalidHeadShape('E_HEAD_QUAD_SHAPE')
    if faces.min()<0 or faces.max()>=len(source):
        raise InvalidHeadShape('E_HEAD_QUAD_INDICES')
    base = _face_vectors(source,faces)
    new = _face_vectors(proposed,faces)
    ratios=[]
    for old,now in zip(base,new):
        area_old=np.linalg.norm(old,axis=1)
        area_new=np.linalg.norm(now,axis=1)
        if (area_old<=1e-12).any():
            raise InvalidHeadShape('E_BASE_QUAD_DEGENERATE')
        if (np.einsum('ij,ij->i',old,now)<=0).any():
            raise InvalidHeadShape('E_QUAD_FLIP')
        ratios.append(area_new/area_old)
    minratio=float(min(map(np.min,ratios)))
    if minratio<min_local_area_ratio:
        raise InvalidHeadShape('E_QUAD_COLLAPSE')
    return {'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS',
            'min_triangle_area_ratio':round(minratio,6),
            'quads_checked':len(faces),
            'global_self_intersection':'UNVERIFIED'}


def apply_head_shape(points, faces, controls):
    p = np.asarray(points,dtype=np.float64)
    delta=displacement_field(p,controls)
    fit=p+delta
    audit=check_deformation(p,fit,faces)
    audit.update({'max_displacement_m':float(np.linalg.norm(delta,axis=1).max()),
                  'moved_vertices_gt_0_1_mm':int((np.linalg.norm(delta,axis=1)>0.0001).sum()),
                  'controls':validate_controls(controls),
                  'identity_likeness':'UNVERIFIED'})
    return fit,audit


def audit_realized_head_shape(source, planned, stored, quads, *, max_storage_error_m=2e-7):
    """Validate the *actual stored* vertex coordinates after Blender float32 writes.

    The fitter plans in float64, whereas Blender mesh coordinates are float32.
    Hashing the float64 plan cannot equal the hash of Blender's stored vertices.
    Compare against an explicitly quantized plan, then re-check local topology
    safety on the realized coordinates. Never accept an unverified hash swap.
    """
    source = np.asarray(source, dtype=np.float64)
    planned = np.asarray(planned, dtype=np.float64)
    stored = np.asarray(stored, dtype=np.float64)
    if (source.shape != planned.shape or source.shape != stored.shape or
        source.ndim != 2 or source.shape[1] != 3 or
        not np.isfinite(source).all() or not np.isfinite(planned).all() or
        not np.isfinite(stored).all()):
        raise InvalidHeadShape('E_HEAD_STORED_SHAPE')
    expected = planned.astype(np.float32).astype(np.float64)
    discrepancy = np.linalg.norm(expected - stored, axis=1)
    max_error = float(discrepancy.max())
    if max_error > max_storage_error_m:
        raise InvalidHeadShape('E_HEAD_STORAGE_MISMATCH')
    audit = check_deformation(source, stored, quads)
    actual_delta = np.linalg.norm(stored - source, axis=1)
    audit.update({
        'max_displacement_m': float(actual_delta.max()),
        'moved_vertices_gt_0_1_mm': int((actual_delta > 0.0001).sum()),
        'max_storage_error_m': max_error,
        'vertex_coordinate_encoding': 'Blender_mesh_float32_xyz',
        'identity_likeness': 'UNVERIFIED',
    })
    return audit
