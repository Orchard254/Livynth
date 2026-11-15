#!/usr/bin/env python3
"""Blender 4.5 / MPFB: matched A/B facial poses with fitted anatomy.

This is an isolated *scene-only* experiment. It does not read or rewrite
the successful existing A/B GLBs, and it never certifies anatomy quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from character.identity_recipe import (
    load_recipe,apply_macro_overrides,neutral_positions_sha256,neutral_topology_sha256)
from character.native_anatomy import load_plan,resolve_native_assets,REQUIRED
from character.head_shape import apply_head_shape,audit_realized_head_shape

SCHEMA='livynth.anatomy-ab-render.v1'
POSES={
    'neutral':{},
    'blink':{'eyeBlinkLeft':1.0,'eyeBlinkRight':1.0},
    'jaw_open':{'jawOpen':0.85},
    'viseme_aa':{'viseme_aa':0.90},
    'viseme_pp':{'viseme_PP':0.90},
}


def _render(scene,body,filename,angle_deg,output,*,oral_closeup=False):
    import bpy
    from mathutils import Vector
    from video.render_talk import bounds,shot_settings
    lo,hi=bounds([body])
    h=hi[2]-lo[2]
    settings=shot_settings(h,'studio')
    target=Vector(((lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,
                   hi[2]-h*(0.135 if oral_closeup else settings['camera_drop'])))
    radius=max(0.44,0.43*h) if oral_closeup else max(1.4,2.0*h)
    theta=math.radians(angle_deg)
    scene.camera.location=target+Vector(
        (radius*math.sin(theta),-radius*math.cos(theta),0))
    scene.camera.rotation_euler=(
        target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    path=output/(filename+'.png')
    scene.render.filepath=str(path.resolve())
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size<1000:
        raise RuntimeError('E_ANATOMY_POSE_RENDER_MISSING_'+filename)
    return {'pose':filename,'filename':path.name,'bytes':path.stat().st_size}


def _set_morphs(body,weights,*,oral_assets=None):
    import bpy
    keys=body.data.shape_keys
    if keys is None:
        raise RuntimeError('E_ANATOMY_POSE_SHAPE_KEYS_MISSING')
    blocks=keys.key_blocks
    if not set(weights).issubset({k.name for k in blocks}):
        raise RuntimeError('E_ANATOMY_POSE_TARGET_MISSING')
    for key in blocks:
        if key.name=='Basis': continue
        key.value=float(weights.get(key.name,0))
        key.keyframe_insert(data_path='value',frame=1)
    for category,obj in (oral_assets or {}).items():
        if obj.data.shape_keys is None:
            raise RuntimeError('E_ORAL_CORRECTIVE_KEYS_MISSING_'+category)
        oral_keys=obj.data.shape_keys.key_blocks
        for name in ('jawOpen','viseme_aa'):
            if name not in oral_keys:
                raise RuntimeError('E_ORAL_CORRECTIVE_KEY_MISSING_'+name)
            oral_keys[name].value=float(weights.get(name,0.0))
            oral_keys[name].keyframe_insert(data_path='value',frame=1)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def _translate_asset_in_body_space(body,asset,offset_fn):
    """Apply offset_fn(body_space_positions) -> (target_positions,audit).

    Shape keys in Blender 4.5 store ABSOLUTE vertex positions and the
    evaluated mesh ignores plain mesh.vertices writes once shape keys exist.
    Translating every key block by the same delta keeps Basis, jawOpen and
    viseme_aa consistent in every pose.
    """
    import numpy as np
    from mathutils import Vector
    if body==asset or body.type!='MESH' or asset.type!='MESH':
        raise RuntimeError('E_MOUTH_ANATOMY_OBJECT_TYPE')
    to_body=body.matrix_world.inverted() @ asset.matrix_world
    to_asset=asset.matrix_world.inverted() @ body.matrix_world
    rotation=to_asset.to_3x3()
    before=np.asarray([tuple(to_body @ v.co) for v in asset.data.vertices],
                      dtype=np.float64)
    target,audit=offset_fn(before)
    deltas=target-before
    asset_deltas=[tuple(rotation @ Vector(tuple(float(x) for x in d))) for d in deltas]
    for vertex,position in zip(asset.data.vertices,target):
        vertex.co=to_asset @ Vector(tuple(float(v) for v in position))
    keys=asset.data.shape_keys
    if keys is not None:
        for key in keys.key_blocks:
            block=key.data
            for i,d in enumerate(asset_deltas):
                local=block[i].co
                block[i].co=Vector((local.x+d[0],local.y+d[1],local.z+d[2]))
    asset.data.update()
    # Verify the stored Basis actually reflects the planned translation.
    stored=np.asarray([tuple(to_body @ v.co) for v in asset.data.vertices],
                      dtype=np.float64)
    if keys is not None:
        basis=keys.key_blocks.get('Basis')
        if basis is not None:
            stored=np.asarray([tuple(to_body @ Vector(tuple(k.co)))
                               for k in basis.data],dtype=np.float64)
    discrepancy=float(np.linalg.norm(stored-target,axis=1).max())
    if not np.isfinite(discrepancy) or discrepancy>2e-6:
        raise RuntimeError('E_MOUTH_ANATOMY_STORAGE_MISMATCH_'+str(round(discrepancy,9)))
    audit['max_storage_error_m']=round(discrepancy,9)
    audit['shape_key_blocks_translated']=(
        len(keys.key_blocks) if keys is not None else 0)
    return audit


def _scale_asset_in_body_space(body,asset,scale,*,label='ASSET'):
    """Uniformly scale a copied asset about its body-space centroid.

    Like _translate_asset_in_body_space, every shape-key block receives
    the identical similarity transform so Basis and corrective poses stay
    consistent. Used to shrink the oversized MPFB dental arch on the
    disposable copy only.
    """
    import numpy as np
    from mathutils import Vector
    from tools.mouth_anatomy import plan_uniform_scale
    if body==asset or body.type!='MESH' or asset.type!='MESH':
        raise RuntimeError('E_MOUTH_ANATOMY_OBJECT_TYPE_'+str(label))
    to_body=body.matrix_world.inverted() @ asset.matrix_world
    to_asset=asset.matrix_world.inverted() @ body.matrix_world
    before=np.asarray([tuple(to_body @ v.co) for v in asset.data.vertices],
                      dtype=np.float64)
    pivot=before.mean(axis=0)
    target,audit=plan_uniform_scale(before,scale,pivot,label=label)
    pivot_local=to_asset @ Vector(tuple(float(v) for v in pivot))
    factor=float(scale)
    for vertex,position in zip(asset.data.vertices,target):
        vertex.co=to_asset @ Vector(tuple(float(v) for v in position))
    keys=asset.data.shape_keys
    if keys is not None:
        for key in keys.key_blocks:
            for point in key.data:
                delta=(point.co-pivot_local)*factor
                point.co=pivot_local+delta
    asset.data.update()
    stored=np.asarray([tuple(to_body @ v.co) for v in asset.data.vertices],
                      dtype=np.float64)
    if keys is not None:
        basis=keys.key_blocks.get('Basis')
        if basis is not None:
            stored=np.asarray([tuple(to_body @ Vector(tuple(k.co)))
                               for k in basis.data],dtype=np.float64)
    discrepancy=float(np.linalg.norm(stored-target,axis=1).max())
    if not np.isfinite(discrepancy) or discrepancy>2e-6:
        raise RuntimeError('E_MOUTH_ANATOMY_SCALE_MISMATCH_'+str(round(discrepancy,9)))
    audit['max_storage_error_m']=round(discrepancy,9)
    audit['shape_key_blocks_scaled']=(
        len(keys.key_blocks) if keys is not None else 0)
    audit['pivot_source']='ASSET_BODY_SPACE_CENTROID_BASIS'
    return audit


def _sha256_file(path):
    import hashlib
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_tree_images_pixels(tree):
    """sha256 of every TexImage image's pixels referenced by a node tree."""
    import numpy as np
    from tools.mouth_anatomy import sha256_of_float_array
    entries=[]
    for node in tree.nodes:
        if node.bl_idname!='ShaderNodeTexImage' or node.image is None:
            continue
        image=node.image
        width,height=image.size
        if width==0 or height==0:
            continue
        count=width*height
        pixels=np.empty(count*4,dtype=np.float32)
        image.pixels.foreach_get(pixels)
        entries.append({'node':node.name,'image':image.name,
                        'width':int(width),'height':int(height),
                        'sha256':sha256_of_float_array(pixels)})
    return entries


def _hash_tree_images_files(tree):
    """sha256 of every on-disk file backing a TexImage image in a tree."""
    entries=[]
    for node in tree.nodes:
        if node.bl_idname!='ShaderNodeTexImage' or node.image is None:
            continue
        filepath=node.image.filepath if (node.image.filepath or '') else ''
        if filepath and Path(filepath).is_file():
            entries.append({'image':node.image.name,
                            'file':str(Path(filepath)),
                            'sha256':_sha256_file(Path(filepath))})
    return entries


