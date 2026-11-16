"""Recompute anomaly evidence from saved timings without executing benchmarks."""
import csv
import json
from pathlib import Path
import statistics as stats

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/updated_vanda_scaling/performance_investigation_20261116'


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def evidence(record):
    path=ROOT/record['source_summary']
    summary=json.loads(path.read_text());timings=rows(path.with_name('timings.csv'))
    values=[float(t['solve_s']) for t in timings]
    assert len(values)==5 and stats.median(values)==summary['solve_median_s']
    assert summary['converged'] and summary['max_residual_l1']<=1e-8
    assert summary['max_rank_sum_error']<=1e-10
    item={k:record[k] for k in ['graph','method','host_nodes','processes','threads','source_summary'] if k in record}
    item.update(iterations=summary['iterations'],solve_repeats_s=values,median_s=stats.median(values),
                min_s=min(values),max_s=max(values))
    if 'communication_s' in timings[0]:
        item['median_max_rank_communication_s']=stats.median(float(t['communication_s']) for t in timings)
        item['median_communication_to_solve_ratio']=stats.median(float(t['communication_s'])/float(t['solve_s']) for t in timings)
    if 'max_local_edges' in summary:
        item['max_edges_divided_by_mean']=summary['max_local_edges']/(summary['edges']/summary['processes'])
        item['min_local_edges']=summary['min_local_edges'];item['max_local_edges']=summary['max_local_edges']
    item['logical_payload_bytes_per_iteration']=summary.get('communication_bytes_per_iteration',0)
    return item


def main():
    fixed=rows(ROOT/'reports/non512/data/fixed_results_19530.csv')
    weak=rows(ROOT/'reports/non512/data/weak_results_372.csv')
    google=[evidence(r) for r in fixed if r['graph']=='google' and r['context']=='cpu_node'
            and r['method'] in ['OpenMP','Kokkos OpenMP'] and r['threads'] in ['16','32']]
    uniform=[evidence(r) for r in fixed if r['graph']=='strong_uniform' and r['context']=='cpu_node'
             and r['method']=='MPI' and r['communication']=='Halo' and r['processes'] in ['64','128','256']
             and int(r['host_nodes'])*32==int(r['processes'])]
    weak256=[]
    for r in weak:
        if r['suite']=='rank_cpu_regular' and r['method']=='MPI' and r['processes']=='256':
            item=evidence(r);item.update(family=r['family'],communication=r['communication'],
                                        weak_efficiency_per_iteration=float(r['weak_efficiency_per_iteration']))
            weak256.append(item)
    OUT.mkdir(exist_ok=True,parents=True)
    result={'google_threads':google,'uniform_halo_strong':uniform,'mpi_weak256':weak256,
            'communication_caveat':'Per-run maxima can occur on different ranks; MPI timing includes wait and local packing. Ratios are not pure network utilization or additive critical-path components.'}
    (OUT/'historical_evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Checked 4 Google thread points, 3 Uniform strong points and 6 MPI weak endpoints.')


if __name__=='__main__':main()
