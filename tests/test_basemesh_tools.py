"""C001-GEO-04: hermetic tests for the basemesh measurement tools.

These tests build tiny synthetic assets in a temp dir, so they pass on any
machine and do NOT depend on Blender, MPFB, or the Character 001 photos being
installed. The *real* measurements against the actual CC0 basemesh are
produced by tools/measure_basemesh.py, tools/blender_audit_basemesh.py,
tools/mpfb_headless_probe.py and tools/verify_glb_rig.py and are recorded in
docs/C001_GEO04_BASEMESH_PROVENANCE.md.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.measure_basemesh import analyse  # noqa: E402
from tools.measure_glb_topology import analyse as analyse_glb  # noqa: E402


def quad_grid_obj(nx=3, ny=3, with_uv=True):
    """Build a planar nx*ny quad grid OBJ (open sheet, 1 shell)."""
    verts = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            verts.append((float(i), float(j), 0.0))
    lines = ["# synthetic test grid"]
    for v in verts:
        lines.append("v %.6f %.6f %.6f" % v)
    if with_uv:
        for v in verts:
            lines.append("vt %.6f %.6f" % ((v[0] + 0.5) / (nx + 1), (v[1] + 0.5) / (ny + 1)))
    lines.append("g body")
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i + 1          # OBJ indices are 1-based
            b = a + 1
            c = a + (nx + 1) + 1
            d = a + (nx + 1)
            if with_uv:
                lines.append("f %d/%d %d/%d %d/%d %d/%d" % (a, a, b, b, c, c, d, d))
            else:
                lines.append("f %d %d %d %d" % (a, b, c, d))
    return "\n".join(lines) + "\n"


def _glb(meshes, nodes, scenes, skins=None, extras=None):
    """Assemble a minimal GLB from raw dict fragments (test helper)."""
    doc = {
        "asset": {"version": "2.0", "generator": "unit-test"},
        "meshes": meshes,
        "nodes": nodes,
        "scenes": scenes,
        "scene": 0,
    }
    if skins:
        doc["skins"] = skins
    if extras:
        doc.update(extras)
    js = json.dumps(doc).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    body = (struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", 0, 0x004E4942))
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


class MeasureObjTests(unittest.TestCase):
    def test_quad_grid_is_all_quads_single_shell(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "grid.obj"
            path.write_text(quad_grid_obj(3, 3), encoding="utf-8")
            rep = analyse(str(path))

        self.assertEqual(rep["counts"]["vertices"], 16)
        self.assertEqual(rep["counts"]["faces"], 9)
        self.assertEqual(rep["quads"], 9)
        self.assertEqual(rep["tris"], 0)
        self.assertEqual(rep["ngons_gt4"], 0)
        self.assertEqual(rep["quad_dominance_pct"], 100.0)
        self.assertEqual(rep["connected_components"]["count"], 1)
        self.assertEqual(rep["body_group_components"]["count"], 1)
        self.assertEqual(rep["edges"]["nonmanifold_gt2face"], 0)
        self.assertEqual(rep["loose_vertices"], 0)
        # an open sheet has boundary edges, not non-manifold ones
        self.assertGreater(rep["edges"]["boundary_open"], 0)
        self.assertEqual(rep["edges"]["euler_V_minus_E_plus_F"], 1)

    def test_uv_layer_is_detected_and_overlap_free(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "grid.obj"
            path.write_text(quad_grid_obj(3, 3, with_uv=True), encoding="utf-8")
            rep = analyse(str(path))

        self.assertTrue(rep["uvs"]["has_uv_layer"])
        self.assertEqual(rep["uvs"]["faces_with_invalid_texture_indices"], 0)
        self.assertEqual(rep["uvs"]["faces_with_texture_indices"], 9)
        self.assertIsNotNone(rep["uv_overlap_estimate"])
        self.assertEqual(rep["uv_overlap_estimate"]["overlapping_cells"], 0)

    def test_missing_uv_is_reported_not_faked(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "grid.obj"
            path.write_text(quad_grid_obj(3, 3, with_uv=False), encoding="utf-8")
            rep = analyse(str(path))

        self.assertFalse(rep["uvs"]["has_uv_layer"])
        self.assertEqual(rep["uvs"]["texture_vertices"], 0)

    def test_report_is_json_serialisable(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "grid.obj"
            path.write_text(quad_grid_obj(2, 2), encoding="utf-8")
            rep = analyse(str(path))
        json.dumps(rep)  # must not raise


class MeasureGlbTests(unittest.TestCase):
    def test_rejects_non_glb(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "not.glb"
            path.write_bytes(b"NOPE" + b"\x00" * 32)
            with self.assertRaises(ValueError):
                analyse_glb(str(path))

    def test_minimal_valid_glb_is_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tri.glb"
            positions = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
            indices = struct.pack("<3H", 0, 1, 2)
            bin_chunk = positions + b"\x00" * ((4 - len(positions) % 4) % 4) + indices
            doc = {
                "asset": {"version": "2.0", "generator": "unit-test"},
                "meshes": [{
                    "name": "tri",
                    "primitives": [{
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "mode": 4,
                    }],
                }],
                "accessors": [
                    {"bufferView": 0, "componentType": 5126, "count": 3,
                     "type": "VEC3", "max": [1, 1, 0], "min": [0, 0, 0]},
                    {"bufferView": 1, "componentType": 5123, "count": 3,
                     "type": "SCALAR"},
                ],
                "bufferViews": [
                    {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
                    {"buffer": 0, "byteOffset": len(positions),
                     "byteLength": len(indices)},
                ],
                "buffers": [{"byteLength": len(bin_chunk)}],
            }
            js = json.dumps(doc).encode("utf-8")
            js += b" " * ((4 - len(js) % 4) % 4)
            body = (struct.pack("<II", len(js), 0x4E4F534A) + js
                    + struct.pack("<II", len(bin_chunk), 0x004E4942) + bin_chunk)
            path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)

            rep = analyse_glb(str(path))

        self.assertEqual(rep["generator"], "unit-test")
        self.assertEqual(len(rep["meshes"]), 1)
        prim = rep["meshes"][0]["primitives"][0]
        self.assertEqual(prim["vertices"], 3)
        self.assertEqual(prim["triangles"], 1)
        self.assertEqual(prim["non_manifold_edges"], 0)
        self.assertEqual(prim["boundary_edges"], 3)
        self.assertEqual(prim["connected_shells"], 1)

    # ---- C001-GEO-04 defect D1/D2/D3 regression coverage ---------------

    def test_multi_mesh_glb_does_not_read_only_meshes_zero(self):
        """The character mesh must be located by name/morph count, not index 0.

        Regression test for the false "0 morph targets" reading caused by
        reading only meshes[0] when meshes[0] is a default cube.
        """
        cube = {"name": "Cube", "primitives": [{"attributes": {}, "mode": 4}]}
        hero = {"name": "base.001", "primitives": [{"attributes": {}, "mode": 4}],
                "extras": {"targetNames": ["eyeBlinkLeft", "jawOpen"]}}
        nodes = [
            {"name": "Cube", "mesh": 0},
            {"name": "Human_export_copy", "mesh": 1},
        ]
        blob = _glb([cube, hero], nodes, [{"nodes": [0, 1]}])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "multi.glb"
            path.write_bytes(blob)
            rep = analyse_glb(str(path))

        self.assertEqual(len(rep["meshes"]), 2)
        # the default cube must be identified, not treated as the character
        self.assertTrue(rep["default_cube_present"])
        self.assertEqual(rep["character_mesh_name"], "base.001")
        self.assertEqual(rep["character"]["target_names_present"], True)
        self.assertEqual(rep["character"]["declared_target_name_count"], 2)
        self.assertEqual(rep["character"]["target_names"],
                         ["eyeBlinkLeft", "jawOpen"])
        self.assertEqual([m["name"] for m in rep["non_character_meshes"]], ["Cube"])

    def test_default_cube_is_never_chosen_as_the_character(self):
        cube = {"name": "Cube", "primitives": [{"attributes": {}, "mode": 4}]}
        nodes = [{"name": "Cube", "mesh": 0}]
        blob = _glb([cube], nodes, [{"nodes": [0]}])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cube.glb"
            path.write_bytes(blob)
            rep = analyse_glb(str(path))

        self.assertTrue(rep["default_cube_present"])
        self.assertIsNone(rep["character_mesh_name"])

    def test_scene_roots_and_skin_are_reported(self):
        hero = {"name": "base.001", "primitives": [{"attributes": {}, "mode": 4}]}
        nodes = [
            {"name": "Human.rig_export_copy", "children": [1]},
            {"name": "Human_export_copy", "mesh": 0, "skin": 0},
            {"name": "jaw"},
        ]
        skins = [{"name": "Human.rig_export_copy", "joints": [2], "skeleton": 0}]
        blob = _glb([hero], nodes, [{"nodes": [0]}], skins=skins)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rigged.glb"
            path.write_bytes(blob)
            rep = analyse_glb(str(path))

        self.assertEqual(rep["scene_roots"], ["Human.rig_export_copy"])
        self.assertTrue(rep["skin_present"])
        self.assertTrue(rep["armature_present"])
        self.assertEqual(rep["joint_count"], 1)
        self.assertEqual(rep["skins"][0]["joint_names"], ["jaw"])
        self.assertEqual(rep["character_mesh_name"], "base.001")
        self.assertEqual(rep["character"]["node_names"], ["Human_export_copy"])


if __name__ == "__main__":
    unittest.main()
