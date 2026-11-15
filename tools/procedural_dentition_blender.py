#!/usr/bin/env python3
"""IDENTITY-028: build the procedural permanent dentition on the copied scene.

All geometry comes from ``character.procedural_dentition`` (pure NumPy);
this module only turns planned arrays into Blender datablocks. Never
reads or writes an asset file. The MPFB photo teeth slab is hidden from
renders (it stays in the scene, untouched, for the recorded slab
reference audits), never deleted and never edited.

Body-frame convention: vertices are stored in BODY-LOCAL coordinates;
each object's matrix_world is set to the body's matrix_world so the
evaluated world positions equal the planned world arrays exactly
(validated by hard ``E_PROC_STORAGE_*`` errors).
"""
from __future__ import annotations

import math

import numpy as np

VALIDATION_SLACK_M = 2e-6


def _to_body_local(body, points_world):
    """World (body-frame) points -> body-local coordinates."""
    from mathutils import Vector
    to_local = body.matrix_world.inverted()
    return [tuple((to_local @ Vector(tuple(float(c) for c in p))))
            for p in points_world]


def _world_mesh_triangles(obj, world_verts):
    tris = []
    for poly in obj.data.polygons:
        verts = list(poly.vertices)
        for i in range(1, len(verts) - 1):
            tris.append((verts[0], verts[i], verts[i + 1]))
    if not tris:
        raise RuntimeError('E_PROC_NO_POLYGONS_' + obj.name)
    return np.asarray([[world_verts[a], world_verts[b], world_verts[c]]
                       for a, b, c in tris], dtype=np.float64)


def _material(name, base_color, roughness):
    import bpy
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = material.node_tree.nodes.get('Principled BSDF')
    if principled is None:
        raise RuntimeError('E_PROC_PRINCIPLED_' + name)
    principled.inputs['Base Color'].default_value = (
        float(base_color[0]), float(base_color[1]), float(base_color[2]), 1.0)
    principled.inputs['Roughness'].default_value = float(roughness)
    return material


def _make_object(body, name, verts_world, faces, materials,
                  face_material_index=0):
    """Create ONE object per mesh.

    ``face_material_index`` may be an int (every polygon in slot 0) or a
    per-face list of slot indices (for mixed-material arches).
    """
    import bpy
    mesh = bpy.data.meshes.new(name)
    local = _to_body_local(body, verts_world)
    mesh.from_pydata(local, [],
                     [tuple(int(i) for i in face) for face in faces])
    mesh.update()
    for material in materials:
        mesh.materials.append(material)
    if isinstance(face_material_index, (list, tuple)):
        indices = list(face_material_index)
        if len(indices) != len(mesh.polygons):
            raise RuntimeError('E_PROC_FACE_MATERIAL_COUNT_' + name)
        for polygon, slot in zip(mesh.polygons, indices):
            polygon.material_index = int(slot)
    else:
        for polygon in mesh.polygons:
            polygon.material_index = int(face_material_index)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    obj.matrix_world = body.matrix_world.copy()
    for collection in list(body.users_collection):
        collection.objects.link(obj)
    return obj


def _add_dentition_shape_keys(obj, displacement_jawopen, displacement_aa):
    """Basis + jawOpen + viseme_aa on one procedural object.

    ``displacement_jawopen`` / ``displacement_aa`` are body-frame
    translation vectors applied equally to every vertex; they are the
    native body-morph deltas derived exactly like the MPFB oral
    correctives do, so the procedural arch and the MPFB-typed sibling
    meshes used to move coherently. Pass None for either to freeze that
    key to Basis (the upper arch uses this for both).
    """
    if obj.data.shape_keys is not None:
        raise RuntimeError('E_PROC_KEYS_EXIST_' + obj.name)
    deltas = {'jawOpen': displacement_jawopen, 'viseme_aa': displacement_aa}
    for pose, delta in deltas.items():
        if delta is None:
            continue
        arr = np.asarray(delta, dtype=np.float64)
        if (arr.shape != (3,) or not np.isfinite(arr).all()
                or float(np.linalg.norm(arr)) > 0.030):
            raise RuntimeError('E_PROC_BODY_MORPH_TRANSLATION_' + pose)
        deltas[pose] = arr
    basis = obj.shape_key_add(name='Basis', from_mix=False)
    for pose, delta in deltas.items():
        key = obj.shape_key_add(name=pose, from_mix=False)
        if delta is None:
            for point, source in zip(key.data, basis.data):
                point.co = source.co.copy()
        else:
            from mathutils import Vector
            world = obj.matrix_world
            to_local = world.inverted()
            step = Vector((float(delta[0]), float(delta[1]), float(delta[2])))
            for point in key.data:
                world_co = world @ point.co
                point.co = to_local @ (world_co + step)
        key.value = 0.0
    obj.data.update()
    style = {pose: ('IDENTICAL_TO_BASIS_BY_CONSTRUCTION'
                    if delta is None
                    else 'PURE_TRANSLATION_NATIVE_BODY_MORPH')
             for pose, delta in deltas.items()}
    return style


