"""Check that the handover cannot label another account's work as unowned."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from export_vanda_handoff import handoff_action, plan_owners


class HandoffTests(unittest.TestCase):
    def test_duplicate_future_ownership_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as directory:
            plans = {}
            for account in ('main', 'teammate'):
                path = Path(directory) / f'{account}.json'
                path.write_text(json.dumps([{'cells': [{'canonical_summary': 'same/config/summary.json'}]}]))
                plans[account] = path
            with self.assertRaisesRegex(ValueError, 'Duplicate future ownership'):
                plan_owners(plans)

    def test_pending_validation_and_unknown_registration_do_not_trigger_reruns(self):
        for status in ('queued', 'running', 'awaiting_validation', 'registered_unconfirmed', 'exiting'):
            self.assertEqual(handoff_action(status), 'track_existing_jobs_do_not_resubmit')

    def test_published_inventory_has_unique_keys_and_owned_missing_cells(self):
        folder = ROOT / 'results/updated_vanda_scaling/git_sync_20261111'
        with (folder / 'experiment_manifest_20700.csv').open() as source:
            rows = list(csv.DictReader(source))
        summary = json.loads((folder / 'handoff_summary.json').read_text())
        owners = plan_owners({user: ROOT / path for user, path in summary['future_plans'].items()})
        self.assertEqual(len(rows), 20700)
        self.assertEqual(len({r['canonical_summary'] for r in rows}), len(rows))
        self.assertEqual(sum(summary['status_counts'].values()), len(rows))
        for row in rows:
            self.assertEqual(row['submission_allowed_from_snapshot'], 'False')
            if row['status'] == 'validated':
                self.assertEqual(row['handoff_action'], 'reuse_do_not_rerun')
                self.assertFalse(row['future_owner'])
            else:
                self.assertEqual(row['future_owner'], owners[row['canonical_summary']])
                if row['assigned_account']:
                    self.assertEqual(row['future_owner'], row['assigned_account'])
        with (folder / 'cells_unsubmitted.csv').open() as source:
            candidates = list(csv.DictReader(source))
        self.assertEqual(len(candidates), summary['status_counts']['unsubmitted'])
        self.assertTrue(all(r['status'] == 'unsubmitted' and r['future_owner'] and
                            not r['performance_job'] and
                            r['handoff_action'] == 'owner_transfer_required_before_submission'
                            for r in candidates))

    def test_missing_weak_evidence_is_not_claimed_as_never_run(self):
        folder = ROOT / 'results/updated_vanda_scaling/git_sync_20261111'
        with (folder / 'weak_experiment_manifest.csv').open() as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 402)
        self.assertEqual(len({r['canonical_summary'] for r in rows}), len(rows))
        for row in rows:
            self.assertEqual(row['submission_allowed_from_snapshot'], 'False')
            if row['status'] != 'validated':
                self.assertEqual(row['status'], 'evidence_missing_verify_remote_first')
                self.assertEqual(row['handoff_action'], 'owner_review_remote_outputs_and_legacy_jobs')


if __name__ == '__main__':
    unittest.main()
