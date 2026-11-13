"""Queued requests must use physical-host capacity without changing experiments."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refresh_vanda_cpu_placement import physical_capacity, placement_changes


class PlacementTests(unittest.TestCase):
    def test_two_numa_fragments_form_one_eligible_physical_host(self):
        nodes = {}
        for index in (0, 1):
            nodes[f'cn-a[{index}]'] = {
                'state': 'free',
                'resources_available': {'host': 'cn-a', 'node_pool': 'cpu_node',
                                        'switch': 'cpu_all', 'ncpus': 36, 'mem': '256gb'},
                'resources_assigned': {'ncpus': 32, 'mem': '228gb'}}
        nodes['unverified'] = {'state': 'free', 'resources_available': {
            'host': 'other-model', 'node_pool': 'cpu_node', 'switch': 'cpu_all',
            'ncpus': 72, 'mem': '512gb'}}
        capacity = physical_capacity(nodes, {'cn-a': 'validated proof'})
        self.assertEqual(set(capacity['cpu_all']), {'cn-a'})
        self.assertEqual(capacity['cpu_all']['cn-a'], {'cpu': 8, 'memory': 56 * 1024**3})

    def test_rebinding_preserves_chunk_resources_and_uses_distinct_physical_hosts(self):
        resources = {'ncpus': 16, 'nodect': 2, 'ngpus': 0, 'mem': '110gb',
                     'walltime': '01:00:00', 'place': 'scatter',
                     'select': '1:ncpus=8:mpiprocs=8:ompthreads=1:mem=55GB:node_pool=cpu_node:'
                               'switch=cpu_all:host=busy-a+1:ncpus=8:mpiprocs=8:ompthreads=1:'
                               'mem=55GB:node_pool=cpu_node:switch=cpu_all:host=busy-b'}
        jobs = {'a': {'job_state': 'Q', 'queue': 'batch_cpu', 'Resource_List': resources},
                'b': {'job_state': 'Q', 'queue': 'batch_cpu', 'Resource_List': copy.deepcopy(resources)}}
        rows = [{'performance_job': job, 'cores': '16'} for job in jobs]
        capacity = {'cpu_all': {host: {'cpu': 8, 'memory': 56 * 1024**3} for host in ('cn-a', 'cn-b')}}
        before = copy.deepcopy(resources)
        changes = placement_changes(rows, jobs, capacity, 256)
        self.assertEqual(len(changes), 1)  # The second request cannot reuse reserved slots in this pass.
        self.assertEqual(changes[0]['hosts'], ['cn-a', 'cn-b'])
        self.assertEqual(changes[0]['select'], resources['select'].replace('busy-a', 'cn-a').replace('busy-b', 'cn-b'))
        self.assertEqual(resources, before)

    def test_running_held_and_deferred_512_requests_are_untouched(self):
        jobs = {name: {'job_state': state, 'queue': 'batch_cpu',
                       'Resource_List': {'ncpus': 512, 'nodect': 8, 'ngpus': 0}}
                for name, state in [('running', 'R'), ('held', 'H'), ('endpoint', 'Q')]}
        rows = [{'performance_job': name, 'cores': '512'} for name in jobs]
        self.assertEqual(placement_changes(rows, jobs, {}, 256), [])

    def test_compatible_queued_binding_is_kept(self):
        resources = {'ncpus': 8, 'nodect': 1, 'ngpus': 0, 'mem': '55gb',
                     'select': '1:ncpus=8:mpiprocs=8:mem=55GB:switch=cpu_all:host=cn-a'}
        jobs = {'a': {'job_state': 'Q', 'queue': 'batch_cpu', 'Resource_List': resources}}
        self.assertEqual(placement_changes([{'performance_job': 'a', 'cores': '8'}], jobs,
                         {'cpu_all': {'cn-a': {'cpu': 8, 'memory': 56 * 1024**3}}}, 256), [])


if __name__ == '__main__':
    unittest.main()
