"""IDENTITY-019: topology-only jaw seam preview; original geometry untouched."""
import unittest
from tools.mhclo_dental_preflight import diagnose_mixed_jaw_faces


def mapping():
    return {
        i: {'verts': (14992,14993,0) if i < 20 else (15060,15061,0),
            'weights': (1.2,-.2,0.) if i < 20 else (1.,0.,0.)}
        for i in range(40)
    }


class DentalSeamDryRunTests(unittest.TestCase):
    def test_bridge_face_can_disconnect_two_valid_shells_without_orphans(self):
        faces = [(0,1,2),(20,21,22),(0,1,20,21)]
        original_faces = list(faces)
        result = diagnose_mixed_jaw_faces(mapping(),faces)
        dry = result['seam_cut_dry_run']
        self.assertEqual(dry['original_faces'],3)
        self.assertEqual(dry['remaining_faces'],2)
        self.assertEqual(dry['bridge_faces_to_exclude'],1)
        self.assertEqual(dry['bridge_face_indices_preview'],[2])
        self.assertEqual(dry['remaining_upper_faces'],1)
        self.assertEqual(dry['remaining_lower_faces'],1)
        self.assertEqual(dry['newly_unused_vertices'],0)
        self.assertEqual(dry['before']['connected_vertex_components'],1)
        self.assertEqual(dry['after']['connected_vertex_components'],2)
        self.assertTrue(dry['all_remaining_faces_single_jaw'])
        self.assertFalse(dry['source_mesh_changed'])
        self.assertFalse(dry['copied_mesh_changed'])
        self.assertEqual(faces,original_faces)

    def test_removed_faces_may_leave_orphaned_vertices_and_must_be_reported(self):
        faces = [(0,1,2),(19,20,21),(18,19,20),(20,21,22)]
        dry = diagnose_mixed_jaw_faces(mapping(),faces)['seam_cut_dry_run']
        self.assertEqual(dry['bridge_faces_to_exclude'],2)
        self.assertEqual(dry['newly_unused_vertices'],2)
        self.assertEqual(dry['newly_unused_vertex_indices_preview'],[18,19])

    def test_no_bridge_faces_means_no_mesh_cut(self):
        faces = [(0,1,2),(20,21,22)]
        dry = diagnose_mixed_jaw_faces(mapping(),faces)['seam_cut_dry_run']
        self.assertEqual(dry['bridge_faces_to_exclude'],0)
        self.assertEqual(dry['newly_unused_vertices'],0)
        self.assertEqual(dry['before'],dry['after'])
        self.assertEqual(dry['remaining_faces'],len(faces))

    def test_input_not_mutated_by_read_only_preview(self):
        faces = [(0,1,2),(20,21,22),(0,1,20,21)]
        entries = mapping()
        before = {i:{k:tuple(v) for k,v in row.items()}
                  for i,row in entries.items()}
        diagnose_mixed_jaw_faces(entries,faces)
        self.assertEqual(before,entries)
        self.assertEqual(faces,[(0,1,2),(20,21,22),(0,1,20,21)])


if __name__=='__main__':
    unittest.main()
