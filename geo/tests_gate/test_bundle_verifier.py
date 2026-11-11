"""C001-GEO-04 gate - bundle verifier tests.

The bundle verifier is the mechanism that keeps the review blind.  These
tests prove that a bundle carrying verdict-like material is rejected, that
a tampered bundle is rejected, and that a clean bundle passes.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from geo.gate import bundle


class BundleVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gate_bundle_test_"))
        self.bundle_dir = self.tmp / "bundle"
        self.bundle_dir.mkdir(parents=True)
        (self.bundle_dir / "RUBRIC.md").write_text("judge the views\n", encoding="utf-8")
        (self.bundle_dir / "README.md").write_text("read the rules\n", encoding="utf-8")
        (self.bundle_dir / "ACCESS_RULES.md").write_text("no prior verdict\n", encoding="utf-8")
        cdir = self.bundle_dir / "candidate_CAAAAA"
        cdir.mkdir()
        (cdir / "clay_front.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        (cdir / "camera_convention.json").write_text(json.dumps({"phi": 0.0}), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _manifest(self):
        man = bundle.manifest_for(self.bundle_dir)
        (self.bundle_dir / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
        return man

    def test_clean_bundle_passes(self):
        man = self._manifest()
        res = bundle.verify_bundle(self.bundle_dir, man)
        self.assertTrue(res["ok"], res["problems"])
        self.assertEqual(res["problems"], [])

    def test_verdict_like_file_name_is_rejected(self):
        (self.bundle_dir / "eval.json").write_text("{}", encoding="utf-8")
        self._manifest()
        res = bundle.verify_bundle(self.bundle_dir)
        self.assertFalse(res["ok"])
        kinds = {p["kind"] for p in res["problems"]}
        self.assertIn("forbidden_file_name", kinds)

    def test_backend_hint_in_file_name_is_rejected(self):
        (self.bundle_dir / "candidate_visual_hull.png").write_bytes(b"x")
        self._manifest()
        res = bundle.verify_bundle(self.bundle_dir)
        self.assertFalse(res["ok"])

    def test_verdict_text_in_a_data_file_is_rejected(self):
        (self.bundle_dir / "notes_for_judge.txt").write_text(
            "previous_verdict: ACCEPT", encoding="utf-8")
        self._manifest()
        res = bundle.verify_bundle(self.bundle_dir)
        self.assertFalse(res["ok"])

    def test_tampered_file_breaks_the_manifest(self):
        man = self._manifest()
        (self.bundle_dir / "candidate_CAAAAA" / "clay_front.png").write_bytes(b"tampered")
        res = bundle.verify_bundle(self.bundle_dir, man)
        self.assertFalse(res["ok"])
        self.assertIn("hash_mismatch", {p["kind"] for p in res["problems"]})

    def test_sealed_manifest_mismatch_is_detected(self):
        man = self._manifest()
        other = json.loads(json.dumps(man))
        other["files"][0]["sha256"] = "0" * 64
        res = bundle.verify_bundle(self.bundle_dir, other)
        self.assertFalse(res["ok"])
        self.assertIn("sealed_manifest_mismatch", {p["kind"] for p in res["problems"]})

    def test_extra_file_not_in_manifest_is_detected(self):
        self._manifest()
        (self.bundle_dir / "surprise.bin").write_bytes(b"x")
        res = bundle.verify_bundle(self.bundle_dir)
        self.assertFalse(res["ok"])
        self.assertIn("file_not_in_manifest", {p["kind"] for p in res["problems"]})

    def test_candidate_ids_do_not_leak_the_source(self):
        ids = bundle.make_candidate_ids("run-1", 3, "secret")
        self.assertEqual(len(set(ids)), 3)
        for cid in ids:
            self.assertTrue(cid.startswith("C"))
            self.assertNotIn("hull", cid.lower())
            self.assertNotIn("tripo", cid.lower())


if __name__ == "__main__":
    unittest.main()
