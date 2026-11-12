#!/usr/bin/env python3
"""CPU-only IDENTITY-025 mouth anatomy fix QA."""
import math
import unittest
import numpy as np

from tools.mouth_anatomy import (
    SCHEMA,UPPER_SEAT_M,TONGUE_SEAT_M,
    validate_seat,plan_masked_translation,plan_translation,
    plan_cavity_faces,cavity_z_window)
from tools.mouth_anatomy import MouthAnatomyError


class SeatValidationTests(unittest.TestCase):
    def test_defaults_in_range(self):
        self.assertEqual(validate_seat(UPPER_SEAT_M,'U'),UPPER_SEAT_M)
        self.assertEqual(validate_seat(TONGUE_SEAT_M,'T'),TONGUE_SEAT_M)

    def test_zero_and_limit_accepted(self):
        self.assertEqual(validate_seat(0.0,'U'),0.0)
        self.assertEqual(validate_seat(0.045,'U'),0.045)

    def test_bool_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SEAT_VALUE_U'):
            validate_seat(True,'U')

    def test_nan_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SEAT_VALUE_U'):
            validate_seat(float('nan'),'U')

    def test_negative_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SEAT_RANGE_U'):
            validate_seat(-0.001,'U')

    def test_oversize_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SEAT_RANGE_U'):
            validate_seat(0.046,'U')

    def test_type_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SEAT_TYPE_U'):
            validate_seat('big','U')


class MaskedTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(9)
        n=3868
        cls.points=rng.uniform([-0.032,-0.16,1.52],[0.032,-0.06,1.59],size=(n,3))
        cls.mask=np.zeros(n)
        cls.mask[:1884]=1.0  # lower
        cls.mask[1884:]=0.0  # upper

    def test_upper_only_moves_down(self):
        moved,audit=plan_masked_translation(
            self.points,self.mask,dz=-0.022,select_value=0,label='UPPER_TEETH')
        upper=self.mask==0
        lower=self.mask==1
        np.testing.assert_allclose(moved[upper]-self.points[upper],
                                   np.tile([0,0,-0.022],(int(upper.sum()),1)),
                                   atol=1e-12)
        np.testing.assert_allclose(moved[lower],self.points[lower],atol=1e-12)
        self.assertEqual(audit['selected_vertices'],int(upper.sum()))
        self.assertEqual(audit['stationary_vertices'],int(lower.sum()))
        self.assertAlmostEqual(audit['translation_magnitude_m'],0.022)
        self.assertEqual(audit['schema'],SCHEMA)
        self.assertEqual(moved.shape,self.points.shape)

    def test_input_not_mutated(self):
        before=self.points.copy()
        plan_masked_translation(self.points,self.mask,dz=-0.02,select_value=0)
        np.testing.assert_array_equal(self.points,before)

    def test_bad_mask_values_rejected(self):
        bad=self.mask.copy(); bad[0]=0.5
        with self.assertRaisesRegex(MouthAnatomyError,'E_MASK_VALUES_'):
            plan_masked_translation(self.points,bad,dz=-0.02)

    def test_wrong_mask_shape_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_MASK_SHAPE_'):
            plan_masked_translation(self.points,self.mask[:-1],dz=-0.02)

    def test_too_few_selected_rejected(self):
        m=np.ones(3868)
        m[:5]=0  # only 5 "upper" — below threshold
        with self.assertRaisesRegex(MouthAnatomyError,'E_MASKED_SELECTION_TOO_SMALL_'):
            plan_masked_translation(self.points,m,dz=-0.02,select_value=0)

    def test_oversize_shift_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_MASKED_SHIFT_'):
            plan_masked_translation(self.points,self.mask,dz=-0.05,select_value=0)

    def test_nonfinite_rejected(self):
        bad=self.points.copy(); bad[3,2]=float('nan')
        with self.assertRaisesRegex(MouthAnatomyError,'E_POINTS_'):
            plan_masked_translation(bad,self.mask,dz=-0.02)


class GlobalTranslationTests(unittest.TestCase):
    def test_all_vertices_move(self):
        rng=np.random.default_rng(3)
        pts=rng.uniform([-0.02,-0.14,1.53],[0.02,-0.05,1.58],size=(226,3))
        moved,audit=plan_translation(pts,dz=-0.016,label='TONGUE')
        np.testing.assert_allclose(moved[:,2]-pts[:,2],-0.016,atol=1e-12)
        self.assertEqual(audit['selected_vertices'],226)
        self.assertEqual(audit['stationary_vertices'],0)

    def test_oversize_rejected(self):
        pts=np.zeros((226,3))+ [0,-0.1,1.55]
        with self.assertRaisesRegex(MouthAnatomyError,'E_TRANSLATION_'):
            plan_translation(pts,dz=-0.05)


