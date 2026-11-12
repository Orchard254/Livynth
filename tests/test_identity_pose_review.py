"""Hermetic renderer-review contract, PNG content and orchestration QA."""
from array import array
import json
import struct
import tempfile
import unittest
from pathlib import Path
import zlib

from tools.identity_pose_review import (
    POSES,VIEW_POSES,CHARACTERS,SCHEMA,PoseReviewError,
    render_jobs,check_png_dimensions,raster_change,
    validate_character_report,gallery_html)
from tools.run_identity_pose_review import build_plan,run


def png_bytes(width=400,height=600):
    def chunk(tag,data):
        return (struct.pack('>I',len(data))+tag+data+
                struct.pack('>I',zlib.crc32(tag+data)&0xffffffff))
    header=struct.pack('>IIBBBBB',width,height,8,6,0,0,0)
    row=b'\x00'+b'\x15\x20\x30\xff'*width
    return (b'\x89PNG\r\n\x1a\n'
            +chunk(b'IHDR',header)
            +chunk(b'IDAT',zlib.compress(row*height,6))
            +chunk(b'IEND',b''))


def make_report(root,char,*,write_images=True):
    entries=[]
    for view,pose,weights in render_jobs():
        path=root/char/(view+'_'+pose+'.png')
        if write_images:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(png_bytes())
        entries.append({'view':view,'pose':pose,'weights':weights,
                        'path':str(path.resolve()),
                        'rendered_motion':None if pose=='neutral' else {
                            'status':'SIGNAL_PRESENT_NOT_VISUAL_APPROVAL',
                            'changed_face_samples':100,'total_face_samples':2500}})
    return {'schema':SCHEMA,'status':'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW',
            'character_id':char,'native_animation_interface':'EXPORTED_MORPH_SIGNAL_VERIFIED',
            'identity_likeness':'UNVERIFIED','renders':entries}


class PlanAndRasterTests(unittest.TestCase):
    def test_stable_plan_and_neutral_first_in_each_view(self):
        jobs=render_jobs()
        self.assertEqual(len(jobs),10)
        self.assertEqual([p for v,p,_ in jobs if v=='front'],list(POSES))
        for view in VIEW_POSES:
            self.assertEqual([p for v,p,_ in jobs if v==view][0],'neutral')
    def test_neutral_equal_image_cannot_be_mistaken_for_expression(self):
        neutral=array('f',[0.0])*(400*600*4)
        signal=raster_change(neutral,neutral,400,600)
        self.assertEqual(signal['status'],'NO_CONFIDENT_RENDERED_POSE_SIGNAL')
        self.assertEqual(signal['changed_face_samples'],0)
    def test_visible_face_pixels_detected(self):
        ref=array('f',[0.0])*(400*600*4)
        changed=ref[:]
        for y in range(280,304,2):
            for x in range(180,210,2):
                changed[(y*400+x)*4]=0.8
        signal=raster_change(ref,changed,400,600)
        self.assertEqual(signal['status'],'SIGNAL_PRESENT_NOT_VISUAL_APPROVAL')
        self.assertGreater(signal['changed_face_samples'],100)
    def test_background_only_does_not_count_as_face_motion(self):
        ref=array('f',[0.0])*(400*600*4)
        changed=ref[:]
        for y in range(0,40,2):
            for x in range(180,210,2):
                changed[(y*400+x)*4]=0.8
        signal=raster_change(ref,changed,400,600)
        self.assertEqual(signal['status'],'NO_CONFIDENT_RENDERED_POSE_SIGNAL')
    def test_nonfinite_pixel_rejected(self):
        ref=array('f',[0.0])*(400*600*4)
        altered=ref[:]
        altered[((300*400+180)*4)]=float('nan')
        with self.assertRaisesRegex(PoseReviewError,'E_RASTER_NONFINITE'):
            raster_change(ref,altered,400,600)


class ImageAndManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def test_real_png_crc_and_pixel_data_required(self):
        img=self.root/'good.png'
        img.write_bytes(png_bytes())
        self.assertEqual(check_png_dimensions(img,400,600),(400,600))
        with self.assertRaisesRegex(PoseReviewError,'E_PNG_DIMENSIONS'):
            check_png_dimensions(img,600,400)
    def test_corrupt_png_crc_rejected(self):
        img=self.root/'bad.png'
        data=bytearray(png_bytes())
        data[29]^=0x08
        img.write_bytes(data)
        with self.assertRaisesRegex(PoseReviewError,'E_PNG_CRC'):
            check_png_dimensions(img,400,600)
    def test_png_signature_only_cannot_pass(self):
        img=self.root/'signature.png'
        img.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\x00'*100)
        with self.assertRaises(PoseReviewError):
            check_png_dimensions(img,400,600)
    def test_missing_pose_fails_closed(self):
        report=make_report(self.root,'demo_head_a')
        report['renders']=report['renders'][:-1]
        with self.assertRaisesRegex(PoseReviewError,'E_MISSING_POSE_RENDERS'):
            validate_character_report(report,self.root,'demo_head_a')
    def test_pose_with_no_raster_signal_fails(self):
        report=make_report(self.root,'demo_head_a')
        report['renders'][1]['rendered_motion']['status']='NO_CONFIDENT_RENDERED_POSE_SIGNAL'
        with self.assertRaisesRegex(PoseReviewError,'E_RENDERED_POSE_INERT'):
            validate_character_report(report,self.root,'demo_head_a')
    def test_complete_report_passes_and_html_has_all_images(self):
        reports=[make_report(self.root,char) for char in CHARACTERS]
        for char,rep in zip(CHARACTERS,reports):
            self.assertTrue(validate_character_report(rep,self.root,char))
        html=gallery_html({'schema':SCHEMA,'status':'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW'})
        self.assertEqual(html.count('<img '),20)
        for char in CHARACTERS:
            self.assertIn(f'{char}/three_quarter_jaw_open.png',html)


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder=self.root/'existing_glbs'
        self.folder.mkdir()
        for char in CHARACTERS:
            (self.folder/(char+'.glb')).write_bytes(b'glTF dummy for fake executor')
        self.out=self.root/'pose_review'
    def verify_stub(self,a,b):
        self.assertEqual(a.name,'demo_head_a.glb')
        self.assertEqual(b.name,'demo_head_b.glb')
        return {'status':'PASS_NONZERO_EXPORTED_MORPH_SIGNAL_NOT_VISUAL_ANIMATION'}
    def fake_blender(self,argv,**kwargs):
        char=argv[argv.index('--character')+1]
        output=Path(argv[argv.index('--out')+1])
        report=make_report(output.parent,char)
        (output/'render_report.json').write_text(json.dumps(report),encoding='utf-8')
    def test_plan_reuses_existing_binaries_not_exporter(self):
        jobs=build_plan(self.folder,self.out,'blender.exe')
        self.assertEqual(len(jobs),2)
        for char,argv in jobs:
            self.assertEqual(argv[0],'blender.exe')
            self.assertNotIn('mpfb_headless_probe.py',argv)
            self.assertEqual(argv[argv.index('--character')+1],char)
    def test_full_fake_orchestration_builds_gallery(self):
        rep=run(self.folder,self.out,'blender.exe',execute=self.fake_blender,
                inspect_glbs=self.verify_stub)
        self.assertEqual(rep['status'],'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW')
        self.assertTrue((self.out/'index.html').is_file())
        self.assertEqual(rep['renders_per_character'],10)
    def test_existing_output_refused_before_any_render(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            run(self.folder,self.out,'blender.exe',execute=self.fake_blender,
                inspect_glbs=self.verify_stub)
    def test_preflight_failure_stops_before_render(self):
        def invalid(*args):
            return {'status':'REJECTED_MORPH'}
        with self.assertRaisesRegex(ValueError,'E_MORPH_PREFLIGHT'):
            run(self.folder,self.out,'blender.exe',execute=self.fake_blender,
                inspect_glbs=invalid)
        self.assertFalse(self.out.exists())


if __name__=='__main__':
    unittest.main()
