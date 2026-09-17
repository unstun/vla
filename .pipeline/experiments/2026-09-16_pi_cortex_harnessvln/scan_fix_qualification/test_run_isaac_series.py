"""Failure-path tests for run_isaac_series.py. Every subprocess call is mocked; nothing contacts a host."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('test_run_isaac_series_module', str(HERE / 'run_isaac_series.py'))
ris = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ris)

IDLE = {'ok': True, 'gpu_memory_used_mib': ['202'], 'compute_apps': [], 'containers': [], 'ports_in_use': []}
PROBE_OK = ('202, 0\n---\n---\n---\n'
            'LISTEN 0      4096       127.0.0.53%lo:53        0.0.0.0:*\n'
            'LISTEN 0      128              0.0.0.0:18765     0.0.0.0:*\n'
            'LISTEN 0      128                 [::]:22           [::]:*\n')


class ProbeParseTest(unittest.TestCase):
    def test_idle_host(self):
        state = ris.parse_probe(PROBE_OK)
        self.assertTrue(state['ok'])
        self.assertEqual(state['gpu_memory_used_mib'], ['202'])
        self.assertEqual(state['gpu_utilization_percent'], ['0'])
        self.assertEqual(state['ports_in_use'], [])

    def test_busy_ports_containers_and_apps(self):
        text = ('7000, 95\n---\n1234, python\n---\nbackend_x\n---\n'
                'LISTEN 0 128 0.0.0.0:8765 0.0.0.0:*\n'
                'LISTEN 0 128 [::]:47631 [::]:*\n')
        state = ris.parse_probe(text)
        self.assertFalse(state['ok'])
        self.assertEqual(state['ports_in_use'], [':8765', ':47631'])
        self.assertEqual(state['compute_apps'], ['1234, python'])
        self.assertEqual(state['containers'], ['backend_x'])

    def test_malformed_or_empty_gpu_section_is_not_idle(self):
        self.assertIsNone(ris.parse_probe('202, 0\n---\n---\n'))
        self.assertFalse(ris.parse_probe('---\n---\n---\n')['ok'])

    def test_probe_fails_closed(self):
        self.assertTrue(ris.HOST_PROBE.startswith('set -e;'))

    def test_host_state_never_raises(self):
        failed = subprocess.CompletedProcess([], 127, stdout='202, 0\n---\n---\n', stderr='podman: not found')
        with mock.patch.object(ris.subprocess, 'run', return_value=failed):
            state = ris.host_state()
        self.assertFalse(state['ok'])
        self.assertIn('podman', state['error'])
        with mock.patch.object(ris.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['ssh'], 60)):
            self.assertFalse(ris.host_state()['ok'])
        with mock.patch.object(ris.subprocess, 'run', side_effect=OSError('ssh missing')):
            self.assertFalse(ris.host_state()['ok'])


class EpisodeLedgerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / 'ledger.jsonl'

    def lines(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def test_host_not_idle_writes_a_line(self):
        with mock.patch.object(ris, 'host_state', return_value={'ok': False, 'error': 'x'}) as probe:
            self.assertFalse(ris.run_episode(4, 0.4, self.ledger))
        self.assertEqual(probe.call_count, 1)
        (line,) = self.lines()
        self.assertEqual(line['outcome'], 'host_not_idle')
        self.assertNotIn('host_after', line)

    def test_launcher_timeout_writes_a_line_with_host_after(self):
        done = subprocess.CompletedProcess([], 0, stdout='prepared', stderr='')
        timeout = subprocess.TimeoutExpired(['launcher'], ris.STEP_TIMEOUT_S, output=b'partial out', stderr=b'err')
        with mock.patch.object(ris, 'host_state', side_effect=[IDLE, {'ok': False, 'containers': ['left_over']}]), \
                mock.patch.object(ris.subprocess, 'run', side_effect=[done, timeout]):
            self.assertFalse(ris.run_episode(5, 0.4, self.ledger))
        (line,) = self.lines()
        self.assertEqual(line['outcome'], 'execute_timeout')
        self.assertTrue(line['execute']['timed_out'])
        self.assertIn('partial out', line['execute']['tail'])
        self.assertEqual(line['host_after']['containers'], ['left_over'])
        self.assertIn('finished_utc', line)

    def test_launcher_failure_writes_a_line(self):
        failed = subprocess.CompletedProcess([], 1, stdout='', stderr='refused')
        with mock.patch.object(ris, 'host_state', side_effect=[IDLE, IDLE]), \
                mock.patch.object(ris.subprocess, 'run', return_value=failed):
            self.assertFalse(ris.run_episode(6, 0.4, self.ledger))
        (line,) = self.lines()
        self.assertEqual(line['outcome'], 'prepare_failed')
        self.assertEqual(line['prepare']['tail'], 'refused')
        self.assertNotIn('execute', line)

    def test_any_review_error_writes_a_line(self):
        done = subprocess.CompletedProcess([], 0, stdout='', stderr='')
        with mock.patch.object(ris, 'host_state', side_effect=[IDLE, IDLE]), \
                mock.patch.object(ris.subprocess, 'run', return_value=done), \
                mock.patch.object(ris, 'summarize', side_effect=IndexError('no terminals')):
            self.assertFalse(ris.run_episode(7, 0.45, self.ledger))
        (line,) = self.lines()
        self.assertEqual(line['outcome'], 'review_error')
        self.assertIn('IndexError', line['review_error'])
        self.assertIn('host_after', line)

    def test_passing_episode_has_no_host_after(self):
        done = subprocess.CompletedProcess([], 0, stdout='', stderr='')

        def passed(run_id, record):
            record['outcome'] = 'passed'
            return True

        with mock.patch.object(ris, 'host_state', return_value=IDLE) as probe, \
                mock.patch.object(ris.subprocess, 'run', return_value=done) as run, \
                mock.patch.object(ris, 'summarize', side_effect=passed):
            self.assertTrue(ris.run_episode(8, 0.5, self.ledger))
        self.assertEqual(probe.call_count, 1)
        (line,) = self.lines()
        self.assertEqual(line['outcome'], 'passed')
        self.assertNotIn('host_after', line)
        prepare, execute = (c.args[0] for c in run.call_args_list)
        self.assertNotIn('--execute', prepare)
        self.assertEqual(execute[-2:], ['--execute', '--lead-authorized-execute'])
        for command in (prepare, execute):
            self.assertIn('--remote-only-bulk', command)
            self.assertEqual(command[command.index('--cancel-displacement-m') + 1], '0.50')

    def test_plan_matches_prd_d12(self):
        self.assertEqual([1] + [i for i, _ in ris.PLAN], list(range(1, 9)))
        triggers = [0.40] + [m for _, m in ris.PLAN]
        self.assertEqual(sorted(triggers).count(0.40), 6)
        self.assertEqual(triggers[-2:], [0.45, 0.50])


if __name__ == '__main__':
    unittest.main()
