# C001-GEO-04 - blinded geometry-first evaluation gate

Owner: multiview-auditor (evaluation protocol lane)
Authority: ADR-C001-004 (geometry-first acceptance protocol)
Scope: this document defines the gate, the evidence it consumes, the rubric
and the controls.  It replaces nothing that came before; the Phase-3 FAIL
stands.

## 0. Why this lane exists

The Phase-3 gate failed twice in instructive ways.

* Run 1 read eval.json from inside the evaluation bundle, so the second judge
  was not blind.  The session was invalidated.
* Run 2 was clean but its numeric sub-gates were inadmissible.  A jitter
  canary (4,878 vertices, sigma 8 px) was NOT rejected by silhouette IoU
  (0.9036 against a 0.80 threshold) nor by the similarity-aligned landmark
  metric (8.92 px against a 16 px threshold).  A wrong-identity canary (face
  band widened 1.18x laterally, 3,801 vertices) was also NOT rejected
  (13.0 px landmarks, 0.0062 scale-normalised ratio deviation).

Root cause, and the rule that follows from it:

> A similarity-aligned 2D landmark metric is invariant to uniform scaling.
> For a candidate whose face is a PROJECTED PHOTOGRAPH the rendered
> appearance IS the reference photograph, so an appearance metric measures
> the photograph, not the geometry.

Consequences for this gate:

1. The decisive measurements are taken from CLAY renders, DEPTH maps,
   NORMAL maps and the candidate MESH.  They never read the texture.
2. Appearance metrics are kept, but only as diagnostics, and they are
   reported side by side with the geometry metrics so that the difference
   is visible.
3. A wrong-identity control that the gate does not reject invalidates the
   GATE, not just the candidate.  The run then reports gate_valid = false.

## 1. Camera convention

Orthographic, one camera per view, 1086 x 1448 px.

    u = cx + s * (cos(psi) * x + sin(psi) * z)
    v = cy - s * y

* model frame of the exported GLB: +x right, +y up, +z the face direction
  (the glTF frame; trimesh loads a GLB unrotated, Blender maps
  p_B = (x, -z, y)).
* psi is the camera azimuth about the vertical axis: psi = 0 is the camera
  on the -z side looking towards +z, psi = +90 puts the camera on the +x
  side.
* s is pixels per metre, (cx, cy) the principal point in pixels, origin
  top-left.
* Blender placement: the camera AIMS AT THE MODEL ORIGIN so that the origin
  lands on the principal point; ortho_scale = L / s with L = max(W, H);
  shift_x = (cx - W/2) / L; shift_y = (cy - H/2) / L; the camera sits on the
  model ray (-sin psi, 0, cos psi).

The renderer verifies this numerically on every view: the analytic bbox of
the projected vertices is compared with the bbox of the rendered silhouette
(1.2 px on the reference candidate) and the rasteriser's own silhouette is
compared with Blender's alpha channel (mask IoU 0.9995).  The per-view
numbers are written into render_manifest.json.

ASSUMPTIONS (stated, not measured):

* A1. The reference photographs are AI generated, carry no EXIF and no
  intrinsics.  There is NO true 3D ground truth for the subject.
* A2. Each reference view is treated as a weak-perspective view with a
  fitted scale s and principal point (cx, cy) so that a candidate and the
  matching photograph share one pixel frame.
* A3. The reference crown and chin rows are manual annotations; the chin row
  of the 45 degree views is estimated from the front view head height scaled
  by that view's scale.  The SAME rows are used on the candidate clay
  renders.
* A4. Depth and normal consistency is a PLAUSIBILITY gate, not measured scan
  accuracy.
* A5. A candidate may be in a different frame and a different size.  The
  gate therefore fits, per candidate and per view, the camera that puts the
  candidate's head silhouette into the reference's pixel frame
  (s = reference head width px / candidate head width m, then a box
  alignment).  The head width of the candidate is measured on its GEOMETRY,
  never on an image, so the fit cannot launder appearance into geometry.
  Shape ratios are then compared in metres on both sides.

