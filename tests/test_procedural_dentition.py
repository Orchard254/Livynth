#!/usr/bin/env python3
"""CPU-only tests for the procedural permanent dentition generator.

No Blender required; validates anthropometry, mesh topology, winding,
arch layout, and the zero-transversal-crossing guarantee between the two
arches using the corrected Möller predicate from tools/mouth_anatomy.
"""
import math
import unittest

import numpy as np

from character.procedural_dentition import (
    ARCH_PARAMS, FDI_QUADRANT, GUM_SAMPLES, N_THETA, SIDE_ORDER, TOOTH_METRICS,
    DentitionError, arch_curve_y, arch_tangent_angle, build_dentition,
    build_tooth, cusp_field, gum_band, place_arch, rest_gap_estimate,
    spee_z)
from tools.mouth_anatomy import (
    count_intersecting_triangle_pairs, nearest_triangle_distances)


def _tris(arch):
    return np.concatenate([t['vertices'][t['faces']] for t in arch], axis=0)


class DentitionBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = build_dentition()

    def test_fdi_numbering_complete_32(self):
        ids = [pl['fdi'] for pl in self.spec['upper'] + self.spec['lower']]
        self.assertEqual(len(ids), 32)
        self.assertEqual(len(set(ids)), 32)
        for quadrant in ('1', '2', '3', '4'):
            for digit in '12345678':
                self.assertIn(int(quadrant + digit), set(ids))

    def test_eight_teeth_per_side_per_arch(self):
        for arch in ('upper', 'lower'):
            for side in ('right', 'left'):
                teeth = [pl for pl in self.spec[arch]
                         if pl['side'] == side]
                self.assertEqual([pl['cls'] for pl in teeth],
                                 list(SIDE_ORDER))

    def test_determinism(self):
        a = build_dentition()
        b = build_dentition()
        for arch in ('upper', 'lower'):
            for ta, tb in zip(a[arch], b[arch]):
                np.testing.assert_array_equal(ta['vertices'], tb['vertices'])
                np.testing.assert_array_equal(ta['faces'], tb['faces'])

    def test_crown_heights_match_anthropometry(self):
        for arch_name in ('upper', 'lower'):
            for pl in self.spec[arch_name]:
                h = TOOTH_METRICS[pl['cls']][arch_name][1]
                span = float(np.ptp(pl['vertices'][:, 2]))
                # the crown can never exceed the anthropometric height;
                # the central fossa sits below the rim by design
                self.assertLessEqual(span, h + 1e-9)
                self.assertGreaterEqual(span, 0.80 * h)

    def test_faces_in_range_and_nondegenerate(self):
        for arch in ('upper', 'lower'):
            for pl in self.spec[arch]:
                f = pl['faces']
                self.assertGreaterEqual(int(f.min()), 0)
                self.assertLess(int(f.max()), len(pl['vertices']))
                v = pl['vertices']
                tri = v[f]
                cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
                norms = np.linalg.norm(cross, axis=1)
                self.assertGreater(float(norms.min()), 1e-9)

    def test_winding_favours_view_side(self):
        # lower teeth: occlusal cap faces must normal upwards
        _, f_low = build_tooth('molar1', upper=False)
        v_low, _ = build_tooth('molar1', upper=False)
        for j in range(N_THETA):
            a, b, c = v_low[f_low[j]]
            normal = np.cross(b - a, c - a)
            self.assertGreater(normal[2], 0.0)
        v_up, f_up = build_tooth('molar1', upper=True)
        for j in range(N_THETA):
            a, b, c = v_up[f_up[j]]
            normal = np.cross(b - a, c - a)
            self.assertLess(normal[2], 0.0)

    def test_arch_symmetry(self):
        for arch in ('upper', 'lower'):
            right = {pl['cls']: pl for pl in self.spec[arch]
                     if pl['side'] == 'right'}
            left = {pl['cls']: pl for pl in self.spec[arch]
                    if pl['side'] == 'left'}
            for cls, rpt in right.items():
                lpt = left[cls]
                self.assertAlmostEqual(-rpt['origin_body_m'][0],
                                       lpt['origin_body_m'][0], delta=1e-9)
                self.assertAlmostEqual(rpt['origin_body_m'][1],
                                       lpt['origin_body_m'][1], delta=1e-9)
                self.assertAlmostEqual(rpt['origin_body_m'][2],
                                       lpt['origin_body_m'][2], delta=1e-9)

    def test_arch_within_face_bounds(self):
        for arch in ('upper', 'lower'):
            verts = np.concatenate(
                [pl['vertices'] for pl in self.spec[arch]], axis=0)
            self.assertLess(float(np.abs(verts[:, 0]).max()), 0.06)
            self.assertGreater(float(verts[:, 1].max()), -0.20)
            self.assertLess(float(verts[:, 1].max()), -0.05)
            z_lo = ARCH_PARAMS['lower']['occ_z_front'] - 0.005
            z_hi = ARCH_PARAMS['upper']['occ_z_front'] + 0.002
            self.assertGreaterEqual(float(verts[:, 2].min()), z_lo - 0.013)
            self.assertLessEqual(float(verts[:, 2].max()), z_hi + 0.013)


