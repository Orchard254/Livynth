import json
import tempfile
import unittest
from pathlib import Path
from tools.run_identity_ab import make_ab_plan,run
ROOT=Path(__file__).resolve().parents[1]

class ABRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/'output'
        self.a=ROOT/'character/recipes/demo_a.json'
        self.b=ROOT/'character/recipes/demo_b.json'
    def test_produces_two_isolated_build_commands(self):
        steps=make_ab_plan(blender='blender.exe',out=self.out,a=self.a,b=self.b)
        self.assertEqual(len(steps),2)
        self.assertNotEqual(steps[0][1],steps[1][1])
        for argv,report in steps:
            self.assertIn('--identity-recipe',argv)
            self.assertIn('--json',argv)
            self.assertEqual(argv[0],'blender.exe')
            self.assertEqual(report.parent,self.out)
    def test_same_recipe_refuses_two_character_claim(self):
        with self.assertRaisesRegex(ValueError,'E_NOT_TWO_DISTINCT_RECIPES'):
            make_ab_plan(blender='blender',out=self.out,a=self.a,b=self.a)
    def test_never_overwrites_existing_outputs(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            run(blender='fake',out=self.out,a=self.a,b=self.b,
                execute=lambda *args,**kwargs: self.fail('should not run'))
    def test_export_failure_does_not_call_second_export(self):
        calls=[]
        def fail(argv,**kwargs):
            calls.append(argv)
            raise OSError('simulated blender failure')
        with self.assertRaisesRegex(OSError,'simulated blender failure'):
            run(blender='fake',out=self.out,a=self.a,b=self.b,execute=fail)
        self.assertEqual(len(calls),1)
    def test_missing_report_does_not_pass(self):
        with self.assertRaises(FileNotFoundError):
            run(blender='fake',out=self.out,a=self.a,b=self.b,execute=lambda *args,**kwargs: None)
if __name__=='__main__': unittest.main()
