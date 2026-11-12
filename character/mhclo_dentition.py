"""Map MPFB teeth asset vertices to original HM08 upper/lower dental helpers.

Source: official MPFB hm08_config.json groups_by_range (inclusive IDs).
No guessed Z-height split or private geometry is necessary. An ambiguous
MHCLO mapping or cross-jaw face MUST fail instead of stretching teeth.
"""
from __future__ import annotations

import hashlib
import math
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
    signed_count=0
    nonunit_sum_count=0
    min_weight_sum=float('inf')
    max_weight_sum=float('-inf')
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
        if not np.isfinite(weights).all():
            raise DentitionMappingError('E_MHCLO_BAD_WEIGHTS: nonfinite at '+str(i))
        # MHCLO interpolations can contain extrapolation/signed coefficients;
        # their sum/positivity is NOT a jaw-affiliation requirement. Never
        # renormalize the actual fitting values used by MPFB.
        absolute=np.abs(weights)
        total=float(absolute.sum())
        if not math.isfinite(total) or total<=1e-10 or total>100:
            raise DentitionMappingError('E_MHCLO_BAD_WEIGHTS: degenerate at '+str(i))
        weight_sum=float(weights.sum())
        min_weight_sum=min(min_weight_sum,weight_sum)
        max_weight_sum=max(max_weight_sum,weight_sum)
        signed_count+=int(np.any(weights<-1e-8))
        nonunit_sum_count+=int(abs(weight_sum-1.0)>1e-4)
        # Absolute contribution mass is used ONLY for attribution, not for
        # fitting geometry. A negatively weighted source reference remains
        # evidence that the vertex depends on that jaw, not negative mass.
        lower_mass=sum(float(abs(w)) for j,w in zip(refs,weights)
                       if LOWER_HELPER[0]<=j<=LOWER_HELPER[1])
        upper_mass=sum(float(abs(w)) for j,w in zip(refs,weights)
                       if UPPER_HELPER[0]<=j<=UPPER_HELPER[1])
        if lower_mass/total>=0.999 and upper_mass/total<=0.001:
            lower[i]=1
        elif upper_mass/total>=0.999 and lower_mass/total<=0.001:
            lower[i]=0
        else:
            raise DentitionMappingError(
                'E_MHCLO_AMBIGUOUS_JAW_VERTEX: index='+str(i)+
                ' lower_mass_fraction='+str(round(lower_mass/total,6))+
                ' upper_mass_fraction='+str(round(upper_mass/total,6)))
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
        'signed_coefficient_vertices':signed_count,
        'nonunit_coefficient_sum_vertices':nonunit_sum_count,
        'minimum_raw_coefficient_sum':round(min_weight_sum,6),
        'maximum_raw_coefficient_sum':round(max_weight_sum,6),
        'jaw_classification_uses':'ABSOLUTE_REFERENCE_CONTRIBUTION_NOT_WEIGHT_NORMALIZATION',
        'lower_mask_sha256':hashlib.sha256(lower.tobytes()).hexdigest(),
        'mesh_topology_modified':False,
        'anatomical_contact':'PENDING_VISUAL_REVIEW',
    }
