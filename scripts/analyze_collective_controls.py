"""Export only independently validated policy controls, without altering main measurements."""
import csv
import json
from pathlib import Path
import statistics

from investigate_collectives import folder_for

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/updated_vanda_scaling/collective_controls_20261117'
OUTPUT = ROOT / 'reports/non512/data/collective_controls.csv'
FIELDS = ['graph', 'implementation', 'cores', 'nodes', 'processes', 'threads',
          'communication', 'policy', 'solve_median_s', 'solve_min_s', 'solve_max_s',
          'communication_median_s', 'communication_bytes_per_iteration', 'iterations', 'max_residual_l1', 'account',
          'performance_job', 'validation_job', 'source_summary', 'source_settings']


def main():
    rows = []
    manifest = []
    launcher_rows=[]
    launcher_manifest=[]
    for account in ('xtt_ella', 'hongxinran'):
        receipt_file = SOURCE / ('submission_' + account + '.json')
        if not receipt_file.exists():
            continue
        for group_row in json.loads(receipt_file.read_text())['rows']:
            group = json.loads((SOURCE / (group_row['id'] + '.json')).read_text())
            is_launcher=group_row.get('study')=='launcher'
            for cell in group['cells']:
                case = SOURCE / 'raw' / account / group['id'] / cell['id']
                (launcher_manifest if is_launcher else manifest).append({**cell, 'cores': group['cores'], 'nodes': group['nodes'], 'account': account,
                                 'state': 'validated' if (case/'validation_complete.txt').exists() else
                                          'measured' if (case/'measurement_complete.txt').exists() else 'scheduled',
                                 'performance_job': group_row['performance_job'],
                                 'validation_job': (case/'validation_complete.txt').read_text().strip() if
                                     (case/'validation_complete.txt').exists() else group_row['validation_job']})
                if not (case / 'validation_complete.txt').exists():
                    continue
                proof = json.loads((case / 'validation.json').read_text())
                assert proof['passed'] and proof['independent_residual_l1_upper_bound'] <= 1e-8+1e-12
                summary_path = case / folder_for(cell) / 'summary.json'
                summary = json.loads(summary_path.read_text())
                timing = list(csv.DictReader((summary_path.parent / 'timings.csv').open()))
                assert len(timing) == summary['repeat_runs'] == 5 and summary['warmup_runs'] == 1
                assert summary['processes'] * cell['threads'] == group['cores']
                times = [float(r['solve_s']) for r in timing]
                assert abs(statistics.median(times) - summary['solve_median_s']) <= 1e-12
                row = {k: cell[k] for k in ('graph', 'implementation', 'processes', 'threads', 'communication', 'policy')}
                row.update(cores=group['cores'], nodes=group['nodes'],
                           solve_median_s=statistics.median(times), solve_min_s=min(times), solve_max_s=max(times),
                           communication_median_s=statistics.median(float(r['communication_s']) for r in timing),
                           communication_bytes_per_iteration=summary['communication_bytes_per_iteration'],
                           iterations=summary['iterations'], max_residual_l1=summary['max_residual_l1'],
                           account=account, performance_job=group_row['performance_job'],
                           validation_job=(case / 'validation_complete.txt').read_text().strip(),
                           source_summary=str(summary_path.relative_to(ROOT)),
                           source_settings=str((case / 'settings.json').relative_to(ROOT)))
                if is_launcher:
                    assert proof['post_mpi_init_cpu_affinity_verified']
                    row['launcher']=cell['launcher'];launcher_rows.append(row)
                else:rows.append(row)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    with (OUTPUT.parent/'launcher_controls.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS+['launcher']);writer.writeheader();writer.writerows(launcher_rows)
    if launcher_manifest:
        assert len(launcher_manifest)==2
        with (SOURCE/'case_manifest_launcher_2.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(launcher_manifest[0]));writer.writeheader();writer.writerows(launcher_manifest)
    if manifest:
        assert len(manifest)==57 and len({(r['cores'],r['id']) for r in manifest})==57
        with (SOURCE/'case_manifest_57.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
        accounting=[]
        for account in ('xtt_ella','hongxinran'):
            receipt=json.loads((SOURCE/('submission_'+account+'.json')).read_text())
            snapshot=json.loads((SOURCE/('live_'+account+'.json')).read_text())
            for group in receipt['rows']:
                job=snapshot['jobs'][group['performance_job']]
                elapsed=(job.get('resources_used') or {}).get('walltime','')
                hours=sum(int(x)/v for x,v in zip(elapsed.split(':'),[1,60,3600])) if elapsed else 0
                maximum=sum(int(x)/v for x,v in zip(group['walltime'].split(':'),[1,60,3600]))
                accounting.append(dict(observed_at=snapshot['time'],account=account,group=group['id'],
                    cores=group['cores'],cells=group['cells'],job=group['performance_job'],state=job['job_state'],
                    exit_status=job.get('Exit_status'),walltime_limit=group['walltime'],walltime_used=elapsed,
                    max_reserved_cpuh=group['cores']*maximum,observed_allocated_cpuh=group['cores']*hours))
        with (SOURCE/'runtime_accounting.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(accounting[0]));writer.writeheader();writer.writerows(accounting)
    print('Independently validated collective controls:', len(rows), '/ 57')
    print('Independently validated launcher controls:',len(launcher_rows),'/ 2')


if __name__ == '__main__':
    main()
