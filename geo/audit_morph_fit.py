#!/usr/bin/env python3
"""Independent structural and morph-behavior QA for a C001 candidate GLB."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from geo.morph_fit import GLB, GLBError


def audit(source_path: Path, candidate_path: Path) -> dict:
    a, b = GLB.from_file(source_path), GLB.from_file(candidate_path)
    for field in ('skins', 'animations', 'nodes', 'scenes', 'materials',
                  'textures', 'images', 'samplers', 'cameras'):
        if a.doc.get(field) != b.doc.get(field):
            raise GLBError(f'{field} changed unexpectedly')
    if a.doc.get('meshes') != b.doc.get('meshes'):
        raise GLBError('Mesh primitive descriptors or target names changed')
    if len(a.doc['accessors']) != len(b.doc['accessors']):
        raise GLBError('Accessor count changed')
    total = 0
    visible = set()
    max_disp = 0.
    for mi, mesh in enumerate(a.doc['meshes']):
        for prim in mesh['primitives']:
            pa = a.accessor(prim['attributes']['POSITION'])
            pb = b.accessor(prim['attributes']['POSITION'])
            if pa.shape != pb.shape:
                raise GLBError('Vertex topology changed')
            max_disp = max(max_disp, float(np.linalg.norm(pb-pa,axis=1).max()))
            for attr in ('JOINTS_0', 'WEIGHTS_0', 'TEXCOORD_0'):
                if attr in prim['attributes']:
                    key = prim['attributes'][attr]
                    if not np.array_equal(a.accessor(key), b.accessor(key)):
                        raise GLBError(f'{attr} changed on mesh {mi}')
            if 'indices' in prim:
                key = prim['indices']
                if not np.array_equal(a.accessor(key), b.accessor(key)):
                    raise GLBError(f'Indices changed on mesh {mi}')
            names = mesh.get('extras', {}).get('targetNames', [])
            if len(names) != len(prim.get('targets', [])):
                raise GLBError('Morph name/target length mismatch')
            for i,target in enumerate(prim.get('targets', [])):
                total += 1
                visible.add(names[i])
                for attribute in ('POSITION','NORMAL'):
                    if attribute in target:
                        av = a.accessor(target[attribute])
                        bv = b.accessor(target[attribute])
                        if not np.isfinite(bv).all() or av.shape != bv.shape:
                            raise GLBError(f'Morph {names[i]} invalid on mesh {mi}')
                if 'POSITION' in target:
                    old = a.accessor(target['POSITION'])
                    new = b.accessor(target['POSITION'])
                    # A fitting operation must not silently destroy a working
                    # expression. Allow tiny numerical changes, reject loss.
                    if np.linalg.norm(old) > 1e-4 and np.linalg.norm(new) < .5*np.linalg.norm(old):
                        raise GLBError(f'Morph {names[i]} collapsed on mesh {mi}')
    essential = {'eyeBlinkLeft','eyeBlinkRight','jawOpen','viseme_aa'}
    if not essential.issubset(visible):
        raise GLBError(f'Missing essential face shapes {essential-visible}')
    if not max_disp > 1e-4:
        raise GLBError('Model had no substantive geometric change')
    try:
        import trimesh
        scene = trimesh.load(str(candidate_path),force='scene')
        if len(scene.geometry) != len(b.doc['meshes']):
            raise GLBError('Trimesh glTF import lost geometry')
        geom_count = len(scene.geometry)
    except ImportError:
        geom_count = None
    return {
        'status': 'PASS: GLB structure and morph behavior preserved',
        'mesh_count':len(b.doc['meshes']),
        'skin_count':len(b.doc.get('skins',[])),
        'animation_count':len(b.doc.get('animations',[])),
        'morph_target_instances':total,
        'max_geometric_displacement_mm':round(max_disp*1000,4),
        'trimesh_import_geometry_count':geom_count,
        'visual_identity_and_blender_synchronization': 'NOT VERIFIED'
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--candidate',required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(audit(args.source,args.candidate),indent=2))

if __name__=='__main__':
    main()