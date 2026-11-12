#!/usr/bin/env python3
"""CPU-only IDENTITY-025 mouth anatomy fix QA."""
import math
import unittest
import numpy as np

from tools.mouth_anatomy import (
    SCHEMA,UPPER_SEAT_M,TONGUE_SEAT_M,TOOTH_SCALE,LIP_MAX_PUSH_M,
    LIP_Z_CENTER,LIP_Z_HALF_SPAN,LIP_X_HALF_SPAN,MIN_TOOTH_SCALE,MAX_TOOTH_SCALE,
    TEETH_GUM_TONE,TEETH_GUM_MUTE_STRENGTH,
    validate_seat,plan_masked_translation,plan_translation,
    plan_cavity_faces,cavity_z_window,validate_tooth_scale,validate_lip_push,
    plan_uniform_scale,plan_lip_soften,validate_polygon_correspondence,
    nearest_triangle_distances,distance_summary,
    classify_gum_pixels,mute_gum_pixels,
    count_intersecting_triangle_pairs,
    describe_intersecting_triangle_pairs)
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


class ToothScaleValidationTests(unittest.TestCase):
    def test_default_in_range(self):
        self.assertEqual(validate_tooth_scale(TOOTH_SCALE),TOOTH_SCALE)

    def test_bounds_accepted(self):
        self.assertEqual(validate_tooth_scale(MIN_TOOTH_SCALE),MIN_TOOTH_SCALE)
        self.assertEqual(validate_tooth_scale(MAX_TOOTH_SCALE),MAX_TOOTH_SCALE)

    def test_out_of_range_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_RANGE_TOOTH_SCALE'):
            validate_tooth_scale(0.59)
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_RANGE_TOOTH_SCALE'):
            validate_tooth_scale(1.31)

    def test_bool_and_nan_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_VALUE_TOOTH_SCALE'):
            validate_tooth_scale(True)
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_VALUE_TOOTH_SCALE'):
            validate_tooth_scale(float('nan'))

    def test_type_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_TYPE_TOOTH_SCALE'):
            validate_tooth_scale('small')


class LipPushValidationTests(unittest.TestCase):
    def test_default_in_range(self):
        self.assertEqual(validate_lip_push(LIP_MAX_PUSH_M),LIP_MAX_PUSH_M)
        self.assertEqual(validate_lip_push(0.0),0.0)

    def test_out_of_range_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_RANGE_LIP_PUSH'):
            validate_lip_push(0.021)
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_RANGE_LIP_PUSH'):
            validate_lip_push(-0.001)

    def test_bool_and_nan_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_VALUE_LIP_PUSH'):
            validate_lip_push(False)
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_VALUE_LIP_PUSH'):
            validate_lip_push(float('nan'))


class UniformScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(11)
        n=3868
        cls.points=rng.uniform([-0.032,-0.16,1.52],[0.032,-0.06,1.59],
                               size=(n,3))
        cls.pivot=cls.points.mean(axis=0)

    def test_unity_scale_is_noop(self):
        moved,audit=plan_uniform_scale(self.points,1.0,self.pivot,label='TEETH')
        np.testing.assert_allclose(moved,self.points,atol=1e-12)
        self.assertEqual(audit['max_displacement_m'],0.0)
        self.assertEqual(audit['schema'],SCHEMA)

    def test_scale_shrinks_toward_pivot(self):
        moved,audit=plan_uniform_scale(self.points,0.85,self.pivot,label='TEETH')
        radius_before=np.linalg.norm(self.points-self.pivot,axis=1)
        radius_after=np.linalg.norm(moved-self.pivot,axis=1)
        np.testing.assert_allclose(radius_after,radius_before*0.85,atol=1e-12)

    def test_pivot_preserved_exactly(self):
        moved,audit=plan_uniform_scale(self.points,0.85,self.pivot,label='TEETH')
        np.testing.assert_allclose(moved.mean(axis=0),self.pivot*0.15+self.points.mean(axis=0)*0.85,atol=1e-12)

    def test_audit_fields(self):
        moved,audit=plan_uniform_scale(self.points,0.85,self.pivot,label='TEETH')
        self.assertEqual(audit['operation'],'UNIFORM_SCALE_ABOUT_PIVOT')
        self.assertEqual(audit['selected_vertices'],len(self.points))
        self.assertEqual(audit['stationary_vertices'],0)
        self.assertEqual(audit['scale'],0.85)
        self.assertAlmostEqual(
            audit['max_displacement_m'],
            float((1.0-0.85)*np.linalg.norm(self.points-self.pivot,axis=1).max()),
            places=7)

    def test_input_not_mutated(self):
        before=self.points.copy()
        plan_uniform_scale(self.points,0.85,self.pivot,label='TEETH')
        np.testing.assert_array_equal(self.points,before)

    def test_bad_pivot_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_PIVOT_TEETH'):
            plan_uniform_scale(self.points,0.85,[0.0,0.0],label='TEETH')
        with self.assertRaisesRegex(MouthAnatomyError,'E_PIVOT_TEETH'):
            plan_uniform_scale(self.points,0.85,[0.0,0.0,float('nan')],label='TEETH')

    def test_out_of_range_scale_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_SCALE_RANGE_'):
            plan_uniform_scale(self.points,1.5,self.pivot,label='TEETH')

    def test_shape_validation(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_POINTS_'):
            plan_uniform_scale(self.points[:,:2],0.85,self.pivot,label='TEETH')


class LipSoftenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # synthetic chin/sulcus profile: centre column with front-facing
        # vertices and a rear point facing backwards
        rng=np.random.default_rng(21)
        z=np.linspace(1.42,1.53,24)
        x=rng.uniform(-LIP_X_HALF_SPAN*0.9,LIP_X_HALF_SPAN*0.9,size=24)
        y=-0.08+rng.normal(0.0,0.004,size=24)
        pts=np.column_stack([x,y,z])
        cls.sulcus=pts

    def test_zero_push_is_noop(self):
        moved,audit=plan_lip_soften(self.sulcus,max_push=0.0)
        np.testing.assert_allclose(moved,self.sulcus,atol=1e-12)
        self.assertEqual(audit['operation'],'FRONT_SULCUS_FORWARD_LIFT')
        self.assertEqual(audit['max_displacement_m'],0.0)

    def test_centre_band_moves_forward_most(self):
        centre=np.array([[0.0,-0.08,LIP_Z_CENTER]])
        moved,audit=plan_lip_soften(centre,max_push=0.008)
        self.assertAlmostEqual(moved[0,1]-centre[0,1],-0.008,places=9)

    def test_weights_fall_off_from_centre(self):
        zs=np.linspace(LIP_Z_CENTER-LIP_Z_HALF_SPAN*0.8,
                       LIP_Z_CENTER+LIP_Z_HALF_SPAN*0.8,9)
        pts=np.column_stack([np.zeros_like(zs),np.full_like(zs,-0.08),zs])
        moved,_=plan_lip_soften(pts,max_push=0.008)
        disp=np.linalg.norm(moved-pts,axis=1)
        mid=len(disp)//2
        self.assertGreater(disp[mid],disp[0])
        self.assertGreater(disp[mid],disp[-1])
        self.assertGreater(disp[mid-1],disp[0])

    def test_outside_x_span_untouched(self):
        pts=np.array([[LIP_X_HALF_SPAN*1.5,-0.08,LIP_Z_CENTER]])
        moved,audit=plan_lip_soften(pts,max_push=0.008)
        np.testing.assert_allclose(moved,pts,atol=1e-12)
        self.assertEqual(audit['selected_vertices'],0)

    def test_outside_z_span_untouched(self):
        pts=np.array([[0.0,-0.08,LIP_Z_CENTER+LIP_Z_HALF_SPAN*2.0],
                      [0.0,-0.08,LIP_Z_CENTER-LIP_Z_HALF_SPAN*2.0]])
        moved,_=plan_lip_soften(pts,max_push=0.008)
        np.testing.assert_allclose(moved,pts,atol=1e-12)

    def test_rear_vertices_untouched(self):
        pts=np.array([[0.0,0.05,LIP_Z_CENTER]])  # back of the head
        moved,_=plan_lip_soften(pts,max_push=0.008)
        np.testing.assert_allclose(moved,pts,atol=1e-12)

    def test_forward_direction(self):
        moved,_=plan_lip_soften(self.sulcus,max_push=0.008)
        deltas=(moved-self.sulcus)[:,1]
        self.assertTrue(np.all(deltas<=0.0))  # toward -Y (front)

    def test_bad_params_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_Z_SPAN_'):
            plan_lip_soften(self.sulcus,z_half_span=0.0)
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_X_SPAN_'):
            plan_lip_soften(self.sulcus,x_half_span=0.0)
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_PUSH_'):
            plan_lip_soften(self.sulcus,max_push=0.021)
        with self.assertRaisesRegex(MouthAnatomyError,'E_LIP_INPUT_'):
            plan_lip_soften(self.sulcus,z_center=float('nan'))

    def test_monotonic_max_displacement(self):
        _,a=plan_lip_soften(self.sulcus,max_push=0.004)
        _,b=plan_lip_soften(self.sulcus,max_push=0.008)
        self.assertLess(a['max_displacement_m'],b['max_displacement_m'])


class PolygonCorrespondenceTests(unittest.TestCase):
    def test_identical_match(self):
        loops=[(0,1,2,3),(4,5,6),(7,8,9,10,11,12)]
        self.assertEqual(validate_polygon_correspondence(loops,loops),3)

    def test_count_mismatch_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_POLYGON_COUNT_'):
            validate_polygon_correspondence([(0,1,2),(3,4,5)],[(0,1,2)])

    def test_winding_change_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_LOOP_MISMATCH_0'):
            validate_polygon_correspondence([(0,1,2)],[(2,1,0)])

    def test_third_face_mismatch_reported_with_index(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_CAVITY_LOOP_MISMATCH_2'):
            validate_polygon_correspondence(
                [(0,1,2),(3,4,5),(6,7,8)],
                [(0,1,2),(3,4,5),(8,7,6)])

    def test_numeric_like_ints_accepted(self):
        self.assertEqual(validate_polygon_correspondence(
            [[0.0,1.0,2.0]],[(0,1,2)]),1)


class PointTriangleDistanceTests(unittest.TestCase):
    def setUp(self):
        self.tri=np.array([[[0.0,0.0,0.0],[1.0,0.0,0.0],[0.0,1.0,0.0]]],
                           dtype=np.float64)

    def test_above_interior(self):
        d=nearest_triangle_distances(np.array([[0.25,0.25,2.0]]),self.tri)
        self.assertAlmostEqual(d[0],2.0,places=7)

    def test_above_vertex(self):
        d=nearest_triangle_distances(np.array([[0.0,0.0,1.0]]),self.tri)
        self.assertAlmostEqual(d[0],1.0,places=7)

    def test_nearest_edge(self):
        d=nearest_triangle_distances(np.array([[0.5,-1.0,0.0]]),self.tri)
        self.assertAlmostEqual(d[0],1.0,places=7)

    def test_hypotenuse_outside(self):
        d=nearest_triangle_distances(np.array([[2.0,2.0,0.0]]),self.tri)
        self.assertAlmostEqual(d[0],np.sqrt(1.5**2+1.5**2),places=7)

    def test_on_plane_inside_is_zero(self):
        d=nearest_triangle_distances(np.array([[0.1,0.1,0.0]]),self.tri)
        self.assertAlmostEqual(d[0],0.0,places=9)

    def test_min_over_multiple_triangles(self):
        tris=np.array([
            [[5.0,5.0,0.0],[6.0,5.0,0.0],[5.0,6.0,0.0]],   # far
            [[0.0,0.0,0.0],[1.0,0.0,0.0],[0.0,1.0,0.0]],   # near
        ])
        d=nearest_triangle_distances(np.array([[0.25,0.25,3.0]]),tris)
        self.assertAlmostEqual(d[0],3.0,places=7)

    def test_chunking_matches_unchunked(self):
        rng=np.random.default_rng(4)
        pts=rng.normal(size=(257,3))
        tris=np.array([
            [[0.0,0.0,0.0],[1.0,0.3,0.0],[0.1,1.0,0.2]],
            [[2.0,0.0,0.0],[3.0,0.5,0.0],[2.1,1.0,0.1]],
        ])
        d1=nearest_triangle_distances(pts,tris,chunk_size=128)
        d2=nearest_triangle_distances(pts,tris,chunk_size=64)
        np.testing.assert_allclose(d1,d2,atol=1e-12)

    def test_bad_inputs_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_DISTANCE_POINTS'):
            nearest_triangle_distances(np.zeros((2,2)),self.tri)
        with self.assertRaisesRegex(MouthAnatomyError,'E_DISTANCE_TRIANGLES'):
            nearest_triangle_distances(np.zeros((2,3)),np.zeros((2,2,3)))
        with self.assertRaisesRegex(MouthAnatomyError,'E_DISTANCE_TRIANGLES_EMPTY'):
            nearest_triangle_distances(np.zeros((2,3)),np.zeros((0,3,3)))


class DistanceSummaryTests(unittest.TestCase):
    def test_summary_fields(self):
        summary=distance_summary(np.array([0.0,0.001,0.005,0.01]))
        self.assertEqual(summary['min_m'],0.0)
        self.assertEqual(summary['max_m'],0.01)
        self.assertEqual(summary['touching_count_lt_1e-4'],1)
        self.assertEqual(summary['sample_count'],4)
        self.assertAlmostEqual(summary['median_m'],0.003,places=9)

    def test_bad_input_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_DISTANCE_SUMMARY'):
            distance_summary(np.array([]))
        with self.assertRaisesRegex(MouthAnatomyError,'E_DISTANCE_SUMMARY'):
            distance_summary(np.array([float('nan')]))


class IntersectionTests(unittest.TestCase):
    def setUp(self):
        # A: triangle in the z=0 plane
        self.tri_a = np.array([[[-1.0, 1.0, 0.0], [1.0, 1.0, 0.0],
                                [0.0, -1.0, 0.0]]])

    def test_transversal_crossing_detected(self):
        # B: triangle in the x=0 plane with an edge piercing A
        tri_b = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                           [0.0, -0.6, 1.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 1)
        self.assertEqual(result['sample_pairs'], [(0, 0)])
        self.assertEqual(result['method'], 'MOLLER_TRIANGLE_PIERCE')

    def test_separated_triangles_yield_zero(self):
        tri_b = np.array([[[5.0, 5.0, 5.0], [6.0, 5.0, 5.0],
                           [5.0, 6.0, 5.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_parallel_plane_above_yields_zero(self):
        tri_b = np.array([[[-1.0, 1.0, 1.0], [1.0, 1.0, 1.0],
                           [0.0, -1.0, 1.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_coplanar_overlap_not_counted(self):
        # coplanar overlapping triangles: transversal test must not fire
        tri_b = np.array([[[-0.5, 0.5, 0.0], [0.5, 0.5, 0.0],
                           [0.0, -0.5, 0.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_vertex_touch_not_counted(self):
        # B's lowest vertex sits exactly on A's plane - tangential
        tri_b = np.array([[[0.0, 0.0, 0.0], [0.0, 0.5, 1.0],
                           [0.0, -0.5, 1.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_far_edge_of_a_outside_b(self):
        # B crosses z=0 far outside A's footprint
        tri_b = np.array([[[5.0, 0.0, -1.0], [5.0, 0.6, 1.0],
                           [5.0, -0.6, 1.0]]])
        result = count_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_broadphase_reports_all_hits(self):
        tris_a = np.repeat(self.tri_a, 30, axis=0)
        tri_b = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                           [0.0, -0.6, 1.0]]])
        result = count_intersecting_triangle_pairs(tris_a, tri_b)
        self.assertEqual(result['pairs'], 30)
        self.assertEqual(result['total_a'], 30)
        self.assertEqual(result['total_b'], 1)

    def test_bad_inputs_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError, 'E_INTERSECT_A'):
            count_intersecting_triangle_pairs(np.zeros((1, 2, 3)), self.tri_a)
        with self.assertRaisesRegex(MouthAnatomyError, 'E_INTERSECT_B'):
            count_intersecting_triangle_pairs(self.tri_a, np.zeros((1, 3, 2)))
        with self.assertRaisesRegex(MouthAnatomyError, 'E_INTERSECT_EMPTY'):
            count_intersecting_triangle_pairs(np.zeros((0, 3, 3)), self.tri_a)
        with self.assertRaisesRegex(MouthAnatomyError, 'E_INTERSECT_MARGIN'):
            count_intersecting_triangle_pairs(
                self.tri_a, self.tri_a, aabb_margin=-1.0)


class DescribeCrossingTests(unittest.TestCase):
    def setUp(self):
        self.tri_a = np.array([[[-1.0, 1.0, 0.0], [1.0, 1.0, 0.0],
                                [0.0, -1.0, 0.0]]])

    def test_locations_and_depth_proxy(self):
        tri_b = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                           [0.0, -0.6, 1.0]]])
        result = describe_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 1)
        detail = result['pair_details'][0]
        self.assertEqual(detail['pair'], [0, 0])
        centroid = detail['centroid_m']
        # six involved vertices: mean = (0, (-1+1+1+0.6+0+0.6... ) ...)
        expected = np.mean(np.array(
            [[-1, 1, 0], [1, 1, 0], [0, -1, 0],
             [0, 0, -1], [0, 0.6, 1], [0, -0.6, 1]]), axis=0)
        np.testing.assert_allclose(np.array(centroid), expected, atol=1e-6)
        # A lies in z=0 (extent of B across A's plane = B's z spread = 2.0)
        self.assertAlmostEqual(detail['extent_b_across_a_plane_m'], 2.0,
                               places=6)
        # B lies in x=0; extent of A across B's plane = A's x spread = 2.0
        self.assertAlmostEqual(detail['extent_a_across_b_plane_m'], 2.0,
                               places=6)
        self.assertAlmostEqual(detail['crossing_depth_estimate_m'], 2.0,
                               places=6)
        self.assertEqual(result['method'],
                         'MOLLER_TRIANGLE_PIERCE_WITH_PLANE_EXTENT_PROXY')
        self.assertEqual(result['summary']['pairs'], 1)

    def test_no_crossings_gives_empty_details(self):
        tri_b = np.array([[[5.0, 5.0, 5.0], [6.0, 5.0, 5.0],
                           [5.0, 6.0, 5.0]]])
        result = describe_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)
        self.assertEqual(result['pair_details'], [])
        self.assertIsNone(result['summary']['crossing_depth_min_m'])
        self.assertIsNone(result['summary']['crossing_depth_median_m'])
        self.assertIsNone(result['summary']['crossing_depth_max_m'])

    def test_tangential_touch_not_counted(self):
        tri_b = np.array([[[0.0, 0.0, 0.0], [0.0, 0.5, 1.0],
                           [0.0, -0.5, 1.0]]])
        result = describe_intersecting_triangle_pairs(self.tri_a, tri_b)
        self.assertEqual(result['pairs'], 0)

    def test_count_and_describe_agree(self):
        tris_a = np.repeat(self.tri_a, 5, axis=0)
        tri_b = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                           [0.0, -0.6, 1.0]]])
        counted = count_intersecting_triangle_pairs(tris_a, tri_b)
        described = describe_intersecting_triangle_pairs(tris_a, tri_b)
        self.assertEqual(counted['pairs'], described['pairs'])

    def test_details_capped(self):
        tris_a = np.repeat(self.tri_a, 4, axis=0)
        tri_b = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                           [0.0, -0.6, 1.0]]])
        result = describe_intersecting_triangle_pairs(
            tris_a, tri_b, max_reported_pairs=2)
        self.assertEqual(result['pairs'], 4)
        self.assertEqual(len(result['pair_details']), 2)
        self.assertTrue(result['pair_details_truncated'])

    def test_bad_report_cap_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError, 'E_INTERSECT_REPORT_CAP'):
            describe_intersecting_triangle_pairs(
                self.tri_a, self.tri_a, max_reported_pairs=0)


class ConstantSanityTests(unittest.TestCase):
    def test_pinned_constants(self):
        self.assertEqual(TONGUE_SEAT_M,0.024)
        self.assertEqual(UPPER_SEAT_M,0.022)
        self.assertEqual(TOOTH_SCALE,0.85)
        self.assertEqual(LIP_MAX_PUSH_M,0.010)
        self.assertEqual(LIP_Z_CENTER,1.492)
        self.assertEqual(LIP_Z_HALF_SPAN,0.030)
        self.assertEqual(LIP_X_HALF_SPAN,0.034)
        self.assertEqual(MIN_TOOTH_SCALE,0.60)
        self.assertEqual(MAX_TOOTH_SCALE,1.30)
        self.assertEqual(TEETH_GUM_TONE,(0.30,0.16,0.14))
        self.assertEqual(TEETH_GUM_MUTE_STRENGTH,0.80)


class GumClassificationTests(unittest.TestCase):
    def test_slab_and_grey_pixels(self):
        slab=np.array([[111/255.,47/255.,52/255.]])
        grey=np.array([[71/255.,68/255.,67/255.]])
        white=np.array([[0.85,0.84,0.84]])
        rgb=np.stack([slab[0],grey[0],white[0]]).reshape(1,3,3)
        mask=classify_gum_pixels(rgb)
        self.assertTrue(mask[0,0])
        self.assertFalse(mask[0,1])
        self.assertFalse(mask[0,2])

    def test_bright_red_still_classified_as_gum(self):
        bright=np.array([[[0.70,0.30,0.30]]])  # vivid gum, under 190/255
        self.assertTrue(classify_gum_pixels(bright)[0,0])

    def test_neutral_tan_not_classified(self):
        tan=np.array([[[0.62,0.60,0.55]]])  # low saturation
        self.assertFalse(classify_gum_pixels(tan)[0,0])

    def test_inputs_not_mutated_and_shape_kept(self):
        rgb=np.random.default_rng(5).uniform(0,1,size=(4,4,3))
        out,mask=mute_gum_pixels(rgb,tone=(0.3,0.15,0.14),strength=0.8)
        np.testing.assert_array_equal(out.shape,rgb.shape)
        np.testing.assert_array_equal(mask.shape,rgb.shape[:2])
        self.assertIsNot(out,rgb)

    def test_tooth_texels_bit_identical(self):
        rng=np.random.default_rng(7)
        rgb=np.vstack([
            np.tile(np.array([[71/255.,68/255.,67/255.]]),(4,1,1)),
        ]).reshape(2,2,3)
        out,mask=mute_gum_pixels(rgb,tone=(0.3,0.15,0.14),strength=0.8)
        self.assertEqual(int(mask.sum()),0)
        np.testing.assert_array_equal(out,rgb)

    def test_gum_texels_move_toward_tone(self):
        slab=np.array([[[111/255.,47/255.,52/255.]]])
        out,mask=mute_gum_pixels(slab,tone=(0.3,0.16,0.14),strength=0.8)
        expected=slab*0.2+np.array([0.3,0.16,0.14])*0.8
        np.testing.assert_allclose(out[0,0],expected[0,0],atol=1e-12)

    def test_bad_geometry_rejected(self):
        with self.assertRaisesRegex(MouthAnatomyError,'E_GUM_PIXELS_LAYOUT'):
            classify_gum_pixels(np.zeros((4,3)))
        with self.assertRaisesRegex(MouthAnatomyError,'E_GUM_PIXELS_EMPTY'):
            classify_gum_pixels(np.zeros((0,0,3)))

    def test_bad_tone_and_strength_rejected(self):
        rgb=np.zeros((1,1,3))
        with self.assertRaisesRegex(MouthAnatomyError,'E_GUM_TONE'):
            mute_gum_pixels(rgb,tone=(0.1,0.2),strength=0.8)
        with self.assertRaisesRegex(MouthAnatomyError,'E_GUM_TONE'):
            mute_gum_pixels(rgb,tone=(0.1,float('nan'),0.1),strength=0.8)
        with self.assertRaisesRegex(MouthAnatomyError,'E_GUM_STRENGTH'):
            mute_gum_pixels(rgb,tone=(0.3,0.15,0.14),strength=1.5)


if __name__=='__main__':
    unittest.main()
