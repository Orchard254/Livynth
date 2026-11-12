"""Uncalibrated image-landmark -> parametric head-shape *diagnostic*.

Requires measured 2D image points plus native vertex correspondences and explicit
camera estimates. Never exports an identity recipe or certifies image likeness.
The face controls are linear in coefficients, so a bounded weighted least-squares
fit can be audited independently of camera estimation.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import lsq_linear
from character.head_shape import CONTROLS, displacement_field, InvalidHeadShape, apply_head_shape

SCHEMA='livynth.image-landmark-fit.v1'

class LandmarkFitRejected(ValueError):
    pass

def camera_projection(yaw_deg,pitch_deg,roll_deg,scale,tx,ty):
    parameters=np.asarray([yaw_deg,pitch_deg,roll_deg,scale,tx,ty],dtype=float)
    if not np.isfinite(parameters).all() or not -180 <= yaw_deg <= 180 or not -30 <= pitch_deg <= 30 or not -15 <= roll_deg <= 15 or not 100 <= scale <= 20000:
        raise LandmarkFitRejected('E_CAMERA_RANGE')
    t,p,r=np.deg2rad([yaw_deg,pitch_deg,roll_deg])
    cam=np.array([np.sin(t),-np.cos(t),0.]);right=np.array([np.cos(t),np.sin(t),0.]);up=np.array([0.,0.,1.])
    up2=up*np.cos(p)-cam*np.sin(p)
    right2=right*np.cos(r)+up2*np.sin(r)
    up3=-right*np.sin(r)+up2*np.cos(r)
    # Image x grows right; image y grows down.
    return np.stack([scale*right2, -scale*up3]),np.array([tx,ty])

def _prepare(points,observations):
    p=np.asarray(points,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)<4 or not np.isfinite(p).all():
        raise LandmarkFitRejected('E_MESH')
    if not isinstance(observations,dict) or observations.get('schema')!=SCHEMA or observations.get('camera_status')!='ESTIMATED_UNCALIBRATED':
        raise LandmarkFitRejected('E_OBSERVATION_SCHEMA')
    views=observations.get('views')
    if not isinstance(views,list) or len(views)<3:
        raise LandmarkFitRejected('E_REQUIRED_THREE_VIEWS')
    valid=[];seen=set()
    for view in views:
        if (not isinstance(view,dict) or set(view)!={'name','camera','landmarks'} or
            not isinstance(view['name'],str) or view['name'] in seen):
            raise LandmarkFitRejected('E_VIEW_SCHEMA')
        name=view['name'];seen.add(name)
        cam=view['camera']
        if set(cam)!={'yaw_deg','pitch_deg','roll_deg','scale','tx','ty'}:
            raise LandmarkFitRejected('E_CAMERA_SCHEMA')
        basis,shift=camera_projection(**cam)
        landmarks=view['landmarks']
        if not isinstance(landmarks,list) or len(landmarks)<3:
            raise LandmarkFitRejected('E_LANDMARK_COUNT')
        out=[]
        for mark in landmarks:
            if not isinstance(mark,dict) or set(mark)!={'name','vertex_ids','observed_xy_px','sigma_px'}:
                raise LandmarkFitRejected('E_LANDMARK_SCHEMA')
            ids=mark['vertex_ids'];xy=mark['observed_xy_px'];sig=mark['sigma_px']
            if (not isinstance(ids,list) or not ids or any(type(i)!=int or i<0 or i>=len(p) for i in ids)
                or not isinstance(xy,list) or len(xy)!=2 or not np.isfinite(np.asarray(xy,dtype=float)).all()
                or isinstance(sig,bool) or not isinstance(sig,(int,float)) or not 1<=sig<=100):
                raise LandmarkFitRejected('E_LANDMARK_INVALID')
            out.append((mark['name'],ids,np.asarray(xy,dtype=float),float(sig)))
        valid.append((name,basis,shift,out))
    if not {'front','left_profile','right_profile'}.issubset(seen):
        raise LandmarkFitRejected('E_REQUIRES_FRONT_BOTH_PROFILES')
    return p,valid

def fit_from_image_landmarks(vertices,observations,quads=None,*,regularization=0.35):
    """Conservative *fixed-camera* bounded fit; never mutates caller's vertices.

    Camera errors, missing/incorrect mesh landmark semantics and AI-image drift
    dominate in real data. A low reprojection error does not establish identity.
    """
    p,views=_prepare(vertices,observations)
    if not isinstance(regularization,(int,float)) or not 0<regularization<=3:
        raise LandmarkFitRejected('E_REGULARIZATION')
    effects=[displacement_field(p,{key:1.0}) for key in CONTROLS]
    rows=[];target=[];view_rows=[]
    for name,projection,shift,marks in views:
        offset_start=len(rows)
        for label,ids,xy,sigma in marks:
            original=p[ids].mean(axis=0)
            projected=projection@original+shift
            columns=np.stack([projection@effect[ids].mean(axis=0) for effect in effects],axis=-1)
            for k in range(2):
                rows.append(columns[k]/sigma)
                target.append((xy[k]-projected[k])/sigma)
        view_rows.append((name,slice(offset_start,len(rows))))
    matrix=np.asarray(rows);obs=np.asarray(target)
    singular=np.linalg.svd(matrix,compute_uv=False)
    rank=int(np.linalg.matrix_rank(matrix, tol=max(singular[0]*1e-6,1e-9)))
    if rank<len(CONTROLS):
        return {'status':'UNIDENTIFIABLE_GEOMETRY_CONTROLS','rank':rank,
                'expected_rank':len(CONTROLS),'source':'uncalibrated_landmarks',
                'approved_identity':False}
    reg=np.sqrt(regularization)*np.eye(len(CONTROLS))
    solved=lsq_linear(np.vstack([matrix,reg]),np.r_[obs,np.zeros(len(CONTROLS))],
                      bounds=(-np.ones(len(CONTROLS)),np.ones(len(CONTROLS))),
                      max_iter=500,tol=1e-10)
    raw_coeffs=np.asarray(solved.x)
    coeffs=raw_coeffs.copy()
    safe_scale=None
    shape_audit=None
    if quads is not None:
        # A good pixel score is invalid if it folds the underlying anatomy.
        # Use deterministic trust-region backoff, record actual strength.
        last_error=None
        for scale in (1.0,.95,.9,.85,.8,.75,.7,.65,.6,.5,.4,.3,.2,.1):
            trial=raw_coeffs*scale
            try:
                _,shape_audit=apply_head_shape(p,quads,dict(zip(CONTROLS,trial)))
                coeffs=trial
                safe_scale=scale
                break
            except InvalidHeadShape as exc:
                last_error=str(exc)
        if safe_scale is None:
            return {'schema':'livynth.image-landmark-proposal.v1',
                    'status':'REJECTED_UNSAFE_GEOMETRY',
                    'reason':last_error or 'NO_VALID_TRUST_REGION',
                    'approved_identity':False}
    original_err=matrix@np.zeros_like(coeffs)-obs
    fitted_err=matrix@coeffs-obs
    def perview(errors):
        return {name:round(float(np.sqrt(np.mean(np.square(errors[row])))),4)
                for name,row in view_rows}
    prev=perview(original_err); nxt=perview(fitted_err)
    worse=[name for name in prev if nxt[name]>prev[name]+0.05]
    return {'schema':'livynth.image-landmark-proposal.v1',
            'status':('REJECTED_PROFILE_REGRESSION' if any(
                v in ('left_profile','right_profile') for v in worse)
                else 'DIAGNOSTIC_ONLY_UNAPPROVED'),
            'reason':'UNREGISTERED_AI_GENERATED_IMAGES_AND_NO_HELDOUT_FIVE_VIEW_GATE',
            'source':'uncalibrated_landmarks',
            'approved_identity':False,
            'camera_status':'ESTIMATED_UNCALIBRATED',
            'raw_coefficients':{k:round(float(v),6) for k,v in zip(CONTROLS,raw_coeffs)},
            'fitted_coefficients':{k:round(float(v),6) for k,v in zip(CONTROLS,coeffs)},
            'geometry_backoff_scale':safe_scale,
            'geometry_audit':shape_audit,
            'geometry_validation':('PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS'
                                    if shape_audit else 'UNVERIFIED_NO_QUADS'),
            'optimizer_success':bool(solved.success),
            'design_matrix_rank':rank,
            'design_condition_number':round(float(singular[0]/max(singular[-1],1e-12)),3),
            'weighted_rmse_before':round(float(np.sqrt(np.mean(original_err**2))),4),
            'weighted_rmse_after':round(float(np.sqrt(np.mean(fitted_err**2))),4),
            'view_weighted_rmse_before':prev,
            'view_weighted_rmse_after':nxt,
            'views_worsened':worse,
            'heldout_views_verified':0}
