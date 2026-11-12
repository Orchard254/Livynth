"""IDENTITY-022: independent binary-mask jaw displacement QA, not visual QA."""
from __future__ import annotations

import math
import numpy as np

SCHEMA='livynth.mhclo.seamed-jaw-motion.v1'
PASS='PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA'


class SeamedJawMotionError(ValueError):
    pass


def audit_seamed_jaw_motion(neutral, jaw_open, lower_mask):
    before=np.asarray(neutral,dtype=np.float64)
    after=np.asarray(jaw_open,dtype=np.float64)
    mask=np.asarray(lower_mask)
    if (before.shape!=(3868,3) or after.shape!=before.shape or
            mask.shape!=(3868,) or
            not np.isfinite(before).all() or
            not np.isfinite(after).all() or
            not np.isin(mask,[0.0,1.0]).all() or
            int(np.count_nonzero(mask))!=1884):
        raise SeamedJawMotionError('E_ID022_SEAM_MOTION_INPUT')

    displacement=np.linalg.norm(after-before,axis=1)
    lower=displacement[mask==1]
    upper=displacement[mask==0]
    upper_max=float(upper.max())
    lower_median=float(np.median(lower))
    lower_max=float(lower.max())
    lower_moved=int(np.count_nonzero(lower>0.0001))
    upper_moved=int(np.count_nonzero(upper>0.0001))
    # No oral-contact or anatomically correct skinning inferred.
    status=(PASS if
            upper_max<=0.0002 and
            upper_moved<=2 and
            lower_moved>=1800 and
            0.001<=lower_median<=0.03 and
            lower_max<=0.035
            else 'FAIL_SEAMED_JAW_MOTION_NOT_VISUAL_QA')
    return {
        'schema':SCHEMA,
        'status':status,
        'source':'EVALUATED_WORLD_COORDINATES_NEUTRAL_VS_JAWOPEN',
        'lower_vertices':int(len(lower)),
        'upper_vertices':int(len(upper)),
        'lower_moved_gt_0_1_mm':lower_moved,
        'upper_moved_gt_0_1_mm':upper_moved,
        'lower_median_displacement_m':round(lower_median,9),
        'lower_max_displacement_m':round(lower_max,9),
        'upper_max_displacement_m':round(upper_max,9),
        'self_intersections':'NOT_TESTED',
        'mouth_contact':'NOT_TESTED',
        'teeth_appearance':'NOT_VISUALLY_APPROVED',
    }
