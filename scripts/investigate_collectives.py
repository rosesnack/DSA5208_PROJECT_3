"""Matched collective-policy and node-boundary controls, separate from the main matrix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


POLICIES = {
    'default': {},
    'a2av_linear': {'coll_tuned_use_dynamic_rules': '1', 'coll_tuned_alltoallv_algorithm': '1'},
    'a2av_pairwise': {'coll_tuned_use_dynamic_rules': '1', 'coll_tuned_alltoallv_algorithm': '2'},
    'agv_bruck': {'coll_tuned_use_dynamic_rules': '1', 'coll_tuned_allgatherv_algorithm': '2'},
    'agv_ring': {'coll_tuned_use_dynamic_rules': '1', 'coll_tuned_allgatherv_algorithm': '3'},
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def execute(command, env, log):
    with log.open('a') as stream:
        stream.write(json.dumps(command) + '\n'); stream.flush()
        subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def folder_for(cell):
    method = cell['implementation'] + ('_halo' if cell['communication'] == 'halo' else '')
    folder = Path(method)
    if cell['implementation'] == 'mpi_kokkos':
        folder /= 'OpenMP'
    config = 'p' + str(cell['processes'])
    if cell['implementation'] == 'hybrid' or cell['threads'] > 1:
        config += '_t' + str(cell['threads'])
    return folder / cell['graph'] / config


def case_env(cell, destination):
    env = os.environ.copy()
    # No inherited collective forcing or user rule file enters a paired control.
    for key in list(env):
        if key.startswith('OMPI_MCA_coll_'):
            env.pop(key)
    env.update(PAGERANK_ENVIRONMENT='vanda-gcc13-release', PAGERANK_REPEATS='5',
               PAGERANK_WARMUPS='1', PAGERANK_RESULTS_ROOT=str(destination),
               OMP_NUM_THREADS=str(cell['threads']), OMP_DYNAMIC='FALSE',
               OMP_PROC_BIND='spread', OMP_PLACES='cores',
               PAGERANK_HYBRID_THREADS=str(cell['threads']),
               PAGERANK_KOKKOS_THREADS=str(cell['threads']),
               PAGERANK_HYBRID_MAX_TOTAL_THREADS=str(cell['processes'] * cell['threads']))
    # Keep the component population identical in all paired policies. The default
    # policy uses tuned's fixed rules; other policies force only the named operation.
    env['OMPI_MCA_coll'] = 'tuned,basic,libnbc,self'
    env.update(OMPI_MCA_coll_tuned_use_dynamic_rules='0',
               OMPI_MCA_coll_tuned_alltoallv_algorithm='0',
               OMPI_MCA_coll_tuned_allgatherv_algorithm='0')
    for key, value in POLICIES[cell['policy']].items():
        env['OMPI_MCA_' + key] = value
    return env


def launcher(group, cell):
    if cell.get('launcher') == 'ompi_core':
        return ['mpiexec', '-x', 'LD_LIBRARY_PATH', '--map-by',
                'ppr:%d:node' % (cell['processes'] // group['nodes']),
                '--bind-to', 'core', '-n', str(cell['processes'])]
    return ['mpiexec', '-x', 'LD_LIBRARY_PATH', '--map-by',
            'ppr:%d:node' % (cell['processes'] // group['nodes']), '--bind-to', 'none',
            '-n', str(cell['processes']), 'python3', 'scripts/mpi_affinity_exec.py',
            str(cell['threads'])]


def check_mapping(records, group, cell):
    assert sorted(r['rank'] for r in records) == list(range(cell['processes']))
    hosts = {r['host'] for r in records}
    assert len(hosts) == group['nodes']
    for host in hosts:
        cpus = [cpu for r in records if r['host'] == host for cpu in r['cpus']]
        assert len(cpus) == len(set(cpus)) == 32
    assert all(len(r['cpus']) == cell['threads'] for r in records)


def compute(group):
    root = Path(group['output']); root.mkdir(parents=True, exist_ok=True)
    log = root / 'compute.log'
    execute(['bash', 'scripts/record_vanda_allocation.sh', str(root / 'cpu_hosts.jsonl')], os.environ.copy(), log)
    hosts = [json.loads(line) for line in (root / 'cpu_hosts.jsonl').read_text().splitlines()]
    assert len({h['host'] for h in hosts}) == group['nodes']
    assert all('Platinum 8452Y' in h['cpu_model'] for h in hosts)
    binaries = {'pagerank_' + c['implementation'] for c in group['cells']}
    metadata = {'job': os.environ['PBS_JOBID'], 'group': group,
                'binaries': {n: digest(Path('build-vanda-matrix-cpu') / n) for n in sorted(binaries)},
                'inherited_ompi': {k: v for k, v in os.environ.items() if k.startswith('OMPI_MCA_')},
                'controlled_component_population': 'tuned,basic,libnbc,self',
                'component_probes_outside_solver_timing': True}
    (root / 'environment.json').write_text(json.dumps(metadata, indent=2) + '\n')
    execute(['ompi_info', '--param', 'coll', 'tuned', '--level', '9'], os.environ.copy(), root / 'ompi_info.log')
    execute(['mpicc', 'scripts/mpi_collective_probe.c', '-o', str(root / 'collective_probe')], os.environ.copy(), log)
    # One untimed probe per distinct p/T/policy captures component-selection output.
    probed = set()
    for cell in group['cells']:
        case = root / cell['id']; case.mkdir(exist_ok=True)
        if (case / 'measurement_complete.txt').exists():
            continue
        env = case_env(cell, case)
        manifest = case / 'dataset.tsv'
        manifest.write_text(group['datasets'][cell['graph']] + '\n')
        env['PAGERANK_DATASET_MANIFEST'] = str(manifest)
        prefix = launcher(group, cell)
        started = time.time()
        mapping = subprocess.check_output(prefix + ['python3', 'scripts/report_core_group_affinity.py'], env=env, text=True)
        check_mapping([json.loads(line) for line in mapping.splitlines()], group, cell)
        (case / 'mapping.jsonl').write_text(mapping)
        signature = (cell['processes'], cell['threads'], cell['policy'], cell.get('launcher'))
        if signature not in probed:
            trace = env.copy(); trace['OMPI_MCA_coll_base_verbose'] = '30'
            trace['OMPI_MCA_coll_tuned_verbose'] = '100'
            execute(prefix + [str(root / 'collective_probe')], trace, case / 'component_probe.log')
            probed.add(signature)
        (case / 'settings.json').write_text(json.dumps({k: v for k, v in env.items()
            if k.startswith(('OMPI_MCA_', 'OMP_', 'PAGERANK_'))}, indent=2) + '\n')
        execute(prefix + ['./build-vanda-matrix-cpu/pagerank_' + cell['implementation'],
                          '--communication=' + cell['communication']], env, log)
        summary = json.loads((case / folder_for(cell) / 'summary.json').read_text())
        assert summary['processes'] == cell['processes']
        if cell['implementation'] == 'hybrid':
            assert summary['threads_per_process'] == [cell['threads']] * cell['processes']
        if cell['implementation'] == 'mpi_kokkos':
            assert summary['actual_threads'] == cell['threads']
        (case / 'measurement_complete.txt').write_text(os.environ['PBS_JOBID'] + '\n')
        (case / 'application_walltime.json').write_text(json.dumps({'seconds': time.time() - started}) + '\n')
    (root / 'measurement_complete.txt').write_text(os.environ['PBS_JOBID'] + '\n')


def validate(group):
    """Reuse an independent raw-edge reference scan and certify every new vector."""
    from validate_collective_controls import validate_group
    validate_group(group)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('compute', 'validate'))
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    group = json.loads(args.plan.read_text())
    {'compute': compute, 'validate': validate}[args.mode](group)


if __name__ == '__main__':
    main()
