#!/usr/bin/env python3
"""Compare two Blender identity exports; checks shape difference and rig contract."""
import argparse
import json
from pathlib import Path

class IdentityComparisonError(ValueError):
    pass

def compare(a, b):
    for label, report in (('a',a),('b',b)):
        if not isinstance(report,dict) or not report.get('assertions_passed') or report.get('errors'):
            raise IdentityComparisonError('E_EXPORT_AUDIT_'+label)
        identity=report.get('identity_recipe') or {}
        if identity.get('source')!='manual_parameters' or not identity.get('sha256'):
            raise IdentityComparisonError('E_RECIPE_MISSING_'+label)
        geo=report.get('neutral_identity_geometry') or {}
        if not geo.get('positions_sha256') or geo.get('vertex_count',0)<4:
            raise IdentityComparisonError('E_GEOMETRY_MISSING_'+label)
        audit=report.get('glb_audit') or {}
        if (audit.get('joint_count'),audit.get('morph_targets_in_exported_glb'))!=(163,67) or not audit.get('skin_present'):
            raise IdentityComparisonError('E_RIG_MORPH_'+label)
    ga,gb=a['neutral_identity_geometry'],b['neutral_identity_geometry']
    if ga['vertex_count']!=gb['vertex_count']:
        raise IdentityComparisonError('E_DIFFERENT_TOPOLOGY')
    if ga['positions_sha256']==gb['positions_sha256']:
        raise IdentityComparisonError('E_IDENTICAL_GEOMETRY')
    if a['identity_recipe']['sha256']==b['identity_recipe']['sha256']:
        raise IdentityComparisonError('E_IDENTICAL_RECIPE')
    if a['identity_recipe']['character_id']==b['identity_recipe']['character_id']:
        raise IdentityComparisonError('E_IDENTICAL_CHARACTER_ID')
    return {'schema':'livynth.identity.compare.v1',
            'status':'PASS_DISTINCT_GEOMETRY_AND_RIG_CONTRACT_NOT_LIKENESS',
            'characters':[a['identity_recipe']['character_id'],b['identity_recipe']['character_id']],
            'native_vertices':ga['vertex_count'],'joints':163,'morph_targets':67,
            'identity_likeness':'UNVERIFIED','visible_animations':'UNVERIFIED'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a',type=Path,required=True)
    p.add_argument('--b',type=Path,required=True)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    try:
        result=compare(json.loads(args.a.read_text(encoding='utf-8')),
                       json.loads(args.b.read_text(encoding='utf-8')))
    except (OSError,ValueError) as exc:
        p.exit(2,str(exc)+'\n')
    text=json.dumps(result,indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(text,encoding='utf-8')
    print(text,end='')

if __name__=='__main__': main()
