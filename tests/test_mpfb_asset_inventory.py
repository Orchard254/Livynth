"""MPFB native asset-inventory readiness, privacy and no-runner false passes."""
import json
import tempfile
import unittest
from pathlib import Path
from tools.mpfb_asset_inventory import (
    CATEGORIES,InventoryError,inventory_category,make_inventory)
from tools.probe_mpfb_assets import build_command,run

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def make(self,category,name,contents=b'fake asset'):
        root=self.root/category
        root.mkdir(exist_ok=True)
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(contents)
        return root
    def test_reports_present_and_missing_anatomy_separately(self):
        groups={x:[] for x in CATEGORIES}
        for cat in ('eyes','teeth','tongue'):
            groups[cat]=[self.make(cat,f'{cat}.mhclo')]
        report=make_inventory(groups,mpfb_version='2.0.18',blender_version='4.5.10')
        self.assertEqual(report['status'],'ASSETS_AVAILABLE_FOR_FITTING_TESTS')
        self.assertEqual(report['missing_required_for_anatomy'],[])
        self.assertEqual(report['assets_fitted_to_body'],'NOT_TESTED')
        self.assertEqual(sum(v['count'] for v in report['categories'].values()),3)
    def test_missing_asset_fails_readiness_only(self):
        groups={x:[] for x in CATEGORIES}
        groups['eyes']=[self.make('eyes','eyes.mhclo')]
        report=make_inventory(groups,mpfb_version='unknown',blender_version='4.5')
        self.assertEqual(report['status'],'MISSING_REQUIRED_ANATOMY_ASSETS')
        self.assertEqual(report['missing_required_for_anatomy'],['teeth','tongue'])
    def test_no_absolute_path_leaked(self):
        root=self.make('eyes','nested/eyeballs.mhclo')
        entry=inventory_category('eyes',[root])[0]
        self.assertEqual(entry['relative_path'],'nested/eyeballs.mhclo')
        self.assertEqual(len(entry['sha256']),64)
        self.assertNotIn(str(self.root),json.dumps(entry))
    def test_wrong_extension_not_counted(self):
        root=self.make('eyes','readme.txt')
        self.assertEqual(inventory_category('eyes',[root]),[])
    def test_ignores_symlink(self):
        root=self.root/'eyes'
        root.mkdir()
        external=self.root/'secret.mhclo'
        external.write_bytes(b'secret')
        try:
            (root/'linked.mhclo').symlink_to(external)
        except (OSError,NotImplementedError):
            self.skipTest('Symlinks not available')
        self.assertEqual(inventory_category('eyes',[root]),[])
    def test_rejects_unknown_category_and_schema(self):
        with self.assertRaisesRegex(InventoryError,'E_ASSET_CATEGORY'):
            inventory_category('unknown',[])
        with self.assertRaisesRegex(InventoryError,'E_INVENTORY_CATEGORY_SET'):
            make_inventory({'eyes':[]},mpfb_version='',blender_version='')
    def test_rejects_asset_limit(self):
        root=self.make('eyes','first.mhclo')
        (root/'second.mhclo').write_bytes(b'b')
        with self.assertRaisesRegex(InventoryError,'E_ASSET_LIMIT'):
            inventory_category('eyes',[root],per_category_limit=1)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dest=Path(self.temp.name)/'inventory.json'
    def test_one_command_uses_blender_and_no_model_exporter(self):
        argv=build_command('blender.exe',self.dest)
        self.assertEqual(argv[0],'blender.exe')
        self.assertIn('--background',argv)
        self.assertIn('mpfb_asset_probe_blender.py',' '.join(argv))
        self.assertNotIn('mpfb_headless_probe.py',' '.join(argv))
    def test_missing_blender_report_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'did not write'):
            run('fake',self.dest,execute=lambda *a,**k:None)
    def test_status_does_not_pretend_assets_attached(self):
        def fake(argv,**kwargs):
            self.dest.write_text(json.dumps({
                'schema':'livynth.mpfb.appearance-inventory.v1',
                'status':'MISSING_REQUIRED_ANATOMY_ASSETS',
                'assets_fitted_to_body':'NOT_TESTED',
                'missing_required_for_anatomy':['teeth']}))
        data=run('fake',self.dest,execute=fake)
        self.assertEqual(data['status'],'MISSING_REQUIRED_ANATOMY_ASSETS')
        self.assertEqual(data['assets_fitted_to_body'],'NOT_TESTED')
    def test_existing_inventory_not_overwritten(self):
        self.dest.write_text('keep')
        with self.assertRaises(FileExistsError):
            run('fake',self.dest,execute=lambda *a,**k:self.fail('should not run'))
        self.assertEqual(self.dest.read_text(),'keep')

if __name__=='__main__':
    unittest.main()
