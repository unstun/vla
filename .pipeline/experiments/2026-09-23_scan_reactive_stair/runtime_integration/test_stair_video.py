"""Regression checks for immutable inputs and fail-closed runtime readiness."""
import ast
import json
import os
from pathlib import Path
import tempfile
import time
import types
import unittest
import yaml

import run_stair_video as launcher


class StairVideoTests(unittest.TestCase):
    def test_walk_requires_measured_settling_without_zeroing_state(self):
        namespace = {"__name__": "stair_start_test"}
        code = launcher.two.pilot_driver_source().split("def main():", 1)[0]
        code += (launcher.HERE / "stair_driver_body.py").read_text()
        exec(compile(code, "driver", "exec"), namespace)
        ready = namespace["snapshot_ready_to_walk"]
        base = {"sim_time_s": 5.0, "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
                "measured": {"horizontal_speed_mps": 0.001, "yaw_rate_radps": 0.002}}
        before = json.dumps(base, sort_keys=True)
        self.assertTrue(ready(base))
        self.assertEqual(before, json.dumps(base, sort_keys=True))
        self.assertFalse(ready({**base, "sim_time_s": 1.7}))
        for values in ({"horizontal_speed_mps": 0.023}, {"yaw_rate_radps": 0.04},
                       {"horizontal_speed_mps": float("nan")}):
            self.assertFalse(ready({**base, "measured": {**base["measured"], **values}}))

    def test_generated_ros_yaml_preserves_two_height_contracts(self):
        original = (launcher.OLD / "p2b_execution/baseline_config/planner.yaml").read_text()
        result = launcher.planner_with_clearance(original, 0.35)
        parameters = yaml.safe_load(result)["scan_planner_node"]["ros__parameters"]
        self.assertEqual(parameters["grid_map.body_height"], 0.0)
        self.assertEqual(parameters["grid_map.reactive_body_clearance"], 0.35)
        old_bad = launcher.two._insert_ros_parameter(original, "    grid_map.reactive_body_clearance: 0.35")
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load(old_bad)

    def test_package_override_does_not_mutate_hardlinked_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Path(folder) / "baseline.json"
            package = Path(folder) / "package.json"
            original.write_text('{"value":"frozen"}\n')
            os.link(original, package)
            launcher.write(package, {"value": "candidate"})
            self.assertEqual(json.loads(original.read_text()), {"value": "frozen"})
            self.assertNotEqual(original.stat().st_ino, package.stat().st_ino)

    def test_sensor_readiness_rejects_missing_stale_incomplete_and_wrong_epoch(self):
        namespace = {"__name__": "stair_driver_test"}
        code = launcher.two.pilot_driver_source().split("def main():", 1)[0]
        code += (launcher.HERE / "stair_driver_body.py").read_text()
        exec(compile(code, "driver", "exec"), namespace)
        ready = namespace["health_ready"]
        base = {"run_id": "r", "run_epoch_ns": 10, "wall_monotonic_ns": time.monotonic_ns(),
                "stamps_ns": {"clock": 2_000_000_000, "cloud": 1_950_000_000,
                              "lidar_pose": 1_950_000_000, "pct_tomogram": 1,
                              "tracked_person_snapshot": 1_950_000_000},
                "tracks_complete": True, "track_source_id": "sensor_lidar_moving_cluster_candidate_v2"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "health.json"
            self.assertFalse(ready(path, "r", 10))
            path.write_text(json.dumps(base))
            self.assertTrue(ready(path, "r", 10))
            source_v3 = "sensor_lidar_static_background_cluster_v3"
            self.assertFalse(ready(path, "r", 10, source_v3))
            upgraded = {**base, "track_source_id": source_v3}
            path.write_text(json.dumps(upgraded))
            self.assertFalse(ready(path, "r", 10, source_v3))
            upgraded["stamps_ns"] = {**base["stamps_ns"], "tracker_ground": 1}
            path.write_text(json.dumps(upgraded))
            self.assertTrue(ready(path, "r", 10, source_v3))
            self.assertFalse(ready(path, "r", 10))
            for change in ({"run_epoch_ns": 11}, {"tracks_complete": False},
                           {"wall_monotonic_ns": 1}, {"track_source_id": "actor_truth"},
                           {"stamps_ns": {**base["stamps_ns"], "cloud": 1}},
                           {"stamps_ns": {**base["stamps_ns"], "tracked_person_snapshot": 3_000_000_000}}):
                path.write_text(json.dumps({**base, **change}))
                self.assertFalse(ready(path, "r", 10), change)

    def test_generated_worker_and_driver_compile(self):
        source = launcher.worker_source()
        ast.parse(source)
        self.assertIn('wait -n "$scan_pid"', source)
        self.assertIn('required runtime process exited', source)
        self.assertIn('pct_sim_clock_publisher.py', source)
        self.assertIn('moving_cluster_tracker', source)
        self.assertTrue(launcher.two.verify_input_manifest()["files"])
        upgraded = launcher.worker_source(True)
        ast.parse(upgraded)
        self.assertIn('wait -n "$support_pid" "$worker_pid" "$tracking_ground_pid"', upgraded)
        self.assertIn('static_background_pcd:=/qualification/inputs/static_background/building2_9.pcd', upgraded)
        self.assertIn('ground_mode:=tracking_physical', upgraded)
        self.assertIn('unpack_foreground_dependency.py', upgraded)

    def test_v3_tracker_input_paths_have_a_readonly_container_mount(self):
        tree = ast.parse(launcher.worker_source(True))
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
                          any(isinstance(t, ast.Name) and t.id == "backend_cmd" for t in n.targets))
        root = Path("/fixture/immutable_run")
        values = {"run_root": root, "logs": root / "artifacts/logs", "scan_ws": Path("/fixture/scan22"),
                  "backend_container": "fixture", "backend_script": "fixture shell",
                  "args": types.SimpleNamespace(ros_domain_id=215, foxy_image_id="fixture-image")}
        command = eval(compile(ast.Expression(assignment.value), "backend_cmd", "eval"), values)
        mounts = [command[i + 1].split(":") for i, token in enumerate(command[:-1]) if token == "-v"]
        self.assertIn([str(root), "/qualification", "ro"], mounts)
        for path in ("/qualification/inputs/static_background/unpack_foreground_dependency.py",
                     "/qualification/inputs/static_background/scipy.whl",
                     "/qualification/inputs/static_background/building2_9.pcd"):
            self.assertTrue(any(path.startswith(target + "/") for _, target, _ in mounts))


if __name__ == "__main__":
    unittest.main()
