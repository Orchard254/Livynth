"""IDENTITY-022: opt-in seam cut on the IN-MEMORY export-copy teeth only.

The pinned installed OBJ/MHCLO and the untouched MPFB source rig never change.
No mesh is exported. This function does not claim visual correctness.
"""
from __future__ import annotations

from tools.mhclo_dental_preflight import diagnose_mixed_jaw_faces
from tools.mhclo_seam_copy_probe import plan_seam_copy
from tools.rigged_seam_copy_probe import (
    _cycles, _weights, prove_rigged_teeth_seam, skin_weight_digest)


class JawStillsSeamError(ValueError):
    pass


def prepare_seamed_render_copy(tooth_original, tooth_copy, copy_rig, metadata):
    """Return (lower_mask, source_jaw_audit, isolated_copy_audit).

    The proven IDENTITY-021 scratch probe MUST pass before committing the same
    surgery on a DIFFERENT in-memory MPFB export-copy mesh data block.
    Roll back the object-data swap if any structural validation fails.
    """
    import bpy
    import bmesh

    proof = prove_rigged_teeth_seam(
        tooth_original, tooth_copy, copy_rig, metadata)
    if proof['status'] != 'PASS_RIGGED_COPY_STRUCTURE_NOT_JAW_MOTION_OR_VISUAL_QA':
        raise JawStillsSeamError('E_ID022_RIGGED_COPY_PROOF_REQUIRED')

    source_data = tooth_copy.data
    source_faces = [tuple(f.vertices) for f in source_data.polygons]
    source_positions = [tuple(v.co) for v in source_data.vertices]
    source_materials = [p.material_index for p in source_data.polygons]
    source_uvs = len(source_data.uv_layers)
    source_groups = [(g.index, g.name) for g in tooth_copy.vertex_groups]
    source_weights = skin_weight_digest(
        _weights(tooth_copy), vertex_count=len(source_positions))

    diagnostics = diagnose_mixed_jaw_faces(metadata.verts, source_faces)
    bridge, retained, lower_mask, jaw_audit = plan_seam_copy(
        metadata.verts, source_faces, diagnostics)
    if (len(bridge) != 20 or len(retained) != 3540 or
            len(source_positions) != 3868):
        raise JawStillsSeamError('E_ID022_UNEXPECTED_SEAM_TOPOLOGY')

    work_data = source_data.copy()
    bm = None
    swapped = False
    try:
        bm = bmesh.new()
        bm.from_mesh(work_data)
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        bm.verts.ensure_lookup_table()
        id_layer = bm.verts.layers.int.new('livynth_id022_source_vertex')
        for i, vertex in enumerate(bm.verts):
            vertex[id_layer] = i
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in bridge],
                         context='FACES')
        bm.to_mesh(work_data)
        work_data.update()
        bm.free()
        bm = None

        if (len(work_data.vertices) != 3868 or
                len(work_data.polygons) != 3540):
            raise JawStillsSeamError('E_ID022_VERTEX_FACE_COUNT')
        original_ids = work_data.attributes.get('livynth_id022_source_vertex')
        if (original_ids is None or
                [int(x.value) for x in original_ids.data] != list(range(3868))):
            raise JawStillsSeamError('E_ID022_VERTEX_ORDER')
        if (max(abs(float(v.co[j]) - source_positions[i][j])
                for i, v in enumerate(work_data.vertices) for j in range(3))
                > 0.000002):
            raise JawStillsSeamError('E_ID022_VERTEX_DRIFT')
        kept_materials = [m for i, m in enumerate(source_materials)
                          if i not in set(bridge)]
        if _cycles([tuple(p.vertices) for p in work_data.polygons],
                   [p.material_index for p in work_data.polygons]) != (
                   _cycles(retained, kept_materials)):
            raise JawStillsSeamError('E_ID022_FACES_OR_MATERIALS_CHANGED')
        if len(work_data.uv_layers) != source_uvs:
            raise JawStillsSeamError('E_ID022_UVS_CHANGED')
        if any(lower_mask[e.vertices[0]] != lower_mask[e.vertices[1]]
               for e in work_data.edges):
            raise JawStillsSeamError('E_ID022_CROSS_JAW_EDGE')

        # Commit ONLY the copied character's teeth datablock, never the
        # installed OBJ, original asset object or prior GLB.
        tooth_copy.data = work_data
        swapped = True
        if skin_weight_digest(_weights(tooth_copy),
                              vertex_count=3868) != source_weights:
            raise JawStillsSeamError('E_ID022_SKIN_WEIGHTS_CHANGED')
        if [(g.index, g.name) for g in tooth_copy.vertex_groups] != source_groups:
            raise JawStillsSeamError('E_ID022_VERTEX_GROUPS_CHANGED')
        if not any(mod.type == 'ARMATURE' and mod.object is copy_rig
                   for mod in tooth_copy.modifiers):
            raise JawStillsSeamError('E_ID022_ARMATURE_MODIFIER_CHANGED')
        if ([tuple(v.co) for v in source_data.vertices] != source_positions or
                [tuple(f.vertices) for f in source_data.polygons] !=
                source_faces):
            raise JawStillsSeamError('E_ID022_PREVIOUS_COPY_CHANGED')

        # Reclassify the REAL committed copy, not the hypothetical face list.
        from character.mhclo_dentition import classify_dentition_mhclo
        confirmed_mask, confirmed_audit = classify_dentition_mhclo(
            len(tooth_copy.data.vertices), metadata.verts,
            [tuple(poly.vertices) for poly in tooth_copy.data.polygons])
        if (confirmed_audit['mixed_jaw_faces'] != 0 or
                confirmed_audit['face_count'] != 3540 or
                not (confirmed_mask == lower_mask).all()):
            raise JawStillsSeamError('E_ID022_COMMITTED_JAW_CLASSIFICATION')
        # Classifier reports pure mapping; disclose the deliberate mesh surgery.
        confirmed_audit.update({
            'mesh_topology_modified':True,
            'modified_only_on_in_memory_export_copy':True,
            'original_obj_faces':3560,
            'cut_bridge_faces':20,
            'installed_mhclo_obj_modified':False,
            'visual_anatomy':'PENDING_INDEPENDENT_REVIEW',
        })
        report = {
            'status':'PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA',
            'source_proof_status':proof['status'],
            'source_skin_weight_sha256':source_weights['sha256'],
            'source_skin_weight_assignments':source_weights['assignments'],
            'retained_vertices':3868,
            'original_faces':3560,
            'seamed_faces':3540,
            'removed_bridge_faces':20,
            'cross_jaw_edges_after':0,
            'jaw_vertex_counts':{
                'upper':confirmed_audit['upper_teeth_vertices'],
                'lower':confirmed_audit['lower_teeth_vertices'],
            },
            'copied_teeth_mesh_modified_in_memory':True,
            'original_mpfb_asset_modified':False,
            'source_human_modified':False,
            'existing_glbs_modified':False,
            'rigged_skin_weights_preserved':True,
            'visual_quality':'NOT_TESTED',
        }
        return confirmed_mask, confirmed_audit, report
    except Exception:
        if swapped:
            tooth_copy.data = source_data
        raise
    finally:
        if bm is not None:
            bm.free()
        if not swapped or tooth_copy.data is not work_data:
            if work_data.users == 0:
                bpy.data.meshes.remove(work_data)
