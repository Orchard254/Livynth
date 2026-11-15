#!/usr/bin/env python3
"""IDENTITY-029: unit tests for character.oral_visibility (pure NumPy)."""
from __future__ import annotations

import math
import unittest

import numpy as np

from character.oral_visibility import (
    SCHEMA, OralVisibilityError, alpha_mask, aperture_profile,
    cavity_aperture_mask, classify_arch_pixels, dark_aperture_mask,
    plan_lip_almonder, visibility_metrics)


class OralVisibilityTests(unittest.TestCase):
    def setUp(self):
        # Synthetic 400x600 render (width, height)
        self.h = 600
        self.w = 400
        self.image = np.ones((self.h, self.w, 4), dtype=np.float64)
        self.image[:, :, 3] = 1.0

    def test_classify_arch_pixels_basic(self):
        upper = np.array([1.0, 0.0, 0.0])
        lower = np.array([0.0, 0.0, 1.0])
        # paint a few pixels
        rgb = self.image[:, :, :3].copy()
        rgb[100:110, 150:160] = upper
        rgb[120:130, 150:160] = lower
        masks = classify_arch_pixels(rgb, upper_color=upper, lower_color=lower,
                                     tolerance=0.06)
        self.assertEqual(masks['upper'][100:110, 150:160].sum(), 100)
        self.assertEqual(masks['lower'][120:130, 150:160].sum(), 100)
        self.assertEqual(masks['other'][100:110, 150:160].sum(), 0)

    def test_classify_arch_pixels_overlap_resolved(self):
        upper = np.array([1.0, 0.0, 0.0])
        lower = np.array([0.0, 0.0, 1.0])
        rgb = self.image[:, :, :3].copy()
        # Overlapping region: assign to whichever is closer
        rgb[100:105, 150:155] = upper  # closer to upper
        rgb[100:105, 155:160] = lower  # closer to lower
        masks = classify_arch_pixels(rgb, upper_color=upper, lower_color=lower,
                                     tolerance=0.06)
        self.assertEqual(masks['upper'][100:105, 150:155].sum(), 25)
        self.assertEqual(masks['lower'][100:105, 155:160].sum(), 25)

    def test_visibility_metrics(self):
        sil = np.zeros((10, 10), dtype=bool)
        sil[2:8, 2:8] = True  # 6x6 = 36 pixels
        vis = sil.copy()
        vis[4:6, 4:6] = False  # 2x2 = 4 occluded
        m = visibility_metrics(sil, vis)
        self.assertEqual(m['silhouette_pixels'], 36)
        self.assertEqual(m['visible_pixels'], 32)
        self.assertEqual(m['occluded_pixels'], 4)
        self.assertAlmostEqual(m['visible_fraction'], 32 / 36, places=6)

    def test_visibility_metrics_empty_rejected(self):
        with self.assertRaises(OralVisibilityError) as ctx:
            visibility_metrics(np.zeros((5, 5), dtype=bool),
                               np.zeros((5, 5), dtype=bool))
        self.assertIn('E_VISIBILITY_EMPTY', str(ctx.exception))

    def test_aperture_profile_synthetic_v(self):
        # Inverted V: centre sits HIGH in image (small row index), corners LOW
        # Image coords: row 0 = top, larger row = lower in image
        # Inverted V (apex at centre): centre top=40, corners top=60
        mask = np.zeros((100, 100), dtype=bool)
        for x in range(30, 71):
            cx = abs(x - 50)
            top = 40 + cx  # centre=40, corners=60 (higher row = lower in image)
            bottom = 60
            mask[top:bottom, x] = True
        profile = aperture_profile(mask)
        # centre_mid (50) < corner_mid (70) -> corners are LOWER in image
        # v_score = (corner_mid - centre_mid) / height > 0
        self.assertGreater(profile['v_score'], 0.0)
        self.assertLess(profile['centre_mid_px'], profile['corner_mid_px'])

    def test_aperture_profile_frown(self):
        # Frown: centre sits LOW in image (large row index), corners HIGH
        mask = np.zeros((100, 100), dtype=bool)
        for x in range(30, 71):
            cx = abs(x - 50)
            top = 60 - cx  # Frown: centre=60, corners=40
            bottom = 80
            mask[top:bottom, x] = True
        profile = aperture_profile(mask)
        # centre_mid (70) > corner_mid (50) -> v_score NEGATIVE
        self.assertLess(profile['v_score'], 0.0)
        self.assertGreater(profile['centre_mid_px'], profile['corner_mid_px'])

    def test_aperture_profile_flat(self):
        # Flat: centre and corners at same level
        mask = np.zeros((100, 100), dtype=bool)
        for x in range(30, 71):
            mask[50:70, x] = True
        profile = aperture_profile(mask)
        self.assertAlmostEqual(profile['v_score'], 0.0, places=2)

    def test_dark_aperture_mask(self):
        rgb = np.zeros((50, 50, 3), dtype=np.float64)
        rgb[:, :] = [0.8, 0.8, 0.8]  # bright
        rgb[20:30, 20:30] = [0.1, 0.1, 0.1]  # dark cavity
        mask = dark_aperture_mask(rgb, max_luma=0.42)
        self.assertTrue(mask[20:30, 20:30].all())
        self.assertFalse(mask[0:20, 0:20].any())

    def test_cavity_aperture_mask(self):
        rgb = np.zeros((50, 50, 3), dtype=np.float64)
        rgb[:, :] = [0.5, 0.5, 0.5]
        rgb[20:30, 20:30] = [0.0, 1.0, 0.0]  # flat green
        mask = cavity_aperture_mask(rgb, cavity_color=[0.0, 1.0, 0.0],
                                    tolerance=0.06)
        self.assertTrue(mask[20:30, 20:30].all())
        self.assertFalse(mask[0:20, 0:20].any())

    def test_alpha_mask(self):
        self.image[:, :, 3] = 1.0
        self.image[10:20, 10:20, 3] = 0.0
        mask = alpha_mask(self.image)
        self.assertEqual(mask.sum(), self.h * self.w - 100)
        self.assertFalse(mask[10:20, 10:20].any())

    def test_plan_lip_almonder_bounds(self):
        # Minimal valid points
        points = np.zeros((100, 3), dtype=np.float64)
        points[:, 1] = -0.05  # front
        points[:, 2] = np.linspace(1.45, 1.55, 100)
        # should not raise with defaults
        moved, audit = plan_lip_almonder(points)
        self.assertEqual(moved.shape, points.shape)
        self.assertIn('schema', audit)
        self.assertEqual(audit['schema'], SCHEMA)

    def test_plan_lip_almonder_invalid_bounds_rejected(self):
        points = np.zeros((10, 3), dtype=np.float64)
        points[:, 1] = -0.05
        points[:, 2] = 1.5
        # upper_centre_drop > MAX_LIP_RESHAPE_M
        with self.assertRaises(OralVisibilityError) as ctx:
            plan_lip_almonder(points, upper_centre_drop=0.02)
        self.assertIn('E_LIP_BOUND_upper_centre_drop', str(ctx.exception))

    def test_plan_lip_almonder_zero_params_is_noop(self):
        points = np.zeros((100, 3), dtype=np.float64)
        points[:, 1] = -0.05
        points[:, 2] = np.linspace(1.45, 1.55, 100)
        moved, audit = plan_lip_almonder(points, upper_centre_drop=0.0,
                                         lower_corner_lift=0.0,
                                         lower_roll_push=0.0)
        self.assertTrue(np.allclose(moved, points))
        self.assertEqual(audit['selected_vertices'], 0)

    def test_plan_lip_almonder_selects_front_vertices_only(self):
        points = np.zeros((100, 3), dtype=np.float64)
        points[:50, 1] = -0.05  # front
        points[50:, 1] = +0.05  # back
        # Use z in the upper border band (default: 1.530 ± 0.018)
        points[:, 2] = 1.53
        moved, audit = plan_lip_almonder(points, upper_centre_drop=0.001)
        self.assertEqual(audit['selected_vertices'], 50)  # only front
        self.assertEqual(audit['stationary_vertices'], 50)


