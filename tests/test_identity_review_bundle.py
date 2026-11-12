"""Portable IDENTITY-007 visual evidence pack; zero GLBs/photos/weights."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib

from tools.identity_pose_review import SCHEMA, CHARACTERS, render_jobs
from tools.package_identity_pose_review import (
    create_bundle, prepare_review_bundle, ReviewBundleError, evidence_paths,
    BUNDLE_SCHEMA,
)


def _png(width=400, height=600):
    def chunk(label, data):
        return (struct.pack(">I",len(data))+label+data+
                struct.pack(">I",zlib.crc32(label+data)&0xffffffff))
    header=struct.pack(">IIBBBBB",width,height,8,6,0,0,0)
    row=b"\x00"+b"\x27\x36\x45\xff"*width
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",header)+
            chunk(b"IDAT",zlib.compress(row*height,6))+chunk(b"IEND",b""))


def _fixture(root):
    root.mkdir(parents=True, exist_ok=False)
    report={"schema":SCHEMA,
            "status":"CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW",
            "character_count":2, "existing_glb_morph_signal":"PASS",
            "raster_signal":"PASS_VISIBLE_DIFFERENCES_NOT_VISUAL_QUALITY",
            "expression_naturalness":"PENDING_HUMAN_REVIEW"}
    (root/"pose_review.json").write_text(json.dumps(report),encoding="utf-8")
    # Ensure arbitrary source HTML is NOT copied to the portable archive.
    (root/"index.html").write_text("<script>malicious_source_placeholder()</script>",
                                   encoding="utf-8")
    for character in CHARACTERS:
        char_folder=root/character
        char_folder.mkdir()
        images=[]
        for view,pose,weights in render_jobs():
            path=char_folder/f"{view}_{pose}.png"
            path.write_bytes(_png())
            images.append({"view":view,"pose":pose,
                           "path":str(path.resolve()),"weights":weights,
                           "rendered_motion":None if pose=="neutral" else {
                               "status":"SIGNAL_PRESENT_NOT_VISUAL_APPROVAL",
                               "changed_face_samples":40,
                               "total_face_samples":200}})
        character_report={"schema":SCHEMA,
                          "status":"CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW",
                          "native_animation_interface":"EXPORTED_MORPH_SIGNAL_VERIFIED",
                          "character_id":character,
                          "renders":images}
        (char_folder/"render_report.json").write_text(
            json.dumps(character_report),encoding="utf-8")
    return report


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"pose_review"
        self.report=_fixture(self.root)
    def test_complete_portable_review_has_only_approved_files(self):
        # Deliberately present sensitive source binary not permitted in ZIP.
        (self.root/"demo_head_a.glb").write_bytes(b"private geometry")
        (self.root/"source_reference.jpg").write_bytes(b"private photo")
        destination, manifest=create_bundle(self.root)
        self.assertTrue(destination.is_file())
        self.assertEqual(manifest["schema"],BUNDLE_SCHEMA)
        self.assertEqual(manifest["status"],"PORTABLE_EVIDENCE_NOT_HUMAN_VISUAL_APPROVAL")
        with zipfile.ZipFile(destination) as archive:
            names=set(archive.namelist())
            self.assertEqual(len(names),25)
            self.assertEqual(sum(name.endswith(".png") for name in names),20)
            self.assertNotIn("demo_head_a.glb",names)
            self.assertNotIn("source_reference.jpg",names)
            self.assertEqual(set(manifest["included_files"]),names-{"bundle_manifest.json"})
            for name, meta in manifest["included_files"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),
                                 meta["sha256"])
            self.assertNotIn(b"malicious_source_placeholder",archive.read("index.html"))
            self.assertEqual(archive.read("index.html").count(b"<img "),20)
    def test_existing_archive_cannot_be_overwritten(self):
        target=self.root.with_suffix(".zip")
        target.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError):
            create_bundle(self.root)
        self.assertEqual(target.read_bytes(),b"preserve")
    def test_missing_pose_blocks_bundle(self):
        (self.root/"demo_head_b/front_viseme_pp.png").unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):
            prepare_review_bundle(self.root)
    def test_corrupt_png_blocks_bundle(self):
        path=self.root/"demo_head_a/front_blink.png"
        data=bytearray(path.read_bytes());data[29]^=0x80;path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,"E_PNG_CRC"):
            prepare_review_bundle(self.root)
    def test_summary_cannot_claim_naturalness_pass(self):
        data=dict(self.report,expression_naturalness="PASS")
        (self.root/"pose_review.json").write_text(json.dumps(data),encoding="utf-8")
        with self.assertRaisesRegex(ReviewBundleError,"E_REVIEW_SUMMARY"):
            prepare_review_bundle(self.root)
    def test_symlink_to_outside_file_rejected(self):
        outside=Path(self.temp.name)/"secret.txt"
        outside.write_text("must not leak")
        target=self.root/"demo_head_a/front_blink.png"
        target.unlink()
        try:
            target.symlink_to(outside)
        except (OSError,NotImplementedError):
            self.skipTest("Symlinks not available")
        with self.assertRaisesRegex(ReviewBundleError,"E_SYMLINK_BLOCKED"):
            prepare_review_bundle(self.root)
    def test_evidence_entries_all_fixed(self):
        paths=evidence_paths(self.root)
        self.assertEqual(len(paths),24)
        self.assertTrue(all(".." not in p.parts and not p.is_absolute() for p in paths))


if __name__=="__main__":
    unittest.main()
