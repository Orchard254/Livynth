"""IDENTITY-023: reversible oral asset visibility controls for attribution stills.

This module never changes source geometry, shape keys, armature or materials.
"""
from __future__ import annotations

VARIANTS=(
    ('jaw_full',False,False),
    ('jaw_no_tongue',False,True),
    ('jaw_no_teeth',True,False),
    ('jaw_no_teeth_no_tongue',True,True),
)


class OralIsolationError(ValueError):
    pass


def capture_oral_visibility(assets,render,*,update=lambda:None):
    if (not isinstance(assets,dict) or
            not {'teeth','tongue'}.issubset(assets) or
            not callable(render) or not callable(update)):
        raise OralIsolationError('E_ID023_ISOLATION_INPUT')
    teeth,tongue=assets['teeth'],assets['tongue']
    if (teeth is tongue or teeth.hide_render or tongue.hide_render):
        raise OralIsolationError('E_ID023_ASSETS_NOT_BOTH_VISIBLE')
    images=[]
    audits=[]
    try:
        for name,hide_teeth,hide_tongue in VARIANTS:
            teeth.hide_render=hide_teeth
            tongue.hide_render=hide_tongue
            update()
            if (teeth.hide_render!=hide_teeth or
                    tongue.hide_render!=hide_tongue):
                raise OralIsolationError('E_ID023_VISIBILITY_NOT_SET')
            entry=render(name)
            if (not isinstance(entry,dict) or
                    entry.get('filename')!=name+'.png'):
                raise OralIsolationError('E_ID023_UNEXPECTED_RENDER_FILENAME')
            images.append(entry)
            audits.append({
                'filename':name+'.png',
                'teeth_visible':not hide_teeth,
                'tongue_visible':not hide_tongue,
                'body_visible':True,
                'source_geometry_modified':False,
                'rendered_visual_inference':'PENDING_INDEPENDENT_REVIEW',
            })
    finally:
        teeth.hide_render=False
        tongue.hide_render=False
        update()
    return images,audits