class BroadphaseEquivalenceTests(unittest.TestCase):
    """The z-bin broadphase must find EXACTLY the brute-force crossing set.

    IDENTITY-029 replaced the original O(N*M) linear scan with a z-bin
    hash to make the millimetre-scale audits (tens of thousands of
    triangles) tractable. A faster broadphase that silently drops
    crossings would invalidate every collision number in the report, so
    the replacement is pinned against a brute-force reference over
    randomized overlapping triangle sets.
    """
    @staticmethod
    def _brute_force_count(A, B, margin=1e-6):
        from tools.mouth_anatomy import _triangles_intersect
        count = 0
        for a in A:
            amin = a.min(axis=0)
            amax = a.max(axis=0)
            for j, b in enumerate(B):
                bmin = b.min(axis=0)
                bmax = b.max(axis=0)
                if (bmax[2] < amin[2] - margin or
                        bmin[2] > amax[2] + margin or
                        bmax[1] < amin[1] - margin or
                        bmin[1] > amax[1] + margin or
                        bmax[0] < amin[0] - margin or
                        bmin[0] > amax[0] + margin):
                    continue
                if _triangles_intersect(a[0], a[1], a[2],
                                        b[0], b[1], b[2]):
                    count += 1
        return count

    def test_zbin_matches_brute_force_randomised(self):
        rng = np.random.default_rng(20261113)
        for trial in range(6):
            n_a = 30 + trial * 9
            n_b = 28 + trial * 11
            A = np.empty((n_a, 3, 3))
            B = np.empty((n_b, 3, 3))
            for i in range(n_a):
                cx = rng.uniform(-0.05, 0.05)
                cy = rng.uniform(-0.05, 0.05)
                cz = rng.uniform(-0.02, 0.02)
                A[i] = np.array([
                    [cx - 0.01, cy - 0.01, cz],
                    [cx + 0.01, cy - 0.01, cz + rng.uniform(-0.01, 0.01)],
                    [cx, cy + 0.01, cz + rng.uniform(-0.01, 0.01)]])
            for i in range(n_b):
                cx = rng.uniform(-0.05, 0.05)
                cy = rng.uniform(-0.05, 0.05)
                cz = rng.uniform(-0.02, 0.02)
                B[i] = np.array([
                    [cx - 0.008, cy - 0.008, cz + rng.uniform(-0.01, 0.01)],
                    [cx + 0.008, cy - 0.008, cz],
                    [cx, cy + 0.008, cz + rng.uniform(-0.01, 0.01)]])
            brute = self._brute_force_count(A, B)
            fast = count_intersecting_triangle_pairs(A, B)['pairs']
            self.assertEqual(fast, brute,
                             'trial %d: zbin=%d brute=%d' % (trial, fast, brute))

    def test_describe_and_count_agree_after_broadphase_change(self):
        rng = np.random.default_rng(4242)
        A = np.empty((60, 3, 3))
        B = np.empty((55, 3, 3))
        for i in range(len(A)):
            c = rng.uniform(-0.04, 0.04, 3)
            A[i] = np.array([c + rng.uniform(-0.01, 0.01, 3) for _ in range(3)])
        for i in range(len(B)):
            c = rng.uniform(-0.04, 0.04, 3)
            B[i] = np.array([c + rng.uniform(-0.01, 0.01, 3) for _ in range(3)])
        counted = count_intersecting_triangle_pairs(A, B)['pairs']
        described = describe_intersecting_triangle_pairs(A, B)['pairs']
        self.assertEqual(counted, described)

    def test_zbin_handles_degenerate_z_span(self):
        # all triangles in one z plane -> the grid must still find hits
        A = np.array([[[-1.0, 1.0, 0.0], [1.0, 1.0, 0.0],
                       [0.0, -1.0, 0.0]]])
        B = np.array([[[0.0, 0.0, -1.0], [0.0, 0.6, 1.0],
                       [0.0, -0.6, 1.0]]])
        self.assertEqual(count_intersecting_triangle_pairs(A, B)['pairs'], 1)
        flat_a = np.repeat(A, 3, axis=0)
        flat_b = np.repeat(B, 3, axis=0)
        self.assertEqual(count_intersecting_triangle_pairs(flat_a, flat_b)['pairs'],
                         9)


# Import the function used by the test above
from tools.mouth_anatomy import (
    count_intersecting_triangle_pairs, describe_intersecting_triangle_pairs)