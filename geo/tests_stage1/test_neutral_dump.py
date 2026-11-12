"""Synthetic archive tests: do not claim Blender or Character 001 validation."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from stage1_neutral_dump import SCHEMA, write_neutral_dump
from geo.stage1_fit import FitRejected, positions_sha256


class Point:
    def __init__(self, xyz):
        self.co = list(xyz)


class Poly:
    def __init__(self, indices):
        self.vertices = indices


class Fixture:
    type = "MESH"
    name = "NeutralFixture"

    def __init__(self, coords=None):
        self.data = types.SimpleNamespace(
            vertices=[Point(v) for v in (coords or ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)))],
            polygons=[Poly((0, 1, 2, 3))],
            shape_keys=None,
        )


class NeutralDumpTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()

    def test_roundtrip_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "mesh.npz"
            report = write_neutral_dump(self.fixture, target)
            with np.load(target, allow_pickle=False) as data:
                points = data["vertices"]
                quads = data["quads"]
                meta = json.loads(data["metadata_utf8"].tobytes().decode("utf-8"))
            self.assertEqual(report["positions_sha256"], positions_sha256(points))
            self.assertEqual(meta["schema"], SCHEMA)
            self.assertEqual(meta["positions_sha256"], report["positions_sha256"])
            self.assertEqual(meta["stage1"], "NOT_RUN")
            np.testing.assert_array_equal(quads, [[0, 1, 2, 3]])
            self.assertEqual(report["bounds_max"], [1., 0., 1.])

    def test_source_not_mutated(self):
        original = [list(v.co) for v in self.fixture.data.vertices]
        with tempfile.TemporaryDirectory() as td:
            write_neutral_dump(self.fixture, Path(td) / "mesh.npz")
        self.assertEqual(original, [list(v.co) for v in self.fixture.data.vertices])

    def test_npz_only(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(FitRejected, "E_NEUTRAL_DUMP_SUFFIX"):
                write_neutral_dump(self.fixture, Path(td) / "mesh.json")
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_missing_mesh_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(FitRejected, "E_NOT_MESH"):
                write_neutral_dump(None, Path(td) / "mesh.npz")

    def test_preexisting_morphs_rejected(self):
        self.fixture.data.shape_keys = types.SimpleNamespace(key_blocks=["Basis", "blink"])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(FitRejected, "E_EXISTING_SHAPE_TARGETS"):
                write_neutral_dump(self.fixture, Path(td) / "mesh.npz")

    def test_non_quad_rejected(self):
        self.fixture.data.polygons = [Poly((0, 1, 2))]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(FitRejected, "E_QUAD_BASEMESH_REQUIRED"):
                write_neutral_dump(self.fixture, Path(td) / "mesh.npz")


if __name__ == "__main__":
    unittest.main()