def _mute_tongue_material(tongue,saturation,value):
    """Desaturate/darken the copied tongue asset's diffuse contribution.

    Operates on a SINGLE-USER COPY of every copied tongue material slot
    (original datablocks - which may be shared with the source human - are
    never edited). Inserts a Hue/Saturation/Value node between the image
    texture and the Principled BSDF Base Color of every isolated copy.
    The installed MPFB asset and its .mhmat/.png are never opened for
    writing. Hard error when the expected node graph is missing (no
    silent skip).
    """
    import colorsys
    applied=[]
    isolation=[]
    if not tongue.data.materials:
        raise RuntimeError('E_MOUTH_ANATOMY_TONGUE_MATERIAL_MISSING')
    for slot_index,material in enumerate(tongue.data.materials):
        if material is None:
            continue
        original=material
        original_nodes=int(len(original.node_tree.nodes)) if original.use_nodes else None
        original_users=int(original.users)
        images_before=_hash_tree_images_pixels(
            original.node_tree) if original.use_nodes else []
        image_files_before=_hash_tree_images_files(
            original.node_tree) if original.use_nodes else []
        iso=original.copy()  # single-user copy: the original stays pristine
        tongue.data.materials[slot_index]=iso
        if not iso.use_nodes:
            iso.use_nodes=True
        tree=iso.node_tree
        principled=next((n for n in tree.nodes
                         if n.bl_idname=='ShaderNodeBsdfPrincipled'),None)
        if principled is None:
            raise RuntimeError('E_MOUTH_ANATOMY_TONGUE_NO_BSDF_'+str(slot_index))
        links=[l for l in tree.links
               if l.to_node==principled and l.to_socket.name=='Base Color']
        if not links:
            # flat-color fallback: rescale the default_value via HSV
            col=principled.inputs['Base Color'].default_value
            h,s,v=colorsys.rgb_to_hsv(col[0],col[1],col[2])
            ns,nv=s*float(saturation),v*float(value)
            r,g,b=colorsys.hsv_to_rgb(h,ns,nv)
            principled.inputs['Base Color'].default_value=(r,g,b,col[3])
            applied.append({'material':iso.name,'slot':slot_index,
                            'mode':'FLAT_COLOR_RESCALE',
                            'saturation':float(saturation),
                            'value':float(value)})
        else:
            for link in list(links):
                source_socket=link.from_socket
                tree.links.remove(link)
                hsv=tree.nodes.new('ShaderNodeHueSaturation')
                hsv.name='livynth_tongue_mute'
                hsv.label='LIVYNTH IDENTITY-026 tongue mute'
                hsv.inputs['Hue'].default_value=0.5
                hsv.inputs['Saturation'].default_value=float(saturation)
                hsv.inputs['Value'].default_value=float(value)
                hsv.inputs['Fac'].default_value=1.0
                hsv.location=(source_socket.node.location.x+220.0,
                              source_socket.node.location.y)
                tree.links.new(source_socket,hsv.inputs['Color'])
                tree.links.new(hsv.outputs['Color'],
                               principled.inputs['Base Color'])
                applied.append({'material':iso.name,'slot':slot_index,
                                'mode':'HSV_NODE_INSERTED',
                                'saturation':float(saturation),
                                'value':float(value)})
        iso_nodes=int(len(iso.node_tree.nodes))
        after_original_nodes=(int(len(original.node_tree.nodes))
                              if original.use_nodes else None)
        images_after=_hash_tree_images_pixels(iso.node_tree)
        image_files_after=_hash_tree_images_files(iso.node_tree)
        images_pixels_unchanged=bool(
            [e['sha256'] for e in images_before]
            ==[e['sha256'] for e in images_after])
        image_files_unchanged=(
            bool([e['sha256'] for e in image_files_before]
                 ==[e['sha256'] for e in image_files_after])
            if image_files_before else None)
        isolation.append({
            'slot':slot_index,
            'original_material':original.name,
            'isolated_copy':iso.name,
            'original_users_before':original_users,
            'original_users_after':int(original.users),
            'original_nodes_before':original_nodes,
            'original_nodes_after':after_original_nodes,
            'isolated_nodes_after':iso_nodes,
            'original_material_unchanged':bool(original_nodes==after_original_nodes),
            'images_pixels_before':images_before,
            'images_pixels_after':images_after,
            'images_pixel_unchanged':images_pixels_unchanged,
            'image_files_before':image_files_before,
            'image_files_after':image_files_after,
            'image_files_unchanged':image_files_unchanged,
        })
    if not applied:
        raise RuntimeError('E_MOUTH_ANATOMY_TONGUE_MATERIAL_UNREACHED')
    for entry in applied:
        entry['source_material']=next(
            (e['original_material'] for e in isolation
             if e['slot']==entry['slot']), None)
    return applied, isolation


def _mute_teeth_gum_texture(teeth):
    """Mute the gum slabs of the copied teeth asset's diffuse texture.

    Operates on a SINGLE-USER COPY of every copied teeth material slot,
    and the TexImage node is re-pointed at an in-memory image COPY whose
    gum texels are blended toward a dark, desaturated brick tone. Tooth
    texels are left bit-identical. The installed MPFB teeth.png is never
    read for writing and never modified: the original image datablock is
    pixel-hashed before and after the pass, and any on-disk image file
    backing the node is sha256-hashed before and after. Hard error when
    the expected texture is missing.
    """
    import bpy
    import numpy as np
    from tools.mouth_anatomy import (
        mute_gum_pixels,TEETH_GUM_MUTE_STRENGTH,TEETH_GUM_TONE,
        sha256_of_float_array)
    applied=[]
    isolation=[]
    if not teeth.data.materials:
        raise RuntimeError('E_MOUTH_ANATOMY_TEETH_MATERIAL_MISSING')
    for slot_index,material in enumerate(teeth.data.materials):
        if material is None or not material.use_nodes:
            continue
        original=material
        original_nodes=int(len(original.node_tree.nodes))
        original_users=int(original.users)
        iso=original.copy()  # single-user copy: the original stays pristine
        teeth.data.materials[slot_index]=iso
        tree=iso.node_tree
        for node in tree.nodes:
            if node.bl_idname!='ShaderNodeTexImage' or node.image is None:
                continue
            image=node.image
            width,height=image.size
            if width==0 or height==0 or width>4096 or height>4096:
                raise RuntimeError('E_MOUTH_ANATOMY_TEETH_IMAGE_SIZE_'+
                                   str(width)+'x'+str(height))
            count=width*height
            original_pixels=np.empty(count*4,dtype=np.float32)
            image.pixels.foreach_get(original_pixels)
            original_image_sha256_before=sha256_of_float_array(original_pixels)
            disk_file=image.filepath if (image.filepath or '') else ''
            disk_sha_before=None
            if disk_file and Path(disk_file).is_file():
                disk_sha_before=_sha256_file(Path(disk_file))
            muted=image.copy()
            muted.name='livynth_oral_gum_muted'
            muted.pack()  # keep fully independent of the installed file
            node.image=muted
            pixels=np.empty(count*4,dtype=np.float32)
            muted.pixels.foreach_get(pixels)
            rgba=pixels.reshape(count,4)[:, :3].astype(np.float64)
            rgb=rgba.reshape(height,width,3)
            toned,mask=mute_gum_pixels(
                rgb,tone=TEETH_GUM_TONE,strength=TEETH_GUM_MUTE_STRENGTH)
            fraction=float(mask.mean())
            if not (0.02<=fraction<=0.60):
                raise RuntimeError('E_MOUTH_ANATOMY_TEETH_GUM_FRACTION_'+
                                   str(round(fraction,4)))
            out=np.empty_like(pixels).reshape(count,4)
            flat=toned.reshape(count,3)
            out[:, :3]=flat.astype(np.float32)
            out[:, 3]=pixels.reshape(count,4)[:, 3]
            muted.pixels.foreach_set(out.reshape(count*4))
            muted.update()
            after_pixels=np.empty(count*4,dtype=np.float32)
            image.pixels.foreach_get(after_pixels)
            original_image_sha256_after=sha256_of_float_array(after_pixels)
            disk_sha_after=None
            if disk_sha_before is not None:
                disk_sha_after=_sha256_file(Path(disk_file))
            image_unchanged=bool(original_image_sha256_before==
                                 original_image_sha256_after)
            disk_unchanged=(None if disk_sha_before is None
                            else bool(disk_sha_before==disk_sha_after))
            applied.append({'material':iso.name,'slot':slot_index,
                            'image':muted.name,
                            'gum_texel_fraction':round(fraction,4),
                            'strength':TEETH_GUM_MUTE_STRENGTH,
                            'tone':list(TEETH_GUM_TONE),
                            'installed_file_untouched':bool(
                                disk_unchanged is not False),
                            'source_material':original.name})
            isolation.append({
                'slot':slot_index,
                'original_material':original.name,
                'isolated_copy':iso.name,
                'original_users_before':original_users,
                'original_users_after':int(original.users),
                'original_nodes_before':original_nodes,
                'original_nodes_after':int(len(original.node_tree.nodes)),
                'isolated_nodes_after':int(len(tree.nodes)),
                'original_material_unchanged':bool(
                    original_nodes==int(len(original.node_tree.nodes))),
                'original_image':image.name,
                'original_image_sha256_before':original_image_sha256_before,
                'original_image_sha256_after':original_image_sha256_after,
                'original_image_unchanged':image_unchanged,
                'installed_image_file':(disk_file if disk_file else None),
                'installed_image_file_sha256_before':disk_sha_before,
                'installed_image_file_sha256_after':disk_sha_after,
                'installed_image_file_unchanged':disk_unchanged,
                'isolated_copy_image':muted.name,
            })
    if not applied:
        raise RuntimeError('E_MOUTH_ANATOMY_TEETH_TEXIMAGE_NOT_FOUND')
    return applied, isolation


