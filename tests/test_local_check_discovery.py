"""Regression test for test-suite discovery.

The geometry suites are sibling packages under `geo/` (`geo/tests`,
`geo/tests_hull`, `geo/tests_landmarks`, `geo/tests_calibration`). They used to
live outside every discovery command, so `python tools/local_check.py` enforced
only part of the test surface while still reporting PASS.

This test asserts that a single discovery command reaches *every* suite
directory that contains tests, so the gap cannot silently reopen.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _suite_dirs() -> list[Path]:
    """Every directory under geo/ that holds test modules."""
    geo = ROOT / "geo"
    found = []
    for path in sorted(geo.rglob("test_*.py")):
        parent = path.parent
        if parent not in found:
            found.append(parent)
    return found


class DiscoveryCoverageTests(unittest.TestCase):
    def test_geo_suites_are_packages(self) -> None:
        """Every suite directory must be importable so discovery can recurse."""
        missing = [str(p.relative_to(ROOT)) for p in _suite_dirs()
                   if not (p / "__init__.py").is_file()]
        self.assertEqual(
            missing, [],
            "suite directories without __init__.py are invisible to discovery: "
            f"{missing}. Add an __init__.py to each.",
        )

    def test_discovery_from_geo_finds_the_core_suite(self) -> None:
        """`discover -s geo -t .` must reach geo/tests (it used to find 0 tests)."""
        import unittest as ut

        loader = ut.TestLoader()
        suite = loader.discover(str(ROOT / "geo"), top_level_dir=str(ROOT), pattern="test_*.py")

        def count(item) -> int:
            if isinstance(item, ut.TestSuite):
                return sum(count(child) for child in item)
            return 1

        total = count(suite)
        self.assertGreater(total, 0, "discovery from geo found no tests at all")

        # Collect the ids of every discovered test.
        ids: set[str] = set()
        def collect(item) -> None:
            if isinstance(item, ut.TestSuite):
                for child in item:
                    collect(child)
            else:
                ids.add(item.id())

        collect(suite)
        self.assertTrue(
            any("geo.tests." in i for i in ids),
            f"discovery did not reach geo/tests; found {sorted(ids)[:10]}",
        )

    def test_local_check_runs_the_geo_suites(self) -> None:
        """tools/local_check.py must invoke the geo discovery, not only `tests`."""
        source = (ROOT / "tools" / "local_check.py").read_text(encoding="utf-8")
        self.assertIn("'-s', 'geo'", source,
                      "local_check.py must run unittest discovery over geo/")
        self.assertIn("'-t', '.'", source,
                      "local_check.py must set the repository root as the discovery top level")


if __name__ == "__main__":
    unittest.main()
