#!/usr/bin/env python3
"""Headless Blender import + topology audit of a candidate basemesh.

C001-GEO-04 / ADR-C001-004 Decision 1 (Topology Option B), sparse proof.
This proves whether the candidate basemesh is *importable headlessly* into the
exact Blender build this project uses, and reports Blender-side topology facts
(polygon counts, UV layers, vertex groups, material slots, modifier stack,
armature presence, shape keys) that the pure-python OBJ reader cannot see.

Usage (Blender 4.5):
    blender --background --factory-startup --python tools/blender_audit_basemesh.py -- <obj> [--json out.json]

Exit code is 0 on success, 1 on failure, so it can be used in CI.
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    argv = sys.argv
    if "--" not in argv:
        print("ERROR: pass args after '--'", file=sys.stderr)
        return 1
    args = argv[argv.index("--") + 1:]

    obj = None
    json_out = None
    i = 0
    while i < len(args):
        if args[i] == "--json":
            json_out = args[i + 1]
            i += 2
            continue
        if obj is None:
            obj = args[i]
        i += 1

    if not obj or not os.path.isfile(obj):
        print("ERROR: obj not found: %r" % obj, file=sys.stderr)
        return 1

    import bpy  # noqa: E402  (only importable inside Blender)

    report = {
        "blender_version": bpy.app.version_string,
        "blender_binary": bpy.app.binary_path,
        "source_obj": os.path.abspath(obj),
        "source_size_bytes": os.path.getsize(obj),
        "import_ok": False,
        "error": None,
    }

    try:
        before = set(bpy.data.objects)
        # Blender 4.x OBJ importer
        bpy.ops.wm.obj_import(filepath=obj)
        new_objs = [o for o in bpy.data.objects if o not in before]
        if not new_objs:
            raise RuntimeError("wm.obj_import created no objects")
        obj_data = new_objs[0]
        me = obj_data.data

        poly_hist = {}
        for p in me.polygons:
            poly_hist[str(len(p.vertices))] = poly_hist.get(str(len(p.vertices)), 0) + 1
        quads = poly_hist.get("4", 0)
        nf = len(me.polygons)

        uv_layers = [uv.name for uv in me.uv_layers]
        vgroups = sorted({vg.name for vg in obj_data.vertex_groups})

        report.update({
            "import_ok": True,
            "object_name": obj_data.name,
            "object_type": obj_data.type,
            "vertices": len(me.vertices),
            "edges": len(me.edges),
            "polygons": nf,
            "loose_vertices": sum(1 for v in me.vertices if not any(
                v.index in e.vertices for e in me.edges)) if nf else 0,
            "polygon_size_histogram": poly_hist,
            "quad_dominance_pct": round(100.0 * quads / nf, 3) if nf else None,
            "uv_layers": uv_layers,
            "has_uv_layer": len(uv_layers) > 0,
            "vertex_group_count": len(vgroups),
            "vertex_groups": vgroups,
            "material_slots": [m.name if m else None for m in me.materials],
            "material_slot_count": len(me.materials),
            "modifiers": [(m.name, m.type) for m in obj_data.modifiers],
            "shape_keys": [],
            "armatures_in_scene": [o.name for o in bpy.data.objects if o.type == "ARMATURE"],
            "scene_objects": [(o.name, o.type) for o in bpy.data.objects],
            "bbox_world": [list(obj_data.bound_box[0]), list(obj_data.bound_box[6])],
        })
        # shape keys
        if me.shape_keys:
            report["shape_keys"] = [k.name for k in me.shape_keys.key_blocks]

        # Non-manifold edge check using Blender's own mesh validation
        try:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            nonman = [e for e in bm.edges if not e.is_manifold]
            boundary = [e for e in bm.edges if e.is_boundary]
            wire = [e for e in bm.edges if e.is_wire]
            report["bmesh_edges"] = {
                "non_manifold": len(nonman),
                "boundary": len(boundary),
                "wire": len(wire),
            }
            bm.free()
        except Exception as exc:  # pragma: no cover
            report["bmesh_edges"] = {"error": repr(exc)}

    except Exception as exc:  # pragma: no cover
        report["error"] = repr(exc)
        print("IMPORT FAILED: %r" % exc, file=sys.stderr)

    text = json.dumps(report, indent=2)
    print("=== BASEMESH BLENDER AUDIT ===")
    print(text)
    if json_out:
        with open(json_out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if report["import_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
