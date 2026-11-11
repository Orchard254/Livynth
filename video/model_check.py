#!/usr/bin/env python3
"""Check the morph-target contract of an actual GLB without editing it.

Pure standard library; this inspects JSON metadata and length consistency,
not the accuracy of rendered eyelids or speech.
"""
import argparse
import json
import struct
from pathlib import Path

REQUIRED = {
    'eyeBlinkLeft', 'eyeBlinkRight', 'jawOpen',
    'viseme_aa', 'mouthSmileLeft', 'mouthSmileRight'
}


def inspect_glb(path):
    path = Path(path)
    with path.open('rb') as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError('GLB too short')
        magic, version, length = struct.unpack('<4sII', header)
        if magic != b'glTF' or version != 2:
            raise ValueError('Expected glTF 2.0 GLB')
        if path.stat().st_size != length:
            raise ValueError('GLB file length does not match its header')
        chunk_header = f.read(8)
        if len(chunk_header) != 8:
            raise ValueError('Missing GLB JSON chunk')
        chunk_length, chunk_type = struct.unpack('<I4s', chunk_header)
        if chunk_type != b'JSON' or chunk_length > 128 * 1024 * 1024:
            raise ValueError('Invalid GLB JSON chunk')
        content = f.read(chunk_length)
        if len(content) != chunk_length:
            raise ValueError('Truncated GLB JSON chunk')
        doc = json.loads(content)

    meshes = []
    compatible = []
    for mesh in doc.get('meshes', []):
        names = mesh.get('extras', {}).get('targetNames', [])
        count = len(mesh.get('primitives', [{}])[0].get('targets', []))
        names = names or [f'target_{i}' for i in range(count)]
        name = mesh.get('name', '(unnamed)')
        meshes.append({'mesh': name, 'target_count': len(names)})
        if REQUIRED.issubset(set(names)):
            compatible.append(name)
    return {
        'file': str(path),
        'meshes': meshes,
        'skins': len(doc.get('skins', [])),
        'animations': len(doc.get('animations', [])),
        'required': sorted(REQUIRED),
        'compatible_face_meshes': compatible,
        'ready': bool(compatible),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--glb', required=True)
    args = p.parse_args()
    result = inspect_glb(args.glb)
    print(json.dumps(result, indent=2))
    if not result['ready']:
        raise SystemExit('ERROR: no single mesh has all required facial morphs')


if __name__ == '__main__':
    main()