## 2. Evidence produced by ONE Blender run per candidate

Per view (front, left45, right45, left90, right90):

* clay_<view>.png      uniform neutral grey matte, every texture disabled,
  alpha = silhouette.  THE geometry evidence.
* wire_<view>.png      Freestyle silhouette / crease / border edges.
* wireframe_<view>.png triangle wireframe (Wireframe modifier).
* review_depth_<view>.png  orthographic depth map, false colour.
* review_normal_<view>.png world-space surface normal map.
* textured_<view>.png  the candidate's own materials.  DIAGNOSTIC ONLY.

Depth and normal maps are produced by geo/gate/raster.py (a numpy z-buffer)
inside the same Blender run rather than by Blender's render passes, because
EEVEE Next's Z pass does not survive the compositor on this build and
because an exact, renderer independent depth map is required by the
geometry metrics.  The rasteriser's silhouette is cross-checked against
Blender's own alpha channel on every view.

The reference photographs have no geometry, so no clay/depth/normal
treatment can be applied to them.  Instead the bundle carries the reference
photographs, the reference silhouette masks and the reference landmark
overlay, and the gate measures the reference side in the same pixel frame
(silhouette widths, face band skin spans, photographic shading detail).

## 3. Artifact QA (machine measured, on the GLB)

Reported per candidate, with the method stated for each check:

| check | method |
| --- | --- |
| manifold / watertight | trimesh is_watertight, euler number, edges whose face adjacency is not exactly two (boundary and non-manifold counted separately) |
| connected components | trimesh.split(); per component faces, area, volume, mean thickness (volume/area) |
| duplicate / offset shell | (a) large components whose bounding boxes overlap, (b) near-duplicate faces with opposing normals inside a component, found with a spatial hash |
| self-intersection | vertices closer than 1 mm to a non-adjacent part of the surface (trimesh proximity) |
| topology class | glTF primitives are triangles by format; the raw polygon class is NOT recoverable from a GLB, so the report states primitive count, attribute set and whether indices are used |
| face normal consistency | is_winding_consistent plus the stored vertex normals |
| degenerate faces | zero-area faces |
| duplicate vertices | vertices sharing a position |
| UV | presence and coverage of the unit UV square |
| rig / blendshapes | skins, animations and morph targets in the raw glTF JSON, and whether they evaluate |
| camera assumptions | the orthographic convention of section 1 and the per-view fit |

## 4. The metric set

All decisive metrics are computed from clay/depth/normal/mesh evidence.

| metric | what it measures | reference side | tolerance |
| --- | --- | --- | --- |
| silhouette_face_band_ratio | median silhouette width over the eye-to-mouth rows divided by the head width | reference photo mask | 8 percent |
| profile_depth_width_ratio | head depth from the 90 degree profile silhouette divided by the head width from the front silhouette, both in metres | reference profile photos | 15 percent |
| relief_shading_correlation | correlation between the candidate's geometric relief (depth map, band-passed) and the reference photograph's photographic shading (luminance, band-passed) in the same face rectangle | reference photo | correlation at least 0.30, no more than 0.15 below 1.0 |
| band_spread_ratio | lateral spread of the surface that the reference eye band designates, divided by the head width | reference skin span in the same rectangle | 10 percent |
| surface_roughness_rel | Laplacian RMS of the surface relative to the median edge length | none (absolute limit) | at most 0.50 |
| depth_symmetry | mean asymmetry of the front depth profile about the face midline | none (absolute limit) | at most 0.05 |
| appearance_silhouette_iou | DIAGNOSTIC: silhouette IoU of the textured render against the reference head mask | reference photo | 5 percent |
| appearance_ncc | DIAGNOSTIC: cross correlation of the face crops, textured render against reference photo | reference photo | 5 percent |

Why the relief metric is decisive for the photo projection: for a candidate
whose face is a projected photograph the depth map is the depth of the
SHELL, not of a face.  The reference photograph's shading and the
candidate's geometric relief then describe different surfaces and the
correlation collapses.  The textured render, by contrast, still shows the
photograph, so the appearance metrics stay satisfied.

