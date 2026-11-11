"""C001-GEO-04 gate - the blinded human review rubric.

The rubric text is generated into the reviewer bundle so that every reviewer
works from the same wording; this module is the source of truth.
"""

RUBRIC_MD = """# C001-GEO-04 blinded profile and facial anatomy rubric

## What you are looking at

For each candidate you get a folder with

* clay_VIEW.png - the candidate rendered in a uniform neutral grey matte with
  every texture removed.  This is the GEOMETRY evidence.
* wire_VIEW.png - the same view with the silhouette, crease and border edges
  drawn over it.
* wireframe_VIEW.png - the triangle wireframe of the same view.
* review_depth_VIEW.png - the orthographic depth map of the same view (false
  colour, blue = near, red = far).
* review_normal_VIEW.png - the world space surface normal map.
* textured_VIEW.png - the candidate with its own materials (APPEARANCE
  evidence only, diagnostic).
* camera_convention.json - how the views were produced, so that the framing
  can be reproduced.

The reference photographs are in reference/, together with the reference
silhouette masks and the reference landmark overlay.

## How to judge

Judge each of the five views separately: front, left45, right45, left90,
right90.

For every view give exactly one label:

* ACCEPT - the geometry of that view is consistent with the reference view:
  the outline, the surface structure and the profile all agree.
* REFERENCE_ONLY - the view is usable as a visual reference but is not
  acceptable as geometry (for example a smooth shell without facial
  structure, or a view that only works because the texture carries it).
* REGENERATE - the view must be rebuilt from scratch.

Every label MUST be accompanied by ONE line of observable evidence, for
example "the profile shows no nasal projection and the occiput ends in a flat
cut at occiput level".  "Looks fine" is not evidence.

## Rules

1. A rejected profile can never be overridden by a good-looking front
   texture.  If left90 or right90 is REGENERATE or REFERENCE_ONLY, the
   candidate is not ACCEPT in aggregate, whatever the front view looks like.
2. The stricter aggregate label wins.  Aggregate label = the worst of the five
   per-view labels, ordered ACCEPT < REFERENCE_ONLY < REGENERATE.
3. The clay renders, the wireframes and the depth/normal maps are the
   geometry evidence.  The textured render is diagnostic only.  A face that
   reads correctly only because a photograph is projected onto a shell is
   REFERENCE_ONLY at best, because the projected photograph contributes no
   geometry.
4. Depth and normal consistency is a PLAUSIBILITY gate, not measured scan
   accuracy.  The reference photographs are AI generated and uncalibrated:
   there is no true 3D ground truth for the subject, so you can only judge
   whether the depth and normals are self consistent and plausible for a
   human head, never whether they are accurate to a millimetre.
5. Depth and normal maps must agree with the clay render.  If the depth map
   shows a flat card where the clay render shows a face, or the normal map
   contradicts the silhouette, that is a REGENERATE for the affected views.
6. Report the evidence, not the conclusion.  State what you measured in the
   clay/depth/wireframe evidence for each view before you give the aggregate
   label.

## What you must write

One file per candidate, in the folder you were given for verdicts (NOT
inside the bundle), containing

* the candidate id,
* one line of evidence and one label per view,
* the aggregate label,
* an explicit statement that no previous verdict, scorecard, evaluation file
  or judge note was read while producing this verdict.
"""
