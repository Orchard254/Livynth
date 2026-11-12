"""Read-only MPFB appearance asset inventory, independent of Blender at import.

Inventory is a prerequisite to selecting fitted eyes, tongue, teeth, hair,
and clothing assets. It never installs, downloads, or attaches assets.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SCHEMA = 'livynth.mpfb.appearance-inventory.v1'
REQUIRED_FOR_ANATOMY = ('eyes', 'teeth', 'tongue')
CATEGORIES = ('eyes', 'teeth', 'tongue', 'eyebrows', 'eyelashes', 'hair', 'clothes', 'skins')
EXTENSIONS = {cat: ('.mhmat' if cat == 'skins' else '.mhclo') for cat in CATEGORIES}

class InventoryError(ValueError):
    pass

def inventory_category(category, asset_roots, *, per_category_limit=500):
    """Scan only extension-approved files in the roots returned by MPFB.

    Reports safe relative paths and content hashes, never user's absolute
    asset directory locations. Symlinks and files escaping a root are ignored.
    """
    if category not in CATEGORIES or not isinstance(asset_roots, (list, tuple)):
        raise InventoryError('E_ASSET_CATEGORY')
    assets = {}
    for root in asset_roots:
        location = Path(root)
        if location.is_symlink() or not location.is_dir():
            continue
        base = location.resolve()
        for path in sorted(location.rglob('*')):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() != EXTENSIONS[category]:
                continue
            if not path.resolve().is_relative_to(base):
                continue
            rel = path.relative_to(location).as_posix()
            with path.open('rb') as stream:
                sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            label = f'{rel}#{sha[:12]}'
            assets[label] = {'relative_path':rel, 'size_bytes':path.stat().st_size,
                             'sha256':sha}
            if len(assets) > per_category_limit:
                raise InventoryError('E_ASSET_LIMIT_'+category)
    return [assets[key] for key in sorted(assets)]

def make_inventory(asset_roots_by_category, *, mpfb_version, blender_version,
                   system_assets_pack_installed=None):
    if not isinstance(asset_roots_by_category, dict) or set(asset_roots_by_category) != set(CATEGORIES):
        raise InventoryError('E_INVENTORY_CATEGORY_SET')
    groups={category: inventory_category(category, asset_roots_by_category[category])
            for category in CATEGORIES}
    missing=[cat for cat in REQUIRED_FOR_ANATOMY if not groups[cat]]
    return {
        'schema':SCHEMA,
        'status':'ASSETS_AVAILABLE_FOR_FITTING_TESTS' if not missing else 'MISSING_REQUIRED_ANATOMY_ASSETS',
        'read_only':True,
        'blender_version':str(blender_version),
        'mpfb_version':str(mpfb_version),
        'system_assets_pack_installed':system_assets_pack_installed,
        'required_for_anatomy':list(REQUIRED_FOR_ANATOMY),
        'missing_required_for_anatomy':missing,
        'categories':{cat:{'count':len(groups[cat]),'assets':groups[cat]} for cat in CATEGORIES},
        'assets_fitted_to_body':'NOT_TESTED',
        'exported_rig_compatibility':'NOT_TESTED',
        'character_identity_likeness':'UNVERIFIED',
        'asset_licences':'REVIEW_BEFORE_COMMERCIAL_USE',
    }
