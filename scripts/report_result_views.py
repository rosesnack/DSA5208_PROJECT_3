"""Matched presentation views derived from the existing validated measurements."""
import csv
from pathlib import Path


def growing_cpu(weak):
    rows = []
    for family in ('uniform', 'hub', 'controlled'):
        for method in ('MPI', 'MPI+OpenMP', 'MPI+Kokkos OpenMP'):
            suite = 'rank_cpu_regular' if method == 'MPI' else 'core_cpu'
            for mode in ('Allgatherv', 'Halo'):
                series = [r for r in weak if r['suite'] == suite and r['family'] == family
                          and r['method'] == method and r['communication'] == mode
                          and 4 <= int(r['active_cpu_threads']) <= 256]
                assert len(series) == 7
                reference = next(r for r in series if int(r['active_cpu_threads']) == 4)
                for row in series:
                    cores = int(row['active_cpu_threads'])
                    assert int(row['vertices']) == 50000 * cores
                    assert int(row['edges']) == 800000 * cores
                    assert int(row['processes']) * int(row['threads']) == cores
                    rows.append({**{key: row[key] for key in ('suite', 'graph', 'family', 'method', 'communication',
                                 'processes', 'threads', 'active_cpu_threads', 'vertices', 'edges', 'iterations',
                                 'solve_median_s', 'seconds_per_iteration', 'source_summary')}, 'reference_cores': 4,
                                 'reference_summary': reference['source_summary'],
                                 'matched_efficiency': float(reference['seconds_per_iteration']) /
                                                       float(row['seconds_per_iteration'])})
    assert len(rows) == 126
    return rows


def payload_by_process(fixed):
    lookup = {(r['graph'], int(r['host_nodes']), int(r['processes']), r['communication']): r
              for r in fixed if r['context'] == 'cpu_node' and r['method'] == 'MPI'}
    rows = []
    for graph in sorted({r['graph'] for r in fixed}):
        for processes in (2, 4, 8, 16, 32, 64, 128, 256):
            nodes = max(1, processes // 32)
            allgatherv = lookup[graph, nodes, processes, 'Allgatherv']
            halo = lookup[graph, nodes, processes, 'Halo']
            reduction = 1 - float(halo['communication_bytes_per_iteration']) / float(
                allgatherv['communication_bytes_per_iteration'])
            assert 0 <= reduction <= 1
            rows.append(dict(graph=graph, family=allgatherv['family'], nodes=nodes,
                             processes=processes, threads=1, payload_reduction=reduction,
                             allgatherv_source=allgatherv['source_summary'],
                             halo_source=halo['source_summary']))
    assert len(rows) == 360
    return rows


def write_view(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
