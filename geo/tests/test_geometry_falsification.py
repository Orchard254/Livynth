"""Geometry-only canaries; no image pixels, texture or Blender required."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from geo.geometry_falsification import (
    Geometry, audit, band_widths, geometry_delta, head_mask, inventory,
    load_geometry, rejects_shape, rigid_align_without_scaling,
    warp_wrong_identity,
)


def sphere(radius=(.09,.13,.08), count=(42,26)):
    # Dense ellipsoid-like head: enough vertices across every vertical band.
    n_u, n_v = count
    verts = []
    for j in range(1,n_v):
        phi = np.pi * j / n_v
        for k in range(n_u):
            theta = 2 * np.pi * k / n_u
            verts.append([radius[0] * np.sin(phi) * np.cos(theta),
                          .13 + radius[1] * np.cos(phi),
                          radius[2] * np.sin(phi) * np.sin(theta)])
    # Face indexing not relevant to drift but valid for GLB export integration.
    faces=[]
    for j in range(n_v-2):
        for k in range(n_u):
            a=j*n_u+k; b=j*n_u+(k+1)%n_u
            faces.extend([(a,b,a+n_u), (b,b+n_u,a+n_u)])
    return np.asarray(verts, float), np.asarray(faces, int)


class GeometryFalsificationTests(unittest.TestCase):
    def setUp(self):
        self.v, self.f = sphere()
        self.g = Geometry(self.v,self.f,'head','head','fake-sha')
        self.mask = head_mask(self.v,1,0,.26)

    def test_correct_canary_rejected_and_unchanged_passed(self):
        r=audit(self.g,1,0,.26)
        self.assertTrue(r['positive_control_wrong_identity']['rejected'])
        self.assertFalse(r['negative_control_unchanged_identity']['rejected'])
        self.assertTrue(r['falsification_gate_pass'])
        self.assertEqual(r['identity_likeness_gate'],'NOT_EVALUATED')
        self.assertTrue(r['no_materials_used'])

    def test_similarity_scaling_is_not_allowed(self):
        scaled=self.v*1.18
        d=geometry_delta(self.v,scaled,self.f,self.f,self.mask,.26,1,0,.26)
        self.assertGreater(d['p95_displacement_over_head_height'],.02)
        self.assertTrue(rejects_shape(d))

    def test_rotation_and_translation_not_rejected(self):
        r=np.array([[0,-1,0],[1,0,0],[0,0,1]],float)
        transformed=self.v@r+np.array([.24,1.25,.30])
        d=geometry_delta(self.v,transformed,self.f,self.f,self.mask,.26,1,0,.26)
        self.assertLess(d['p95_displacement_over_head_height'],1e-6)
        self.assertFalse(rejects_shape(d))

    def test_canary_changes_real_geometry(self):
        wrong=warp_wrong_identity(self.v,1,0,.26,1.18)
        self.assertGreater(np.max(np.linalg.norm(wrong-self.v,axis=1)),.01)
        d=geometry_delta(self.v,wrong,self.f,self.f,self.mask,.26,1,0,.26)
        self.assertTrue(rejects_shape(d))
        self.assertGreater(d['absolute_width_delta_max'],.01)

    def test_hidden_surface_distortion_with_identical_outer_silhouette(self):
        # A front-projected photo and coarse outline cannot observe this change:
        # move only interior/front-facing geometry, leaving extrema unchanged.
        changed=self.v.copy()
        interior=((changed[:,2] > .034) & (np.abs(changed[:,0]) < .063) &
                  (changed[:,1] > .042) & (changed[:,1] < .22))
        self.assertGreater(np.count_nonzero(interior),70)
        changed[interior,2] += .012
        # Same front bounding silhouette in X/Y, different physical 3D depth.
        np.testing.assert_allclose(self.v[:,:2].min(0), changed[:,:2].min(0))
        np.testing.assert_allclose(self.v[:,:2].max(0), changed[:,:2].max(0))
        d=geometry_delta(self.v,changed,self.f,self.f,self.mask,.26,1,0,.26)
        self.assertTrue(rejects_shape(d))
        self.assertGreater(d['p95_displacement_over_head_height'],.006)

    def test_topology_corruption_rejected(self):
        with self.assertRaisesRegex(ValueError,'correspondence'):
            geometry_delta(self.v,self.v,self.f,self.f[::-1],self.mask,.26,1,0,.26)

    def test_wrong_head_band_rejected(self):
        with self.assertRaisesRegex(ValueError,'Head-range'):
            head_mask(self.v,1,100,200)
        with self.assertRaisesRegex(ValueError,'lower < upper'):
            head_mask(self.v,1,.3,.1)

    def test_geometry_roundtrip_real_glb(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'head.glb'
            trimesh.Trimesh(vertices=self.v,faces=self.f,process=False).export(p)
            inv=inventory(p)
            self.assertEqual(len(inv),1)
            loaded=load_geometry(p,None)
            self.assertEqual(len(loaded.vertices),len(self.v))
            self.assertEqual(len(loaded.faces),len(self.f))
            report=audit(loaded,1,0,.26)
            self.assertTrue(report['falsification_gate_pass'])

    def test_multimesh_requires_explicit_selection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'two.glb'; scene=trimesh.Scene()
            scene.add_geometry(trimesh.Trimesh(vertices=self.v,faces=self.f,process=False),geom_name='head')
            scene.add_geometry(trimesh.creation.box(),geom_name='box')
            scene.export(p)
            with self.assertRaisesRegex(ValueError,'Expected one'):
                load_geometry(p,None)
            self.assertEqual(len(load_geometry(p,'head').vertices),len(self.v))

    def test_nopass_claim_when_candidate_present(self):
        r=audit(self.g,1,0,.26,self.g)
        self.assertFalse(r['candidate']['geometry_change_detected'])
        self.assertEqual(r['candidate']['identity_likeness_gate'],'NOT_EVALUATED')


if __name__=='__main__':
    unittest.main()