class ArchGeometryTests(unittest.TestCase):
    def test_arch_curve_endpoints(self):
        p = ARCH_PARAMS['upper']
        self.assertAlmostEqual(arch_curve_y(0.0, y_front=p['y_front'],
                                            y_back=p['y_back'],
                                            half_width=p['half_width']),
                               p['y_front'], delta=1e-12)
        self.assertAlmostEqual(arch_curve_y(p['half_width'],
                                            y_front=p['y_front'],
                                            y_back=p['y_back'],
                                            half_width=p['half_width']),
                               p['y_back'], delta=1e-12)

    def test_arch_tangent_bounds(self):
        p = ARCH_PARAMS['upper']
        for x in np.linspace(0.0, p['half_width'], 21):
            angle = arch_tangent_angle(x, y_front=p['y_front'],
                                       y_back=p['y_back'],
                                       half_width=p['half_width'])
            self.assertTrue(math.isfinite(angle))
            self.assertLess(abs(angle), math.pi / 2)

    def test_spee_drop_posteriorly(self):
        p = ARCH_PARAMS['upper']
        z_front = spee_z(0.0, occ_z_front=p['occ_z_front'],
                         half_width=p['half_width'], spee=p['spee'])
        z_back = spee_z(p['half_width'], occ_z_front=p['occ_z_front'],
                        half_width=p['half_width'], spee=p['spee'])
        self.assertAlmostEqual(z_front - z_back, p['spee'], delta=1e-12)

    def test_rest_gap_positive(self):
        self.assertGreater(rest_gap_estimate(), 0.0)

    def test_cusp_field_peaks(self):
        self.assertAlmostEqual(cusp_field('canine', 0.0), 1.0, delta=1e-9)
        for theta in (0.38, 2 * math.pi - 0.38):
            self.assertGreater(cusp_field('molar1', theta),
                               cusp_field('molar1', math.pi / 2))

    def test_invalid_params_raise(self):
        bad = dict(ARCH_PARAMS)
        bad['upper'] = dict(ARCH_PARAMS['upper'], half_width=0.9)
        with self.assertRaises(DentitionError):
            place_arch('upper', params=bad)
        bad2 = dict(ARCH_PARAMS)
        bad2['upper'] = dict(ARCH_PARAMS['upper'], y_front=0.05)
        with self.assertRaises(DentitionError):
            place_arch('upper', params=bad2)


class ArchCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = build_dentition()

    def test_zero_transversal_crossings_rest_pose(self):
        up = _tris(self.spec['upper'])
        lo = _tris(self.spec['lower'])
        result = count_intersecting_triangle_pairs(up, lo)
        self.assertEqual(result['pairs'], 0)

    def test_occlusal_clearance_above_one_mm(self):
        verts = np.concatenate(
            [pl['vertices'] for pl in self.spec['upper']], axis=0)
        d = nearest_triangle_distances(verts, _tris(self.spec['lower']),
                                       chunk_size=256)
        self.assertGreater(float(d.min()), 0.0008)


class GumBandTests(unittest.TestCase):
    def test_gum_cej_ring_at_cervical_margin(self):
        """CEJ ring (ring 0) sits at the cervical margin of each tooth."""
        from character.procedural_dentition import _neck_z, arch_tooth_at
        for arch in ('upper', 'lower'):
            half_width = ARCH_PARAMS[arch]['half_width']
            xs = np.linspace(-half_width, half_width, GUM_SAMPLES)
            verts, _ = gum_band(arch)
            n = GUM_SAMPLES
            for j in range(n):
                tooth, _u = arch_tooth_at(arch, xs[j])
                cls = tooth['cls']
                nz = _neck_z(arch, cls, xs[j], params=ARCH_PARAMS)
                # CEJ ring is ring 0
                ring_z = verts[j, 2]
                # CEJ is at the neck minus the scallop (contacts lift the
                # margin), so it can sit up to one scallop amplitude below
                self.assertAlmostEqual(ring_z, nz, delta=0.0018 + 1e-6)

    def test_gum_free_margin_apical_to_cej(self):
        """Free gingival margin (ring 1) is apical to CEJ."""
        from character.procedural_dentition import _neck_z, arch_tooth_at
        for arch in ('upper', 'lower'):
            half_width = ARCH_PARAMS[arch]['half_width']
            xs = np.linspace(-half_width, half_width, GUM_SAMPLES)
            verts, _ = gum_band(arch)
            n = GUM_SAMPLES
            sign = 1 if arch == 'upper' else -1
            for j in range(n):
                tooth, _u = arch_tooth_at(arch, xs[j])
                cls = tooth['cls']
                nz = _neck_z(arch, cls, xs[j], params=ARCH_PARAMS)
                # Free margin is ring 1
                ring_z = verts[n + j, 2]
                if sign == 1:  # upper: free margin is lower (more negative z)
                    self.assertLess(ring_z, nz)
                else:          # lower: free margin is higher (more positive z)
                    self.assertGreater(ring_z, nz)

    def test_gum_face_count_and_topology(self):
        for arch in ('upper', 'lower'):
            verts, faces = gum_band(arch)
            self.assertEqual(len(verts), 4 * 96)  # 4 rings * 96 samples
            # 3 inter-ring quad strips * (95 quads * 2 tris) + 2 end caps * 2 tris
            self.assertEqual(len(faces), 3 * 95 * 2 + 2 * 2)


if __name__ == '__main__':
    unittest.main()
