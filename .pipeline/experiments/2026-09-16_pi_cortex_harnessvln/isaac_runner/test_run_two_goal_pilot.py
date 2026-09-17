import importlib.util
import json
import subprocess
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "run_two_goal_pilot.py"
REAL_STAND_SNAPSHOT = HERE / "runs/stand_20260916T152235Z_p2b_fix1/returned_artifacts/external_episode/current_command.json"


def load_module():
    spec = importlib.util.spec_from_file_location("run_two_goal_pilot", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TwoGoalPilotPreparationTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_prepare_only_materializes_contract_and_keeps_execute_pending(self):
        scan_dir = Path(self.tmp.name) / "scan_03_identity"
        scan_dir.mkdir()
        (scan_dir / "build_result.json").write_text('{"passed": true}\n', encoding="utf-8")
        args = self.m.build_parser().parse_args([
            "--run-id", "two_goal_unittest",
            "--local-runs-root", self.tmp.name,
            "--accepted-scan-build-dir", str(scan_dir),
            "--remote-scan-workspace", "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03",
        ])
        local_run, commands = self.m.prepare(args)
        self.assertTrue((local_run / "remote_worker.py").exists())
        self.assertTrue((local_run / "pilot_driver.py").exists())
        self.assertTrue((local_run / "RUNBOOK.md").read_text(encoding="utf-8").startswith("# P2B two-goal pilot"))
        run_request = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))
        self.assertFalse(run_request["default_execute"])
        self.assertEqual(run_request["case"], "flat_nominal")
        self.assertEqual(run_request["duration_seconds"], 45.0)
        self.assertEqual(run_request["max_wall_seconds"], 1200.0)
        bridge_cfg = (local_run / "config/foxy_bridge_two_goal.yaml").read_text(encoding="utf-8")
        self.assertIn("max_vx: 1.0", bridge_cfg)
        self.assertIn("max_vy: 0.35", bridge_cfg)
        self.assertIn("max_wz: 1.0", bridge_cfg)
        self.assertIn("max_horizontal_command_norm: 1.0", bridge_cfg)
        planner_cfg = (local_run / "config/planner.yaml").read_text(encoding="utf-8")
        controller_cfg = (local_run / "config/controller.yaml").read_text(encoding="utf-8")
        self.assertIn("p2b_mode: true", planner_cfg)
        self.assertIn("p2b_mode: true", controller_cfg)
        source = json.loads((local_run / "source_env_hashes.json").read_text(encoding="utf-8"))
        self.assertIn("backend_ros", source)
        self.assertIn("backend_adapter", source)
        self.assertIn("navigation_service", source)
        self.assertEqual(source["accepted_scan_build_identity"]["local_path"], str(scan_dir))
        self.assertIn("scan_03", " ".join(commands["run"]))
        scope = json.loads((local_run / "inputs/two_goal_scope.json").read_text(encoding="utf-8"))
        self.assertEqual(scope["profile"], "diagnostic_simulator_truth_known_map_full_two_goal")
        self.assertIs(scope["execution_configuration"]["external_goal_mode"], True)
        self.assertEqual(scope["execution_configuration"]["speed_profile"], "speed_1p0")
        self.assertEqual(scope["execution_configuration"]["max_vx"], 1.0)
        self.assertEqual(scope["execution_configuration"]["max_vy"], 0.35)
        self.assertEqual(scope["execution_configuration"]["max_wz"], 1.0)
        self.assertEqual(scope["execution_configuration"]["max_horizontal_norm"], 1.0)
        route = json.loads((local_run / "inputs/two_goal_route_artifact.json").read_text(encoding="utf-8"))
        self.assertIn("not command", route["note"])
        self.assertIsInstance(route["statistics"]["arc_length_xy_m"], float)
        self.assertGreater(route["statistics"]["arc_length_xy_m"], 3.0)
        self.assertIsInstance(scope["platform_segment"]["arc_length_xy_m"], float)

    def test_execute_refuses_without_lead_gate_before_remote_commands(self):
        local_run = Path(self.tmp.name) / "prepared"
        local_run.mkdir()
        (local_run / "source_env_hashes.json").write_text('{"accepted_scan_build_identity": {}}\n', encoding="utf-8")
        args = self.m.build_parser().parse_args(["--execute", "--run-id", "prepared", "--local-runs-root", self.tmp.name])
        with self.assertRaisesRegex(RuntimeError, "lead-authorized"):
            self.m.execute(args, local_run, {"mkdir": ["false"]})

    def test_remote_worker_sequence_uses_runner_epoch_before_backend_and_no_duplicate_bridge(self):
        src = self.m.remote_worker_source()
        self.assertLess(src.index("first_snapshot = wait_snapshot"), src.index("backend_cfg[\"run_epoch_ns\"] = run_epoch_ns"))
        self.assertLess(src.index("bridge_cmd ="), src.index("runner_cmd ="))
        self.assertLess(src.index("runner_cmd ="), src.index("pct_cmd ="))
        self.assertLess(src.index("pct_cmd ="), src.index("backend_cmd ="))
        self.assertNotIn("reference_path_publisher", src)
        self.assertIn("/qualification/backend_adapter:/qualification/pct_runtime/python", src)
        self.assertIn("runner_runtime_error_before_snapshot", src)
        self.assertIn("python3 -m p2b_backend_ros.node", src)
        self.assertIn(":/navigation_service:ro", src)
        self.assertIn("source /workspace/install/setup.bash", src)
        self.assertIn("-r body_pose:=/quad_0/body_pose > /logs/closed_loop_controller.log", src)
        self.assertNotIn("& &&", src)



    def test_remote_worker_wait_snapshot_detects_runner_exit_without_runtime_error(self):
        source = self.m.remote_worker_source()
        module = types.ModuleType("remote_worker_wait_snapshot_test")
        exec(compile(source, "remote_worker_wait_snapshot_test.py", "exec"), module.__dict__)
        run_root = Path(self.tmp.name) / "run"
        snapshot = run_root / "artifacts/external_episode/current_command.json"
        snapshot.parent.mkdir(parents=True)

        class ExitedProc:
            def poll(self):
                return 7

        with self.assertRaisesRegex(RuntimeError, "runner_exited_before_snapshot: exit_code=7"):
            module.wait_snapshot(snapshot, "run", 0.0, timeout_s=5.0, runner_proc=ExitedProc())

    def test_remote_worker_cleanup_timeout_is_bounded_and_hashes_still_written(self):
        source = self.m.remote_worker_source()
        module = types.ModuleType("remote_worker_cleanup_test")
        exec(compile(source, "remote_worker_cleanup_test.py", "exec"), module.__dict__)
        artifacts = Path(self.tmp.name) / "artifacts"
        artifacts.mkdir()
        (artifacts / "kept.log").write_text("raw log survives\n", encoding="utf-8")

        real_run = module.subprocess.run
        def fake_run(cmd, *args, **kwargs):
            if cmd[:3] == ["podman", "rm", "-f"]:
                raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
            return real_run(cmd, *args, **kwargs)

        module.subprocess.run = fake_run
        try:
            cleanup = module.cleanup_container("vla-p2b-owned", timeout_s=0.01)
        finally:
            module.subprocess.run = real_run
        self.assertFalse(cleanup["ok"])
        self.assertTrue(cleanup["timeout"])
        result = {"passed": False, "error": "synthetic failure", "container_cleanup": [cleanup]}
        final = module.finalize_result_artifacts(artifacts, result, "after_container_cleanup")
        self.assertTrue(final["ok"])
        written = json.loads((artifacts / "result.json").read_text(encoding="utf-8"))
        hashes = json.loads((artifacts / "artifact_hashes.json").read_text(encoding="utf-8"))
        self.assertEqual(written["container_cleanup"][0]["error_type"], "TimeoutExpired")
        self.assertIn("kept.log", hashes)
        self.assertIn("result.json", hashes)

    def test_pilot_driver_accepts_real_stand_snapshot_schema_and_rejects_generic_http_ok(self):
        source = self.m.pilot_driver_source()
        module = types.ModuleType("pilot_driver_schema_test")
        exec(compile(source, "pilot_driver_schema_test.py", "exec"), module.__dict__)
        snapshot = json.loads(REAL_STAND_SNAPSHOT.read_text(encoding="utf-8"))
        snapshot["run_id"] = "schema-run"
        snapshot["wall_monotonic_ns"] = module.time.monotonic_ns()
        self.assertTrue(module.snapshot_ok(snapshot, "schema-run"))
        legacy = dict(snapshot)
        legacy.pop("applied_command")
        legacy["applied_cmd"] = {"vx": 0.0, "vy": 0.0, "wz": 0.0}
        self.assertFalse(module.snapshot_ok(legacy, "schema-run"))

        calls = {"count": 0}
        module.wait_snapshot = lambda *_args, **_kwargs: snapshot
        module.time.sleep = lambda _seconds: None
        def generic_state(_base, _endpoint):
            calls["count"] += 1
            if calls["count"] > 3:
                raise RuntimeError("stop-test")
            return {"ok": True, "readiness": {"http_ready": True}, "run_id": "schema-run", "run_epoch_ns": snapshot["run_epoch_ns"]}
        module.get_json = generic_state
        with self.assertRaisesRegex(RuntimeError, "HTTP backend not ready|stop-test"):
            module.wait_http_ready("http://127.0.0.1:8765", [], Path("unused"), "schema-run", snapshot["run_epoch_ns"], timeout_s=0.01)

    def test_pilot_driver_requires_cancel_two_arrivals_and_writes_finish(self):
        source = self.m.pilot_driver_source()
        module = types.ModuleType("pilot_driver_under_test")
        exec(compile(source, "pilot_driver_under_test.py", "exec"), module.__dict__)
        run_root = Path(self.tmp.name) / "driver_run"
        (run_root / "inputs").mkdir(parents=True)
        (run_root / "artifacts/external_episode").mkdir(parents=True)
        pilot = {
            "frame_id": "world",
            "stop_command_norm": 0.01,
            "stop_speed_mps": 0.1,
            "stop_yaw_rate_radps": 0.15,
            "stop_dwell_sim_seconds": 1.0,
            "goals": [
                {"goal_id": "goal-a", "ground_xyz_m": [0.0, 0.0, 0.0]},
                {"goal_id": "goal-b", "ground_xyz_m": [1.0, 0.0, 0.0]},
            ],
        }
        snapshots = [
            {"run_id": "runA", "run_epoch_ns": 123, "sim_time_s": 0.1, "wall_monotonic_ns": module.time.monotonic_ns(), "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}, "measured": {"base_xyz": [0.0, 0.0, 0.0], "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0}},
            {"run_id": "runA", "run_epoch_ns": 123, "sim_time_s": 0.2, "wall_monotonic_ns": module.time.monotonic_ns(), "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}, "measured": {"base_xyz": [0.5, 0.0, 0.0], "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0}},
            {"run_id": "runA", "run_epoch_ns": 123, "sim_time_s": 0.3, "wall_monotonic_ns": module.time.monotonic_ns(), "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}, "measured": {"base_xyz": [0.5, 0.0, 0.0], "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0}},
            {"run_id": "runA", "run_epoch_ns": 123, "sim_time_s": 1.4, "wall_monotonic_ns": module.time.monotonic_ns(), "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}, "measured": {"base_xyz": [0.5, 0.0, 0.0], "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0}},
            {"run_id": "runA", "run_epoch_ns": 123, "sim_time_s": 2.5, "wall_monotonic_ns": module.time.monotonic_ns(), "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0}, "measured": {"base_xyz": [0.5, 0.0, 0.0], "horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0}},
        ]
        posts = []
        state_polls = {"count": 0}

        def fake_read_json(path):
            path = Path(path)
            if path.name == "pilot.json":
                return pilot
            if path.name == "current_command.json":
                if len(snapshots) > 1:
                    snap = dict(snapshots.pop(0))
                else:
                    snapshots[0]["sim_time_s"] = float(snapshots[0]["sim_time_s"]) + 1.1
                    snap = dict(snapshots[0])
                snap["wall_monotonic_ns"] = module.time.monotonic_ns()
                return snap
            return json.loads(path.read_text(encoding="utf-8"))

        def fake_post_json(base, endpoint, payload):
            posts.append((endpoint, payload))
            return {"ok": True, "status": "accepted"}

        def fake_get_json(base, endpoint):
            state_polls["count"] += 1
            terminals = []
            if state_polls["count"] >= 2:
                terminals.append({"request_id": "runA-goal-a-attempt-1", "status": "cancelled"})
            if state_polls["count"] >= 3:
                terminals.append({"request_id": "runA-goal-a-attempt-2", "status": "arrived"})
            if state_polls["count"] >= 4:
                terminals.append({"request_id": "runA-goal-b", "status": "arrived"})
            return {"run_id": "runA", "run_epoch_ns": 123, "readiness": {"body_pose_ready": True, "applied_snapshot": {"configured": True, "ready": True}}, "measurement_body_pose": {"position_world_m": [0.0, 0.0, 0.0]}, "service": {"current_owner": None}, "terminal_results": terminals}

        module.read_json = fake_read_json
        module.post_json = fake_post_json
        module.get_json = fake_get_json
        module.time.sleep = lambda _seconds: None
        old_argv = sys.argv[:]
        try:
            sys.argv = ["pilot_driver.py", "--run-root", str(run_root), "--http-port", "8765", "--run-id", "runA"]
            rc = module.main()
        finally:
            sys.argv = old_argv
        self.assertEqual(rc, 0)
        self.assertEqual([p[0] for p in posts], ["/goal", "/cancel", "/goal", "/goal"])
        finish = json.loads((run_root / "artifacts/external_episode/finish_request.json").read_text(encoding="utf-8"))
        self.assertEqual(finish["backend_terminal_status"], "FINISHED")
        journal = json.loads((run_root / "artifacts/pilot_journal.json").read_text(encoding="utf-8"))
        self.assertTrue(journal["passed"])


if __name__ == "__main__":
    unittest.main()
