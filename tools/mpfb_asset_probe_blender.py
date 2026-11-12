#!/usr/bin/env python3
"""Read-only MPFB asset scan under registered Blender user extension."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.mpfb_asset_inventory import CATEGORIES,make_inventory

def inspect_assets(out):
    import bpy
    from bl_ext.user_default.mpfb.services.assetservice import AssetService
    from bl_ext.user_default import mpfb
    roots={category: AssetService.get_asset_roots(category) for category in CATEGORIES}
    installed=AssetService.system_assets_pack_is_installed()
    result=make_inventory(roots,mpfb_version=getattr(mpfb,'__version__','build_unreported'),
                          blender_version=bpy.app.version_string,
                          system_assets_pack_installed=bool(installed))
    out=Path(out)
    if out.exists() or out.is_symlink():
        raise FileExistsError('Refusing to overwrite asset inventory: '+str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:
        f.write(json.dumps(result,indent=2)+'\n')
    print('[LIVYNTH] MPFB appearance inventory status:',result['status'])
    print('[LIVYNTH] Missing anatomy assets:',result['missing_required_for_anatomy'])
    print('[LIVYNTH] Inventory:',out)
    return result

if __name__=='__main__':
    if '--' not in sys.argv:
        raise SystemExit('Pass arguments after blender --')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    inspect_assets(args.out)
