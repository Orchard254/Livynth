#!/usr/bin/env python3
"""Texture-independent 3D face deformation audit and wrong-identity canary.

This is a *falsification test*, NOT an identity-likeness or scan-accuracy score.
It intentionally ignores images, material/UV data, facial projections, and
similarity alignment. It operates on real GLB mesh VERTEX POSITIONS in meters.

Examples:
  python -m geo.geometry_falsification --source original.glb --mesh GLTF_4 \
    --head-range 1.50 1.77 --axis y --out output/c001_geom_audit.json
  python -m geo.geometry_falsification --source original.glb \
    --candidate fitted.glb --mesh GLTF_4 --head-range 1.50 1.77 \
    --out output/c001_geom_comparison.json
  python -m geo.geometry_falsification --source original.glb --list-meshes

For skinned meshes this reads bind-pose geometry, not animated/deformed frames.
Neither matching the source nor passing the canary proves the source is correct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

AXIS = {'x': 0, 'y': 1, 'z': 2}


@dataclass(frozen=True)
class Geometry:
    vertices: np.ndarray
    faces: np.ndarray
    mesh_name: str
    node_name: str
    file_sha256: str


def load_geometry(path: Path, mesh_name: str | None, node_name: str | None = None) -> Geometry:
    """Load exactly one mesh instance; do not silently concatenate other nodes."""
    import trimesh
    path = Path(path)
    if path.suffix.lower() not in ('.glb', '.gltf'):
        raise ValueError('Expect a glTF/GLB mesh')
    scene = trimesh.load(path, force='scene', process=False)
    options = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph[node]
        if mesh_name is not None and geom_name != mesh_name:
            continue
        if node_name is not None and node != node_name:
            continue
        options.append((node, geom_name, transform))
    if len(options) != 1:
        inventory = [(node, scene.graph[node][1]) for node in scene.graph.nodes_geometry]
        raise ValueError(f'Expected one mesh instance; found {len(options)}. Available nodes/meshes: {inventory}. Supply --mesh and/or --node.')
    node, name, transform = options[0]
    mesh = scene.geometry[name]
    if not hasattr(mesh, 'faces') or len(mesh.faces) == 0:
        raise ValueError(f'{name} is not a triangulated surface')
    v = np.asarray(mesh.vertices, dtype=np.float64)
    f = np.asarray(mesh.faces, dtype=np.int64)
    if not np.all(np.isfinite(v)):
        raise ValueError('Non-finite vertices')
    v = (np.column_stack((v, np.ones(len(v)))) @ np.asarray(transform).T)[:, :3]
    return Geometry(v, f, name, node, hashlib.sha256(path.read_bytes()).hexdigest())


def inventory(path: Path) -> list[dict]:
    import trimesh
    scene = trimesh.load(path, force='scene', process=False)
    return [{'node': str(node), 'mesh': str(scene.graph[node][1]),
             'vertices': len(scene.geometry[scene.graph[node][1]].vertices),
             'triangles': len(scene.geometry[scene.graph[node][1]].faces)}
            for node in scene.graph.nodes_geometry]


def head_mask(vertices: np.ndarray, up: int, low: float, high: float) -> np.ndarray:
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError('Head-range must have finite lower < upper')
    mask = (vertices[:, up] >= low) & (vertices[:, up] <= high)
    if np.count_nonzero(mask) < 25:
        raise ValueError('Head-range selects <25 vertices; check axis and coordinates')
    return mask


def rigid_align_without_scaling(source: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    """Align position/rotation only. Never use similarity fit: it masks width canaries."""
    if source.shape != candidate.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError('Identical N-by-3 vertex arrays are required')
    a = source - source.mean(axis=0)
    b = candidate - candidate.mean(axis=0)
    u, _s, vt = np.linalg.svd(b.T @ a)
    reflection = np.linalg.det(u @ vt)
    rotation = u @ np.diag([1.0, 1.0, np.sign(reflection)]) @ vt
    return b @ rotation + source.mean(axis=0)


def band_widths(vertices: np.ndarray, axis: int, low: float, high: float,
                fractions=(.25, .40, .55, .70, .80)) -> dict:
    """Quantile lateral width at fixed physical heights (invariant to textures)."""
    lateral = 0 if axis != 0 else 1
    H = high - low
    result = {}
    for f in fractions:
        mask = np.abs(vertices[:, axis] - (low + f * H)) <= H * .035
        if np.count_nonzero(mask) < 8:
            result[f'{f:.2f}'] = None
        else:
            x = vertices[mask, lateral]
            result[f'{f:.2f}'] = round(float((np.quantile(x, .98) - np.quantile(x, .02)) / H), 6)
    return result


def geometry_delta(source: np.ndarray, candidate: np.ndarray, faces_a: np.ndarray,
                   faces_b: np.ndarray, mask: np.ndarray, head_height: float,
                   axis: int, low: float, high: float) -> dict:
    """Same-topology position comparison. Not a ground-truth identity evaluator."""
    if source.shape != candidate.shape or not np.array_equal(faces_a, faces_b):
        raise ValueError('Vertex/face correspondence differs. This paired audit requires the same topology; use a separately validated surface-distance comparison for retopologized meshes.')
    if head_height <= 0:
        raise ValueError('Head height must be positive')
    aligned = rigid_align_without_scaling(source[mask], candidate[mask])
    distances = np.linalg.norm(aligned - source[mask], axis=1) / head_height
    s_widths = band_widths(source, axis, low, high)
    # Reconstruct aligned full candidate from the same rigid transform on head points.
    centered_source = source[mask] - source[mask].mean(axis=0)
    centered_candidate = candidate[mask] - candidate[mask].mean(axis=0)
    u, _s, vt = np.linalg.svd(centered_candidate.T @ centered_source)
    rot = u @ np.diag([1.0, 1.0, np.sign(np.linalg.det(u @ vt))]) @ vt
    aligned_full = (candidate - candidate[mask].mean(axis=0)) @ rot + source[mask].mean(axis=0)
    c_widths = band_widths(aligned_full, axis, low, high)
    width_deltas = {k: (None if s_widths[k] is None or c_widths[k] is None else
                        round(c_widths[k] - s_widths[k], 6)) for k in s_widths}
    return {
        'head_vertex_count': int(np.count_nonzero(mask)),
        'rms_displacement_over_head_height': round(float(np.sqrt(np.mean(distances ** 2))), 7),
        'p95_displacement_over_head_height': round(float(np.quantile(distances, .95)), 7),
        'max_displacement_over_head_height': round(float(np.max(distances)), 7),
        'source_width_over_height': s_widths,
        'candidate_width_over_height': c_widths,
        'signed_width_ratio_delta': width_deltas,
        'absolute_width_delta_max': round(float(max([abs(v) for v in width_deltas.values() if v is not None] or [0])), 7),
        'unit': 'All displacements and cross-section changes divided by fixed source head height; no scale alignment',
    }


def warp_wrong_identity(vertices: np.ndarray, axis: int, low: float, high: float,
                        factor: float = 1.18) -> np.ndarray:
    """Falsification canary: widen the middle face band without shifting the top/bottom."""
    if not 1.05 <= factor <= 1.5:
        raise ValueError('Canary factor must be between 1.05 and 1.5')
    result = np.array(vertices, dtype=np.float64, copy=True)
    H = high - low
    if H <= 0:
        raise ValueError('Invalid head range')
    lateral = 0 if axis != 0 else 1
    t = np.clip((vertices[:, axis] - low) / H, 0.0, 1.0)
    # Continuous weighting, strongest at cheeks; zero toward chin and crown.
    upweight = np.clip((t - .15) / .25, 0, 1)
    downweight = np.clip((.90 - t) / .20, 0, 1)
    s = (upweight ** 2 * (3 - 2 * upweight)) * (downweight ** 2 * (3 - 2 * downweight))
    mask = (vertices[:, axis] >= low) & (vertices[:, axis] <= high)
    center = float(np.median(vertices[mask, lateral]))
    result[:, lateral] += (vertices[:, lateral] - center) * ((factor - 1.0) * s)
    return result


def rejects_shape(delta: dict, minimum_p95: float = .006,
                  minimum_width_delta: float = .010) -> bool:
    """Flag known-incorrect deformation if nonrigid drift OR width ratio changes."""
    return (delta['p95_displacement_over_head_height'] >= minimum_p95 or
            delta['absolute_width_delta_max'] >= minimum_width_delta)


def audit(source: Geometry, axis: int, low: float, high: float,
          candidate: Geometry | None = None, canary_factor: float = 1.18) -> dict:
    mask = head_mask(source.vertices, axis, low, high)
    H = high - low
    wrong = warp_wrong_identity(source.vertices, axis, low, high, canary_factor)
    identity = geometry_delta(source.vertices, source.vertices, source.faces,
                              source.faces, mask, H, axis, low, high)
    canary = geometry_delta(source.vertices, wrong, source.faces, source.faces,
                            mask, H, axis, low, high)
    positive_control_passes = rejects_shape(canary)
    negative_control_passes = not rejects_shape(identity)
    report = {
        'schema': 'livynth.geometry-falsification.v1',
        'source_sha256': source.file_sha256,
        'mesh': source.mesh_name, 'node': source.node_name,
        'up_axis': 'xyz'[axis], 'head_range_source_units': [low, high],
        'head_vertices': int(np.count_nonzero(mask)),
        'no_materials_used': True,
        'no_images_used': True,
        'scale_alignment_used': False,
        'positive_control_wrong_identity': {'factor': canary_factor, 'rejected': positive_control_passes, 'measurements': canary},
        'negative_control_unchanged_identity': {'rejected': not negative_control_passes, 'measurements': identity},
        'falsification_gate_pass': bool(positive_control_passes and negative_control_passes),
        'interpretation': 'Can detect geometric deformations with vertex correspondence; cannot establish likeness to photographic identity, identify duplicate shells, or validate retopologized meshes.',
        'identity_likeness_gate': 'NOT_EVALUATED',
    }
    if candidate is not None:
        delta = geometry_delta(source.vertices, candidate.vertices, source.faces,
                               candidate.faces, mask, H, axis, low, high)
        report['candidate'] = {'sha256': candidate.file_sha256,
                               'geometry_change_detected': rejects_shape(delta),
                               'measurements': delta,
                               'identity_likeness_gate': 'NOT_EVALUATED'}
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--candidate', type=Path)
    p.add_argument('--mesh', help='Exact trimesh geometry name; mandatory for multi-mesh GLB')
    p.add_argument('--node', help='Exact instance name for multiply-instanced mesh')
    p.add_argument('--axis', choices=tuple(AXIS), default='y')
    p.add_argument('--head-range', type=float, nargs=2, metavar=('LOW', 'HIGH'))
    p.add_argument('--list-meshes', action='store_true')
    p.add_argument('--canary-factor', type=float, default=1.18)
    p.add_argument('--out', type=Path, default=Path('output/geometry_falsification.json'))
    a = p.parse_args(argv)
    if a.list_meshes:
        print(json.dumps(inventory(a.source), indent=2))
        return 0
    if a.head_range is None:
        p.error('Supply the anatomical head-only --head-range explicitly; whole-body bounds invalidate the test')
    try:
        s = load_geometry(a.source, a.mesh, a.node)
        c = load_geometry(a.candidate, a.mesh, a.node) if a.candidate else None
        result = audit(s, AXIS[a.axis], *a.head_range, candidate=c,
                       canary_factor=a.canary_factor)
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ('falsification_gate_pass', 'identity_likeness_gate')}, indent=2))
    print('Saved:', a.out.resolve())
    return 0 if result['falsification_gate_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())