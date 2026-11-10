"""One explicit retry of ten unmeasured cells on previously validated CPU hosts."""
import csv
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
from zoneinfo import ZoneInfo

os.chdir('/scratch/hongxinran/DSA5208_PROJECT_3_assist_20261111')
run_id = '20261111_hongxinran_assist'
project = 'personal-hongxinran'
source_job = '1537799.stdct-mgmt-02'
hosts = ['cn-051', 'cn-053']
root = Path('results/updated_vanda_scaling') / run_id
receipt = root / 'controlled_host_retry_1537799.json'
assert not receipt.exists(), 'Inspect the existing retry instead of submitting twice'


def call(parts, env=None):
    return subprocess.check_output(parts, text=True, env=env, timeout=35).strip()


with (root / 'core_group_submit.lock').open('w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    registry = root / 'core_group_jobs.tsv'
    with registry.open() as source:
        reader = csv.DictReader(source, delimiter='\t')
        fields = reader.fieldnames
        rows = list(reader)
    row = next(r for r in rows if r['performance_job'] == source_job)
    previous_row = dict(row)
    failed = json.loads(call(['qstat', '-x', '-f', '-F', 'json', source_job]))['Jobs'][source_job]
    assert failed['job_state'] == 'F' and int(failed['Exit_status']) == -29
    group = json.loads(Path(row['plan']).read_text())
    assert group['nodes'] == 2 and group['cores'] == 64
    assert len(group['cells']) == 10
    assert not any((root / Path(c['canonical_summary']).parent / 'complete.txt').exists()
                   for c in group['cells'])
    raw = Path('/scratch/hongxinran/dsa5208_scaling') / run_id / 'results/cpu_core_groups' / group['graph'] / 'nodes2_cores32'
    assert not list(raw.rglob('performance_job.txt')), 'Saved cells require independent reuse review'
    available = json.loads((root / 'available_validated_hosts_20261111.json').read_text())
    assert all(h in available for h in hosts)
    balance_text = call(['hpc', 'project'])
    balance = float(next(line for line in balance_text.splitlines()
                         if line.strip().startswith(project + ' ')).split('|')[2])
    legacy = set(json.loads((root / 'legacy_held_jobs.json').read_text())['legacy_user_held_jobs'])
    ids = call(['qselect', '-u', 'hongxinran']).split()
    pending = 0.0
    for start in range(0, len(ids), 20):
        live = json.loads(call(['qstat', '-f', '-F', 'json', *ids[start:start + 20]]))['Jobs']
        for job_id, job in live.items():
            if job_id in legacy and job['job_state'] == 'H' and 'u' in job.get('Hold_Types', ''):
                continue
            if job.get('project') == project and job['queue'] == 'batch_cpu' and job['job_state'] in ('Q', 'H'):
                h, m, s = map(int, job['Resource_List']['walltime'].split(':'))
                pending += int(job['Resource_List']['ncpus']) * (h + m / 60 + s / 3600)
    reservation = 32.0
    assert balance - pending - reservation >= 64
    evidence = root / 'failed_attempts/source_1537799'
    evidence.mkdir(parents=True, exist_ok=True)
    for name in ['environment.json', 'cpu_hosts.jsonl', 'group_plan.json', 'dataset.tsv']:
        if (raw / name).is_file():
            shutil.copy2(raw / name, evidence / name)
    group.update(requested_hosts=hosts, retry_of=source_job,
                 retry_reason='No solver cell measured; MPI allocation probe stalled on CN-148/CN-151. Use already validated hosts.')
    plan = root / 'core_group_plans/grid_hub_n400000_d16_n2_c32_retry_1537799.json'
    plan.write_text(json.dumps(group, indent=2) + '\n')
    env = os.environ.copy()
    env.update(RUN_ID=run_id, DATA_ROOT='/scratch/hongxinran/dsa5208_scaling/' + run_id,
               CORE_GROUP_PLAN=str(plan.resolve()), OMPI_MCA_btl='self,vader,tcp',
               OMPI_MCA_pml='ob1', UCX_NET_DEVICES='', PAGERANK_HYBRID_MAX_TOTAL_THREADS='512')
    resources = '+'.join(f'1:ncpus=32:mpiprocs=32:ompthreads=1:mem=32gb:host={h}' for h in hosts)
    perf = call(['qsub', '-h', '-P', project, '-q', 'auto', '-l', 'select=' + resources,
                 '-l', 'walltime=' + group['walltime'], '-W', 'depend=afterok:1537725.stdct-mgmt-02',
                 'scripts/vanda_core_group_job.pbs'], env)
    record = {'observed_at': datetime.now(ZoneInfo('Asia/Singapore')).isoformat(),
              'source_job': source_job, 'previous_registry_row': previous_row,
              'previous_exit_status': failed['Exit_status'], 'hosts': hosts,
              'balance_before': balance, 'prior_pending_reservations': pending,
              'new_reservation_cpu_hours': reservation, 'performance_job': perf,
              'validation_job': '', 'status': 'performance_user_held'}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    val = call(['qsub', '-q', 'auto_free', '-W', 'depend=afterok:' + perf,
                'scripts/vanda_finalize_core_group_job.pbs'], env)
    record.update(validation_job=val)
    allocated = json.loads(call(['qstat', '-f', '-F', 'json', perf]))['Jobs'][perf]['Resource_List']
    assert int(allocated['ncpus']) == 64 and int(allocated['nodect']) == 2
    assert all(h in allocated['select'] for h in hosts)
    row.update(performance_job=perf, validation_job=val, plan=str(plan))
    temporary = root / 'core_group_jobs.retry.tmp'
    with temporary.open('w', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(registry)
    record.update(status='registered_with_free_validation')
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    call(['qrls', '-h', 'u', perf])
    record.update(status='released')
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
