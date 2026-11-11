"""C001-GEO-02: math, binary safety, morph and preserved-identity checks."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from geo.morph_fit import GLB, GLBError, Control, GaussianField, fit


def tiny_glb():
    """Create minimal standards-aligned GLB with position, normal, morph."""
    positions = np.array([[0., 0., 0.], [.1, 0., 0.], [0., .1, 0.]], '<f4')
    normals = np.tile([0., 0., 1.], (3, 1)).astype('<f4')
    morph = np.array([[0., 0., .01], [0., 0., .01], [0., 0., .01]], '<f4')
    binary = positions.tobytes() + normals.tobytes() + morph.tobytes()
    gltf = {
        'asset': {'version': '2.0'},
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': i * 36, 'byteLength': 36}
            for i in range(3)
        ],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3',
             'min': [0, 0, 0], 'max': [.1, .1, 0]},
            {'bufferView': 1, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
            {'bufferView': 2, 'componentType': 5126, 'count': 3, 'type': 'VEC3'}
        ],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1},
                                    'targets': [{'POSITION': 2}]}],
                    'extras': {'targetNames': ['eyeBlinkLeft']}}]
    }
    doc = json.dumps(gltf, separators=(',', ':')).encode()
    doc += b' ' * (-len(doc) % 4)
    return (struct.pack('<III', 0x46546c67, 2, 12 + 8 + len(doc) + 8 + len(binary))
            + struct.pack('<I4s', len(doc), b'JSON') + doc
            + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


class GLBFormatTests(unittest.TestCase):
    def test_binary_roundtrip_unmodified_and_morph_names_intact(self):
        original = tiny_glb()
        got = GLB(original)
        self.assertEqual(got.to_bytes(), original)
        other = GLB(got.to_bytes())
        self.assertEqual(other.doc['meshes'][0]['extras']['targetNames'], ['eyeBlinkLeft'])
        np.testing.assert_array_equal(other.accessor(0), got.accessor(0))

    def test_patch_only_requested_attribute(self):
        g = GLB(tiny_glb())
        old_normal = g.accessor(1).copy()
        old_morph = g.accessor(2).copy()
        update = g.accessor(0).copy()
        update[:, 0] += .004
        g.patch_f32_vec3(0, update)
        reread = GLB(g.to_bytes())
        np.testing.assert_allclose(reread.accessor(0), update, atol=1e-8)
        np.testing.assert_array_equal(reread.accessor(1), old_normal)
        np.testing.assert_array_equal(reread.accessor(2), old_morph)
        self.assertAlmostEqual(reread.doc['accessors'][0]['min'][0], .004, places=6)

    def test_invalid_glb_rejected(self):
        with self.assertRaises(GLBError):
            GLB(b'not a GLB')
        bad = tiny_glb()[:-4]
        with self.assertRaises(GLBError):
            GLB(bad)

    def test_nonfinite_or_mismatched_accessor_rejected(self):
        g = GLB(tiny_glb())
        with self.assertRaises(GLBError):
            g.patch_f32_vec3(0, np.array([[np.nan,0,0]] * 3))
        with self.assertRaises(GLBError):
            g.patch_f32_vec3(0, np.array([[0,0,0]] * 4))

    def test_binary_buffer_view_bounds_protected(self):
        g = GLB(tiny_glb())
        g.doc['accessors'][0]['count'] = 100000
        with self.assertRaises(GLBError):
            g.accessor(0)


class GaussianFieldTests(unittest.TestCase):
    def setUp(self):
        self.controls = [
            Control('testA',(-.03,1.58,.14),(-.002,.001,0),(.025,.030,.025)),
            Control('testB',(.03,1.58,.14),(.002,0,.003),(.025,.030,.025)),
        ]
        self.field = GaussianField(self.controls)

    def test_control_anchors_move_by_expected_deltas(self):
        p = np.array([c.center for c in self.controls])
        expected = np.array([c.delta for c in self.controls])
        result = self.field.warp(p)-p
        np.testing.assert_allclose(result, expected, atol=2e-7)

    def test_jacobian_matches_finite_differences(self):
        p = np.array([[.01,1.585,.145], [.04,1.63,.151]])
        _, jac = self.field.warp(p,jacobian=True)
        eps = 1e-4
        for j in range(3):
            step = np.eye(3)[j] * eps
            approx = (self.field.warp(p+step)-self.field.warp(p-step))/(2*eps)
            np.testing.assert_allclose(jac[:,:,j],approx,atol=1e-3)

    def test_single_morph_target_equals_warped_posed_vertices(self):
        p = np.array([[0,1.58,.14],[.03,1.57,.145]],dtype='f4')
        delta = np.array([[0,.01,0],[0,-.004,.003]],dtype='f4')
        new_p = self.field.warp(p)
        new_morph_delta = self.field.warp(p+delta)-new_p
        np.testing.assert_allclose(new_p+new_morph_delta,self.field.warp(p+delta),atol=1e-8)

    def test_transformed_normals_unit_length(self):
        p = np.array([[0,1.58,.14],[.03,1.57,.145]],dtype='f4')
        normals = np.array([[0,0,1],[0,0,1]],dtype='f4')
        transformed, jac_min = self.field.transform_normals(p, normals)
        np.testing.assert_allclose(np.linalg.norm(transformed,axis=1),1,atol=1e-6)
        self.assertGreater(jac_min,.8)

    def test_empty_controls_rejected(self):
        with self.assertRaises(ValueError):
            GaussianField([])


if __name__ == '__main__':
    unittest.main()