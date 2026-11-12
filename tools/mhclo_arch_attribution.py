"""IDENTITY-024: jaw-arch attribution from the already verified MHCLO mask.

Build temporary, static, evaluated Head A dental arch meshes only for rendering.
No original asset, rigged teeth mesh, material or shape key gets edited.
"""
from __future__ import annotations

from contextlib import contextmanager
from collections import Counter
import math

SCHEMA='livynth.mhclo.arch-attribution.v1'

class ArchAttributionError(ValueError):
    pass


def plan_arch_faces(mask,faces):
    """Compute exact arch face indexes from source vertex IDs, fail on bridges."""
    if len(mask)!=3868 or len(faces)!=3540:
        raise ArchAttributionError('E_ID024_PINNED_JAW_COUNTS')
    labels=[]
    for value in mask:
        try:
            f=float(value)
        except (ValueError,TypeError) as exc:
            raise ArchAttributionError('E_ID024_MASK_INVALID') from exc
        if f not in (0.,1.):
            raise ArchAttributionError('E_ID024_MASK_INVALID')
        labels.append(int(f))
    if sum(labels)!=1884:
        raise ArchAttributionError('E_ID024_LOWER_VERTEX_COUNT')
    upper=[]
    lower=[]
    used={0:set(),1:set()}
    for i,face in enumerate(faces):
        if (not isinstance(face,(tuple,list)) or len(face)<3 or
            any(type(v)!=int or v<0 or v>=3868 for v in face)):
            raise ArchAttributionError('E_ID024_FACE_INDEX')
        jaw={labels[v] for v in face}
        if len(jaw)!=1:
            raise ArchAttributionError('E_ID024_CROSS_JAW_FACE')
        side=jaw.pop()
        (lower if side else upper).append(i)
        used[side].update(face)
    if (len(upper)!=1818 or len(lower)!=1722 or
            len(used[0])!=1984 or len(used[1])!=1884):
        raise ArchAttributionError('E_ID024_DENTAL_ARCH_SURFACE_COUNTS')
    return {
        'upper_face_indices':upper,
        'lower_face_indices':lower,
        'upper_source_vertex_indices':sorted(used[0]),
        'lower_source_vertex_indices':sorted(used[1]),
    }


def _bounds(points):
    import numpy as np
    xyz=np.asarray(points,dtype=np.float64)
    if (xyz.ndim!=2 or xyz.shape[1]!=3 or len(xyz)<1 or
            not np.isfinite(xyz).all()):
        raise ArchAttributionError('E_ID024_BOUNDS_INVALID')
    a=xyz.min(axis=0)
    b=xyz.max(axis=0)
    c=xyz.mean(axis=0)
    return {
        'world_min_xyz_m':[round(float(v),8) for v in a],
        'world_max_xyz_m':[round(float(v),8) for v in b],
        'world_centroid_xyz_m':[round(float(v),8) for v in c],
        'world_extent_xyz_m':[round(float(v),8) for v in b-a],
    }


def arch_location_audit(teeth_world,tongue_world,mask):
    """World-axis occupancy only; cannot infer tissue contact or camera occlusion."""
    import numpy as np
    teeth=np.asarray(teeth_world,dtype=np.float64)
    tongue=np.asarray(tongue_world,dtype=np.float64)
    m=np.asarray(mask,dtype=np.float64)
    if (teeth.shape!=(3868,3) or tongue.ndim!=2 or
            tongue.shape[1]!=3 or len(tongue)!=226 or
            m.shape!=(3868,) or not np.isin(m,[0.,1.]).all() or
            int(np.count_nonzero(m))!=1884):
        raise ArchAttributionError('E_ID024_LOCATION_INPUT')
    if not np.isfinite(teeth).all() or not np.isfinite(tongue).all():
        raise ArchAttributionError('E_ID024_LOCATION_NONFINITE')
    upper=teeth[m==0]
    lower=teeth[m==1]
    return {
        'schema':SCHEMA,
        'upper_dental_arch':_bounds(upper),
        'lower_dental_arch':_bounds(lower),
        'tongue':_bounds(tongue),
        'tongue_centroid_minus_lower_arch_xyz_m':[
            round(float(v),8)
            for v in tongue.mean(axis=0)-lower.mean(axis=0)],
        'tongue_centroid_minus_upper_arch_xyz_m':[
            round(float(v),8)
            for v in tongue.mean(axis=0)-upper.mean(axis=0)],
        'axes':'BLENDER_WORLD_XYZ; front approximate -Y; Z is up',
        'jaw_pose':'jawOpen_0.85',
        'anatomical_contact':'NOT_TESTED',
        'visual_approval':'NOT_TESTED',
    }


