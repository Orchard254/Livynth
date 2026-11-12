"""IDENTITY-021 focused tests; do not require Blender or MPFB installation."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.rigged_seam_copy_probe import RiggedSeamError, skin_weight_digest
from tools.run_mpfb_rigged_seam_probe import (
    SCHEMA, PASS, command, run)


class WeightFingerprintTests(unittest.TestCase):
    def test_group_order_does_not_change_fingerprint(self):
        first=[[(3,.75),(1,.25)],[(3,1.)],[]]
        second=[[(1,.25),(3,.75)],[(3,1.)],[]]
        a=skin_weight_digest(first,vertex_count=3)
        b=skin_weight_digest(second,vertex_count=3)
        self.assertEqual(a,b)
        self.assertEqual(a['weighted_vertices'],2)
        self.assertEqual(a['assignments'],3)

    def test_weight_drift_changes_fingerprint(self):
        a=skin_weight_digest([[(1,.3)],[(2,.7)]],vertex_count=2)
        b=skin_weight_digest([[(1,.4)],[(2,.7)]],vertex_count=2)
        self.assertNotEqual(a['sha256'],b['sha256'])

    def test_missing_all_weights_rejected(self):
        with self.assertRaisesRegex(RiggedSeamError,'E_RIGGED_SEAM_UNWEIGHTED'):
            skin_weight_digest([[],[]],vertex_count=2)

    def test_duplicate_or_nonfinite_weights_rejected(self):
        for weights in (
            [[(0,.5),(0,.5)],[(1,1)]],
            [[(0,float('nan'))],[(1,1)]],
            [[(0,1.2)],[(1,.8)]],
        ):
            with self.assertRaises(RiggedSeamError):
                skin_weight_digest(weights,vertex_count=2)

    def test_wrong_number_of_vertices_rejected(self):
        with self.assertRaisesRegex(RiggedSeamError,'E_RIGGED_SEAM_WEIGHT_LAYOUT'):
            skin_weight_digest([[(1,1)]],vertex_count=2)


class OwnerRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.output=self.root/'probe'
        self.asset_plan=Path(__file__).resolve().parents[1]/(
            'character/appearance/native_anatomy_demo.json')

    def pass_report(self):
        return {
            'schema':SCHEMA,
            'character':'demo_head_a',
            'status':PASS,
            'source_asset_modified':False,
            'existing_glbs_modified':False,
            'render_started':False,
            'vertices_preserved':3868,
            'retained_faces':3540,
            'bridge_faces_removed_on_disposable_copy':20,
            'vertex_order_preserved':True,
            'armature_modifier_preserved':True,
            'vertex_groups_preserved':True,
            'materials_preserved':True,
            'cross_jaw_edges_after':0,
            'facial_motion':'NOT_TESTED',
            'visual_quality':'NOT_TESTED',
            'skin_weight_sha256_before_after':'f'*64,
            'skin_weight_assignments':5600,
        }

    def fake_result(self,data,code=0):
        class Completed:
            returncode=code
        def execute(argv,**kwargs):
            self.assertIn('--rigged-seam-probe',argv)
            self.assertNotIn('--mhclo-dentition',argv)
            self.assertNotIn('--oral-correctives',argv)
            self.output.mkdir()
            (self.output/'rigged_seam_probe.json').write_text(json.dumps(data))
            return Completed()
        return execute

    def test_command_only_head_a_and_no_render_flags(self):
        argv=command('blender.exe',self.asset_plan,self.output)
        self.assertIn('--rigged-seam-probe',argv)
        self.assertIn('demo_head_a',argv)
        self.assertNotIn('demo_head_b',argv)
        self.assertNotIn('--audit-oral-motion',argv)
        self.assertNotIn('--mhclo-dentition',argv)

    def test_complete_pass_contract_accepted(self):
        report=run('blender.exe',self.asset_plan,self.output,
                   execute=self.fake_result(self.pass_report()))
        self.assertEqual(report['status'],PASS)

    def test_fake_pass_without_preserved_weights_rejected(self):
        report=self.pass_report()
        report.pop('skin_weight_sha256_before_after')
        with self.assertRaisesRegex(RuntimeError,
                                    'E_RIGGED_SEAM_REPORT_FALSE_PASS'):
            run('blender.exe',self.asset_plan,self.output,
                execute=self.fake_result(report))

    def test_failed_blender_report_preserved_for_diagnosis(self):
        report=self.pass_report()
        report.update(status='FAIL_RIGGED_SEAM_COPY_NOT_PRODUCTION_QA',
                      error='E_RIGGED_SEAM_WEIGHTS_CHANGED')
        with self.assertRaisesRegex(RuntimeError,'E_RIGGED_SEAM_REJECTED'):
            run('blender.exe',self.asset_plan,self.output,
                execute=self.fake_result(report,code=1))
        self.assertTrue((self.output/'rigged_seam_probe.json').is_file())

    def test_no_report_rejected(self):
        class Completed:
            returncode=0
        with self.assertRaisesRegex(RuntimeError,'E_RIGGED_SEAM_REPORT_MISSING'):
            run('blender.exe',self.asset_plan,self.output,
                execute=lambda *args,**kwargs:Completed())


if __name__=='__main__':
    unittest.main()
