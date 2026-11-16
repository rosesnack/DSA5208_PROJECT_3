"""Audit the validated non-512 Vanda snapshot and build report tables.

Only saved measurements are read. No benchmark, submission, or rank validation
is rerun. The independent validation markers remain the authority for ranks.
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import re
import statistics as stats

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'results/updated_vanda_scaling/git_sync_20261111'
OUT = ROOT / 'reports/non512/data'
LABELS = {
    'serial': 'Serial', 'openmp': 'OpenMP', 'kokkos_openmp': 'Kokkos OpenMP',
    'mpi_cpu': 'MPI', 'mpi_openmp': 'MPI+OpenMP',
    'mpi_kokkos_cpu_t1': 'MPI+Kokkos OpenMP',
    'mpi_kokkos_cpu_threads': 'MPI+Kokkos OpenMP',
    'cuda': 'CUDA', 'kokkos_cuda': 'Kokkos CUDA',
    'mpi_cuda': 'MPI+CUDA', 'mpi_kokkos_cuda': 'MPI+Kokkos CUDA',
    'gpu_node_serial': 'Serial', 'gpu_node_openmp': 'OpenMP',
    'gpu_node_mpi_cpu': 'MPI', 'gpu_node_mpi_openmp': 'MPI+OpenMP',
}
PARALLEL = ('MPI', 'MPI+OpenMP', 'MPI+Kokkos OpenMP')


def read_csv(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def geomean(values):
    return math.exp(stats.mean(math.log(v) for v in values))


def family(graph):
    return next((f for f in ('uniform', 'hub', 'controlled') if f in graph), 'google')


def origin(graph):
    if graph in ('google', 'uniform', 'hub'):
        return 'original'
    if graph.startswith('grid_'):
        return 'grid'
    return 'large' if graph.startswith('strong_') else 'canonical'


def dimensions(stage, summary, path):
    p = summary.get('processes', 1)
    t = summary.get('requested_threads', summary.get('threads', 1))
    if stage == 'kokkos_openmp':
        t = int(re.search(r'kokkos_threads_(\d+)', str(path))[1])
    if stage.startswith('mpi_kokkos_cpu'):
        t = summary.get('actual_threads', 1)
        assert 'actual_threads' in summary or stage == 'mpi_kokkos_cpu_t1'
    gpu_environment = 'a40' in summary['environment']
    if 'processes' in summary:
        n = p if gpu_environment else int(re.search(r'/nodes(\d+)', str(path))[1])
    else:
        n = 1
    return n, p, t


def load_fixed():
    inventory = read_csv(INVENTORY / 'experiment_manifest_20700.csv')
    selected = [r for r in inventory if '512' not in r['stage']]
    assert len(selected) == 19530
    assert len({r['canonical_summary'] for r in selected}) == len(selected)
    records, variants = [], Counter()
    max_median_error = 0
    for row in selected:
        path = ROOT / row['summary']
        assert row['status'] == 'validated' and (ROOT / row['marker']).is_file()
        s = json.loads(path.read_text())
        timings = read_csv(path.with_name('timings.csv'))
        assert (s['build_type'], s['repeat_runs'], s['warmup_runs']) == ('Release', 5, 1)
        assert (s['alpha'], s['tolerance_l1'], s['fixed_iterations']) == (.85, 1e-8, 0)
        assert s['converged'] and s['max_residual_l1'] <= 1e-8 and s['max_rank_sum_error'] <= 1e-10
        assert len(timings) == 5 and [int(x['run']) for x in timings] == list(range(1, 6))
        assert all(x['converged'] == 'true' for x in timings)
        values = [float(x['solve_s']) for x in timings]
        assert all(math.isfinite(x) and x > 0 for x in values)
        error = abs(stats.median(values) - s['solve_median_s'])
        assert math.isclose(stats.median(values), s['solve_median_s'], rel_tol=1e-12, abs_tol=1e-12)
        max_median_error = max(max_median_error, error)
        n, p, t = dimensions(row['stage'], s, row['canonical_summary'])
        assert p % n == 0
        if s['implementation'] == 'hybrid':
            assert s['threads_per_process'] == [t] * p and s['total_threads'] == p * t
        if s['implementation'] == 'openmp':
            assert s['threads'] == t
        context = 'gpu_node' if 'a40' in s['environment'] else 'cpu_node'
        if context == 'cpu_node':
            assert p * t <= 256 and p * t <= n * 32
        mode = 'none' if 'processes' not in s else ('Halo' if s['communication'] == 'halo' else 'Allgatherv')
        graph = row['graph']
        record = dict(graph=graph, family=family(graph), origin=origin(graph),
                      stage=row['stage'], context=context, method=LABELS[row['stage']],
                      vertices=s['nodes'], edges=s['edges'], host_nodes=n, processes=p,
                      threads=t, active_cpu_threads=p*t, communication=mode,
                      iterations=s['iterations'], solve_median_s=s['solve_median_s'],
                      solve_min_s=min(values), solve_max_s=max(values),
                      seconds_per_iteration=stats.median(float(x['solve_s']) / int(x['iterations']) for x in timings),
                      repeat_relative_range=(max(values)-min(values))/stats.median(values),
                      communication_bytes_per_iteration=s.get('communication_bytes_per_iteration', 0),
                      communication_setup_s=s.get('communication_setup_s', 0),
                      communication_setup_bytes=s.get('communication_setup_bytes', 0),
                      communication_fraction=stats.median(float(x.get('communication_s', 0))/float(x['solve_s']) for x in timings),
                      communication_median_s=stats.median(float(x.get('communication_s', 0)) for x in timings),
                      compute_median_s=stats.median(float(x.get('backend_compute_s', 0)) for x in timings),
                      transfer_median_s=stats.median(float(x.get('transfer_s', 0)) for x in timings),
                      edge_imbalance=(s['max_local_edges']/s['min_local_edges'] if s.get('min_local_edges', 0) else ''),
                      max_residual_l1=s['max_residual_l1'], max_rank_sum_error=s['max_rank_sum_error'],
                      compact_setup=s.get('compact_setup', False),
                      source_summary=row['summary'], validation_marker=row['marker'],
                      performance_job=row['performance_job'], validation_job=row['validation_job'])
        records.append(record)
        variants[(context, s['build_type'], s['repeat_runs'], s['warmup_runs'])] += 1
    return records, max_median_error


def load_weak():
    result = []
    for row in read_csv(INVENTORY / 'weak_experiment_manifest.csv'):
        if row['status'] != 'validated' or row['suite'] == 'rank_cpu_512':
            continue
        path = Path(row['source_root']) / row['canonical_summary']
        s = json.loads((ROOT / path).read_text())
        p = s.get('processes', 1)
        t = s.get('requested_threads', s.get('actual_threads', s.get('threads', 1)))
        if p*t > 256:
            continue
        timings = read_csv((ROOT / path).with_name('timings.csv'))
        assert len(timings) == 5 and s['converged']
        assert (s['repeat_runs'], s['warmup_runs'], s['build_type']) == (5, 1, 'Release')
        assert s['max_residual_l1'] <= 1e-8 and s['max_rank_sum_error'] <= 1e-10
        mode = ('none' if 'processes' not in s else
                'Halo' if s['communication'] == 'halo' else 'Allgatherv')
        method = {'mpi': 'MPI', 'hybrid': 'MPI+OpenMP', 'mpi_cuda': 'MPI+CUDA',
                  'mpi_kokkos': 'MPI+Kokkos ' + s.get('backend', 'OpenMP'),
                  'serial': 'Serial', 'openmp': 'OpenMP', 'cuda': 'CUDA',
                  'kokkos': 'Kokkos ' + s.get('backend', '')}[s['implementation']]
        result.append(dict(suite=row['suite'], graph=s['dataset'], family=row['family'], method=method,
                           communication=mode, processes=p, threads=t, active_cpu_threads=p*t,
                           vertices=s['nodes'], edges=s['edges'], iterations=s['iterations'],
                           solve_median_s=s['solve_median_s'], resource_scaled='processes' in s,
                           seconds_per_iteration=stats.median(float(x['solve_s'])/int(x['iterations']) for x in timings),
                           source_summary=str(path), validation_marker=row['marker']))
    assert len(result) == 372
    for r in result:
        if not r['resource_scaled']:
            r['weak_efficiency_per_iteration'] = ''
            r['weak_efficiency_total_solve'] = ''
            continue
        peers = [x for x in result if (x['suite'], x['family'], x['method'], x['threads'], x['communication']) ==
                 (r['suite'], r['family'], r['method'], r['threads'], r['communication'])]
        baseline = min(peers, key=lambda x:x['processes'])
        r['weak_efficiency_per_iteration'] = baseline['seconds_per_iteration']/r['seconds_per_iteration']
        r['weak_efficiency_total_solve'] = baseline['solve_median_s']/r['solve_median_s']
    return result


def google_insights():
    path = Path('/tmp/dsa5208_google_refreshed_ranks.csv')
    if not path.is_file():
        return None
    ranks, indegrees, pairs = [], [], []
    with path.open() as stream:
        for row in csv.DictReader(stream):
            score, degree = float(row['rank']), int(row['in_degree'])
            ranks.append(score); indegrees.append(degree)
            pairs.append((score, int(row['node_id']), degree, int(row['out_degree'])))
    assert len(ranks) == 875713 and math.isclose(sum(ranks), 1, abs_tol=1e-10)
    ordered = sorted(pairs, reverse=True)
    count = len(ranks); mean_r = sum(ranks)/count; mean_d = sum(indegrees)/count
    covariance = sum((r-mean_r)*(d-mean_d) for r,d in zip(ranks,indegrees))
    denominator = math.sqrt(sum((r-mean_r)**2 for r in ranks)*sum((d-mean_d)**2 for d in indegrees))
    return dict(vertices=count, rank_sum=math.fsum(ranks),
                dangling_vertices=sum(x[3]==0 for x in pairs),
                top_1_percent_rank_mass=sum(x[0] for x in ordered[:math.ceil(count*.01)]),
                pagerank_indegree_pearson=covariance/denominator,
                source='Fresh validated Serial ranks from Vanda RUN 20261106T185006Z; local analysis only',
                vector_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                top10=[dict(node_id=x[1],rank=x[0],in_degree=x[2],out_degree=x[3]) for x in ordered[:10]])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records, median_error = load_fixed()
    baselines = {(x['context'], x['graph']):x['solve_median_s'] for x in records if x['method']=='Serial'}
    for r in records:
        r['speedup_vs_matched_serial'] = baselines[r['context'],r['graph']]/r['solve_median_s']
        r['cpu_efficiency_vs_serial'] = (r['speedup_vs_matched_serial']/r['active_cpu_threads']
                                        if r['context']=='cpu_node' else '')
    write_csv('fixed_results_19530.csv', records)
    weak = load_weak(); write_csv('weak_results_372.csv', weak)
    graph_rows = []
    for graph in sorted({r['graph'] for r in records}, key=lambda g:(origin(g)!='original',origin(g),g)):
        row = next(r for r in records if r['graph']==graph and r['method']=='Serial' and r['context']=='cpu_node')
        graph_rows.append({k:row[k] for k in ('graph','origin','family','vertices','edges','iterations','solve_median_s')})
    write_csv('graphs_45.csv', graph_rows)
    matrix=[]
    for g in graph_rows:
        r=dict(g)
        methods = [('cpu_node',m) for m in ('Serial','OpenMP','Kokkos OpenMP',*PARALLEL)]
        methods += [('gpu_node',m) for m in ('CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA')]
        for context, method in methods:
            selected = min((x for x in records if x['graph']==g['graph'] and x['context']==context and x['method']==method),key=lambda x:x['solve_median_s'])
            r[method+'_best_s']=selected['solve_median_s']
            r[method+'_configuration']=f"n{selected['host_nodes']}:p{selected['processes']}:T{selected['threads']}:{selected['communication']}"
        matrix.append(r)
    write_csv('runtime_matrix_45.csv', matrix)
    strong=[r for r in records if r['context']=='cpu_node' and r['method'] in PARALLEL
            and r['host_nodes']==max(1,r['active_cpu_threads']//32)]
    write_csv('cpu_strong_mainline.csv',strong)
    fixed256=[r for r in strong if r['active_cpu_threads']==256]
    write_csv('cpu_256_splits.csv',fixed256)
    lookup={(r['context'],r['graph'],r['method'],r['host_nodes'],r['processes'],r['threads'],r['communication']):r for r in records}
    pairs=[]
    for a in records:
        if a['communication']!='Allgatherv' or a['processes']==1:continue
        key=(a['context'],a['graph'],a['method'],a['host_nodes'],a['processes'],a['threads'],'Halo')
        h=lookup[key]
        pairs.append(dict(graph=a['graph'],family=a['family'],origin=a['origin'],context=a['context'],method=a['method'],
                          host_nodes=a['host_nodes'],processes=a['processes'],threads=a['threads'],cores=a['active_cpu_threads'],
                          allgatherv_s=a['solve_median_s'],halo_s=h['solve_median_s'],
                          halo_speedup=a['solve_median_s']/h['solve_median_s'],
                          payload_reduction=1-h['communication_bytes_per_iteration']/a['communication_bytes_per_iteration'],
                          allgatherv_bytes=a['communication_bytes_per_iteration'],halo_bytes=h['communication_bytes_per_iteration']))
    write_csv('halo_pairs.csv',pairs)
    halo_summary=[]
    for context in ('cpu_node','gpu_node'):
        for f in ('google','uniform','hub','controlled'):
            subset=[r for r in pairs if r['context']==context and r['family']==f]
            halo_summary.append(dict(context=context,family=f,paired_configurations=len(subset),
                                     geomean_halo_speedup=geomean(x['halo_speedup'] for x in subset),
                                     median_payload_reduction=stats.median(x['payload_reduction'] for x in subset),
                                     halo_faster_fraction=stats.mean(x['halo_speedup']>1 for x in subset)))
    write_csv('halo_summary.csv',halo_summary)
    splits=[]
    for method in PARALLEL[1:]:
        for mode in ('Allgatherv','Halo'):
            for t in (1,2,4,8,16,32):
                subset=[r for r in fixed256 if r['method']==method and r['communication']==mode and r['threads']==t]
                ratios=[lookup[('cpu_node',r['graph'],method,8,256,1,mode)]['solve_median_s']/r['solve_median_s'] for r in subset]
                splits.append(dict(method=method,communication=mode,threads=t,processes=256//t,graphs=len(subset),
                                   geomean_speedup_vs_T1=geomean(ratios)))
    write_csv('split_summary.csv',splits)
    iteration_variation=Counter()
    for context,graph in baselines:
        iteration_variation[len({r['iterations'] for r in records if r['context']==context and r['graph']==graph})]+=1
    checks=dict(fixed_configurations=len(records),timed_runs=len(records)*5,weak_configurations=len(weak),
                weak_suite_counts=dict(Counter(r['suite'] for r in weak)),
                graph_count=len(graph_rows),all_512_excluded=True,
                non512_targets_complete=True,max_residual_l1=max(r['max_residual_l1'] for r in records),
                max_rank_sum_error=max(r['max_rank_sum_error'] for r in records),
                max_summary_median_difference_s=median_error,
                median_repeat_relative_range=stats.median(r['repeat_relative_range'] for r in records),
                p95_repeat_relative_range=stats.quantiles([r['repeat_relative_range'] for r in records],n=20)[18],
                iteration_distinct_counts_per_graph_context=dict(iteration_variation),
                compact_setup_configurations=sum(r['compact_setup'] for r in records),
                stage_counts=dict(Counter(r['stage'] for r in records)),
                source_manifest=str(INVENTORY.relative_to(ROOT)/'experiment_manifest_20700.csv'),
                source_manifest_sha256=hashlib.sha256((INVENTORY/'experiment_manifest_20700.csv').read_bytes()).hexdigest())
    (OUT/'audit.json').write_text(json.dumps(checks,indent=2)+'\n')
    insights=google_insights()
    if insights:
        (OUT/'google_insights.json').write_text(json.dumps(insights,indent=2)+'\n')
        write_csv('google_top10.csv',insights['top10'])
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    main()
