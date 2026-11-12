"""Strict MPFB native eye/teeth/tongue fitting plan; pure standard library.

This is an isolated attachment experiment, not Character 001 reconstruction.
The selected file digest is pinned to the owner's verified 2026-11-12 inventory.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'livynth.native-anatomy.plan.v1'
REQUIRED = ('eyes', 'teeth', 'tongue')
MATERIAL = {'eyes': 'PROCEDURAL_EYES', 'teeth': 'MAKESKIN', 'tongue': 'MAKESKIN'}

class AnatomyPlanError(ValueError):
    pass

def validate_plan(data):
    if not isinstance(data,dict) or set(data) != {'schema','source','assets'}:
        raise AnatomyPlanError('E_PLAN_FIELDS')
    if data['schema'] != SCHEMA or data['source'] != 'owner_mpfb_inventory':
        raise AnatomyPlanError('E_PLAN_SCHEMA')
    chosen=data['assets']
    if not isinstance(chosen,dict) or set(chosen) != set(REQUIRED):
        raise AnatomyPlanError('E_REQUIRED_ASSETS')
    out={}
    for category in REQUIRED:
        item=chosen[category]
        if not isinstance(item,dict) or set(item) != {'relative_path','sha256'}:
            raise AnatomyPlanError('E_ASSET_FIELDS_'+category)
        path=item['relative_path']
        digest=item['sha256']
        if (not isinstance(path,str) or not re.fullmatch(
                r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+[.]mhclo',path) or
                not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest)):
            raise AnatomyPlanError('E_ASSET_PATH_OR_HASH_'+category)
        out[category]={'relative_path':path,'sha256':digest}
    return {'schema':SCHEMA,'source':'owner_mpfb_inventory','assets':out}

def load_plan(filename):
    try:
        pairs=lambda values: _distinct_pairs(values)
        data=json.loads(Path(filename).read_text(encoding='utf-8'),object_pairs_hook=pairs)
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise AnatomyPlanError('E_PLAN_FILE: '+str(exc)) from exc
    return validate_plan(data)

def _distinct_pairs(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise AnatomyPlanError('E_DUPLICATE_KEY_'+key)
        out[key]=value
    return out

def verify_asset_file(path, expected_digest):
    """Check an actual resolved installed asset before MPFB imports it."""
    path=Path(path)
    if not path.is_file() or path.is_symlink() or path.suffix.lower()!='.mhclo':
        raise AnatomyPlanError('E_ASSET_NOT_REGULAR_FILE')
    with path.open('rb') as source:
        digest=hashlib.file_digest(source,'sha256').hexdigest()
    if digest != expected_digest:
        raise AnatomyPlanError('E_ASSET_HASH_MISMATCH')
    return {'sha256':digest,'size_bytes':path.stat().st_size}
