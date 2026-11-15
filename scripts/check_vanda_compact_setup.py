"""Check the optional root-edge release before scheduling low-memory performance runs."""
import csv
import json
import os
from pathlib import Path
import re
import subprocess


run = os.environ['RUN_ID']
root = Path('results/updated_vanda_scaling') / run
data = Path(os.environ['DATA_ROOT'])
rank_memory_only = os.environ.get('PAGERANK_PREFLIGHT_RANK_MEMORY_ONLY') == '1'
output = root / os.environ.get('PAGERANK_PREFLIGHT_STAGE',
    'non512_rank_memory_preflight_20261115' if rank_memory_only else 'non512_memory_preflight_20261115')
output.mkdir(exist_ok=True)
env = os.environ.copy()
env.update(PAGERANK_REPEATS='1', PAGERANK_WARMUPS='0', OMP_NUM_THREADS='1',
           PAGERANK_KOKKOS_THREADS='1', OMP_DYNAMIC='FALSE', LC_ALL='C',
           OMPI_MCA_btl='self,vader,tcp', OMPI_MCA_pml='ob1',
           PAGERANK_ENVIRONMENT='vanda-free-validation-only')
original = './build-vanda-matrix-cpu/pagerank_mpi_kokkos'
compact = './' + os.environ.get('PAGERANK_MEMORY_BUILD_DIR', 'build-vanda-memory-repair') + '/pagerank_mpi_kokkos'
checks = []


def measure(graph, mode, binary, label):
    destination = output / graph / mode / label
    destination.mkdir(parents=True, exist_ok=True)
    manifest = destination / 'dataset.tsv'
    subprocess.run(['python3', 'scripts/select_graph_manifest.py',
                    str(data / 'manifests/strong_scaling.tsv'), graph, str(manifest)], check=True)
    settings = {**env, 'PAGERANK_RESULTS_ROOT': str(destination.resolve()),
                'PAGERANK_DATASET_MANIFEST': str(manifest.resolve())}
    if graph.startswith('strong_'):
        settings.update(PAGERANK_REPEATS='5', PAGERANK_WARMUPS='1')
    memory = destination / 'time.txt'
    command = ['mpiexec', '--bind-to', 'none', '-n', '1', '/usr/bin/time', '-v',
               '-o', str(memory.resolve()), binary, '--communication=' + mode]
    with (destination / 'run.log').open('w') as log:
        subprocess.run(command, env=settings, stdout=log, stderr=subprocess.STDOUT, check=True)
    maximum_kb = int(re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',
                               memory.read_text())[1])
    method = 'mpi_kokkos' + ('_halo' if mode == 'halo' else '')
    folder = destination / method / 'OpenMP' / graph / 'p1'
    summary = json.loads((folder / 'summary.json').read_text())
    assert summary['converged'] and summary['processes'] == summary['actual_threads'] == 1
    assert summary['repeat_runs'] == int(settings['PAGERANK_REPEATS'])
    assert summary['warmup_runs'] == int(settings['PAGERANK_WARMUPS'])
    checks.append({'graph': graph, 'communication': mode, 'binary': binary,
                   'max_rss_kb': maximum_kb, 'summary': str(folder / 'summary.json')})
    return folder, maximum_kb


for mode in (() if rank_memory_only else ('allgather', 'halo')):
    old, _ = measure('grid_controlled_n100000_d16', mode, original, 'original')
    new, _ = measure('grid_controlled_n100000_d16', mode, compact, 'compact')
    assert (old / 'ranks.csv').read_bytes() == (new / 'ranks.csv').read_bytes()
    assert (old / 'history.csv').read_bytes() == (new / 'history.csv').read_bytes()
    before, after = (json.loads((folder / 'summary.json').read_text()) for folder in (old, new))
    for name in ('nodes', 'edges', 'iterations', 'communication', 'alpha', 'tolerance_l1'):
        assert before[name] == after[name], name

for graph in ('strong_controlled', 'strong_hub'):
    for mode in ('allgather', 'halo'):
        _, maximum_kb = measure(graph, mode, compact, 'compact')
        # Leave space for MPI/PBS helpers inside the paid one-core 6 GiB allocation.
        assert 1024**2 < maximum_kb < (6 * 1024 - 192) * 1024, (graph, mode, maximum_kb)

if rank_memory_only:
    previous = json.loads((root / 'requirements/compact_correctness_launcher_rss_20261115.json').read_text())
    assert previous['original_small_graph_ranks_and_history_identical']

proof = {'job': os.environ['PBS_JOBID'], 'purpose': 'validation only; never performance data',
         'original_small_graph_ranks_and_history_identical': True,
         'rss_scope': 'GNU time runs inside the MPI rank, measures the actual solver process',
         'timed_solver_unchanged': True, 'tests': checks}
target = root / 'requirements/large_graph_one_core_memory_verified.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2), flush=True)