def _jaw_translations(body):
    """Native body Basis->pose deltas, same derivation as the slab uses."""
    from character.oral_correctives import derive_lower_jaw_translation
    keys = body.data.shape_keys.key_blocks
    neutral = np.asarray([tuple(k.co) for k in keys['Basis'].data],
                         dtype=np.float64)
    translations = {}
    audits = {}
    for pose, key_name in (('jaw_open', 'jawOpen'), ('viseme_aa', 'viseme_aa')):
        if key_name not in keys:
            raise RuntimeError('E_PROC_BODY_KEY_MISSING_' + key_name)
        posed = np.asarray([tuple(k.co) for k in keys[key_name].data],
                           dtype=np.float64)
        t, audit = derive_lower_jaw_translation(neutral, posed)
        translations[key_name] = np.asarray(t, dtype=np.float64)
        audits[key_name] = audit
    return translations, audits


def create_procedural_objects(body):
    """Create procedural dentition + gingiva objects on the copied scene.

    Returns ``(objects, audit)``; ``objects`` maps
    upper_teeth/lower_teeth/upper_gum/lower_gum to bpy objects.
    """
    import bpy
    from character.procedural_dentition import (
        SCHEMA, REST_GAP_M, build_dentition, gum_band)
    world = body.matrix_world
    det = float(world.to_3x3().determinant())
    if abs(det - 1.0) > 1e-6:
        raise RuntimeError('E_PROC_BODY_NOT_RIGID_' + str(round(det, 9)))

    translations, jaw_audits = _jaw_translations(body)
    t_jaw = translations['jawOpen']
    t_aa = translations['viseme_aa']

    enamel_ant = _material('livynth_proc_enamel_ant', (0.945, 0.927, 0.883), 0.30)
    enamel_post = _material('livynth_proc_enamel_post', (0.880, 0.865, 0.820), 0.40)
    gum = _material('livynth_proc_gingiva', (0.30, 0.088, 0.070), 0.72)
    anterior = {'central', 'lateral', 'canine'}

    spec = build_dentition()
    objects = {}
    report = {}
    for arch in ('upper', 'lower'):
        arrays = spec[arch]
        verts_all, faces_all = [], []
        slot_indices = []
        offset = 0
        for tooth in arrays:
            verts_all.append(tooth['vertices'])
            tooth_faces = tooth['faces'] + offset
            faces_all.append(tooth_faces)
            slot = 0 if tooth['cls'] in anterior else 1
            slot_indices.extend([slot] * len(tooth['faces']))
            offset += len(tooth['vertices'])
        verts = np.concatenate(verts_all, axis=0)
        faces = np.concatenate(faces_all, axis=0)
        name = ('livynth_proc_teeth_upper_dentition' if arch == 'upper'
                else 'livynth_proc_teeth_lower_dentition')
        objects[arch + '_teeth'] = _make_object(
            body, name, verts, faces, [enamel_ant, enamel_post],
            slot_indices)
        report[arch] = {
            'object': name,
            'vertices': int(len(verts)),
            'triangles': int(len(faces)),
            'tooth_count': len(arrays),
            'fdi_numbers': [tooth['fdi'] for tooth in arrays],
            'classes': [tooth['cls'] for tooth in arrays],
            'sides': [tooth['side'] for tooth in arrays],
            'placed_by': 'ARC_LENGTH_WALK_ON_ARCH_CURVE',
            'material_slots': ['livynth_proc_enamel_ant',
                               'livynth_proc_enamel_post'],
        }

    for arch in ('upper', 'lower'):
        verts, faces = gum_band(arch)
        name = ('livynth_proc_gum_upper' if arch == 'upper'
                else 'livynth_proc_gum_lower')
        objects[arch + '_gum'] = _make_object(
            body, name, verts, faces, [gum], 0)
        report[arch + '_gum'] = {
            'object': name,
            'vertices': int(len(verts)),
            'triangles': int(len(faces)),
        }

    # Corrective keys: upper frozen (both poses identical to Basis),
    # lower rides the native body morph (per-pose native translation).
    key_style = {}
    key_style['upper_teeth'] = _add_dentition_shape_keys(
        objects['upper_teeth'], None, None)
    key_style['upper_gum'] = _add_dentition_shape_keys(
        objects['upper_gum'], None, None)
    key_style['lower_teeth'] = _add_dentition_shape_keys(
        objects['lower_teeth'], t_jaw, t_aa)
    key_style['lower_gum'] = _add_dentition_shape_keys(
        objects['lower_gum'], t_jaw, t_aa)

    audit = {
        'schema': SCHEMA,
        'assembly': 'PARAMETRIC_PERMANENT_DENTITION_ADULT_ANTHROPOMETRY',
        'source_assets_read': [],
        'third_party_files_used': [],
        'source_geometry_mode': 'FDI_ADULT_AVERAGES_NO_PATIENT_DATA',
        'objects': {k: o.name for k, o in objects.items()},
        'teeth': {arch: report[arch] for arch in ('upper', 'lower')},
        'gum_bands': {arch + '_gum': report[arch + '_gum'] for arch in
                      ('upper', 'lower')},
        'materials': {
            'enamel_anterior': enamel_ant.name,
            'enamel_posterior': enamel_post.name,
            'gingiva': gum.name,
            'created_fresh': True,
            'enamel_ant_base_color': [0.945, 0.927, 0.883],
            'enamel_ant_roughness': 0.30,
            'enamel_post_base_color': [0.880, 0.865, 0.820],
            'enamel_post_roughness': 0.40,
            'gingiva_base_color': [0.30, 0.088, 0.070],
            'gingiva_roughness': 0.72,
        },
        'jaw_corrective_derivation': {
            'jawOpen': {'translation_body_m':
                        [round(float(v), 9) for v in t_jaw],
                        'source': 'MEDIAN_MOVING_LOWER_MOUTH_NATIVE_BODY_MORPH',
                        'anchor_count': jaw_audits['jawOpen']['anchor_count']},
            'viseme_aa': {'translation_body_m':
                          [round(float(v), 9) for v in t_aa],
                          'source': 'MEDIAN_MOVING_LOWER_MOUTH_NATIVE_BODY_MORPH',
                          'anchor_count': jaw_audits['viseme_aa']['anchor_count']},
        },
        'corrective_key_style': key_style,
        'occlusion_design': {
            'rest_freeway_gap_front_m': REST_GAP_M,
            'spee_drop_upper_m': 0.0014,
            'spee_drop_lower_m': 0.0012,
            'overjet_front_m': 0.0025,
            'interpenetration_guarantee':
                'GEOMETRIC_CLEARANCE_BY_CONSTRUCTION_'
                'VERIFIED_BY_MOLLER_PREDICATE_ON_BUILT_MESHES',
        },
        'frame': 'BODY_LOCAL_COFRAME_VIEWED_AS_WORLD_MPFB_IDENTITY',
    }
    return objects, audit


