"""Numerical camera projection to head-control estimator, including negative tests."""
import unittest
import numpy as np
from character.head_shape import CONTROLS,displacement_field
from character.image_landmark_fit import (
    SCHEMA,camera_projection,LandmarkFitRejected,fit_from_image_landmarks)

class LandmarkFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(412)
        face=rng.uniform([-.09,-.20,1.47],[.09,-.09,1.70],size=(180,3))
        cls.points=np.vstack([face,np.array([[0,0,0],[.1,0,0],[-.1,0,0],[0,0,1.747]])])
        cls.truth=np.array([.58,-.51,.34,.7,-.6,.45])
        delta=sum((displacement_field(cls.points,{key:val})
                   for key,val in zip(CONTROLS,cls.truth)),np.zeros_like(cls.points))
        cls.target=cls.points+delta
        cls.ids=list(range(0,180,3))
        views=[]
        for name,yaw,tx in [('front',0,550),('left_profile',90,880),('right_profile',-90,200)]:
            cam=dict(yaw_deg=yaw,pitch_deg=0,roll_deg=0,scale=3300,tx=tx,ty=5700)
            basis,shift=camera_projection(**cam)
            landmarks=[dict(name=f'point{i}',vertex_ids=[idx],
                observed_xy_px=list((basis@cls.target[idx]+shift).astype(float)),sigma_px=4.0)
                for i,idx in enumerate(cls.ids)]
            views.append(dict(name=name,camera=cam,landmarks=landmarks))
        cls.observations=dict(schema=SCHEMA,camera_status='ESTIMATED_UNCALIBRATED',views=views)
    def test_camera_projection_finite_orthogonal(self):
        basis,shift=camera_projection(30,5,2,4000,540,6800)
        self.assertEqual(basis.shape,(2,3))
        self.assertAlmostEqual(float(np.dot(basis[0],basis[1])),0,places=6)
    def test_synthetic_multiview_coefficients_recovered(self):
        result=fit_from_image_landmarks(self.points,self.observations,regularization=.005)
        self.assertEqual(result['design_matrix_rank'],6)
        recovered=np.array([result['fitted_coefficients'][key] for key in CONTROLS])
        np.testing.assert_allclose(recovered,self.truth,atol=.07,rtol=0)
        self.assertLess(result['weighted_rmse_after'],result['weighted_rmse_before'])
        self.assertFalse(result['approved_identity'])
        self.assertEqual(result['status'],'DIAGNOSTIC_ONLY_UNAPPROVED')
    def test_does_not_modify_input(self):
        source=self.points.copy()
        fit_from_image_landmarks(self.points,self.observations)
        np.testing.assert_array_equal(source,self.points)
    def test_requires_three_named_views(self):
        bad=dict(self.observations,views=self.observations['views'][:2])
        with self.assertRaisesRegex(LandmarkFitRejected,'E_REQUIRED_THREE_VIEWS'):
            fit_from_image_landmarks(self.points,bad)
    def test_rejects_wrong_camera_claim(self):
        bad=dict(self.observations,camera_status='CALIBRATED')
        with self.assertRaisesRegex(LandmarkFitRejected,'E_OBSERVATION_SCHEMA'):
            fit_from_image_landmarks(self.points,bad)
    def test_rejects_invalid_vertex_id(self):
        views=[dict(v,camera=dict(v['camera']),landmarks=[dict(x) for x in v['landmarks']]) for v in self.observations['views']]
        views[0]['landmarks'][0]['vertex_ids']=[999999]
        with self.assertRaisesRegex(LandmarkFitRejected,'E_LANDMARK_INVALID'):
            fit_from_image_landmarks(self.points,dict(self.observations,views=views))
    def test_rejects_nan_camera(self):
        with self.assertRaisesRegex(LandmarkFitRejected,'E_CAMERA_RANGE'):
            camera_projection(0,0,0,float('nan'),0,0)
    def test_rejects_unknown_observation_schema(self):
        with self.assertRaisesRegex(LandmarkFitRejected,'E_OBSERVATION_SCHEMA'):
            fit_from_image_landmarks(self.points,dict(self.observations,schema='wrong'))
if __name__=='__main__':unittest.main()
