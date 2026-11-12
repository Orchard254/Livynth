"""IDENTITY-023: visibility restoration and strict four-render report contract."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.oral_asset_visibility import (
    VARIANTS, OralIsolationError, capture_oral_visibility)
from tools.run_mpfb_oral_isolation import (
    IsolationReviewError, FILES, SCOPE, STATUS, command, validate)


class DummyAsset:
    def __init__(self):
        self.hide_render=False


def valid_report():
    return {
        'schema':'livynth.anatomy-ab-render.v1',
        'status':STATUS,
        'character_id':'demo_head_a',
        'render_scope':SCOPE,
        'framing':'MOUTH_FOCUSED_FACE_CLOSEUP',
        'existing_glbs_modified':False,
        'dental_visual_quality':'PENDING_INDEPENDENT_REVIEW',
        'full_character_glb_export':'NOT_TESTED',
        'rig_joints':163,'native_body_vertices':13380,
        'native_quads':13378,'facial_morph_count':67,
        'seamed_render_copy_audit':{
            'status':'PASS_SEAMED_RENDER_COPY_STRUCTURE_NOT_VISUAL_QA',
            'original_mpfb_asset_modified':False,
            'seamed_faces':3540,
        },
        'seamed_jaw_motion_audit':{
            'status':'PASS_LOWER_JAW_MOTION_UPPER_STABLE_NOT_VISUAL_QA',
        },
        'images':[{'filename':x} for x in FILES],
        'oral_asset_visibility_audit':[
            {'filename':name+'.png','teeth_visible':not hide_teeth,
             'tongue_visible':not hide_tongue,'body_visible':True,
             'source_geometry_modified':False,
             'rendered_visual_inference':'PENDING_INDEPENDENT_REVIEW'}
            for name,hide_teeth,hide_tongue in VARIANTS
        ],
    }


class OralVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.teeth=DummyAsset()
        self.tongue=DummyAsset()
        self.assets={'teeth':self.teeth,'tongue':self.tongue}

    def test_four_variants_and_visibility_restored(self):
        states=[]
        def render(name):
            states.append((name,self.teeth.hide_render,self.tongue.hide_render))
            return {'filename':name+'.png'}
        images,audit=capture_oral_visibility(self.assets,render)
        self.assertEqual(states,list(VARIANTS))
        self.assertEqual([x['filename'] for x in images],list(FILES))
        self.assertEqual([x['filename'] for x in audit],list(FILES))
        self.assertFalse(self.teeth.hide_render)
        self.assertFalse(self.tongue.hide_render)

    def test_restore_both_assets_even_if_renderer_fails(self):
        def render(name):
            if name=='jaw_no_teeth':
                raise RuntimeError('simulated Blender failure')
            return {'filename':name+'.png'}
        with self.assertRaisesRegex(RuntimeError,'simulated Blender failure'):
            capture_oral_visibility(self.assets,render)
        self.assertFalse(self.teeth.hide_render)
        self.assertFalse(self.tongue.hide_render)

    def test_already_hidden_asset_rejected(self):
        self.tongue.hide_render=True
        with self.assertRaisesRegex(OralIsolationError,
                                    'E_ID023_ASSETS_NOT_BOTH_VISIBLE'):
            capture_oral_visibility(self.assets,lambda name:None)

    def test_same_asset_cannot_be_used_for_teeth_and_tongue(self):
        self.assets['tongue']=self.teeth
        with self.assertRaisesRegex(OralIsolationError,
                                    'E_ID023_ASSETS_NOT_BOTH_VISIBLE'):
            capture_oral_visibility(self.assets,lambda name:None)

    def test_wrong_render_filename_rejected_and_restored(self):
        with self.assertRaisesRegex(OralIsolationError,
                                    'E_ID023_UNEXPECTED_RENDER_FILENAME'):
            capture_oral_visibility(
                self.assets,lambda name:{'filename':'wrong.png'})
        self.assertFalse(self.teeth.hide_render)
        self.assertFalse(self.tongue.hide_render)


class IsolationReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)

    def test_command_uses_head_a_stills_pipeline_and_optin(self):
        flags=command('blender.exe','native-plan.json',self.out)
        self.assertIn('--oral-isolation',flags)
        self.assertIn('--seam-jaw-stills',flags)
        self.assertIn('--oral-correctives',flags)
        self.assertIn('demo_head_a',flags)
        self.assertNotIn('demo_head_b',flags)

    def test_valid_report_contract(self):
        with patch('tools.run_mpfb_oral_isolation.check_png_dimensions'):
            self.assertTrue(validate(valid_report(),self.out))

    def test_tongue_visibility_mislabel_rejected(self):
        report=valid_report()
        report['oral_asset_visibility_audit'][1]['tongue_visible']=True
        with patch('tools.run_mpfb_oral_isolation.check_png_dimensions') as check:
            with self.assertRaisesRegex(IsolationReviewError,
                                        'E_ID023_VISIBILITY_AUDIT'):
                validate(report,self.out)
            # Metadata must fail before any missing-image disk access.
            check.assert_not_called()

    def test_valid_metadata_still_requires_real_png_files(self):
        with self.assertRaises(FileNotFoundError):
            validate(valid_report(),self.out)

    def test_missing_still_is_rejected(self):
        report=valid_report()
        report['images'].pop()
        with self.assertRaisesRegex(IsolationReviewError,'E_ID023_IMAGE_SET'):
            validate(report,self.out)

    def test_failed_jaw_gate_not_accepted(self):
        report=valid_report()
        report['seamed_jaw_motion_audit']['status']='FAIL_SEAMED_JAW_MOTION_NOT_VISUAL_QA'
        with self.assertRaisesRegex(IsolationReviewError,'E_ID023_SEAM_GATE'):
            validate(report,self.out)

    def test_misleading_visual_approval_rejected(self):
        report=valid_report()
        report['dental_visual_quality']='PASS'
        with self.assertRaisesRegex(IsolationReviewError,'E_ID023_REPORT_CONTRACT'):
            validate(report,self.out)


if __name__=='__main__':
    unittest.main()
