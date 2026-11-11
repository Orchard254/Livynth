"""C001-GEO-04 gate - the orchestrator.

Runs the whole protocol for a set of candidates:

  1. reference analysis (photos, masks, landmarks, skin spans)
  2. per candidate: camera fit, ONE Blender run producing the clay, wire,
     wireframe, depth and normal evidence, the metric set, the artifact QA
  3. per candidate: the identity controls, each rendered and measured again,
     and the control rejection decision
  4. the blinded bundle, its manifest, the sealed label map and the bundle
     verification
  5. the gate report, with gate_valid

gate_valid is FALSE when any control is not rejected.  A gate that cannot
reject a deliberately wrong identity is not a gate.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from . import artifact_qa, bundle, candidate, controls, metrics, reference
from .rubric import RUBRIC_MD

VIEWS = ["front", "left45", "right45", "left90", "right90"]
CONTROL_VIEWS = ["front", "left90", "right90"]

CONTROL_SPECS = [
    {"kind": "face_band_widen", "params": {"factor": 1.18},
     "label": "face band widened 1.18x laterally (the previous canary)"},
    {"kind": "ipd_widen", "params": {"factor": 1.12},
     "label": "inter-ocular distance widened 1.12x"},
    {"kind": "eye_shrink", "params": {"factor": 0.80},
     "label": "eye regions shrunk to 0.80x"},
    {"kind": "nose_lengthen", "params": {"factor": 1.25},
     "label": "nose lengthened 1.25x"},
    {"kind": "jitter", "params": {"sigma_px": 8.0, "seed": 20261111},
     "label": "random vertex jitter, sigma 8 px (the previous canary)"},
    {"kind": "photo_plane", "params": {},
     "label": "face region flattened onto a plane (the projected photograph survives)"},
]


def log(msg, fh):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def write_reference_outputs(ref, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for name, v in ref["views"].items():
        rgb = (np.clip(v["rgb"], 0, 1) * 255).astype(np.uint8)
        p = out_dir / ("reference_%s.png" % name)
        Image.fromarray(rgb).save(p)
        files.append(p)
        mask = (v["foreground"] * 255).astype(np.uint8)
        pm = out_dir / ("reference_mask_%s.png" % name)
        Image.fromarray(mask).save(pm)
        files.append(pm)
    lm = ref["landmarks"]
    front = (np.clip(ref["views"]["front"]["rgb"], 0, 1) * 255).astype(np.uint8)
    ov = front.copy()
    for pt in [lm["eyes"]["left"], lm["eyes"]["right"], lm["chin"]] + list(lm["mouth_corners"]):
        x, y = int(pt[0]), int(pt[1])
        ov[max(0, y - 6):y + 7, max(0, x - 6):x + 7] = [0, 255, 0]
    po = out_dir / "reference_landmarks_front.png"
    Image.fromarray(ov).save(po)
    files.append(po)
    return files


def evaluate_candidate(name, glb_path, ref, rects, out_dir, fh, do_controls=True,
                       reuse=False):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log("candidate %s: loading %s" % (name, glb_path), fh)
    cand = candidate.load_candidate(glb_path)
    calib = candidate.fit_cameras(cand, ref, VIEWS)
    calib_path = out_dir / "camera_fit.json"
    calib_path.write_text(json.dumps(calib, indent=2) + "\n", encoding="utf-8")
    log("candidate %s: camera fitted (front scale ratio vs reference %.4f)"
        % (name, calib["views"]["front"]["scale_ratio_vs_reference"]), fh)
    render_dir = out_dir / "renders"
    if reuse and (render_dir / "render_manifest.json").exists():
        res = {"returncode": 0, "log": str(render_dir), "tail": "reused", "reused": True,
               "problems": [], "ok": True}
    else:
        res = candidate.render_candidate(glb_path, calib_path, render_dir, VIEWS)
    log("candidate %s: blender rc=%s" % (name, res["returncode"]), fh)
    if not res.get("ok", False):
        problems = res.get("problems", ["render verification failed"])
        log("candidate %s: RENDER INCOMPLETE: %s" % (name, "; ".join(problems)), fh)
        raise RuntimeError(
            "candidate %s: render incomplete, refusing to build a blind bundle "
            "from partial evidence: %s" % (name, "; ".join(problems)))
    renders = candidate.load_renders(render_dir, VIEWS)
    textured_rgb = None
    tp = render_dir / "textured_front.png"
    if tp.exists():
        textured_rgb = np.asarray(Image.open(tp).convert("RGB"), dtype=np.float64) / 255.0
    m = metrics.compute_all(cand, ref, calib, renders, rects, textured_rgb)
    art = artifact_qa.audit_glb(glb_path)
    log("candidate %s: artifact QA %s" % (name, art["verdict"]["reasons"]), fh)

    controls_out = []
    if do_controls:
        ipd_m = ref["landmarks"]["ipd_px"] / calib["views"]["front"]["s"]
        for spec in CONTROL_SPECS:
            params = dict(spec["params"])
            if spec["kind"] == "jitter":
                params["sigma_m"] = params.pop("sigma_px") / calib["views"]["front"]["s"]
            if spec["kind"] == "nose_lengthen":
                params["ipd_m"] = ipd_m
            if spec["kind"] == "face_band_widen":
                params["row_range"] = [int(ref["landmarks"]["eye_row"]),
                                       int(ref["landmarks"]["mouth_row"])]
            if spec["kind"] == "ipd_widen":
                half = 0.25 * ref["landmarks"]["ipd_px"]
                params["row_range"] = [int(ref["landmarks"]["eye_row"] - half),
                                       int(ref["landmarks"]["eye_row"] + half)]
            cdir = out_dir / ("control_%s" % spec["kind"])
            cdir.mkdir(parents=True, exist_ok=True)
            cglb = cdir / ("controlled_%s.glb" % spec["kind"])
            cverts, cinfo = controls.apply_control(
                cand["verts"], cand["faces"], spec["kind"], params,
                calib["views"]["front"], rects)
            controls.write_control(glb_path, cglb, cverts, cand["faces"])
            ccand = candidate.load_candidate(cglb)
            ccalib = candidate.fit_cameras(ccand, ref, CONTROL_VIEWS)
            ccalib_path = cdir / "camera_fit.json"
            ccalib_path.write_text(json.dumps(ccalib, indent=2) + "\n", encoding="utf-8")
            crender = cdir / "renders"
            if not (reuse and (crender / "render_manifest.json").exists()):
                cresult = candidate.render_candidate(cglb, ccalib_path, crender,
                                                     CONTROL_VIEWS, passes="clay,textured")
                if not cresult.get("ok", False):
                    log("candidate %s: control %s render INCOMPLETE: %s"
                        % (name, spec["kind"], "; ".join(cresult.get("problems", []))), fh)
                    raise RuntimeError(
                        "candidate %s: control %s render incomplete: %s"
                        % (name, spec["kind"], "; ".join(cresult.get("problems", []))))
            crenders = candidate.load_renders(crender, CONTROL_VIEWS)
            ctex = None
            ctp = crender / "textured_front.png"
            if ctp.exists():
                ctex = np.asarray(Image.open(ctp).convert("RGB"), dtype=np.float64) / 255.0
            cm = metrics.compute_all(ccand, ref, ccalib, crenders, rects, ctex)
            verdict = metrics.control_rejected(m, cm)
            controls_out.append({
                "control": spec["kind"], "label": spec["label"],
                "params": spec["params"], "vertices_changed": cinfo.get("vertices_changed"),
                "rejected": verdict["rejected"],
                "rejected_by": verdict["rejected_by"],
                "appearance_metrics_that_did_not_move":
                    verdict["appearance_metrics_that_did_not_move"],
                "metrics": {k: v for k, v in cm.items() if not k.startswith("_")},
            })
            log("candidate %s: control %s rejected=%s by %s"
                % (name, spec["kind"], verdict["rejected"],
                   [x["metric"] for x in verdict["rejected_by"]]), fh)
    return {"name": name, "glb": str(glb_path), "candidate": cand, "calib": calib,
            "render_dir": render_dir, "renders": renders, "metrics": m,
            "artifact_qa": art, "controls": controls_out}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidate", action="append", required=True,
                    help="NAME=path/to.glb")
    ap.add_argument("--seed-secret", default="c001-geo04")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--reuse-renders", action="store_true")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    logfh = open(out_dir / "gate_run.log", "a", encoding="utf-8")
    log("run %s starting" % args.run_id, logfh)

    ref = reference.load_reference(VIEWS)
    rects = controls.band_rects(ref["landmarks"])
    ref_files = write_reference_outputs(ref, out_dir / "reference_evidence")
    log("reference analysed: ipd %.1f px, eye band %s"
        % (ref["landmarks"]["ipd_px"], ref["eye_band_rect"]), logfh)

    entries = []
    results = []
    camera_json = {}
    for spec in args.candidate:
        name, path = spec.split("=", 1)
        r = evaluate_candidate(name, path, ref, rects, out_dir / ("work_" + name),
                               logfh, do_controls=not args.no_controls,
                               reuse=args.reuse_renders)
        results.append(r)
        render_files = []
        for p in sorted(r["render_dir"].glob("*.png")):
            render_files.append(p)
        entries.append({"glb": path, "render_dir": r["render_dir"],
                        "render_files": render_files, "camera": r["calib"]})
        camera_json[name] = r["calib"]

    built = bundle.build_bundle(out_dir, entries, ref_files, out_dir, camera_json,
                                args.run_id, args.seed_secret)
    verification = bundle.verify_bundle(built["bundle"], built["manifest"])
    log("bundle verification: ok=%s problems=%s"
        % (verification["ok"], verification["problems"]), logfh)

    gate_valid = True
    failure_reasons = []
    for r in results:
        for c in r["controls"]:
            if not c["rejected"]:
                gate_valid = False
                failure_reasons.append("%s: control %s NOT rejected"
                                       % (r["name"], c["control"]))
    if not verification["ok"]:
        gate_valid = False
        failure_reasons.append("bundle verification failed")

    report = {
        "schema": "livynth.c001.gate.report.v1",
        "run_id": args.run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gate_valid": gate_valid,
        "gate_valid_reasons": failure_reasons,
        "views": VIEWS,
        "reference": {
            "ipd_px": ref["landmarks"]["ipd_px"],
            "eye_band_rect": ref["eye_band_rect"],
            "mouth_band_rect": ref["mouth_band_rect"],
            "reference_face_band": ref["reference_face_band"],
            "head_metrics": {k: v["metrics"] for k, v in ref["views"].items()},
        },
        "candidates": [],
        "bundle": {
            "path": str(built["bundle"]),
            "sealed_map": str(built["sealed"] / "blind_map.json"),
            "verdicts_dir": str(built["verdicts"]),
            "manifest_sha256": bundle.sha256_file(built["bundle"] / "MANIFEST.json"),
            "file_count": built["manifest"]["file_count"],
            "verification": verification,
        },
    }
    for r, cid in zip(results, built["ids"]):
        report["candidates"].append({
            "blinded_id": cid,
            "name": r["name"],
            "artifact_qa": r["artifact_qa"],
            "metrics": {k: v for k, v in r["metrics"].items() if not k.startswith("_")},
            "metric_verdicts": metrics.compare_to_reference(r["metrics"]),
            "controls": r["controls"],
            "camera_fit": r["calib"],
        })
    (out_dir / "gate_report.json").write_text(json.dumps(report, indent=2) + "\n",
                                               encoding="utf-8")
    log("gate_valid = %s" % gate_valid, logfh)
    logfh.close()
    print(json.dumps({"gate_valid": gate_valid,
                      "reasons": failure_reasons,
                      "report": str(out_dir / "gate_report.json")}, indent=2))
    return 0 if gate_valid else 2


if __name__ == "__main__":
    sys.exit(main())
