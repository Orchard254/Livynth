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


def diagnose_mixed_jaw_faces(mappings, faces, *, sample_limit=8):
    """Describe cross-jaw polygon boundaries; NEVER override strict classification.

    Called only after the production classifier rejects a mixed-jaw face.
    Vertex ownership follows the identical pinned helper ranges and 99.9%
    absolute-weight contribution threshold. Output is evidence, not approval.
    """
    from character.mhclo_dentition import LOWER_HELPER, UPPER_HELPER

    if (not isinstance(mappings, dict) or not isinstance(faces, (tuple, list))
            or type(sample_limit) is not int or not 1 <= sample_limit <= 32):
        raise DentalPreflightError('E_MIXED_FACE_DIAGNOSTIC_INPUT')

    ownership = {}
    for index, entry in mappings.items():
        try:
            refs = entry['verts']
            coeff = entry['weights']
            if len(refs) != 3 or len(coeff) != 3:
                raise ValueError('wrong source tuple')
            values = [float(w) for w in coeff]
            total = sum(abs(w) for w in values)
            if not all(math.isfinite(w) for w in values) or not 1e-10 < total <= 100:
                raise ValueError('invalid weights')
            lower = sum(abs(w) for ref, w in zip(refs, values)
                        if LOWER_HELPER[0] <= ref <= LOWER_HELPER[1]) / total
            upper = sum(abs(w) for ref, w in zip(refs, values)
                        if UPPER_HELPER[0] <= ref <= UPPER_HELPER[1]) / total
            if lower >= .999 and upper <= .001:
                ownership[index] = 'lower'
            elif upper >= .999 and lower <= .001:
                ownership[index] = 'upper'
            else:
                raise ValueError('ambiguous source references')
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise DentalPreflightError(
                'E_MIXED_FACE_DIAGNOSTIC_JAW_VERTEX: ' + str(index)) from exc

    mixed_count = 0
    cross_jaw_vertices = set()
    samples = []
    for face_index, face in enumerate(faces):
        try:
            labels = [ownership[index] for index in face]
        except (KeyError, TypeError) as exc:
            raise DentalPreflightError('E_MIXED_FACE_DIAGNOSTIC_FACE_INDEX') from exc
        if len(set(labels)) <= 1:
            continue
        mixed_count += 1
        cross_jaw_vertices.update(face)
        if len(samples) < sample_limit:
            samples.append({
                'face_index': face_index,
                'vertices': [{
                    'index': index,
                    'jaw': label,
                    'refs': list(mappings[index]['verts']),
                    'weights': [float(w) for w in mappings[index]['weights']],
                } for index, label in zip(face, labels)],
            })
    return {
        'mixed_face_count': mixed_count,
        'mixed_face_unique_vertices': len(cross_jaw_vertices),
        'face_count': len(faces),
        'sample_limit': sample_limit,
        'samples': samples,
        'production_classifier_bypassed': False,
        'visual_quality': 'NOT_TESTED',
    }