@contextmanager
def isolated_arch_objects(tooth_obj,mask):
    """Yield two static posed, materials-preserving arch objects; destroy on exit.

    Important: use the dependency-graph EVALUATED tooth mesh so both the
    armature and jawOpen accessory shape are incorporated before splitting.
    """
    import bpy
    import bmesh
    from mathutils import Matrix

    if tooth_obj.type!='MESH' or tooth_obj.hide_render:
        raise ArchAttributionError('E_ID024_RIGGED_TEETH_NOT_VISIBLE')
    originals=[tuple(p.vertices) for p in tooth_obj.data.polygons]
    plans=plan_arch_faces(mask,originals)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated=tooth_obj.evaluated_get(depsgraph)
    created=[]
    try:
        for side,side_value,face_indices,vertex_indices in (
            ('upper',0,plans['upper_face_indices'],plans['upper_source_vertex_indices']),
            ('lower',1,plans['lower_face_indices'],plans['lower_source_vertex_indices'])
        ):
            mesh=bpy.data.meshes.new_from_object(
                evaluated,preserve_all_data_layers=True,depsgraph=depsgraph)
            if mesh is None:
                raise ArchAttributionError('E_ID024_EVALUATED_MESH_MISSING')
            created.append((None,mesh))
            if (len(mesh.vertices)!=3868 or len(mesh.polygons)!=3540):
                raise ArchAttributionError('E_ID024_EVALUATED_VERTEX_FACE_LAYOUT')
            bm=bmesh.new()
            try:
                bm.from_mesh(mesh)
                bm.verts.ensure_lookup_table()
                label=bm.verts.layers.int.new('livynth_id024_original_index')
                discard=[]
                for i,v in enumerate(bm.verts):
                    v[label]=i
                    if int(mask[i])!=side_value:
                        discard.append(v)
                bmesh.ops.delete(bm,geom=discard,context='VERTS')
                bm.to_mesh(mesh)
                mesh.update()
            finally:
                bm.free()
            layer=mesh.attributes.get('livynth_id024_original_index')
            if layer is None:
                raise ArchAttributionError('E_ID024_VERTEX_SOURCE_IDS_LOST')
            recovered=[int(item.value) for item in layer.data]
            if (len(mesh.vertices)!=len(vertex_indices) or
                    sorted(recovered)!=vertex_indices or
                    len(mesh.polygons)!=len(face_indices)):
                raise ArchAttributionError('E_ID024_ARCH_ISOLATION_COUNTS')
            if mesh.shape_keys is not None:
                raise ArchAttributionError('E_ID024_EVALUATED_MESH_HAS_SHAPE_KEYS')
            if len(mesh.materials)!=len(tooth_obj.data.materials):
                raise ArchAttributionError('E_ID024_MATERIAL_SLOTS_LOST')
            obj=bpy.data.objects.new('livynth_id024_'+side+'_temporary',mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj.matrix_world=tooth_obj.matrix_world.copy()
            created[-1]=(obj,mesh)

        bpy.context.view_layer.update()
        yield {
            'upper':created[0][0],
            'lower':created[1][0],
            'source_face_count':3540,
            'upper_face_count':1818,
            'lower_face_count':1722,
            'source_vertex_order': 'PRESERVED_BY_EXPLICIT_VERTEX_ID_ATTRIBUTE',
        }
    finally:
        for obj,mesh in reversed(created):
            if obj is not None:
                bpy.data.objects.remove(obj,do_unlink=True)
            if mesh.users==0:
                bpy.data.meshes.remove(mesh)
        bpy.context.view_layer.update()
