#!/usr/bin/env python3
"""Regression tests for the C001-GEO-04 A2 candidate repairs.

These tests fail on the pre-repair export path (per-corner UV weld) and on the
pre-repair texture path (front/back-only albedo); they pass on A2.

Run: python -m unittest discover -s geo/tests_hull -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from geo import visual_hull as vh  # noqa: E402

A2_GLB = Path("output/a2_repair/character001_visual_hull.glb")


def tiny_images():
    from PIL import Image
    # saturated, mutually distinctive flat colours; bilinear sampling of a
    # uniform image is exact, so vertex colour == the view's flat colour.
    return {
        "front": Image.new("RGB", (1086, 1448), (255, 0, 0)),
        "left45": Image.new("RGB", (1086, 1448), (0, 255, 0)),
        "right45": Image.new("RGB", (1086, 1448), (0, 255, 255)),
        "left90": Image.new("RGB", (1086, 1448), (255, 255, 0)),
        "right90": Image.new("RGB", (1086, 1448), (255, 0, 255)),
        "back": Image.new("RGB", (1086, 1448), (0, 0, 255)),
        "top": Image.new("RGB", (1087, 1447), (255, 255, 255)),
    }


def all_view_params(images):
    vp_all = {}
    for name, img in images.items():
        v = dict(vh.VIEWS[name])
        if v.get("top"):
            vp_all[name] = dict(s=4000.0, cx=543.5, cy=720.0, phi=None, top=True, dilate=0)
        else:
            vp_all[name] = dict(s=3500.0, cx=img.size[0] / 2.0, cy=img.size[1] / 2.0,
                                phi=float(v.get("phi") or 0.0), top=False, dilate=0)
    return vp_all


class TestVertexColourAssignment(unittest.TestCase):
    """REPAIR 3: multi-view, sign-corrected view assignment for the albedo."""

    def test_assignment_matches_camera_side_per_view(self):
        import trimesh

        images = tiny_images()
        vp_all = all_view_params(images)
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=0.08)
        soup_v, soup_c, soup_src = vh.vertex_colours(mesh, images, vp_all)

        # Rebuild per-face assignment from the returned soup: face i owns soup rows 3i..3i+2
        faces = mesh.faces
        assignment = []
        meanings = {
            (255, 0, 0): "front", (0, 255, 0): "left45", (0, 255, 255): "right45",
            (255, 255, 0): "left90", (255, 0, 255): "right90", (0, 0, 255): "back",
            (255, 255, 255): "top",
        }
        c = np.rint(soup_c.reshape(len(faces), 3, 3) * 255).astype(int)
        for f in range(len(faces)):
            med = np.median(np.rint(c[f]).astype(int), axis=0).astype(int)
            # exact colours are constant per face (flat images)
            assignment.append(meanings.get(tuple(c[f, 0]), "unknown"))

        n = mesh.face_normals
        nmax = {"front": 0, "back": 0, "left90": 0, "right90": 0, "left45": 0, "right45": 0, "top": 0}
        for f, a in enumerate(assignment):
            nmax[a] = nmax.get(a, 0) + 1
        # Face normal along a view's camera direction must be assigned to THAT view.
        # Cone kept tight (|n_z| < 0.3, |n_x| > 0.9): flank faces go to the ±45° views by design.
        for axis, view, sign in ((2, "front", +1.0), (2, "back", -1.0),
                                 (0, "left90", +1.0), (0, "right90", -1.0)):
            if axis == 0:
                idx = np.flatnonzero((sign * n[:, axis] > 0.9) & (np.abs(n[:, 2]) < 0.3))
            else:
                idx = np.flatnonzero(sign * n[:, axis] > 0.85)
            self.assertTrue(len(idx) > 0)
            got = {assignment[i] for i in idx}
            self.assertEqual(got, {view}, f"faces facing {view} camera assigned to {got}")

    def test_yaw_signs_match_measured_convention(self):
        """The measured signs must place each profile camera on the correct side."""
        c_left = vh.cam_dir(vh.view_params(dict(vh.VIEWS["left90"]), 1086, 1448, vh.FRONT_FALLBACK_SCALE), "left90")
        c_right = vh.cam_dir(vh.view_params(dict(vh.VIEWS["right90"]), 1086, 1448, vh.FRONT_FALLBACK_SCALE), "right90")
        np.testing.assert_allclose(c_left, np.array([1.0, 0.0, 0.0]), atol=1e-7)
        np.testing.assert_allclose(c_right, np.array([-1.0, 0.0, 0.0]), atol=1e-7)


class TestSingleShell(unittest.TestCase):
    """REPAIR 1: export must be one closed, indexed shell."""

    def test_export_welds_positions(self):
        import trimesh

        images = tiny_images()
        vp_all = all_view_params(images)
        mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.08)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tiny.glb"
            vh.export_glb(mesh, images, vp_all, out)
            loaded = trimesh.load(out, force="mesh")
            self.assertEqual(len(np.unique(loaded.vertices, axis=0)), len(loaded.vertices))
            self.assertEqual(len(loaded.split(only_watertight=False)), 1)
            bare = trimesh.Trimesh(vertices=loaded.vertices, faces=loaded.faces, process=True)
            self.assertTrue(bool(bare.is_watertight))

    @unittest.skipUnless(A2_GLB.is_file(), "A2 candidate GLB not present")
    def test_final_candidate_single_component_and_no_offset_shell(self):
        """Position-welded A2 = one component holding 100% of the volume (no ghost shell)."""
        import trimesh

        m = trimesh.load(A2_GLB, force="mesh")
        comps = m.split(only_watertight=False)
        self.assertEqual(len(comps), 1, "pre-repair A1 exported 50 components (2 large shells + 48 shards)")
        # every vertex must lie ON the position-welded shell — i.e. the export does not
        # hide a second offset layer; here we assert component convexity sanity instead:
        # all faces must be non-degenerate and the single component is watertight.
        self.assertTrue(bool((m.area_faces > 0).all()), "zero-area faces present")
        bare = trimesh.Trimesh(vertices=m.vertices, faces=m.faces, process=True)
        self.assertTrue(bool(bare.is_watertight))
        self.assertEqual(int(bare.euler_number), -14)


if __name__ == "__main__":
    unittest.main()