def _soften_body_sulcus(body,max_push):
    """Lift the mentolabial sulcus vertices forward on the copied body.

    Applies the same per-vertex delta to Basis and every corrective key
    block (the same shape-key-safe pattern as the seat fix), so topology
    and morph behaviour are preserved. Hard error on storage mismatch.
    """
    import numpy as np
    from mathutils import Vector
    from tools.mouth_anatomy import (
        plan_lip_soften,LIP_Z_CENTER,LIP_Z_HALF_SPAN,LIP_X_HALF_SPAN)
    world=body.matrix_world
    rot_inv=world.to_3x3().inverted()
    before=np.asarray([tuple(world @ v.co) for v in body.data.vertices],
                      dtype=np.float64)
    target,audit=plan_lip_soften(before,max_push=max_push,label='BODY')
    # Anti-collision invariant: the lifted sulcus must stay behind the
    # lip bulge. The lip-bulge band (z >= 1.515) is weight~0 and never
    # moves, so comparing pre/post front reach is exact for the copy.
    lip_band=((np.abs(before[:,0])<=0.040) &
              (before[:,2]>=1.515) & (before[:,2]<=1.640) &
              (before[:,1]<0.0))
    sulcus_band=(before[:,1]<0.0) & \
        (np.abs(before[:,0])<=LIP_X_HALF_SPAN*1.6) & \
        (np.abs(before[:,2]-LIP_Z_CENTER)<LIP_Z_HALF_SPAN)
    lip_front=float(before[lip_band,1].min()) if lip_band.any() else float('nan')
    sulcus_before=float(before[sulcus_band,1].min()) if sulcus_band.any() else float('nan')
    sulcus_after=float(target[sulcus_band,1].min()) if sulcus_band.any() else float('nan')
    margin=float(sulcus_after-lip_front)
    audit['lip_bulge_front_m']=round(lip_front,9)
    audit['sulcus_front_before_m']=round(sulcus_before,9)
    audit['sulcus_front_after_m']=round(sulcus_after,9)
    audit['sulcus_behind_lip_margin_m']=round(margin,9)
    if not np.isfinite(margin) or margin<0.002:
        raise RuntimeError('E_MOUTH_ANATOMY_SULCUS_COLLISION_'+str(round(margin,9)))
    deltas=target-before
    local_deltas=[tuple(rot_inv @ Vector(tuple(float(c) for c in d)))
                  for d in deltas]
    for vertex,delta in zip(body.data.vertices,local_deltas):
        vertex.co=Vector((vertex.co.x+delta[0],vertex.co.y+delta[1],
                          vertex.co.z+delta[2]))
    keys=body.data.shape_keys
    if keys is not None:
        for key in keys.key_blocks:
            for index,point in enumerate(key.data):
                delta=local_deltas[index]
                point.co=Vector((point.co.x+delta[0],point.co.y+delta[1],
                                 point.co.z+delta[2]))
    body.data.update()
    if keys is not None:
        basis=keys.key_blocks.get('Basis')
        if basis is not None:
            stored=np.asarray(
                [tuple(world @ Vector(tuple(k.co))) for k in basis.data],
                dtype=np.float64)
            discrepancy=float(np.linalg.norm(stored-target,axis=1).max())
            if not np.isfinite(discrepancy) or discrepancy>2e-6:
                raise RuntimeError('E_MOUTH_ANATOMY_SULCUS_MISMATCH_'+
                                   str(round(discrepancy,9)))
            audit['max_storage_error_m']=round(discrepancy,9)
            audit['shape_key_blocks_lifted']=len(keys.key_blocks)
    return audit


def _arch_world_triangles(teeth, teeth_world, mask):
    """Triangulate the copied teeth and split into upper/lower arch tris."""
    import numpy as np
    triangles=[]
    upper_tris=[]
    lower_tris=[]
    mixed_faces=0
    for poly in teeth.data.polygons:
        verts=list(poly.vertices)
        face_tris=[(verts[0],verts[i],verts[i + 1])
                   for i in range(1,len(verts) - 1)]
        world_tris=[(teeth_world[a],teeth_world[b],teeth_world[c])
                    for a,b,c in face_tris]
        triangles.extend(world_tris)
        flags=mask[verts]
        if bool((flags == 1).all()):
            lower_tris.extend(world_tris)
        elif bool((flags == 0).all()):
            upper_tris.extend(world_tris)
        else:
            mixed_faces += 1
    return (np.asarray(triangles,dtype=np.float64),
            np.asarray(upper_tris,dtype=np.float64),
            np.asarray(lower_tris,dtype=np.float64),
            mixed_faces)


def _oral_collision_audit(body,teeth,tongue,dental_mask,pose_label):
    """Clearance + crossing-location audit of the oral assets.

    Distances are point-to-triangle minima (not a volumetric proof).
    Crossings use a Möller transversal-crossing predicate; tangential
    touches are explicitly not counted as interpenetration. Locations are
    world-space centroids of the six involved vertices plus the smaller
    of the two onto-other-plane extents as a conservative depth proxy.
    """
    import numpy as np
    from tools.mouth_anatomy import (
        nearest_triangle_distances,distance_summary,
        describe_intersecting_triangle_pairs)
    try:
        mask=np.asarray(dental_mask).astype(np.int64)
    except (TypeError,ValueError) as exc:
        raise RuntimeError('E_MOUTH_ANATOMY_MASK_'+str(exc)) from exc
    if mask.shape!=(len(teeth.data.vertices),) or not np.isin(mask,[0,1]).all():
        raise RuntimeError('E_MOUTH_ANATOMY_MASK_LAYOUT')
    snapshot=_evaluated_world_vertices({'teeth':teeth,'tongue':tongue})
    teeth_world=snapshot['teeth']
    tongue_world=snapshot['tongue']
    triangles,upper_tris,lower_tris,mixed_faces=_arch_world_triangles(
        teeth,teeth_world,mask)
    tongue_tris=[]
    for poly in tongue.data.polygons:
        verts=list(poly.vertices)
        for i in range(1,len(verts)-1):
            tongue_tris.append((tongue_world[verts[0]],
                                tongue_world[verts[i]],
                                tongue_world[verts[i+1]]))
    tongue_tris=np.asarray(tongue_tris,dtype=np.float64)
    tongue_d=nearest_triangle_distances(tongue_world,triangles)
    upper_mask=(mask==0)
    lower_mask=(mask==1)
    distances={
        'tongue_to_teeth':distance_summary(tongue_d),
        'mixed_jaw_faces_skipped':mixed_faces,
    }
    for name,points,other in (('upper_arch_to_lower',upper_mask,lower_tris),
                              ('lower_arch_to_upper',lower_mask,upper_tris)):
        if points.sum() and len(other):
            distances[name]=distance_summary(
                nearest_triangle_distances(teeth_world[points],other))
        else:
            distances[name]={'min_m':None,'sample_count':0}
    arch=describe_intersecting_triangle_pairs(upper_tris,lower_tris)
    tongue_int=describe_intersecting_triangle_pairs(tongue_tris,triangles)
    return {
        'pose':pose_label,
        'distance_method':'POINT_TO_TRIANGLE_EVALUATED_WORLD',
        'intersection_method':arch['method'],
        'tangential_contact_not_counted':True,
        'depth_proxy':'MIN_OF_TWO_ONTO_OTHER_PLANE_EXTENTS',
        'distances':distances,
        'upper_lower_arch_intersections':arch,
        'tongue_teeth_intersections':tongue_int,
    }


