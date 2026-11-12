"""IDENTITY-013: evaluate actual bone-bound oral asset movement versus jaw morph."""
import tempfile
import unittest
from pathlib import Path
import numpy as np

from character.anatomy_motion_audit import (
    SCHEMA,OralMotionError,displacement_stats,diagnose_oral_motion)
from tools.run_anatomy_ab_review import plan,validate_character,AnatomyABError

ROOT=Path(__file__).resolve().parents[1]


def sample_coords(size=120):
    x=np.arange(size,dtype=float)/100
    return np.column_stack([x,x*0+0.1,x*0+1.5])


def snapshots(*,body_m=0.008,teeth_m=0.0,tongue_m=0.0):
    before={name:sample_coords() for name in ('body','teeth','tongue')}
    after={name:points.copy() for name,points in before.items()}
    for name,delta in (('body',body_m),('teeth',teeth_m),('tongue',tongue_m)):
        after[name][:,2] += delta
    return before,after


class MotionMetricsTests(unittest.TestCase):
    def test_motion_detects_static_teeth_and_tongue_despite_body_jaw(self):
        initial,posed=snapshots()
        result=diagnose_oral_motion(initial,posed,pose='jaw_open')
        self.assertEqual(result['schema'],SCHEMA)
        self.assertEqual(result['status'],'FAIL_ORAL_ASSETS_STATIC_WHILE_BODY_MORPHS')
        self.assertEqual(result['stats']['body']['moved_vertices_gt_0_1_mm'],120)
        self.assertEqual(result['stats']['teeth']['moved_vertices_gt_0_1_mm'],0)
    def test_motion_detects_only_tongue_static(self):
        initial,posed=snapshots(teeth_m=.003,tongue_m=0)
        result=diagnose_oral_motion(initial,posed,pose='viseme_aa')
        self.assertEqual(result['status'],'FAIL_PARTIAL_ORAL_MOTION_SIGNAL')
    def test_motion_signal_not_mistaken_for_appearance_approval(self):
        initial,posed=snapshots(teeth_m=.002,tongue_m=.004)
        result=diagnose_oral_motion(initial,posed,pose='jaw_open')
        self.assertEqual(result['status'],'ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED')
        self.assertEqual(result['oral_contact_and_collision'],'NOT_TESTED')
        self.assertFalse(result['bone_to_morph_retarget_verified'])
    def test_body_morph_inert_is_distinct_from_oral_static(self):
        initial,posed=snapshots(body_m=0,teeth_m=0,tongue_m=0)
        result=diagnose_oral_motion(initial,posed,pose='jaw_open')
        self.assertEqual(result['status'],'FAIL_BODY_FACIAL_MORPH_INERT')
    def test_no_source_array_mutation(self):
        initial,posed=snapshots(teeth_m=.002,tongue_m=.004)
        base={k:v.copy() for k,v in initial.items()}
        diagnose_oral_motion(initial,posed,pose='jaw_open')
        for k in initial:
            np.testing.assert_array_equal(initial[k],base[k])
    def test_different_mesh_lengths_rejected(self):
        initial,posed=snapshots()
        posed['teeth']=posed['teeth'][:-1]
        with self.assertRaisesRegex(OralMotionError,'E_MOTION_ARRAY_INVALID'):
            diagnose_oral_motion(initial,posed,pose='jaw_open')
    def test_nan_evaluated_vertex_rejected(self):
        initial,posed=snapshots()
        posed['tongue'][0,2]=float('nan')
        with self.assertRaisesRegex(OralMotionError,'E_MOTION_ARRAY_INVALID'):
            diagnose_oral_motion(initial,posed,pose='jaw_open')
    def test_invalid_pose_rejected(self):
        initial,posed=snapshots()
        with self.assertRaisesRegex(OralMotionError,'E_MOTION_POSE'):
            diagnose_oral_motion(initial,posed,pose='neutral')
    def test_missing_asset_cannot_be_interpreted_as_motion(self):
        initial,posed=snapshots()
        del posed['tongue']
        with self.assertRaisesRegex(OralMotionError,'E_MOTION_OBJECT_SET'):
            diagnose_oral_motion(initial,posed,pose='jaw_open')
    def test_stats_respect_real_units(self):
        original=sample_coords()
        later=original.copy();later[:,2]+=0.005
        report=displacement_stats(original,later)
        self.assertAlmostEqual(report['max_displacement_m'],.005,places=6)
        self.assertEqual(report['moved_vertices_gt_0_1_mm'],120)


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.asset_plan=ROOT/'character/appearance/native_anatomy_demo.json'
    def test_audit_flag_only_in_explicit_mode(self):
        without=plan('blender.exe',self.asset_plan,self.root/'default')
        with_audit=plan('blender.exe',self.asset_plan,self.root/'diagnostic',
                        align_accessories=True,audit_oral_motion=True)
        for _,command in without:
            self.assertNotIn('--audit-oral-motion',command)
        for _,command in with_audit:
            self.assertIn('--audit-oral-motion',command)
            self.assertIn('--align-accessories',command)
    def test_forged_audit_is_rejected_before_render_check(self):
        report={
            'schema':'livynth.anatomy-ab-render.v1',
            'status':'CAPTURED_ANATOMY_AB_REQUIRES_VISUAL_REVIEW',
            'character_id':'demo_head_a','existing_glbs_modified':False,
            'rig_joints':163,'facial_morph_count':67,
            'native_body_vertices':13380,'native_quads':13378,
            'head_shape_audit':{'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS'},
            'source_body_sha256':'a','fitted_body_sha256':'b',
            'native_topology_sha256':'c',
            'facial_morph_names':[f'key{i}' for i in range(67)],
            'oral_motion_status':'RECORDED_DO_NOT_INFER_VISUAL_APPROVAL',
            'oral_motion_audit':{'jaw_open':{'schema':SCHEMA,'pose':'jaw_open',
                 'status':'ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED','stats':{}}}
        }
        with self.assertRaisesRegex(AnatomyABError,'E_MISSING_ORAL_MOTION_AUDIT'):
            validate_character(report,self.root,'demo_head_a',
                               expect_oral_motion=True)


if __name__=='__main__':
    unittest.main()
