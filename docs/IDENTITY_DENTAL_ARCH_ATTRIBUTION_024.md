# IDENTITY-024 — Upper/lower dental arch attribution on real posed Head A

## Established evidence

IDENTITY-021: Windows Blender and 10/10 tests PASS for 20-face seam exclusion
on a rigged disposable copy, preserving 3,868 tooth vertices and all skin
weights, UV/materials, and armature connection.

IDENTITY-022: Head A neutral/jaw-open two-still ZIP technically PASS, but
independent visual anatomy **FAIL**. 1,884 lower dental vertices move about
17.76 mm while all 1,984 upper vertices stay stationary. The visible mouth
looks like a grille and excess oral tissue, not natural teeth and tongue.

IDENTITY-023: Windows 12/12 tests PASS; real four-view render ZIP examined.
Compared at exactly the same pose, lighting and camera:

- The **pink upper-mouth dome is the tongue asset**: it disappears when
  the tongue is hidden.
- The **bright packed tooth row and large dark-red wedge below the row**
  are both from the teeth asset: both disappear when teeth are hidden.
  The wedge is consistent with gum geometry, not proven to be a particular
  submesh until arch-level isolation.
- A gray-speckled mouth surface remains even with **both teeth and tongue
  hidden**, so this portion comes from the base/body mesh and its material
  or internal geometry.
- These are THREE separate visual issues. Do not treat successful jaw
  displacement or topological separation as a visually approved mouth.

## Next small evidence gate: upper and lower arch isolation

Branch diagnostic/identity-024-dental-arch-isolation; stacked on PR #29.
Run **only** the new focused tests, then one opt-in Head A probe.

The existing Head A seam correction, alignment, shape-target interface and
jaw-open evaluation run unmodified. After the numerical jaw motion gates,
the diagnostic evaluates the **deformed** teeth once (shape keys/rig motion
already applied), creates two temporary Blender data meshes and removes the
opposite-jaw vertices from each. The source mask remains the SHA-pinned
MHCLO helper mapping; no Z-height guessing. Expected proof:
upper: 1,984 vertices, 1,818 source-labeled faces;
lower: 1,884 vertices, 1,722 source-labeled faces.
All original vertex IDs are preserved as a temporary int attribute.

It takes **four stills**:
1. jaw_upper_only.png — upper arch; tongue and lower teeth hidden
2. jaw_lower_only.png — lower arch; tongue and upper teeth hidden
3. jaw_both_arches.png — both arches, tongue hidden
4. jaw_lower_no_body.png — lower arch alone, body hidden

The lower-only with/without body comparison distinguishes lower arch
presence from lower lip/body occlusion. A JSON report additionally logs
the evaluated three-axis world-space bounds and centroids for both arches
and tongue at jawOpen=0.85 to identify suspect source alignment/depth.
World-axis occupancy **does not** certify tissue clearance or contact.

The temporary separated arch meshes are deleted in finally. MPFB installed
assets, existing GLBs, real copied rigged teeth, body materials and source
body are not modified. Neither main nor earlier PRs is merged.

## Owner commands (after pulling branch)

    python -m unittest discover -s tests -p "test_mhclo_dental_arch_isolation.py" -v
    python tools/run_mpfb_dental_arch_isolation.py

If successful, upload identity024_dental_arch_isolation.zip; otherwise
send the full error. No A/B 12-pose run, no unsupported claims of anatomy
or character likeness. New Windows tests and Head A renders remain PENDING.