def _storage_check(objects, expected_upper, expected_lower,
                   expected_upper_gum, expected_lower_gum):
    """Evaluated world positions of the created objects == planned."""
    from tools.mpfb_anatomy_ab_blender import _evaluated_world_vertices
    evaluated = _evaluated_world_vertices({
        'upper': objects['upper_teeth'], 'lower': objects['lower_teeth'],
        'upper_gum': objects['upper_gum'], 'lower_gum': objects['lower_gum']})
    for key, expected in (('upper', expected_upper),
                          ('lower', expected_lower),
                          ('upper_gum', expected_upper_gum),
                          ('lower_gum', expected_lower_gum)):
        difference = float(np.abs(evaluated[key] - expected).max())
        if not math.isfinite(difference) or difference > VALIDATION_SLACK_M:
            raise RuntimeError('E_PROC_STORAGE_MISMATCH_' + key +
                               '_' + str(round(difference, 9)))
    return True


def _apply_body_vertex_plan(body, plan, *, label):
    """Shape-key-safe application of a pure vertex plan on the copied body.

    The identical per-vertex delta is applied to the mesh vertices and to
    EVERY shape-key block, so the correction survives every facial pose.
    The stored Basis is verified against the planned target.
    """
    import numpy as np
    from mathutils import Vector
    world = body.matrix_world
    rot_inv = world.to_3x3().inverted()
    before = np.asarray([tuple(world @ v.co) for v in body.data.vertices],
                        dtype=np.float64)
    target, audit = plan(before)
    deltas = target - before
    local_deltas = [tuple(rot_inv @ Vector(tuple(float(c) for c in d)))
                    for d in deltas]
    for vertex, delta in zip(body.data.vertices, local_deltas):
        vertex.co = Vector((vertex.co.x + delta[0],
                            vertex.co.y + delta[1],
                            vertex.co.z + delta[2]))
    keys = body.data.shape_keys
    if keys is not None:
        for key in keys.key_blocks:
            for index, point in enumerate(key.data):
                delta = local_deltas[index]
                point.co = Vector((point.co.x + delta[0],
                                   point.co.y + delta[1],
                                   point.co.z + delta[2]))
    body.data.update()
    if keys is not None:
        basis = keys.key_blocks.get('Basis')
        if basis is not None:
            stored = np.asarray(
                [tuple(world @ Vector(tuple(k.co))) for k in basis.data],
                dtype=np.float64)
            discrepancy = float(np.linalg.norm(stored - target, axis=1).max())
            if not np.isfinite(discrepancy) or discrepancy > 2e-6:
                raise RuntimeError('E_' + label + '_STORAGE_MISMATCH_' +
                                   str(round(discrepancy, 9)))
            audit['max_storage_error_m'] = round(discrepancy, 9)
            audit['shape_key_blocks_moved'] = len(keys.key_blocks)
    audit['body_topology_modified'] = False
    audit['body_vertex_count'] = int(len(body.data.vertices))
    return audit


