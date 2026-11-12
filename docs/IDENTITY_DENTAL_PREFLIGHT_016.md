# IDENTITY-016 — Real MPFB teeth MHCLO preflight after strict-weight failure

Date: 2026-11-12. Status: source fix and hermetic tests authored; Windows retest pending.

## Owner's authoritative Windows failure

Branch experiment/c001-geo05-stage1, after fast-forward d41b676 → c44f6c1.
`python -m unittest discover -s tests -p "test_mhclo_dentition.py" -v`
**14/14 PASS** in 0.157 seconds.

Then `python tools/run_anatomy_ab_review.py --align-accessories --audit-oral-motion --oral-correctives --mhclo-dentition`
opened Blender 4.5.10, created native Head A and loaded eyes, teeth, tongue.
It failed **before copying/rending** at
`character/mhclo_dentition.py` on `E_MHCLO_BAD_WEIGHTS`.
Because no JSON report was produced, the outer wrapper then also printed a
`FileNotFoundError` for anatomy_pose_report.json: this was a downstream symptom,
not a second independent root cause. No new success ZIP exists.

MPFB nodeservice eye-shader socket-name errors appeared earlier in this
same run but did not stop asset import. They are separate material issues.

## Analysis of overstrict input contract

The original mapping validator incorrectly required *each* three-source
MHCLO interpolation weight to be nonnegative AND sum to 1±0.0001.
The source fitting system supports signed interpolation/extrapolation and
uses the three references plus offsets to position fitted assets; the
jaw-classification step does **not** need to reconstruct the geometry.

**Correct decision for jaw ownership:** use the absolute contribution mass
of the three original MHCLO reference coefficients. A tooth vertex can be
assigned lower only if ≥99.9% of that contribution references the documented
lower-teeth helper indices (14992..15059). Upper only if ≥99.9% references
the upper helper indices (15060..15127). A mixed upper/lower, non-dental
significant source, degenerate zero weights or bridging polygon MUST fail.
Never renormalize the source fitting coefficients or permit mixed-jaw
polygons. The classifier preserves unambiguous binary jaw membership.

The real teeth_base.mhclo numerical coefficient distribution was **not**
in the console log. This is a targeted candidate fix to the identified
overstrict condition, not proof the real source will pass its jaw mapping.

## Implemented

- Fix `character/mhclo_dentition.py` to use absolute MHCLO source
  contributions for jaw attribution, not nonnegative/sum-to-one tests.
  Record counts of signed and nonunit-weight vertices, raw sum min/max,
  and first ambiguous vertex's contribution fractions.
- Add five cases to `tests/test_mhclo_dentition.py`: negative and
  nonunit same-jaw coefficients accepted; cross-jaw negative,
  zero-weight, and non-dental negative cases rejected.
- Add `tools/mhclo_dental_preflight.py` to read real original OBJ
  face topology and summarize real MHCLO coefficient distributions.
- Add `tools/mpfb_dental_preflight_blender.py` plus Windows wrapper
  `tools/run_mpfb_dental_preflight.py`. Only reads the owner's
  SHA256-pinned native `teeth_base.mhclo` and referenced OBJ.
  **No human construction, model writes, GLB changes, rendering, or downloads.**
  Writes a fresh JSON status even when the jaw classification fails,
  so debugging does not depend on another expensive render.
- Add 11 regression tests for OBJ indexing, symlink/missing report
  refusal, signed/nonunit summary and fail-closed runner status.

## One lightweight owner acceptance sequence

Run on Windows in `C:\PROJECT\Livynth` on the same experimental branch:

    git pull --ff-only
    python -m unittest discover -s tests -p "test_mhclo_dentition.py" -v
    python -m unittest discover -s tests -p "test_mhclo_dental_preflight.py" -v
    python tools/run_mpfb_dental_preflight.py

The last command produces a dated `output/dental_preflight/.../dentition_probe.json`.
On `PASS_REAL_MHCLO_JAW_GROUP_MAPPING_NOT_VISUAL_QA`, the actual
installed asset's references and mesh jaw ownership have been validated;
then run the original expensive 12-pose A/B command if desired.
On `FAIL_REAL_MHCLO_JAW_GROUP_MAPPING`, upload the small JSON and STOP.
Do not run the full character renderer repeatedly or suppress the
ambiguous helper guard. The report includes the first classification
error and bounded examples of unusual weight triplets.

## Outstanding gate

All previously accepted Head A/B GLBs, 163 bones and 67 face controls
remain untouched. IDENTITY-014 demonstrated oral movement but dental
appearance remains FAIL. IDENTITY-015 visual correction remains unverified.
Character 001 five-view photo likeness is still Phase-3 FAIL.

Official references:
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/entities/clothes/mhclo.md
- https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/clothesservice.md
