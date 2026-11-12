"""Map MPFB teeth asset vertices to original HM08 upper/lower dental helpers.

Source: official MPFB hm08_config.json groups_by_range (inclusive IDs).
No guessed Z-height split or private geometry is necessary. An ambiguous
MHCLO mapping or cross-jaw face MUST fail instead of stretching teeth.
"""
from __future__ import annotations

import hashlib
import numpy as np

LOWER_HELPER=(14992,15059)
UPPER_HELPER=(15060,15127)
SOURCE_VERTEX_COUNT=19158
SCHEMA='livynth.mhclo-dentition.v1'


class DentitionMappingError(ValueError):
    pass


def classify_dentition_mhclo(vertex_count,mappings,faces,*,source_vertex_count=SOURCE_VERTEX_COUNT):
    """Return 0/1 lower-jaw mask plus an auditable source mapping report.

    mappings is Mhclo.load(...).verts (not an image/shape-based guess).
    Pure code, independent of Blender; face boundaries prohibit stretching.
    """
    if (type(vertex_count)!=int or vertex_count<32 or vertex_count>100000 or
        type(source_vertex_count)!=int or source_vertex_count!=SOURCE_VERTEX_COUNT or
        not isinstance(mappings,dict) or len(mappings)!=vertex_count or
        not isinstance(faces,(list,tuple)) or not faces):
        raise DentitionMappingError('E_MHCLO_INPUT_CONTRACT')
    lower=np.empty(vertex_count,dtype=np.uint8)
    for i in range(vertex_count):
        match=mappings.get(i)
        if not isinstance(match,dict):
            raise DentitionMappingError('E_MHCLO_MAPPING_GAP')
        refs=match.get('verts')
        coeff=match.get('weights')
        if (not isinstance(refs,(tuple,list)) or len(refs)!=3 or
            not isinstance(coeff,(tuple,list)) or len(coeff)!=3 or
            any(type(v)!=int or not 0<=v<source_vertex_count for v in refs)):
            raise DentitionMappingError('E_MHCLO_BAD_REFERENCE')
        try:
            weights=np.asarray(coeff,dtype=float)
        except (TypeError,ValueError) as exc:
            raise DentitionMappingError('E_MHCLO_BAD_WEIGHTS') from exc
        if (not np.isfinite(weights).all() or np.min(weights)<-1e-8 or
            abs(float(weights.sum())-1.0)>1e-4):
            raise DentitionMappingError('E_MHCLO_BAD_WEIGHTS')
        lo=sum(float(w) for j,w in zip(refs,weights)
               if LOWER_HELPER[0]<=j<=LOWER_HELPER[1])
        hi=sum(float(w) for j,w in zip(refs,weights)
               if UPPER_HELPER[0]<=j<=UPPER_HELPER[1])
        if lo>=0.999 and hi<=0.001:
            lower[i]=1
        elif hi>=0.999 and lo<=0.001:
            lower[i]=0
        else:
            raise DentitionMappingError('E_MHCLO_AMBIGUOUS_JAW_VERTEX')
    count_lower=int(np.count_nonzero(lower))
    count_upper=vertex_count-count_lower
    if min(count_lower,count_upper)<max(20,vertex_count//10):
        raise DentitionMappingError('E_MHCLO_UNBALANCED_JAWS')
    for face in faces:
        if (not isinstance(face,(tuple,list)) or len(face)<3 or
            any(type(v)!=int or v<0 or v>=vertex_count for v in face)):
            raise DentitionMappingError('E_MHCLO_FACE_INVALID')
        if any(lower[v]!=lower[face[0]] for v in face[1:]):
            raise DentitionMappingError('E_MHCLO_MIXED_UPPER_LOWER_FACE')
    return lower.astype(np.float64), {
        'schema':SCHEMA,
        'status':'PASS_HELPER_GROUP_JAW_MAPPING_NOT_VISUAL_APPROVAL',
        'source':'PINNED_MHCLO_BASEMESH_VERTEX_REFERENCES',
        'lower_helper_range_inclusive':list(LOWER_HELPER),
        'upper_helper_range_inclusive':list(UPPER_HELPER),
        'source_vertex_count':source_vertex_count,
        'total_teeth_vertices':vertex_count,
        'lower_teeth_vertices':count_lower,
        'upper_teeth_vertices':count_upper,
        'face_count':len(faces),
        'mixed_jaw_faces':0,
        'lower_mask_sha256':hashlib.sha256(lower.tobytes()).hexdigest(),
        'mesh_topology_modified':False,
        'anatomical_contact':'PENDING_VISUAL_REVIEW',
    }
