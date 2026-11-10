"""Account splitting must preserve ownership and never reclaim measured work."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from partition_vanda_account_plan import partition


class AccountPartitionTests(unittest.TestCase):
    def test_second_batch_keeps_full_node_groups_on_primary_and_uses_remaining_budget(self):
        groups = [
            {'graph': 'grid_hub_a', 'cores_per_node': 4, 'cores': 4, 'nodes': 1,
             'walltime': '00:20:00', 'cells': [{'canonical_summary': str(i)} for i in range(4)]},
            {'graph': 'grid_hub_b', 'cores_per_node': 32, 'cores': 32, 'nodes': 1,
             'walltime': '00:20:00', 'cells': [{'canonical_summary': 'full_node'}]},
            {'graph': 'grid_hub_c', 'cores_per_node': 8, 'cores': 8, 'nodes': 1,
             'walltime': '00:20:00', 'cells': [{'canonical_summary': 'too_large'}]}]
        primary, assist, reserved = partition(groups, set(), set(), 1.4, low_core=True)
        self.assertEqual([g['graph'] for g in assist], ['grid_hub_a'])
        self.assertAlmostEqual(reserved, 4 / 3)
        self.assertEqual({g['graph'] for g in primary}, {'grid_hub_b', 'grid_hub_c'})

    def test_partial_groups_remain_disjoint_and_respect_budget(self):
        def group(graph, cores, cells):
            return {'graph': graph, 'cores': cores, 'cores_per_node': 32, 'nodes': cores // 32,
                    'walltime': '01:00:00',
                    'cells': [{'canonical_summary': c} for c in cells]}
        groups = [group('grid_hub_a', 32, ['running', 'validated', 'missing']),
                  group('grid_hub_b', 64, ['over_budget']),
                  group('grid_hub_endpoint', 512, ['endpoint']),
                  group('grid_controlled_a', 32, ['other_family'])]
        primary, assist, reserved = partition(groups, {'running'}, {'validated'}, 32)
        assigned = {c['canonical_summary'] for g in assist for c in g['cells']}
        retained = {c['canonical_summary'] for g in primary for c in g['cells']}
        self.assertEqual(assigned, {'missing'})
        self.assertEqual(reserved, 32)
        self.assertFalse(assigned & retained)
        self.assertEqual(assigned | retained,
                         {'running', 'validated', 'missing', 'over_budget', 'endpoint', 'other_family'})


if __name__ == '__main__':
    unittest.main()
