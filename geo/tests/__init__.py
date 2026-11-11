"""LIVYNTH geometry test package.

This package marker exists so that `python -m unittest discover -s geo -t .`
recurses into this directory. Without it, `unittest` refuses to descend into a
directory that is not a package, and the sibling suites (`geo/tests_hull`,
`geo/tests_landmarks`, `geo/tests_calibration`) were reachable by no discovery
command at all -- meaning `python tools/local_check.py` silently enforced only
part of the test surface.

See `tools/local_check.py` and `tests/test_local_check_discovery.py`.
"""
