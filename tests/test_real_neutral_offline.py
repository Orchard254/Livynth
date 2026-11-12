"""Optional real-neutral deformation proof (requires owner's private NPZ ZIP).

No photograph, GLB, or owner-provided binary is committed to the repository.
Set LIVYNTH_NATIVE_NEUTRAL_ZIP if the owner uses a different archive path.
"""
import io
import os
from pathlib import Path
import unittest
import zipfile
import numpy as np
from character.head_shape import apply_head_shape
from character.identity_recipe import load_recipe,neutral_positions_sha256
ROOT=Path(__file__).resolve().parents[1]
REFZIP=Path(os.getenv('LIVYNTH_NATIVE_NEUTRAL_ZIP',str(ROOT/'output/c001_geo05/stage1_review.zip')))

@unittest.skipUnless(REFZIP.is_file(),'Requires owner-supplied neutral_mesh.npz ZIP')
class RealNeutralProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(REFZIP) as archive:
            with np.load(io.BytesIO(archive.read('neutral_mesh.npz')),allow_pickle=False) as mesh:
                cls.p=mesh['vertices'].copy();cls.q=mesh['quads'].copy()
    def test_real_source_fingerprint(self):
        self.assertEqual(neutral_positions_sha256(self.p),
            '64b001da1ec4a4094cfa7ce1da3aee3b2a9da7d570492c6a56d76e78a47eb542')
        self.assertEqual(self.p.shape,(13380,3))
        self.assertEqual(self.q.shape,(13378,4))
    def test_two_distinct_reversible_geometries_same_connectivity(self):
        recipe_a=load_recipe(ROOT/'character/recipes/demo_head_a.json')
        recipe_b=load_recipe(ROOT/'character/recipes/demo_head_b.json')
        self.assertEqual(recipe_a['macros'],recipe_b['macros'])
        before=neutral_positions_sha256(self.p)
        a,qa=apply_head_shape(self.p,self.q,recipe_a['head_shape'])
        b,qb=apply_head_shape(self.p,self.q,recipe_b['head_shape'])
        self.assertNotEqual(neutral_positions_sha256(a),neutral_positions_sha256(b))
        self.assertEqual(neutral_positions_sha256(self.p),before)
        self.assertGreater(qa['moved_vertices_gt_0_1_mm'],1000)
        self.assertGreater(qb['moved_vertices_gt_0_1_mm'],1000)
        self.assertGreater(qa['min_triangle_area_ratio'],0.4)
        self.assertGreater(qb['min_triangle_area_ratio'],0.4)
        self.assertLess(max(qa['max_displacement_m'],qb['max_displacement_m']),.025)
        self.assertGreater(np.linalg.norm(a-b,axis=1).max(),.010)
if __name__=='__main__':unittest.main()
