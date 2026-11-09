"""Budget and reuse regressions for the controller that can spend project credits."""
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import submit_vanda_core_groups as submit
import watch_vanda_core_groups as watch
from watch_vanda_core_groups import unregistered_groups


class AutoSubmitTests(unittest.TestCase):
    def test_non512_priority_excludes_endpoints_even_after_their_proof_passes(self):
        normal = {'cores': 256, 'prerequisite': '', 'cells': [{'canonical_summary': 'a/summary.json'}]}
        endpoint = {'cores': 512, 'prerequisite': '', 'cells': [{'canonical_summary': 'b/summary.json'}]}
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(unregistered_groups([normal, endpoint], [], Path(folder), {}, 256), [normal])

    def test_scheduler_reply_without_jobs_becomes_recoverable_error(self):
        response = SimpleNamespace(stdout='{"pbs_version":"23"}', stderr='', returncode=0)
        with patch.object(watch.subprocess, 'run', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'waiting for scheduler recovery'):
                watch.job_snapshot({'pending'}, {})

    def test_scheduler_outage_records_heartbeat_instead_of_crashing(self):
        prior = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                root = Path('results/updated_vanda_scaling/test')
                root.mkdir(parents=True)
                argv = ['watch', 'test', 'personal-test', 'plan.json', '--dependency', 'proof',
                        '--until', '2099-01-01T00:00:00+08:00', '--once', '--state-dir', 'state']
                with patch.object(sys, 'argv', argv), \
                     patch.object(watch, 'cycle', side_effect=RuntimeError('PBS response has no Jobs mapping')), \
                     contextlib.redirect_stdout(io.StringIO()):
                    watch.main()
                status = json.loads(Path('state/auto_monitor_status.json').read_text())
                self.assertEqual(status['action'], 'query_or_submission_error_no_blind_retry')
                self.assertEqual(status['error_type'], 'RuntimeError')
                self.assertIn('observed_at', status)
                self.assertFalse((root / 'auto_monitor_status.json').exists())
            finally:
                os.chdir(prior)

    def test_full_results_filesystem_pauses_spending_and_keeps_external_heartbeat(self):
        prior = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                root = Path('results/updated_vanda_scaling/test')
                root.mkdir(parents=True)
                argv = ['watch', 'test', 'personal-test', 'plan.json', '--dependency', 'proof',
                        '--until', '2099-01-01T00:00:00+08:00', '--once', '--state-dir', 'state']
                with patch.object(sys, 'argv', argv), \
                     patch.object(watch, 'cycle', side_effect=OSError(errno.ENOSPC, 'No space left on device')), \
                     contextlib.redirect_stdout(io.StringIO()):
                    watch.main()
                status = json.loads(Path('state/auto_monitor_status.json').read_text())
                self.assertEqual(status['action'], 'waiting_result_storage')
                self.assertTrue(Path('state/auto_monitor_events.jsonl').exists())
            finally:
                os.chdir(prior)

    def test_waiting_validation_and_validated_cells_are_never_resubmitted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registered = root / 'registered.json'
            registered.write_text(json.dumps({'cells': [{'canonical_summary': 'a/summary.json'}]}))
            (root / 'b').mkdir()
            (root / 'b/complete.txt').write_text('passed')
            group = {'prerequisite': '', 'cells': [{'canonical_summary': f'{x}/summary.json'} for x in 'abc']}
            result = unregistered_groups([group], [{'plan': str(registered)}], root, {})
            self.assertEqual(result[0]['cells'], [{'canonical_summary': 'c/summary.json'}])

    def test_512_requires_successful_independent_validation(self):
        group = {'required_job': 'proof', 'prerequisite': '', 'cells': [{'canonical_summary': 'c/summary.json'}]}
        with tempfile.TemporaryDirectory() as folder:
            for record in ({'job_state': 'Q'}, {'job_state': 'F', 'Exit_status': 1}):
                self.assertEqual(unregistered_groups([group], [], Path(folder), {'proof': record}), [])
            self.assertEqual(len(unregistered_groups([group], [], Path(folder), {'proof': {'job_state': 'F', 'Exit_status': 0}})), 1)

    def check_budget(self, deferred=False, user_hold=False):
        prior = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                root = Path('results/updated_vanda_scaling/test')
                root.mkdir(parents=True)
                groups = [{'graph': str(i), 'nodes': 1, 'cores_per_node': 32, 'cores': 32,
                           'prerequisite': '', 'walltime': '00:20:00',
                           'cells': [{'canonical_summary': f'{i}/summary.json'}]} for i in range(7)]
                Path('plan.json').write_text(json.dumps(groups))
                queued = {'project': 'personal-test', 'queue': 'batch_cpu', 'job_state': 'Q',
                          'Resource_List': {'ncpus': 512, 'walltime': '01:00:00'}}
                if user_hold:
                    queued.update(job_state='H', Hold_Types='u')

                def fake_run(*parts):
                    if parts[0] == 'qstat':
                        return json.dumps({'Jobs': {'queued': queued}})
                    return 'personal-test | 10000 | 642.130 | 1000 | 1000'

                argv = ['submit', 'test', 'personal-test', 'plan.json', '--dependency', 'proof', '--margin', '64']
                if deferred:
                    argv += ['--defer-held-job', 'queued']
                with patch.object(sys, 'argv', argv), patch.object(submit, 'run', fake_run), \
                     patch.object(submit.subprocess, 'run', return_value=SimpleNamespace(stdout='queued')), \
                     contextlib.redirect_stdout(io.StringIO()):
                    submit.main()
                record = next(root.glob('core_group_last_check_*.json'))
                summary = json.loads(record.read_text())
                return summary
            finally:
                os.chdir(prior)

    def test_queued_512_budget_is_reserved_without_using_future_refunds(self):
        summary = self.check_budget()
        self.assertEqual(len(summary['groups']), 6)
        self.assertAlmostEqual(summary['prior_pending_reservations'], 512)
        self.assertAlmostEqual(summary['new_reservations'], 64)
        self.assertAlmostEqual(summary['uncommitted_after_margin'], 2.13)

    def test_deferral_does_not_ignore_a_job_that_is_still_queued(self):
        summary = self.check_budget(deferred=True)
        self.assertAlmostEqual(summary['prior_pending_reservations'], 512)
        self.assertEqual(summary['deferred_user_held_jobs'], [])

    def test_confirmed_user_hold_releases_512_reservation_for_non512_work(self):
        summary = self.check_budget(deferred=True, user_hold=True)
        self.assertAlmostEqual(summary['prior_pending_reservations'], 0)
        self.assertEqual(summary['deferred_user_held_jobs'], ['queued'])
        self.assertEqual(len(summary['groups']), 7)


if __name__ == '__main__':
    unittest.main()
