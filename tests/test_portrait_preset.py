"""Pure portrait QA logic tests (no Blender installation needed)."""
import unittest
from types import SimpleNamespace

from video.render_talk import shot_settings, studio_palette, shirt_cutoff, find_face_body_mesh, mesh_shape_inventory


class PortraitPresetTests(unittest.TestCase):
    def test_studio_is_tighter_than_legacy(self):
        studio=shot_settings(1.6,'studio')
        legacy=shot_settings(1.6,'legacy')
        self.assertLess(studio['ortho_scale'],legacy['ortho_scale'])
        self.assertLess(studio['camera_drop'],legacy['camera_drop'])

    def test_studio_camera_centers_nearer_head(self):
        height=1.6
        crown=1.6
        center=crown-height*shot_settings(height,'studio')['camera_drop']
        self.assertGreater(center,1.40)

    def test_studio_crop_is_bounded_and_moves_up_for_bigger_face(self):
        studio=shot_settings(1.74729,'studio')
        legacy=shot_settings(1.74729,'legacy')
        # Hard regression against the actual 2026-11-12 Windows smoke frame.
        self.assertGreaterEqual(studio['ortho_scale'],0.18)
        self.assertLessEqual(studio['ortho_scale'],0.24)
        self.assertGreaterEqual(studio['camera_drop'],0.04)
        self.assertLessEqual(studio['camera_drop'],0.08)
        self.assertLess(studio['ortho_scale'],0.29)
        self.assertLess(studio['camera_drop'],0.11)
        self.assertLess(studio['ortho_scale'],legacy['ortho_scale'])

    def test_neutral_clay_and_navy_shirt_are_visibly_distinct(self):
        colors=studio_palette()
        self.assertEqual(set(colors),{'skin','shirt'})
        for role,rgba in colors.items():
            with self.subTest(role=role):
                self.assertEqual(len(rgba),4)
                self.assertEqual(rgba[-1],1.0)
                self.assertTrue(all(0 <= channel <= 1 for channel in rgba))
        # Compare approximate luminance; clay must be brighter than garment.
        clay=colors['skin']
        shirt=colors['shirt']
        luma=lambda v: .2126*v[0]+.7152*v[1]+.0722*v[2]
        self.assertGreater(luma(clay),3*luma(shirt))
        self.assertGreater(clay[0],clay[2])  # warm, not blue diagnostic skin
        self.assertGreater(shirt[2],shirt[0])  # navy placeholder

    def test_reject_invalid_height(self):
        for h in (0,-1,0.05,11):
            with self.assertRaises(ValueError):
                shot_settings(h,'studio')

    def test_shirt_recolors_upper_torso(self):
        height,crown=1.6,1.6
        self.assertTrue(shirt_cutoff(0,1.2,0,crown,height))
        self.assertFalse(shirt_cutoff(0,1.5,0,crown,height))

    def test_shirt_cutoff_higher_at_shoulders(self):
        height,crown=1.6,1.6
        self.assertFalse(shirt_cutoff(0,1.26,0,crown,height))
        self.assertTrue(shirt_cutoff(0.30,1.26,0,crown,height))

    def test_shirt_cutoff_rejects_invalid_height(self):
        with self.assertRaises(ValueError):
            shirt_cutoff(0,1,0,1,0)


class BlenderImportedMeshSelectionTests(unittest.TestCase):
    @staticmethod
    def mesh(name, *shape_names):
        blocks=[SimpleNamespace(name=key) for key in shape_names]
        data=SimpleNamespace(shape_keys=SimpleNamespace(key_blocks=blocks) if blocks else None)
        return SimpleNamespace(name=name, data=data)

    def test_body_selected_by_shapes_even_with_renamed_object(self):
        markers=['eyeBlinkLeft','eyeBlinkRight','jawOpen','viseme_aa']
        hair=self.mesh('short01.001.005', *markers, *('hair'+str(i) for i in range(15)))
        body=self.mesh('Human_export_copy_base.004', *markers,
                       *('face'+str(i) for i in range(63)))
        eyebrows=self.mesh('brows', 'eyeBlinkLeft','eyeBlinkRight')
        selected=find_face_body_mesh([hair,eyebrows,body])
        self.assertIs(selected,body)

    def test_selection_does_not_depend_on_mesh_order(self):
        markers=['eyeBlinkLeft','eyeBlinkRight','jawOpen','viseme_aa']
        full=self.mesh('renamed-body', *markers, *('extra'+str(i) for i in range(63)))
        small=self.mesh('renamed-hair', *markers, 'extra0')
        for order in ([full,small], [small,full]):
            self.assertIs(find_face_body_mesh(order),full)

    def test_missing_face_morphs_fails_closed(self):
        eye=self.mesh('eye', 'eyeBlinkLeft','eyeBlinkRight')
        empty=self.mesh('static-body')
        self.assertIsNone(find_face_body_mesh([eye,empty]))
        self.assertIn('static-body (0 shape keys)',mesh_shape_inventory([empty]))

    def test_empty_scene_has_no_body(self):
        self.assertIsNone(find_face_body_mesh([]))



if __name__=='__main__':
    unittest.main()
