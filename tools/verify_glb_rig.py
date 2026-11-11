#!/usr/bin/env python3
"""Functional verification of a character's rig and morph targets in a GLB.

C001-GEO-04 (ADR-C001-004) artifact QA. AGENTS.md gate 3 asks whether
"any facial rig or blendshapes actually work"; the ADR's artifact-QA list
asks the same. This tool answers it by MEASURING, not by inspecting metadata:

  * imports the GLB into a fresh Blender scene
  * reports the armature, its bones, and the facial control bones
  * reports skin-weight coverage (how many vertices are actually bound)
  * POSES a facial bone (default: the jaw) and measures how far the mesh moves
  * DRIVES a morph target (default: eyeBlinkLeft) and measures how far the mesh moves
  * exits non-zero if the rig or the morph target does not move the mesh

Usage:
    blender --background --python tools/verify_glb_rig.py -- <file.glb> [--json out.json]
    blender --background --python tools/verify_glb_rig.py -- <file.glb> --bone jaw --morph eyeBlinkLeft
"""

from __future__ import annotations

import json
import math
import os
import sys


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    path = None
    json_out = None
    bone = "jaw"
    morph = "eyeBlinkLeft"
    i = 0
    while i < len(argv):
        if argv[i] == "--json" and i + 1 < len(argv):
            json_out = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--bone" and i + 1 < len(argv):
            bone = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--morph" and i + 1 < len(argv):
            morph = argv[i + 1]
            i += 2
            continue
        if path is None:
            path = argv[i]
        i += 1
    return path, json_out, bone, morph


def _mesh_coords(obj):
    import bpy
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = [0.0] * (n * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    return co


def _max_delta(a, b):
    m = 0.0
    moved = 0
    for i in range(0, len(a), 3):
        dx = a[i] - b[i]
        dy = a[i + 1] - b[i + 1]
        dz = a[i + 2] - b[i + 2]
        d = (dx * dx + dy * dy + dz * dz) ** 0.5
        if d > 1e-6:
            moved += 1
            if d > m:
                m = d
    return m, moved


def main() -> int:
    import bpy
    import mathutils

    path, json_out, bone_name, morph_name = _parse_args()
    if not path or not os.path.isfile(path):
        print("ERROR: glb not found: %r" % path, file=sys.stderr)
        return 2

    report = {"glb": os.path.abspath(path), "errors": []}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)

    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    report["scene_objects"] = [(o.name, o.type) for o in bpy.data.objects]
    report["armature_count"] = len(armatures)
    report["mesh_count"] = len(meshes)

    if not armatures:
        report["errors"].append("no armature in the imported GLB")
        print(json.dumps(report, indent=2))
        return 1
    if not meshes:
        report["errors"].append("no mesh in the imported GLB")
        print(json.dumps(report, indent=2))
        return 1

    arm = armatures[0]
    mesh = max(meshes, key=lambda o: len(o.data.vertices))
    bones = [b.name for b in arm.data.bones]
    lower = {b.lower(): b for b in bones}
    report["armature"] = {
        "name": arm.name,
        "bone_count": len(bones),
        "facial_bones": sorted(b for b in bones if any(
            t in b.lower() for t in ("jaw", "head", "neck", "eye", "orbicular"))),
    }
    report["mesh"] = {
        "name": mesh.name,
        "vertices": len(mesh.data.vertices),
        "polygons": len(mesh.data.polygons),
        "has_armature_modifier": any(
            m.type == "ARMATURE" for m in mesh.modifiers),
        "vertex_groups": len(mesh.vertex_groups),
        "shape_keys": ([k.name for k in mesh.data.shape_keys.key_blocks]
                       if mesh.data.shape_keys else []),
    }
    print("ARMATURE:", json.dumps(report["armature"], indent=1))
    print("MESH:", json.dumps(report["mesh"], indent=1))

    # ---- skin weight coverage --------------------------------------------
    bound = 0
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.weight > 1e-4:
                bound += 1
                break
    report["skin_weight_coverage"] = {
        "vertices_total": len(mesh.data.vertices),
        "vertices_bound": bound,
        "bound_pct": round(100.0 * bound / max(1, len(mesh.data.vertices)), 3),
    }
    print("SKIN WEIGHT COVERAGE:", json.dumps(report["skin_weight_coverage"]))

    # ---- functional test 1: pose a facial bone ---------------------------
    target_bone = lower.get(bone_name.lower())
    report["bone_test"] = {"requested": bone_name, "found": bool(target_bone)}
    if target_bone:
        bpy.context.view_layer.objects.active = arm
        arm.select_set(True)
        pb = arm.pose.bones[target_bone]
        before = _mesh_coords(mesh)
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(20.0), 0.0, 0.0)
        bpy.context.view_layer.update()
        after = _mesh_coords(mesh)
        maxd, moved = _max_delta(before, after)
        report["bone_test"].update({
            "bone": target_bone,
            "rotation_deg": 20.0,
            "max_vertex_displacement": round(maxd, 6),
            "vertices_moved": moved,
            "works": moved > 0,
        })
        # restore
        pb.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
    print("BONE TEST:", json.dumps(report["bone_test"], indent=1))

    # ---- functional test 2: drive a morph target -------------------------
    report["morph_test"] = {"requested": morph_name}
    sk = mesh.data.shape_keys
    if sk:
        kb = sk.key_blocks.get(morph_name)
        if kb is None:
            # case-insensitive fallback
            for k in sk.key_blocks:
                if k.name.lower() == morph_name.lower():
                    kb = k
                    break
        if kb is not None:
            before = _mesh_coords(mesh)
            kb.value = 1.0
            bpy.context.view_layer.update()
            after = _mesh_coords(mesh)
            maxd, moved = _max_delta(before, after)
            kb.value = 0.0
            bpy.context.view_layer.update()
            report["morph_test"].update({
                "shape_key": kb.name,
                "max_vertex_displacement": round(maxd, 6),
                "vertices_moved": moved,
                "works": moved > 0,
            })
        else:
            report["morph_test"]["error"] = "shape key not found"
            report["errors"].append("shape key %r not found" % morph_name)
    else:
        report["morph_test"]["error"] = "mesh has no shape keys"
        report["errors"].append("mesh has no shape keys")
    print("MORPH TEST:", json.dumps(report["morph_test"], indent=1))

    # ---- verdict ----------------------------------------------------------
    checks = {
        "armature_present": report["armature_count"] > 0,
        "facial_bones_present": bool(report["armature"]["facial_bones"]),
        "mesh_bound_to_skin": report["skin_weight_coverage"]["bound_pct"] > 50.0,
        "bone_pose_moves_mesh": bool(report["bone_test"].get("works")),
        "morph_target_moves_mesh": bool(report["morph_test"].get("works")),
    }
    report["checks"] = checks
    report["checks_passed"] = all(checks.values())
    report["checks_failed"] = [k for k, v in checks.items() if not v]
    text = json.dumps(report, indent=2)
    print("=== GLB RIG VERIFICATION ===")
    print(text)
    if json_out:
        os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if report["checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
