"""Tests for tools/branch_audit.py.

The audit tool is a review aid for the lead developer, so the properties that
matter are: it must never report a clean repository as unsafe, and it must
actually catch the two failure modes it exists to catch (a committed binary
artefact, and a moved `main`).
"""
from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import branch_audit  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), check=True, capture_output=True, text=True
    ).stdout


@contextlib.contextmanager
def quiet():
    """The audit prints a human report; swallow it during tests."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


class BranchAuditSyntheticRepoTests(unittest.TestCase):
    """Exercise the detection logic against a throwaway git repository."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.repo = Path(self._tmp) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "README.md").write_text("hello\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-m", "initial")
        self.base = git(self.repo, "rev-parse", "HEAD").strip()
        self._orig_root = branch_audit.ROOT
        branch_audit.ROOT = self.repo
        self.addCleanup(setattr, branch_audit, "ROOT", self._orig_root)

    def test_binary_artefact_in_history_is_detected(self) -> None:
        (self.repo / "model.glb").write_bytes(b"\x00\x01\x02fake glb bytes")
        git(self.repo, "add", "model.glb")
        git(self.repo, "commit", "-m", "add binary")
        with quiet():
            found = branch_audit.tracked_binaries()
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0]["path"], "model.glb")
        self.assertEqual(found[0]["suffix"], ".glb")

    def test_text_files_are_not_flagged_as_binaries(self) -> None:
        (self.repo / "notes.md").write_text("not a binary\n", encoding="utf-8")
        git(self.repo, "add", "notes.md")
        git(self.repo, "commit", "-m", "add text")
        with quiet():
            found = branch_audit.tracked_binaries()
        self.assertEqual(found, [])

    def test_model_weights_are_flagged_as_binaries(self) -> None:
        (self.repo / "weights").mkdir()
        (self.repo / "weights" / "model.ckpt").write_bytes(b"\x00" * 32)
        git(self.repo, "add", "weights/model.ckpt")
        git(self.repo, "commit", "-m", "add weights")
        with quiet():
            found = branch_audit.tracked_binaries()
        self.assertEqual([f["suffix"] for f in found], [".ckpt"])

    def test_moved_main_is_detected(self) -> None:
        git(self.repo, "checkout", "-b", "feature")
        (self.repo / "feature.txt").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", "feature.txt")
        git(self.repo, "commit", "-m", "feature work")
        git(self.repo, "checkout", "main")
        (self.repo / "main.txt").write_text("y\n", encoding="utf-8")
        git(self.repo, "add", "main.txt")
        git(self.repo, "commit", "-m", "main moved")
        with quiet():
            branches = branch_audit.branches(self.base)
        main_branch = next(b for b in branches if b["branch"] == "main")
        self.assertGreater(main_branch["commits_ahead_of_base"], 0)

    def test_unchanged_main_is_not_reported_as_moved(self) -> None:
        with quiet():
            branches = branch_audit.branches(self.base)
        main_branch = next(b for b in branches if b["branch"] == "main")
        self.assertEqual(main_branch["commits_ahead_of_base"], 0)

    def test_worktree_listing_reports_branch_and_head(self) -> None:
        with quiet():
            wts = branch_audit.worktrees()
        self.assertTrue(wts)
        entry = next(w for w in wts if Path(w["path"]).resolve() == self.repo.resolve())
        self.assertEqual(entry["branch"], "main")
        self.assertEqual(entry["head"], self.base)
        self.assertEqual(entry["dirty_count"], 0)


class BranchAuditRealRepoTests(unittest.TestCase):
    """The audit's invariants must hold for the actual LIVYNTH checkout."""

    def test_no_binary_artefact_is_tracked(self) -> None:
        with quiet():
            found = branch_audit.tracked_binaries()
        self.assertEqual(found, [], f"binary artefacts are tracked in git: {found}")

    def test_main_is_untouched(self) -> None:
        with quiet():
            branches = branch_audit.branches("b0235c1")
        main_branch = next(b for b in branches if b["branch"] == "main")
        self.assertEqual(main_branch["commits_ahead_of_base"], 0)
        self.assertEqual(main_branch["head"], branch_audit.git("rev-parse", "main").strip())

    def test_user_changes_remain_unstaged(self) -> None:
        with quiet():
            protected = branch_audit.protected_state()
        paths = {p["path"] for p in protected}
        self.assertIn("assets/voice_transcript.txt", paths)
        for p in protected:
            self.assertFalse(p["staged"], f"{p['path']} was staged by an agent")

    def test_audit_runs_and_exits_clean(self) -> None:
        with quiet():
            code = branch_audit.main([])
        self.assertEqual(code, 0, "audit reported the repository as unsafe")


if __name__ == "__main__":
    unittest.main()
