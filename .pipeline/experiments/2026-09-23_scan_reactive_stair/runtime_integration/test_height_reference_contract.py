import ast
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import height_reference_contract as contract
import run_stair_video as launcher


def config(spawn=.35, target=.30):
    return types.SimpleNamespace(
        scene=types.SimpleNamespace(robot=types.SimpleNamespace(init_state=types.SimpleNamespace(pos=(0., 0., spawn)))),
        rewards=types.SimpleNamespace(base_height_l2=types.SimpleNamespace(params={"target_height": target})))


class HeightContractTests(unittest.TestCase):
    def test_spawn_reference_and_loaded_source_are_independently_validated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.py"
            path.write_text("pinned fixture\n")
            hashes = {"source.py": hashlib.sha256(path.read_bytes()).hexdigest()}
            with patch.object(contract, "PINNED_SOURCES", hashes):
                result = contract.verify_runtime_height_contract(config(), folder, .35, .30)
                self.assertEqual(result["registry_reward_target_height_m"], .30)
                self.assertEqual(result["registry_default_base_position_m"], [0., 0., .35])
                for cfg, spawn, ref in ((config(), .30, .30), (config(), .35, .35),
                                        (config(target=.35), .35, .30), (config(spawn=.30), .35, .30)):
                    with self.assertRaises(ValueError):
                        contract.verify_runtime_height_contract(cfg, folder, spawn, ref)
                path.write_text("changed source\n")
                with self.assertRaises(ValueError):
                    contract.verify_runtime_height_contract(config(), folder, .35, .30)

    def test_candidate_splits_spawn_and_metric_but_keeps_old_default_source(self):
        route = launcher.HERE / "prepared/stair_actor_right065/actor_route.json"
        with tempfile.TemporaryDirectory() as folder:
            old, new = Path(folder) / "legacy", Path(folder) / "separated"
            launcher.materializer.materialize(old, route)
            launcher.materializer.materialize(new, route, True)
            before = (old / "run_pct_scan_building.py").read_text()
            after = (new / "run_pct_scan_building.py").read_text()
            ast.parse(after)
            self.assertIn('body_height = float(segment["nominal_body_height_m"])', before)
            self.assertIn('body_height = float(segment["spawn_body_height_m"])', after)
            self.assertIn('float(start_ground[2] + body_height)', after)
            self.assertIn('abs((position[2] - locomotion_reference_height) - goal_ground[2])', after)
            self.assertIn('contract["height_reference_contract"] = verify_runtime_height_contract', after)
            self.assertTrue((new / "height_reference_contract.py").is_file())
            self.assertNotIn('locomotion_reference_height', before)

    def test_pct_source_and_scan_offset_use_reference_without_changing_route_offset(self):
        old = launcher.worker_source(True)
        new = launcher.worker_source(True, True)
        self.assertIn('--reference-height-m 0.35 &', old)
        self.assertIn('--reference-height-m 0.30 &', new)
        self.assertNotIn('--reference-height-m 0.35 &', new)
        text = (launcher.OLD / "p2b_execution/baseline_config/planner.yaml").read_text()
        import yaml
        params = yaml.safe_load(launcher.planner_with_clearance(text, .30))["scan_planner_node"]["ros__parameters"]
        self.assertEqual(params["grid_map.body_height"], 0.)
        self.assertEqual(params["grid_map.reactive_body_clearance"], .30)


if __name__ == "__main__":
    unittest.main()
