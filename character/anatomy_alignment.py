"""Opt-in native accessory alignment for parametric head changes.

When the head mesh is sculpted in its own local coordinates, MPFB-fitted
eyeballs/teeth/tongue must receive the same identity field in the SAME
coordinate frame. Simply having an Armature modifier does not align them.

This is bind-space identity correction, NOT jaw-bone animation retargeting.
"""
from __future__ import annotations

import numpy as np
from character.head_shape import displacement_field, InvalidHeadShape

class AccessoryAlignmentError(ValueError):
    pass


def align_positions(reference_body, asset_points_in_body_space, controls):
    """Deform one accessory using the baked source body's spatial field.

    Does not mutate arrays, topology, bone weights, armature or shape keys.
    Every vertex uses source BODY bounds, never the accessory's own min/max.
    """
    ref=np.asarray(reference_body,dtype=np.float64)
    src=np.asarray(asset_points_in_body_space,dtype=np.float64)
    if (src.ndim!=2 or src.shape[1]!=3 or len(src)<4 or
        not np.isfinite(src).all()):
        raise AccessoryAlignmentError('E_ASSET_INPUT_POINTS')
    try:
        delta=displacement_field(src,controls,reference_vertices=ref)
    except InvalidHeadShape as exc:
        raise AccessoryAlignmentError('E_ASSET_IDENTITY_FIELD: '+str(exc)) from exc
    displaced=src+delta
    distances=np.linalg.norm(delta,axis=1)
    if not np.isfinite(displaced).all() or float(distances.max())>0.025:
        raise AccessoryAlignmentError('E_ASSET_WARP_LIMIT')
    return displaced,{
        'status':'IDENTITY_FIELD_APPLIED_NOT_VISUALLY_APPROVED',
        'vertices':len(src),
        'moved_vertices_gt_0_1_mm':int(np.count_nonzero(distances>0.0001)),
        'mean_displacement_m':round(float(distances.mean()),9),
        'max_displacement_m':round(float(distances.max()),9),
        'anatomical_alignment':'REQUIRES_RENDERED_REVIEW',
        'jaw_morph_bone_follow':'NOT_TESTED',
    }


def apply_to_blender_object(body, accessory, reference_body, controls):
    """Map accessory vertices into body's local bind-space, apply field, map back.

    Import Blender lazily; module remains unit-testable on a CPU-only machine.
    Transform matrices, *not* object origins, determine the shared coordinates.
    Does not touch the original MPFB human (only copied accessory meshes).
    """
    from mathutils import Vector
    if body==accessory or body.type!='MESH' or accessory.type!='MESH':
        raise AccessoryAlignmentError('E_ASSET_OBJECT_TYPE')
    to_body=body.matrix_world.inverted() @ accessory.matrix_world
    to_asset=accessory.matrix_world.inverted() @ body.matrix_world
    before=np.asarray([tuple(to_body @ v.co) for v in accessory.data.vertices],
                      dtype=np.float64)
    target,report=align_positions(reference_body,before,controls)
    for vertex,target_body in zip(accessory.data.vertices,target):
        vertex.co=to_asset @ Vector(tuple(float(x) for x in target_body))
    accessory.data.update()
    # Re-read Blender float32 storage in the same body coordinate space.
    actual=np.asarray([tuple(to_body @ v.co) for v in accessory.data.vertices],
                      dtype=np.float64)
    discrepancy=np.linalg.norm(actual-target,axis=1)
    if not np.isfinite(discrepancy).all() or float(discrepancy.max())>0.000002:
        raise AccessoryAlignmentError('E_ASSET_REALIZED_STORAGE_MISMATCH')
    report['max_storage_error_m']=round(float(discrepancy.max()),9)
    report['mesh_vertices_unchanged']=len(accessory.data.vertices)==len(before)
    return report
