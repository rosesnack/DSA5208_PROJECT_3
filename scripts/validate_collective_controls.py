"""Certify each control against an independently raw-edge-validated Serial vector.

For PageRank's alpha-contractive map F, residual(x) <= residual(s) +
(1+alpha)*L1(x-s). Every output vector is checked in full; one independent
raw-edge reference scan is reused instead of rescanning identical edges.
"""
from array import array
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import statistics

from investigate_collectives import folder_for
from validate_serial import validate as validate_reference


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def certify_reference(group, graph, cache):
    reference = Path(group['serial_root']) / graph / 'serial' / graph
    _, edge, node = group['datasets'][graph].split()
    proof = cache / (graph + '.json')
    with (cache / (graph + '.lock')).open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if proof.exists():
            result = json.loads(proof.read_text())
            assert result['ranks_sha256'] == sha256(reference / 'ranks.csv')
        else:
            print('Independent raw-edge Serial residual:', graph, flush=True)
            result = validate_reference(graph, Path(edge), None if node == '-' else Path(node), reference)
            result.update(reference=str(reference), ranks_sha256=sha256(reference / 'ranks.csv'),
                          validation_job=os.environ['PBS_JOBID'], edge_path=edge, node_path=node)
            proof.write_text(json.dumps(result, indent=2) + '\n')
    return reference, result


def load_reference(reference):
    ranks, indegree, outdegree = array('d'), array('I'), array('I')
    with (reference / 'ranks.csv').open() as stream:
        for i, row in enumerate(csv.DictReader(stream)):
            assert int(row['node_id']) == i
            ranks.append(float(row['rank']))
            indegree.append(int(row['in_degree'])); outdegree.append(int(row['out_degree']))
    return ranks, indegree, outdegree


