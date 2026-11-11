"""C001-GEO-04 gate - camera convention (clean-room, no shared code with the
candidate-producing lanes).

MODEL
-----
Orthographic weak-perspective, one camera per view:

    u = cx + s * (cos(psi) * x + sin(psi) * z)
    v = cy - s * y

with

    (x, y, z)  model frame of the exported GLB:
                +x  model right axis
                +y  model UP axis
                +z  model FACE axis (direction the face points)
    psi        camera azimuth about the vertical axis, degrees.
                psi =   0  -> camera on the -z side, looking towards +z ("front")
                psi = +90  -> camera on the +x side
                psi = -90  -> camera on the -x side
    s          pixels per metre (scale of that view)
    (cx, cy)   principal point in pixels, origin top-left, image plane of the
                reference photograph that the view corresponds to.

AXIS MAPPING INTO BLENDER
--------------------------
glTF import into Blender maps

    glTF +x -> Blender +X
    glTF +y (up)  -> Blender +Z
    glTF +z (face) -> Blender -Y

so the Blender point is  p_B = (x, z, y).

The orthographic camera is placed with

    local +X (image right) = ( cos psi, -sin psi, 0 )   in Blender coords
    local +Y (image up)    = ( 0, 0, 1 )
    local -Z (view dir)    = ( sin psi, cos psi, 0 )
    camera position        = ( -sin psi, -cos psi, 0 ) * D   in Blender coords
                          = ( -sin psi, 0, cos psi ) * D   in model coords
    image right in model   = ( cos psi, 0, sin psi )
    view direction (model) = ( sin psi, 0, -cos psi )

which reproduces the projection above exactly.  The renderer verifies this
numerically on every run (analytic vertex bbox vs rendered silhouette bbox,
see geo/gate/blender_render.py).

BLENDER CAMERA PARAMETERS
--------------------------
    ortho_scale = L / s            with L = max(W, H) (the long image side)
    shift_x     = (cx - W/2) / L
    shift_y     = (cy - H/2) / L   (sign verified by the self-check)

ASSUMPTIONS (stated, not measured)
----------------------------------
A1. The reference photographs are AI-generated portraits.  They carry no EXIF
    and no camera intrinsics.  There is NO ground-truth 3D of the subject.
A2. The reference set is therefore treated as a set of weak-perspective views
    with a *fitted* scale s and principal point (cx, cy) per view, so that a
    candidate head and the corresponding photograph can be compared in the
    same pixel frame.  The fitted constants live in
    geo/gate/reference_views.json and are data, not code.
A3. The reference "left" / "right" labels are resolved empirically per view
    by comparing the CLAY silhouette against the reference silhouette (the gate
    records both signs and the chosen one).  A mismatch here is a framing
    artefact, not an identity signal, and is reported separately.
A4. Depth and normal consistency is a PLAUSIBILITY gate, not measured scan
    accuracy: no true 3D ground truth exists for the reference subject.
A5. Head height is not independently calibrated.  Any quantity that mixes
    millimetres with the photograph scale is reported as a ratio only.
"""

import json
import math
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parent
REFERENCE_VIEWS_JSON = GATE_DIR / "reference_views.json"

AXIS_MAPPING = {
    "model_frame": "+x model right, +y model up, +z model face direction",
    "blender_frame": "x_B = x, y_B = z, z_B = y (glTF import)",
    "image_frame": "u right, v down, origin top-left",
}


def load_reference_views(path=None):
    p = Path(path) if path else REFERENCE_VIEWS_JSON
    return json.loads(p.read_text(encoding="utf-8"))


def project_point(point, view):
    """Project a model-frame 3D point to pixels with the gate convention."""
    x, y, z = float(point[0]), float(point[1]), float(point[2])
    psi = math.radians(float(view["phi"]))
    u = float(view["cx"]) + float(view["s"]) * (math.cos(psi) * x + math.sin(psi) * z)
    v = float(view["cy"]) - float(view["s"]) * y
    return u, v


def project_depth(point, view):
    """Distance along the camera view axis, in metres, for an ortho camera."""
    psi = math.radians(float(view["phi"]))
    x, y, z = float(point[0]), float(point[1]), float(point[2])
    return math.sin(psi) * x - math.cos(psi) * z


def blender_camera(view, width, height, centre, extent):
    """Return the Blender camera placement that reproduces a reference view."""
    psi = math.radians(float(view["phi"]))
    dist = 4.0 * extent + 1.0
    loc = (-math.sin(psi) * dist,
           -math.cos(psi) * dist,
           0.0)
    L = max(width, height)
    return {
        "location": list(loc),
        "ortho_scale": L / float(view["s"]),
        "shift_x": (float(view["cx"]) - width / 2.0) / L,
        "shift_y": (float(view["cy"]) - height / 2.0) / L,
        "clip_start": max(0.001, dist - 3.0 * extent),
        "clip_end": dist + 3.0 * extent,
    }


def view_names(calib):
    return [k for k, v in calib["views"].items() if not v.get("top")]
