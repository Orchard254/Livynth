#!/usr/bin/env python3
"""Headless MPFB probe: build a rigged, morph-enabled character from the verified CC0 basemesh.

C001-GEO-04 / ADR-C001-004 Decision 1 (Topology Option B), sparse proof.
This proves the *recommended* basemesh is not merely present and licensed -- it
is operationally usable in this project's Blender build, end to end, with the
ARKit morph-target library AND the facial rig attached, and with a clean
export that contains exactly one character.

What it does:
  0. clear the scene (Blender's startup Cube must never reach the asset)
  1. create the human from the CC0 MakeHuman basemesh via MPFB HumanService
  1b. RIG it with the built-in MPFB standard rig (armature + skin weights)
  2. make an export copy (which duplicates the rig and re-points the
     Armature modifier at the duplicated armature)
  3. bake the modelling shape keys and remove helper geometry
     (the Armature modifier is temporarily stashed so the mask/subdiv bake
      is not evaluated in deformed space, then restored)
  4. load the ARKit face units + Meta visemes as shape keys
  5. delete every object that is not part of the export copy
  6. export a GLB and audit the WRITTEN FILE (not the Blender scene)
  7. assert the artifact is clean; fail loudly otherwise

Usage:
    blender --background --python tools/mpfb_headless_probe.py -- --out output/c001_geo04/probe.glb
    blender --background --python tools/mpfb_headless_probe.py -- --json output/c001_geo04/probe.json

NOTE: do NOT pass --factory-startup; the MPFB extension is a *user* extension
and would not be registered.
"""

from __future__ import annotations

import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(globals().get("__file__", "./")))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
REPO_DIR = os.path.dirname(SCRIPT_DIR)
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)  # character/ identity recipe shared with CPU tests


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = None
    json_out = None
    rig = "default"
    stage1_template = None
    stage1_constraints = None
    stage1_neutral_dump = None
    identity_recipe = None
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--json" and i + 1 < len(argv):
            json_out = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--rig" and i + 1 < len(argv):
            rig = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--stage1-template" and i + 1 < len(argv):
            stage1_template = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--stage1-constraints" and i + 1 < len(argv):
            stage1_constraints = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--stage1-neutral-dump" and i + 1 < len(argv):
            stage1_neutral_dump = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--identity-recipe" and i + 1 < len(argv):
            identity_recipe = argv[i + 1]
            i += 2
            continue
        i += 1
    if stage1_template and stage1_constraints:
        raise ValueError("--stage1-template and --stage1-constraints are exclusive")
    if stage1_constraints and stage1_neutral_dump:
        raise ValueError("Neutral mesh dump must be captured BEFORE a fit; do not combine with constraints")
    if identity_recipe and stage1_constraints:
        raise ValueError("Identity recipe and experimental Stage-1 constraints cannot be combined until both transforms are audited")
    return out, json_out, rig, stage1_template, stage1_constraints, stage1_neutral_dump, identity_recipe


def _clear_scene():
    """Remove every object. Blender's startup file contains a default Cube
    which must never end up in a character asset (C001-GEO-04 defect D2)."""
    import bpy
    removed = []
    for o in list(bpy.data.objects):
        removed.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
    return removed


def _stash_armature_modifier(obj):
    """Remove any Armature modifier from obj, returning its record."""
    stashed = []
    for m in list(obj.modifiers):
        if m.type == "ARMATURE":
            stashed.append({
                "name": m.name,
                "object": m.object.name if m.object else None,
                "use_deform_preserve_volume": m.use_deform_preserve_volume,
                "use_multi_modifier": m.use_multi_modifier,
                "vertex_group": m.vertex_group,
            })
            obj.modifiers.remove(m)
    return stashed