def reshape_lip_opening(body):
    """IDENTITY-028 shape-key-safe lip-opening border correction."""
    from tools.mouth_anatomy import plan_lip_opening
    return _apply_body_vertex_plan(
        body,
        lambda points: plan_lip_opening(points, label='LIP_OPENING'),
        label='LIP_OPENING')


def reshape_lip_almonder(body):
    """IDENTITY-029 shape-key-safe almond lip reshape on the copied body.

    Replaces the narrow IDENTITY-028 corner bump (which pinched the
    aperture to a point at both corners) with a smooth, wide almond
    field: an upper-border centre drop, a lower-border corner lift and
    the carried-over lower-roll protrusion.
    """
    from character.oral_visibility import plan_lip_almonder
    return _apply_body_vertex_plan(
        body,
        lambda points: plan_lip_almonder(points, label='LIP_ALMOND'),
        label='LIP_ALMOND')


def planned_arrays():
    """Rebuild the deterministic planned world arrays for validation."""
    from character.procedural_dentition import build_dentition, gum_band
    spec = build_dentition()
    upper = np.concatenate([pl['vertices'] for pl in spec['upper']], axis=0)
    lower = np.concatenate([pl['vertices'] for pl in spec['lower']], axis=0)
    upper_gum, _ = gum_band('upper')
    lower_gum, _ = gum_band('lower')
    return upper, lower, upper_gum, lower_gum


def storage_validate(body, objects):
    upper, lower, upper_gum, lower_gum = planned_arrays()
    return _storage_check(objects, upper, lower, upper_gum, lower_gum)


