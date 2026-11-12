"""IDENTITY-012 bind-space anatomy correction, separate from animation QA."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from character.anatomy_alignment import (
    align_positions,AccessoryAlignmentError)
from character.head_shape import displacement_field,InvalidHeadShape
from character.identity_recipe import load_recipe

ROOT=Path(__file__).resolve().parents[1]


class SharedCoordinateFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Synthetic full-body reference: permits repeatable CPU-only tests.
        cls.ref=np.array([
            [-.56,-.3,0],[.56,.09,.1],[-.56,-.3,1.747],[.56,.09,1.747],
            [0,-.15,1.6],[0,-.15,1.2]],dtype=float)
        cls.eyes=np.array([
            [-.04,-.18,1.60],[-.035,-.16,1.61],[-.03,-.18,1.62],
            [.03,-.18,1.62],[.035,-.16,1.61],[.04,-.18,1.60]],dtype=float)
        cls.a=load_recipe(ROOT/'character/recipes/demo_head_a.json')['head_shape']
        cls.b=load_recipe(ROOT/'character/recipes/demo_head_b.json')['head_shape']

    def test_field_matches_reference_coordinate_frame(self):
        _,audit=align_positions(self.ref,self.eyes,self.b)
        fitted,_=align_positions(self.ref,self.eyes,self.b)
        expected=self.eyes+displacement_field(
            self.eyes,self.b,reference_vertices=self.ref)
        np.testing.assert_allclose(fitted,expected,atol=1e-12,rtol=0)
        self.assertEqual(audit['vertices'],len(self.eyes))

    def test_different_head_recipes_move_anatomy_differently(self):
        a,_=align_positions(self.ref,self.eyes,self.a)
        b,_=align_positions(self.ref,self.eyes,self.b)
        self.assertGreater(np.max(np.linalg.norm(a-b,axis=1)),0.005)
        self.assertEqual(len(a),len(b))

    def test_original_source_and_input_not_mutated(self):
        before=self.eyes.copy()
        neutral=self.ref.copy()
        align_positions(self.ref,self.eyes,self.b)
        np.testing.assert_array_equal(self.eyes,before)
        np.testing.assert_array_equal(self.ref,neutral)

    def test_zero_coefficient_is_identity_transform(self):
        zero={key:0.0 for key in self.b}
        result,audit=align_positions(self.ref,self.eyes,zero)
        np.testing.assert_array_equal(result,self.eyes)
        self.assertEqual(audit['moved_vertices_gt_0_1_mm'],0)

    def test_invalid_nan_proxy_rejected(self):
        corrupt=self.eyes.copy()
        corrupt[0,2]=np.nan
        with self.assertRaisesRegex(AccessoryAlignmentError,'E_ASSET_INPUT_POINTS'):
            align_positions(self.ref,corrupt,self.b)

    def test_invalid_reference_mesh_rejected(self):
        with self.assertRaisesRegex(AccessoryAlignmentError,'E_ASSET_IDENTITY_FIELD'):
            align_positions(np.array([[0,0,0]]),self.eyes,self.b)

    def test_proxy_bounds_do_not_affect_shared_field(self):
        # Per-accessory automatic crown height would incorrectly make the
        # head field depend on each asset's own bounding box.
        single=self.eyes[:4]
        d1=displacement_field(single,self.b,reference_vertices=self.ref)
        d2=displacement_field(self.eyes,self.b,reference_vertices=self.ref)[:4]
        np.testing.assert_allclose(d1,d2,atol=1e-12,rtol=0)

    def test_neutral_body_field_unchanged_when_no_reference_argument(self):
        from character.head_shape import apply_head_shape
        p=self.ref
        implicit=displacement_field(p,self.b)
        explicit=displacement_field(p,self.b,reference_vertices=p)
        np.testing.assert_allclose(implicit,explicit,atol=0,rtol=0)


class AlignmentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.plan=ROOT/'character/appearance/native_anatomy_demo.json'

    def test_aligned_mode_is_explicit_not_default(self):
        from tools.run_anatomy_ab_review import plan
        original=plan('blender.exe',self.plan,self.root/'original')
        aligned=plan('blender.exe',self.plan,self.root/'aligned',align_accessories=True)
        for _,command in original:
            self.assertNotIn('--align-accessories',command)
        for _,command in aligned:
            self.assertIn('--align-accessories',command)

    def test_fake_alignment_audit_required(self):
        from tools.run_anatomy_ab_review import validate_character,AnatomyABError
        from tests.test_anatomy_ab_review import fake_report
        folder=self.root/'demo_head_b'
        folder.mkdir()
        report=fake_report('demo_head_b',folder)
        with self.assertRaisesRegex(AnatomyABError,'E_IDENTITY_FIELD_ALIGNMENT_NOT_APPLIED'):
            validate_character(report,folder,'demo_head_b',expect_alignment=True)

    def test_fake_alignment_audit_cannot_claim_good_rigging_from_name(self):
        from tools.run_anatomy_ab_review import validate_character,AnatomyABError
        from tests.test_anatomy_ab_review import fake_report
        folder=self.root/'demo_head_b'
        folder.mkdir()
        report=fake_report('demo_head_b',folder)
        report['anatomy_alignment_mode']='shared_identity_field'
        report['anatomy_alignment_audit']={name:{} for name in ('eyes','teeth','tongue')}
        with self.assertRaisesRegex(AnatomyABError,'E_IDENTITY_FIELD_ALIGNMENT_eyes'):
            validate_character(report,folder,'demo_head_b',expect_alignment=True)


if __name__=='__main__':
    unittest.main()
