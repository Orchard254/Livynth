#!/usr/bin/env python3
"""C001-GEO-02: conservative, reversible fitting of an existing morph-enabled GLB.

Modifies neutral positions and each morph POSITION/NORMAL using a smooth
landmark deformation, preserving scene, skin, animation and texture tables.

This is a *first fitting candidate*, not a 3D photo scan or a proven likeness.
Current reference anchors were manually estimated, not automatic landmarks.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

COMPONENT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
COMPONENT_COUNT = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class GLBError(ValueError):
    pass


class GLB:
    """Lossless BIN accessor editor: only requested vertex attribute values change."""
    def __init__(self, source: bytes):
        if len(source) < 20 or source[:4] != b'glTF':
            raise GLBError('Not a GLB file')
        magic, version, total = struct.unpack_from('<III', source)
        if version != 2 or total != len(source):
            raise GLBError('Invalid GLB 2 length/version')
        offset = 12
        chunks = []
        while offset < len(source):
            if offset + 8 > len(source):
                raise GLBError('Incomplete GLB chunk header')
            length, tag = struct.unpack_from('<I4s', source, offset)
            if length % 4 or offset + 8 + length > len(source):
                raise GLBError('Invalid GLB chunk length')
            chunks.append((tag, source[offset + 8:offset + 8 + length]))
            offset += 8 + length
        if len(chunks) != 2 or chunks[0][0] != b'JSON' or chunks[1][0] != b'BIN\x00':
            raise GLBError('Only single-buffer JSON + BIN GLB supported')
        self.doc = json.loads(chunks[0][1].decode('utf8'))
        if len(self.doc.get('buffers', [])) != 1:
            raise GLBError('Expected exactly one embedded buffer')
        self.binary = bytearray(chunks[1][1])
        if len(self.binary) < self.doc['buffers'][0]['byteLength']:
            raise GLBError('Truncated embedded buffer')

    @classmethod
    def from_file(cls, path: Path):
        return cls(Path(path).read_bytes())

    def accessor(self, index: int) -> np.ndarray:
        info = self.doc['accessors'][index]
        if info.get('sparse') or 'bufferView' not in info:
            raise GLBError(f'Sparse/no-buffer accessor {index} not supported')
        if info['componentType'] not in COMPONENT or info['type'] not in COMPONENT_COUNT:
            raise GLBError(f'Unsupported accessor type: {index}')
        view = self.doc['bufferViews'][info['bufferView']]
        if view.get('buffer', 0) != 0:
            raise GLBError(f'Accessor {index}: nonzero buffer')
        dtype = np.dtype('<' + COMPONENT[info['componentType']])
        num = COMPONENT_COUNT[info['type']]
        row_bytes = dtype.itemsize * num
        stride = view.get('byteStride', row_bytes)
        base = view.get('byteOffset', 0) + info.get('byteOffset', 0)
        last = base + (info['count'] - 1) * stride + row_bytes
        view_end = view.get('byteOffset', 0) + view['byteLength']
        if (info['count'] < 1 or stride < row_bytes or stride % dtype.itemsize
                or base < view.get('byteOffset', 0) or last > view_end
                or last > len(self.binary)):
            raise GLBError(f'Accessor {index}: out of bounds or invalid stride')
        return np.ndarray((info['count'], num), dtype=dtype, buffer=self.binary,
                          offset=base, strides=(stride, dtype.itemsize))

    def patch_f32_vec3(self, index: int, new_values: np.ndarray):
        a = self.doc['accessors'][index]
        if a['componentType'] != 5126 or a['type'] != 'VEC3':
            raise GLBError(f'Accessor {index} not float32 VEC3')
        old = self.accessor(index)
        new = np.asarray(new_values, dtype='<f4')
        if new.shape != old.shape or not np.isfinite(new).all():
            raise GLBError('Invalid replacement shape or nonfinite position/normal')
        old[:] = new
        if 'min' in a:
            a['min'] = new.min(axis=0).astype(float).tolist()
        if 'max' in a:
            a['max'] = new.max(axis=0).astype(float).tolist()

    def to_bytes(self) -> bytes:
        encoded = json.dumps(self.doc, ensure_ascii=False, separators=(',', ':')).encode('utf8')
        encoded += b' ' * (-len(encoded) % 4)
        raw = bytes(self.binary)
        raw += b'\0' * (-len(raw) % 4)
        total = 12 + 8 + len(encoded) + 8 + len(raw)
        return (struct.pack('<III', 0x46546C67, 2, total)
                + struct.pack('<I4s', len(encoded), b'JSON') + encoded
                + struct.pack('<I4s', len(raw), b'BIN\x00') + raw)


@dataclass(frozen=True)
class Control:
    name: str
    center: tuple[float, float, float]
    delta: tuple[float, float, float]
    sigma: tuple[float, float, float]


def landmark_controls(doc: dict, original: GLB, image_measurements: dict) -> tuple[list[Control], dict]:
    """Derive conservative target deltas from measured photo ratios and morph markers.

    Assumes baseline V32 coordinates (meters; glTF Y up, +Z face forward).
    Refuse other coordinate systems/meshes. This intentionally does not claim
    a calibrated inverse graphics solution.
    """
    meshes = doc['meshes']
    face_candidates = []
    for mesh_index, mesh in enumerate(meshes):
        names = mesh.get('extras', {}).get('targetNames', [])
        required = {'eyeBlinkLeft', 'eyeBlinkRight', 'mouthSmileLeft',
                    'mouthSmileRight', 'jawOpen'}
        if required.issubset(set(names)):
            face_candidates.append((len(names), mesh_index))
    if not face_candidates:
        raise GLBError('Morph-rich face mesh not found; only V32-like source supported')
    face_index = max(face_candidates)[1]
    face_mesh = meshes[face_index]
    fprim = face_mesh['primitives'][0]
    source_face = np.asarray(original.accessor(fprim['attributes']['POSITION'])).copy()
    eye_candidates = []
    for i, mesh in enumerate(meshes):
        if i == face_index:
            continue
        prim = mesh['primitives'][0]
        eye_v = np.asarray(original.accessor(prim['attributes']['POSITION']))
        if (600 < len(eye_v) < 4000 and 1.62 < float(eye_v[:,1].min()) < 1.67
                and 1.66 < float(eye_v[:,1].max()) < 1.70):
            eye_candidates.append((i, eye_v))
    if len(eye_candidates) != 1:
        raise GLBError(f'Could not uniquely detect eyeball mesh, found {len(eye_candidates)}')
    eye_index, eyeballs = eye_candidates[0]
    left_eye = eyeballs[eyeballs[:,0] < 0].mean(0)
    right_eye = eyeballs[eyeballs[:,0] > 0].mean(0)
    eye_gap = float(right_eye[0] - left_eye[0])
    eye_y = float((left_eye[1] + right_eye[1]) / 2)
    if not (.05 < eye_gap < .09 and 1.6 < eye_y < 1.7):
        raise GLBError('Unsupported source scale/eye placement')

    def morph_centre(name):
        names = face_mesh['extras']['targetNames']
        index = names.index(name)
        delta = np.asarray(original.accessor(fprim['targets'][index]['POSITION']))
        mag = np.linalg.norm(delta, axis=1)
        threshold = np.quantile(mag, .985)
        keep = mag >= threshold
        return (source_face[keep] * mag[keep, None]).sum(0) / mag[keep].sum()

    lip_l = morph_centre('mouthSmileRight')
    lip_r = morph_centre('mouthSmileLeft')
    # Image y increases downward; image x increases rightward.
    pupil_left = image_measurements['eyes']['left']
    pupil_right = image_measurements['eyes']['right']
    ref_eye_gap = float(pupil_right[0] - pupil_left[0])
    ref_eye_y = (pupil_left[1] + pupil_right[1]) * .5
    chin_y = float(image_measurements['chin'][1])
    if not (150 < ref_eye_gap < 350 and 250 < chin_y-ref_eye_y < 600):
        raise ValueError('Reference landmarks outside supported scale')
    target_chin_y = eye_y - (chin_y - ref_eye_y) / ref_eye_gap * eye_gap
    source_chin = np.array((0., 1.535, .139))
    chin_delta = float(np.clip(target_chin_y - source_chin[1], -.012, .012))
    mouth_x0, mouth_x1 = image_measurements['mouth_corners']
    target_half_mouth = abs(mouth_x1[0] - mouth_x0[0]) / ref_eye_gap * eye_gap * .5
    current_half_mouth = float((lip_r[0]-lip_l[0]) * .5)
    mouth_delta = float(np.clip(target_half_mouth-current_half_mouth, -.004, .004))
    # One-sided landmark source nose controls are uncertain: do not force-fit
    # nostril width from a textual 'nose size' claim. Use only a 2 mm soft hint.
    controls = [
        Control('chin_vertical', tuple(source_chin), (0, chin_delta, 0), (.052,.045,.050)),
        Control('left_mouth_corner', tuple(lip_l), (-mouth_delta,0,0), (.022,.022,.025)),
        Control('right_mouth_corner', tuple(lip_r), (mouth_delta,0,0), (.022,.022,.025)),
        Control('left_brow_depth', (-.039,1.683,.14), (0,0,.002), (.026,.020,.028)),
        Control('right_brow_depth', (.039,1.683,.14), (0,0,.002), (.026,.020,.028)),
        Control('nose_projection', (0,1.607,.169), (0,0,.0035), (.019,.032,.022)),
        Control('left_jaw', (-.046,1.551,.105), (-.0025,0,0), (.039,.041,.046)),
        Control('right_jaw', (.046,1.551,.105), (.0025,0,0), (.039,.041,.046)),
    ]
    inferred = {'face_mesh_index':face_index,'eye_mesh_index':eye_index,
                'source_interocular_m':eye_gap,'source_eye_y_m':eye_y,
                'target_chin_y_m':target_chin_y,
                'chin_dy_m':chin_delta,
                'mouth_halfwidth_delta_m':mouth_delta,
                'source_mouth_halfwidth_m':current_half_mouth,
                'target_mouth_halfwidth_m':target_half_mouth}
    return controls, inferred


class GaussianField:
    def __init__(self, controls: list[Control], damping: float = 1e-5):
        if not controls:
            raise ValueError('At least one anchor needed')
        self.centres = np.asarray([x.center for x in controls], dtype=np.float64)
        self.sigma = np.asarray([x.sigma for x in controls], dtype=np.float64)
        deltas = np.asarray([x.delta for x in controls], dtype=np.float64)
        if not np.all(self.sigma > 0) or not np.isfinite(deltas).all():
            raise ValueError('Invalid Gaussian control')
        # Asymmetric sigmas can yield a nonsymmetric K: defined consistently.
        diff = (self.centres[:,None,:] - self.centres[None,:,:]) / self.sigma[None,:,:]
        matrix = np.exp(-.5 * np.sum(diff*diff, axis=2))
        self.coef = np.linalg.solve(matrix + damping*np.eye(len(controls)), deltas)
        self.target_deltas = deltas

    def warp(self, points: np.ndarray, jacobian: bool = False):
        p = np.asarray(points, dtype=np.float64)
        if p.ndim != 2 or p.shape[1] != 3:
            raise ValueError('Expected Nx3 points')
        d = p[:,None,:]-self.centres[None,:,:]
        w = np.exp(-.5*np.sum((d/self.sigma[None,:,:])**2, axis=2))
        displacement = w @ self.coef
        result = p + displacement
        if not jacobian:
            return result.astype('<f4')
        gradient = -w[:,:,None] * d / (self.sigma[None,:,:]**2)
        J = np.tile(np.eye(3), (len(p), 1, 1))
        J += np.einsum('ak,naj->nkj', self.coef, gradient)
        return result.astype('<f4'), J

    def transform_normals(self, points: np.ndarray, normals: np.ndarray):
        _, J = self.warp(points, jacobian=True)
        det = np.linalg.det(J)
        if np.any(det < .25) or not np.isfinite(det).all():
            raise GLBError('Deformation folds geometry (Jacobian determinant too small)')
        transformed = np.linalg.solve(np.swapaxes(J, 1, 2), normals.astype('f8')[...,None])[...,0]
        n = np.linalg.norm(transformed,axis=1,keepdims=True)
        transformed = transformed / np.maximum(n, 1e-9)
        return transformed.astype('<f4'), float(det.min())


def fit(source: Path, reference: Path, destination: Path, report_path: Path):
    data = source.read_bytes()
    glb = GLB(data)
    doc = glb.doc
    original = GLB(data)
    measurements = json.loads(reference.read_text(encoding='utf8'))
    controls, inferred = landmark_controls(doc, original, measurements)
    field = GaussianField(controls)
    pre_mesh_stats = [len(m['primitives'][0].get('targets',[])) for m in doc['meshes']]
    orig_skins = copy.deepcopy(doc.get('skins', []))
    orig_anim = copy.deepcopy(doc.get('animations', []))
    orig_images = copy.deepcopy(doc.get('images', []))
    orig_materials = copy.deepcopy(doc.get('materials', []))
    changed = []
    max_displacement = 0.
    min_det = 1.
    for mesh_i, mesh in enumerate(doc['meshes']):
        for prim_i, prim in enumerate(mesh['primitives']):
            if 'POSITION' not in prim['attributes']:
                continue
            aid = prim['attributes']['POSITION']
            original_p = original.accessor(aid).astype('f4').copy()
            # Head-local ROI; lower body/garments are unchanged.
            if not np.any((original_p[:,1] > 1.45) & (original_p[:,1] < 1.80)):
                continue
            transformed = field.warp(original_p)
            dist = np.linalg.norm(transformed - original_p,axis=1)
            if not np.any(dist > 1e-7):
                continue
            max_displacement = max(max_displacement, float(dist.max()))
            old_normals = None
            new_normals = None
            if 'NORMAL' in prim['attributes']:
                old_normals = original.accessor(prim['attributes']['NORMAL']).astype('f4').copy()
                new_normals, d = field.transform_normals(original_p, old_normals)
                min_det = min(min_det, d)
            morph_changes = 0
            for target in prim.get('targets', []):
                if 'POSITION' not in target:
                    continue
                d0 = original.accessor(target['POSITION']).astype('f4').copy()
                if len(d0) != len(original_p):
                    raise GLBError('Morph topology does not match neutral mesh')
                posed = original_p + d0
                d1 = field.warp(posed) - transformed
                glb.patch_f32_vec3(target['POSITION'], d1)
                if ('NORMAL' in target and old_normals is not None and new_normals is not None):
                    dn0 = original.accessor(target['NORMAL']).astype('f4').copy()
                    posed_normal, d = field.transform_normals(posed, old_normals + dn0)
                    min_det = min(min_det, d)
                    glb.patch_f32_vec3(target['NORMAL'], posed_normal-new_normals)
                morph_changes += 1
            glb.patch_f32_vec3(aid, transformed)
            if new_normals is not None:
                glb.patch_f32_vec3(prim['attributes']['NORMAL'], new_normals)
            changed.append({'mesh': mesh_i, 'primitive': prim_i,
                            'vertices': len(original_p),'morphs_updated':morph_changes,
                            'max_displacement_mm':round(float(dist.max())*1000,3),
                            'vertices_changed':int(np.count_nonzero(dist > 1e-6))})
    assert orig_skins == doc.get('skins', [])
    assert orig_anim == doc.get('animations', [])
    assert orig_images == doc.get('images', [])
    assert orig_materials == doc.get('materials', [])
    assert pre_mesh_stats == [len(m['primitives'][0].get('targets',[])) for m in doc['meshes']]
    if not changed:
        raise GLBError('Warp did not affect any mesh')
    metadata = {
        'method': 'livynth.c001.smooth-morph-fit.v1',
        'fit_status': 'diagnostic morphology candidate; identity unverified',
        'source_sha256': hashlib.sha256(data).hexdigest(),
        'reference_annotation_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
    }
    doc.setdefault('asset', {}).setdefault('extras', {})['livynth_c001'] = metadata
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(glb.to_bytes())
    reloaded = GLB.from_file(destination)
    if len(reloaded.doc['meshes']) != len(doc['meshes']):
        raise GLBError('Round-trip mesh count changed')
    report = {'schema':'livynth.c001.fit-report.v1',**metadata,'inferred':inferred,
              'controls':[{'name':c.name,'center':c.center,'delta':c.delta,
                           'sigma':c.sigma} for c in controls],
              'meshes_changed':changed,
              'max_displacement_mm':round(max_displacement * 1000,3),
              'min_jacobian_det':round(min_det,6),
              'source_skin_count':len(orig_skins),
              'source_animation_count':len(orig_anim),
              'source_mesh_target_counts':pre_mesh_stats,
              'candidate_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
              'limitations':['Original source is a different identity and hairstyle',
                             'No camera-calibrated 3D reconstruction from generated photos',
                             'Photo pixels were manually annotated',
                             'Hair geometry/materials not yet replaced',
                             'Morph geometry is preserved but visual eyelid quality must be tested in Blender']}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,default=lambda v: v.item() if isinstance(v,np.generic) else str(v))+'\n',encoding='utf8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--reference',type=Path,default=Path('geo/character001_landmarks.json'))
    p.add_argument('--out',type=Path,default=Path('output/character001_geo02_candidate.glb'))
    p.add_argument('--report',type=Path,default=Path('output/character001_geo02_fit_report.json'))
    a=p.parse_args()
    result=fit(a.source,a.reference,a.out,a.report)
    print(json.dumps({k:result[k] for k in ['max_displacement_mm','min_jacobian_det','source_skin_count','source_animation_count','source_mesh_target_counts']},indent=2))
    print('[C001-GEO-02] Fitting candidate:',a.out.resolve())

if __name__=='__main__':
    main()