"""Read-only source OBJ + MHCLO diagnostics before costly Blender anatomy render.

Never modifies installed assets or GLBs. Inspect actual source-reference
weights and topology instead of assuming sanitized synthetic test input.
"""
from __future__ import annotations
import math
from pathlib import Path

SCHEMA='livynth.mhclo.dental-preflight.v1'

class DentalPreflightError(ValueError):
    pass


def load_obj_topology(filename, *, max_vertices=100000, max_faces=100000):
    path=Path(filename)
    if not path.is_file() or path.is_symlink():
        raise DentalPreflightError('E_OBJ_MISSING_OR_SYMLINK')
    count=0
    faces=[]
    with path.open('r',encoding='utf-8',errors='strict') as stream:
        for line in stream:
            stripped=line.strip()
            if stripped.startswith('v '):
                count+=1
                if count>max_vertices:
                    raise DentalPreflightError('E_OBJ_VERTEX_LIMIT')
            elif stripped.startswith('f '):
                tokens=stripped.split()[1:]
                if len(tokens)<3:
                    raise DentalPreflightError('E_OBJ_FACE_SIZE')
                indices=[]
                for token in tokens:
                    first=token.split('/')[0]
                    try:
                        vertex=int(first)
                    except ValueError as exc:
                        raise DentalPreflightError('E_OBJ_FACE_INDEX') from exc
                    if vertex==0:
                        raise DentalPreflightError('E_OBJ_FACE_INDEX')
                    # OBJ negative indices are relative to vertex count at
                    # the face line; positive indices are 1-based.
                    index=(vertex-1) if vertex>0 else (count+vertex)
                    if not 0<=index<count:
                        raise DentalPreflightError('E_OBJ_FACE_INDEX')
                    indices.append(index)
                if len(set(indices))<3:
                    raise DentalPreflightError('E_OBJ_DEGENERATE_FACE')
                faces.append(tuple(indices))
                if len(faces)>max_faces:
                    raise DentalPreflightError('E_OBJ_FACE_LIMIT')
    if not faces or count<32:
        raise DentalPreflightError('E_OBJ_EMPTY')
    return count,faces


def inspect_mhclo_weights(mappings, *, sample_limit=5):
    if not isinstance(mappings,dict):
        raise DentalPreflightError('E_MHCLO_MAPPING_TYPE')
    negative=nonunit=zero=bad=0
    min_sum=float('inf')
    max_sum=float('-inf')
    examples=[]
    for i,entry in sorted(mappings.items()):
        try:
            coeff=entry['weights']
            refs=entry['verts']
            if len(coeff)!=3 or len(refs)!=3:
                raise ValueError('wrong tuple length')
            values=[float(x) for x in coeff]
            if not all(math.isfinite(w) for w in values):
                raise ValueError('nonfinite')
            weight_sum=sum(values)
            min_sum=min(weight_sum,min_sum)
            max_sum=max(weight_sum,max_sum)
            signed=any(w< -1e-8 for w in values)
            different=abs(weight_sum-1.0)>1e-4
            invalid=sum(abs(w) for w in values)<1e-10
            negative+=int(signed)
            nonunit+=int(different)
            zero+=int(invalid)
            if (signed or different or invalid) and len(examples)<sample_limit:
                examples.append({'index':i,'refs':[int(x) for x in refs],
                                 'weights':[round(x,9) for x in values],
                                 'raw_sum':round(weight_sum,9),
                                 'reason':('ZERO' if invalid else
                                           'SIGNED' if signed else 'NON_UNIT')})
        except (ValueError,TypeError,IndexError,KeyError):
            bad+=1
            if len(examples)<sample_limit:
                examples.append({'index':i,'reason':'UNREADABLE_WEIGHT_TRIPLET'})
    return {
        'schema':SCHEMA,
        'mapped_vertices':len(mappings),
        'signed_weight_vertices':negative,
        'nonunit_sum_vertices':nonunit,
        'zero_abs_weight_vertices':zero,
        'invalid_weight_triplet_vertices':bad,
        'min_raw_coefficient_sum':None if min_sum==float('inf') else round(min_sum,9),
        'max_raw_coefficient_sum':None if max_sum==float('-inf') else round(max_sum,9),
        'samples':examples,
        'source_assets_modified':False,
        'user_files_included':False,
    }
