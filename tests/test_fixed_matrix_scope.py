"""Keep the original target and the later 512-core request distinct and auditable."""
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_fixed_matrix import additional_512_cells, resolve_cell, vanda_cells
from export_vanda_handoff import source_jobs


class FixedMatrixScopeTests(unittest.TestCase):
    def test_resumed_batch_keeps_validation_job_separate_from_performance_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            summary = root / 'mpi_cuda/Cuda/graph/p2/summary.json'
            summary.parent.mkdir(parents=True)
            summary.write_text('{}')
            (root / 'job_environment.txt').write_text('PBS job: original-performance\n')
            (root / 'resume_gpu_complete.txt').write_text('resume-performance\n')
            marker = root / 'complete.txt'
            marker.write_text('independent-validator\n')
            perf, val, completion, candidates = source_jobs({'summary': str(summary), 'marker': str(marker)})
            self.assertEqual(perf, '')
            self.assertEqual(val, 'independent-validator')
            self.assertEqual(completion, 'independent-validator')
            self.assertEqual(set(candidates.split('|')), {'original-performance', 'resume-performance'})

    def test_full_target_adds_only_720_unique_512_splits(self):
        root = Path('results/test')
        original = list(vanda_cells(root))
        extra = list(additional_512_cells(root))
        old_paths = {c['summary'] for c in original}
        new_paths = {c['summary'] for c in extra}
        self.assertEqual(len(original), 19980)
        self.assertEqual(len(old_paths), 19980)
        self.assertEqual(len(extra), 720)
        self.assertEqual(len(new_paths), 720)
        self.assertFalse(old_paths & new_paths)
        self.assertEqual(len(old_paths | new_paths), 20700)
        for c in extra:
            layout = dict(x.split('=') for x in c['layout'].split(',') if '=' in x)
            self.assertEqual(int(layout['n']), 8)
            self.assertIn(int(layout['T']), (2, 8, 16, 32))
            self.assertEqual(int(layout['p']) * int(layout['T']), 512)

    def test_old_512_batch_does_not_validate_a_new_thread_split(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            c = next(additional_512_cells(root))
            c['summary'].parent.mkdir(parents=True)
            c['summary'].write_text('{}')
            old_marker = root / 'strong' / c['graph'] / 'nodes8_p512/complete.txt'
            old_marker.write_text('old-T1-T4-batch')
            resolved, _ = resolve_cell(c, root)
            self.assertFalse(resolved['marker'].exists())
            (c['summary'].parent / 'complete.txt').write_text('new-independent-check')
            resolved, _ = resolve_cell(c, root)
            self.assertTrue(resolved['marker'].exists())


if __name__ == '__main__':
    unittest.main()