def _apply_mouth_anatomy(body,teeth,tongue,dental_mask,*,upper_seat,tongue_seat,
                         tooth_scale=None,lip_push=None,oral_assets=None,
                         tongue_scale=None,tongue_shift_y=None):
    """Seat upper arch and tongue; shrink the oversized dental arch; lift
    the mentolabial sulcus; mute the tongue's pink; darken the exposed
    mouth-cavity faces.

    All edits happen on the disposable copied scene assets — never on the
    installed MPFB files, the source human or any exported GLB.
    ``oral_assets`` (the copied teeth/tongue with corrective morphs) is
    switched to the jaw-open pose for the BVH/contact evaluation and
    restored afterwards, so the recorded contacts are the true open-pose
    contacts, not the rest pose.
    """
    import bpy
    import numpy as np
    from tools.mouth_anatomy import (
        SCHEMA,UPPER_SEAT_M,TONGUE_SEAT_M,TOOTH_SCALE,
        TONGUE_SCALE,TONGUE_SHIFT_Y_M,
        TONGUE_SATURATION,TONGUE_VALUE,LIP_MAX_PUSH_M,
        validate_seat,validate_tooth_scale,validate_lip_push,
        validate_tongue_scale,validate_tongue_shift_y,
        plan_masked_translation,plan_translation,
        cavity_z_window,plan_cavity_faces,plan_cavity_faces_bvh,
        validate_polygon_correspondence,
        CAVITY_BASE_COLOR,EXTERIOR_BASE_COLOR,
        CAVITY_ROUGHNESS,EXTERIOR_ROUGHNESS,
        CAVITY_HALF_WIDTH,CAVITY_OPENING_HALF_WIDTH,CAVITY_MIN_DEPTH_Y,
        CAVITY_SIDE_NORMAL_THRESHOLD)
    upper_seat=validate_seat(upper_seat,'UPPER_SEAT')
    tongue_seat=validate_seat(tongue_seat,'TONGUE_SEAT')
    tooth_scale=validate_tooth_scale(
        TOOTH_SCALE if tooth_scale is None else tooth_scale,'TOOTH_SCALE')
    tongue_scale=validate_tongue_scale(
        TONGUE_SCALE if tongue_scale is None else tongue_scale,'TONGUE_SCALE')
    tongue_shift_y=validate_tongue_shift_y(
        TONGUE_SHIFT_Y_M if tongue_shift_y is None else tongue_shift_y,
        'TONGUE_SHIFT_Y')
    lip_push=validate_lip_push(
        LIP_MAX_PUSH_M if lip_push is None else lip_push,'LIP_PUSH')
    # 1) Oversized dental appearance: uniform down-scale on the copy.
    tooth_audit=_scale_asset_in_body_space(
        body,teeth,tooth_scale,label='TEETH')
    # 2) Seats (scale commutes with the rigid translations).
    upper_audit=_translate_asset_in_body_space(
        body,teeth,
        lambda before: plan_masked_translation(
            before,dental_mask,dz=-upper_seat,select_value=0,
            label='UPPER_TEETH'))
    # 2a) Tongue: seat + posterior shift in one translation, then scale.
    tongue_audit=_translate_asset_in_body_space(
        body,tongue,
        lambda before: plan_translation(
            before,dy=tongue_shift_y,dz=-tongue_seat,label='TONGUE'))
    tongue_scale_audit=_scale_asset_in_body_space(
        body,tongue,tongue_scale,label='TONGUE')
    # 3) Sharp lower-lip contour: forward lift of the mentolabial sulcus.
    sulcus_audit=_soften_body_sulcus(body,lip_push)
    # 4) Unnatural pink surface: desaturate/darken the copied tongue.
    tongue_material,tongue_isolation=_mute_tongue_material(
        tongue,TONGUE_SATURATION,TONGUE_VALUE)
    # 4b) The upper "gum dinner-plate": mute the gum texels of the copied
    # teeth diffuse (in-memory image copy only, tooth texels untouched).
    teeth_gum_texture,teeth_isolation=_mute_teeth_gum_texture(teeth)
    world=body.matrix_world
    world_min=np.array([min((world @ p.co)[i] for p in body.data.vertices) for i in range(3)],dtype=np.float64)
    world_max=np.array([max((world @ p.co)[i] for p in body.data.vertices) for i in range(3)],dtype=np.float64)
    crown=float(world_max[2])
    height=crown-float(world_min[2])
    base_z_min,base_z_max=cavity_z_window(crown,height,
                                          z_min_fraction=0.870,
                                          z_max_fraction=0.915)
    # Interior mouth walls are only visible when the lips part. Earlier
    # revisions mixed poses here: BVH rays were cast at the EVALUATED
    # jawOpen mesh while the centres/normals used for the depth filter
    # came from the BASE pose, and the index correspondence between the
    # evaluated and the base mesh was assumed. This revision keeps the
    # whole selection in the same evaluated jawOpen pose and validates
    # the evaluated<->base index mapping explicitly before assigning
    # materials on the base polygons.
    jaw_keys=body.data.shape_keys.key_blocks if body.data.shape_keys else None
    saved_jaw=float(jaw_keys['jawOpen'].value) if (
        jaw_keys is not None and 'jawOpen' in jaw_keys) else None
    temp_object=None
    collision_audits={}
    pose_applied_with_correctives=False
    try:
        if oral_assets is not None:
            # body morph AND teeth/tongue correctives to jawOpen together,
            # so the evaluated pose is the true open pose for both.
            _set_morphs(body,POSES['jaw_open'],oral_assets=oral_assets)
            pose_applied_with_correctives=True
        elif saved_jaw is not None:
            jaw_keys['jawOpen'].value=0.85
            jaw_keys['jawOpen'].keyframe_insert(data_path='value',frame=1)
            bpy.context.scene.frame_set(1)
            bpy.context.view_layer.update()
        depsgraph=bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        evaluated=body.evaluated_get(depsgraph)
        temp_mesh=bpy.data.meshes.new_from_object(
            evaluated,preserve_all_data_layers=False,depsgraph=depsgraph)
        if temp_mesh is None:
            raise RuntimeError('E_MOUTH_ANATOMY_EVALUATED_MESH')
        temp_object=bpy.data.objects.new(
            'livynth_oral_cavity_probe',temp_mesh)
        bpy.context.scene.collection.objects.link(temp_object)
        temp_object.matrix_world=body.matrix_world.copy()
        bpy.context.view_layer.update()
        eval_world=np.asarray(
            [tuple((body.matrix_world @ v.co)) for v in temp_mesh.vertices],
            dtype=np.float64)
        eval_crown=float(eval_world[:,2].max())
        eval_height=eval_crown-float(eval_world[:,2].min())
        z_min,z_max=cavity_z_window(eval_crown,eval_height,
                                    z_min_fraction=0.870,
                                    z_max_fraction=0.915)
        candidates=plan_cavity_faces_bvh(
            temp_object,z_min=z_min,z_max=z_max,rays_x=48,rays_z=48)
        eval_matrix=temp_object.matrix_world
        eval_normals_matrix=eval_matrix.to_3x3()
        eval_polys=temp_object.data.polygons
        centers=[]
        normals=[]
        for index in candidates:
            poly=eval_polys[index]
            centers.append(tuple(eval_matrix @ poly.center))
            normals.append(tuple(
                (eval_normals_matrix @ poly.normal).normalized()))
        centers=np.asarray(centers,dtype=np.float64)
        normals=np.asarray(normals,dtype=np.float64)
        chosen=plan_cavity_faces(
            centers,normals,half_width=CAVITY_OPENING_HALF_WIDTH,
            z_min=z_min,z_max=z_max,min_depth_y=CAVITY_MIN_DEPTH_Y,
            side_normal_threshold=CAVITY_SIDE_NORMAL_THRESHOLD)
        cavity=sorted(candidates[i] for i in chosen)
        candidate_count=len(candidates)
        # Never assume the index correspondence between evaluated and
        # base meshes - validate it explicitly on loop vertex tuples.
        validated_faces=validate_polygon_correspondence(
            [tuple(p.vertices) for p in body.data.polygons],
            [tuple(p.vertices) for p in temp_object.data.polygons])
        collision_audits['jaw_open_0_85']=_oral_collision_audit(
            body,teeth,tongue,dental_mask,'jaw_open_0.85')
    finally:
        if temp_object is not None:
            temp_mesh=temp_object.data
            bpy.data.objects.remove(temp_object,do_unlink=True)
            if temp_mesh.users==0:
                bpy.data.meshes.remove(temp_mesh)
        if pose_applied_with_correctives:
            _set_morphs(body,POSES['neutral'],oral_assets=oral_assets)
        elif saved_jaw is not None:
            jaw_keys['jawOpen'].value=saved_jaw
            jaw_keys['jawOpen'].keyframe_insert(data_path='value',frame=1)
            bpy.context.scene.frame_set(1)
            bpy.context.view_layer.update()
    # Collision audits across the remaining review poses (the geometry is
    # final at this point; pose morphs are set and restored around each).
    if oral_assets is not None:
        for label,weights in (('viseme_aa_0_90',POSES['viseme_aa']),
                              ('viseme_pp_0_90',POSES['viseme_pp'])):
            _set_morphs(body,weights,oral_assets=oral_assets)
            collision_audits[label]=_oral_collision_audit(
                body,teeth,tongue,dental_mask,label)
        _set_morphs(body,POSES['neutral'],oral_assets=oral_assets)
    collision_audits['neutral']=_oral_collision_audit(
        body,teeth,tongue,dental_mask,'neutral')
    if not 8<=len(cavity)<=2000:
        raise RuntimeError('E_MOUTH_ANATOMY_CAVITY_FACE_COUNT_'+str(len(cavity)))
    centers_total=len(body.data.polygons)
    exterior=bpy.data.materials.new('livynth_oral_exterior_clay')
    exterior.use_nodes=True
    principled=exterior.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value=EXTERIOR_BASE_COLOR
    principled.inputs['Roughness'].default_value=EXTERIOR_ROUGHNESS
    cavity_mat=bpy.data.materials.new('livynth_oral_cavity')
    cavity_mat.use_nodes=True
    principled=cavity_mat.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value=CAVITY_BASE_COLOR
    principled.inputs['Roughness'].default_value=CAVITY_ROUGHNESS
    body.data.materials.append(exterior)
    body.data.materials.append(cavity_mat)
    cavity_set=set(cavity)
    for index,poly in enumerate(body.data.polygons):
        poly.material_index=1 if index in cavity_set else 0
    body.data.update()
    return {
        'schema':SCHEMA,
        'status':'MOUTH_ANATOMY_FIXED_PENDING_VISUAL_REVIEW',
        'upper_seat_m':round(upper_seat,9),
        'tongue_seat_m':round(tongue_seat,9),
        'tongue_shift_y_m':round(tongue_shift_y,9),
        'tooth_scale':tooth_audit,
        'tooth_scale_value':round(float(tooth_scale),9),
        'tongue_scale':tongue_scale_audit,
        'tongue_scale_value':round(float(tongue_scale),9),
        'upper':upper_audit,
        'tongue':tongue_audit,
        'lip_soften':sulcus_audit,
        'tongue_material':tongue_material,
        'teeth_gum_texture':teeth_gum_texture,
        'material_isolation':{
            'method':'SINGLE_USER_MATERIAL_COPIES_AND_IN_MEMORY_IMAGE_COPIES',
            'tongue_slots':tongue_isolation,
            'teeth_slots':teeth_isolation,
            'body_materials_created_fresh':[exterior.name,cavity_mat.name],
            'copies_created':len(tongue_isolation)+len(teeth_isolation),
            'original_materials_unchanged':bool(all(
                e['original_material_unchanged']
                for e in tongue_isolation+teeth_isolation)),
            'original_images_unchanged':bool(
                all(e['original_image_unchanged'] for e in teeth_isolation)
                and all(e['images_pixel_unchanged'] for e in tongue_isolation)),
            'installed_image_files_checked':sum(
                1 for e in teeth_isolation
                if e['installed_image_file_unchanged'] is not None)
                + sum(1 for e in tongue_isolation
                      if e['image_files_unchanged'] is not None),
            'installed_image_files_unchanged':(
                bool(all(e['installed_image_file_unchanged']
                         for e in teeth_isolation
                         if e['installed_image_file_unchanged'] is not None)
                     and all(e['image_files_unchanged']
                             for e in tongue_isolation
                             if e['image_files_unchanged'] is not None))
                if any(e['installed_image_file_unchanged'] is not None
                       for e in teeth_isolation)
                or any(e['image_files_unchanged'] is not None
                       for e in tongue_isolation) else None),
        },
        'material_isolation_verified':bool(
            all(e['original_material_unchanged']
                for e in tongue_isolation+teeth_isolation)
            and all(e['original_image_unchanged'] for e in teeth_isolation)
            and all(e['images_pixel_unchanged'] for e in tongue_isolation)
            and all(e['installed_image_file_unchanged'] is not False
                    for e in teeth_isolation)
            and all(e['image_files_unchanged'] is not False
                    for e in tongue_isolation)),
        'cavity_faces':len(cavity),
        'cavity_candidates':candidate_count,
        'cavity_method':'BVH_FIRST_HIT_FRONT_OPENINGS_JAWOPEN_SAME_POSE_FILTER',
        'cavity_indexes':cavity,
        'cavity_index_correspondence':'VALIDATED_POLYGON_LOOP_VERTEX_TUPLES',
        'cavity_validated_polygons':validated_faces,
        'cavity_opening_half_width_m':CAVITY_OPENING_HALF_WIDTH,
        'cavity_side_normal_threshold':CAVITY_SIDE_NORMAL_THRESHOLD,
        'cavity_total_faces':centers_total,
        'cavity_z_window_m':[round(z_min,6),round(z_max,6)],
        'cavity_z_window_base_m':[round(base_z_min,6),round(base_z_max,6)],
        'cavity_z_window_evaluated_m':[round(z_min,6),round(z_max,6)],
        'collision_audits':collision_audits,
        'contact_jaw_open_0_85':collision_audits.get('jaw_open_0_85'),
        'contact_neutral':collision_audits.get('neutral'),
        'cavity_half_width_m':CAVITY_HALF_WIDTH,
        'cavity_min_depth_y_m':CAVITY_MIN_DEPTH_Y,
        'body_material_slots':2,
        'body_topology_modified':False,
        'teeth_topology_modified':False,
        'tongue_topology_modified':False,
        'upper_arch_translation_xyz_m':[0.0,0.0,-round(upper_seat,9)],
        'tongue_translation_xyz_m':[0.0,0.0,-round(tongue_seat,9)],
        'source_assets_modified':False,
        'installed_mhclo_obj_modified':False,
        'source_human_modified':False,
        'existing_glbs_modified':False,
    }


