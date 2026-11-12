"""IDENTITY-016: local asset-only preflight, without costly Blender renders."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.mhclo_dental_preflight import (
    SCHEMA,DentalPreflightError,load_obj_topology,inspect_mhclo_weights)
from tools.run_mpfb_dental_preflight import command,run

ROOT=Path(__file__).resolve().parents[1]


class SourceOBJTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.obj=self.root/'teeth.obj'
    def make_obj(self,face='f 1/1/1 2/2/2 3/3/3 4/4/4'):
        self.obj.write_text('\n'.join(['v 0 0 0']*40+[face])+'\n',encoding='utf-8')
    def test_obj_reads_original_order_and_face_topology(self):
        self.make_obj()
        count,faces=load_obj_topology(self.obj)
        self.assertEqual(count,40)
        self.assertEqual(faces,[(0,1,2,3)])
    def test_negative_obj_face_indices_are_handled(self):
        self.make_obj('f -4 -3 -2 -1')
        count,faces=load_obj_topology(self.obj)
        self.assertEqual(faces,[(36,37,38,39)])
    def test_zero_or_out_of_range_faces_rejected(self):
        self.make_obj('f 0 2 3')
        with self.assertRaisesRegex(DentalPreflightError,'E_OBJ_FACE_INDEX'):
            load_obj_topology(self.obj)
    def test_linked_obj_outside_asset_directory_is_rejected(self):
        self.make_obj()
        other=self.root/'pointer.obj'
        try:
            other.symlink_to(self.obj)
        except (OSError,NotImplementedError):
            self.skipTest('Symlinks unsupported')
        with self.assertRaisesRegex(DentalPreflightError,'E_OBJ_MISSING_OR_SYMLINK'):
            load_obj_topology(other)
    def test_obj_limiter_prevents_unbounded_input(self):
        self.make_obj()
        with self.assertRaisesRegex(DentalPreflightError,'E_OBJ_VERTEX_LIMIT'):
            load_obj_topology(self.obj,max_vertices=10)


class MappingDiagnosticsTests(unittest.TestCase):
    def test_samples_are_bounded_and_distinguish_signed_from_nonunit(self):
        entries={
          0:{'verts':(14992,14993,0),'weights':(1.2,-.2,0)},
          1:{'verts':(14992,14993,0),'weights':(.6,.3,0)},
          2:{'verts':(14992,14993,0),'weights':(0.0,0.0,0.0)},
          3:{'verts':(14992,14993,0),'weights':(1.0,0.0,0.0)},
        }
        data=inspect_mhclo_weights(entries,sample_limit=2)
        self.assertEqual(data['schema'],SCHEMA)
        self.assertEqual(data['signed_weight_vertices'],1)
        self.assertEqual(data['nonunit_sum_vertices'],2)
        self.assertEqual(data['zero_abs_weight_vertices'],1)
        self.assertEqual(len(data['samples']),2)
        self.assertNotIn('C:\\',json.dumps(data))
    def test_invalid_weight_triplet_reported_instead_of_crashing(self):
        data=inspect_mhclo_weights({0:{'verts':(1,2,3),'weights':('bad',0,0)}})
        self.assertEqual(data['invalid_weight_triplet_vertices'],1)


class PreflightRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.out=self.root/'metadata.json'
        self.plan=ROOT/'character/appearance/native_anatomy_demo.json'
    def test_plan_runs_metadata_script_not_full_character_export(self):
        argv=command('blender.exe',self.plan,self.out)
        self.assertEqual(argv[0],'blender.exe')
        self.assertIn('mpfb_dental_preflight_blender.py',' '.join(argv))
        self.assertNotIn('mpfb_anatomy_ab_blender.py',' '.join(argv))
    def test_verified_preflight_report_passes(self):
        class Status: returncode=0
        def fake(*args,**kwargs):
            self.out.write_text(json.dumps({
              'schema':SCHEMA,'status':'PASS_REAL_MHCLO_JAW_GROUP_MAPPING_NOT_VISUAL_QA',
              'human_created':False,'glbs_touched':False}))
            return Status()
        report=run('blender.exe',self.plan,self.out,execute=fake)
        self.assertTrue(report['status'].startswith('PASS_'))
    def test_failed_real_asset_still_preserves_diagnostic_json(self):
        class Status: returncode=3
        def fake(*args,**kwargs):
            self.out.write_text(json.dumps({
              'schema':SCHEMA,'status':'FAIL_REAL_MHCLO_JAW_GROUP_MAPPING',
              'first_error':'E_MHCLO_AMBIGUOUS_JAW_VERTEX: index=9',
              'human_created':False,'glbs_touched':False}))
            return Status()
        with self.assertRaisesRegex(RuntimeError,'E_PREFLIGHT_REJECTED'):
            run('blender.exe',self.plan,self.out,execute=fake)
        self.assertTrue(self.out.is_file())
    def test_no_report_cannot_be_passed(self):
        class Status: returncode=0
        with self.assertRaisesRegex(RuntimeError,'E_PREFLIGHT_REPORT_MISSING'):
            run('blender.exe',self.plan,self.out,execute=lambda *args,**kw: Status())


if __name__=='__main__':
    unittest.main()