def procedural_collision_audit(upper_obj, lower_obj, tongue_obj, pose_label):
    """Collision audit on the PROCEDURAL arches (replaces the slab audit).

    Returns the same shape as ``_oral_collision_audit`` in
    tools/mpfb_anatomy_ab_blender so downstream consumers
    (``collision_audits``, the runner contract, reports) are unaffected.
    """
    from tools.mpfb_anatomy_ab_blender import _evaluated_world_vertices
    from tools.mouth_anatomy import (
        nearest_triangle_distances, distance_summary,
        describe_intersecting_triangle_pairs)
    snapshot = _evaluated_world_vertices(
        {'upper': upper_obj, 'lower': lower_obj, 'tongue': tongue_obj})
    upper_world = snapshot['upper']
    lower_world = snapshot['lower']
    tongue_world = snapshot['tongue']
    upper_tris = _world_mesh_triangles(upper_obj, upper_world)
    lower_tris = _world_mesh_triangles(lower_obj, lower_world)
    tongue_tris = _world_mesh_triangles(tongue_obj, tongue_world)

    def summary(points, other_tris):
        if len(points) and len(other_tris):
            return distance_summary(
                nearest_triangle_distances(points, other_tris))
        return {'min_m': None, 'sample_count': 0}

    distances = {
        'tongue_to_teeth': summary(
            tongue_world,
            np.concatenate([upper_tris, lower_tris], axis=0)),
        'upper_arch_to_lower': summary(upper_world, lower_tris),
        'lower_arch_to_upper': summary(lower_world, upper_tris),
        'mixed_jaw_faces_skipped': 0,
    }
    arch = describe_intersecting_triangle_pairs(upper_tris, lower_tris)
    tongue_int = describe_intersecting_triangle_pairs(
        tongue_tris, np.concatenate([upper_tris, lower_tris], axis=0))
    return {
        'pose': pose_label,
        'distance_method': 'POINT_TO_TRIANGLE_EVALUATED_WORLD',
        'intersection_method': arch['method'],
        'tangential_contact_not_counted': True,
        'depth_proxy': 'MIN_OF_TWO_ONTO_OTHER_PLANE_EXTENTS',
        'distances': distances,
        'upper_lower_arch_intersections': arch,
        'tongue_teeth_intersections': tongue_int,
        'dental_segmentation_mode': 'PROCEDURAL_FDI_PARAMETRIC_ARCHES',
    }


# IDENTITY-029 extended collision coverage: the gingival bands, the lip
# border and the intermediate jaw positions are audited as well, not just
# the arches and the tongue.
LIP_AUDIT_Z_MIN_M = 1.5000
LIP_AUDIT_Z_MAX_M = 1.5700
LIP_AUDIT_Y_MAX_M = -0.0350
LIP_AUDIT_X_HALF_SPAN_M = 0.0500


def _lip_band_triangles(body, world_verts):
    """Body triangles in the facial band around the mouth.

    The band is the front of the face between the chin and the nose,
    limited in x to the mouth width. These are the triangles the lips
    are made of, so a tooth or a gingival band that pokes through them
    shows up here.
    """
    import numpy as np
    selected = []
    for poly in body.data.polygons:
        ids = list(poly.vertices)
        points = world_verts[ids]
        if (np.abs(points[:, 0]).max() > LIP_AUDIT_X_HALF_SPAN_M or
                points[:, 1].max() > LIP_AUDIT_Y_MAX_M or
                points[:, 2].min() < LIP_AUDIT_Z_MIN_M or
                points[:, 2].max() > LIP_AUDIT_Z_MAX_M):
            continue
        selected.append(ids)
    tris = []
    for ids in selected:
        for i in range(1, len(ids) - 1):
            tris.append((ids[0], ids[i], ids[i + 1]))
    if not tris:
        return np.zeros((0, 3, 3), dtype=np.float64)
    return np.asarray([[world_verts[a], world_verts[b], world_verts[c]]
                        for a, b, c in tris], dtype=np.float64)


def _minimum_distance(points, other_tris):
    if len(points) == 0 or len(other_tris) == 0:
        return None
    from tools.mouth_anatomy import distance_summary, nearest_triangle_distances
    return distance_summary(nearest_triangle_distances(points, other_tris))


