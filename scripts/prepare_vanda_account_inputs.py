"""Reuse existing graph inputs and Serial references when transferring a batch."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('reference_data_root', type=Path)
    args = parser.parse_args()
    data = Path(os.environ['DATA_ROOT'])
    graphs = sorted({g['graph'] for g in json.loads(args.plan.read_text())})
    manifest = data / 'manifests/strong_scaling.tsv'
    rows = {line.split()[0]: line.split() for line in manifest.read_text().splitlines()
            if line.strip() and not line.startswith('#')}
    for graph in graphs:
        assert Path(rows[graph][1]).is_file(), rows[graph]
        if rows[graph][2] != '-':
            assert Path(rows[graph][2]).is_file(), rows[graph]
        target = data / 'results/serial_grid' / graph / 'serial' / graph
        source = args.reference_data_root / 'results/serial_grid' / graph / 'serial' / graph
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source.resolve(), target_is_directory=True)
        for name in ('summary.json', 'history.csv', 'timings.csv', 'ranks.csv'):
            assert (target / name).is_file(), target / name
        baseline = json.loads((target / 'summary.json').read_text())
        assert baseline['repeat_runs'] == 5 and baseline['warmup_runs'] == 1
    cache = Path('build-vanda-matrix-cpu/CMakeCache.txt').read_text()
    assert 'CMAKE_BUILD_TYPE:STRING=Release' in cache
    for name in ('pagerank_mpi', 'pagerank_hybrid', 'pagerank_mpi_kokkos'):
        assert os.access(Path('build-vanda-matrix-cpu') / name, os.X_OK), name
    receipt = {'preparation_job': os.environ['PBS_JOBID'], 'graphs': graphs,
               'reference_data_root': str(args.reference_data_root),
               'serial_performance_rerun': False, 'new_build': False}
    destination = Path('results/updated_vanda_scaling') / os.environ['RUN_ID']
    receipt_name = os.environ.get('PAGERANK_INPUT_RECEIPT', 'phase3_inputs_ready_20261111.json')
    (destination / receipt_name).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
