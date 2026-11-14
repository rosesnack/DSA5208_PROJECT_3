"""Independently validate intact cells from a failed batch without measuring them again."""
import json
import os
from pathlib import Path
import shutil
import sys

from run_vanda_core_group import folder_for


plan = Path(sys.argv[1])
group = json.loads(plan.read_text())
source = Path(group['reuse_source'])
raw = Path(os.environ['DATA_ROOT']) / 'results' / group['raw_stage'] / group['graph'] / (
    f"nodes{group['nodes']}_cores{group['cores_per_node']}")
assert not raw.exists(), raw
raw.mkdir(parents=True)
for name in ('cpu_hosts.jsonl', 'environment.json', 'dataset.tsv'):
    shutil.copy2(source / name, raw / name)
(raw / 'group_plan.json').write_text(json.dumps(group, indent=2) + '\n')
serial = raw / 'serial' / group['graph']
serial.mkdir(parents=True)
for name in ('summary.json', 'history.csv', 'timings.csv', 'ranks.csv'):
    os.link(source / 'serial' / group['graph'] / name, serial / name)
mapping = raw / 'mapping'
mapping.mkdir()
jobs = set()
for cell in group['cells']:
    relative = folder_for(cell, group['graph'])
    destination = raw / relative
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('summary.json', 'history.csv', 'timings.csv', 'ranks.csv', 'performance_job.txt'):
        os.link(source / relative / name, destination / name)
    summary = json.loads((destination / 'summary.json').read_text())
    assert summary['warmup_runs'] == 1 and summary['repeat_runs'] == 5
    jobs.add((destination / 'performance_job.txt').read_text().strip())
    p, t = cell['processes'], cell['threads']
    for suffix in ('jsonl', 'csv'):
        path = source / 'mapping' / f'p{p}_t{t}.{suffix}'
        shutil.copy2(path, mapping / path.name)
assert len(jobs) == 1, jobs
(raw / 'measurement_complete.txt').write_text(next(iter(jobs)) + '\n')
(raw / 'reuse_origin.json').write_text(json.dumps({
    'source_raw': str(source), 'performance_job': next(iter(jobs)),
    'validation_job': os.environ['PBS_JOBID'], 'cells': group['cells'],
    'scope': 'Only intact saved cells; the original batch failed later. No performance rerun.'
}, indent=2) + '\n')
os.execvp('python3', ['python3', 'scripts/run_vanda_core_group.py', 'finalize', str(plan)])
