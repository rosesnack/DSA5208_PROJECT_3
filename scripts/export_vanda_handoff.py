"""Export full-target coverage, current job assignments, and CPU split coverage."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re

from audit_fixed_matrix import additional_512_cells, graph_names, gpu_cells, vanda_cells


def write_csv(path, rows, fieldnames=None):
    with path.open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames or list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def source_jobs(row, performance_job='', validation_job=''):
    folder = Path(row['summary']).parent
    batch = Path(row['marker']).parent
    completion_job = Path(row['marker']).read_text().strip()
    if (folder / 'performance_job.txt').exists():
        performance_job = (folder / 'performance_job.txt').read_text().strip()
    if (folder / 'provenance.json').exists():
        proof = json.loads((folder / 'provenance.json').read_text())
        performance_job = proof.get('performance_job', performance_job)
        validation_job = proof.get('validation_job', validation_job)
    candidates = {performance_job} if performance_job else set()
    if not performance_job:
        for name in ('performance_job.txt', 'measurement_complete.txt', 'resume_gpu_complete.txt', 'resume_serial_complete.txt'):
            if (batch / name).exists():
                candidates.add((batch / name).read_text().strip())
        for name in ('job_environment.txt', 'environment.txt', 'resume_environment.txt'):
            if (batch / name).exists():
                candidates.update(re.findall(r'^(?:PBS job|Resume job):\s*(\S+)', (batch / name).read_text(), re.M))
        if len(candidates) == 1:
            performance_job = next(iter(candidates))
    if (batch / 'resume_gpu_complete.txt').exists() or (batch / 'resume_serial_complete.txt').exists():
        validation_job = validation_job or completion_job
    return performance_job, validation_job, completion_job, '|'.join(sorted(candidates))


def cpu_path(root, graph, nodes, cores, method, threads, communication):
    processes = cores // threads
    suffix = '_halo' if communication == 'halo' else ''
    if method == 'mpi_kokkos' and threads > 1:
        folder = root / 'kokkos_cpu_512' / graph if cores == 512 else root / 'kokkos_cpu_grid' / graph / f'nodes{nodes}'
    else:
        folder = root / 'strong' / graph / ('nodes8_p512' if cores == 512 else f'nodes{nodes}')
    folder /= method + suffix
    if method == 'mpi_kokkos':
        folder /= 'OpenMP'
    config = f'p{processes}' + (f'_t{threads}' if method == 'hybrid' or threads > 1 else '')
    return folder / graph / config / 'summary.json'


def plan_owners(plans):
    """Future plans are ownership records, including cells not yet submitted."""
    owners = {}
    for account, path in plans.items():
        for group in json.loads(path.read_text()):
            for item in group['cells']:
                key = item['canonical_summary']
                if key in owners:
                    raise ValueError(f'Duplicate future ownership: {key}')
                owners[key] = account
    return owners


def handoff_action(status):
    if status == 'validated':
        return 'reuse_do_not_rerun'
    if status == 'unsubmitted':
        return 'owner_transfer_required_before_submission'
    if status == 'deferred_512':
        return 'deferred_do_not_submit'
    if status == 'performance_failed':
        return 'owner_review_failure_and_partial_results'
    if status == 'held':
        return 'owner_review_existing_job_do_not_duplicate'
    return 'track_existing_jobs_do_not_resubmit'


def export_weak_inventory(output, roots):
    """Keep the separate weak curves visible without assigning an unverified rerun."""
    rows = []

    def add(suite, family, path, marker):
        source = next((root for root in roots if (root / path).is_file() and (root / marker).is_file()), None)
        rows.append({'suite': suite, 'family': family, 'canonical_summary': str(path),
                     'status': 'validated' if source else 'evidence_missing_verify_remote_first',
                     'source_root': str(source) if source else '',
                     'marker': str(source / marker) if source else '',
                     'handoff_action': 'reuse_do_not_rerun' if source else 'owner_review_remote_outputs_and_legacy_jobs',
                     'submission_allowed_from_snapshot': False})

    for family in ('uniform', 'hub', 'controlled'):
        for method in ('mpi', 'mpi_kokkos', 'hybrid'):
            for endpoint in (False, True):
                counts = (128,) if method == 'hybrid' else (512,)
                if not endpoint:
                    counts = (1, 2, 4, 8, 16, 32, 64) if method == 'hybrid' else (1, 2, 4, 8, 16, 32, 64, 128, 256)
                folder = Path('weak_512') / family if endpoint else Path('weak')
                for p in counts:
                    for mode in ('', '_halo'):
                        base = folder / (method + mode)
                        if method == 'mpi_kokkos':
                            base /= 'OpenMP'
                        config = f'p{p}_t4' if method == 'hybrid' else f'p{p}'
                        add('rank_cpu_512' if endpoint else 'rank_cpu_regular', family,
                            base / f'weak_{family}_p{p:03d}' / config / 'summary.json', folder / 'complete.txt')
        for cores in (4, 8, 16, 32, 64, 128, 256, 512):
            folder = Path('weak_core') / family
            for method in ('hybrid', 'mpi_kokkos'):
                for mode in ('', '_halo'):
                    base = folder / (method + mode)
                    if method == 'mpi_kokkos':
                        base /= 'OpenMP'
                    add('core_cpu', family, base / f'weak_{family}_p{cores:03d}' / f'p{cores // 4}_t4/summary.json',
                        folder / f'complete_p{512 if cores == 512 else 256}.txt')
        for scale in (1, 2):
            for item in gpu_cells(Path('gpu_weak'), f'weak_{family}_p{scale:03d}',
                                  Path('gpu_weak/complete.txt'), (scale,), (1, 2, 4, 8, 16, 32)):
                add('gpu_node', family, item['summary'], item['marker'])
    write_csv(output / 'weak_experiment_manifest.csv', rows)
    return {suite: dict(Counter(r['status'] for r in rows if r['suite'] == suite))
            for suite in sorted({r['suite'] for r in rows})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--main-root', required=True, type=Path)
    parser.add_argument('--assist-root', required=True, type=Path)
    parser.add_argument('--snapshots', required=True, type=Path)
    parser.add_argument('--main-plan', required=True, type=Path)
    parser.add_argument('--assist-plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.audit.open() as source:
        audit = list(csv.DictReader(source))
    plans = {'xtt_ella': args.main_plan, 'hongxinran': args.assist_plan}
    owners = plan_owners(plans)
    registered, snapshots, submitted = {}, {}, []
    for account, root in [('xtt_ella', args.main_root), ('hongxinran', args.assist_root)]:
        snapshots[account] = json.loads((args.snapshots / f'queue_{account}.json').read_text())
        with (root / 'core_group_jobs.tsv').open() as source:
            for row in csv.DictReader(source, delimiter='\t'):
                plan = json.loads(Path(row['plan']).read_text())
                submitted.append({'account': account, **row})
                for c in plan['cells']:
                    key = c['canonical_summary']
                    assert key not in registered, key
                    registered[key] = {'account': account, **row,
                                       'saved_measurement_check': plan.get('reuse_saved_measurements', False)}
    manifest, coverage = [], {}
    for row in audit:
        key = str(Path(row['summary']).relative_to(Path(row['source_root'])))
        assignment = registered.get(key)
        validated = row['validated'] == 'True'
        perf = assignment['performance_job'] if assignment else ''
        val = assignment['validation_job'] if assignment else ''
        account = assignment['account'] if assignment else ''
        job = snapshots[account]['known_jobs'].get(perf, {}) if account else {}
        if validated:
            status = 'validated'
            perf, val, completion, candidates = source_jobs(row, perf, val)
        elif assignment:
            state = job.get('job_state', '')
            if assignment['saved_measurement_check']:
                check = snapshots[account]['known_jobs'].get(val, {})
                status = ('performance_failed' if check.get('job_state') == 'F'
                          and str(check.get('Exit_status')) != '0' else 'awaiting_validation')
            elif state == 'F':
                status = 'awaiting_validation' if str(job.get('Exit_status')) == '0' else 'performance_failed'
            else:
                status = {'H': 'held', 'Q': 'queued', 'R': 'running', 'E': 'exiting'}.get(state, 'registered_unconfirmed')
        else:
            status = 'deferred_512' if '512' in row['stage'] else 'unsubmitted'
        if not validated:
            completion, candidates = '', perf
            if key not in owners:
                raise ValueError(f'Unfinished cell has no future owner: {key}')
            if assignment and owners[key] != account:
                raise ValueError(f'Submitted cell conflicts with future ownership: {key}')
        item = {**row, 'canonical_summary': key, 'status': status, 'assigned_account': account,
                'performance_job': perf, 'validation_job': val, 'completion_job': completion,
                'performance_job_candidates': candidates, 'pbs_state': job.get('job_state', ''),
                'hold_types': job.get('Hold_Types', ''), 'submission_plan': assignment['plan'] if assignment else '',
                'future_owner': '' if validated else owners[key],
                'future_plan': '' if validated else str(plans[owners[key]]),
                'handoff_action': handoff_action(status), 'submission_allowed_from_snapshot': False}
        manifest.append(item)
        coverage[key] = item
    write_csv(args.output / 'experiment_manifest_20700.csv', manifest)
    write_csv(args.output / 'submitted_core_groups.csv', submitted)
    # These are frozen inventories, not reservations or runnable submission plans.
    statuses = ('validated', 'unsubmitted', 'deferred_512', 'performance_failed', 'held',
                'queued', 'running', 'exiting', 'awaiting_validation', 'registered_unconfirmed')
    for status in statuses:
        write_csv(args.output / f'cells_{status}.csv', [r for r in manifest if r['status'] == status],
                  fieldnames=list(manifest[0]))

    original = {str(c['summary'].relative_to(args.main_root)) for c in vanda_cells(args.main_root)}
    full = {str(c['summary'].relative_to(args.main_root)) for c in additional_512_cells(args.main_root)} | original
    assert len(original) == 19980 and len(full) == 20700
    layouts, totals = [], []
    for cores, nodes in [(1, 1), (2, 1), (4, 1), (8, 1), (16, 1), (32, 1), (64, 2), (128, 4), (256, 8), (512, 8)]:
        start = len(layouts)
        for graph in graph_names():
            for method in ('mpi', 'hybrid', 'mpi_kokkos'):
                for threads in ((1,) if method == 'mpi' else (1, 2, 4, 8, 16, 32)):
                    if cores % threads or cores // threads < nodes or (cores // threads) % nodes:
                        continue
                    for mode in ('allgather', 'halo'):
                        key = str(cpu_path(args.main_root, graph, nodes, cores, method, threads, mode).relative_to(args.main_root))
                        assert key in full, (cores, nodes, method, threads, key)
                        layouts.append({'graph': graph, 'cores': cores, 'nodes': nodes, 'implementation': method,
                                        'processes': cores // threads, 'threads': threads, 'communication': mode,
                                        'in_original_19980': key in original, 'status': coverage[key]['status'],
                                        'canonical_summary': key})
        rows = layouts[start:]
        totals.append({'cores': cores, 'mainline_nodes': nodes, 'expected_configs': len(rows),
                       'in_original_19980': sum(x['in_original_19980'] for x in rows),
                       'added_targets': sum(not x['in_original_19980'] for x in rows),
                       'validated_configs': sum(x['status'] == 'validated' for x in rows)})
    write_csv(args.output / 'cpu_core_layouts.csv', layouts)
    weak = export_weak_inventory(args.output, list(dict.fromkeys([args.main_root, args.assist_root,
                                *(Path(r['source_root']) for r in audit)])))
    summary = {'target': 20700, 'original_target': 19980, 'later_512_splits': 720,
               'status_counts': {status: sum(x['status'] == status for x in manifest)
                                 for status in statuses},
               'submitted_group_counts': dict(Counter(x['account'] for x in submitted)),
               'mainline_coverage': totals, 'registered_cross_account_overlap': 0,
               'future_plan_cross_account_overlap': 0,
               'unfinished_owner_counts': dict(Counter(x['future_owner'] for x in manifest if x['future_owner'])),
               'future_plans': {user: str(path) for user, path in plans.items()},
               'handoff_rule': 'Frozen snapshot: no row grants submission permission. Unsubmitted cells remain owned; transfer ownership out of the live source plan and check both live queues before a teammate submits. Local RUN_ID deduplication is not cross-account locking.',
               'weak_scaling_separate': weak,
               'snapshots': {user: {'observed_at': snap['observed_at'], 'monitor_action': snap['monitor']['action'],
                                     'active_job_count': len(snap['active_jobs'])} for user, snap in snapshots.items()},
               'scope_note': 'Thread range is 1/2/4/8/16/32. Regular per-node CPU budget is at most 32; the 512 endpoint uses 8 nodes x 64. Weak scaling is separate.'}
    (args.output / 'handoff_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
