"""CPU-only IDENTITY-014 jaw morph to oral mesh corrective shape QA."""
import io
import os
from pathlib import Path
import zipfile
import unittest
import numpy as np
from character.oral_correctives import (
    SCHEMA, OralCorrectiveError, derive_lower_jaw_translation,
    dental_influence, corrected_asset_points)

ROOT=Path(__file__).resolve().parents[1]


class OralCorrectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(17)
        face=rng.uniform([-.08,-.20,1.49],[.08,-.065,1.59],size=(700,3))
        cls.body=np.vstack((face,np.array([
            [-.567,-.30,0.0],[.567,.09,0.1],[-.567,-.30,1.747],
            [.567,.09,1.747],[0,-.15,1.6],[0,-.15,1.45]],dtype=float)))
        cls.teeth=np.array([[0,0,1.530+i*.0003] for i in range(200)],dtype=float)
        cls.tongue=np.array([[0,0,1.54+i*.0002] for i in range(50)],dtype=float)
        h=float(np.ptp(cls.body[:,2]))
        depth=(cls.body[:,2].max()-cls.body[:,2])/h
        mask=((depth>.11)&(depth<.13)&(np.abs(cls.body[:,0])/h<.03)&
              (cls.body[:,1]/h<-.06))
        cls.pose=cls.body.copy()
        cls.pose[mask,2]-=.011

    def test_lower_mouth_anchor_recovery(self):
        shift,audit=derive_lower_jaw_translation(self.body,self.pose)
        self.assertGreater(audit['anchor_count'],20)
        np.testing.assert_allclose(shift,[0,0,-.011],atol=1e-9)
        self.assertEqual(audit['schema'],SCHEMA)

    def test_both_bone_assets_can_receive_corrective_motion(self):
        shift,_=derive_lower_jaw_translation(self.body,self.pose)
        teeth,tstats=corrected_asset_points(self.teeth,shift,category='teeth')
        tongue,ustats=corrected_asset_points(self.tongue,shift,category='tongue')
        self.assertGreater(tstats['moved_vertices_gt_0_1_mm'],20)
        self.assertGreater(tstats['stationary_vertices_lt_0_1_mm'],20)
        self.assertEqual(ustats['moved_vertices_gt_0_1_mm'],len(tongue))
        self.assertAlmostEqual(tongue[0,2]-self.tongue[0,2],-.011)
        self.assertEqual(teeth.shape,self.teeth.shape)

    def test_upper_teeth_stay_stationary(self):
        influence=dental_influence(self.teeth,category='teeth')
        self.assertEqual(influence[-1],0)
        self.assertEqual(influence[0],1)
        self.assertGreater(np.count_nonzero(influence==0),30)

    def test_no_input_mutation(self):
        before=self.teeth.copy()
        corrected_asset_points(self.teeth,[0,0,-.01],category='teeth')
        np.testing.assert_array_equal(before,self.teeth)

    def test_face_morph_inert_rejected(self):
        with self.assertRaisesRegex(OralCorrectiveError,'E_JAW_ANCHORS_INERT'):
            derive_lower_jaw_translation(self.body,self.body)

    def test_wrong_direction_rejected(self):
        raised=self.body.copy()
        raised[:,2]+=.010
        with self.assertRaisesRegex(OralCorrectiveError,'E_JAW_TRANSLATION_UNSAFE'):
            derive_lower_jaw_translation(self.body,raised)

    def test_oversize_mouth_motion_rejected(self):
        moved=self.body.copy()
        moved[:,2]-=.050
        with self.assertRaisesRegex(OralCorrectiveError,'E_JAW_TRANSLATION_UNSAFE'):
            derive_lower_jaw_translation(self.body,moved)

    def test_nonfinite_dental_vertices_rejected(self):
        corrupt=self.teeth.copy()
        corrupt[0,1]=float('nan')
        with self.assertRaisesRegex(OralCorrectiveError,'E_ASSET_VERTICES'):
            corrected_asset_points(corrupt,[0,0,-.01],category='teeth')

    def test_tooth_arch_z_extent_must_be_plausible(self):
        with self.assertRaisesRegex(OralCorrectiveError,'E_TEETH_SPAN_INVALID'):
            dental_influence(np.ones((100,3)),category='teeth')

    def test_eyes_cannot_be_treated_as_oral_asset(self):
        with self.assertRaisesRegex(OralCorrectiveError,'E_UNSUPPORTED_ORAL_CATEGORY'):
            dental_influence(self.tongue,category='eyes')

    def test_wild_translation_rejected(self):
        with self.assertRaisesRegex(OralCorrectiveError,'E_JAW_TRANSLATION_UNSAFE'):
            corrected_asset_points(self.tongue,[0,0,-.09],category='tongue')

    def test_tongue_transform_is_rigid_translation(self):
        shifted,_=corrected_asset_points(self.tongue,[.001,0,-.005],category='tongue')
        np.testing.assert_allclose(np.diff(shifted,axis=0),
                                   np.diff(self.tongue,axis=0),atol=1e-12)

    def test_owner_native_geometry_when_available(self):
        path=Path(os.getenv('LIVYNTH_NATIVE_NEUTRAL_ZIP',
            str(ROOT/'output/c001_geo05/stage1_review.zip')))
        if not path.is_file():
            self.skipTest('Original private owner NPZ ZIP is optional')
        with zipfile.ZipFile(path) as archive:
            with np.load(io.BytesIO(archive.read('neutral_mesh.npz')),
                         allow_pickle=False) as mesh:
                body=mesh['vertices'].copy()
        h=float(np.ptp(body[:,2]))
        depth=(body[:,2].max()-body[:,2])/h
        mask=((depth>.11)&(depth<.13)&(np.abs(body[:,0])/h<.03)&
              (body[:,1]/h<-.06))
        posed=body.copy()
        posed[mask,2]-=.011
        shift,audit=derive_lower_jaw_translation(body,posed)
        self.assertGreater(audit['anchor_count'],20)
        np.testing.assert_allclose(shift,[0,0,-.011],atol=1e-9)


class OralRunnerFlagTests(unittest.TestCase):
    def setUp(self):
        self.plan=ROOT/'character/appearance/native_anatomy_demo.json'

    def test_oral_correctives_opt_in_not_default(self):
        from tools.run_anatomy_ab_review import plan
        normal=plan('blender.exe',self.plan,ROOT/'output/test_default_oral')
        experimental=plan('blender.exe',self.plan,ROOT/'output/test_corrective_oral',
                          align_accessories=True,audit_oral_motion=True,
                          oral_correctives=True)
        self.assertTrue(all('--oral-correctives' not in command for _,command in normal))
        self.assertTrue(all('--oral-correctives' in command for _,command in experimental))
        self.assertTrue(all('--align-accessories' in command and '--audit-oral-motion' in command
                            for _,command in experimental))

    def test_cannot_run_correctives_without_motion_evidence(self):
        from tools.run_anatomy_ab_review import run,AnatomyABError
        with self.assertRaisesRegex(AnatomyABError,
                                    'E_ORAL_CORRECTIVES_REQUIRE_ALIGNMENT_AND_AUDIT'):
            run('fake',self.plan,ROOT/'output/unused_never_written',
                oral_correctives=True,
                execute=lambda *args,**kwargs: self.fail('Blender must not launch'))


if __name__=='__main__':
    unittest.main()
