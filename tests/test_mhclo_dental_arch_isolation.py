"""IDENTITY-024 safety and report contracts; requires no Blender installation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tools.mhclo_arch_attribution import (
    ArchAttributionError, arch_location_audit, plan_arch_faces)
from tools.run_mpfb_dental_arch_isolation import (
    ArchReviewError,FILES,SCOPE,STATUS,command,validate)


def synthetic_mesh():
    mask=np.array([0.]*1984+[1.]*1884,dtype=np.float64)
    upper=[(i,i+1,i+166) for i in range(1818)]
    lower=[(1984+i,1984+i+1,1984+i+162) for i in range(1722)]
    return mask,upper+lower


def sample_report():
    a=arch_location_audit(
        np.zeros((3868,3),dtype=np.float64),
        np.zeros((226,3),dtype=np.float64),
        synthetic_mesh()[0])
    variants=[
        ('jaw_upper_only.png',True,False,True),
        ('jaw_lower_only.png',False,True,True),
        ('jaw_both_arches.png',True,True,True),
        ('jaw_lower_no_body.png',False,True,False),
    ]
    return {
        'schema':'livynth.anatomy-ab-render.v1',
        'status':STATUS,
        'character_id':'demo_head_a',
        'render_scope':SCOPE,
        'framing':'MOUTH_FOCUSED_FACE_CLOSEUP',
        'dental_visual_quality':'PENDING_INDEPENDENT_REVIEW',
        'existing_glbs_modified':False,
        'full_character_glb_export':'NOT_TESTED',
        'rig_joints':163,'facial_morph_count':67,
        'native_body_vertices':13380,'native_quads':13378,
        'seamed_render_copy_audit':{
            'status':'PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA',
            'removed_bridge_faces':20,
            'rigged_skin_weights_preserved':True,
            'original_mpfb_asset_modified':False,
        },
        'seamed_jaw_motion_audit':{
            'status':'PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA',
        },
        'dental_arch_location_audit':a,
        'dental_arch_render_audit':{
            'schema':'livynth.mhclo.arch-attribution.v1',
            'source_face_count':3540,
            'upper_face_count':1818,
            'lower_face_count':1722,
            'temporary_evaluated_arch_objects_removed_on_exit':True,
            'rendered_variants':[
                {'filename':name,
                 'upper_arch_visible':u,
                 'lower_arch_visible':l,
                 'body_visible':body,
                 'tongue_visible':False,
                 'original_rigged_teeth_visible':False,
                 'source_assets_modified':False,
                 'visual_approval':'PENDING'}
                for name,u,l,body in variants
            ],
        },
        'images':[{'filename':name} for name in FILES],
    }


class PureArchPlanningTests(unittest.TestCase):
    def test_complete_source_faces_split_without_overlap(self):
        mask,faces=synthetic_mesh()
        result=plan_arch_faces(mask,faces)
        self.assertEqual(len(result['upper_face_indices']),1818)
        self.assertEqual(len(result['lower_face_indices']),1722)
        self.assertEqual(len(result['upper_source_vertex_indices']),1984)
        self.assertEqual(len(result['lower_source_vertex_indices']),1884)
        self.assertEqual(result['lower_face_indices'][0],1818)
        self.assertEqual(len(faces),3540)

    def test_mixed_jaw_face_fails_closed(self):
        mask,faces=synthetic_mesh()
        faces[0]=(0,1984,166)
        with self.assertRaisesRegex(ArchAttributionError,'E_ID024_CROSS_JAW_FACE'):
            plan_arch_faces(mask,faces)

    def test_short_or_ambiguous_mask_fails_closed(self):
        mask,faces=synthetic_mesh()
        with self.assertRaisesRegex(ArchAttributionError,'E_ID024_PINNED_JAW_COUNTS'):
            plan_arch_faces(mask[:-1],faces)
        mask[0]=.5
        with self.assertRaisesRegex(ArchAttributionError,'E_ID024_MASK_INVALID'):
            plan_arch_faces(mask,faces)

    def test_missing_arch_vertex_is_rejected(self):
        mask,faces=synthetic_mesh()
        faces[-1]=(3863,3864,3865)
        with self.assertRaisesRegex(ArchAttributionError,
                                    'E_ID024_DENTAL_ARCH_SURFACE_COUNTS'):
            plan_arch_faces(mask,faces)

    def test_geometry_bounds_and_relative_centroids(self):
        mask,_=synthetic_mesh()
        teeth=np.zeros((3868,3),dtype=float)
        teeth[:1984,2]=.03
        teeth[1984:,2]=-.01
        tongue=np.zeros((226,3),dtype=float)
        tongue[:,2]=.01
        audit=arch_location_audit(teeth,tongue,mask)
        self.assertAlmostEqual(
            audit['tongue_centroid_minus_upper_arch_xyz_m'][2],-.02)
        self.assertAlmostEqual(
            audit['tongue_centroid_minus_lower_arch_xyz_m'][2],.02)
        self.assertEqual(audit['anatomical_contact'],'NOT_TESTED')

    def test_bad_location_layout_rejected(self):
        mask,_=synthetic_mesh()
        with self.assertRaisesRegex(ArchAttributionError,'E_ID024_LOCATION_INPUT'):
            arch_location_audit(
                np.zeros((3868,3)),np.zeros((225,3)),mask)


class ArchReviewTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.out=Path(t.name)

    def test_command_one_head_only_with_exclusive_arch_flag(self):
        argv=command('blender.exe','native-plan.json',self.out)
        self.assertIn('--dental-arch-isolation',argv)
        self.assertIn('--seam-jaw-stills',argv)
        self.assertIn('--mhclo-dentition',argv)
        self.assertNotIn('--oral-isolation',argv)
        self.assertNotIn('demo_head_b',argv)

    def test_valid_metadata_requires_real_png_data(self):
        with self.assertRaises(FileNotFoundError):
            validate(sample_report(),self.out)

    def test_correct_metadata_accepted_when_images_checked(self):
        with patch('tools.run_mpfb_dental_arch_isolation.check_png_dimensions'):
            self.assertTrue(validate(sample_report(),self.out))

    def test_fake_dental_surface_claim_rejected(self):
        r=sample_report()
        r['dental_visual_quality']='PASS'
        with self.assertRaisesRegex(ArchReviewError,'E_ID024_REPORT_CONTRACT'):
            validate(r,self.out)

    def test_mislabelled_arch_visibility_rejected_before_file_access(self):
        r=sample_report()
        r['dental_arch_render_audit']['rendered_variants'][1][
            'upper_arch_visible']=True
        with patch('tools.run_mpfb_dental_arch_isolation.check_png_dimensions') as check:
            with self.assertRaisesRegex(ArchReviewError,'E_ID024_ARCH_RENDER_LABELS'):
                validate(r,self.out)
            check.assert_not_called()

    def test_wrong_png_set_rejected(self):
        r=sample_report()
        r['images'].pop()
        with self.assertRaisesRegex(ArchReviewError,'E_ID024_STILL_FILES'):
            validate(r,self.out)

    def test_fake_motion_pass_rejected(self):
        r=sample_report()
        r['seamed_jaw_motion_audit']['status']='FAIL_SEAMED_JAW_MOTION_NOT_VISUAL_QA'
        with self.assertRaisesRegex(ArchReviewError,'E_ID024_SOURCE_GEOMETRY_GATE'):
            validate(r,self.out)


if __name__=='__main__':
    unittest.main()
