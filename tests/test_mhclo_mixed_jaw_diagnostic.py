"""IDENTITY-018: read-only source face diagnostics, strict jaw gate unchanged."""
import unittest

from character.mhclo_dentition import (
    classify_dentition_mhclo, DentitionMappingError)
from tools.mhclo_dental_preflight import (
    diagnose_mixed_jaw_faces, DentalPreflightError)


def fixture():
    mapping = {
        i: {
            'verts': (14992, 14993, 0) if i < 20 else (15060, 15061, 0),
            'weights': (1.2, -.2, 0.) if i < 20 else (1., 0., 0.),
        }
        for i in range(40)
    }
    faces = [(0, 1, 2), (19, 20, 21), (18, 19, 20), (20, 21, 22)]
    return mapping, faces


class MixedJawDiagnosticTests(unittest.TestCase):
    def test_mixed_boundary_counts_and_bounded_samples(self):
        mapping, faces = fixture()
        report = diagnose_mixed_jaw_faces(mapping, faces, sample_limit=1)
        self.assertEqual(report['mixed_face_count'], 2)
        self.assertEqual(report['mixed_face_unique_vertices'], 4)
        self.assertEqual(len(report['samples']), 1)
        self.assertEqual(report['samples'][0]['face_index'], 1)
        self.assertEqual(
            [x['jaw'] for x in report['samples'][0]['vertices']],
            ['lower', 'upper', 'upper'])
        self.assertEqual(
            report['samples'][0]['vertices'][0]['refs'], [14992, 14993, 0])
        self.assertFalse(report['production_classifier_bypassed'])
        self.assertEqual(report['visual_quality'], 'NOT_TESTED')

    def test_full_face_samples_include_references_and_source_weights(self):
        mapping, faces = fixture()
        report = diagnose_mixed_jaw_faces(mapping, faces, sample_limit=8)
        self.assertEqual([x['face_index'] for x in report['samples']], [1, 2])
        self.assertEqual(report['samples'][0]['vertices'][0]['weights'],
                         [1.2, -.2, 0.])

    def test_production_gate_still_rejects_faces(self):
        mapping, faces = fixture()
        with self.assertRaisesRegex(
                DentitionMappingError, 'E_MHCLO_MIXED_UPPER_LOWER_FACE'):
            classify_dentition_mhclo(40, mapping, faces)

    def test_ambiguous_weight_references_fail_closed(self):
        mapping, faces = fixture()
        mapping[0] = {
            'verts': (14992, 15060, 0),
            'weights': (.7, .3, 0.),
        }
        with self.assertRaisesRegex(
                DentalPreflightError, 'E_MIXED_FACE_DIAGNOSTIC_JAW_VERTEX'):
            diagnose_mixed_jaw_faces(mapping, faces)

    def test_sample_bounds_rejected(self):
        mapping, faces = fixture()
        for limit in (0, 33, True):
            with self.assertRaisesRegex(
                    DentalPreflightError, 'E_MIXED_FACE_DIAGNOSTIC_INPUT'):
                diagnose_mixed_jaw_faces(mapping, faces, sample_limit=limit)


if __name__ == '__main__':
    unittest.main()
