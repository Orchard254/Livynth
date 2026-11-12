#!/usr/bin/env python3
"""One-command read-only MPFB appearance-asset readiness probe on Windows."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from livynth_studio import find_blender

def build_command(blender,report):
    return [str(blender),'--background','--python',
            str(ROOT/'tools/mpfb_asset_probe_blender.py'),'--',
            '--out',str(Path(report).resolve())]

def run(blender,report,*,execute=subprocess.run):
    report=Path(report).resolve()
    if report.exists() or report.is_symlink():
        raise FileExistsError('Existing inventory report: '+str(report))
    execute(build_command(blender,report),cwd=str(ROOT),check=True)
    if not report.is_file():
        raise RuntimeError('Blender did not write MPFB inventory')
    data=json.loads(report.read_text(encoding='utf-8'))
    if data.get('schema')!='livynth.mpfb.appearance-inventory.v1' or data.get('status') not in ('MISSING_REQUIRED_ANATOMY_ASSETS','ASSETS_AVAILABLE_FOR_FITTING_TESTS'):
        raise ValueError('Unrecognized asset inventory status')
    return data

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender',default='')
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    output=args.out or ROOT/'output'/'asset_inventory'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')/'mpfb_asset_inventory.json'
    try:
        result=run(find_blender(args.blender),output)
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        p.exit(2,'LIVYNTH asset inventory FAILED: '+str(exc)+'\n')
    print(json.dumps({'inventory':str(Path(output).resolve()),'readiness':result['status'],
                      'missing_assets':result['missing_required_for_anatomy'],
                      'attachment_not_yet_tested':True},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
