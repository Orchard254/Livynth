"""Pure numeric head identity controls, including shape and fold negative controls."""
import math
import unittest
from pathlib import Path
import numpy as np
from character.head_shape import (validate_controls,InvalidHeadShape,displacement_field,
                                  apply_head_shape,check_deformation)
from character.identity_recipe import (load_recipe,validate_recipe,InvalidIdentityRecipe,recipe_sha256,SCHEMA,SCHEMA_V2)
ROOT=Path(__file__).resolve().parents[1]

class RecipeV2Tests(unittest.TestCase):
    def setUp(self):
        self.a=load_recipe(ROOT/'character/recipes/demo_head_a.json')
        self.b=load_recipe(ROOT/'character/recipes/demo_head_b.json')
    def test_variation_reuses_exact_same_mpfb_macros(self):
        self.assertEqual(self.a['macros'],self.b['macros'])
        self.assertNotEqual(self.a['head_shape'],self.b['head_shape'])
        self.assertNotEqual(recipe_sha256(self.a),recipe_sha256(self.b))
    def test_legacy_v1_backwards_compatible(self):
        legacy=load_recipe(ROOT/'character/recipes/demo_a.json')
        self.assertEqual(legacy['schema'],SCHEMA)
        self.assertNotIn('head_shape',legacy)
    def test_v2_requires_shape(self):
        bad=dict(self.a);del bad['head_shape']
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_RECIPE_FIELDS'):
            validate_recipe(bad)
    def test_v1_rejects_unannounced_extra_shape(self):
        bad=dict(self.a,schema=SCHEMA)
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_RECIPE_FIELDS'):
            validate_recipe(bad)
    def test_rejects_false_likeness_source(self):
        bad=dict(self.a,source='auto_from_images')
        with self.assertRaisesRegex(InvalidIdentityRecipe,'E_SOURCE_UNSUPPORTED'):
            validate_recipe(bad)

class HeadControlTests(unittest.TestCase):
    def test_finite_bounded_controls(self):
        for value in (True,False,float('nan'),float('inf'),1.01,-1.01,'0.5'):
            with self.subTest(value=value),self.assertRaises(InvalidHeadShape):
                validate_controls({'cranial_width':value})
    def test_unsupported_morph_rejected(self):
        with self.assertRaisesRegex(InvalidHeadShape,'E_HEAD_CONTROL_KEYS'):
            validate_controls({'hair_density':0.5})
    def test_empty_morph_rejected(self):
        with self.assertRaisesRegex(InvalidHeadShape,'E_HEAD_CONTROL_KEYS'):
            validate_controls({})
    def test_zero_coefficients_never_move_anything(self):
        p=np.array([[0,0,0],[-0.1,-0.1,1.5],[0.1,0,1.7],[0,0,1.8]],dtype=float)
        d=displacement_field(p,{'cranial_width':0.0,'nose_projection':0.0})
        self.assertEqual(int(np.count_nonzero(d)),0)
        self.assertTrue(np.array_equal(p,p+d))
    def test_no_source_mutation(self):
        p=np.array([[0,0,0],[-0.06,-0.15,1.6],[0.06,-0.15,1.6],[0,0,1.747]],dtype=float)
        copy=p.copy()
        d=displacement_field(p,{'cranial_width':0.7,'nose_projection':0.8})
        np.testing.assert_array_equal(p,copy)
        self.assertEqual(d.shape,p.shape)
    def test_symmetry_of_nose_projection(self):
        p=np.array([[0,0,0],[-.02,-.15,1.60],[.02,-.15,1.60],[0,0,1.75]],dtype=float)
        d=displacement_field(p,{'nose_projection':0.8})
        self.assertAlmostEqual(d[1,1],d[2,1],places=12)
    def test_input_validation(self):
        with self.assertRaisesRegex(InvalidHeadShape,'E_HEAD_MESH_INPUT'):
            displacement_field(np.zeros((3,3)),{'cranial_width':1})
        with self.assertRaisesRegex(InvalidHeadShape,'E_HEAD_BODY_HEIGHT'):
            displacement_field(np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],dtype=float),{'cranial_width':1})
    def test_can_detect_flipped_triangle(self):
        p=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],
                    [0,0,1],[1,0,1],[1,1,1],[0,1,1]],dtype=float)
        quads=np.array([[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5]])
        dest=p.copy(); dest[[0,1]]=dest[[1,0]]
        with self.assertRaises(InvalidHeadShape):
            check_deformation(p,dest,quads)
    def test_rejects_malformed_quad_indices(self):
        p=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],dtype=float)
        with self.assertRaisesRegex(InvalidHeadShape,'E_HEAD_QUAD_INDICES'):
            check_deformation(p,p,np.array([[0,1,2,99]]*4))

if __name__=='__main__':unittest.main()
