import json
import math
import tempfile
import unittest
from pathlib import Path
from character.identity_recipe import (InvalidIdentityRecipe, load_recipe,validate_recipe,
    apply_macro_overrides, recipe_sha256, neutral_positions_sha256, neutral_topology_sha256)
from tools.identity_compare import compare,IdentityComparisonError
ROOT=Path(__file__).resolve().parents[1]

def sample(name,version,fingerprint,morphs=67):
    return {'assertions_passed':True,'errors':[],
            'identity_recipe':{'source':'manual_parameters','character_id':name,'sha256':version},
            'neutral_identity_geometry':{'positions_sha256':fingerprint,'topology_sha256':'topoA','vertex_count':13380,'quad_count':13378},
            'glb_audit':{'joint_count':163,'morph_targets_in_exported_glb':morphs,'skin_present':True,
                'target_names':['eyeBlinkLeft','eyeBlinkRight','viseme_aa'],
                'skin_joint_names':['root','head','jaw'],
                'character_primitives':[{'has_uv':True}]}}

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

    def test_topology_hash_order_sensitive(self):
        faces=[(0,1,2,3),(4,5,6,7),(8,9,10,11),(12,13,14,15)]
        self.assertNotEqual(neutral_topology_sha256(faces),neutral_topology_sha256(faces[::-1]))
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_TOPOLOGY_QUADS'):
            neutral_topology_sha256(faces[:3]+[(1,2,3)])

class ExporterArgumentTests(unittest.TestCase):
    def test_existing_default_cli_unchanged(self):
        import sys
        from unittest.mock import patch
        from tools.mpfb_headless_probe import _parse_args
        with patch.object(sys,'argv',['blender','--','--out','output/default.glb']):
            args=_parse_args()
        self.assertEqual(args[0],'output/default.glb')
        self.assertIsNone(args[-1])

    def test_identity_recipe_reaches_exporter_cli(self):
        import sys
        from unittest.mock import patch
        from tools.mpfb_headless_probe import _parse_args
        with patch.object(sys,'argv',['blender','--','--identity-recipe','demo_b.json']):
            self.assertEqual(_parse_args()[-1],'demo_b.json')

    def test_identity_recipe_and_stage1_constraints_fail_closed(self):
        import sys
        from unittest.mock import patch
        from tools.mpfb_headless_probe import _parse_args
        with patch.object(sys,'argv',['blender','--','--identity-recipe','demo_a.json',
                                        '--stage1-constraints','old_fit.json']):
            with self.assertRaisesRegex(ValueError,'cannot be combined'):
                _parse_args()


class ComparisonTests(unittest.TestCase):
    def test_distinct_verified_structure(self):
        self.assertIn('NOT_LIKENESS',compare(sample('a','a','hashA'),sample('b','b','hashB'))['status'])
    def test_same_geometry_fails(self):
        with self.assertRaisesRegex(IdentityComparisonError,'E_IDENTICAL_GEOMETRY'):
            compare(sample('a','a','same'),sample('b','b','same'))
    def test_lost_face_morph_fails(self):
        with self.assertRaisesRegex(IdentityComparisonError,'E_RIG_MORPH'):
            compare(sample('a','a','one'),sample('b','b','two',morphs=66))
    def test_different_topology_fails(self):
        a=sample('a','a','one');b=sample('b','b','two')
        b['neutral_identity_geometry']['topology_sha256']='different'
        with self.assertRaisesRegex(IdentityComparisonError,'E_DIFFERENT_TOPOLOGY'):
            compare(a,b)
    def test_different_target_names_fails(self):
        a=sample('a','a','one');b=sample('b','b','two')
        b['glb_audit']['target_names']=['other']
        with self.assertRaisesRegex(IdentityComparisonError,'E_MORPH_NAME_MISMATCH'):
            compare(a,b)
    def test_head_shape_audit_same_source_accepted(self):
        a=sample('a','recipeA','outA')
        b=sample('b','recipeB','outB')
        for candidate in (a,b):
            audit={
                'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS',
                'min_triangle_area_ratio':0.61,
                'max_displacement_m':0.010,
                'moved_vertices_gt_0_1_mm':3500,
                'source_positions_sha256':'verified-neutral-sha',
                'output_positions_sha256':candidate['neutral_identity_geometry']['positions_sha256'],
            }
            candidate['identity_head_shape']=audit
        self.assertIn('PASS_DISTINCT',compare(a,b)['status'])

    def test_head_shape_audit_rejects_different_source(self):
        a=sample('a','recipeA','outA')
        b=sample('b','recipeB','outB')
        for candidate,source_sha in ((a,'baseA'),(b,'baseB')):
            candidate['identity_head_shape']={
                'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS',
                'min_triangle_area_ratio':0.6,'max_displacement_m':0.01,
                'moved_vertices_gt_0_1_mm':3500,
                'source_positions_sha256':source_sha,
                'output_positions_sha256':candidate['neutral_identity_geometry']['positions_sha256'],
            }
        with self.assertRaisesRegex(IdentityComparisonError,'E_HEAD_SOURCE_DIFFERENT'):
            compare(a,b)

    def test_head_shape_missing_second_audit_rejected(self):
        a=sample('a','recipeA','outA')
        b=sample('b','recipeB','outB')
        a['identity_head_shape']={'status':'PASS_LOCAL_QUADS_NOT_GLOBAL_INTERSECTIONS'}
        with self.assertRaisesRegex(IdentityComparisonError,'E_HEAD_SHAPE_AUDIT_MISSING'):
            compare(a,b)

    def test_failed_export_fails(self):
        a=sample('a','a','one');a['assertions_passed']=False
        with self.assertRaisesRegex(IdentityComparisonError,'E_EXPORT_AUDIT'):
            compare(a,sample('b','b','two'))
if __name__=='__main__': unittest.main()
