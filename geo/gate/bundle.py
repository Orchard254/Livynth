"""C001-GEO-04 gate - blinded reviewer bundle builder and verifier.

A bundle contains ONLY

  candidate_<ID>/   clay, wire, wireframe, depth, normal and textured renders
                    per view, plus the camera convention used
  reference/        the reference photographs, their silhouette masks and
                    the reference landmark overlay
  RUBRIC.md         the human review rubric
  ACCESS_RULES.md   what a reviewer may open, and the blinding statement
  README.md         what the bundle is
  MANIFEST.json     sha256 of every file in the bundle

and NOTHING that carries a verdict, a previous judge, a backend hint, a
file size or a timing.

The label to candidate map is SEALED OUTSIDE the bundle, in
<run>/sealed/blind_map.json, and is never copied into it.
"""

import hashlib
import json
import random
import re
import shutil
from pathlib import Path

from .rubric import RUBRIC_MD

FORBIDDEN_NAME_PATTERNS = [
    r"eval", r"verdict", r"sign[_-]?off", r"judge", r"score", r"scorecard",
    r"notes?", r"hull", r"triposr", r"tripo", r"marching", r"backend",
    r"source[_-]?glb", r"ground[_-]?truth", r"candidate[_-]?(a|b)\b",
    r"identity[_-]?judge", r"pass[_-]?fail", r"summary", r"report",
]

FORBIDDEN_TEXT_PATTERNS = [
    r"visual[_-]?hull", r"triposr", r"tripo\b", r"marching[_-]?cubes",
    r"eval\.json", r"previous[_-]?verdict", r"sign[_-]?off",
    r"scorecard", r"identity[_-]?judge", r"gate_valid",
]

# documentation files legitimately use the words judge/verdict in their
# instructions to the reviewer, so they are not text scanned
DOC_FILES = {"README.md", "RUBRIC.md", "ACCESS_RULES.md"}

ACCESS_RULES_MD = """# Reviewer access rules (C001-GEO-04)

1. You may open EVERYTHING inside this bundle folder.
2. The bundle contains no previous verdict, no evaluation file, no judge
   notes, no score and nothing that identifies which backend produced a
   candidate.  If you find any of those, the bundle is broken: stop and
   report it.
3. The mapping from candidate id to source model is SEALED OUTSIDE this
   bundle.  Do not ask for it, do not try to infer it from the images, and
   do not accept it from anyone during the review.
4. Do not run any other candidate, do not read any other bundle, and do not
   discuss the candidates with another reviewer before you have written your
   own verdict.
5. Write your verdict OUTSIDE this bundle, into the verdicts folder you were
   given.  Never write into the bundle.
6. Your verdict MUST contain the explicit statement: "I did not read any
   previous verdict, scorecard, evaluation file or judge note while
   producing this verdict."
7. Use the rubric in RUBRIC.md.  The clay renders, the wireframes and the
   depth/normal maps are the geometry evidence; the textured renders are
   diagnostic only.
"""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _png_text_chunks(path):
    data = Path(path).read_bytes()
    out = []
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return out
    off = 8
    while off + 8 <= len(data):
        length = int.from_bytes(data[off:off + 4], "big")
        ctype = data[off + 4:off + 8]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            out.append(data[off + 8:off + 8 + length].decode("utf-8", "replace"))
        off += 12 + length
        if ctype == b"IEND":
            break
    return out


