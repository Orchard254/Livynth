"""Offline IDENTITY-011 runner and evidence contract tests (no Blender)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.run_anatomy_ab_review import (
    CHARACTERS,POSE_FILES,SCHEMA,AnatomyABError,
    plan,compare_reports,validate_character,run,
)
from tools.identity_pose_review import check_png_dimensions


class AnatomyPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.plan=Path(__file__).resolve().parents[1]/'character/appearance/native_anatomy_demo.json'
        self.dest=self.root/'render'
    def test_both_detailed_characters_have_independent_scenes(self):
        jobs=plan('blender.exe',self.plan,self.dest)
        self.assertEqual([row[0] for row in jobs],list(CHARACTERS))
        for char,cmd in jobs:
            self.assertIn('mpfb_anatomy_ab_blender.py',' '.join(cmd))
            self.assertIn('--character',cmd)
            self.assertIn(char,cmd)
            self.assertNotIn('mpfb_headless_probe.py',' '.join(cmd))
            self.assertNotIn('demo_head_a.glb',' '.join(cmd))
    def test_missing_asset_plan_rejected_before_blender(self):
        with self.assertRaises(Exception):
            plan('fake',self.root/'does_not_exist.json',self.dest)
    def test_existing_folder_prevents_render(self):
        self.dest.mkdir()
        with self.assertRaises(FileExistsError):
            run('fake',self.plan,self.dest,execute=lambda *a,**k:self.fail('no launch'))
    def test_failed_first_blender_blocks_second(self):
        calls=[]
        def explode(argv,**kwargs):
            calls.append(argv)
            raise OSError('simulated attachment failure')
        with self.assertRaisesRegex(OSError,'simulated attachment failure'):
            run('fake',self.plan,self.dest,execute=explode)
        self.assertEqual(len(calls),1)


def fake_report(char,folder,*,source='source',topology='topo',fitted='unique',
                joints=163,morphs=67):
    return {
        'schema':SCHEMA,'status':'CAPTURED_ANATOMY_AB_REQUIRES_VISUAL_REVIEW',
        'character_id':char,'existing_glbs_modified':False,
        'rig_joints':joints,'facial_morph_count':morphs,
        'native_body_vertices':13380,'native_quads':13378,
        'source_body_sha256':source,'fitted_body_sha256':fitted+char,
        'native_topology_sha256':topology,
        'head_shape_audit':{'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS'},
        'facial_morph_names':[f'key_{i}' for i in range(67)],
        'assets':[{'category':cat,'mesh_vertices':150,
                   'rigged_to_copied_armature':True}
                  for cat in ('eyes','teeth','tongue')],
        'images':[{'filename':name} for name in POSE_FILES],
        '_validated_folder':str(folder),
    }


class ValidateAnatomyReports(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.a=self.root/'demo_head_a'
        self.b=self.root/'demo_head_b'
        self.a.mkdir()
        self.b.mkdir()
    def test_bad_rig_rejected_before_any_render_claim(self):
        report=fake_report('demo_head_a',self.a,joints=162)
        with self.assertRaisesRegex(AnatomyABError,'E_ANATOMY_AB_REPORT'):
            validate_character(report,self.a,'demo_head_a')
    def test_bad_face_target_names_rejected(self):
        report=fake_report('demo_head_a',self.a)
        report['facial_morph_names']=['same']*67
        with self.assertRaisesRegex(AnatomyABError,'E_ANATOMY_AB_GEOMETRY'):
            validate_character(report,self.a,'demo_head_a')
    def test_unbound_eye_rejected(self):
        report=fake_report('demo_head_a',self.a)
        report['assets'][0]['rigged_to_copied_armature']=False
        with self.assertRaisesRegex(AnatomyABError,'E_ANATOMY_AB_RIGGED_ASSETS'):
            validate_character(report,self.a,'demo_head_a')
    def test_missing_images_rejected(self):
        report=fake_report('demo_head_a',self.a)
        with self.assertRaises(FileNotFoundError):
            validate_character(report,self.a,'demo_head_a')
    def test_mismatched_original_source_rejected(self):
        # Patch image validation locally for this cross-file contract test:
        # production validator separately checks every real PNG file.
        import tools.run_anatomy_ab_review as module
        original=module.validate_character
        module.validate_character=lambda *args,**kwargs:True
        try:
            a=fake_report('demo_head_a',self.a,source='base_a')
            b=fake_report('demo_head_b',self.b,source='base_b')
            with self.assertRaisesRegex(AnatomyABError,'E_INCOMPATIBLE_SOURCE'):
                compare_reports(a,b)
        finally:
            module.validate_character=original
    def test_identical_head_geometry_rejected(self):
        import tools.run_anatomy_ab_review as module
        original=module.validate_character
        module.validate_character=lambda *args,**kwargs:True
        try:
            a=fake_report('demo_head_a',self.a)
            b=fake_report('demo_head_b',self.b)
            a['fitted_body_sha256']='identical'
            b['fitted_body_sha256']='identical'
            with self.assertRaisesRegex(AnatomyABError,'E_SAME_FITTED_IDENTITY'):
                compare_reports(a,b)
        finally:
            module.validate_character=original


if __name__=='__main__':
    unittest.main()
