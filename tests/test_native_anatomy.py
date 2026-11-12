"""Isolated MPFB anatomy plan and preview runner; no Blender required."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
import zlib

from character.native_anatomy import (
    SCHEMA, REQUIRED, AnatomyPlanError, load_plan, validate_plan,
    verify_asset_file, resolve_native_assets,
)
from tools.run_native_anatomy_probe import (
    build_command, validate_output, run,
)

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'character/appearance/native_anatomy_demo.json'


def _png(width=480,height=720):
    def chunk(tag,data):
        return (struct.pack('>I',len(data))+tag+data+
                struct.pack('>I',zlib.crc32(tag+data)&0xffffffff))
    row=b'\x00'+b'\x26\x40\x55\xff'*width
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',
        width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(row*height))+chunk(b'IEND',b'')


class NativeAnatomyPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan=load_plan(DEFAULT)
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def test_default_plan_covers_exact_owner_anatomy(self):
        self.assertEqual(self.plan['schema'],SCHEMA)
        self.assertEqual(set(self.plan['assets']),set(REQUIRED))
        self.assertEqual(self.plan['assets']['eyes']['relative_path'],'high-poly/high-poly.mhclo')
        self.assertEqual(self.plan['assets']['teeth']['relative_path'],'teeth_base/teeth_base.mhclo')
        self.assertEqual(self.plan['assets']['tongue']['relative_path'],'tongue01/tongue01.mhclo')
    def test_rejects_unknown_asset_category(self):
        p=dict(self.plan,assets=dict(self.plan['assets'],hair=self.plan['assets']['eyes']))
        with self.assertRaisesRegex(AnatomyPlanError,'E_REQUIRED_ASSETS'):
            validate_plan(p)
    def test_rejects_path_escape(self):
        items=dict(self.plan['assets'])
        items['eyes']=dict(items['eyes'],relative_path='../secret.mhclo')
        with self.assertRaisesRegex(AnatomyPlanError,'E_ASSET_PATH_OR_HASH'):
            validate_plan(dict(self.plan,assets=items))
    def test_rejects_duplicate_json_key(self):
        p=self.root/'invalid.json'
        p.write_text('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(AnatomyPlanError,'E_DUPLICATE_KEY'):
            load_plan(p)
    def test_detects_tampered_asset_bytes(self):
        source=self.root/'eyes.mhclo'
        source.write_bytes(b'good')
        digest=hashlib.sha256(b'good').hexdigest()
        self.assertEqual(verify_asset_file(source,digest)['size_bytes'],4)
        source.write_bytes(b'BAD!')
        with self.assertRaisesRegex(AnatomyPlanError,'E_ASSET_HASH_MISMATCH'):
            verify_asset_file(source,digest)
    def test_resolves_three_files_against_verified_hashes(self):
        items={}
        files={}
        for category in REQUIRED:
            root=self.root/category
            root.mkdir()
            path=root/f'{category}.mhclo'
            path.write_bytes((category+' MPFB asset').encode())
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            items[category]={'relative_path':f'{category}/{category}.mhclo','sha256':digest}
            files[category]=path
        p=dict(self.plan,assets=items)
        def finder(fragment,*,asset_subdir):
            self.assertEqual(fragment,items[asset_subdir]['relative_path'])
            return str(files[asset_subdir])
        selected=resolve_native_assets(p,finder)
        self.assertEqual([s['category'] for s in selected],list(REQUIRED))
        self.assertEqual(selected[0]['material_type'],'PROCEDURAL_EYES')
        self.assertEqual(selected[1]['material_type'],'MAKESKIN')
    def test_missing_installed_asset_fails_before_blender_mutation(self):
        with self.assertRaisesRegex(AnatomyPlanError,'E_MISSING_INSTALLED_ASSET_eyes'):
            resolve_native_assets(self.plan,lambda fragment,*,asset_subdir: None)


class NativeAnatomyRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.out=self.root/'run'
    def fake_execute(self,argv,**kwargs):
        self.out.mkdir()
        images=[]
        for view,name in [('neutral_front','neutral_front.png'),
                          ('neutral_three_quarter','neutral_three_quarter.png')]:
            file=self.out/name
            file.write_bytes(_png())
            images.append({'view':view,'file':str(file.resolve()),'bytes':file.stat().st_size})
        data={'schema':'livynth.native-anatomy.attach-probe.v1',
              'status':'ATTACHED_NEUTRAL_ASSETS_PENDING_VISUAL_AND_EXPRESSION_QA',
              'existing_glbs_modified':False,'detailed_head_shape_applied':False,
              'rig_joint_count':163,'attachments':[
                  {'category':category,'vertices':100} for category in REQUIRED],
              'images':images}
        (self.out/'anatomy_probe.json').write_text(json.dumps(data))
    def test_command_uses_standalone_probe_not_original_exporter(self):
        cmd=build_command('blender.exe',DEFAULT,self.out)
        self.assertEqual(cmd[0],'blender.exe')
        self.assertIn('mpfb_native_anatomy_probe_blender.py',' '.join(cmd))
        self.assertNotIn('mpfb_headless_probe.py',' '.join(cmd))
    def test_simulated_complete_output_passes_structural_gate(self):
        data=run('fake-blender',DEFAULT,self.out,execute=self.fake_execute)
        self.assertEqual(data['status'],'ATTACHED_NEUTRAL_ASSETS_PENDING_VISUAL_AND_EXPRESSION_QA')
        self.assertFalse(data['existing_glbs_modified'])
    def test_missing_render_refused(self):
        self.fake_execute([],cwd=None,check=True)
        (self.out/'neutral_front.png').unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):
            validate_output(self.out)
    def test_failed_attachment_refused(self):
        self.fake_execute([],cwd=None,check=True)
        report=self.out/'anatomy_probe.json'
        data=json.loads(report.read_text())
        data['attachments'][1]['vertices']=0
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'E_ANATOMY_ATTACHMENTS'):
            validate_output(self.out)
    def test_existing_output_not_overwritten(self):
        self.out.mkdir()
        (self.out/'secret.txt').write_text('keep')
        with self.assertRaises(FileExistsError):
            run('fake',DEFAULT,self.out,execute=lambda *a,**k:self.fail('must not run'))
        self.assertEqual((self.out/'secret.txt').read_text(),'keep')


if __name__=='__main__':
    unittest.main()
