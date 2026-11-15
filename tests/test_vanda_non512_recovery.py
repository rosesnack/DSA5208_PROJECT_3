"""Protect saved results and resource layouts when repairing the remaining non-512 cells."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plan_vanda_non512_recovery import prepare


class RecoveryTests(unittest.TestCase):
    def test_followup_reuses_nineteen_intact_cells_and_transfers_only_fifty_five(self):
        report = ROOT / 'results/updated_vanda_scaling/storage_recovery_20261116/remaining_inspection.json'
        paid, reused = prepare(json.loads(report.read_text()), '20261116',
                               'build-vanda-memory-repair-20261116')
        paid_keys = {c['canonical_summary'] for g in paid for c in g['cells']}
        reused_keys = {c['canonical_summary'] for g in reused for c in g['cells']}
        self.assertEqual((len(paid_keys), len(reused_keys)), (55, 19))
        self.assertFalse(paid_keys & reused_keys)
        for group in paid:
            if group['cores_per_node'] == 1:
                self.assertIn('20261116', group['executables']['mpi_kokkos'])
            else:
                self.assertNotIn('executables', group)

    def test_reviewed_saved_cells_never_enter_paid_plan_and_every_target_has_one_action(self):
        report = ROOT / 'results/updated_vanda_scaling/non512_recovery_20261115/inspection.json'
        inspection = json.loads(report.read_text())
        paid, reused = prepare(inspection)
        paid_keys = {c['canonical_summary'] for g in paid for c in g['cells']}
        reused_keys = {c['canonical_summary'] for g in reused for c in g['cells']}
        self.assertEqual(len(paid_keys), 96)
        self.assertEqual(len(reused_keys), 18)
        self.assertFalse(paid_keys & reused_keys)
        expected = {c['canonical_summary'] for item in inspection['groups']
                    for c in item['group']['cells']}
        self.assertEqual(paid_keys | reused_keys, expected)
        for group in paid + reused:
            self.assertLessEqual(group['cores'], 256)
            for cell in group['cells']:
                self.assertEqual(cell['processes'] * cell['threads'], group['cores'])
                self.assertEqual(cell['processes'] % group['nodes'], 0)

    def test_recovery_never_writes_into_original_partial_measurement_directories(self):
        report = ROOT / 'results/updated_vanda_scaling/non512_recovery_20261115/inspection.json'
        paid, reused = prepare(json.loads(report.read_text()))
        self.assertTrue(all(g['raw_stage'] == 'cpu_recovery_20261115' for g in paid))
        self.assertTrue(all(g['raw_stage'] == 'cpu_reuse_20261115' for g in reused))
        self.assertTrue(all('/cpu_core_groups/' in g['reuse_source'] for g in reused))


if __name__ == '__main__':
    unittest.main()
