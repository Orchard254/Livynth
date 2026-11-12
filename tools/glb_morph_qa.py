#!/usr/bin/env python3
"""Read two EXISTING rigged GLBs and verify exported facial morph signal.

No Blender and no re-export required. A PASS proves named nonzero morph
deltas and distinct base coordinates, not realistic motion or image likeness.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from tools.measure_glb_topology import load_glb,read_accessor

REQUIRED_MOTION=(
    'eyeBlinkLeft','eyeBlinkRight','jawOpen',
    'mouthClose','mouthPucker','viseme_aa','viseme_PP',
)

class MorphSignalError(ValueError):
    pass


def delta_statistics(deltas,expected_count,*,threshold=1e-6):
    if not isinstance(expected_count,int) or expected_count<3 or len(deltas)!=expected_count:
        raise MorphSignalError('E_MORPH_VERTEX_COUNT')
    moved=0
    maxd=0.0
    for d in deltas:
        if len(d)!=3 or any(not math.isfinite(float(v)) for v in d):
            raise MorphSignalError('E_MORPH_NONFINITE')
        mag=math.sqrt(sum(float(v)**2 for v in d))
        if mag>threshold:
            moved+=1
            maxd=max(maxd,mag)
    return {'moved_vertices':moved,'max_delta_m':round(maxd,7),
            'source_units':'glTF_POSITION_DELTA_metres'}


def inspect_one(path):
    js,chunk=load_glb(path)
    skins=js.get('skins') or []
    if len(skins)!=1 or len(skins[0].get('joints',[]))!=163:
        raise MorphSignalError('E_MISSING_RIG_163')
    node_names=[n.get('name') for n in js.get('nodes',[])]
    joint_names=[node_names[i] for i in skins[0]['joints']]
    meshes=js.get('meshes') or []
    choices=[(i,m) for i,m in enumerate(meshes)
             if len((m.get('extras') or {}).get('targetNames') or [])==67]
    if len(choices)!=1:
        raise MorphSignalError('E_CHARACTER_WITH_67_TARGET_NAMES')
    index,mesh=choices[0]
    names=mesh['extras']['targetNames']
    if len(set(names))!=67:
        raise MorphSignalError('E_DUPLICATE_MORPH_NAMES')
    if len(mesh.get('primitives',[]))!=1:
        raise MorphSignalError('E_EXPECTED_ONE_CHARACTER_PRIMITIVE')
    prim=mesh['primitives'][0]
    targets=prim.get('targets',[])
    if len(targets)!=len(names) or 'POSITION' not in prim.get('attributes',{}):
        raise MorphSignalError('E_TARGET_LENGTH_MISMATCH')
    attached=[n for n in js.get('nodes',[])
              if n.get('mesh')==index and n.get('skin')==0]
    if len(attached)!=1:
        raise MorphSignalError('E_RIG_NOT_ATTACHED_TO_CHARACTER')
    attrs=prim['attributes']
    if not all(key in attrs for key in ('JOINTS_0','WEIGHTS_0','TEXCOORD_0')):
        raise MorphSignalError('E_MISSING_SKIN_OR_UV_ATTRIBUTES')
    position=read_accessor(js,chunk,attrs['POSITION'])
    if not position or any(len(p)!=3 or not all(math.isfinite(float(v)) for v in p)
                           for p in position):
        raise MorphSignalError('E_BAD_CHARACTER_POSITION')
    checks={}
    for name in REQUIRED_MOTION:
        if name not in names:
            raise MorphSignalError('E_REQUIRED_MORPH_MISSING_'+name)
        tgt=targets[names.index(name)]
        if 'POSITION' not in tgt:
            raise MorphSignalError('E_MORPH_DELTA_MISSING_'+name)
        check=delta_statistics(read_accessor(js,chunk,tgt['POSITION']),len(position))
        if check['moved_vertices']<20 or check['max_delta_m']<0.0001:
            raise MorphSignalError('E_INERT_REQUIRED_MORPH_'+name)
        if check['max_delta_m']>0.20:
            raise MorphSignalError('E_EXCESSIVE_MORPH_'+name)
        checks[name]=check
    return {'path':str(Path(path).resolve()),'base_positions':position,
            'morph_names':names,'joint_names':joint_names,
            'base_vertex_count':len(position),'required_motion_checks':checks}


def compare_existing_glbs(a,b):
    aa=inspect_one(a);bb=inspect_one(b)
    if aa['joint_names']!=bb['joint_names'] or aa['morph_names']!=bb['morph_names']:
        raise MorphSignalError('E_MORPH_OR_RIG_INTERFACE_MISMATCH')
    pa,pb=aa.pop('base_positions'),bb.pop('base_positions')
    if len(pa)!=len(pb):
        raise MorphSignalError('E_DIFFERENT_EXPORTED_VERTEX_LAYOUT')
    moved=0;maxd=0.0
    for left,right in zip(pa,pb):
        delta=math.sqrt(sum((left[k]-right[k])**2 for k in range(3)))
        if delta>0.0001:
            moved+=1
            maxd=max(maxd,delta)
    if moved<100 or maxd<0.001:
        raise MorphSignalError('E_NO_MEANINGFUL_IDENTITY_DIFFERENCE')
    return {'schema':'livynth.glb.morph-signal-qa.v1',
            'status':'PASS_NONZERO_EXPORTED_MORPH_SIGNAL_NOT_VISUAL_ANIMATION',
            'characters':[
                {k:v for k,v in entry.items() if k not in ('joint_names','morph_names')}
                for entry in (aa,bb)],
            'compatible_joint_names':True,'compatible_morph_names':True,
            'joint_count':len(aa['joint_names']),'morph_count':len(aa['morph_names']),
            'exported_vertex_count_each':len(pa),'different_export_vertices_gt_0_1_mm':moved,
            'max_export_vertex_delta_m':round(maxd,7),
            'actual_expression_visual_qa':'UNVERIFIED',
            'identity_likeness':'UNVERIFIED','full_lipsync':'UNVERIFIED'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,
                        help='Existing A/B folder containing demo_head_a.glb and demo_head_b.glb')
    parser.add_argument('--a',type=Path)
    parser.add_argument('--b',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    if args.folder and (args.a or args.b):
        parser.error('Choose --folder OR both --a and --b')
    if not args.folder and (args.a is None or args.b is None):
        parser.error('Provide --folder or --a and --b')
    a=args.folder/'demo_head_a.glb' if args.folder else args.a
    b=args.folder/'demo_head_b.glb' if args.folder else args.b
    target=args.out or (args.folder/'morph_signal_qa.json' if args.folder else None)
    try:
        result=compare_existing_glbs(a,b)
        if target:
            target=target.resolve()
            if target.exists(): raise FileExistsError('Refusing overwrite: '+str(target))
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
        return 0
    except (OSError,ValueError,IndexError,KeyError) as exc:
        print('LIVYNTH GLB MORPH QA FAILED: '+str(exc),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
