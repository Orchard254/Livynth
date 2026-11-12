"""IDENTITY-020: safety contract for one in-memory Blender seam-copy probe."""
import tempfile
import unittest
from pathlib import Path

from character.mhclo_dentition import DentitionMappingError
from tools.mhclo_dental_preflight import diagnose_mixed_jaw_faces
from tools.mhclo_seam_copy_probe import (
    SeamCopyError, load_obj_positions, plan_seam_copy)


def source():
    mappings = {
        i: {'verts': (14992,14993,0) if i < 20 else (15060,15061,0),
            'weights': (1.2,-.2,0.) if i < 20 else (1.,0.,0.)}
        for i in range(40)
    }
    faces = [(0,1,2),(20,21,22),(0,1,20,21)]
    return mappings, faces


class SeamCopyProbeTests(unittest.TestCase):
    def test_safe_bridge_plan_retains_exact_faces_and_strict_jaw_assignment(self):
        mapping, faces = source()
        dry = diagnose_mixed_jaw_faces(mapping, faces)
        original = list(faces)
        bridge, kept, lower, audit = plan_seam_copy(mapping, faces, dry)
        self.assertEqual(bridge, [2])
        self.assertEqual(kept, [(0,1,2),(20,21,22)])
        self.assertEqual(len(lower), 40)
        self.assertEqual(audit['mixed_jaw_faces'], 0)
        self.assertEqual(audit['upper_teeth_vertices'], 20)
        self.assertEqual(audit['lower_teeth_vertices'], 20)
        self.assertEqual(faces, original)

    def test_no_mixed_face_cannot_claim_seam_proof(self):
        mapping, faces = source()
        clean = faces[:2]
        dry = diagnose_mixed_jaw_faces(mapping, clean)
        with self.assertRaisesRegex(SeamCopyError, 'E_SEAM_PLAN_UNSAFE_TO_EXCLUDE'):
            plan_seam_copy(mapping, clean, dry)

    def test_orphaned_vertex_must_fail_before_any_blender_operation(self):
        mapping, faces = source()
        dry = diagnose_mixed_jaw_faces(mapping, faces)
        dry['seam_cut_dry_run']['newly_unused_vertices'] = 1
        with self.assertRaisesRegex(SeamCopyError, 'E_SEAM_PLAN_UNSAFE_TO_EXCLUDE'):
            plan_seam_copy(mapping, faces, dry)

    def test_missing_bridge_face_cannot_reclassify_bad_mesh(self):
        mapping, faces = source()
        dry = diagnose_mixed_jaw_faces(mapping, faces)
        dry['seam_cut_dry_run']['bridge_face_indices_preview'] = [0]
        with self.assertRaises(DentitionMappingError):
            plan_seam_copy(mapping, faces, dry)

    def test_obj_positions_load_strict_finite_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'teeth.obj'
            path.write_text('\n'.join(['v 1.25 2.5 -3.0']*40)+'\n',
                            encoding='utf-8')
            self.assertEqual(len(load_obj_positions(path)), 40)
            self.assertEqual(load_obj_positions(path)[0],(1.25,2.5,-3.0))

    def test_invalid_obj_position_fails_without_blender(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'teeth.obj'
            path.write_text('\n'.join(['v 0 1 nan']*40)+'\n',
                            encoding='utf-8')
            with self.assertRaisesRegex(SeamCopyError,'E_SEAM_OBJ_NONFINITE'):
                load_obj_positions(path)


if __name__ == '__main__':
    unittest.main()
