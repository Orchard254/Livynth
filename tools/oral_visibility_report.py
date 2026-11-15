#!/usr/bin/env python3
"""IDENTITY-029: measure the rendered oral diagnostics (system Python).

Reads the diagnostic PNGs produced by ``tools.oral_visibility_blender``
and turns them into numbers with ``character.oral_visibility``:

* **dental visibility** - the fraction of each arch's silhouette that
  survives the lips, the opposite arch and the tongue;
* **aperture shape** - the outline of the oral opening and its
  dimensionless V-score.

The tool never touches a source asset; it only reads the PNGs of the
current run folder.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from character.oral_visibility import (
    SCHEMA, OralVisibilityError, aperture_profile, alpha_mask,
    cavity_aperture_mask, classify_arch_pixels, visibility_metrics,
    dark_aperture_mask)
from tools.oral_visibility_blender import (
    COLOR_TOLERANCE, DIAG_CAVITY_RGB, DIAG_LOWER_RGB, DIAG_UPPER_RGB)

METRICS_SCHEMA = 'livynth.oral-visibility.metrics.v1'


class OralVisibilityReportError(ValueError):
    pass


def _load(path):
    """Load a PNG as float RGBA in [0, 1]."""
    from PIL import Image
    path = Path(path)
    if not path.is_file():
        raise OralVisibilityReportError('E_ORAL_VIS_MISSING_' + path.name)
    with Image.open(path) as image:
        return np.asarray(image.convert('RGBA'), dtype=np.float64) / 255.0


def _arch_masks(path, *, tolerance=COLOR_TOLERANCE):
    image = _load(path)
    rgb = image[:, :, :3]
    masks = classify_arch_pixels(
        rgb, upper_color=DIAG_UPPER_RGB, lower_color=DIAG_LOWER_RGB,
        tolerance=tolerance)
    foreground = alpha_mask(image)
    return {key: value & foreground for key, value in masks.items()}


def measure_pose(folder, pose, *, stage, tolerance=COLOR_TOLERANCE):
    """Measure one pose from the diagnostic PNGs of one stage."""
    folder = Path(folder)
    prefix = 'diag_%s_%s' % (stage, pose)
    upper_only = _arch_masks(folder / (prefix + '_upper_arch.png'),
                             tolerance=tolerance)
    lower_only = _arch_masks(folder / (prefix + '_lower_arch.png'),
                             tolerance=tolerance)
    both = _arch_masks(folder / (prefix + '_arches.png'),
                       tolerance=tolerance)
    visible = _arch_masks(folder / (prefix + '_visible.png'),
                          tolerance=tolerance)
    # Use dark aperture mask on the VISIBLE render (clay exterior)
    # rather than the cavity render which shows the full interior.
    visible_image = _load(folder / (prefix + '_visible.png'))
    aperture = dark_aperture_mask(
        visible_image[:, :, :3], max_luma=0.42) & alpha_mask(visible_image)
    record = {
        'stage': stage,
        'pose': pose,
        'upper_visibility': visibility_metrics(
            upper_only['upper'], visible['upper']),
        'lower_visibility': visibility_metrics(
            lower_only['lower'], visible['lower']),
        'arch_classification': {
            'both_arches_pixels': int(both['upper'].sum() + both['lower'].sum()),
            'upper_pixels': int(both['upper'].sum()),
            'lower_pixels': int(both['lower'].sum()),
            'overlap_pixels': int((both['upper'] & both['lower']).sum()),
        },
        'visible_pixels': {
            'upper': int(visible['upper'].sum()),
            'lower': int(visible['lower'].sum()),
        },
    }
    if aperture.any():
        record['aperture'] = aperture_profile(aperture)
    else:
        record['aperture'] = None
        record['aperture_note'] = 'NO_VISIBLE_ORAL_APERTURE_IN_THIS_POSE'
    return record


def measure_stage(folder, poses, *, stage, tolerance=COLOR_TOLERANCE):
    records = {}
    for pose in poses:
        records[pose] = measure_pose(folder, pose, stage=stage,
                                     tolerance=tolerance)
    return records


def compare_stages(before, after):
    """Before/after deltas for the aperture shape and visibility."""
    deltas = {}
    for pose, record in after.items():
        old = before.get(pose)
        if old is None:
            continue
        entry = {}
        old_aperture = old.get('aperture')
        new_aperture = record.get('aperture')
        if old_aperture and new_aperture:
            entry['v_score_before'] = old_aperture['v_score']
            entry['v_score_after'] = new_aperture['v_score']
            entry['v_score_delta'] = round(
                new_aperture['v_score'] - old_aperture['v_score'], 6)
            entry['aperture_area_px_before'] = old_aperture['area_px']
            entry['aperture_area_px_after'] = new_aperture['area_px']
        for arch in ('upper', 'lower'):
            key = arch + '_visibility'
            entry[key + '_before'] = old[key]['visible_fraction']
            entry[key + '_after'] = record[key]['visible_fraction']
        deltas[pose] = entry
    return deltas


def analyse(folder, *, poses, stages=('before', 'after'),
            tolerance=COLOR_TOLERANCE):
    folder = Path(folder)
    measured = {}
    for stage in stages:
        try:
            measured[stage] = measure_stage(folder, poses, stage=stage,
                                            tolerance=tolerance)
        except OralVisibilityReportError as exc:
            if stage == 'after':
                raise
            measured[stage] = {'_unavailable': str(exc)}
    report = {
        'schema': METRICS_SCHEMA,
        'module_schema': SCHEMA,
        'folder': str(folder),
        'poses': list(poses),
        'stages': list(stages),
        'color_tolerance': float(tolerance),
        'measured': measured,
    }
    if 'before' in measured and 'after' in measured and \
            '_unavailable' not in measured['before']:
        report['deltas'] = compare_stages(measured['before'],
                                          measured['after'])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pose', action='append', default=None)
    parser.add_argument('--stage', action='append', default=None)
    parser.add_argument('--tolerance', type=float, default=COLOR_TOLERANCE)
    args = parser.parse_args(argv)
    poses = tuple(args.pose or ('neutral', 'jaw_open', 'viseme_aa',
                                 'viseme_pp'))
    stages = tuple(args.stage or ('before', 'after'))
    try:
        report = analyse(args.folder, poses=poses, stages=stages,
                         tolerance=args.tolerance)
    except (OralVisibilityError, OralVisibilityReportError) as exc:
        parser.exit(2, 'LIVYNTH IDENTITY-029 ORAL VISIBILITY FAIL: ' +
                     str(exc) + '\n')
    args.out.write_text(json.dumps(report, indent=2) + '\n',
                        encoding='utf-8')
    print(json.dumps({
        'status': 'MEASURED',
        'poses': list(poses),
        'stages': list(stages),
        'out': str(args.out),
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