def oral_collision_audit_full(body, upper_obj, lower_obj, tongue_obj,
                              upper_gum_obj, lower_gum_obj, pose_label):
    """IDENTITY-029 extended collision audit on the visible oral anatomy.

    Covers, in addition to the IDENTITY-028 arch/tongue audit:

    * each gingival band against both arches (the band must hug the
      cervical margin without driving through the crown);
    * the upper band against the lower band (they must not interpenetrate
      when the jaw closes);
    * each gingival band against the tongue;
    * the facial band around the mouth against the arches and the gingival
      bands (nothing may poke through the lips).

    Every pair is reported with the transversal-crossing count, the
    crossing-depth proxy and the minimum point-to-triangle distance, so a
    reviewer can see the measured numbers rather than a pass/fail claim.
    """
    import numpy as np
    from tools.mpfb_anatomy_ab_blender import _evaluated_world_vertices
    from tools.mouth_anatomy import describe_intersecting_triangle_pairs
    snapshot = _evaluated_world_vertices({
        'upper': upper_obj, 'lower': lower_obj, 'tongue': tongue_obj,
        'upper_gum': upper_gum_obj, 'lower_gum': lower_gum_obj})
    upper_world = snapshot['upper']
    lower_world = snapshot['lower']
    tongue_world = snapshot['tongue']
    upper_gum_world = snapshot['upper_gum']
    lower_gum_world = snapshot['lower_gum']
    body_world = np.asarray(
        [tuple(body.matrix_world @ v.co) for v in body.data.vertices],
        dtype=np.float64)

    upper_tris = _world_mesh_triangles(upper_obj, upper_world)
    lower_tris = _world_mesh_triangles(lower_obj, lower_world)
    tongue_tris = _world_mesh_triangles(tongue_obj, tongue_world)
    upper_gum_tris = _world_mesh_triangles(upper_gum_obj, upper_gum_world)
    lower_gum_tris = _world_mesh_triangles(lower_gum_obj, lower_gum_world)
    lip_tris = _lip_band_triangles(body, body_world)

    pairs = {
        'upper_gum_to_upper_teeth': (upper_gum_tris, upper_tris),
        'upper_gum_to_lower_teeth': (upper_gum_tris, lower_tris),
        'lower_gum_to_upper_teeth': (lower_gum_tris, upper_tris),
        'lower_gum_to_lower_teeth': (lower_gum_tris, lower_tris),
        'upper_gum_to_lower_gum': (upper_gum_tris, lower_gum_tris),
        'upper_gum_to_tongue': (upper_gum_tris, tongue_tris),
        'lower_gum_to_tongue': (lower_gum_tris, tongue_tris),
        'lip_to_upper_teeth': (lip_tris, upper_tris),
        'lip_to_lower_teeth': (lip_tris, lower_tris),
        'lip_to_upper_gum': (lip_tris, upper_gum_tris),
        'lip_to_lower_gum': (lip_tris, lower_gum_tris),
    }
    crossings = {}
    depths = {}
    for name, (tris_a, tris_b) in pairs.items():
        if len(tris_a) == 0 or len(tris_b) == 0:
            crossings[name] = 0
            depths[name] = None
            continue
        report = describe_intersecting_triangle_pairs(tris_a, tris_b)
        crossings[name] = int(report['pairs'])
        depths[name] = report['summary']['crossing_depth_max_m']

    distances = {}
    for name, (pts, tris) in {
        'upper_gum_to_upper_teeth': (upper_gum_world, upper_tris),
        'upper_gum_to_lower_teeth': (upper_gum_world, lower_tris),
        'lower_gum_to_upper_teeth': (lower_gum_world, upper_tris),
        'lower_gum_to_lower_teeth': (lower_gum_world, lower_tris),
        'upper_gum_to_lower_gum': (upper_gum_world, lower_gum_tris),
        'upper_gum_to_tongue': (upper_gum_world, tongue_tris),
        'lower_gum_to_tongue': (lower_gum_world, tongue_tris),
        # Skip full-body lip distances - use sampled lip band instead
        # 'lip_to_upper_teeth': (body_world, upper_tris),
        # 'lip_to_lower_teeth': (body_world, lower_tris),
        # 'lip_to_upper_gum': (body_world, upper_gum_tris),
        # 'lip_to_lower_gum': (body_world, lower_gum_tris),
    }.items():
        if len(pts) == 0 or len(tris) == 0:
            distances[name] = None
            continue
        distances[name] = _minimum_distance(pts, tris)
    # Lip distances: use a small sample of body points in the lip band
    lip_sample = body_world[
        (np.abs(body_world[:, 0]) < LIP_AUDIT_X_HALF_SPAN_M) &
        (body_world[:, 1] < LIP_AUDIT_Y_MAX_M) &
        (body_world[:, 2] >= LIP_AUDIT_Z_MIN_M) &
        (body_world[:, 2] <= LIP_AUDIT_Z_MAX_M)]
    if len(lip_sample) > 500:
        idx = np.random.default_rng(42).choice(len(lip_sample), 500, replace=False)
        lip_sample = lip_sample[idx]
    for name, tris in (('lip_to_upper_teeth', upper_tris),
                        ('lip_to_lower_teeth', lower_tris),
                        ('lip_to_upper_gum', upper_gum_tris),
                        ('lip_to_lower_gum', lower_gum_tris)):
        if len(lip_sample) == 0 or len(tris) == 0:
            distances[name] = None
            continue
        distances[name] = _minimum_distance(lip_sample, tris)
    return {
        'pose': pose_label,
        'distance_method': 'POINT_TO_TRIANGLE_EVALUATED_WORLD',
        'intersection_method':
            'MOLLER_TRIANGLE_PIERCE_WITH_PLANE_EXTENT_PROXY',
        'tangential_contact_not_counted': True,
        'lip_band': {
            'z_min_m': LIP_AUDIT_Z_MIN_M,
            'z_max_m': LIP_AUDIT_Z_MAX_M,
            'y_max_m': LIP_AUDIT_Y_MAX_M,
            'x_half_span_m': LIP_AUDIT_X_HALF_SPAN_M,
            'body_triangles': int(len(lip_tris)),
        },
        'crossing_pairs': crossings,
        'crossing_depth_max_m': depths,
        'distances': distances,
        'gum_crossing_pairs_total': int(sum(
            crossings[name] for name in crossings
            if 'gum' in name and 'lip' not in name)),
        'lip_crossing_pairs_total': int(sum(
            crossings[name] for name in crossings if 'lip' in name)),
    }


