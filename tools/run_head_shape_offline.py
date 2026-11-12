#!/usr/bin/env python3
"""Produce unrigged OBJ identity geometry variants from owner's neutral mesh ZIP/NPZ.

Offline proof only: these OBJs have NO skeleton, skin, morphs or likeness claims.
The Blender A/B GLB run is a separate and mandatory validation gate.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import zipfile
import numpy as np
from character.head_shape import apply_head_shape
from character.identity_recipe import load_recipe,neutral_positions_sha256,neutral_topology_sha256


def read_neutral(path):
    path=Path(path)
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as archive:
            with np.load(io.BytesIO(archive.read('neutral_mesh.npz')),allow_pickle=False) as data:
                return data['vertices'].copy(),data['quads'].copy()
    with np.load(path,allow_pickle=False) as data:
        return data['vertices'].copy(),data['quads'].copy()


def export_obj(path, positions, quads):
    with Path(path).open('w',encoding='ascii') as output:
        output.write('# LIVYNTH geometry-only demonstration: NOT RIGGED\n')
        for x,y,z in positions:
            output.write(f'v {x:.9f} {y:.9f} {z:.9f}\n')
        for a,b,c,d in quads:
            output.write(f'f {a+1} {b+1} {c+1} {d+1}\n')


def run(neutral,recipes,output_dir):
    positions,quads=read_neutral(neutral)
    if len(positions)!=13380 or len(quads)!=13378:
        raise ValueError('E_UNEXPECTED_NEUTRAL_TOPOLOGY; test only verified C001 baked mesh')
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=False)  # never overwrite previous runs
    source_hash=neutral_positions_sha256(positions)
    topo_hash=neutral_topology_sha256(quads)
    result={'schema':'livynth.identity.offline-proof.v1',
            'status':'PASS_NUMERIC_IDENTITY_VARIANTS_NOT_RIGGED_OR_LIKENESS',
            'source_positions_sha256':source_hash,'topology_sha256':topo_hash,
            'source_vertices':len(positions),'quads':len(quads),'characters':[]}
    for path in recipes:
        recipe=load_recipe(path)
        if 'head_shape' not in recipe:
            raise ValueError('E_HEAD_SHAPE_RECIPE_V2_REQUIRED')
        fit,audit=apply_head_shape(positions,quads,recipe['head_shape'])
        artifact=out/f"{recipe['character_id']}.obj"
        export_obj(artifact,fit,quads)
        result['characters'].append({'id':recipe['character_id'],
             'geometry_sha256':neutral_positions_sha256(fit),'obj':str(artifact),
             'numeric_audit':audit})
    if len({c['geometry_sha256'] for c in result['characters']})!=len(result['characters']):
        raise ValueError('E_IDENTICAL_SHAPE_OUTPUT')
    (out/'identity_offline_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--neutral',type=Path,required=True)
    p.add_argument('--a',type=Path,default=Path('character/recipes/demo_head_a.json'))
    p.add_argument('--b',type=Path,default=Path('character/recipes/demo_head_b.json'))
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    result=run(args.neutral,[args.a,args.b],args.out)
    print(json.dumps(result,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