def manifest_for(bundle_dir):
    bundle_dir = Path(bundle_dir)
    files = []
    for p in sorted(bundle_dir.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            files.append({"path": p.relative_to(bundle_dir).as_posix(),
                          "sha256": sha256_file(p)})
    return {"schema": "livynth.c001.gate.bundle-manifest.v1",
            "file_count": len(files), "files": files}


def verify_bundle(bundle_dir, sealed_manifest=None):
    """Assert the bundle is verdict free and matches the sealed manifest."""
    bundle_dir = Path(bundle_dir)
    problems = []
    names = []
    for p in sorted(bundle_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(bundle_dir).as_posix()
        names.append(rel)
        low = rel.lower()
        for pat in FORBIDDEN_NAME_PATTERNS:
            if re.search(pat, low):
                problems.append({"kind": "forbidden_file_name", "file": rel, "pattern": pat})
        if rel in DOC_FILES:
            continue
        if p.suffix.lower() in (".md", ".json", ".txt", ".csv"):
            text = p.read_text(encoding="utf-8", errors="replace")
            for pat in FORBIDDEN_TEXT_PATTERNS:
                if re.search(pat, text, re.IGNORECASE):
                    problems.append({"kind": "forbidden_text", "file": rel, "pattern": pat})
        if p.suffix.lower() == ".png":
            for chunk in _png_text_chunks(p):
                for pat in FORBIDDEN_TEXT_PATTERNS:
                    if re.search(pat, chunk, re.IGNORECASE):
                        problems.append({"kind": "forbidden_png_metadata", "file": rel,
                                         "pattern": pat})
    man_path = bundle_dir / "MANIFEST.json"
    if not man_path.exists():
        problems.append({"kind": "missing_manifest"})
        return {"ok": False, "problems": problems, "file_count": len(names)}
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    listed = {f["path"]: f["sha256"] for f in manifest.get("files", [])}
    actual = set(names) - {"MANIFEST.json"}
    for rel in sorted(actual):
        if rel not in listed:
            problems.append({"kind": "file_not_in_manifest", "file": rel})
    for rel in sorted(listed):
        if rel not in actual:
            problems.append({"kind": "manifest_file_missing", "file": rel})
        else:
            digest = sha256_file(bundle_dir / rel)
            if digest != listed[rel]:
                problems.append({"kind": "hash_mismatch", "file": rel})
    if sealed_manifest is not None:
        sealed = {f["path"]: f["sha256"] for f in sealed_manifest.get("files", [])}
        if sealed != listed:
            problems.append({"kind": "sealed_manifest_mismatch"})
    return {"ok": len(problems) == 0, "problems": problems, "file_count": len(names),
            "manifest_file_count": len(listed)}


def make_candidate_ids(run_id, count, seed_secret):
    rng = random.Random("%s|%s" % (run_id, seed_secret))
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    ids = set()
    while len(ids) < count:
        ids.add("C" + "".join(rng.choice(alphabet) for _ in range(5)))
    return sorted(ids)


def build_bundle(run_dir, entries, reference_files, ref_dir, camera_json_by_id,
                 run_id, seed_secret, extra_readme=""):
    """Assemble the blinded bundle and seal the label map outside it."""
    run_dir = Path(run_dir)
    bundle = run_dir / "bundle"
    sealed = run_dir / "sealed"
    verdicts = run_dir / "verdicts"
    for d in (bundle, sealed, verdicts):
        d.mkdir(parents=True, exist_ok=True)
    ids = make_candidate_ids(run_id, len(entries), seed_secret)
    mapping = []
    for cid, entry in zip(ids, entries):
        cdir = bundle / ("candidate_%s" % cid)
        cdir.mkdir(parents=True, exist_ok=True)
        for src in entry["render_files"]:
            shutil.copy2(src, cdir / Path(src).name)
        (cdir / "camera_convention.json").write_text(
            json.dumps(entry.get("camera", {}), indent=2) + "\n", encoding="utf-8")
        mapping.append({"id": cid, "source_glb": str(entry["glb"]),
                        "source_sha256": sha256_file(entry["glb"]),
                        "render_dir": str(entry["render_dir"])})
    ref_out = bundle / "reference"
    ref_out.mkdir(parents=True, exist_ok=True)
    for src in reference_files:
        shutil.copy2(src, ref_out / Path(src).name)
    (bundle / "RUBRIC.md").write_text(RUBRIC_MD, encoding="utf-8")
    (bundle / "ACCESS_RULES.md").write_text(ACCESS_RULES_MD, encoding="utf-8")
    readme = ["# C001-GEO-04 blinded review bundle", "",
              "Run id: %s" % run_id, "",
              "Each candidate folder holds the geometry evidence (clay, wire,",
              "wireframe, depth, normal) and one diagnostic textured render per",
              "view, plus the camera convention used to produce them.",
              "reference/ holds the reference photographs, their silhouette masks",
              "and the landmark overlay.", "",
              "Read ACCESS_RULES.md and RUBRIC.md before judging.", ""]
    if extra_readme:
        readme.append(extra_readme)
    (bundle / "README.md").write_text("\n".join(readme), encoding="utf-8")
    manifest = manifest_for(bundle)
    (bundle / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                          encoding="utf-8")
    blind_map = {"schema": "livynth.c001.gate.blind-map.v1", "run_id": run_id,
                 "candidates": mapping,
                 "bundle_manifest_sha256": sha256_file(bundle / "MANIFEST.json")}
    (sealed / "blind_map.json").write_text(json.dumps(blind_map, indent=2) + "\n",
                                            encoding="utf-8")
    (sealed / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                  encoding="utf-8")
    return {"bundle": bundle, "sealed": sealed, "verdicts": verdicts,
            "manifest": manifest, "blind_map": blind_map, "ids": ids}
