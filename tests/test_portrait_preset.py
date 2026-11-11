"""Pure portrait QA logic tests (no Blender installation needed)."""
import unittest

from video.render_talk import shot_settings, shirt_cutoff


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


if __name__=='__main__':
    unittest.main()
