"""Recompute policy and launch-binding tables from validated measurement archives."""
import csv
import json
from pathlib import Path
import statistics

from result_store import result_file, verify_archives

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/tables'
FIELDS=['graph','implementation','cores','nodes','processes','threads','communication','policy',
        'solve_median_s','solve_min_s','solve_max_s','communication_median_s',
        'communication_bytes_per_iteration','iterations','max_residual_l1','account',
        'performance_job','validation_job','source_summary','source_settings','validation_marker']


def main():
    verify_archives()
    rows=[];bindings=[]
    manifest=list(csv.DictReader((ROOT/'results/manifests/controls.csv').open()))
    assert len(manifest)==59
    for case in manifest:
        source=result_file(case['source_summary'])
        summary=json.loads(source.read_text())
        proof=json.loads(result_file(case['validation_marker']).read_text())
        settings=json.loads(result_file(case['source_settings']).read_text())
        assert proof['passed'] and proof['serial_l1_error']<=1e-8
        assert proof['independent_residual_l1_upper_bound']<=1e-8+1e-12
        assert summary['repeat_runs']==5 and summary['warmup_runs']==1 and summary['converged']
        assert summary['processes']==int(case['processes'])
        assert int(case['processes'])*int(case['threads'])==int(case['cores'])
        assert settings['OMPI_MCA_coll_tuned_use_dynamic_rules']==('0' if case['policy']=='default' else '1')
        expected={'default':('0','0'),'a2av_linear':('1','0'),'a2av_pairwise':('2','0'),
                  'agv_bruck':('0','2'),'agv_ring':('0','3')}[case['policy']]
        assert (settings['OMPI_MCA_coll_tuned_alltoallv_algorithm'],settings['OMPI_MCA_coll_tuned_allgatherv_algorithm'])==expected
        with (source.parent/'timings.csv').open(newline='') as stream:
            times=list(csv.DictReader(stream))
        assert len(times)==5
        values=[float(x['solve_s']) for x in times]
        assert abs(statistics.median(values)-summary['solve_median_s'])<=1e-12
        row={key:case[key] for key in FIELDS if key in case}
        row.update(solve_median_s=statistics.median(values),solve_min_s=min(values),solve_max_s=max(values),
                   communication_median_s=statistics.median(float(x['communication_s']) for x in times),
                   communication_bytes_per_iteration=summary['communication_bytes_per_iteration'],
                   iterations=summary['iterations'],max_residual_l1=summary['max_residual_l1'])
        if case['study']=='binding':
            assert proof['post_mpi_init_cpu_affinity_verified']
            row['launcher']=case['launcher'];bindings.append(row)
        else:rows.append(row)
    assert len(rows)==57 and len(bindings)==2
    for filename,values,fields in [('collective_controls.csv',rows,FIELDS),('launcher_controls.csv',bindings,FIELDS+['launcher'])]:
        with (OUT/filename).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
            writer.writeheader();writer.writerows(values)
    print('Validated controls: 57 collective/context cases and 2 binding cases')


if __name__=='__main__':main()