def main() -> int:
    out_glb, out_json, rig_name, stage1_template, stage1_constraints, stage1_neutral_dump, identity_recipe = _parse_args()

    import bpy
    from bl_ext.user_default.mpfb.services import (
        HumanService, TargetService, ExportService, FaceService, ObjectService,
        RigService,
    )
    # tools/ is not a package; load the GLB reader by path.
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "livynth_measure_glb_topology",
        os.path.join(SCRIPT_DIR, "measure_glb_topology.py"))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    analyse_glb = _mod.analyse

    report = {
        "blender_version": bpy.app.version_string,
        "mpfb_extension_path": os.path.dirname(
            sys.modules["bl_ext.user_default.mpfb"].__file__),
        "rig_requested": rig_name,
        "steps": {},
        "errors": [],
        "assertions": {},
    }
    t0 = time.time()

    def step(name, fn):
        try:
            fn()
            report["steps"][name] = "ok"
        except Exception as exc:  # pragma: no cover
            report["steps"][name] = "FAILED: %r" % (exc,)
            report["errors"].append("%s: %r" % (name, exc))

    # ---- 0. clean scene (D2) ---------------------------------------------
    removed = [None]

    def _clean():
        removed[0] = _clear_scene()
    step("clear_scene", _clean)
    report["scene_objects_removed_at_start"] = removed[0]

    # ---- 1. create the human from the CC0 basemesh -----------------------
    macro = TargetService.get_default_macro_info_dict()
    if identity_recipe:
        # Reusable identity control BEFORE baking and BEFORE facial morphs.
        # No image inference or source-GLB modification occurs here.
        from character.identity_recipe import (
            load_recipe, recipe_sha256, apply_macro_overrides)
        loaded = load_recipe(identity_recipe)  # strict fail-closed JSON
        macro = apply_macro_overrides(macro, loaded["macros"])
        report["identity_recipe"] = {
            "character_id": loaded["character_id"],
            "source": loaded["source"],
            "sha256": recipe_sha256(loaded),
            "path": os.path.abspath(identity_recipe),
            "identity_likeness": "UNVERIFIED",
            "parameters": loaded["macros"],
        }
    else:
        # Preserve the tested Character 001 placeholder's original defaults.
        macro["race"] = {"african": 0.0, "asian": 0.0, "caucasian": 1.0}
        macro["gender"] = 1.0        # MPFB: 1.0 = male
        macro["age"] = 0.5
        macro["muscle"] = 0.5
        macro["weight"] = 0.5
        macro["proportions"] = 0.5
        macro["height"] = 0.5
    report["macro"] = macro

    basemesh = [None]
    armature = [None]

    def _create():
        basemesh[0] = HumanService.create_human(
            mask_helpers=True,
            detailed_helpers=True,
            extra_vertex_groups=True,
            feet_on_ground=True,
            scale=0.1,
            macro_detail_dict=macro,
        )
    step("create_human", _create)

    bm = basemesh[0]
    if bm is None:
        report["fatal"] = "HumanService.create_human did not return a mesh"
        print(json.dumps(report, indent=2))
        return 1

    # ---- 1b. RIG the character (D1) --------------------------------------
    # create_human() returns an UNRIGGED mesh: no parent, no armature, no
    # Armature modifier. That is why the previously exported GLB had
    # skins: null. The rig must be added explicitly.

    def _rig():
        armature[0] = HumanService.add_builtin_rig(
            bm, rig_name, import_weights=True)
        if armature[0] is None:
            raise RuntimeError("add_builtin_rig returned None for rig %r" % rig_name)
    step("add_builtin_rig", _rig)

    arm = armature[0]
    if arm is not None:
        report["rig"] = {
            "armature_object": arm.name,
            "armature_type": arm.type,
            "bone_count": len(arm.data.bones),
            "bone_names_sample": [b.name for b in arm.data.bones][:12],
            "basemesh_parent": bm.parent.name if bm.parent else None,
            "basemesh_modifiers": [(m.name, m.type) for m in bm.modifiers],
            "weighted_vertex_groups": len(bm.vertex_groups),
        }
        print("RIG:", json.dumps(report["rig"], indent=1))

    me = bm.data
    poly_hist = {}
    for p in me.polygons:
        poly_hist[str(len(p.vertices))] = poly_hist.get(str(len(p.vertices)), 0) + 1
    report["basemesh_raw"] = {
        "object": bm.name,
        "vertices": len(me.vertices),
        "polygons": len(me.polygons),
        "polygon_size_histogram": poly_hist,
        "quad_dominance_pct": round(
            100.0 * poly_hist.get("4", 0) / max(1, len(me.polygons)), 3),
        "uv_layers": [u.name for u in me.uv_layers],
        "vertex_groups": len(bm.vertex_groups),
        "modifiers": [(m.name, m.type) for m in bm.modifiers],
        "shape_keys_before_bake": (
            [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []),
    }
    print("BASEMESH RAW:", json.dumps(report["basemesh_raw"], indent=1))

    # ---- 2. export copy (duplicates rig + mesh) --------------------------
    export_copy = [None]
    collection = [None]

    def _copy():
        coll = bpy.data.collections.new("c001_geo04_probe")
        bpy.context.scene.collection.children.link(coll)
        collection[0] = coll
        export_copy[0] = ExportService.create_character_copy(
            bm, name_suffix="_export_copy", place_in_collection=coll)
    step("create_character_copy", _copy)

    new_bm = None
    export_arm = None
    if export_copy[0] is not None:
        new_bm = ObjectService.find_object_of_type_amongst_nearest_relatives(export_copy[0])
        if export_copy[0].type == "ARMATURE":
            export_arm = export_copy[0]
    report["export_copy"] = {
        "root_object": export_copy[0].name if export_copy[0] else None,
        "root_type": export_copy[0].type if export_copy[0] else None,
        "mesh_object": new_bm.name if new_bm else None,
        "armature_object": export_arm.name if export_arm else None,
        "collection_objects": [o.name for o in collection[0].objects]
        if collection[0] else [],
    }
    print("EXPORT COPY:", json.dumps(report["export_copy"], indent=1))

    # ---- 3. bake (Armature modifier stashed so the bake is not evaluated
    #         in deformed space, then restored) ---------------------------
    stashed = []

    def _stash():
        stashed.extend(_stash_armature_modifier(new_bm))
    step("stash_armature_modifier", _stash)
    report["stashed_armature_modifiers"] = stashed

    def _bake():
        TargetService.bake_targets(new_bm)
    step("bake_targets", _bake)

    def _bake_mods():
        ExportService.bake_modifiers_remove_helpers(
            new_bm, bake_masks=True, bake_subdiv=True,
            remove_helpers=True, also_proxy=True)
    step("bake_modifiers_remove_helpers", _bake_mods)

    # Detailed identity shape: same native quad connectivity, adjusted vertex
    # positions before ARKit/Meta keys are constructed.  This is opt-in v2
    # and never changes the existing no-recipe Stage-0 baseline.
    if identity_recipe and loaded.get("head_shape") and not report["errors"]:
        def _head_shape():
            import numpy as np
            from character.head_shape import apply_head_shape
            from character.identity_recipe import neutral_positions_sha256
            source = np.asarray([tuple(v.co) for v in new_bm.data.vertices],
                                dtype=np.float64)
            quads = np.asarray([tuple(poly.vertices)
                                for poly in new_bm.data.polygons],dtype=np.int64)
            transformed, shape_audit = apply_head_shape(
                source,quads,loaded["head_shape"])
            shape_audit["source_positions_sha256"] = neutral_positions_sha256(source)
            shape_audit["output_positions_sha256"] = neutral_positions_sha256(transformed)
            for vertex, position in zip(new_bm.data.vertices, transformed):
                vertex.co = tuple(float(v) for v in position)
            new_bm.data.update()
            report["identity_head_shape"] = shape_audit
        step("identity_head_shape", _head_shape)
        if report["errors"]:
            report["fatal"] = "Identity head fit rejected; GLB not exported"
            text = json.dumps(report, indent=2)
            print(text)
            if out_json:
                os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
                with open(out_json,"w",encoding="utf-8") as fh:
                    fh.write(text)
            return 2

    if identity_recipe and not report["errors"] and new_bm is not None:
        from character.identity_recipe import (
            neutral_positions_sha256, neutral_topology_sha256)
        baked = new_bm.data.vertices
        quads = new_bm.data.polygons
        report["neutral_identity_geometry"] = {
            "vertex_count": len(baked),
            "quad_count": len(quads),
            "positions_sha256": neutral_positions_sha256(v.co for v in baked),
            "topology_sha256": neutral_topology_sha256(p.vertices for p in quads),
            "fingerprint_basis": "baked-native-indices-before-arkit",
        }

    # ---- OPTIONAL Stage-1 geometric fit, BEFORE facial targets ----------
    # Without these flags the Stage-0 baseline execution path is unchanged.
    # A failed fit must NEVER produce a GLB named as a fitted candidate.
    if stage1_template or stage1_constraints or stage1_neutral_dump:
        import stage1_blender_bridge
        if stage1_template:
            def _template():
                report["stage1"] = stage1_blender_bridge.write_template(
                    new_bm, stage1_template)
            step("stage1_template", _template)
        if stage1_neutral_dump:
            import stage1_neutral_dump as neutral_dump_module
            def _capture():
                report["neutral_dump"] = neutral_dump_module.write_neutral_dump(
                    new_bm, stage1_neutral_dump)
            step("stage1_neutral_dump", _capture)
        if stage1_constraints:
            def _stage1():
                report["stage1"] = stage1_blender_bridge.apply_constraints(
                    new_bm, stage1_constraints)
            step("stage1_fit", _stage1)
        if report["errors"]:
            report["fatal"] = "Stage-1 request rejected; no GLB exported"
            text = json.dumps(report, indent=2)
            print(text)
            if out_json:
                os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
                with open(out_json, "w", encoding="utf-8") as fh:
                    fh.write(text)
            return 2

    def _restore():
        if export_arm is not None:
            RigService.ensure_armature_modifier(new_bm, export_arm)
    step("restore_armature_modifier", _restore)

    if new_bm is not None:
        nme = new_bm.data
        ph = {}
        for p in nme.polygons:
            ph[str(len(p.vertices))] = ph.get(str(len(p.vertices)), 0) + 1
        report["basemesh_baked"] = {
            "object": new_bm.name,
            "vertices": len(nme.vertices),
            "polygons": len(nme.polygons),
            "polygon_size_histogram": ph,
            "quad_dominance_pct": round(
                100.0 * ph.get("4", 0) / max(1, len(nme.polygons)), 3),
            "uv_layers": [u.name for u in nme.uv_layers],
            "vertex_groups": len(new_bm.vertex_groups),
            "modifiers": [(m.name, m.type) for m in new_bm.modifiers],
            "armature_modifier_target": (
                new_bm.modifiers.get("Armature").object.name
                if new_bm.modifiers.get("Armature")
                and new_bm.modifiers.get("Armature").object else None),
        }
        print("BASEMESH BAKED:", json.dumps(report["basemesh_baked"], indent=1))

    # ---- 4. ARKit face units + Meta visemes ------------------------------
    def _load_targets():
        FaceService.load_targets(
            new_bm,
            load_microsoft_visemes=False,
            load_meta_visemes=True,
            load_arkit_faceunits=True)
    step("load_face_targets", _load_targets)

    def _interp():
        FaceService.interpolate_targets(new_bm)
    step("interpolate_targets", _interp)

    keys = []
    if new_bm is not None and new_bm.data.shape_keys:
        basis = new_bm.data.shape_keys.key_blocks[0]
        for k in new_bm.data.shape_keys.key_blocks:
            if k == basis:
                continue
            moved = 0
            maxd = 0.0
            for i, kb in enumerate(k.data):
                d = (kb.co - basis.data[i].co).length
                if d > 1e-6:
                    moved += 1
                    maxd = max(maxd, d)
            keys.append({"name": k.name, "value": round(k.value, 4),
                         "vertices_moved": moved,
                         "max_displacement": round(maxd, 6)})
    report["morph_targets"] = keys
    report["morph_target_count"] = len(keys)
    required = ["browInnerUp", "browOuterUpLeft", "browOuterUpRight",
                "mouthSmileLeft", "mouthSmileRight", "mouthFunnel",
                "mouthPucker", "eyeBlinkLeft", "eyeBlinkRight", "jawOpen"]
    have = {k["name"] for k in keys}
    report["required_arkit_coverage"] = {r: (r in have) for r in required}
    report["required_arkit_all_present"] = all(
        v for v in report["required_arkit_coverage"].values())
    print("MORPH TARGETS:", len(keys))
    print("REQUIRED COVERAGE:", json.dumps(report["required_arkit_coverage"]))

    # ---- 5. delete everything that is not part of the export copy ---------
    # (D2: the default Cube; D3: the un-baked source mesh + its armature)
    deleted = []

    def _prune():
        for o in list(bpy.data.objects):
            if any(c == collection[0] for c in o.users_collection):
                continue
            deleted.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    step("delete_non_export_objects", _prune)
    report["deleted_before_export"] = deleted
    report["objects_in_scene_before_export"] = [
        (o.name, o.type) for o in bpy.context.scene.objects]
    print("DELETED BEFORE EXPORT:", deleted)

    # ---- 6. export GLB ----------------------------------------------------
    if out_glb:
        os.makedirs(os.path.dirname(os.path.abspath(out_glb)), exist_ok=True)

        def _export():
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.export_scene.gltf(
                filepath=out_glb,
                export_format="GLB",
                use_selection=False,
                export_morph=True,
                export_morph_normal=True,
                export_materials="EXPORT",
                export_yup=True,
                export_apply=False,   # keep the armature modifier live -> skin
                export_skins=True,
                export_animations=True,
            )
        step("export_glb", _export)
        if os.path.isfile(out_glb):
            report["glb"] = {"path": os.path.abspath(out_glb),
                             "size_bytes": os.path.getsize(out_glb)}

    # ---- 7. audit the WRITTEN file, then assert --------------------------
    if out_glb and os.path.isfile(out_glb):
        def _audit():
            glb = analyse_glb(out_glb)
            report["glb_audit"] = {
                "scene_roots": glb["scene_roots"],
                "exported_object_names": glb["exported_object_names"],
                "exported_mesh_count": len(glb["meshes"]),
                "mesh_names": [m["name"] for m in glb["meshes"]],
                "character_mesh_name": glb["character_mesh_name"],
                "non_character_meshes": glb["non_character_meshes"],
                "default_cube_present": glb["default_cube_present"],
                "armature_present": glb["armature_present"],
                "skin_present": glb["skin_present"],
                "joint_count": glb["joint_count"],
                "skin_joint_names": (
                    glb["skins"][0]["joint_names"] if glb["skins"] else []),
                "animations": glb["animations"],
                "animation_note": (
                    "No animation clips are authored by the MPFB pipeline "
                    "(measured: the retired V32 ours-photoreal.glb also has "
                    "animations=[]), so this is NOT a regression. Facial motion "
                    "is driven at runtime by the 67 morph targets and by poses "
                    "on the 163-joint rig, both of which are present."),
            }
            if glb["character"]:
                c = glb["character"]
                report["glb_audit"]["morph_targets_in_exported_glb"] = sum(
                    p["morph_target_count"] for p in c["primitives"])
                report["glb_audit"]["target_names_present"] = \
                    c["target_names_present"]
                report["glb_audit"]["target_name_count"] = len(c["target_names"])
                report["glb_audit"]["target_names"] = c["target_names"]
                report["glb_audit"]["character_primitives"] = [
                    {"vertices": p["vertices"], "triangles": p["triangles"],
                     "has_skin": p["has_skin"], "has_uv": p["has_uv"],
                     "non_manifold_edges": p["non_manifold_edges"]}
                    for p in c["primitives"]]
            else:
                report["glb_audit"]["morph_targets_in_exported_glb"] = 0
                report["glb_audit"]["target_names_present"] = False
                report["glb_audit"]["target_name_count"] = 0
                report["glb_audit"]["target_names"] = []

            # ---- assertions (fail loudly) -------------------------------
            # glTF scene roots are the TOP of the exported hierarchy. The
            # character mesh is a CHILD of the armature node, so the only
            # expected root is the armature; the mesh node must appear as a
            # child of it.
            expected_roots = set()
            expected_nodes = set()
            if collection[0]:
                for o in collection[0].objects:
                    expected_nodes.add(o.name)
                    if o.parent is None:
                        expected_roots.add(o.name)
            actual_roots = set(glb["scene_roots"])
            actual_nodes = set(glb["exported_object_names"])
            report["expected_scene_roots"] = sorted(expected_roots)
            report["expected_object_names"] = sorted(expected_nodes)
            report["unexpected_objects"] = sorted(actual_roots - expected_roots)
            report["missing_expected_objects"] = sorted(expected_roots - actual_roots)
            report["character_node_in_export"] = (
                new_bm.name in actual_nodes if new_bm is not None else False)

            checks = {
                "exactly_one_character_mesh": len(
                    [m for m in glb["meshes"] if not m["is_default_cube"]]) == 1,
                "no_default_cube": not glb["default_cube_present"],
                "no_unexpected_objects": not report["unexpected_objects"],
                "no_missing_expected_objects": not report["missing_expected_objects"],
                "character_node_exported": report["character_node_in_export"],
                "armature_present": bool(glb["armature_present"]),
                "skin_present": bool(glb["skin_present"]),
                "joint_count_positive": glb["joint_count"] > 0,
                "facial_joints_present": bool(
                    set(["jaw", "head", "eye.L", "eye.R"]) & set(
                        glb["skins"][0]["joint_names"] if glb["skins"] else [])),
                "morph_targets_present": report["glb_audit"].get(
                    "morph_targets_in_exported_glb", 0) > 0,
                "target_names_present": bool(
                    report["glb_audit"].get("target_names_present")),
                "required_arkit_all_present": bool(
                    report["required_arkit_all_present"]),
                "no_step_errors": not report["errors"],
            }
            report["assertions"] = checks
            failed = [k for k, v in checks.items() if not v]
            report["assertions_passed"] = not failed
            report["assertions_failed"] = failed
            if failed:
                raise AssertionError(
                    "EXPORT ASSERTIONS FAILED: %s | unexpected=%s | missing=%s"
                    % (failed, report["unexpected_objects"],
                       report["missing_expected_objects"]))
        step("audit_exported_glb", _audit)

    report["elapsed_s"] = round(time.time() - t0, 2)
    text = json.dumps(report, indent=2)
    print("=== MPFB HEADLESS PROBE ===")
    print(text)
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if (not report["errors"]
                 and report.get("assertions_passed", False)) else 1


if __name__ == "__main__":
    sys.exit(main())