def _evaluated_world_vertices(objects):
    """Snapshot Blender dependency-graph evaluated mesh positions in world space.

    This captures skinning, morphs, object transforms and any other modifiers.
    Reading original mesh.data coordinates would miss armature animation.
    """
    import bpy
    import numpy as np
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    result={}
    for name,obj in objects.items():
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        if mesh is None:
            raise RuntimeError('E_EVALUATED_ASSET_MESH_'+name)
        try:
            matrix=evaluated.matrix_world
            result[name]=np.asarray([tuple(matrix @ v.co) for v in mesh.vertices],
                                    dtype=np.float64)
        finally:
            evaluated.to_mesh_clear()
    return result


def _audit_jaw_and_visemes(body,assets,*,use_oral_correctives=False):
    from character.anatomy_motion_audit import diagnose_oral_motion
    objects={'body':body,'teeth':assets['teeth'],'tongue':assets['tongue']}
    controlled={category:assets[category] for category in ('teeth','tongue')} if use_oral_correctives else None
    _set_morphs(body,{},oral_assets=controlled)
    before=_evaluated_world_vertices(objects)
    reports={}
    for pose in ('jaw_open','viseme_aa'):
        _set_morphs(body,POSES[pose],oral_assets=controlled)
        after=_evaluated_world_vertices(objects)
        reports[pose]=diagnose_oral_motion(before,after,pose=pose)
    _set_morphs(body,{},oral_assets=controlled)
    return reports


