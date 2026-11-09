"""Poll PBS/project credits and submit only unregistered, unvalidated missing cells.

This lightweight controller runs outside performance allocations. Stop it with
the STOP_AUTO_SUBMIT file in the run directory. It never retries failed jobs.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import errno
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from zoneinfo import ZoneInfo


def command(parts, timeout=60):
    return subprocess.run(parts, text=True, capture_output=True, check=True, timeout=timeout).stdout


def unregistered_groups(plan, rows, root, jobs, max_total_cores=512):
    known = {c['canonical_summary'] for r in rows
             for c in json.loads(Path(r['plan']).read_text())['cells']}
    result = []
    for group in plan:
        if group.get('cores', 0) > max_total_cores:
            continue
        proof = group.get('required_job')
        if proof and not (jobs.get(proof, {}).get('job_state') == 'F' and jobs[proof].get('Exit_status') == 0):
            continue
        if group['prerequisite'] and not (root / group['prerequisite']).is_file():
            continue
        cells = [c for c in group['cells'] if c['canonical_summary'] not in known
                 and not (root / Path(c['canonical_summary']).parent / 'complete.txt').is_file()]
        if cells:
            result.append({**group, 'cells': cells})
    return result


def job_snapshot(ids, cached):
    jobs = dict(cached)
    query_ids = sorted(i for i in ids if jobs.get(i, {}).get('job_state') != 'F')
    for start in range(0, len(query_ids), 25):
        batch = query_ids[start:start + 25]
        response = subprocess.run(['qstat', '-x', '-f', '-F', 'json', *batch], text=True,
                                  capture_output=True, timeout=45)
        if not response.stdout.strip():
            raise RuntimeError('PBS job history query returned no JSON')
        reply = json.loads(response.stdout)
        data = reply.get('Jobs')
        if not isinstance(data, dict):
            raise RuntimeError('PBS response has no Jobs mapping; waiting for scheduler recovery')
        for job_id, record in data.items():
            jobs[job_id] = {k: record[k] for k in ('job_state', 'Exit_status', 'queue', 'comment', 'Hold_Types',
                                                'Resource_List', 'resources_used') if k in record}
        if response.returncode and not data:
            raise RuntimeError('PBS job history query failed')
    return jobs


def cycle(args, root, jobs):
    rows = list(csv.DictReader((root / 'core_group_jobs.tsv').open(), delimiter='\t'))
    plan = json.loads(args.plan.read_text())
    ids = {r[c] for r in rows for c in ('performance_job', 'validation_job') if r[c]}
    ids.add(args.dependency)
    ids.update(g['required_job'] for g in plan if g.get('required_job'))
    jobs = job_snapshot(ids, jobs)
    deferred = [r['performance_job'] for r in rows if int(r['cores']) > args.max_total_cores
                and jobs.get(r['performance_job'], {}).get('job_state') in ('Q', 'H')]
    for job_id in deferred:
        if 'u' not in jobs[job_id].get('Hold_Types', ''):
            command(['qhold', '-h', 'u', job_id])
    if deferred:
        jobs = job_snapshot(set(deferred), jobs)
        deferred = [i for i in deferred if jobs[i].get('job_state') == 'H'
                    and 'u' in jobs[i].get('Hold_Types', '')]
    failed = [i for i in ids if jobs.get(i, {}).get('job_state') == 'F'
              and jobs[i].get('Exit_status') != 0]
    pending_performance = sum(jobs.get(r['performance_job'], {}).get('job_state') != 'F'
                              and r['performance_job'] not in deferred for r in rows)
    pending_validation = sum(jobs.get(r['performance_job'], {}).get('Exit_status') == 0
                             and jobs.get(r['validation_job'], {}).get('job_state') != 'F' for r in rows)
    state = {'pending_performance_groups': pending_performance, 'deferred_held_jobs': deferred,
             'pending_validation_groups': pending_validation, 'failed_jobs_not_retried': sorted(failed),
             'performance_states': dict(Counter(jobs.get(r['performance_job'], {}).get('job_state', 'unknown') for r in rows)),
             'validation_states': dict(Counter(jobs.get(r['validation_job'], {}).get('job_state', 'unknown') for r in rows))}
    candidates = unregistered_groups(plan, rows, root, jobs, args.max_total_cores)
    state['eligible_unregistered_groups'] = len(candidates)
    state['eligible_unregistered_cells'] = sum(len(g['cells']) for g in candidates)
    state['endpoint_proof_state'] = {g['required_job']: jobs.get(g['required_job'], {}).get('job_state', 'unknown')
                                     for g in plan if g.get('required_job')}
    project_output = command(['hpc', 'project'])
    balance_rows = [line for line in project_output.splitlines() if line.strip().startswith(args.project + ' ')]
    if not balance_rows:
        state['action'] = 'waiting_amgr_login'
        return state, jobs
    state['balance_cpu_hours'] = float(balance_rows[0].split('|')[2])
    if pending_performance >= args.max_pending or pending_validation >= args.max_unvalidated:
        state['action'] = 'waiting_existing_jobs'
    elif not candidates:
        state['action'] = 'no_eligible_unregistered_cells'
    else:
        # A successful metadata query must not trigger spending when results cannot be saved.
        probe = root / '.auto_monitor_write_probe'
        try:
            with probe.open('wb') as target:
                target.write(b'0' * 4096)
                target.flush()
                os.fsync(target.fileno())
        finally:
            probe.unlink(missing_ok=True)
        selected = root / 'auto_monitor_candidates.json'
        selected.write_text(json.dumps(candidates, indent=2) + '\n')
        submit_command = ['python3', str(args.submit_script), args.run_id, args.project,
                          str(selected), '--submit', '--dependency', args.dependency,
                          '--margin', str(args.margin), '--max-new', str(args.max_pending - pending_performance),
                          '--cores-per-node', '1', '2', '4', '8', '16', '32', '64']
        for job_id in deferred:
            submit_command += ['--defer-held-job', job_id]
        result = command(submit_command, timeout=180)
        print(result, flush=True)
        last_check = root / f'core_group_last_check_{datetime.now(ZoneInfo("Asia/Singapore")).strftime("%Y%m%d")}.json'
        state['submission_check'] = json.loads(last_check.read_text())
        state['action'] = 'submitted' if state['submission_check']['groups'] else 'waiting_real_credits'
    return state, jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('project')
    parser.add_argument('plan', type=Path)
    parser.add_argument('--dependency', required=True)
    parser.add_argument('--interval', type=int, default=300)
    parser.add_argument('--margin', type=float, default=64)
    parser.add_argument('--max-pending', type=int, default=6)
    parser.add_argument('--max-unvalidated', type=int, default=24)
    parser.add_argument('--until', required=True, help='ISO timestamp with timezone; no new submissions after this time')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--state-dir', type=Path, help='Keep heartbeat/log metadata outside a full results filesystem')
    parser.add_argument('--max-total-cores', type=int, default=512, help='Defer larger queued groups and only submit within this limit')
    parser.add_argument('--submit-script', type=Path, default=Path('scripts/submit_vanda_core_groups.py'))
    args = parser.parse_args()
    root = Path('results/updated_vanda_scaling') / args.run_id
    deadline = datetime.fromisoformat(args.until)
    state_dir = args.state_dir or root
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = state_dir / 'auto_monitor_jobs.json'
    cache = snapshot if snapshot.exists() else root / 'auto_monitor_jobs.json'
    jobs = json.loads(cache.read_text()) if cache.exists() else {}
    with (root / 'auto_monitor.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (state_dir / 'auto_monitor.pid').write_text(str(os.getpid()) + '\n')
        while True:
            now = datetime.now(ZoneInfo('Asia/Singapore'))
            if (root / 'STOP_AUTO_SUBMIT').exists() or (state_dir / 'STOP_AUTO_SUBMIT').exists() or now >= deadline:
                state = {'action': 'stopped', 'reason': 'stop_file_or_submission_deadline'}
            else:
                try:
                    state, jobs = cycle(args, root, jobs)
                    snapshot.write_text(json.dumps(jobs, indent=2) + '\n')
                except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
                    storage_error = isinstance(error, OSError) and error.errno in (errno.ENOSPC, errno.EDQUOT)
                    state = {'action': 'waiting_result_storage' if storage_error else 'query_or_submission_error_no_blind_retry',
                             'error_type': type(error).__name__, 'error': str(error)}
            state.update(observed_at=now.isoformat(), pid=os.getpid(), interval_seconds=args.interval,
                         until=args.until, margin_cpu_hours=args.margin, state_directory=str(state_dir),
                         max_total_cores=args.max_total_cores)
            record = json.dumps(state, ensure_ascii=False)
            (state_dir / 'auto_monitor_status.json').write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
            with (state_dir / 'auto_monitor_events.jsonl').open('a') as output:
                output.write(record + '\n')
            print(record, flush=True)
            if args.once or state['action'] == 'stopped':
                break
            time.sleep(args.interval)


if __name__ == '__main__':
    main()