class CavityFaceTests(unittest.TestCase):
    def _faces(self):
        centers=np.array([
            [0.0, -0.055, 1.50],   # mouth back wall, centre: deep, faces camera
            [0.03, -0.060, 1.55],  # inner cheek, faces centre: deep
            [0.0, -0.166, 1.50],   # outer lip skin: shallow
            [0.08, -0.055, 1.50],  # outside opening: excluded
            [0.0, -0.055, 1.30],   # below window
            [0.0, -0.055, 1.70],   # above window
            [0.0, -0.139, 1.52],   # lip corner skin: shallow
            [-0.04, -0.08, 1.52],  # left wall, faces centre: keep
            [-0.04, -0.08, 1.52],  # left cheek skin, faces outward: reject
            [0.04, -0.08, 1.52],   # right cheek skin, faces outward: reject
        ])
        normals=np.array([
            [0.0, -0.99, 0.1],
            [-0.8, -0.5, 0.3],
            [0.0, -0.99, 0.1],
            [0.0, -0.99, 0.1],
            [0.0, -0.99, 0.1],
            [0.0, -0.99, 0.1],
            [0.2, -0.9, 0.2],
            [0.8, -0.5, 0.3],
            [-0.8, -0.5, -0.3],
            [0.8, -0.5, -0.3],
        ])
        return centers,normals

    def test_selects_deep_mouth_band(self):
        centers,normals=self._faces()
        sel=plan_cavity_faces(centers,normals,half_width=0.046,
                              z_min=1.32,z_max=1.62)
        self.assertEqual(sel,[0,1,7])

    def test_outward_side_faces_rejected(self):
        centers,normals=self._faces()
        centers=centers.copy(); normals=normals.copy()
        # keep only rows 0, 7, 8, 9 and drop the centre-facing left wall
        sub_c=np.vstack([centers[0],centers[7],centers[8],centers[9]])
        sub_n=np.vstack([normals[0],normals[7],normals[8],normals[9]])
        sel=plan_cavity_faces(sub_c,sub_n,half_width=0.046,
                              z_min=1.32,z_max=1.62)
        self.assertEqual(sel,[0,1])

    def test_depth_threshold_excludes_shallow_skin(self):
        centers,normals=self._faces()
        centers=centers.copy(); normals=normals.copy()
        centers[1,1]=-0.061
        sel=plan_cavity_faces(centers,normals,half_width=0.046,
                              z_min=1.32,z_max=1.62,min_depth_y=-0.06)
        self.assertEqual(sel,[0])

    def test_shape_mismatch_rejected(self):
        centers,normals=self._faces()
        with self.assertRaisesRegex(MouthAnatomyError,'E_POINTS_'):
            plan_cavity_faces(centers[:,:2],normals)

    def test_bad_window_rejected(self):
        centers,normals=self._faces()
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_Z_WINDOW'):
            plan_cavity_faces(centers,normals,z_min=1.62,z_max=1.32)

    def test_bad_half_width_rejected(self):
        centers,normals=self._faces()
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_HALF_WIDTH'):
            plan_cavity_faces(centers,normals,half_width=0.0)

    def test_nan_depth_rejected(self):
        centers,normals=self._faces()
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_DEPTH'):
            plan_cavity_faces(centers,normals,min_depth_y=float('nan'))

    def test_bad_side_threshold_rejected(self):
        centers,normals=self._faces()
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_SIDE_THRESHOLD'):
            plan_cavity_faces(centers,normals,side_normal_threshold=1.0)


class CavityWindowTests(unittest.TestCase):
    def test_window_inside_body(self):
        z_min,z_max=cavity_z_window(1.747,1.747)
        self.assertLess(1.0,z_min)
        self.assertLess(z_min,z_max)
        self.assertLess(z_max,1.747)

    def test_default_fractions_target_mouth_band(self):
        z_min,z_max=cavity_z_window(1.747,1.747,
                                    z_min_fraction=0.870,
                                    z_max_fraction=0.915)
        self.assertGreater(z_min,1.48)
        self.assertLess(z_min,1.55)
        self.assertGreater(z_max,1.58)
        self.assertLess(z_max,1.65)

    def test_bad_height_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_Z_WINDOW_HEIGHT'):
            cavity_z_window(1.0,3.0)

    def test_inverted_fractions_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_Z_WINDOW_FRACTION'):
            cavity_z_window(1.747,1.747,z_min_fraction=0.9,z_max_fraction=0.8)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_Z_WINDOW_INPUT'):
            cavity_z_window(float('nan'),1.747)

    def test_nan_free(self):
        z_min,z_max=cavity_z_window(1.747,1.747)
        self.assertTrue(math.isfinite(z_min) and math.isfinite(z_max))


if __name__=='__main__':
    unittest.main()
