"""Synthetic regression coverage for safe Phase-3 blinding (no image deps)."""
from __future__ import annotations
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from blind_bundle_preflight import (BlindBundleError, REFERENCES, VIEWS,
    build, inside, png_clean_bytes, required_candidate_files, verify)


def chunk(kind: bytes, data: bytes) -> bytes:
    return len(data).to_bytes(4, "big") + kind + data + (zlib.crc32(kind + data) & 0xffffffff).to_bytes(4, "big")


def png(meta: bool = False) -> bytes:
    # Valid one-pixel RGBA PNG, with an optional backend-identifying text chunk.
    ihdr = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"
    raw = b"\x00\xff\xd0\x10\xff"
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            (chunk(b"tEXt", b"backend\x00visual_hull") if meta else b"") +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class BlindReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "private"
        self.dest = self.root / "judge"
        self.refs = self.source / "references"
        self.refs.mkdir(parents=True)
        for name in REFERENCES:
            (self.refs / name).write_bytes(png(meta=True))
        for label in "AB":
            folder = self.source / label
            folder.mkdir()
            for name in required_candidate_files("geometry"):
                (folder / name).write_bytes(png(meta=True))
        (self.source / "blind_map.sealed.json").write_text('{"A":"visual_hull"}')
        (self.source / "eval.json").write_text('{"A":"ACCEPT"}')

    def test_judge_export_is_geometry_complete_and_strips_metadata(self):
        result = build(self.source, self.dest, ["A", "B"])
        self.assertEqual(result["status"], "SAFE_TO_JUDGE_ONLY")
        self.assertFalse(result["geometry_accepted"])
        self.assertEqual(result["review_files"], 1 + len(REFERENCES) + 2 * len(required_candidate_files("geometry")))
        self.assertFalse((self.dest / "eval.json").exists())
        self.assertFalse((self.dest / "blind_map.sealed.json").exists())
        self.assertNotIn(b"visual_hull", (self.dest / "A" / "front.png").read_bytes())
        self.assertEqual(verify(self.dest, ["A", "B"])["mode"], "geometry")

    def test_malformed_labels_rejected(self):
        for labels in (["A", "A"], ["../secret"], ["triposr"], []):
            with self.assertRaises(BlindBundleError):
                build(self.source, self.dest, labels)

    def test_legacy_private_bundle_is_not_safe_for_judges(self):
        with self.assertRaises(BlindBundleError):
            verify(self.source, ["A", "B"])

    def test_injected_verdict_after_export_fails(self):
        build(self.source, self.dest, ["A", "B"])
        (self.dest / "eval.json").write_text('{"ACCEPT":true}')
        with self.assertRaisesRegex(BlindBundleError, "Prohibited"):
            verify(self.dest, ["A", "B"])

    def test_sealed_map_after_export_fails(self):
        build(self.source, self.dest, ["A"])
        (self.dest / "blind_map.sealed.json").write_text("secret")
        with self.assertRaisesRegex(BlindBundleError, "Prohibited"):
            verify(self.dest, ["A"])

    def test_image_metadata_after_export_fails(self):
        build(self.source, self.dest, ["A"])
        (self.dest / "A" / "front.png").write_bytes(png(meta=True))
        with self.assertRaisesRegex(BlindBundleError, "Metadata-bearing"):
            verify(self.dest, ["A"])

    def test_missing_geometry_blocked(self):
        (self.source / "A" / "clay_front.png").unlink()
        with self.assertRaises(BlindBundleError):
            build(self.source, self.dest, ["A"])
        self.assertFalse(self.dest.exists())

    def test_appearance_mode_not_certified(self):
        result = build(self.source, self.dest, ["A"], mode="appearance-diagnostic")
        self.assertFalse(result["geometry_accepted"])
        self.assertEqual(result["mode"], "appearance-diagnostic")
        with self.assertRaises(BlindBundleError):
            verify(self.dest, ["A"], mode="geometry")

    def test_overlapping_paths_blocked(self):
        with self.assertRaises(BlindBundleError):
            build(self.source, self.source / "judges", ["A"])
        with self.assertRaises(BlindBundleError):
            build(self.source, self.root, ["A"])
        self.assertFalse((self.source / "judges").exists())

    def test_source_is_never_modified(self):
        before = (self.source / "eval.json").read_bytes()
        build(self.source, self.dest, ["A"])
        self.assertEqual((self.source / "eval.json").read_bytes(), before)

    def test_existing_directory_blocked(self):
        self.dest.mkdir()
        (self.dest / "eval.json").write_text("previous verdict")
        with self.assertRaisesRegex(BlindBundleError, "already exists"):
            build(self.source, self.dest, ["A"])
        self.assertTrue((self.dest / "eval.json").is_file())

    def test_corrupt_image_blocked(self):
        (self.source / "A" / "front.png").write_bytes(png()[:-3])
        with self.assertRaises(BlindBundleError):
            build(self.source, self.dest, ["A"])
        self.assertFalse(self.dest.exists())

    def test_symlink_source_blocked(self):
        outside = self.root / "outside.png"
        outside.write_bytes(png())
        src = self.source / "A" / "front.png"
        src.unlink()
        try:
            src.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(BlindBundleError):
            build(self.source, self.dest, ["A"])

    def test_png_validates_crc_and_rejects_unknown_critical(self):
        self.assertEqual(png_clean_bytes(png(meta=True)), png())
        damaged = bytearray(png())
        damaged[20] ^= 255
        with self.assertRaises(BlindBundleError):
            png_clean_bytes(bytes(damaged))

    def test_report_cannot_be_inside_judge_bundle(self):
        build(self.source, self.dest, ["A"])
        from blind_bundle_preflight import main
        rc = main(["verify", "--bundle", str(self.dest), "--labels", "A", "--report", str(self.dest / "eval.json")])
        self.assertEqual(rc, 2)
        self.assertFalse((self.dest / "eval.json").exists())


if __name__ == "__main__":
    unittest.main()