## 5. Wrong-identity controls

Controls are applied to the CANDIDATE MESH, in the regions that the
reference landmarks designate, and every controlled candidate is rendered
and measured again with the identical pipeline.

* face_band_widen  1.18x lateral widening of the whole face band (eyes and
  mouth).  The canary of the previous protocol.
* ipd_widen        1.12x widening of the eye band only.
* eye_shrink       the surface around each eye centre scaled to 0.80x.
* nose_lengthen    the surface around the nose tip pushed forward 1.25x.
* jitter           every vertex displaced by Gaussian noise of sigma 8 px.
  The canary of the previous protocol.
* photo_plane      the face region flattened onto a plane.  The projected
  photograph survives, so the appearance is unchanged while the geometry is
  destroyed.  This is the control that demonstrates the blindness of an
  appearance metric.

A control is REJECTED when at least one metric moves by more than its
tolerance relative to the unmodified baseline candidate.  The report lists
which metric rejected each control and, separately, which appearance metrics
did NOT move.

## 6. Gate validity

    gate_valid = every control of every candidate was rejected
                 AND the reviewer bundle verified clean

A run whose controls are not rejected is BLOCKED.  This is the ADR rule:
a false acceptance means the evaluation gate fails, not just the model.

## 7. The blinded bundle

output/qa/<run>/bundle/ contains only

* candidate_<ID>/ clay, wire, wireframe, depth, normal and one diagnostic
  textured render per view, plus camera_convention.json
* reference/ the reference photographs, their silhouette masks and the
  landmark overlay
* RUBRIC.md, ACCESS_RULES.md, README.md
* MANIFEST.json  the SHA-256 of every file

The candidate ids are random tokens.  The label to candidate map is SEALED
in output/qa/<run>/sealed/blind_map.json, physically outside the bundle,
together with a copy of the bundle manifest.  Verdicts are written into
output/qa/<run>/verdicts/, never into the bundle.

Before a reviewer is given the bundle, the verifier asserts

* no file name matches a verdict or backend pattern (eval, verdict,
  signoff, judge, score, notes, hull, triposr, backend, ...),
* no non-document file contains verdict text, a backend hint or a verdict
  bearing token, including inside PNG text chunks,
* the bundle manifest matches the sealed manifest and every file hash
  matches.

The bundle deliberately carries NO file sizes and NO timings, so the
pipeline cannot be identified from the bundle.

## 8. The rubric

See geo/gate/rubric.py for the generated text; it is copied into every
bundle as RUBRIC.md.  Summary:

* one label per view (ACCEPT / REFERENCE_ONLY / REGENERATE) for front,
  left45, right45, left90, right90, each with ONE line of observable
  evidence,
* a rejected profile can never be overridden by a good-looking front
  texture,
* the stricter aggregate label wins,
* the clay renders, wireframes and depth/normal maps are the geometry
  evidence; the textured render is diagnostic only,
* depth and normal consistency is a plausibility gate, not measured scan
  accuracy,
* the verdict must state that no previous verdict, scorecard, evaluation
  file or judge note was read.

## 9. What this gate cannot decide

* It cannot measure likeness to the subject in absolute terms.  There is no
  3D ground truth for the reference, only five uncalibrated AI generated
  photographs.
* It cannot certify a rig, a skin or a blend shape system: neither
  reference candidate carries one, and the rig checks only report whether
  the rig exists and whether it evaluates.
* It cannot decide whether the reference photographs are consistent with
  each other; the per-view scale of the reference set is a fitted constant
  and its uncertainty is not quantified here.
* Depth and normal consistency is a plausibility statement about the
  candidate alone, never an accuracy statement about the subject.
* The photographic-shading relief estimate is a proxy.  It assumes the
  reference lighting is broadly comparable with a studio key light and it
  is used as a plausibility gate, not as a measurement.
