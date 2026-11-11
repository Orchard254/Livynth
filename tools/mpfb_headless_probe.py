#!/usr/bin/env python3
"""Headless MPFB sparse proof: build a character from the verified CC0 basemesh.

C001-GEO-04 / ADR-C001-004 Decision 1 (Topology Option B), sparse proof.
This proves the *recommended* basemesh is not merely present and licensed -- it
is operationally usable in this project's Blender build, end to end, with the
ARKit morph-target library attached.

What it does (mirrors the proven `our_avatar/build_photoreal.py` pipeline):
  1. create the human from the CC0 MakeHuman basemesh via MPFB HumanService
  2. bake the modelling shape keys and remove helper geometry
  3. load the ARKit face units + Meta visemes as shape keys
  4. report measured topology + the morph-target inventory
  5. export a GLB (to a git-ignored output dir) for downstream measurement

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


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = None
    json_out = None
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
        i += 1
    return out, json_out


def main() -> int:
    out_glb, out_json = _parse_args()

    import bpy
    from bl_ext.user_default.mpfb.services import (
        HumanService, TargetService, ExportService, FaceService, ObjectService,
    )

    report = {
        "blender_version": bpy.app.version_string,
        "mpfb_extension_path": os.path.dirname(
            sys.modules["bl_ext.user_default.mpfb"].__file__),
        "steps": {},
        "errors": [],
    }
    t0 = time.time()

    def step(name, fn):
        try:
            fn()
            report["steps"][name] = "ok"
        except Exception as exc:  # pragma: no cover
            report["steps"][name] = "FAILED: %r" % (exc,)
            report["errors"].append("%s: %r" % (name, exc))

    # ---- 1. create the human from the CC0 basemesh -----------------------
    macro = TargetService.get_default_macro_info_dict()
    # Character 001 is an adult man; use the closest available macro preset.
    macro["race"] = {"african": 0.0, "asian": 0.0, "caucasian": 1.0}
    macro["gender"] = 1.0        # MakeHuman convention: 1.0 = male
    macro["age"] = 0.5
    macro["muscle"] = 0.5
    macro["weight"] = 0.5
    macro["proportions"] = 0.5
    macro["height"] = 0.5
    report["macro"] = macro

    basemesh = [None]

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

    # ---- 2. export copy + bake ------------------------------------------
    export_copy = [None]

    def _copy():
        coll = bpy.data.collections.new("c001_geo04_probe")
        bpy.context.scene.collection.children.link(coll)
        export_copy[0] = ExportService.create_character_copy(
            bm, name_suffix="_export_copy", place_in_collection=coll)
    step("create_character_copy", _copy)

    new_bm = None
    if export_copy[0] is not None:
        new_bm = ObjectService.find_object_of_type_amongst_nearest_relatives(export_copy[0])

    def _bake():
        TargetService.bake_targets(new_bm)
    step("bake_targets", _bake)

    def _bake_mods():
        ExportService.bake_modifiers_remove_helpers(
            new_bm, bake_masks=True, bake_subdiv=True,
            remove_helpers=True, also_proxy=True)
    step("bake_modifiers_remove_helpers", _bake_mods)

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
        }
        print("BASEMESH BAKED:", json.dumps(report["basemesh_baked"], indent=1))

    # ---- 3. ARKit face units + Meta visemes ------------------------------
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
    report["required_arkit_all_present"] = all(v for v in
                                                report["required_arkit_coverage"].values())
    print("MORPH TARGETS:", len(keys))
    print("REQUIRED COVERAGE:", json.dumps(report["required_arkit_coverage"]))

    # ---- 4. export GLB ----------------------------------------------------
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
                export_apply=False,
            )
        step("export_glb", _export)
        if os.path.isfile(out_glb):
            report["glb"] = {"path": os.path.abspath(out_glb),
                             "size_bytes": os.path.getsize(out_glb)}

    report["elapsed_s"] = round(time.time() - t0, 2)
    text = json.dumps(report, indent=2)
    print("=== MPFB HEADLESS PROBE ===")
    print(text)
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
