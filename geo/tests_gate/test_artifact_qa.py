"""C001-GEO-04 gate - artifact QA tests on synthesised meshes.

The artifact QA has to catch the defects that the visual-hull candidate is
known to have, so the checks are exercised on meshes whose defect is known
by construction.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from geo.gate import artifact_qa


def _tetra(offset=(0.0, 0.0, 0.0), scale=0.05, flip=False):
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
    f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
    if flip:
        f = f[:, ::-1]
    return v * scale + np.asarray(offset, dtype=np.float64), f


def _write(meshes, path):
    scene = trimesh.Scene()
    for i, (v, f) in enumerate(meshes):
        scene.add_geometry(trimesh.Trimesh(vertices=v, faces=f, process=False),
                           node_name="g%d" % i, geom_name="g%d" % i)
    scene.export(str(path))


class ArtifactQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gate_artifact_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_two_component_mesh_is_flagged(self):
        p = self.tmp / "two.glb"
        _write([_tetra((0, 0, 0)), _tetra((0.2, 0, 0))], p)
        rep = artifact_qa.audit_glb(p)
        reasons = rep["verdict"]["reasons"]
        self.assertFalse(rep["verdict"]["pass"])
        self.assertTrue(any("connected_components" in r for r in reasons), reasons)
        total = sum(g["component_count"] for g in rep["geometries"])
        self.assertEqual(total, 2)
        self.assertEqual(len(rep["geometries"]), 2)

    def test_non_manifold_mesh_is_flagged(self):
        v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0]], dtype=np.float64)
        f = np.array([[0, 1, 2], [0, 1, 3], [0, 1, 2]], dtype=np.int64)
        p = self.tmp / "nonmanifold.glb"
        _write([(v, f)], p)
        rep = artifact_qa.audit_glb(p)
        reasons = rep["verdict"]["reasons"]
        self.assertFalse(rep["verdict"]["pass"])
        self.assertTrue(any("non_manifold_edges" in r for r in reasons), reasons)

    def test_doubled_surface_is_flagged(self):
        v, f = _tetra((0, 0, 0))
        # one geometry that carries the surface twice, the second copy with
        # the opposite winding: a doubled, ghost surface
        doubled = np.concatenate([f, f[:, ::-1]], axis=0)
        p = self.tmp / "doubled.glb"
        _write([(v, doubled)], p)
        rep = artifact_qa.audit_glb(p)
        reasons = rep["verdict"]["reasons"]
        self.assertFalse(rep["verdict"]["pass"])
        self.assertTrue(any("duplicate_opposite_faces" in r for r in reasons), reasons)

    def test_clean_mesh_reports_its_measurements(self):
        v, f = _tetra((0, 0, 0))
        p = self.tmp / "clean.glb"
        _write([(v, f)], p)
        rep = artifact_qa.audit_glb(p)
        g = rep["geometries"][0]
        self.assertEqual(g["component_count"], 1)
        self.assertEqual(g["faces"], 4)
        self.assertIn("uv", g)
        self.assertIn("rig", rep)
        self.assertEqual(rep["rig"]["skins"], 0)
        self.assertEqual(rep["rig"]["morph_targets"], 0)

    def test_rig_and_blendshape_presence_is_reported(self):
        v, f = _tetra((0, 0, 0))
        p = self.tmp / "clean2.glb"
        _write([(v, f)], p)
        rep = artifact_qa.audit_glb(p)
        self.assertFalse(rep["rig"]["rig_present"])
        self.assertTrue(rep["gltf"]["primitive_modes"] in ([4], []))


if __name__ == "__main__":
    unittest.main()
