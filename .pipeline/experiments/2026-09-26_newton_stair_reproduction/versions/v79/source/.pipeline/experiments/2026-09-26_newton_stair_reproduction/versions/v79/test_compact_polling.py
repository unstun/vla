from pathlib import Path
from types import SimpleNamespace as NS
import ast
import json
import sys
import tempfile
import threading
import time
import unittest

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path[:0] = [str(HERE / 'backend_ros'), str(BASE / 'runtime_sources/backend_adapter')]
from p2b_backend_ros.plan_history import PlanHistory
from p2b_backend_ros.node import LayeredPctClient
from p2b_backend_ros.runtime import make_http_handler, start_http_server


class CompactPolling(unittest.TestCase):
    def test_full_records_once_and_bounded_summaries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.jsonl'
            history = PlanHistory(path, {'run_id': 'test', 'run_epoch_ns': 1})
            for i in range(65):
                history.append({'request_id': str(i), 'request': {'target': [1, 2, 3]},
                                'ok': i != 4, 'waypoints_m': [[i, 0, 0]] * 1500})
            compact = history.snapshot()
            full = history.snapshot(True)
            self.assertEqual(compact['plan_count'], 65)
            self.assertEqual(len(compact['plan_history']), 50)
            self.assertNotIn('waypoints_m', compact['plan_history'][0])
            self.assertNotIn('request', compact['plan_history'][0])
            self.assertEqual(compact['plan_history'][0]['waypoint_count'], 1500)
            self.assertEqual(full['plan_history'][0]['waypoints_m'], [[15, 0, 0]] * 1500)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 65)
            self.assertFalse(rows[4]['ok'])
            self.assertEqual(rows[4]['evidence_identity']['run_id'], 'test')
            self.assertEqual([row['history_seq'] for row in rows], list(range(1, 66)))
            with self.assertRaises(FileExistsError):
                PlanHistory(path)

    def test_layered_client_route_and_failure_unchanged(self):
        route = NS(route_id='route', waypoints_m=((1, 2, 3), (2, 3, 4)), planner='native', z_semantics='body')
        client = LayeredPctClient(NS(plan=lambda request: route), None)
        request = NS(request_id='req', goal_id='goal', to_wire=lambda: {'x': 1})
        self.assertIs(client.plan(request), route)
        self.assertEqual(client.snapshot(True)['plan_history'][0]['request'], {'x': 1})
        def fail(request):
            raise ValueError('original_failure')
        client.inner.plan = fail
        with self.assertRaisesRegex(ValueError, 'original_failure'):
            client.plan(request)
        self.assertEqual(client.snapshot()['plan_history'][-1]['error'], 'original_failure')

    def test_evidence_failure_explicit_without_changing_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.jsonl'
            history = PlanHistory(path)
            path.unlink()
            path.mkdir()
            history.append({'ok': True})
            self.assertIsNotNone(history.snapshot()['history_evidence']['error'])
            self.assertTrue(history.snapshot()['plan_history'][0]['ok'])

    def test_http_default_compact_explicit_full_and_not_found(self):
        import urllib.request
        from urllib.error import HTTPError
        calls = []
        def state(include_history=False):
            calls.append(include_history)
            return {'ok': True, 'full': include_history, 'gate': {'closed_reason': 'open'}}
        server = start_http_server(NS(state=state), '127.0.0.1', 0)
        root = 'http://127.0.0.1:%d' % server.server_address[1]
        try:
            for endpoint, expected in [('/state', False), ('/state?include_history=1', True),
                                       ('/state?include_history=0', False)]:
                with urllib.request.urlopen(root + endpoint) as response:
                    self.assertEqual(json.load(response)['full'], expected)
            with self.assertRaises(HTTPError):
                urllib.request.urlopen(root + '/other')
            self.assertEqual(calls, [False, True, False])
        finally:
            server.shutdown()
            server.server_close()

    def test_control_callback_and_stop_flow_asts_identical(self):
        for name in ('node.py', 'runtime.py'):
            before = ast.parse((BASE / 'versions/v59/backend_ros/p2b_backend_ros' / name).read_text())
            after = ast.parse((HERE / 'backend_ros/p2b_backend_ros' / name).read_text())
            def methods(tree):
                return {node.name: ast.dump(node, include_attributes=False)
                        for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
            old, new = methods(before), methods(after)
            selectors = ('_on_raw_command', '_on_body_pose', '_watchdog_tick', '_on_admission',
                         '_request_stop_flow', '_drive_stop_flow', '_finish_stop_flow', '_monitor_arrival')
            for method in selectors:
                if method in old:
                    self.assertEqual(old[method], new[method], method)

    def test_concurrent_polling_and_evidence_append(self):
        history = PlanHistory()
        def write():
            for i in range(200):
                history.append({'request_id': str(i), 'waypoints_m': [[i, 0, 0]] * 100})
        thread = threading.Thread(target=write)
        thread.start()
        while thread.is_alive():
            snapshot = history.snapshot()
            sequences = [row['history_seq'] for row in snapshot['plan_history']]
            self.assertEqual(sequences, sorted(set(sequences)))
            self.assertLessEqual(len(sequences), 50)
        thread.join()
        self.assertEqual(history.snapshot()['plan_count'], 200)


if __name__ == '__main__':
    unittest.main()