def certify_case(group, cell, reference, reference_check, vectors):
    case = Path(group['output']) / cell['id']; folder = case / folder_for(cell)
    summary = json.loads((folder / 'summary.json').read_text())
    baseline = json.loads((reference / 'summary.json').read_text())
    for key in ('dataset', 'environment', 'build_type', 'nodes', 'edges', 'alpha', 'tolerance_l1',
                'max_iterations', 'fixed_iterations', 'warmup_runs', 'repeat_runs', 'iterations'):
        assert summary[key] == baseline[key], key
    assert summary['warmup_runs'] == 1 and summary['repeat_runs'] == 5
    assert summary['implementation'] == cell['implementation'] and summary['processes'] == cell['processes']
    assert cell['processes'] * cell['threads'] == group['cores']
    assert summary['communication'] in (('allgather','allgatherv') if cell['communication']=='allgather' else ('halo',))
    if 'launcher' in cell:
        from investigate_collectives import check_mapping
        after=[json.loads(line.split('affinity_after_init ',1)[1]) for line in
               (case/'component_probe.log').read_text().splitlines() if 'affinity_after_init ' in line]
        check_mapping(after,group,cell)
        before=[json.loads(line) for line in (case/'mapping.jsonl').read_text().splitlines()]
        assert {r['rank']:(r['host'].split('.')[0].lower(),r['cpus']) for r in after}=={r['rank']:(r['host'].split('.')[0].lower(),r['cpus']) for r in before}
    if cell['implementation'] == 'hybrid':
        assert summary['threads_per_process'] == [cell['threads']] * cell['processes']
        assert summary['total_threads'] == group['cores']
    if cell['implementation'] == 'mpi_kokkos':
        assert summary['actual_threads'] == cell['threads'] and summary['backend'] == 'OpenMP'
    reference_ranks, indegree, outdegree = vectors
    ranks, errors = array('d'), array('d')
    with (folder / 'ranks.csv').open() as stream:
        for i, row in enumerate(csv.DictReader(stream)):
            assert int(row['node_id']) == i
            assert int(row['in_degree']) == indegree[i] and int(row['out_degree']) == outdegree[i]
            value = float(row['rank']); assert math.isfinite(value) and value >= 0
            ranks.append(value); errors.append(abs(value-reference_ranks[i]))
    assert len(ranks) == len(reference_ranks) == summary['nodes']
    l1 = math.fsum(errors)
    bound = reference_check['independent_residual_l1'] + (1+summary['alpha'])*l1
    assert l1 <= 1e-8 and bound <= summary['tolerance_l1'] + 1e-12
    assert abs(math.fsum(ranks)-1) <= 1e-10
    timing = list(csv.DictReader((folder / 'timings.csv').open()))
    assert len(timing) == 5 and [int(r['run']) for r in timing] == list(range(1,6))
    assert all(r['converged']=='true' and int(r['processes'])==cell['processes'] and int(r['iterations'])==summary['iterations'] for r in timing)
    assert all(0 <= float(r['residual_l1']) <= summary['tolerance_l1']+1e-12 and abs(float(r['rank_sum'])-1) <= 1e-10 for r in timing)
    if cell['implementation']=='hybrid':
        assert all(int(r['threads_min'])==int(r['threads_max'])==cell['threads'] and int(r['total_threads'])==group['cores'] for r in timing)
    times = [float(r['solve_s']) for r in timing]
    assert all(math.isfinite(x) and x>0 for x in times)
    for key, expected in [('solve_median_s',statistics.median(times)),('solve_min_s',min(times)),('solve_max_s',max(times)),
                          ('max_residual_l1',max(float(r['residual_l1']) for r in timing)),
                          ('max_rank_sum_error',max(abs(float(r['rank_sum'])-1) for r in timing))]:
        assert math.isclose(summary[key],expected,rel_tol=1e-12,abs_tol=1e-15),key
    history = list(csv.DictReader((folder / 'history.csv').open()))
    assert summary['converged'] and len(history)==summary['iterations']
    assert [int(r['iteration']) for r in history] == list(range(1,len(history)+1))
    assert all(math.isfinite(float(r['delta_l1'])) and float(r['delta_l1'])>=0 for r in history)
    assert float(history[-1]['delta_l1'])<=summary['tolerance_l1']
    if not summary['fixed_iterations']:
        assert all(float(r['delta_l1'])>summary['tolerance_l1'] for r in history[:-1])
    proof = {'passed':True,'method':'Independent Serial raw-edge residual plus full-vector L1 residual certificate',
             'residual_bound_formula':'residual(x) <= residual(s) + (1+alpha)*L1(x-s)',
             'serial_l1_error':l1,'independent_residual_l1_upper_bound':bound,
             'reference':reference_check,'performance_job':(case/'measurement_complete.txt').read_text().strip(),
             'validation_job':os.environ['PBS_JOBID'],'settings_and_five_timings_checked':True}
    if 'launcher' in cell:
        proof['post_mpi_init_cpu_affinity_verified']=True
    (case/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
    (case/'validation_complete.txt').write_text(os.environ['PBS_JOBID']+'\n')
    print('PASS',cell['id'],'L1=',l1,'residual bound=',bound,flush=True)


def validate_group(group):
    root = Path(group['output'])
    cache = root.parent.parent / 'reference_certificates'; cache.mkdir(exist_ok=True)
    for graph in sorted(group['datasets'], key=lambda graph: (graph!='strong_uniform',graph)):
        cells = [c for c in group['cells'] if c['graph']==graph and not (root/c['id']/'validation_complete.txt').exists()]
        if not cells:
            continue
        reference, proof = certify_reference(group, graph, cache)
        vectors = load_reference(reference)
        for cell in cells:
            assert (root/cell['id']/'measurement_complete.txt').exists()
            certify_case(group,cell,reference,proof,vectors)
        del vectors
    if not group.get('partial_validation', False):
        (root/'validation_complete.txt').write_text(os.environ['PBS_JOBID']+'\n')