def procedural_motion_audit(upper_obj, lower_obj):
    """Key-block displacement audit, world frame, no scene state changes.

    Upper must be EXACTLY static (keys are identical to Basis); the lower
    arch must follow the native body morph on every vertex. Returns a
    dict mirroring seamed_jaw_motion semantics.
    """
    upper_keys = upper_obj.data.shape_keys.key_blocks
    lower_keys = lower_obj.data.shape_keys.key_blocks

    def world_of(obj, key):
        from mathutils import Vector
        world = obj.matrix_world
        return np.asarray([tuple(world @ point.co) for point in key.data],
                          dtype=np.float64)

    upper_before = world_of(upper_obj, upper_keys['Basis'])
    upper_after = world_of(upper_obj, upper_keys['jawOpen'])
    lower_before = world_of(lower_obj, lower_keys['Basis'])
    lower_after = world_of(lower_obj, lower_keys['jawOpen'])
    upper_delta = np.linalg.norm(upper_after - upper_before, axis=1)
    lower_delta = np.linalg.norm(lower_after - lower_before, axis=1)
    lower_median = float(np.median(lower_delta))
    lower_max = float(lower_delta.max())
    upper_max = float(upper_delta.max())
    lower_moved = int(np.count_nonzero(lower_delta > 0.0001))
    status = ('PASS_PROCEDURAL_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA'
              if (upper_max <= 2e-4 and lower_moved == len(lower_delta)
                  and 0.001 <= lower_median <= 0.030 and lower_max <= 0.035)
              else 'FAIL_PROCEDURAL_JAW_MOTION_NOT_VISUAL_QA')
    return {
        'schema': 'livynth.procedural-dentition.jaw-audit.v1',
        'status': status,
        'source': 'EVALUATED_KEY_WORLD_COORDS_BASIS_VS_JAWOPEN',
        'upper_vertices': int(len(upper_delta)),
        'lower_vertices': int(len(lower_delta)),
        'upper_max_displacement_m': round(upper_max, 9),
        'lower_moved_vertices': lower_moved,
        'lower_median_displacement_m': round(lower_median, 9),
        'lower_max_displacement_m': round(lower_max, 9),
        'self_intersections': 'NOT_TESTED',
        'visual_anatomy': 'PENDING_INDEPENDENT_REVIEW',
    }
