"""IDENTITY-021: prove seam surgery on a disposable copy of actual rigged teeth.

Never changes the installed MPFB asset, the MPFB source object, the character
export copy, existing GLBs, or saved blend files. No scene render.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import struct

from tools.mhclo_dental_preflight import diagnose_mixed_jaw_faces, load_obj_topology
from tools.mhclo_seam_copy_probe import plan_seam_copy

SCHEMA = 'livynth.mhclo.rigged-seam-probe.v1'


class RiggedSeamError(ValueError):
    pass


def skin_weight_digest(rows, *, vertex_count):
    """Deterministic float32 signature for Blender vertex group assignments."""
    if (type(vertex_count) is not int or vertex_count < 1 or
            len(rows) != vertex_count):
        raise RiggedSeamError('E_RIGGED_SEAM_WEIGHT_LAYOUT')
    digest = hashlib.sha256()
    weighted = 0
    assignments = 0
    for i, groups in enumerate(rows):
        entries = []
        for group, weight in groups:
            if (type(group) is not int or group < 0 or
                    isinstance(weight, bool)):
                raise RiggedSeamError('E_RIGGED_SEAM_WEIGHT_ENTRY')
            try:
                value = float(weight)
            except (TypeError, ValueError) as exc:
                raise RiggedSeamError('E_RIGGED_SEAM_WEIGHT_ENTRY') from exc
            if not math.isfinite(value) or not 0.0 <= value <= 1.000001:
                raise RiggedSeamError('E_RIGGED_SEAM_WEIGHT_ENTRY')
            entries.append((group, value))
        entries.sort()
        if len({g for g, _ in entries}) != len(entries):
            raise RiggedSeamError('E_RIGGED_SEAM_DUPLICATE_GROUP')
        if entries:
            weighted += 1
        assignments += len(entries)
        digest.update(struct.pack('<II', i, len(entries)))
        for group, weight in entries:
            digest.update(struct.pack('<If', group, weight))
    if weighted == 0:
        raise RiggedSeamError('E_RIGGED_SEAM_UNWEIGHTED')
    return {
        'sha256': digest.hexdigest(),
        'weighted_vertices': weighted,
        'assignments': assignments,
        'vertex_count': vertex_count,
    }


def _weights(obj):
    return [[(entry.group, entry.weight) for entry in vertex.groups]
            for vertex in obj.data.vertices]


def _cycles(faces, material_indices=None):
    if material_indices is None:
        material_indices = [0] * len(faces)
    def cycle(face):
        x = tuple(face)
        return min(x[i:] + x[:i] for i in range(len(x)))
    return Counter((cycle(f), m) for f, m in zip(faces, material_indices))


def prove_rigged_teeth_seam(tooth_original, tooth_copy, copy_rig,
                            mhclo_metadata, original_mhclo_path):
    """Compare real rigged teeth against a disposable duplicated Blender mesh."""
    import bpy
    import bmesh
    import numpy as np

    if (tooth_original is tooth_copy or
            tooth_original.data is tooth_copy.data or
            tooth_copy.type != 'MESH' or tooth_original.type != 'MESH' or
            copy_rig.type != 'ARMATURE' or
            tooth_copy.data.shape_keys is not None):
        raise RiggedSeamError('E_RIGGED_SEAM_ASSET_CONTRACT')

    count = len(tooth_copy.data.vertices)
    original_count, obj_faces = load_obj_topology(mhclo_metadata.obj_file)
    if count != 3868 or original_count != count or len(obj_faces) != 3560:
        raise RiggedSeamError('E_RIGGED_SEAM_PINNED_TOPOLOGY')
    copy_faces = [tuple(poly.vertices) for poly in tooth_copy.data.polygons]
    if Counter(tuple(sorted(face)) for face in copy_faces) != Counter(
            tuple(sorted(face)) for face in obj_faces):
        raise RiggedSeamError('E_RIGGED_SEAM_COPY_FACES_DIFFER_FROM_OBJ')
    src_world = np.asarray(
        [tuple(tooth_original.matrix_world @ v.co)
         for v in tooth_original.data.vertices], dtype=float)
    copy_world = np.asarray(
        [tuple(tooth_copy.matrix_world @ v.co)
         for v in tooth_copy.data.vertices], dtype=float)
    if src_world.shape != copy_world.shape or (
            float(np.linalg.norm(src_world - copy_world, axis=1).max())
            > .0001):
        raise RiggedSeamError('E_RIGGED_SEAM_COPY_VERTEX_ORDER')

    before_positions = [tuple(v.co) for v in tooth_copy.data.vertices]
    original_faces = [tuple(p.vertices) for p in tooth_original.data.polygons]
    original_coords = [tuple(v.co) for v in tooth_original.data.vertices]
    copy_face_materials = [p.material_index for p in tooth_copy.data.polygons]
    weights_before = skin_weight_digest(_weights(tooth_copy), vertex_count=count)
    groups_before = [(g.index, g.name) for g in tooth_copy.vertex_groups]
    if not any(m.type == 'ARMATURE' and m.object is copy_rig
               for m in tooth_copy.modifiers):
        raise RiggedSeamError('E_RIGGED_SEAM_ARMATURE_MISSING')

    diagnostics = diagnose_mixed_jaw_faces(mhclo_metadata.verts, copy_faces)
    dry = diagnostics['seam_cut_dry_run']
    bridge, retained, mask, audit = plan_seam_copy(
        mhclo_metadata.verts, copy_faces, diagnostics)
    if len(bridge) != 20 or len(retained) != 3540:
        raise RiggedSeamError('E_RIGGED_SEAM_UNEXPECTED_BRIDGE_COUNT')

    probe = None
    temporary_mesh = None
    bm = None
    try:
        probe = tooth_copy.copy()
        temporary_mesh = tooth_copy.data.copy()
        probe.data = temporary_mesh
        bpy.context.scene.collection.objects.link(probe)

        if ([(g.index, g.name) for g in probe.vertex_groups] != groups_before or
                not any(m.type == 'ARMATURE' and m.object is copy_rig
                        for m in probe.modifiers)):
            raise RiggedSeamError('E_RIGGED_SEAM_PROBE_RIG')
        uv_count = len(probe.data.uv_layers)
        material_names = [m.name if m else None for m in probe.data.materials]
        bm = bmesh.new()
        bm.from_mesh(temporary_mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        id_layer = bm.verts.layers.int.new('livynth_rigged_seam_original_id')
        for i, vertex in enumerate(bm.verts):
            vertex[id_layer] = i
        bmesh.ops.delete(
            bm, geom=[bm.faces[i] for i in bridge], context='FACES')
        bm.to_mesh(temporary_mesh)
        temporary_mesh.update()
        bm.free()
        bm = None

        if (len(temporary_mesh.vertices) != count or
                len(temporary_mesh.polygons) != len(retained)):
            raise RiggedSeamError('E_RIGGED_SEAM_COPY_COUNTS')
        attr = temporary_mesh.attributes.get('livynth_rigged_seam_original_id')
        if attr is None or [int(a.value) for a in attr.data] != list(range(count)):
            raise RiggedSeamError('E_RIGGED_SEAM_VERTEX_REORDERED')

        after_positions = [tuple(v.co) for v in temporary_mesh.vertices]
        position_error = max(
            abs(a[j] - b[j]) for a, b in zip(before_positions, after_positions)
            for j in range(3))
        if position_error > 2e-6:
            raise RiggedSeamError('E_RIGGED_SEAM_POSITION_DRIFT')
        retained_materials = [
            m for i, m in enumerate(copy_face_materials) if i not in set(bridge)]
        if _cycles([tuple(p.vertices) for p in temporary_mesh.polygons],
                   [p.material_index for p in temporary_mesh.polygons]) != (
                   _cycles(retained, retained_materials)):
            raise RiggedSeamError('E_RIGGED_SEAM_FACE_OR_MATERIAL_DRIFT')
        if len(temporary_mesh.uv_layers) != uv_count:
            raise RiggedSeamError('E_RIGGED_SEAM_UV_LOST')
        if [m.name if m else None for m in temporary_mesh.materials] != material_names:
            raise RiggedSeamError('E_RIGGED_SEAM_MATERIALS_CHANGED')
        if any(mask[e.vertices[0]] != mask[e.vertices[1]]
               for e in temporary_mesh.edges):
            raise RiggedSeamError('E_RIGGED_SEAM_CROSS_JAW_EDGE')
        after_weight = skin_weight_digest(_weights(probe), vertex_count=count)
        if after_weight != weights_before:
            raise RiggedSeamError('E_RIGGED_SEAM_WEIGHTS_CHANGED')
        if [(g.index, g.name) for g in probe.vertex_groups] != groups_before:
            raise RiggedSeamError('E_RIGGED_SEAM_GROUPS_CHANGED')
        if not any(m.type == 'ARMATURE' and m.object is copy_rig
                   for m in probe.modifiers):
            raise RiggedSeamError('E_RIGGED_SEAM_MODIFIER_LOST')
        if (len(tooth_copy.data.polygons) != 3560 or
                [tuple(v.co) for v in tooth_copy.data.vertices] != before_positions or
                [tuple(p.vertices) for p in tooth_original.data.polygons]
                != original_faces or
                [tuple(v.co) for v in tooth_original.data.vertices]
                != original_coords):
            raise RiggedSeamError('E_RIGGED_SEAM_ORIGINAL_OBJECT_CHANGED')
        return {
            'schema': SCHEMA,
            'status': 'PASS_RIGGED_COPY_STRUCTURE_NOT_JAW_MOTION_OR_VISUAL_QA',
            'original_faces': len(copy_faces),
            'bridge_faces_removed_on_disposable_copy': len(bridge),
            'retained_faces': len(retained),
            'vertices_preserved': count,
            'vertex_order_preserved': True,
            'max_position_error_m': round(position_error, 9),
            'skin_weight_sha256_before_after': weights_before['sha256'],
            'skin_weight_assignments': weights_before['assignments'],
            'weighted_vertices': weights_before['weighted_vertices'],
            'armature_modifier_preserved': True,
            'vertex_groups_preserved': True,
            'uv_layer_count_preserved': uv_count,
            'materials_preserved': True,
            'cross_jaw_edges_after': 0,
            'jaw_vertices': {
                'upper':audit['upper_teeth_vertices'],
                'lower':audit['lower_teeth_vertices'],
            },
            'source_asset_modified': False,
            'source_object_modified': False,
            'original_copied_object_modified': False,
            'existing_glbs_modified': False,
            'body_morphs_loaded': False,
            'facial_motion': 'NOT_TESTED',
            'visual_quality': 'NOT_TESTED',
        }
    finally:
        if bm is not None:
            bm.free()
        if probe is not None:
            bpy.data.objects.remove(probe, do_unlink=True)
        if temporary_mesh is not None and temporary_mesh.users == 0:
            bpy.data.meshes.remove(temporary_mesh)
