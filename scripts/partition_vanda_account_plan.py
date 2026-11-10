"""Assign unregistered ordinary hub groups to a second account without overlap."""
import argparse
import json
from pathlib import Path


def partition(groups, registered, completed, budget, low_core=False):
    candidates = []
    for index, group in enumerate(groups):
        allocation_matches = group['cores_per_node'] < 32 if low_core else group['cores_per_node'] == 32
        if not (group['graph'].startswith('grid_hub_') and allocation_matches
                and group['cores'] <= 256 and not group.get('extension')):
            continue
        cells = [c for c in group['cells']
                 if c['canonical_summary'] not in registered | completed]
        if cells:
            candidates.append((index, {**group, 'cells': cells}))
    delegated = []
    reserved = 0.0
    def request_hours(group):
        h, m, s = map(int, group['walltime'].split(':'))
        return group['cores'] * (h + m / 60 + s / 3600)

    order = (lambda pair: (request_hours(pair[1]) / len(pair[1]['cells']),
                            pair[1]['nodes'], pair[1]['graph'], pair[1]['cores_per_node'])) if low_core else \
            (lambda pair: (pair[1]['nodes'], pair[1]['graph']))
    for _, group in sorted(candidates, key=order):
        h, m, s = map(int, group['walltime'].split(':'))
        hours = group['cores'] * (h + m / 60 + s / 3600)
        if reserved + hours <= budget:
            delegated.append(group)
            reserved += hours
    claimed = {c['canonical_summary'] for g in delegated for c in g['cells']}
    primary = []
    for group in groups:
        cells = [c for c in group['cells'] if c['canonical_summary'] not in claimed]
        if cells:
            primary.append({**group, 'cells': cells})
    original = {c['canonical_summary'] for g in groups for c in g['cells']}
    retained = {c['canonical_summary'] for g in primary for c in g['cells']}
    assert not retained & claimed
    assert retained | claimed == original
    assert not claimed & (registered | completed)
    return primary, delegated, reserved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--budget', type=float, required=True)
    parser.add_argument('--low-core', action='store_true', help='Assign ordinary hub groups below 32 cores per node, prioritizing configurations per reserved CPU-hour')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    primary, assist, reserved = partition(snapshot['groups'], set(snapshot['registered_cells']),
                                          set(snapshot['completed_cells']), args.budget, args.low_core)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, plan in [('primary_plan.json', primary), ('hongxinran_plan.json', assist)]:
        (args.output_dir / name).write_text(json.dumps(plan, indent=2) + '\n')
    summary = {'source_observed_at': snapshot['observed_at'], 'reservation_ceiling_cpu_hours': args.budget,
               'delegated_reservations_cpu_hours': reserved, 'delegated_groups': len(assist),
               'delegated_cells': sum(len(g['cells']) for g in assist),
               'ownership': {c['canonical_summary']: 'hongxinran' for g in assist for c in g['cells']}}
    (args.output_dir / 'account_partition.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'ownership'}, indent=2))


if __name__ == '__main__':
    main()
