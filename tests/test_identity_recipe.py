import json
import math
import tempfile
import unittest
from pathlib import Path
from character.identity_recipe import (InvalidIdentityRecipe, load_recipe,validate_recipe,
    apply_macro_overrides, recipe_sha256, neutral_positions_sha256)
from tools.identity_compare import compare,IdentityComparisonError
ROOT=Path(__file__).resolve().parents[1]

def sample(name,version,fingerprint,morphs=67):
    return {'assertions_passed':True,'errors':[],
            'identity_recipe':{'source':'manual_parameters','character_id':name,'sha256':version},
            'neutral_identity_geometry':{'positions_sha256':fingerprint,'vertex_count':13380},
            'glb_audit':{'joint_count':163,'morph_targets_in_exported_glb':morphs,'skin_present':True}}

class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.a=load_recipe(ROOT/'character/recipes/demo_a.json')
        self.b=load_recipe(ROOT/'character/recipes/demo_b.json')
    def test_distinct_recipes(self):
        self.assertNotEqual(recipe_sha256(self.a),recipe_sha256(self.b))
        self.assertNotEqual(self.a['macros']['gender'],self.b['macros']['gender'])
    def test_hash_order_invariant(self):
        self.assertEqual(recipe_sha256(self.a),recipe_sha256(dict(reversed(list(self.a.items())))))
    def test_defaults_not_mutated(self):
        defaults={'gender':.5,'age':.5,'height':.5,'muscle':.5,'weight':.5,
                  'proportions':.5,'race':{'african':0,'asian':0,'caucasian':1},'cupsize':.5}
        original=json.loads(json.dumps(defaults))
        result=apply_macro_overrides(defaults,self.b['macros'])
        self.assertEqual(defaults,original)
        self.assertEqual(result['cupsize'],defaults['cupsize'])
        result['race']['caucasian']=0
        self.assertEqual(defaults['race']['caucasian'],1)
    def test_unsupported_image_source_rejected(self):
        bad=dict(self.a,source='image_estimate')
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_SOURCE_UNSUPPORTED'):validate_recipe(bad)
    def test_unknown_macro_rejected(self):
        bad=dict(self.a,macros=dict(self.a['macros'],nose_width=.3))
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_MACRO_FIELDS'):validate_recipe(bad)
    def test_invalid_scalar_rejected(self):
        for v in (True,False,'0.5',float('nan'),float('inf'),-0.1,1.01):
            with self.subTest(v=v),self.assertRaises(InvalidIdentityRecipe):
                validate_recipe(dict(self.a,macros=dict(self.a['macros'],age=v)))
    def test_race_requires_normalization(self):
        bad=dict(self.a,macros=dict(self.a['macros'],race={'african':.2,'asian':.2,'caucasian':.2}))
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_RACE_SUM'):validate_recipe(bad)
    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.json';path.write_text('{"schema":"x","schema":"y"}')
            with self.assertRaisesRegex(InvalidIdentityRecipe,'E_DUPLICATE_JSON_KEY'):load_recipe(path)
    def test_reject_claim_of_likeness(self):
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_RECIPE_FIELDS'):
            validate_recipe(dict(self.a,likeness_pass=True))
    def test_missing_mpfb_macro(self):
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_MACRO_NOT_SUPPORTED_BY_MPFB'):
            apply_macro_overrides({'gender':.5},self.a['macros'])
    def test_neutral_sha_sensitive_to_vertex_order(self):
        coords=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
        self.assertNotEqual(neutral_positions_sha256(coords),neutral_positions_sha256(coords[::-1]))
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_POSITION_NONFINITE'):
            neutral_positions_sha256(coords[:3]+[(math.nan,0,1)])

class ComparisonTests(unittest.TestCase):
    def test_distinct_verified_structure(self):
        self.assertIn('NOT_LIKENESS',compare(sample('a','a','hashA'),sample('b','b','hashB'))['status'])
    def test_same_geometry_fails(self):
        with self.assertRaisesRegex(IdentityComparisonError,'E_IDENTICAL_GEOMETRY'):
            compare(sample('a','a','same'),sample('b','b','same'))
    def test_lost_face_morph_fails(self):
        with self.assertRaisesRegex(IdentityComparisonError,'E_RIG_MORPH'):
            compare(sample('a','a','one'),sample('b','b','two',morphs=66))
    def test_failed_export_fails(self):
        a=sample('a','a','one');a['assertions_passed']=False
        with self.assertRaisesRegex(IdentityComparisonError,'E_EXPORT_AUDIT'):
            compare(a,sample('b','b','two'))
if __name__=='__main__': unittest.main()
