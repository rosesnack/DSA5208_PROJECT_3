"""Split reviewed non-512 failures into saved-cell checks and missing performance cells."""
import argparse
import json
from pathlib import Path


def prepare(inspection):
    performance, reuse = [], []
    for item in inspection['groups']:
        group = item['group']
        assert group['cores'] <= 256
        saved = {row['cell']['canonical_summary'] for row in item['saved']}
        if saved:
            hosts = [json.loads(line) for line in item['metadata']['cpu_hosts.jsonl'].splitlines()]
            assert len({h['host'] for h in hosts}) == group['nodes']
            assert all('Platinum 8452Y' in h['cpu_model'] for h in hosts)
            for row in item['saved']:
                summary = row['summary']
                assert summary['warmup_runs'] == 1 and summary['repeat_runs'] == 5
                assert summary['build_type'] == 'Release'
            reuse.append({**group, 'cells': [c for c in group['cells'] if c['canonical_summary'] in saved],
                          'extension': 'reuse_20261115', 'raw_stage': 'cpu_reuse_20261115',
                          'reuse_source': item['raw'], 'reuse_saved_measurements': True})
        missing = [c for c in group['cells'] if c['canonical_summary'] not in saved]
        if missing:
            repaired = {**group, 'cells': missing, 'extension': 'repair_20261115',
                        'raw_stage': 'cpu_recovery_20261115', 'prerequisite': '',
                        'walltime': ('04:30:00' if group['graph'] == 'strong_hub' else '03:45:00')
                                    if group['graph'].startswith('strong_') else '01:00:00'}
            if group['graph'].startswith('strong_'):
                repaired['executables'] = {'mpi_kokkos': './build-vanda-memory-repair/pagerank_mpi_kokkos'}
                repaired['memory_setup'] = 'Root edge copy released after distribution, outside solver timing'
            performance.append(repaired)
    original = {c['canonical_summary'] for item in inspection['groups'] for c in item['group']['cells']}
    measured = [c['canonical_summary'] for g in performance for c in g['cells']]
    reused = [c['canonical_summary'] for g in reuse for c in g['cells']]
    assert not set(measured) & set(reused)
    assert len(set(measured)) == len(measured) and len(set(reused)) == len(reused)
    assert set(measured) | set(reused) == original
    return sorted(performance, key=lambda g: (g['cores'], g['graph'])), reuse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inspection', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    performance, reuse = prepare(json.loads(args.inspection.read_text()))
    args.output.mkdir(exist_ok=True)
    for name, value in [('performance_plan.json', performance), ('reuse_plan.json', reuse)]:
        (args.output / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'paid_groups': len(performance), 'paid_cells': sum(len(g['cells']) for g in performance),
                      'free_groups': len(reuse), 'reuse_cells': sum(len(g['cells']) for g in reuse)}))
