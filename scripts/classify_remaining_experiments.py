"""Classify each missing Vanda cell using saved exclusions, submissions and raw output."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from audit_fixed_matrix import graph_names, resolve_cell, vanda_cells


LABELS = {
    'first_run': '未见正式提交或运行记录',
    'excluded_result': '旧完整结果被排除，需合格补跑',
    'submitted_incomplete': '已有提交或部分输出，尚无确认完整测量',
    'awaiting_validation': '已保存完整测量，等待独立校验',
}


def batch_key(item, root):
    parts = item['summary'].relative_to(root).parts
    if parts[0] == 'strong':
        stage = 'mpi_strong_512' if parts[2] == 'nodes8_p512' else 'mpi_strong'
        return stage, item['graph'], 8 if stage.endswith('512') else int(parts[2][5:])
    if parts[0] == 'kokkos_cpu_grid':
        return 'kokkos_cpu_grid', item['graph'], int(parts[2][5:])
    if parts[0] == 'kokkos_cpu_512':
        return 'kokkos_cpu_512', item['graph'], 8
    if parts[0] == 'gpu':
        return 'gpu', item['graph'], 2
    return 'serial', item['graph'], 1


def read_history(roots):
    result = defaultdict(set)
    aliases = {'strong': 'mpi_strong', 'strong512': 'mpi_strong_512',
               'mpi_512_fixed': 'mpi_strong_512', 'kokkos_retry': 'kokkos_cpu_grid',
               'mpi_strong_retry': 'mpi_strong'}
    names = ['submitted_jobs.tsv', 'failed_jobs.tsv', 'replaced_jobs.tsv', 'retry_jobs.tsv',
             'audited_resume_jobs.tsv', 'free_cpu_archived.tsv',
             'free_cpu_archived_submissions.tsv', 'cancelled_free_jobs_20261106.tsv']
    for root in roots:
        for name in names:
            path = root / name
            if not path.exists():
                continue
            for row in csv.DictReader(path.open(), delimiter='\t'):
                stage = aliases.get(row.get('stage'), row.get('stage'))
                if stage not in ('serial', 'gpu', 'mpi_strong', 'mpi_strong_512',
                                 'kokkos_cpu_grid', 'kokkos_cpu_512'):
                    continue
                graph = row.get('graph', row.get('graph_or_case'))
                nodes = row.get('nodes', '')
                if graph not in graph_names() or not nodes.isdigit():
                    continue
                for field in ('job_id', 'original_job', 'replacement_job', 'performance_job'):
                    if row.get(field):
                        result[stage, graph, int(nodes)].add(row[field])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--reuse-root', type=Path, action='append', default=[])
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--raw-cells', type=Path, required=True)
    parser.add_argument('--historical-raw', type=Path, action='append', default=[])
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args()
    roots = [args.root, *args.reuse_root]
    history = read_history(roots)
    snapshot = json.loads(args.snapshot.read_text())
    raw_data = json.loads(args.raw_cells.read_text())
    raw = {c['canonical_summary']: c for c in raw_data['cells']}
    old_invalid_raw = {}
    for path in args.historical_raw:
        for record in json.loads(path.read_text())['cells']:
            if record['complete'] and record['queue'] == 'cpu_parallel':
                old_invalid_raw[record['canonical_summary']] = record
    submitted = {}
    for row in csv.DictReader((args.root / 'core_group_jobs.tsv').open(), delimiter='\t'):
        plan = json.loads(Path(row['plan']).read_text())
        for item in plan['cells']:
            submitted[item['canonical_summary']] = (row['performance_job'], row['validation_job'])
    exclusions = []
    for root in roots:
        table = root / 'excluded_invalid_performance_results_20261106.tsv'
        if table.exists():
            for row in csv.DictReader(table.open(), delimiter='\t'):
                prefix = Path(row['removed_path']).relative_to(Path('results/updated_vanda_scaling') / root.name)
                exclusions.append((prefix.parts, row['job_id'], row['exclusion_reason']))
    records = []
    completed = 0
    for item in vanda_cells(args.root):
        resolved, _ = resolve_cell(item, args.root, args.reuse_root)
        if resolved['summary'].exists() and resolved['marker'].exists():
            completed += 1
            continue
        relative = item['summary'].relative_to(args.root)
        key = str(relative)
        old_jobs = history.get(batch_key(item, args.root), set())
        current = submitted.get(key)
        excluded = [x for x in exclusions if relative.parts[:len(x[0])] == x[0]]
        old_raw = old_invalid_raw.get(key)
        validation = snapshot['Jobs'].get(current[1], {}) if current else {}
        performance = snapshot['Jobs'].get(current[0], {}) if current else {}
        bad_validation = validation.get('job_state') == 'F' and validation.get('Exit_status') != 0
        has_output = any((root / relative).exists() for root in roots)
        if key in raw and not bad_validation:
            category = 'awaiting_validation'
            reason = 'Original five-repeat solver completed this cell; no independent completion marker yet.'
        elif excluded or old_raw:
            category = 'excluded_result'
            reason = '; '.join(sorted({x[2] for x in excluded})) if excluded else old_raw['reason']
        elif old_jobs or current or has_output:
            category = 'submitted_incomplete'
            reason = 'Submission or partial output exists; complete reusable measurement has not been confirmed.'
            if bad_validation:
                reason = 'Saved output failed independent validation; inspect before resubmission.'
        else:
            category = 'first_run'
            reason = 'No matching formal Vanda submission/output found in the preserved records.'
        records.append({'scope': 'original_fixed_matrix', 'stage': item['stage'],
                        'graph': item['graph'], 'layout': item['layout'], 'category': category,
                        'category_label': LABELS[category], 'canonical_summary': key,
                        'historical_jobs': ';'.join(sorted(old_jobs)),
                        'excluded_jobs': ';'.join(sorted({x[1] for x in excluded})),
                        'historical_partial_summary': old_raw['source_raw_summary'] if old_raw else '',
                        'exclusion_basis': 'excluded_complete_batch' if excluded else 'old_free_partial_cell' if old_raw else '',
                        'current_performance_job': current[0] if current else '',
                        'performance_state': performance.get('job_state', ''),
                        'validation_state': validation.get('job_state', ''),
                        'complete_raw_measurement': key in raw, 'reason': reason})
    # Added endpoint splits are separate from the original 19,980-cell target.
    for graph in graph_names():
        for method in ('mpi_openmp', 'mpi_kokkos_openmp'):
            for threads in (2, 8, 16, 32):
                for mode in ('allgather', 'halo'):
                    records.append({'scope': 'additional_512_splits', 'stage': method,
                                    'graph': graph, 'layout': f'n=8,p={512 // threads},T={threads},{mode}',
                                    'category': 'first_run', 'category_label': LABELS['first_run'],
                                    'reason': 'Added target; no formal submission or measurement recorded.'})
    counts = Counter((r['scope'], r['category']) for r in records)
    waiting = [r for r in records if r['category'] == 'awaiting_validation']
    submitted_incomplete = [r for r in records if r['category'] == 'submitted_incomplete']
    summary = {'snapshot_at': snapshot['captured_at'], 'validated_original_cells': completed,
               'missing_original_cells': sum(v for (scope, _), v in counts.items() if scope == 'original_fixed_matrix'),
               'counts': {scope: {c: counts[scope, c] for c in LABELS}
                          for scope in ('original_fixed_matrix', 'additional_512_splits')},
               'currently_covered_by_category': {category: sum(bool(r.get('current_performance_job'))
                   for r in records if r['scope'] == 'original_fixed_matrix' and r['category'] == category)
                   for category in LABELS},
               'waiting_by_parent_state': dict(Counter(r.get('performance_state') for r in waiting)),
               'excluded_result_by_basis': dict(Counter(r['exclusion_basis'] for r in records if r['category'] == 'excluded_result')),
               'submitted_incomplete_with_current_job': sum(bool(r['current_performance_job']) for r in submitted_incomplete),
               'precedence': ['validated results excluded', 'complete raw measurement awaiting validation',
                              'explicitly excluded result', 'submission/partial output', 'no matching record'],
               'scope_note': 'Formal Vanda fixed-graph cells only. No-history means absent from preserved records, not proof that no ad-hoc or local run ever occurred.'}
    assert completed + summary['missing_original_cells'] == 19980
    assert sum(summary['counts']['additional_512_splits'].values()) == 720
    fields = list(records[0])
    with args.csv.open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader(); writer.writerows(records)
    args.json.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
