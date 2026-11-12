"""Quantitative diagnostic: do native teeth/tongue follow body facial morphs?

Evaluates real deformed world coordinates, not material pixels or whether
armature modifiers exist. This module does not apply jaw retargeting.
"""
from __future__ import annotations

import math
import numpy as np

SCHEMA="livynth.anatomy.oral-motion-audit.v1"
REQUIRED=("body","teeth","tongue")
POSES=("jaw_open","viseme_aa")


class OralMotionError(ValueError):
    pass


def displacement_stats(neutral,posed,*,threshold_m=0.0001):
    """World-space one-to-one displacement metrics, retaining vertex order."""
    before=np.asarray(neutral,dtype=np.float64)
    after=np.asarray(posed,dtype=np.float64)
    if (before.ndim!=2 or before.shape[1]!=3 or len(before)<4
        or before.shape!=after.shape or not np.isfinite(before).all()
        or not np.isfinite(after).all() or not math.isfinite(threshold_m)
        or not 0<threshold_m<=0.005):
        raise OralMotionError("E_MOTION_ARRAY_INVALID")
    distances=np.linalg.norm(after-before,axis=1)
    return {
        "vertex_count":len(before),
        "moved_vertices_gt_0_1_mm":int(np.count_nonzero(distances>threshold_m)),
        "max_displacement_m":round(float(np.max(distances)),9),
        "mean_displacement_m":round(float(np.mean(distances)),9),
        "p95_displacement_m":round(float(np.percentile(distances,95)),9),
    }


def classify_motion_stats(stats):
    """Recompute diagnostic status from measured metrics, including report QA."""
    if not isinstance(stats,dict) or set(stats)!=set(REQUIRED):
        raise OralMotionError("E_MOTION_METRICS_SET")
    for name in REQUIRED:
        record=stats[name]
        if not isinstance(record,dict):
            raise OralMotionError("E_MOTION_METRICS_ENTRY_"+name)
        n=record.get("vertex_count")
        moved=record.get("moved_vertices_gt_0_1_mm")
        maxd=record.get("max_displacement_m")
        if (type(n)!=int or n<4 or type(moved)!=int or not 0<=moved<=n
            or isinstance(maxd,bool) or not isinstance(maxd,(int,float))
            or not math.isfinite(maxd) or maxd<0 or maxd>5):
            raise OralMotionError("E_MOTION_METRICS_INVALID_"+name)
        if (moved==0 and maxd>0.000101) or (moved>0 and maxd<0.000099):
            raise OralMotionError("E_MOTION_METRICS_INCONSISTENT_"+name)
    body=stats["body"]
    if body["moved_vertices_gt_0_1_mm"]<20 or body["max_displacement_m"]<0.001:
        return "FAIL_BODY_FACIAL_MORPH_INERT"
    stalled=[name for name in ("teeth","tongue") if
             stats[name]["moved_vertices_gt_0_1_mm"]==0 or
             stats[name]["max_displacement_m"]<0.0001]
    if len(stalled)==2:
        return "FAIL_ORAL_ASSETS_STATIC_WHILE_BODY_MORPHS"
    if stalled:
        return "FAIL_PARTIAL_ORAL_MOTION_SIGNAL"
    return "ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED"


def diagnose_oral_motion(neutral_by_object,posed_by_object,*,pose):
    """Report BODY motion vs teeth/tongue follow signal; no visual approval.

    Upper teeth can legitimately be stationary, so whole-teeth movement is
    only a signal. A static entire tooth mesh and tongue despite jawOpen is
    strong evidence that body shape keys have not driven the jaw-bound assets.
    """
    if pose not in POSES:
        raise OralMotionError("E_MOTION_POSE")
    if (not isinstance(neutral_by_object,dict)
        or not isinstance(posed_by_object,dict)
        or set(neutral_by_object)!=set(REQUIRED)
        or set(posed_by_object)!=set(REQUIRED)):
        raise OralMotionError("E_MOTION_OBJECT_SET")
    stats={name:displacement_stats(neutral_by_object[name],posed_by_object[name])
           for name in REQUIRED}
    status=classify_motion_stats(stats)
    return {
        "schema":SCHEMA,
        "pose":pose,
        "status":status,
        "measurement":"EVALUATED_MESH_WORLD_SPACE_AT_SAME_FRAME",
        "stats":stats,
        "bone_to_morph_retarget_verified":False,
        "oral_contact_and_collision":"NOT_TESTED",
        "natural_speech_motion":"NOT_TESTED",
    }
