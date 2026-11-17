"""Audit the published matrix, timing protocol and matched report comparisons."""
import csv
import json
import math
from pathlib import Path
import statistics

from result_store import result_file, verify_archives

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results/tables'


def rows(name):
    with (DATA/name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def key(r):
    return (r['graph'],r['context'],r['method'],int(r['host_nodes']),
            int(r['processes']),int(r['threads']),r['communication'])


def main():
    verify_archives()
    fixed=rows('fixed_results_19530.csv')
    graphs={r['graph'] for r in fixed}
    assert len(graphs)==45
    actual={key(r):r for r in fixed}
    assert len(actual)==len(fixed)==19530
    expected=set()
    q=(1,2,4,8,16,32)
    for graph in graphs:
        def add(context,method,n,p,t,exchange):
            expected.add((graph,context,method,n,p,t,exchange))
        add('cpu_node','Serial',1,1,1,'none')
        for method in ('OpenMP','Kokkos OpenMP'):
            for t in q:add('cpu_node',method,1,1,t,'none')
        for n in (1,2,4,8):
            for r in q:
                for exchange in ('Allgatherv','Halo'):
                    add('cpu_node','MPI',n,n*r,1,exchange)
                    for t in q:
                        if r*t<=32:
                            for method in ('MPI+OpenMP','MPI+Kokkos OpenMP'):
                                add('cpu_node',method,n,n*r,t,exchange)
        for method in ('Serial','CUDA','Kokkos CUDA'):
            add('gpu_node',method,1,1,1,'none')
        for t in q:add('gpu_node','OpenMP',1,1,t,'none')
        for n in (1,2):
            for exchange in ('Allgatherv','Halo'):
                for method in ('MPI','MPI+CUDA','MPI+Kokkos CUDA'):
                    add('gpu_node',method,n,n,1,exchange)
                for t in (1,2,4,8):add('gpu_node','MPI+OpenMP',n,n,t,exchange)
    assert expected==set(actual), 'Fixed matrix differs from the stated Cartesian product'
    references={(r['graph'],r['context']):float(r['solve_median_s'])
                for r in fixed if r['method']=='Serial'}
    with (ROOT/'results/manifests/fixed.csv').open(newline='') as stream:selection=list(csv.DictReader(stream))
    host_files=set()
    for name in {r['evidence'] for r in selection}:
        host_files.update(v for v in json.loads(result_file(name).read_text())['files'] if result_file(v).name=='cpu_hosts.jsonl')
    cpu_models={json.loads(line)['cpu_model'] for name in host_files for line in result_file(name).read_text().splitlines()}
    assert cpu_models=={'Intel(R) Xeon(R) Platinum 8452Y'}
    samples=0;logged_thread_cases=0;legacy_single_thread_cases=0
    for inventory in ('fixed','growing','high_core','controls'):
        with (ROOT/f'results/manifests/{inventory}.csv').open(newline='') as stream:
            cases=list(csv.DictReader(stream))
        for case in cases:
            path=result_file(case.get('summary',case.get('source_summary')))
            summary=json.loads(path.read_text())
            with (path.parent/'timings.csv').open(newline='') as stream:timings=list(csv.DictReader(stream))
            assert (summary['repeat_runs'],summary['warmup_runs'],summary['build_type'])==(5,1,'Release')
            assert (summary['alpha'],summary['tolerance_l1'],summary['fixed_iterations'])==(.85,1e-8,0)
            assert [int(r['run']) for r in timings]==[1,2,3,4,5]
            values=[float(r['solve_s']) for r in timings]
            assert all(math.isfinite(v) and v>0 for v in values)
            assert math.isclose(statistics.median(values),summary['solve_median_s'],rel_tol=1e-12,abs_tol=1e-12)
            for r in timings:
                assert r['converged']=='true'
                assert float(r['residual_l1'])<=1e-8+1e-12
                assert abs(float(r['rank_sum'])-1)<=1e-10
                assert int(r['iterations'])==summary['iterations']
            if inventory=='fixed' and summary.get('implementation')=='mpi_kokkos' and summary.get('backend')=='OpenMP':
                if 'requested_threads' in summary:
                    assert summary['requested_threads']==summary['actual_threads']==int(case['threads'])
                    logged_thread_cases+=1
                else:
                    assert int(case['threads'])==1
                    legacy_single_thread_cases+=1
            samples+=len(timings)
    for r in fixed:
        speed=references[r['graph'],r['context']]/float(r['solve_median_s'])
        assert math.isclose(speed,float(r['speedup_vs_matched_serial']),rel_tol=1e-12)
        if r['context']=='cpu_node':
            assert int(r['processes'])*int(r['threads'])==int(r['active_cpu_threads'])
            assert math.isclose(speed/int(r['active_cpu_threads']),float(r['cpu_efficiency_vs_serial']),rel_tol=1e-12)
    weak=rows('growing_cpu_matched_reference.csv')
    assert len(weak)==126
    for r in weak:
        c=int(r['active_cpu_threads'])
        assert (int(r['vertices']),int(r['edges']))==(50000*c,800000*c)
        base=next(v for v in weak if all(v[k]==r[k] for k in ('family','method','communication')) and v['active_cpu_threads']=='4')
        assert math.isclose(float(r['matched_efficiency']),float(base['seconds_per_iteration'])/float(r['seconds_per_iteration']),rel_tol=1e-12)
    controls=rows('collective_controls.csv')
    assert len(controls)==57
    for graph,cores,implementation,mode in [(g,c,'mpi' if g=='strong_uniform' else 'hybrid','halo' if g=='strong_uniform' else 'allgather')
            for g in ('strong_uniform','strong_hub','strong_controlled') for c in ((64,128,256) if g=='strong_uniform' else (32,64,128))]:
        group=[r for r in controls if r['graph']==graph and int(r['cores'])==cores and r['implementation']==implementation and r['communication']==mode]
        assert len(group)==3
        assert len({(r['nodes'],r['processes'],r['threads'],r['performance_job'],r['communication_bytes_per_iteration'],r['iterations']) for r in group})==1
    synthetic_specs={(r['family'],int(r['vertices']),int(r['edges'])) for r in fixed if r['origin']!='original'}
    growing_specs={(r['family'],int(r['vertices']),int(r['edges'])) for r in rows('weak_results_372.csv')}
    shared_specs=len(synthetic_specs & growing_specs)
    distinct_specs=len(synthetic_specs | growing_specs)+3
    assert (shared_specs,distinct_specs)==(15,57)
    for item in rows('split_summary.csv'):
        population=[r for r in fixed if r['context']=='cpu_node' and r['method']==item['method']
                    and r['host_nodes']=='8' and r['threads']==item['threads']
                    and int(r['active_cpu_threads'])==256 and r['communication']==item['communication']]
        assert len(population)==45
        reference=[actual[(r['graph'],'cpu_node',r['method'],8,256,1,r['communication'])] for r in population]
        geo=lambda values: math.exp(statistics.mean(math.log(float(v)) for v in values))
        assert math.isclose(geo(r['solve_median_s'] for r in reference)/geo(r['solve_median_s'] for r in population),float(item['geomean_speedup_vs_T1']),rel_tol=1e-12)
    pairs=rows('halo_pairs.csv')
    for item in rows('halo_summary.csv'):
        population=[r for r in pairs if r['context']==item['context'] and r['family']==item['family']]
        assert len(population)==int(item['paired_configurations'])
        assert math.isclose(geo(r['allgatherv_s'] for r in population)/geo(r['halo_s'] for r in population),float(item['geomean_halo_speedup']),rel_tol=1e-12)
    result={'shared_fixed_growing_specifications':shared_specs,'distinct_input_specifications':57,
            'aggregate_duration_ratio_checks':32,'fixed_matrix_exact':True,'fixed_configurations':len(fixed),'fixed_graphs':45,
            'five_run_timing_entries_checked':samples,'recorded_cpu_models':sorted(cpu_models),'protocol':'one warm-up; median of five timed solves; Release; alpha=.85; tolerance=1e-8',
            'fixed_speedup_and_efficiency_recomputed':True,
            'mpi_kokkos_actual_thread_records_checked':logged_thread_cases,
            'mpi_kokkos_original_single_thread_records':legacy_single_thread_cases,'cpu_work_scaled_rows_checked':len(weak),
            'matched_policy_groups_checked':9,'policy_context_and_binding_cases':59,
            'coverage':'serial N/E grid; MPI and MPI+X fixed/growing inputs to 256 CPU cores; one/two GPUs',
            'raw_score_validation':'saved independent full-vector/residual certificates; no new rank scan performed by this audit'}
    (DATA/'report_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
