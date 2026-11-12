#!/usr/bin/env python3
"""Offline image-landmark fit diagnostic; never exports an approved character.

Requires manually verified 2D points, mesh correspondences and camera guesses.
Rejects unsafe or profile-regressing proposals; output is evidence, not a GLB.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from character.image_landmark_fit import fit_from_image_landmarks
from tools.run_head_shape_offline import read_neutral


def run(neutral,observations,out):
    points,quads=read_neutral(neutral)
    data=json.loads(Path(observations).read_text(encoding='utf-8'))
    result=fit_from_image_landmarks(points,data,quads)
    target=Path(out)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        raise FileExistsError('Refusing to overwrite existing diagnostic: '+str(target))
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--neutral',type=Path,required=True)
    p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    result=run(args.neutral,args.observations,args.out)
    print(json.dumps(result,indent=2))
    # A diagnostic rejection is non-zero so automation cannot misread
    # it as successful image-driven identity reconstruction.
    return 2 if result['status'].startswith(('REJECTED','UNIDENTIFIABLE')) else 0
if __name__=='__main__':raise SystemExit(main())