def run(character,plan_file,output,*,align_accessories=False,audit_oral_motion=False,oral_correctives=False,mhclo_dentition=False,rigged_seam_probe=False,seam_jaw_stills=False,oral_isolation=False,dental_arch_isolation=False,oral_anatomy=False,upper_seat=None,tongue_seat=None,tooth_scale=None,lip_push=None,tongue_scale=None,tongue_shift_y=None,procedural_dentition=False,oral_visibility=False):
    import bpy
    import numpy as np
    from bl_ext.user_default.mpfb.services import (
        HumanService,TargetService,ExportService,FaceService,RigService,AssetService)
    from video.render_talk import camera_and_lights
    from tools.mpfb_headless_probe import _stash_armature_modifier
    from tools.mouth_anatomy import UPPER_SEAT_M,TONGUE_SEAT_M

    if oral_anatomy:
        if character!='demo_head_a' or rigged_seam_probe:
            raise ValueError('E_ID025_REQUIRES_HEAD_A')
        if oral_isolation or dental_arch_isolation:
            raise ValueError('E_ID025_EXCLUSIVE_MODE')
        if not all((align_accessories,audit_oral_motion,oral_correctives,
                    mhclo_dentition)):
            raise ValueError('E_ID025_REQUIRES_VERIFIED_ORAL_PIPELINE')
        upper_seat=UPPER_SEAT_M if upper_seat is None else float(upper_seat)
        tongue_seat=TONGUE_SEAT_M if tongue_seat is None else float(tongue_seat)
        seam_jaw_stills=True
    if procedural_dentition:
        if not oral_anatomy:
            raise ValueError('E_ID028_REQUIRES_ORAL_ANATOMY')
        if not all((align_accessories,audit_oral_motion,oral_correctives,
                    mhclo_dentition,seam_jaw_stills)):
            raise ValueError('E_ID028_REQUIRES_VERIFIED_ORAL_PIPELINE')

    if oral_correctives and not (align_accessories and audit_oral_motion):
        raise ValueError('E_ORAL_CORRECTIVES_REQUIRE_ALIGNMENT_AND_AUDIT')
    if mhclo_dentition and not oral_correctives:
        raise ValueError('E_MHCLO_DENTITION_NEEDS_ORAL_CORRECTIVES')
    if rigged_seam_probe and any((
            align_accessories,audit_oral_motion,oral_correctives,mhclo_dentition)):
        raise ValueError('E_RIGGED_SEAM_PROBE_ISOLATED_ONLY')
    if seam_jaw_stills and (character!='demo_head_a' or rigged_seam_probe or
            not all((align_accessories,audit_oral_motion,oral_correctives,
                     mhclo_dentition))):
        raise ValueError('E_ID022_REQUIRES_HEAD_A_AND_VERIFIED_ORAL_PIPELINE')
    if oral_isolation and not seam_jaw_stills:
        raise ValueError('E_ID023_VISIBILITY_REQUIRES_SEAM_JAW_STILLS')
    if dental_arch_isolation and (
            not seam_jaw_stills or oral_isolation):
        raise ValueError('E_ID024_ARCH_VISIBILITY_REQUIRES_EXCLUSIVE_SEAM_JAW_STILLS')
    output=Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError('E_ANATOMY_POSE_OUTPUT_EXISTS')
    recipe=load_recipe(ROOT/'character/recipes'/f'{character}.json')
    if 'head_shape' not in recipe:
        raise ValueError('E_NEEDS_DETAILED_HEAD_SHAPE')
    plan=load_plan(plan_file)
    resolved=resolve_native_assets(plan,AssetService.find_asset_absolute_path)
    # Validate all files and parameters BEFORE creating the Blender scene.
    macro=apply_macro_overrides(TargetService.get_default_macro_info_dict(),
                                recipe['macros'])
    output.mkdir(parents=True,exist_ok=False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    source=HumanService.create_human(
        mask_helpers=True,detailed_helpers=True,extra_vertex_groups=True,
        feet_on_ground=True,scale=0.1,macro_detail_dict=macro)
    if source is None or source.type!='MESH':
        raise RuntimeError('E_MPFb_HUMAN_SOURCE_MISSING')
    rig=HumanService.add_builtin_rig(source,'default',import_weights=True)
    if rig is None or rig.type!='ARMATURE' or len(rig.data.bones)!=163:
        raise RuntimeError('E_MPFb_SOURCE_RIG')
    source_assets={}
    for asset in resolved:
        obj=HumanService.add_mhclo_asset(
            asset['_absolute_path_for_blender_only'],source,
            asset_type=asset['category'].title(),
            subdiv_levels=0,material_type=asset['material_type'],
            set_up_rigging=True,interpolate_weights=True,
            import_subrig=True,import_weights=True)
        if obj is None or obj.type!='MESH' or not len(obj.data.vertices):
            raise RuntimeError('E_SOURCE_ANATOMY_ATTACH_'+asset['category'])
        source_assets[asset['category']]=obj

    collection=bpy.data.collections.new('livynth_anatomy_ab_export_copy')
    bpy.context.scene.collection.children.link(collection)
    copied=ExportService.create_character_copy(
        source,name_suffix='_anatomy_ab_copy',place_in_collection=collection)
    if copied is None:
        raise RuntimeError('E_ANATOMY_COPY_NOT_CREATED')
    copies=list(collection.objects)
    meshes=[o for o in copies if o.type=='MESH']
    if len(meshes)<4:
        raise RuntimeError('E_COPIED_ANATOMY_MISSING: '+repr([x.name for x in meshes]))
    # The unbaked full-body mesh has far more vertices than eyes/teeth/tongue.
    # Never identify an attached tooth mesh as the character basemesh.
    body=max(meshes,key=lambda item:len(item.data.vertices))
    if len(body.data.vertices)<15000:
        raise RuntimeError('E_COPIED_BASEMESH_NOT_FOUND')
    copied_rigs=[o for o in copies if o.type=='ARMATURE' and len(o.data.bones)==163]
    if len(copied_rigs)!=1:
        raise RuntimeError('E_COPIED_163_JOINT_RIG')
    copy_rig=copied_rigs[0]
    actual_assets={}
    for item in resolved:
        label=Path(item['relative_path']).stem
        choices=[obj for obj in meshes if obj!=body and
                 label.lower() in obj.name.lower()]
        if len(choices)!=1:
            raise RuntimeError('E_COPIED_ASSET_'+item['category']+
                               ': '+repr([x.name for x in meshes]))
        actual_assets[item['category']]=choices[0]
    for obj in actual_assets.values():
        if (not obj.vertex_groups or
            not any(m.type=='ARMATURE' and m.object==copy_rig
                    for m in obj.modifiers)):
            raise RuntimeError('E_COPIED_ASSET_RIG_MISMATCH_'+obj.name)

    if rigged_seam_probe:
        # IDENTITY-021 must stop BEFORE head deformation, FaceService morphs,
        # oral correctives, camera setup or any render. Mutate only a disposable
        # third copy of the rigged teeth mesh, never the source/export objects.
        from bl_ext.user_default.mpfb.entities.clothes.mhclo import Mhclo
        from tools.rigged_seam_copy_probe import prove_rigged_teeth_seam
        dental_source=next(x for x in resolved if x['category']=='teeth')
        teeth_meta=Mhclo()
        teeth_meta.load(dental_source['_absolute_path_for_blender_only'])
        report={
            'schema':'livynth.mhclo.rigged-seam-probe.v1',
            'character':character,
            'source_teeth_sha256':dental_source['sha256'],
            'human_created_in_memory':True,
            'source_asset_modified':False,
            'existing_glbs_modified':False,
            'render_started':False,
        }
        try:
            report.update(prove_rigged_teeth_seam(
                source_assets['teeth'],actual_assets['teeth'],copy_rig,
                teeth_meta))
        except Exception as exc:
            report.update({
                'status':'FAIL_RIGGED_SEAM_COPY_NOT_PRODUCTION_QA',
                'error_type':type(exc).__name__,
                'error':str(exc),
                'visual_quality':'NOT_TESTED',
                'facial_motion':'NOT_TESTED',
            })
        (output/'rigged_seam_probe.json').write_text(
            json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('[LIVYNTH RIGGED SEAM] '+json.dumps({
            'status':report['status'],
            'error':report.get('error'),
            'report':str((output/'rigged_seam_probe.json').resolve()),
        },indent=2),flush=True)
        if report['status'].startswith('FAIL_'):
            raise RuntimeError('E_RIGGED_SEAM_PROBE_FAILED: '+str(report.get('error')))
        return report

    dental_mask=None
    dental_mapping_audit=None
    seam_copy_audit=None
    if mhclo_dentition:
        from bl_ext.user_default.mpfb.entities.clothes.mhclo import Mhclo
        from character.mhclo_dentition import classify_dentition_mhclo
        if len(source.data.vertices)!=19158:
            raise RuntimeError('E_MHCLO_UNEXPECTED_HM08_NATIVE_SOURCE')
        tooth_original=source_assets['teeth']
        tooth_copy=actual_assets['teeth']
        if len(tooth_original.data.vertices)!=len(tooth_copy.data.vertices):
            raise RuntimeError('E_MHCLO_COPIED_TEETH_VERTEX_COUNT')
        # MPFB MHCLO mapping is ordered by original OBJ vertex index.
        # Verify the cloned asset retained that ordering before using it.
        src_world=np.asarray([tuple(tooth_original.matrix_world @ v.co)
                              for v in tooth_original.data.vertices],dtype=np.float64)
        copy_world=np.asarray([tuple(tooth_copy.matrix_world @ v.co)
                               for v in tooth_copy.data.vertices],dtype=np.float64)
        if float(np.linalg.norm(src_world-copy_world,axis=1).max())>0.0001:
            raise RuntimeError('E_MHCLO_COPY_VERTEX_ORDER_NOT_VERIFIED')
        tooth_path=next(x['_absolute_path_for_blender_only']
                        for x in resolved if x['category']=='teeth')
        metadata=Mhclo()
        metadata.load(tooth_path)
        if seam_jaw_stills:
            from tools.mhclo_seam_render_copy import prepare_seamed_render_copy
            dental_mask,dental_mapping_audit,seam_copy_audit=(
                prepare_seamed_render_copy(
                    tooth_original,tooth_copy,copy_rig,metadata))
        else:
            dental_mask,dental_mapping_audit=classify_dentition_mhclo(
                len(tooth_copy.data.vertices),metadata.verts,
                [tuple(poly.vertices) for poly in tooth_copy.data.polygons],
                source_vertex_count=len(source.data.vertices))
        dental_mapping_audit['pinned_asset_sha256']=next(
            x['sha256'] for x in resolved if x['category']=='teeth')
        dental_mapping_audit['copied_vertex_order_error_m']=round(
            float(np.linalg.norm(src_world-copy_world,axis=1).max()),9)

    # Same verified pre-face-keys sequence used by the working Head A/B GLBs.
    _stash_armature_modifier(body)
    TargetService.bake_targets(body)
    ExportService.bake_modifiers_remove_helpers(
        body,bake_masks=True,bake_subdiv=True,
        remove_helpers=True,also_proxy=True)
    if len(body.data.vertices)!=13380 or len(body.data.polygons)!=13378:
        raise RuntimeError('E_ANATOMY_NATIVE_TOPOLOGY_CHANGED')
    if seam_jaw_stills:
        if (len(actual_assets['teeth'].data.vertices)!=3868 or
                len(actual_assets['teeth'].data.polygons)!=3540):
            raise RuntimeError('E_ID022_TOOTH_MESH_CHANGED_DURING_BODY_BAKE')
        # The MPFB baking stage must not reintroduce a cross-jaw polygon.
        mask_after,audit_after=classify_dentition_mhclo(
            3868,metadata.verts,
            [tuple(f.vertices) for f in actual_assets['teeth'].data.polygons],
            source_vertex_count=len(source.data.vertices))
        if (audit_after['mixed_jaw_faces']!=0 or
                not (mask_after==dental_mask).all()):
            raise RuntimeError('E_ID022_POST_BAKE_MHCLO_MAPPING')
    source_points=np.asarray([tuple(v.co) for v in body.data.vertices],dtype=np.float64)
    quads=np.asarray([tuple(p.vertices) for p in body.data.polygons],dtype=np.int64)
    planned,_=apply_head_shape(source_points,quads,recipe['head_shape'])
    for vertex,position in zip(body.data.vertices,planned):
        vertex.co=tuple(float(v) for v in position)
    body.data.update()
    actual=np.asarray([tuple(v.co) for v in body.data.vertices],dtype=np.float64)
    shape_audit=audit_realized_head_shape(source_points,planned,actual,quads)
    alignment_audits={}
    if align_accessories:
        from character.anatomy_alignment import apply_to_blender_object
        # This is an OPT-IN IDENTITY-012 experiment. Same identity field as
        # body, evaluated in the original baked BODY coordinate frame.
        # Do not move original source anatomical objects or replace GLBs.
        bpy.context.view_layer.update()
        for cat,proxy in actual_assets.items():
            alignment_audits[cat]=apply_to_blender_object(
                body,proxy,source_points,recipe['head_shape'])
            if not alignment_audits[cat]['mesh_vertices_unchanged']:
                raise RuntimeError('E_ANATOMY_ALIGNMENT_CHANGED_TOPOLOGY_'+cat)
    RigService.ensure_armature_modifier(body,copy_rig)
    FaceService.load_targets(body,load_microsoft_visemes=False,
                             load_meta_visemes=True,load_arkit_faceunits=True)
    FaceService.interpolate_targets(body)
    if body.data.shape_keys is None:
        raise RuntimeError('E_ANATOMY_FACE_TARGETS_MISSING')
    names=[k.name for k in body.data.shape_keys.key_blocks if k.name!='Basis']
    if len(names)!=67 or not set().union(*(set(x) for x in POSES.values())).issubset(set(names)):
        raise RuntimeError('E_ANATOMY_67_MORPH_INTERFACE')

    oral_corrective_audit=None
    if oral_correctives:
        from character.oral_correctives import add_oral_shape_keys
        oral_corrective_audit=add_oral_shape_keys(
            body,{category:actual_assets[category] for category in ('teeth','tongue')},
            lower_teeth_mask=dental_mask,dental_mapping_report=dental_mapping_audit)
    controlled={category:actual_assets[category] for category in ('teeth','tongue')} if oral_correctives else None

    # Remove the original character so it cannot obscure the cloned one.
    for obj in list(bpy.data.objects):
        if obj not in copies:
            bpy.data.objects.remove(obj,do_unlink=True)

    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=400
    scene.render.resolution_y=600
    scene.render.resolution_percentage=100
    scene.eevee.taa_render_samples=16
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.image_settings.color_depth='8'
    scene.view_settings.view_transform='AgX'
    camera_and_lights(scene,list(actual_assets.values())+[body],
                      'negative-y','studio')

    oral_motion_audit=(_audit_jaw_and_visemes(
        body,actual_assets,use_oral_correctives=oral_correctives)
        if audit_oral_motion else None)

    mouth_anatomy_audit=None
    if oral_anatomy:
        mouth_anatomy_audit=_apply_mouth_anatomy(
            body,actual_assets['teeth'],actual_assets['tongue'],dental_mask,
            upper_seat=upper_seat,tongue_seat=tongue_seat,
            tooth_scale=tooth_scale,lip_push=lip_push,
            tongue_scale=tongue_scale,tongue_shift_y=tongue_shift_y,
            oral_assets=controlled)
        from character.seamed_jaw_motion import audit_seamed_jaw_motion as _audit_after_fix
        _set_morphs(body,{},oral_assets=controlled)
        neutral_teeth=_evaluated_world_vertices(
            {'teeth':actual_assets['teeth']})['teeth']
        _set_morphs(body,POSES['jaw_open'],oral_assets=controlled)
        opened_teeth=_evaluated_world_vertices(
            {'teeth':actual_assets['teeth']})['teeth']
        after_fix=_audit_after_fix(neutral_teeth,opened_teeth,dental_mask)
        mouth_anatomy_audit['seamed_jaw_motion_after_fix']=after_fix
        if after_fix['status']!='PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA':
            raise RuntimeError('E_ID025_ORAL_MOTION_AFTER_FIX')
        _set_morphs(body,{},oral_assets=controlled)

    if procedural_dentition:
        # IDENTITY-028: replace the photo slab with the procedural
        # permanent dentition; correct the lip-opening border. The slab
        # itself is hidden from renders and never edited or exported.
        from tools.procedural_dentition_blender import (
            create_procedural_objects,storage_validate,
            procedural_collision_audit,procedural_motion_audit,
            reshape_lip_opening)
        slab_collision_reference={pose:{'pairs':audit['upper_lower_arch_intersections']['pairs'],
                                        'depth_max_m':audit['upper_lower_arch_intersections']['summary']['crossing_depth_max_m'],
                                        'tongue_pairs':audit['tongue_teeth_intersections']['pairs'],
                                        'tongue_depth_max_m':audit['tongue_teeth_intersections']['summary']['crossing_depth_max_m'],
                                        'tongue_teeth_min_m':audit['distances']['tongue_to_teeth']['min_m']}
                                  for pose,audit in mouth_anatomy_audit['collision_audits'].items()}
        proc_objects,proc_audit=create_procedural_objects(body)
        storage_validate(body,proc_objects)
        lip_audit=reshape_lip_opening(body)
        slab=actual_assets['teeth']
        slab_hide_render_archived=slab.hide_render
        slab.hide_render=True
        # NOTE: hide_viewport must stay False - hiding from the viewport
        # removes the object from the view layer and the depsgraph would
        # evaluate it with no shape keys, silently zeroing the motion audit.
        # From here the procedural arches ARE the visible teeth; every
        # downstream _set_morphs must drive them. Re-binding the
        # corrective-objects dict is enough - _set_morphs sets
        # jawOpen/viseme_aa on any object with those keys.
        controlled=dict(controlled)
        controlled.update({
            'proc_upper_teeth':proc_objects['upper_teeth'],
            'proc_lower_teeth':proc_objects['lower_teeth'],
            'proc_upper_gum':proc_objects['upper_gum'],
            'proc_lower_gum':proc_objects['lower_gum'],
        })
        proc_audits={}
        for label,weights in (('jaw_open_0_85',POSES['jaw_open']),
                              ('viseme_aa_0_90',POSES['viseme_aa']),
                              ('viseme_pp_0_90',POSES['viseme_pp'])):
            _set_morphs(body,weights,oral_assets=controlled)
            proc_audits[label]=procedural_collision_audit(
                proc_objects['upper_teeth'],proc_objects['lower_teeth'],
                actual_assets['tongue'],label)
        _set_morphs(body,POSES['neutral'],oral_assets=controlled)
        proc_audits['neutral']=procedural_collision_audit(
            proc_objects['upper_teeth'],proc_objects['lower_teeth'],
            actual_assets['tongue'],'neutral')
        _set_morphs(body,{},oral_assets=controlled)
        proc_motion=procedural_motion_audit(
            proc_objects['upper_teeth'],proc_objects['lower_teeth'])
        if proc_motion['status']!='PASS_PROCEDURAL_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA':
            raise RuntimeError('E_ID028_PROCEDURAL_MOTION: '+str(proc_motion))
        # Visible-arch oral motion audit (the slab audit above stays as
        # the source reference; this one audits the rendered teeth).
        from character.anatomy_motion_audit import diagnose_oral_motion
        visible_assets={'body':body,'teeth':proc_objects['lower_teeth'],
                        'tongue':actual_assets['tongue']}
        _set_morphs(body,{},oral_assets=controlled)
        before_vis=_evaluated_world_vertices(visible_assets)
        oral_motion_visible={}
        for pose in ('jaw_open','viseme_aa'):
            _set_morphs(body,POSES[pose],oral_assets=controlled)
            after_vis=_evaluated_world_vertices(visible_assets)
            oral_motion_visible[pose]=diagnose_oral_motion(
                before_vis,after_vis,pose=pose)
        _set_morphs(body,{},oral_assets=controlled)
        mouth_anatomy_audit['collision_audits']=proc_audits
        mouth_anatomy_audit['slab_collision_audits_reference']=slab_collision_reference
        mouth_anatomy_audit['dental_rebuild']={
            **proc_audit,
            'lip_opening':lip_audit,
            'procedural_jaw_motion':proc_motion,
            'oral_motion_visible_lower_arch':oral_motion_visible,
            'slab_hidden_from_renders':True,
            'slab_viewport_hidden':False,
            'slab_hide_render_archived':slab_hide_render_archived,
            'slab_untouched':True,
            'slab_collision_audits_reference':slab_collision_reference,
            'teeth_collision_audits_visible':proc_audits,
            'dental_visual_quality':'PENDING_INDEPENDENT_REVIEW',
            'existing_glbs_modified':False,
        }

    # IDENTITY-029: isolated dental-visibility and lip-aperture diagnostics
    # (runs after the procedural dentition and the IDENTITY-028 lip-opening
    # correction, so the 'before' stage reflects the IDENTITY-028 state and
    # the 'after' stage reflects the almond reshape).
    oral_visibility_audit = None
    if procedural_dentition and oral_visibility:
        from tools.procedural_dentition_blender import (
            reshape_lip_almonder, oral_collision_audit_full)
        from tools.oral_visibility_blender import capture_oral_visibility

        poses = ('neutral', 'jaw_open', 'viseme_aa', 'viseme_pp')

        # --- 'before' stage: after IDENTITY-028 corner lift -------------
        def set_pose(name):
            _set_morphs(body, POSES[name], oral_assets=controlled)

        def render_diag(name):
            return _render(scene, body, name, 0, output, oral_closeup=True)

        diag_before = capture_oral_visibility(
            scene, body, proc_objects, actual_assets['tongue'],
            render_diag, set_pose, poses=poses, stage='before',
            cavity_indexes=mouth_anatomy_audit.get('cavity_indexes'))
        oral_visibility_audit = {'before': diag_before}

        # --- 'after' stage: apply the almond reshape --------------------
        lip_almond_audit = reshape_lip_almonder(body)

        # --- extended collision audit (after almond) --------------------
        full_audits = {}
        for label, weights in (('neutral', POSES['neutral']),
                               ('jaw_open', POSES['jaw_open']),
                               ('viseme_aa', POSES['viseme_aa']),
                               ('viseme_pp', POSES['viseme_pp'])):
            _set_morphs(body, weights, oral_assets=controlled)
            full_audits[label] = oral_collision_audit_full(
                body,
                proc_objects['upper_teeth'],
                proc_objects['lower_teeth'],
                actual_assets['tongue'],
                proc_objects['upper_gum'],
                proc_objects['lower_gum'],
                label)
            _set_morphs(body, POSES['neutral'], oral_assets=controlled)

        diag_after = capture_oral_visibility(
            scene, body, proc_objects, actual_assets['tongue'],
            render_diag, set_pose, poses=poses, stage='after',
            cavity_indexes=mouth_anatomy_audit.get('cavity_indexes'))
        oral_visibility_audit['after'] = diag_after
        oral_visibility_audit['lip_almond'] = lip_almond_audit
        oral_visibility_audit['extended_collision'] = full_audits

    seam_jaw_motion_audit=None
    if seam_jaw_stills:
        from character.seamed_jaw_motion import audit_seamed_jaw_motion
        _set_morphs(body,{},oral_assets=controlled)
        neutral_teeth=_evaluated_world_vertices({'teeth':actual_assets['teeth']})['teeth']
        _set_morphs(body,POSES['jaw_open'],oral_assets=controlled)
        opened_teeth=_evaluated_world_vertices({'teeth':actual_assets['teeth']})['teeth']
        seam_jaw_motion_audit=audit_seamed_jaw_motion(
            neutral_teeth,opened_teeth,dental_mask)
        _set_morphs(body,{},oral_assets=controlled)

    if seam_jaw_stills and (
            not isinstance(oral_motion_audit,dict) or
            oral_motion_audit.get('jaw_open',{}).get('status')!=
                'ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED' or
            seam_jaw_motion_audit['status']!=
                'PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA'):
        (output/'seam_jaw_gate_failure.json').write_text(
            json.dumps({'status':'FAIL_ID022_ORAL_MOTION_BEFORE_RENDER',
                        'oral_motion_audit':oral_motion_audit,
                        'seam_copy_audit':seam_copy_audit,
                        'seam_jaw_motion_audit':seam_jaw_motion_audit},
                       indent=2)+'\n',encoding='utf-8')
        raise RuntimeError('E_ID022_ORAL_MOTION_BEFORE_RENDER')
    images=[]
    # Preserve the IDENTITY-029 diagnostic audit populated above;
    # only reset when the diagnostic block did not run.
    if not (procedural_dentition and oral_visibility):
        oral_visibility_audit = None
    dental_arch_location_audit=None
    dental_arch_render_audit=None
    if oral_anatomy:
        # IDENTITY-025: neutral, jaw-open and speech poses after the mouth fix.
        for label in ('neutral','jaw_open'):
            _set_morphs(body,POSES[label],oral_assets=controlled)
            images.append(_render(
                scene,body,'front_'+label,0,output,oral_closeup=True))
        for label in ('viseme_aa','viseme_pp'):
            _set_morphs(body,POSES[label],oral_assets=controlled)
            images.append(_render(
                scene,body,'front_'+label,0,output,oral_closeup=True))
        _set_morphs(body,POSES['viseme_aa'],oral_assets=controlled)
        images.append(_render(
            scene,body,'three_quarter_viseme_aa',38,output,oral_closeup=True))
        _set_morphs(body,{},oral_assets=controlled)
    elif dental_arch_isolation:
        from character.seamed_jaw_motion import PASS as SEAM_PASS
        from tools.mhclo_arch_attribution import (
            isolated_arch_objects,arch_location_audit)
        _set_morphs(body,POSES['jaw_open'],oral_assets=controlled)
        evaluated_assets=_evaluated_world_vertices({
            'teeth':actual_assets['teeth'],
            'tongue':actual_assets['tongue']})
        dental_arch_location_audit=arch_location_audit(
            evaluated_assets['teeth'],evaluated_assets['tongue'],dental_mask)
        teeth=actual_assets['teeth']
        tongue=actual_assets['tongue']
        archived_body_hide=body.hide_render
        archived_teeth_hide=teeth.hide_render
        archived_tongue_hide=tongue.hide_render
        try:
            with isolated_arch_objects(teeth,dental_mask) as arch:
                upper,lower=arch['upper'],arch['lower']
                teeth.hide_render=True
                tongue.hide_render=True
                views=(
                    ('jaw_upper_only',True,False,True),
                    ('jaw_lower_only',False,True,True),
                    ('jaw_both_arches',True,True,True),
                    ('jaw_lower_no_body',False,True,False),
                )
                audit_rows=[]
                for name,upper_visible,lower_visible,body_visible in views:
                    upper.hide_render=not upper_visible
                    lower.hide_render=not lower_visible
                    body.hide_render=not body_visible
                    bpy.context.view_layer.update()
                    images.append(_render(
                        scene,body,name,0,output,oral_closeup=True))
                    audit_rows.append({
                        'filename':name+'.png',
                        'upper_arch_visible':upper_visible,
                        'lower_arch_visible':lower_visible,
                        'body_visible':body_visible,
                        'tongue_visible':False,
                        'original_rigged_teeth_visible':False,
                        'source_assets_modified':False,
                        'visual_approval':'PENDING',
                    })
                dental_arch_render_audit={
                    'schema':'livynth.mhclo.arch-attribution.v1',
                    'source_face_count':arch['source_face_count'],
                    'upper_face_count':arch['upper_face_count'],
                    'lower_face_count':arch['lower_face_count'],
                    'rendered_variants':audit_rows,
                    'temporary_evaluated_arch_objects_removed_on_exit':True,
                    'photorealism':'NOT_TESTED',
                }
        finally:
            body.hide_render=archived_body_hide
            teeth.hide_render=archived_teeth_hide
            tongue.hide_render=archived_tongue_hide
            bpy.context.view_layer.update()
    elif oral_isolation:
        from tools.oral_asset_visibility import capture_oral_visibility
        _set_morphs(body,POSES['jaw_open'],oral_assets=controlled)
        images,oral_visibility_audit=capture_oral_visibility(
            actual_assets,
            lambda name:_render(scene,body,name,0,output,oral_closeup=True),
            update=lambda:bpy.context.view_layer.update())
    elif seam_jaw_stills:
        # Only two front stills for a first owner visual gate. No A/B batch.
        for label in ('neutral','jaw_open'):
            _set_morphs(body,POSES[label],oral_assets=controlled)
            images.append(_render(
                scene,body,'front_'+label,0,output,oral_closeup=True))
    else:
        for label,weights in POSES.items():
            _set_morphs(body,weights,oral_assets=controlled)
            images.append(_render(scene,body,'front_'+label,0,output))
        _set_morphs(body,POSES['jaw_open'],oral_assets=controlled)
        images.append(_render(scene,body,'three_quarter_jaw_open',38,output))
    installed_mhclo_reverified={}
    for entry in resolved:
        digest=_sha256_file(entry['_absolute_path_for_blender_only'])
        installed_mhclo_reverified[entry['category']]={
            'sha256':digest,
            'expected_sha256':entry['sha256'],
            'unchanged':bool(digest==entry['sha256']),
        }
    report={
        'schema':SCHEMA,'character_id':character,
        'status':('CAPTURED_HEAD_A_MOUTH_ANATOMY_PENDING_VISUAL_REVIEW'
                  if oral_anatomy else
                  'CAPTURED_HEAD_A_DENTAL_ARCH_ISOLATION_PENDING_VISUAL_REVIEW'
                  if dental_arch_isolation else
                  'CAPTURED_HEAD_A_ORAL_ISOLATION_PENDING_VISUAL_REVIEW'
                  if oral_isolation else
                  'CAPTURED_HEAD_A_SEAM_JAW_STILLS_PENDING_VISUAL_REVIEW'
                  if seam_jaw_stills else
                  'CAPTURED_ANATOMY_AB_REQUIRES_VISUAL_REVIEW'),
        'blender_version':bpy.app.version_string,
        'source_body_sha256':neutral_positions_sha256(source_points),
        'fitted_body_sha256':neutral_positions_sha256(actual),
        'native_topology_sha256':neutral_topology_sha256(quads),
        'head_shape_audit':shape_audit,
        'native_body_vertices':len(body.data.vertices),
        'native_quads':len(body.data.polygons),
        'rig_joints':len(copy_rig.data.bones),
        'facial_morph_count':len(names),
        'facial_morph_names':names,
        'anatomy_alignment_mode':(
            'shared_identity_field' if align_accessories else 'original_mpfb_fit'),
        'anatomy_alignment_audit':alignment_audits,
        'oral_corrective_mode':('MORPH_LINKED_LOWER_TEETH_AND_TONGUE'
                                 if oral_correctives else 'OFF'),
        'oral_corrective_audit':oral_corrective_audit,
        'dental_segmentation_mode':('MHCLO_HM08_UPPER_LOWER_HELPERS'
                                    if mhclo_dentition else 'LEGACY_Z_SPLIT'),
        'dental_mapping_audit':dental_mapping_audit,
        'seamed_render_copy_audit':seam_copy_audit,
        'seamed_jaw_motion_audit':seam_jaw_motion_audit,
        'mouth_anatomy_audit':mouth_anatomy_audit,
        'oral_asset_visibility_audit':oral_visibility_audit,
        'oral_visibility_audit':oral_visibility_audit,
        'dental_arch_location_audit':dental_arch_location_audit,
        'dental_arch_render_audit':dental_arch_render_audit,
        'oral_motion_audit':oral_motion_audit,
        'oral_motion_status':('RECORDED_DO_NOT_INFER_VISUAL_APPROVAL'
                              if oral_motion_audit else 'NOT_RUN'),
        'assets':[
            {'category':cat,'source_sha256':entry['sha256'],
             'size_bytes':entry.get('size_bytes'),
             'mesh_vertices':len(actual_assets[cat].data.vertices),
             'rigged_to_copied_armature':True}
            for cat,entry in [(x['category'],x) for x in resolved]
        ],
        'installed_mhclo_reverified':installed_mhclo_reverified,
        'images':images,
        'existing_glbs_modified':False,
        'eyes_teeth_tongue_follow_expression':'PENDING_VISUAL_REVIEW',
        'natural_animation':'NOT_TESTED',
        'character_001_likeness':'NOT_TESTED',
        'render_scope':('HEAD_A_NEUTRAL_JAWOPEN_AND_SPEECH_MOUTH_ANATOMY'
                        if oral_anatomy else
                        'HEAD_A_JAW_OPEN_DENTAL_ARCH_ATTRIBUTION_ONLY'
                        if dental_arch_isolation else
                        'HEAD_A_JAW_OPEN_ORAL_ASSET_VISIBILITY_ONLY'
                        if oral_isolation else
                        'HEAD_A_FRONT_NEUTRAL_AND_JAW_OPEN_ONLY'
                        if seam_jaw_stills else 'STANDARD_AB_POSES'),
        'dental_visual_quality':'PENDING_INDEPENDENT_REVIEW',
        'framing':('MOUTH_FOCUSED_FACE_CLOSEUP'
                   if seam_jaw_stills else 'EXISTING_STANDARD_SHOT'),
        'full_character_glb_export':'NOT_TESTED',
    }
    (output/'anatomy_pose_report.json').write_text(
        json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('[LIVYNTH IDENTITY-011] '+json.dumps(
        {'character':character,'status':report['status'],
         'images':len(images),'morphs':len(names)},indent=2))
    return report


if __name__=='__main__':
    if '--' not in sys.argv: raise SystemExit('Arguments required after Blender --')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--character',choices=('demo_head_a','demo_head_b'),required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--rigged-seam-probe',action='store_true',
                        help='IDENTITY-021 disposable rigged-teeth geometry check; no render')
    parser.add_argument('--seam-jaw-stills',action='store_true',
                        help='IDENTITY-022 opt-in Head A two front stills, cut only copied teeth')
    parser.add_argument('--oral-isolation',action='store_true',
                        help='IDENTITY-023 Head A jaw-open with teeth/tongue on-off comparison')
    parser.add_argument('--dental-arch-isolation',action='store_true',
                        help='IDENTITY-024 split evaluated upper/lower jaw arches for attribution')
    parser.add_argument('--oral-anatomy',action='store_true',
                        help='IDENTITY-025 opt-in mouth anatomy fix + five mouth-focused stills')
    parser.add_argument('--upper-seat',type=float,default=None,
                        help='IDENTITY-025 upper-arch seat (m, default pinned in tools/mouth_anatomy.py)')
    parser.add_argument('--tongue-seat',type=float,default=None,
                        help='IDENTITY-025 tongue seat (m, default pinned in tools/mouth_anatomy.py)')
    parser.add_argument('--tooth-scale',type=float,default=None,
                        help='IDENTITY-026 teeth uniform scale (default pinned in tools/mouth_anatomy.py)')
    parser.add_argument('--lip-push',type=float,default=None,
                        help='IDENTITY-026 mentolabial sulcus forward lift in m (default pinned)')
    parser.add_argument('--tongue-scale',type=float,default=None,
                        help='IDENTITY-027 tongue uniform scale (default pinned in tools/mouth_anatomy.py)')
    parser.add_argument('--tongue-shift-y',type=float,default=None,
                        help='IDENTITY-027 tongue posterior shift in m (bounded; default pinned)')
    parser.add_argument('--procedural-dentition',action='store_true',
                        help='IDENTITY-028 procedural permanent dentition replaces the photo slab; corrects the lip-opening border')
    parser.add_argument('--oral-visibility',action='store_true',
                        help='IDENTITY-029 isolated dental-visibility and lip-aperture diagnostics; requires --procedural-dentition')
    parser.add_argument('--mhclo-dentition',action='store_true',
                        help='Use original MPFB teeth helper mapping instead of visual Z split')
    parser.add_argument('--oral-correctives',action='store_true',
                        help='Opt-in lower dental/tongue corrective morphs; requires --align-accessories --audit-oral-motion')
    parser.add_argument('--audit-oral-motion',action='store_true',
                        help='Measure evaluated teeth/tongue world motion for jawOpen and AA')
    parser.add_argument('--align-accessories',action='store_true',
                        help='Apply same detailed identity field to copied eyes/teeth/tongue')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    run(args.character,args.plan,args.out,align_accessories=args.align_accessories,
        audit_oral_motion=args.audit_oral_motion,oral_correctives=args.oral_correctives,
        mhclo_dentition=args.mhclo_dentition,
        rigged_seam_probe=args.rigged_seam_probe,
        seam_jaw_stills=args.seam_jaw_stills,
        oral_isolation=args.oral_isolation,
        dental_arch_isolation=args.dental_arch_isolation,
        oral_anatomy=args.oral_anatomy,
        upper_seat=args.upper_seat,tongue_seat=args.tongue_seat,
        tooth_scale=args.tooth_scale,lip_push=args.lip_push,
        tongue_scale=args.tongue_scale,tongue_shift_y=args.tongue_shift_y,
        procedural_dentition=args.procedural_dentition,
        oral_visibility=args.oral_visibility)
