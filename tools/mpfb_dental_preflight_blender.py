#!/usr/bin/env python3
"""Lightweight Blender preflight for installed SHA-pinned MPFB teeth_base.

Reads MHCLO and OBJ metadata, writes one small JSON; NO human construction,
scene render, GLB export, asset modification, or install required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from character.native_anatomy import load_plan,verify_asset_file
from character.mhclo_dentition import classify_dentition_mhclo,DentitionMappingError
from tools.mhclo_dental_preflight import (
    SCHEMA,load_obj_topology,inspect_mhclo_weights)


def inspect(plan_file,out):
    import bpy
    from bl_ext.user_default.mpfb.services import AssetService
    from bl_ext.user_default.mpfb.entities.clothes.mhclo import Mhclo

    out=Path(out).resolve()
    if out.exists() or out.is_symlink():
        raise FileExistsError('E_MHCLO_PREFLIGHT_OUTPUT_EXISTS')
    plan=load_plan(plan_file)
    selected=plan['assets']['teeth']
    path=AssetService.find_asset_absolute_path(
        selected['relative_path'],asset_subdir='teeth')
    if not path:
        raise FileNotFoundError('E_PINNED_TEETH_ASSET_MISSING')
    fingerprint=verify_asset_file(path,selected['sha256'])
    metadata=Mhclo()
    metadata.load(path)
    count,faces=load_obj_topology(metadata.obj_file)
    weights=inspect_mhclo_weights(metadata.verts)
    result={
        'schema':SCHEMA,'blender_version':bpy.app.version_string,
        'asset_relative_path':selected['relative_path'],
        'asset_sha256':fingerprint['sha256'],
        'obj_vertices':count,'obj_faces':len(faces),
        'mhclo_entries':len(metadata.verts),
        'weight_diagnostics':weights,
        'human_created':False,'glbs_touched':False,
    }
    try:
        _mask,assignment=classify_dentition_mhclo(
            count,metadata.verts,faces,source_vertex_count=19158)
        result.update({
            'status':'PASS_REAL_MHCLO_JAW_GROUP_MAPPING_NOT_VISUAL_QA',
            'jaw_assignment':assignment,
        })
    except DentitionMappingError as exc:
        result.update({
            'status':'FAIL_REAL_MHCLO_JAW_GROUP_MAPPING',
            'first_error':str(exc),
            'jaw_assignment':'NOT_ACCEPTED',
        })
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('[LIVYNTH DENTAL PREFLIGHT] '+json.dumps({
        'status':result['status'],
        'asset':result['asset_relative_path'],
        'mapped_vertices':len(metadata.verts),
        'signed':weights['signed_weight_vertices'],
        'nonunit':weights['nonunit_sum_vertices'],
        'first_error':result.get('first_error'),
        'report':str(out)},indent=2),flush=True)
    return result


if __name__=='__main__':
    if '--' not in sys.argv:
        raise SystemExit('Pass arguments after Blender --')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    argv=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    result=inspect(argv.plan,argv.out)
    if result['status'].startswith('FAIL_'):
        raise SystemExit(3)
