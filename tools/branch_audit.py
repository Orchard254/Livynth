#!/usr/bin/env python3
"""Audit LIVYNTH's local branch/worktree state and emit review evidence.

This is a *review aid for the lead developer*, not a release tool. It reports, in
one place and in a machine-readable form:

  * every worktree: path, branch, HEAD SHA, dirty-file count
  * every local branch and the commits it carries ahead of the base branch
  * whether any binary artefact (GLB, PNG, model weights, ...) has been committed
  * whether `main` is untouched
  * whether pre-existing user changes are still untracked/unstaged
  * optionally, the result of the local test suites

Standard-library Python only, matching `tools/local_check.py`.

Examples:
    python tools/branch_audit.py
    python tools/branch_audit.py --json output/branch_audit.json --run-tests
    python tools/branch_audit.py --base b0235c1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The Windows console default codec (cp1252) cannot encode some characters that
# appear in test output; never let a report line crash the audit.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Artefacts that must never enter Git history for this project.
BINARY_SUFFIXES = {
    ".glb", ".gltf", ".fbx", ".obj", ".blend", ".abc",
    ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".exr", ".hdr",
    ".wav", ".mp3", ".m4a", ".ogg", ".mp4", ".mov",
    ".ckpt", ".pth", ".pt", ".onnx", ".task", ".safetensors", ".bin", ".npy", ".npz",
    ".zip", ".7z", ".tar", ".gz", ".pdf",
}

# User-owned changes that must never be staged or committed by an agent.
PROTECTED_PATHS = ("assets/README.md", "assets/voice_transcript.txt")


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd or ROOT),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def git_ok(*args: str, cwd: Path | None = None) -> bool:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd or ROOT),
        check=False,
        capture_output=True,
    ).returncode == 0


def worktrees() -> list[dict]:
    out = []
    raw = git("worktree", "list", "--porcelain")
    current: dict = {}
    for line in raw.splitlines():
        if not line.strip():
            if current:
                out.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value}
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.replace("refs/heads/", "")
        elif key == "detached":
            current["branch"] = "(detached)"
    if current:
        out.append(current)

    for wt in out:
        path = Path(wt["path"])
        wt["exists"] = path.is_dir()
        dirty = []
        if wt["exists"]:
            status = git("status", "--porcelain", cwd=path)
            dirty = [ln for ln in status.splitlines() if ln.strip()]
        wt["dirty_count"] = len(dirty)
        wt["dirty_sample"] = dirty[:8]
        wt["dirty_files"] = dirty
    return out


def branches(base: str) -> list[dict]:
    out = []
    raw = git("for-each-ref", "--format=%(refname:short)|%(objectname)|%(committerdate:iso8601)|%(subject)",
              "refs/heads/")
    for line in raw.splitlines():
        if not line.strip():
            continue
        name, sha, date, subject = (line.split("|", 3) + ["", "", "", ""])[:4]
        ahead = 0
        # Every branch is counted against the base, including `main`: a moved
        # `main` is exactly the failure this audit must catch.
        count = git("rev-list", "--count", f"{base}..{name}").strip()
        ahead = int(count) if count.isdigit() else 0
        commits = []
        if ahead:
            log = git("log", "--no-merges", "--pretty=format:%H|%s", f"{base}..{name}")
            for entry in log.splitlines():
                if not entry.strip():
                    continue
                csha, _, csubject = entry.partition("|")
                files = [f for f in git("show", "--name-only", "--pretty=format:", csha).splitlines() if f.strip()]
                commits.append({"sha": csha, "subject": csubject, "files": files})
        out.append({
            "branch": name,
            "head": sha,
            "date": date,
            "subject": subject,
            "commits_ahead_of_base": ahead,
            "commits": commits,
        })
    return out


def tracked_binaries() -> list[dict]:
    """Any binary artefact reachable from a local branch."""
    found = []
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        ref = ref.strip()
        if not ref:
            continue
        listing = git("ls-tree", "-r", "--long", ref)
        for line in listing.splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            meta, path = parts
            fields = meta.split()
            if not fields:
                continue
            suffix = Path(path.strip()).suffix.lower()
            if suffix in BINARY_SUFFIXES:
                found.append({"ref": ref, "path": path.strip(), "suffix": suffix})
    return found


def protected_state() -> list[dict]:
    """Report the state of the pre-existing user changes (never staged by agents)."""
    out = []
    status = git("status", "--porcelain", "--untracked-files=all")
    for line in status.splitlines():
        for protected in PROTECTED_PATHS:
            if line[3:].strip().strip('"') == protected or line[3:].strip() == protected:
                out.append({
                    "path": protected,
                    "status": line[:2].strip(),
                    "staged": line[0] not in (" ", "?"),
                })
    return out


def run_suite(label: str, args: list[str]) -> dict:
    proc = subprocess.run([sys.executable, *args], cwd=str(ROOT), check=False,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (proc.stdout or "").strip().splitlines()[-4:]
    return {
        "label": label,
        "command": " ".join([sys.executable, *args]),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "tail": tail,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="b0235c1", help="base commit the branches forked from")
    ap.add_argument("--json", default=None, help="also write the report as JSON to this path")
    ap.add_argument("--run-tests", action="store_true", help="also run the local test suites")
    args = ap.parse_args(argv)

    base = args.base
    wts = worktrees()
    brs = branches(base)
    binaries = tracked_binaries()
    protected = protected_state()

    main_branch = next((b for b in brs if b["branch"] == "main"), None)
    main_untouched = bool(main_branch) and main_branch["commits_ahead_of_base"] == 0 \
        and main_branch["head"] == git("rev-parse", "main").strip()

    report = {
        "tool": "tools/branch_audit.py",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": str(ROOT),
        "base": base,
        "current_branch": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "current_head": git("rev-parse", "HEAD").strip(),
        "worktrees": wts,
        "branches": brs,
        "tracked_binaries": binaries,
        "binary_free": not binaries,
        "protected_user_changes": protected,
        "main_untouched": main_untouched,
        "main_head": main_branch["head"] if main_branch else None,
        "status": git("status", "--porcelain").strip().splitlines(),
        "tests": [],
    }
    if args.run_tests:
        report["tests"].append(run_suite("geo/tests", ["-m", "unittest", "discover", "-s", "geo/tests"]))
        report["tests"].append(run_suite("local_check", [str(Path("tools") / "local_check.py")]))

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")

    print(f"repo        : {ROOT}")
    print(f"branch/HEAD : {report['current_branch']} @ {report['current_head'][:12]}")
    print(f"main        : untouched={main_untouched} head={report['main_head'] and report['main_head'][:12]}")
    print(f"binaries    : {len(binaries)} tracked (must be 0)")
    for b in binaries[:10]:
        print(f"              {b['ref']}:{b['path']}")
    print(f"worktrees   : {len(wts)}")
    for wt in wts:
        print(f"              {wt['path']}\n                {wt.get('branch')} @ "
              f"{(wt.get('head') or '')[:12]} dirty={wt['dirty_count']}")
    print("branches    :")
    for b in brs:
        print(f"              {b['branch']:<40} ahead={b['commits_ahead_of_base']}")
        for c in b["commits"]:
            print(f"                {c['sha'][:12]} {c['subject']} ({len(c['files'])} files)")
    print("protected user changes:")
    for p in protected:
        print(f"              {p['path']} status='{p['status']}' staged={p['staged']}")
    if report["tests"]:
        print("tests       :")
        for t in report["tests"]:
            print(f"              {t['label']}: exit={t['exit_code']} passed={t['passed']}")
            for line in t["tail"]:
                print(f"                {line}")

    return 0 if (report["binary_free"] and main_untouched) else 1


if __name__ == "__main__":
    raise SystemExit(main())
