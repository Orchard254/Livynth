"""IDENTITY-015: upper/lower jaw classification from original MPFB MHCLO helper vertices."""
import unittest
import numpy as np
from character.mhclo_dentition import (
    SCHEMA, DentitionMappingError, classify_dentition_mhclo)
from character.oral_correctives import corrected_asset_points, OralCorrectiveError
from tools.run_anatomy_ab_review import plan,run,AnatomyABError
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def fixture(count=200):
    mapping={
        i:{'verts':((14992+i%68,0,0) if i<count//2
                    else (15060+i%68,0,0)),
           'weights':(1.0,0.0,0.0)}
        for i in range(count)}
    polygons=[list(range(i,i+4)) for i in range(0,count,4)]
    return mapping,polygons


class OriginalHelperDentalTests(unittest.TestCase):
    def test_source_helper_assignments_upper_lower(self):
        mapping,faces=fixture()
        lower,audit=classify_dentition_mhclo(200,mapping,faces)
        self.assertEqual(audit['schema'],SCHEMA)
        self.assertEqual(audit['lower_teeth_vertices'],100)
        self.assertEqual(audit['upper_teeth_vertices'],100)
        self.assertEqual(lower.tolist(),[1.0]*100+[0.0]*100)

    def test_whole_tooth_faces_move_rigidly_not_stretched(self):
        mapping,faces=fixture()
        lower,_=classify_dentition_mhclo(200,mapping,faces)
        rng=np.random.default_rng(3)
        teeth=rng.normal(0,0.005,(200,3))
        teeth[:,2]+=1.5
        shifted,report=corrected_asset_points(
            teeth,[0,.014,-.012],category='teeth',lower_teeth_mask=lower)
        self.assertEqual(report['moved_vertices_gt_0_1_mm'],100)
        self.assertEqual(report['stationary_vertices_lt_0_1_mm'],100)
        self.assertEqual(report['dentition_segmentation'],
                         'MHCLO_UPPER_LOWER_HELPER_GROUPS')
        for face in faces:
            np.testing.assert_allclose(
                shifted[face]-teeth[face],
                np.tile(shifted[face[0]]-teeth[face[0]],(len(face),1)),
                atol=1e-12,rtol=0)

    def test_ambiguous_upper_lower_mapping_is_rejected(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,15060,0),'weights':(.7,.3,0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_AMBIGUOUS_JAW_VERTEX'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_reference_outside_dentition_is_rejected(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(10854,0,0),'weights':(1.0,0,0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_AMBIGUOUS_JAW_VERTEX'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_face_bridging_both_jaws_is_rejected(self):
        mapping,faces=fixture()
        faces.append([98,99,100,101])
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_MIXED_UPPER_LOWER_FACE'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_missing_mapping_rejected(self):
        mapping,faces=fixture()
        del mapping[3]
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_INPUT_CONTRACT'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_nonfinite_barycentric_weights_rejected(self):
        mapping,faces=fixture()
        mapping[0]['weights']=(float('nan'),0,0)
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_BAD_WEIGHTS'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_unbalanced_helper_classification_is_rejected(self):
        mapping,faces=fixture()
        for i in range(196):
            mapping[i]={'verts':(14992,0,0),'weights':(1.0,0,0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_UNBALANCED_JAWS'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_signed_extrapolation_within_lower_jaw_is_accepted(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,14993,0),'weights':(1.20,-.20,0)}
        lower,audit=classify_dentition_mhclo(200,mapping,faces)
        self.assertEqual(lower[0],1)
        self.assertEqual(audit['signed_coefficient_vertices'],1)
        self.assertEqual(audit['lower_teeth_vertices'],100)

    def test_nonunit_coefficients_within_one_jaw_are_attributed_not_refitted(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,14993,0),'weights':(.50,.30,0)}
        lower,audit=classify_dentition_mhclo(200,mapping,faces)
        self.assertEqual(lower[0],1)
        self.assertEqual(audit['nonunit_coefficient_sum_vertices'],1)
        self.assertAlmostEqual(audit['minimum_raw_coefficient_sum'],.8)

    def test_negative_reference_to_other_jaw_remains_ambiguous(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,15060,0),'weights':(1.2,-.2,0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_AMBIGUOUS_JAW_VERTEX'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_all_zero_coefficients_are_rejected(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,14993,0),'weights':(0.0,0.0,0.0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_BAD_WEIGHTS'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_non_dental_reference_with_negative_weight_rejected(self):
        mapping,faces=fixture()
        mapping[0]={'verts':(14992,8000,0),'weights':(1.1,-.1,0)}
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_AMBIGUOUS_JAW_VERTEX'):
            classify_dentition_mhclo(200,mapping,faces)

    def test_source_mesh_must_be_native_19158(self):
        mapping,faces=fixture()
        with self.assertRaisesRegex(DentitionMappingError,'E_MHCLO_INPUT_CONTRACT'):
            classify_dentition_mhclo(200,mapping,faces,source_vertex_count=13380)

    def test_dental_split_stable_sha_between_characters(self):
        mapping,faces=fixture()
        x,a=classify_dentition_mhclo(200,mapping,faces)
        y,b=classify_dentition_mhclo(200,mapping,faces)
        np.testing.assert_array_equal(x,y)
        self.assertEqual(a['lower_mask_sha256'],b['lower_mask_sha256'])

    def test_mask_must_be_rigid_zero_or_one(self):
        teeth=np.zeros((200,3),dtype=float)
        mask=np.r_[np.ones(100),np.zeros(99),0.5]
        with self.assertRaisesRegex(OralCorrectiveError,'E_DENTAL_MASK_INVALID'):
            corrected_asset_points(teeth,[0,.012,-.010],
                                   category='teeth',lower_teeth_mask=mask)

    def test_do_not_apply_dental_mask_to_tongue(self):
        tongue=np.zeros((50,3),dtype=float)
        with self.assertRaisesRegex(OralCorrectiveError,'E_DENTAL_MASK_ON_NON_TEETH'):
            corrected_asset_points(tongue,[0,.012,-.010],
                                   category='tongue',lower_teeth_mask=np.ones(50))


class AnatomyABOptInTests(unittest.TestCase):
    def setUp(self):
        self.file=ROOT/'character/appearance/native_anatomy_demo.json'

    def test_new_mode_requires_explicit_flag(self):
        default=plan('blender.exe',self.file,ROOT/'output/old')
        new=plan('blender.exe',self.file,ROOT/'output/mhclo',
                 align_accessories=True,audit_oral_motion=True,
                 oral_correctives=True,mhclo_dentition=True)
        self.assertTrue(all('--mhclo-dentition' not in argv for _,argv in default))
        self.assertTrue(all('--mhclo-dentition' in argv for _,argv in new))
        self.assertTrue(all('--oral-correctives' in argv for _,argv in new))

    def test_cannot_bypass_corrective_and_jaw_gates(self):
        with self.assertRaisesRegex(AnatomyABError,'E_MHCLO_DENTITION_REQUIRES_CORRECTIVES'):
            run('fake',self.file,ROOT/'output/no_read_only_run',
                mhclo_dentition=True,
                execute=lambda *a,**kw:self.fail('Blender must not start'))


if __name__=='__main__':
    unittest.main()
