#!/usr/bin/env python3
"""IDENTITY-029: isolated dental-visibility and lip-aperture diagnostics.

Blender-side only. This module renders the diagnostic frames and records
exactly what was visible in each one. Every MEASUREMENT (visibility
fraction, aperture outline, V-score) is done afterwards by
``character.oral_visibility`` on the rendered PNGs, so the maths stays
pure, Blender-free and unit-testable.

Diagnostic convention
---------------------
* The upper arch is painted pure red, the lower arch pure blue, with
  unlit emission materials, so a pixel classification is unambiguous.
* The body's oral-cavity material slot is swapped for a pure green
  emission material to expose the true shape of the oral opening
  (the "aperture") without any lighting guesswork.
* The diagnostics run with the Standard view transform and a transparent
  film, so a diagnostic colour appears in the PNG byte-for-byte.

Nothing here reads or writes a source asset: the diagnostics operate on
the disposable copied scene only and restore every scene property they
touch.
"""
from __future__ import annotations

DIAG_UPPER_RGB = (1.0, 0.0, 0.0)
DIAG_LOWER_RGB = (0.0, 0.0, 1.0)
DIAG_CAVITY_RGB = (0.0, 1.0, 0.0)
COLOR_TOLERANCE = 0.06
SCHEMA = 'livynth.oral-visibility.blender.v1'


class OralVisibilityBlenderError(RuntimeError):
    pass


def _emission_material(name, rgb):
    """Flat, unlit diagnostic material (exact colour under Standard view)."""
    import bpy
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (
        float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)
    emission.inputs['Strength'].default_value = 1.0
    tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return material


def _slot_materials(obj):
    return list(obj.data.materials)


def _set_slot_materials(obj, materials):
    obj.data.materials.clear()
    for material in materials:
        obj.data.materials.append(material)


class _SceneGuard:
    """Archive and restore every scene property the diagnostics touch."""

    def __init__(self, scene, body, objects, tongue):
        self.scene = scene
        self.body = body
        self.objects = objects
        self.tongue = tongue
        self._hidden = {}
        self._slots = {}
        self._view_transform = None
        self._look = None
        self._film_transparent = None

    def __enter__(self):
        self._hidden['body'] = self.body.hide_render
        if self.tongue is not None:
            self._hidden['tongue'] = self.tongue.hide_render
        for key, obj in self.objects.items():
            self._hidden[key] = obj.hide_render
            self._slots[key] = _slot_materials(obj)
        self._view_transform = self.scene.view_settings.view_transform
        self._look = self.scene.view_settings.look
        self._film_transparent = self.scene.render.film_transparent
        return self

    def __exit__(self, exc_type, exc, tb):
        self.body.hide_render = self._hidden['body']
        if self.tongue is not None:
            self.tongue.hide_render = self._hidden['tongue']
        for key, obj in self.objects.items():
            obj.hide_render = self._hidden[key]
            _set_slot_materials(obj, self._slots[key])
        self.scene.view_settings.view_transform = self._view_transform
        self.scene.view_settings.look = self._look
        self.scene.render.film_transparent = self._film_transparent
        import bpy
        bpy.context.view_layer.update()
        return False


def _standard_view(scene):
    """Standard view transform: a 1.0 emission lands on 255 in the PNG."""
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError as exc:
        raise OralVisibilityBlenderError(
            'E_ORAL_VIS_VIEW_TRANSFORM: ' + str(exc))
    try:
        scene.view_settings.look = 'None'
    except TypeError:
        pass
    scene.render.film_transparent = True


def _tint_teeth(objects, upper_material, lower_material):
    _set_slot_materials(objects['upper_teeth'],
                        [upper_material] * len(_slot_materials(
                            objects['upper_teeth'])))
    _set_slot_materials(objects['lower_teeth'],
                        [lower_material] * len(_slot_materials(
                            objects['lower_teeth'])))


