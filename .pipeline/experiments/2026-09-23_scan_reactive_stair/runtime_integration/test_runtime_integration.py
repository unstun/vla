from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(result)
    return result


prepare = module("prepare_reactive_runtime", HERE / "prepare_runtime.py")
driver = module("single_goal_driver", HERE / "single_goal_driver.py")


class RuntimeIntegrationTest(unittest.TestCase):
    def test_current_gate_fails_closed_without_route_or_first_hit(self):
        gate = prepare.gate_report()
        self.assertFalse(gate["passed"])
        self.assertTrue(any("APPROVED_ROUTE_SHA256" in error for error in gate["errors"]))
        self.assertTrue(any("first-hit" in error for error in gate["errors"]))
        self.assertTrue(any("start separation" in error for error in gate["errors"]))

    def test_prepared_package_is_local_and_non_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review"
            status = prepare.prepare(output, "review")
            self.assertEqual(status["status"], "prepared_overlay_execution_blocked")
            self.assertFalse(status["execution_allowed"])
            self.assertIn("use_sim_time: true", (output / "config/planner.yaml").read_text())
            self.assertIn("grid_map.cloud_is_world: false", (output / "config/planner.yaml").read_text())
            self.assertEqual(json.loads((output / "inputs/single_goal.json").read_text())["spawn_ground_xyz_m"], None)
            manifest = json.loads((output / "source_manifest.json").read_text())
            for relative, expected in manifest["files"].items():
                self.assertEqual(prepare.digest(output / relative), expected)
            with self.assertRaisesRegex(RuntimeError, "package execution gates"):
                driver.verify_package(output, "review")

    def test_driver_rejects_initial_overlap_even_with_synthetic_approved_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver.write(root / "execution_gate.json", {"passed": True})
            driver.write(root / "package_status.json", {"run_id": "test", "execution_allowed": True})
            driver.write(root / "inputs/single_goal.json", {
                "status": "reviewed_stair_goal", "frame_id": "world", "goal_ground_xyz_m": [-5.3, 1.3, 0.86],
                "spawn_ground_xyz_m": [-5.3, 2.0, 0.74],
            })
            driver.write(root / "inputs/actor_route.proposed.json", {
                "geometry_reviewed": True,
                "official_human": {"waypoints_ground_xyz_m": [[-5.3, 1.4, 0.74]]}
            })
            route_sha = prepare.digest(root / "inputs/actor_route.proposed.json")
            (root / "runner").mkdir()
            (root / "runner/official_building_human.py").write_text(
                f'APPROVED_ROUTE_SHA256 = "{route_sha}"\n')
            driver.write(root / "evidence/first_hit_result.json", {"passed": True})
            driver.write(root / "evidence/scan_build_result.json", {
                "passed": True, "source_matches_before_after": True})
            files = {path.relative_to(root).as_posix(): prepare.digest(path)
                     for path in root.rglob("*") if path.is_file()}
            driver.write(root / "source_manifest.json", {"files": files})
            with self.assertRaisesRegex(RuntimeError, "initial robot/person separation"):
                driver.verify_package(root, "test")

    def test_runtime_health_requires_current_sensor_stamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            driver.write(path, {"run_id": "test", "run_epoch_ns": 1, "wall_monotonic_ns": 0})
            with self.assertRaisesRegex(RuntimeError, "runtime health stale"):
                driver.runtime_health(path, "test", 1)

    def test_runtime_health_rejects_old_track_with_fresh_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            driver.write(path, {
                "run_id": "test", "run_epoch_ns": 1, "wall_monotonic_ns": time.monotonic_ns(),
                "clock_advancing": True, "sidecar_alive": True, "tracker_alive": True,
                "scan_alive": True, "pct_socket_worker_alive": True,
                "pct_tomogram_publisher_count": 1, "track_source": "sensor_lidar_current_only",
                "track_snapshot_complete": True, "ros_domain_id": 192, "tracked_person_count": 1,
                "stamps_ns": {"clock": 3_000_000_000, "pct_tomogram": 1_000_000_000,
                              "cloud": 3_000_000_000, "lidar_pose": 3_000_000_000,
                              "tracked_person_snapshot": 2_000_000_000},
            })
            with self.assertRaisesRegex(RuntimeError, "current track snapshot is stale"):
                driver.runtime_health(path, "test", 1)

    def test_runtime_health_accepts_complete_empty_current_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            health = {
                "run_id": "test", "run_epoch_ns": 1, "wall_monotonic_ns": time.monotonic_ns(),
                "clock_advancing": True, "sidecar_alive": True, "tracker_alive": True,
                "scan_alive": True, "pct_socket_worker_alive": True,
                "pct_tomogram_publisher_count": 1, "track_source": "sensor_lidar_current_only",
                "track_snapshot_complete": True, "ros_domain_id": 192, "tracked_person_count": 0,
                "stamps_ns": {"clock": 3_000_000_000, "pct_tomogram": 1_000_000_000,
                              "cloud": 3_000_000_000, "lidar_pose": 3_000_000_000,
                              "tracked_person_snapshot": 3_000_000_000},
            }
            driver.write(path, health)
            self.assertEqual(driver.runtime_health(path, "test", 1)["tracked_person_count"], 0)

    def test_deadline_cancel_and_stillness_is_not_avoidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            goal = {
                "goal_id": "stair-goal", "goal_ground_xyz_m": [0.0, 0.0, 0.0],
                "frame_id": "world", "map_epoch": "stair_reactive", "map_revision": 1,
                "max_sim_seconds": 1.0, "max_wall_seconds": 1200.0,
                "stop_dwell_sim_seconds": 1.0, "stop_command_norm": 0.01,
                "stop_speed_mps": 0.1, "stop_yaw_rate_radps": 0.15,
            }
            def snapshot(sim_time):
                return {"run_epoch_ns": 1, "sim_time_s": sim_time,
                        "measured": {"base_xyz": [0.0, 0.0, 0.0],
                                     "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0},
                        "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}}
            snapshots = iter([snapshot(0.0), snapshot(1.0), snapshot(1.1), snapshot(2.2)])
            get_count = 0
            def backend_state(_base, _endpoint):
                nonlocal get_count
                get_count += 1
                if get_count == 1:
                    return {"run_id": "test", "run_epoch_ns": 1,
                            "readiness": {"body_pose_ready": True,
                                          "applied_snapshot": {"ready": True}}}
                return {"terminal_results": [] if get_count == 2 else [
                    {"request_id": "test-stair-goal", "status": "cancelled"}]}
            health = {"stamps_ns": {"tracked_person_snapshot": 1},
                      "tracked_person_count": 0}
            with (mock.patch.object(driver, "verify_package", return_value=goal),
                  mock.patch.object(driver, "fresh_snapshot", side_effect=lambda *_args: next(snapshots)),
                  mock.patch.object(driver, "runtime_health", return_value=health),
                  mock.patch.object(driver, "get", side_effect=backend_state),
                  mock.patch.object(driver, "post", return_value={"ok": True}),
                  mock.patch.object(driver.time, "sleep", return_value=None)):
                result = driver.drive(root, "test", 8765)
            self.assertEqual(result["outcome"], "DEADLINE_STOPPED")
            self.assertIn("unassessed", result["avoidance_assessment"])
            self.assertEqual(driver.read(root / "artifacts/external_episode/finish_request.json")
                             ["backend_terminal_status"], "FAILED")
            self.assertEqual(driver.terminal({"terminal_results": [
                {"request_id": "test-stair-goal", "status": "arrived"}]},
                "test-stair-goal"), "arrived")


if __name__ == "__main__":
    unittest.main()
