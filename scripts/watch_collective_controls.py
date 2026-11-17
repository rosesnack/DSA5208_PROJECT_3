"""Monitor registered controls and refresh placement without changing queue or layout."""
import argparse
from datetime import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time

from refresh_vanda_cpu_placement import refresh_queued


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('hosts', type=Path)
    parser.add_argument('--until', required=True)
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    home = args.receipt.parent
    deadline = datetime.fromisoformat(args.until)
    with (home / 'watch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while datetime.now(deadline.tzinfo) < deadline:
            rows = json.loads(args.receipt.read_text())['rows']
            ids = [r[key] for r in rows for key in ('performance_job', 'validation_job')]
            try:
                response = subprocess.check_output(['qstat', '-x', '-f', '-F', 'json', *ids], text=True, timeout=45)
                jobs = json.loads(response)['Jobs']
                updates = refresh_queued(rows, jobs, args.hosts, 256)
                state = {'time': datetime.now(deadline.tzinfo).isoformat(),
                         'jobs': {k: {field: v.get(field) for field in
                                  ('job_state', 'Exit_status', 'queue', 'Resource_List',
                                   'resources_used', 'exec_vnode', 'comment')} for k, v in jobs.items()},
                         'progress': {}, 'placement_updates': updates}
                for row in rows:
                    plan = json.loads(Path(row['plan']).read_text())
                    root = Path(plan['output'])
                    state['progress'][row['id']] = {
                        'target': row['cells'],
                        'measured': sum((root / c['id'] / 'measurement_complete.txt').exists() for c in plan['cells']),
                        'validated': sum((root / c['id'] / 'validation_complete.txt').exists() for c in plan['cells'])}
                (home / 'watch_status.json').write_text(json.dumps(state, indent=2) + '\n')
                if updates:
                    with (home / 'placement_events.jsonl').open('a') as out:
                        out.write(json.dumps({'time': state['time'], 'updates': updates}) + '\n')
                if len(jobs) == len(ids) and all(j['job_state'] == 'F' for j in jobs.values()):
                    break
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                with (home / 'watch_errors.log').open('a') as out:
                    out.write(datetime.now(deadline.tzinfo).isoformat() + ' ' + str(error) + '\n')
            time.sleep(args.interval)


if __name__ == '__main__':
    main()