def capture_oral_visibility(scene, body, objects, tongue, render, set_pose, *,
                            poses, stage, update=None, cavity_indexes=None):
    """Render the IDENTITY-029 diagnostic frames for every pose.

    ``render(name)`` writes ``<name>.png`` into the run output folder and
    returns a record; ``set_pose(label)`` applies the named pose to the
    body and the controlled oral assets; ``update()`` refreshes the
    depsgraph (defaults to ``bpy.context.view_layer.update``).

    ``stage`` is ``'before'`` or ``'after'`` the lip correction and is
    used purely as a filename/metadata tag.
    """
    import bpy
    if update is None:
        def update():
            bpy.context.view_layer.update()
    if stage not in ('before', 'after'):
        raise OralVisibilityBlenderError('E_ORAL_VIS_STAGE_' + str(stage))
    upper_material = _emission_material('livynth_diag_upper_arch',
                                        DIAG_UPPER_RGB)
    lower_material = _emission_material('livynth_diag_lower_arch',
                                        DIAG_LOWER_RGB)
    cavity_material = _emission_material('livynth_diag_cavity',
                                         DIAG_CAVITY_RGB)
    images = []
    with _SceneGuard(scene, body, objects, tongue) as guard:
        _standard_view(scene)
        body_slots = _slot_materials(body)
        if len(body_slots) < 2:
            raise OralVisibilityBlenderError('E_ORAL_VIS_BODY_SLOTS')
        cavity_slot = 1
        for pose in poses:
            set_pose(pose)
            update()
            prefix = 'diag_%s_%s' % (stage, pose)

            # --- 1. arches only (body, tongue and gums hidden) ---------
            body.hide_render = True
            if tongue is not None:
                tongue.hide_render = True
            for key in ('upper_gum', 'lower_gum'):
                objects[key].hide_render = True
            _tint_teeth(objects, upper_material, lower_material)
            update()
            images.append(render(prefix + '_arches'))

            # --- 2. upper arch only ------------------------------------
            objects['upper_teeth'].hide_render = False
            objects['lower_teeth'].hide_render = True
            update()
            images.append(render(prefix + '_upper_arch'))

            # --- 3. lower arch only ------------------------------------
            objects['upper_teeth'].hide_render = True
            objects['lower_teeth'].hide_render = False
            update()
            images.append(render(prefix + '_lower_arch'))

            # --- 4. visible scene (body, tongue and gums in front) -----
            body.hide_render = False
            if tongue is not None:
                tongue.hide_render = False
            for key in ('upper_gum', 'lower_gum'):
                objects[key].hide_render = False
            objects['upper_teeth'].hide_render = False
            objects['lower_teeth'].hide_render = False
            update()
            images.append(render(prefix + '_visible'))

            # --- 5. the oral aperture (cavity faces lit flat green) ---
            for key in ('upper_teeth', 'lower_teeth',
                        'upper_gum', 'lower_gum'):
                objects[key].hide_render = True
            if tongue is not None:
                tongue.hide_render = True
            # Geometry-grounded aperture: paint the cavity-opening polygons
            # (from the BVH audit) with the flat green material so the
            # aperture mask is recovered from actual cavity geometry rather
            # than a luminance threshold. Restore material indices after.
            original_indices = None
            if cavity_indexes:
                original_indices = [body.data.polygons[i].material_index
                                    for i in cavity_indexes]
            _set_slot_materials(body, body_slots)
            body.data.materials[cavity_slot] = cavity_material
            if cavity_indexes:
                for i in cavity_indexes:
                    body.data.polygons[i].material_index = cavity_slot
            update()
            images.append(render(prefix + '_aperture'))
            if original_indices is not None:
                for idx, i in enumerate(cavity_indexes):
                    body.data.polygons[i].material_index = original_indices[idx]
            _set_slot_materials(body, body_slots)
            update()

    return {
        'schema': SCHEMA,
        'stage': stage,
        'poses': list(poses),
        'colors': {
            'upper_arch_rgb': list(DIAG_UPPER_RGB),
            'lower_arch_rgb': list(DIAG_LOWER_RGB),
            'cavity_rgb': list(DIAG_CAVITY_RGB),
            'tolerance': COLOR_TOLERANCE,
        },
        'view_transform': 'Standard',
        'film_transparent': True,
        'images': images,
        'source_assets_modified': False,
        'scene_state_restored': True,
    }
