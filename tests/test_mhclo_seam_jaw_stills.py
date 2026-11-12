"""IDENTITY-022 focused tests: jaw-specific signal, strict two-image contract."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

import numpy as np

from character.seamed_jaw_motion import (
    PASS, SeamedJawMotionError, audit_seamed_jaw_motion)
from tools.run_mpfb_seam_jaw_stills import (
    SeamJawStillsError, POSE_IMAGES, command, run, validate_report)


def mask():
    return np.array([1.0]*1884+[0.0]*1984)


def report():
    return {
        'schema':'livynth.anatomy-ab-render.v1',
        'status':'CAPTURED_HEAD_A_SEAM_JAW_STILLS_PENDING_VISUAL_REVIEW',
        'character_id':'demo_head_a',
        'render_scope':'HEAD_A_FRONT_NEUTRAL_AND_JAW_OPEN_ONLY',
        'framing':'MOUTH_FOCUSED_FACE_CLOSEUP',
        'native_body_vertices':13380,
        'native_quads':13378,
        'rig_joints':163,
        'facial_morph_count':67,
        'existing_glbs_modified':False,
        'full_character_glb_export':'NOT_TESTED',
        'dental_visual_quality':'PENDING_INDEPENDENT_REVIEW',
        'seamed_render_copy_audit':{
            'status':'PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA',
            'retained_vertices':3868,'removed_bridge_faces':20,
            'seamed_faces':3540,'rigged_skin_weights_preserved':True,
            'cross_jaw_edges_after':0,'original_mpfb_asset_modified':False,
        },
        'dental_mapping_audit':{
            'status':'PASS_HELPER_GROUP_JAW_MAPPING_NOT_VISUAL_APPROVAL',
            'mesh_topology_modified':True,
            'modified_only_on_in_memory_export_copy':True,
            'face_count':3540,'mixed_jaw_faces':0,
            'lower_teeth_vertices':1884,'upper_teeth_vertices':1984,
        },
        'seamed_jaw_motion_audit':{
            'status':PASS,'lower_vertices':1884,'upper_vertices':1984,
        },
        'oral_motion_audit':{
            'jaw_open':{'status':'ORAL_MOTION_PRESENT_NOT_VISUALLY_APPROVED'},
        },
        'oral_corrective_audit':{
            'jaw_open':{'teeth':{
                'moved_vertices_gt_0_1_mm':1884,
                'stationary_vertices_lt_0_1_mm':1984,
            }},
        },
        'images':[{'filename':name} for name in POSE_IMAGES],
    }


class JawMotionTests(unittest.TestCase):
    def setUp(self):
        self.neutral=np.zeros((3868,3),dtype=float)
        self.opened=self.neutral.copy()
        self.opened[:1884,2]=-.016

    def test_realistic_lower_only_motion_passes_without_visual_approval(self):
        audit=audit_seamed_jaw_motion(self.neutral,self.opened,mask())
        self.assertEqual(audit['status'],PASS)
        self.assertEqual(audit['lower_moved_gt_0_1_mm'],1884)
        self.assertEqual(audit['upper_moved_gt_0_1_mm'],0)
        self.assertEqual(audit['mouth_contact'],'NOT_TESTED')

    def test_upper_jaw_motion_rejected(self):
        self.opened[1884:,2]=-.002
        audit=audit_seamed_jaw_motion(self.neutral,self.opened,mask())
        self.assertTrue(audit['status'].startswith('FAIL_'))

    def test_lower_jaw_inert_rejected(self):
        audit=audit_seamed_jaw_motion(self.neutral,self.neutral,mask())
        self.assertTrue(audit['status'].startswith('FAIL_'))

    def test_ambiguous_mask_rejected(self):
        wrong=mask()
        wrong[0]=.5
        with self.assertRaisesRegex(SeamedJawMotionError,'E_ID022_SEAM_MOTION_INPUT'):
            audit_seamed_jaw_motion(self.neutral,self.opened,wrong)


class HeadAStillRunnerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)/'head_a'
        self.data=report()

    def test_command_scoped_to_two_stills_head_a_opt_in(self):
        args=command('blender.exe','native-plan.json',self.folder)
        self.assertIn('demo_head_a',args)
        self.assertNotIn('demo_head_b',args)
        for flag in ('--seam-jaw-stills','--mhclo-dentition',
                     '--oral-correctives','--align-accessories',
                     '--audit-oral-motion'):
            self.assertIn(flag,args)
        self.assertNotIn('--rigged-seam-probe',args)

    def test_complete_contract_accepted_for_zip_packaging(self):
        with patch('tools.run_mpfb_seam_jaw_stills.check_png_dimensions'):
            self.assertTrue(validate_report(self.data,self.folder))

    def test_fake_pass_without_topology_change_rejected(self):
        self.data['dental_mapping_audit']['mesh_topology_modified']=False
        with self.assertRaisesRegex(SeamJawStillsError,'E_ID022_ORAL_CONTRACT'):
            validate_report(self.data,self.folder)

    def test_fake_pass_without_stable_upper_jaw_rejected(self):
        self.data['seamed_jaw_motion_audit']['status']='FAIL_SEAMED_JAW_MOTION_NOT_VISUAL_QA'
        with self.assertRaisesRegex(SeamJawStillsError,'E_ID022_ORAL_CONTRACT'):
            validate_report(self.data,self.folder)

    def test_extra_images_or_wrong_pose_rejected(self):
        self.data['images'].append({'filename':'three_quarter_jaw_open.png'})
        with self.assertRaisesRegex(SeamJawStillsError,'E_ID022_IMAGE_SET'):
            validate_report(self.data,self.folder)

    def test_two_image_zip_contains_only_review_evidence(self):
        class Completed:
            returncode=0
        def fake(argv,**kwargs):
            self.folder.mkdir()
            for name in POSE_IMAGES:
                (self.folder/name).write_bytes(b'test synthetic image')
            (self.folder/'anatomy_pose_report.json').write_text(
                json.dumps(self.data),encoding='utf-8')
            return Completed()
        with patch('tools.run_mpfb_seam_jaw_stills.check_png_dimensions'):
            _data,archive=run('blender.exe','native-plan.json',self.folder,
                              execute=fake)
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(
                set(bundle.namelist()),
                set(POSE_IMAGES)|{'anatomy_pose_report.json'})
        self.assertTrue(archive.is_file())


if __name__=='__main__':
    unittest.main()
