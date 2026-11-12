"""IDENTITY-020: isolated in-memory Blender copy proof for actual MPFB dental seam.

No fitted human, rig, source asset editing, GLB export or rendering.
This proof is deliberately weaker than validating a rigged/animated copy.
"""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path

from character.mhclo_dentition import classify_dentition_mhclo
from tools.mhclo_dental_preflight import DentalPreflightError


class SeamCopyError(ValueError):
    pass


def load_obj_positions(filename, *, max_vertices=100000):
    path = Path(filename)
    if not path.is_file() or path.is_symlink():
        raise SeamCopyError('E_SEAM_OBJ_NOT_REGULAR')
    vertices = []
    with path.open('r', encoding='utf-8', errors='strict') as stream:
        for line in stream:
            if not line.startswith('v '):
                continue
            fields = line.split()
            if len(fields) < 4:
                raise SeamCopyError('E_SEAM_OBJ_VERTEX_FORMAT')
            try:
                coords = tuple(float(x) for x in fields[1:4])
            except ValueError as exc:
                raise SeamCopyError('E_SEAM_OBJ_VERTEX_FORMAT') from exc
            if not all(math.isfinite(x) for x in coords):
                raise SeamCopyError('E_SEAM_OBJ_NONFINITE')
            vertices.append(coords)
            if len(vertices) > max_vertices:
                raise SeamCopyError('E_SEAM_OBJ_VERTEX_LIMIT')
    if len(vertices) < 32:
        raise SeamCopyError('E_SEAM_OBJ_EMPTY')
    return vertices


def plan_seam_copy(mappings, faces, diagnostic):
    """Require established real-asset bridge proof before permitting any copy."""
    if not isinstance(diagnostic, dict) or not isinstance(faces, (list, tuple)):
        raise SeamCopyError('E_SEAM_PLAN_INPUT')
    dry = diagnostic.get('seam_cut_dry_run')
    if not isinstance(dry, dict):
        raise SeamCopyError('E_SEAM_PLAN_NO_DRY_RUN')
    bridge = dry.get('bridge_face_indices_preview')
    count = dry.get('bridge_faces_to_exclude')
    if (type(count) is not int or not 1 <= count <= 32 or
        not isinstance(bridge, list) or len(bridge) != count or
        any(type(i) is not int or not 0 <= i < len(faces) for i in bridge) or
        len(set(bridge)) != count or
        dry.get('original_faces') != len(faces) or
        dry.get('remaining_faces') != len(faces) - count or
        dry.get('newly_unused_vertices') != 0 or
        dry.get('all_remaining_faces_single_jaw') is not True or
        dry.get('before', {}).get('nonmanifold_edges') != 0 or
        dry.get('after', {}).get('nonmanifold_edges') != 0 or
        dry.get('after', {}).get('connected_vertex_components') !=
          dry.get('before', {}).get('connected_vertex_components', -100) + 1):
        raise SeamCopyError('E_SEAM_PLAN_UNSAFE_TO_EXCLUDE')
    excluded = set(bridge)
    kept = [tuple(face) for i, face in enumerate(faces) if i not in excluded]
    if len(kept) != len(faces) - count:
        raise SeamCopyError('E_SEAM_PLAN_FACE_COUNT')
    # Re-run the existing PRODUCTION classifier on hypothetically retained
    # topology. Its strict mixed-face rule is not modified or bypassed.
    mask, audit = classify_dentition_mhclo(len(mappings), mappings, kept)
    if audit['mixed_jaw_faces'] != 0:
        raise SeamCopyError('E_SEAM_PLAN_STILL_MIXED')
    return bridge, kept, mask, audit


def prove_temporary_blender_mesh_copy(obj_file, mappings, faces, diagnostic):
    """Test BMesh FACES_ONLY on temporary geometry, then destroy both meshes."""
    import bpy
    import bmesh

    bridge, retained, _mask, audit = plan_seam_copy(mappings, faces, diagnostic)
    points = load_obj_positions(obj_file)
    if len(points) != len(mappings):
        raise SeamCopyError('E_SEAM_COPY_OBJ_COUNT')

    original = bpy.data.meshes.new('livynth_seam_probe_temporary_original')
    temporary = None
    bm = None
    try:
        original.from_pydata(points, [], faces)
        original.update()
        if (len(original.vertices) != len(points) or
            len(original.polygons) != len(faces)):
            raise SeamCopyError('E_SEAM_COPY_INPUT_MESH')
        temporary = original.copy()
        bm = bmesh.new()
        bm.from_mesh(temporary)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        original_id = bm.verts.layers.int.new('livynth_probe_original_id')
        for i, vertex in enumerate(bm.verts):
            vertex[original_id] = i
        bmesh.ops.delete(
            bm, geom=[bm.faces[i] for i in bridge], context='FACES_ONLY')
        bm.to_mesh(temporary)
        temporary.update()
        bm.free()
        bm = None

        if (len(temporary.vertices) != len(points) or
            len(temporary.polygons) != len(retained)):
            raise SeamCopyError('E_SEAM_COPY_TOPOLOGY_COUNT')
        identity = temporary.attributes.get('livynth_probe_original_id')
        if (identity is None or len(identity.data) != len(points) or
            [int(item.value) for item in identity.data] != list(range(len(points)))):
            raise SeamCopyError('E_SEAM_COPY_VERTEX_REORDERED')
        max_error = max(max(abs(float(v.co[j]) - points[i][j]) for j in range(3))
                        for i, v in enumerate(temporary.vertices))
        if not math.isfinite(max_error) or max_error > 0.000002:
            raise SeamCopyError('E_SEAM_COPY_POSITION_DRIFT')
        saved_faces = Counter(tuple(v for v in poly.vertices)
                              for poly in temporary.polygons)
        if saved_faces != Counter(retained):
            raise SeamCopyError('E_SEAM_COPY_FACES_DIFFER')
        if (len(original.vertices) != len(points) or
            len(original.polygons) != len(faces)):
            raise SeamCopyError('E_SEAM_COPY_ORIGINAL_CHANGED')
        return {
            'status':'PASS_ISOLATED_BLENDER_COPY_NOT_RIG_OR_VISUAL_QA',
            'removed_faces':len(bridge),
            'remaining_faces':len(retained),
            'vertices_preserved':len(points),
            'original_vertex_order_preserved':True,
            'max_position_error_m':round(max_error,9),
            'retained_faces_identical':True,
            'post_cut_upper_vertices':audit['upper_teeth_vertices'],
            'post_cut_lower_vertices':audit['lower_teeth_vertices'],
            'production_classifier_on_retained_faces':audit['status'],
            'installed_obj_modified':False,
            'original_in_memory_mesh_modified':False,
            'existing_glbs_modified':False,
            'rigging_preserved':'NOT_TESTED',
            'visual_quality':'NOT_TESTED',
        }
    finally:
        if bm is not None:
            bm.free()
        if temporary is not None:
            bpy.data.meshes.remove(temporary)
        bpy.data.meshes.remove(original)
