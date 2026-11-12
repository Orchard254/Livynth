"""Manual MPFB identity recipes. Image-driven fitting is NOT implemented."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import struct

SCHEMA = 'livynth.identity.recipe.v1'
MACROS = frozenset(('gender','age','muscle','weight','proportions','height','race'))
RACES = frozenset(('african','asian','caucasian'))  # Names from MPFB API

class InvalidIdentityRecipe(ValueError):
    pass

def _unique(pairs):
    out = {}
    for key, val in pairs:
        if key in out:
            raise InvalidIdentityRecipe('E_DUPLICATE_JSON_KEY: '+key)
        out[key] = val
    return out

def _fraction(x, label):
    if isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x) or not 0 <= x <= 1:
        raise InvalidIdentityRecipe('E_MACRO_VALUE: '+label)
    return float(x)

def validate_recipe(data):
    if not isinstance(data,dict) or set(data) != {'schema','character_id','source','macros'}:
        raise InvalidIdentityRecipe('E_RECIPE_FIELDS')
    if data['schema'] != SCHEMA:
        raise InvalidIdentityRecipe('E_RECIPE_SCHEMA')
    if not isinstance(data['character_id'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{1,39}', data['character_id']):
        raise InvalidIdentityRecipe('E_CHARACTER_ID')
    if data['source'] != 'manual_parameters':
        raise InvalidIdentityRecipe('E_SOURCE_UNSUPPORTED: not image reconstructed')
    macros=data['macros']
    if not isinstance(macros,dict) or not macros or not set(macros).issubset(MACROS):
        raise InvalidIdentityRecipe('E_MACRO_FIELDS')
    result={}
    for key,val in macros.items():
        if key != 'race':
            result[key] = _fraction(val,key)
        else:
            if not isinstance(val,dict) or set(val) != RACES:
                raise InvalidIdentityRecipe('E_RACE_KEYS')
            race={k:_fraction(val[k],'race.'+k) for k in sorted(RACES)}
            if abs(sum(race.values())-1)>1e-6:
                raise InvalidIdentityRecipe('E_RACE_SUM')
            result['race']=race
    return {'schema':SCHEMA,'character_id':data['character_id'],
            'source':'manual_parameters','macros':result}

def load_recipe(path):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_unique,
                        parse_constant=lambda x: (_ for _ in ()).throw(InvalidIdentityRecipe('E_JSON_NONFINITE')))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise InvalidIdentityRecipe('E_READ_RECIPE: '+str(exc)) from exc
    return validate_recipe(data)

def recipe_sha256(recipe):
    return hashlib.sha256(json.dumps(validate_recipe(recipe),sort_keys=True,
            ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')).hexdigest()

def apply_macro_overrides(defaults, overrides):
    # Validate with the same strict schema as files; no mutation of defaults.
    clean=validate_recipe({'schema':SCHEMA,'character_id':'validation',
                           'source':'manual_parameters','macros':overrides})['macros']
    if not isinstance(defaults,dict) or not set(clean).issubset(defaults):
        raise InvalidIdentityRecipe('E_MACRO_NOT_SUPPORTED_BY_MPFB')
    result=dict(defaults)
    if isinstance(result.get('race'),dict):
        result['race']=dict(result['race'])
    for key,val in clean.items():
        result[key]=dict(val) if isinstance(val,dict) else val
    return result

def neutral_positions_sha256(positions):
    """Native Blender baked-neutral vertex-order SHA, float64 LE (Stage-1 convention)."""
    dig=hashlib.sha256(); count=0
    for pos in positions:
        if len(pos)!=3: raise InvalidIdentityRecipe('E_POSITION_SHAPE')
        xyz=[float(v) for v in pos]
        if not all(math.isfinite(v) for v in xyz):
            raise InvalidIdentityRecipe('E_POSITION_NONFINITE')
        dig.update(struct.pack('<ddd',*xyz)); count+=1
    if count < 4: raise InvalidIdentityRecipe('E_POSITION_EMPTY')
    return dig.hexdigest()

def neutral_topology_sha256(polygons):
    """Stable fingerprint of the baked native quad face vertex indices."""
    dig=hashlib.sha256(); count=0
    for face in polygons:
        indices=tuple(int(i) for i in face)
        if len(indices)!=4 or any(i<0 for i in indices):
            raise InvalidIdentityRecipe('E_TOPOLOGY_QUADS')
        dig.update(struct.pack('<IIII',*indices));count+=1
    if count<4: raise InvalidIdentityRecipe('E_TOPOLOGY_EMPTY')
    return dig.hexdigest()
