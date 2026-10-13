"""Require the original spatial start and goal, not a zero-clock corner run."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
from run_local_episode import building_scenario

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


class FullRouteTests(unittest.TestCase):
    def test_selector_preserves_original_start_yaw_and_goal(self):
        path = BASE / 'inputs/historical_full_building.json'
        original = json.loads(path.read_text())
        identity = json.loads((HERE / 'full_route_input.json').read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), identity['source_sha256'])
        selected = building_scenario('historical_full', 1500.0)
        for key in ['spawn_ground_xyz_m', 'spawn_yaw_rad', 'goal_ground_xyz_m']:
            self.assertEqual(selected[key], original[key])
            self.assertEqual(identity[key], original[key])
        self.assertEqual(selected['max_sim_seconds'], 600.0)
        self.assertEqual(selected['max_wall_seconds'], 1500.0)
        corner = building_scenario('corner_start', 180.0)
        self.assertNotEqual(selected['spawn_ground_xyz_m'], corner['spawn_ground_xyz_m'])

    def test_actual_launcher_requests_full_profile_and_recording(self):
        tree = ast.parse((HERE / 'run_mac_full.py').read_text())
        episode = next(node.value for node in ast.walk(tree)
                       if isinstance(node, ast.Assign) and any(
                           isinstance(t, ast.Name) and t.id == 'episode' for t in node.targets))
        values = [node.value if isinstance(node, ast.Constant) else None for node in episode.elts]
        self.assertEqual(values[values.index('--building-route') + 1], 'historical_full')
        self.assertEqual(values[values.index('--recording-sim-seconds') + 1], '600')
        self.assertEqual(values[values.index('--goal-wall-budget') + 1], '1500')
        self.assertEqual(values[values.index('--integration-version') + 1], 'v184')


if __name__ == '__main__':
    unittest.main()
