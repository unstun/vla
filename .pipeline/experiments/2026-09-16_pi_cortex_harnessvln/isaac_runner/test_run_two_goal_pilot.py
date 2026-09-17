import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "run_two_goal_pilot.py"
REAL_STAND_SNAPSHOT = HERE / "runs/stand_20260916T152235Z_p2b_fix1/returned_artifacts/external_episode/current_command.json"
ACTUAL4 = HERE / "two_goal_runs/two_goal_20260916T162236Z_p2b_actual4"
SCAN_03 = HERE.parent / "p2b_execution/builds/scan_03"
SCAN_03_REMOTE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03"
NEW_RUN_REQUEST_FIELDS = {"cancel_displacement_m", "cancel_trigger_check", "allow_missing_install_identity", "scan_workspace_gate", "resource_recording",
                          "remote_only_bulk", "remote_only_bulk_detail", "package_storage", "stance_hold"}
# Runner bytes executed by actual4 (external-episode anchors only); see materialize_runner_patch.py.
ACTUAL4_RUNNER_SHA256 = "e215a6014bf15dc22a3261cb97c3435252b83ce2bde2f042375ae313493470f3"
RUNNER_REL = "lite3_sim_bridge/run_pct_scan_building.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_two_goal_pilot", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_scan_build(root, remote_workspace, with_install_identity=True):
    """Synthetic accepted build dir plus a matching 'remote' workspace tree."""
    build = Path(root)
    for rel, text in {"src/pkg/a.cpp": "int a;\r\n", "src/pkg/CMakeLists.txt": "project(pkg)\n"}.items():
        (build / rel).parent.mkdir(parents=True, exist_ok=True)
        (build / rel).write_text(text, encoding="utf-8")
    sources = {p.relative_to(build).as_posix(): digest(p) for p in (build / "src").rglob("*") if p.is_file()}
    (build / "source_sha256.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    (build / "build_result.json").write_text(json.dumps({"passed": True, "remote_workspace": remote_workspace}) + "\n", encoding="utf-8")
    (build / "install/pkg/lib").mkdir(parents=True)
    (build / "install/pkg/lib/libpkg.a").write_bytes(b"\x00lib")
    (build / "install/setup.bash").write_text("# setup\n", encoding="utf-8")
    (build / "install/pkg/lib/python3.8/site-packages/pkg/__pycache__").mkdir(parents=True)
    (build / "install/pkg/lib/python3.8/site-packages/pkg/__pycache__/__init__.cpython-38.pyc").write_bytes(b"pyc")
    installed = {p.relative_to(build).as_posix(): digest(p) for p in (build / "install").rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts}
    if with_install_identity:
        identity = {"installed_files": installed, "source_file_count": len(sources), "source_matches": True,
                    "remote_workspace": remote_workspace, "image_id": "image"}
        (build / "install_identity.json").write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    return build


class TwoGoalPilotPreparationTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_prepare_only_materializes_contract_and_keeps_execute_pending(self):
        scan_dir = make_scan_build(
            Path(self.tmp.name) / "scan_03_identity",
            "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03",
        )
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
        cancel = [e for e in journal["events"] if e.get("event") == "post_cancel"][0]
        self.assertEqual(cancel["cancel_displacement_m"], 0.4)


class ScanGateCancelAndResourceTests(unittest.TestCase):
    remote = "/remote/p2b/builds/scan_test"

    def setUp(self):
        self.m = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        worker = types.ModuleType("remote_worker_gate_test")
        exec(compile(self.m.remote_worker_source(), "remote_worker_gate_test.py", "exec"), worker.__dict__)
        self.worker = worker
        self.pilot = json.loads((self.m.P2B / "inputs/pilot.json").read_text(encoding="utf-8"))

    def identity_for(self, build, allow_missing=False):
        gate = self.m.build_scan_workspace_gate(build, None, allow_missing)
        path = build / "install_identity.json"
        return {"install_identity": json.loads(path.read_text(encoding="utf-8")) if path.exists() else None,
                "workspace_gate": gate}

    def gates(self, workspace, identity):
        local = self.m.scan_workspace_gate(workspace, identity)
        remote = self.worker.scan_workspace_gate(workspace, identity)
        self.assertEqual(local, remote)
        return local

    def test_workspace_gate_passes_matching_tree_and_lists_bytecode(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", str(Path(self.tmp.name) / "ws"))
        record = self.gates(build, self.identity_for(build))
        self.assertTrue(record["passed"], record)
        self.assertTrue(record["install_checked"])
        self.assertEqual(record["install"]["excluded"], ["install/pkg/lib/python3.8/site-packages/pkg/__pycache__/__init__.cpython-38.pyc"])

    def test_workspace_gate_refuses_changed_extra_or_missing_files(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", str(Path(self.tmp.name) / "ws"))
        identity = self.identity_for(build)
        (build / "install/pkg/lib/libpkg.a").write_bytes(b"\x00other")
        (build / "src/pkg/extra.cpp").write_text("int b;\n", encoding="utf-8")
        (build / "install/setup.bash").unlink()
        record = self.gates(build, identity)
        self.assertFalse(record["passed"])
        self.assertEqual(record["install"]["mismatched"], ["install/pkg/lib/libpkg.a"])
        self.assertEqual(record["install"]["missing"], ["install/setup.bash"])
        self.assertEqual(record["source"]["unexpected"], ["src/pkg/extra.cpp"])
        self.assertEqual(len(record["errors"]), 2)

    def test_workspace_gate_refuses_wrong_path_and_missing_gate(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", "/elsewhere/scan_03")
        identity = self.identity_for(build)
        record = self.gates(build, identity)
        self.assertIn("workspace path differs from the build identity", record["errors"])
        self.assertFalse(self.gates(build, {"install_identity": identity["install_identity"]})["passed"])
        self.assertFalse(self.gates(build, None)["passed"])

    def test_missing_install_identity_needs_explicit_flag(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", str(Path(self.tmp.name) / "ws"), with_install_identity=False)
        with self.assertRaisesRegex(RuntimeError, "allow-missing-install-identity"):
            self.m.build_scan_workspace_gate(build, None, False)
        identity = self.identity_for(build, allow_missing=True)
        record = self.gates(build, identity)
        self.assertTrue(record["passed"])
        self.assertFalse(record["install_checked"])
        identity["workspace_gate"]["allow_missing_install_identity"] = False
        self.assertIn("install identity missing and not explicitly allowed", self.gates(build, identity)["errors"])

    def test_local_build_gate_refuses_source_drift_and_remote_path_mismatch(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", self.remote)
        with self.assertRaisesRegex(RuntimeError, "differs from the build identity"):
            self.m.build_scan_workspace_gate(build, "/remote/p2b/builds/scan_other", False)
        (build / "src/pkg/a.cpp").write_text("int changed;\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "local SCAN src/ differs"):
            self.m.build_scan_workspace_gate(build, self.remote, False)

    def test_prepare_refuses_bad_scan_build_before_creating_run(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", self.remote, with_install_identity=False)
        args = self.m.build_parser().parse_args([
            "--run-id", "refused_run", "--local-runs-root", self.tmp.name,
            "--accepted-scan-build-dir", str(build), "--remote-scan-workspace", self.remote,
        ])
        with self.assertRaisesRegex(RuntimeError, "install_identity"):
            self.m.prepare(args)
        self.assertFalse((Path(self.tmp.name) / "refused_run").exists())

    def test_cancel_trigger_limits(self):
        spawn, goal_a = self.pilot["spawn_ground_xyz_m"], self.pilot["goals"][0]["ground_xyz_m"]
        straight = ((goal_a[0] - spawn[0]) ** 2 + (goal_a[1] - spawn[1]) ** 2) ** 0.5
        default = self.m.cancel_trigger_check(0.40, self.pilot)
        self.assertAlmostEqual(default["spawn_to_goal_a_xy_m"], straight)
        self.assertAlmostEqual(default["maximum_allowed_m"], straight - 0.30)
        for value in (0.45, 0.50, 0.55, straight - 0.30):
            self.assertEqual(self.m.cancel_trigger_check(value, self.pilot)["cancel_displacement_m"], value)
        for value in (0.39, 0.0, -1.0):
            with self.assertRaisesRegex(ValueError, "below the 0.40 m review minimum"):
                self.m.cancel_trigger_check(value, self.pilot)
        for value in (straight - 0.29, straight, 5.0):
            with self.assertRaisesRegex(ValueError, "within 0.30 m of goal A"):
                self.m.cancel_trigger_check(value, self.pilot)
        with self.assertRaises(ValueError):
            self.m.cancel_trigger_check(float("nan"), self.pilot)

    def test_prepare_refuses_cancel_values_before_creating_run(self):
        for value in ("0.39", "1.8"):
            args = self.m.build_parser().parse_args([
                "--run-id", "cancel_refused", "--local-runs-root", self.tmp.name, "--cancel-displacement-m", value,
            ])
            with self.assertRaises(ValueError):
                self.m.prepare(args)
            self.assertFalse((Path(self.tmp.name) / "cancel_refused").exists())

    def test_nondefault_cancel_is_carried_to_worker_driver_and_runbook(self):
        build = make_scan_build(Path(self.tmp.name) / "ws", self.remote)
        args = self.m.build_parser().parse_args([
            "--run-id", "cancel_055", "--local-runs-root", self.tmp.name, "--cancel-displacement-m", "0.55",
            "--accepted-scan-build-dir", str(build), "--remote-scan-workspace", self.remote,
        ])
        local_run, commands = self.m.prepare(args)
        self.assertTrue(commands["run"][-1].endswith("--cancel-displacement-m 0.55"))
        request = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))
        self.assertEqual(request["cancel_displacement_m"], 0.55)
        self.assertEqual(request["scan_workspace_gate"]["installed_file_count"], 2)
        self.assertIn("at least 0.55 m measured displacement", (local_run / "RUNBOOK.md").read_text(encoding="utf-8"))
        worker = (local_run / "remote_worker.py").read_text(encoding="utf-8")
        self.assertIn('"--cancel-displacement-m", repr(args.cancel_displacement_m)', worker)
        source = json.loads((local_run / "source_env_hashes.json").read_text(encoding="utf-8"))
        self.assertEqual(source["accepted_scan_build_identity"]["workspace_gate"]["expected_remote_workspace"], self.remote)

    def test_pilot_driver_refuses_cancel_below_minimum(self):
        module = types.ModuleType("pilot_driver_cancel_test")
        exec(compile(self.m.pilot_driver_source(), "pilot_driver_cancel_test.py", "exec"), module.__dict__)
        old_argv = sys.argv[:]
        try:
            sys.argv = ["pilot_driver.py", "--run-root", self.tmp.name, "--http-port", "1", "--run-id", "r", "--cancel-displacement-m", "0.39"]
            with self.assertRaises(SystemExit) as raised:
                module.main()
        finally:
            sys.argv = old_argv
        self.assertEqual(raised.exception.code, 2)

    def test_execute_refuses_package_without_workspace_gate(self):
        local_run = Path(self.tmp.name) / "old_package"
        local_run.mkdir()
        (local_run / "source_env_hashes.json").write_text('{"accepted_scan_build_identity": {"local_path": "x"}}\n', encoding="utf-8")
        args = self.m.build_parser().parse_args([
            "--execute", "--lead-authorized-execute", "--run-id", "old_package", "--local-runs-root", self.tmp.name,
            "--remote-scan-workspace", self.remote,
        ])
        with self.assertRaisesRegex(RuntimeError, "predates the SCAN workspace hash gate"):
            self.m.execute(args, local_run, {"mkdir": ["false"]})
        self.assertFalse((local_run / "host_logs").exists())

    def test_gpu_sampler_records_peak_and_errors(self):
        rows = iter([
            [{"index": 0, "memory_used_mib": 500.0, "memory_total_mib": 16303.0, "utilization_percent": 1.0}],
            [{"index": 0, "memory_used_mib": 7082.0, "memory_total_mib": 16303.0, "utilization_percent": 90.0}],
            RuntimeError("nvidia-smi exit 9"),
        ])

        def fake_query():
            item = next(rows, [{"index": 0, "memory_used_mib": 100.0, "memory_total_mib": 16303.0, "utilization_percent": 0.0}])
            if isinstance(item, Exception):
                raise item
            return item

        self.worker.query_gpus = fake_query
        path = Path(self.tmp.name) / "gpu_samples.jsonl"
        sampler = self.worker.GpuSampler(path, 0.01)
        self.assertFalse(sampler.stop()["started"])
        sampler.start()
        deadline = self.worker.time.monotonic() + 5.0
        while sampler.summary["sample_count"] < 4 and self.worker.time.monotonic() < deadline:
            self.worker.time.sleep(0.01)
        summary = sampler.stop()
        self.assertTrue(summary["stopped"])
        self.assertEqual(summary["peak_memory_used_mib"], 7082.0)
        self.assertEqual(summary["peak_by_gpu"]["0"]["memory_used_mib"], 7082.0)
        self.assertEqual(summary["first_sample"]["gpus"][0]["memory_used_mib"], 500.0)
        self.assertEqual(summary["error_count"], 1)
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), summary["sample_count"])
        self.assertIn("error", lines[2])

    def test_query_gpus_parses_nvidia_smi_csv(self):
        real_run = self.worker.subprocess.run
        self.worker.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "0, 7082, 16303, [N/A]\n", "")
        try:
            rows = self.worker.query_gpus()
        finally:
            self.worker.subprocess.run = real_run
        self.assertEqual(rows, [{"index": 0, "memory_used_mib": 7082.0, "memory_total_mib": 16303.0, "utilization_percent": None}])

    def test_remote_worker_gate_replaces_install_existence_check(self):
        src = self.m.remote_worker_source()
        self.assertNotIn('(scan_ws / "install").exists()', src)
        self.assertLess(src.index("scan_gate = scan_workspace_gate(scan_ws, scan_identity)"), src.index("ensure_tcp_port_free(port)\n        for container"))
        self.assertLess(src.index("scan_gate = scan_workspace_gate"), src.index("bridge_cmd = ["))
        self.assertIn('result["remote_wall_seconds"]', src)
        self.assertIn('result["gpu_memory"] = gpu_sampler.stop()', src)
        self.assertLess(src.index("gpu_sampler.start()"), src.index("verify_manifest(run_root"))

    def test_default_request_matches_actual4_apart_from_new_fields(self):
        if not (ACTUAL4 / "run_request.json").exists() or not (SCAN_03 / "src").is_dir():
            self.skipTest("local-only actual4 package or scan_03 source is absent")
        args = self.m.build_parser().parse_args([
            "--run-id", ACTUAL4.name, "--local-runs-root", self.tmp.name,
            "--accepted-scan-build-dir", str(SCAN_03), "--remote-scan-workspace", SCAN_03_REMOTE,
        ])
        local_run, commands = self.m.prepare(args)

        def normalized(path, root):
            return json.loads(path.read_text(encoding="utf-8").replace(str(root), "LOCAL_RUN"))

        old_request = normalized(ACTUAL4 / "run_request.json", ACTUAL4)
        new_request = normalized(local_run / "run_request.json", local_run)
        self.assertEqual(set(new_request) - set(old_request), NEW_RUN_REQUEST_FIELDS)
        self.assertEqual({k: v for k, v in new_request.items() if k not in NEW_RUN_REQUEST_FIELDS}, old_request)
        self.assertEqual(new_request["cancel_displacement_m"], 0.4)
        self.assertFalse(new_request["allow_missing_install_identity"])
        self.assertEqual(new_request["scan_workspace_gate"]["source_file_count"], 67)
        self.assertEqual(new_request["scan_workspace_gate"]["installed_file_count"], 380)
        self.assertIs(new_request["remote_only_bulk"], False)
        self.assertIsNone(new_request["remote_only_bulk_detail"])
        self.assertEqual(new_request["stance_hold"], "off")
        storage = new_request["package_storage"]
        self.assertEqual(storage["linked_count"] + storage["copied_count"], storage["linked_files_hash_checked"])
        self.assertFalse((local_run / "make_walk_review.py").exists())

        old_commands = normalized(ACTUAL4 / "commands.json", ACTUAL4)
        new_commands = normalized(local_run / "commands.json", local_run)
        self.assertEqual(new_commands["run"][:-1], old_commands["run"][:-1])
        # Intended differences: the runner argv gains exactly `--stance-hold off` (stance-hold task) and the
        # worker gains `--cancel-displacement-m 0.4`. Every other token is unchanged.
        old_tokens = shlex.split(old_commands["run"][-1])
        new_tokens = shlex.split(new_commands["run"][-1])
        old_argv = json.loads(old_tokens[old_tokens.index("--runner-argv-json") + 1])
        new_argv = json.loads(new_tokens[new_tokens.index("--runner-argv-json") + 1])
        at = new_argv.index("--stance-hold")
        self.assertEqual(new_argv[at:at + 2], ["--stance-hold", "off"])
        self.assertEqual(new_argv[:at] + new_argv[at + 2:], old_argv)
        old_tokens[old_tokens.index("--runner-argv-json") + 1] = "ARGV"
        new_tokens[new_tokens.index("--runner-argv-json") + 1] = "ARGV"
        self.assertEqual(new_tokens, old_tokens + ["--cancel-displacement-m", "0.4"])
        self.assertEqual({k: v for k, v in new_commands.items() if k != "run"}, {k: v for k, v in old_commands.items() if k != "run"})
        for rel in ["inputs/two_goal_route_artifact.json",
                    "config/p2b_backend_ros.two_goal.json", "config/foxy_bridge_two_goal.yaml", "config/planner.yaml", "config/controller.yaml"]:
            self.assertEqual((local_run / rel).read_bytes(), (ACTUAL4 / rel).read_bytes(), rel)
        # The scope and execution manifest differ only by the stance-hold runner bytes and configuration keys:
        # --stance-hold (stance-hold task) and the PRD D5 parser defaults --camera-heading-mode body and
        # --stance-entry-kd ramp, which keep the previous camera and control path. --command-script is a
        # path and stays out of the execution configuration.
        new_runner_sha = digest(local_run / "bridge" / RUNNER_REL)
        self.assertNotEqual(new_runner_sha, ACTUAL4_RUNNER_SHA256)
        old_manifest = json.loads((ACTUAL4 / "inputs/execution_manifest.json").read_text(encoding="utf-8"))
        new_manifest = json.loads((local_run / "inputs/execution_manifest.json").read_text(encoding="utf-8"))
        old_files = {item["path"]: item for item in old_manifest.pop("files")}
        new_files = {item["path"]: item for item in new_manifest.pop("files")}
        self.assertEqual(new_manifest, old_manifest)
        self.assertEqual(old_files.pop(RUNNER_REL)["sha256"], ACTUAL4_RUNNER_SHA256)
        self.assertEqual(new_files.pop(RUNNER_REL)["sha256"], new_runner_sha)
        self.assertEqual(new_files, old_files)
        old_scope = json.loads((ACTUAL4 / "inputs/two_goal_scope.json").read_text(encoding="utf-8"))
        new_scope = json.loads((local_run / "inputs/two_goal_scope.json").read_text(encoding="utf-8"))
        self.assertEqual(new_scope["execution_configuration"].pop("stance_hold"), "off")
        self.assertEqual(new_scope["execution_configuration"].pop("camera_heading_mode"), "body")
        self.assertEqual(new_scope["execution_configuration"].pop("stance_entry_kd"), "ramp")
        self.assertNotIn("command_script", new_scope["execution_configuration"])
        self.assertEqual(old_scope.pop("execution_source_sha256"), ACTUAL4_RUNNER_SHA256)
        self.assertEqual(new_scope.pop("execution_source_sha256"), new_runner_sha)
        self.assertEqual(old_scope.pop("execution_manifest_sha256"), digest(ACTUAL4 / "inputs/execution_manifest.json"))
        self.assertEqual(new_scope.pop("execution_manifest_sha256"), digest(local_run / "inputs/execution_manifest.json"))
        self.assertEqual(new_scope, old_scope)
        old_source = json.loads((ACTUAL4 / "source_env_hashes.json").read_text(encoding="utf-8"))
        new_source = json.loads((local_run / "source_env_hashes.json").read_text(encoding="utf-8"))
        self.assertEqual(new_source["accepted_scan_build_identity"]["install_identity"], old_source["accepted_scan_build_identity"]["install_identity"])
        self.assertIsNone(old_source["accepted_scan_build_identity"].get("workspace_gate"))
        self.assertTrue(new_source["accepted_scan_build_identity"]["workspace_gate"]["local_source_check"]["match"])


FAKE_ARTIFACTS = {
    "result.json": b'{"passed": true}\n',
    "pilot_journal.json": b'{"events": []}\n',
    "runner_output/metrics.jsonl": b'{"step": 0}\n',
    "runner_output/camera_frames.jsonl": b'{"frame_index": 0}\n',
    "runner_output/clouds.jsonl": b"cloud-row\n" * 64,
    "runner_output/third_person_master.mp4": b"\x00\x00\x00\x18ftypmp42" * 32,
}


def make_remote_artifacts(remote_run):
    """Fake execution-host artifacts plus an artifact_hashes.json shaped like the worker's."""
    artifacts = Path(remote_run) / "artifacts"
    for rel, data in FAKE_ARTIFACTS.items():
        (artifacts / rel).parent.mkdir(parents=True, exist_ok=True)
        (artifacts / rel).write_bytes(data)
    hashes = {rel: hashlib.sha256(data).hexdigest() for rel, data in FAKE_ARTIFACTS.items()}
    hashes["artifact_hashes.json"] = "0" * 64  # the worker's manifest lists its previous self
    (artifacts / "artifact_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    return artifacts


def pull_artifacts(remote_run, local_run, skip=()):
    for path in (Path(remote_run) / "artifacts").rglob("*"):
        rel = path.relative_to(Path(remote_run) / "artifacts").as_posix()
        if path.is_file() and rel not in skip:
            target = Path(local_run) / "returned_artifacts" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


class PackageStorageAndRemoteOnlyTests(unittest.TestCase):
    remote = "/remote/p2b/builds/scan_test"

    def setUp(self):
        self.m = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.build = make_scan_build(self.root / "scan_build", self.remote)
        self.remote_root = self.root / "remote_host"

    def prepare(self, run_id, *extra):
        args = self.m.build_parser().parse_args([
            "--run-id", run_id, "--local-runs-root", str(self.root / "runs"), "--remote-root", str(self.remote_root),
            "--accepted-scan-build-dir", str(self.build), "--remote-scan-workspace", self.remote, *extra,
        ])
        local_run, commands = self.m.prepare(args)
        return args, local_run, commands

    def frozen_sources(self):
        paths = [self.m.P2B / rel for rel in ("inputs/building.usda", "inputs/new_building.pickle", "inputs/pilot.json", "input_manifest.json")]
        # Same ignore rule as copytree_clean: build/install/log trees and bytecode are not packaged.
        skipped = {"__pycache__", ".pytest_cache", ".mypy_cache", "build", "install", "log"}
        paths += [p for p in self.m.PCT_RUNTIME.rglob("*") if p.is_file() and p.suffix not in {".pyc", ".pyo"}
                  and not skipped & set(p.relative_to(self.m.PCT_RUNTIME).parts)]
        return {p: digest(p) for p in paths}

    def test_hardlinked_package_passes_existing_hash_verification(self):
        before = self.frozen_sources()
        args, local_run, _ = self.prepare("linked_run")
        storage = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))["package_storage"]
        same_device = (self.root.stat().st_dev == self.m.P2B.stat().st_dev)
        self.assertEqual(storage["linked_count"] + storage["copied_count"], len(before))
        self.assertEqual(storage["linked_files_hash_checked"], len(before))
        self.assertEqual(storage["copied_count"], 0 if same_device else len(before))
        big = local_run / "inputs/new_building.pickle"
        self.assertEqual(os.path.samefile(big, self.m.P2B / "inputs/new_building.pickle"), same_device)
        self.assertTrue((local_run / "pct_runtime/lib/libgtsam.so.4").is_file())
        # Rewritten files are never links to their sources.
        self.assertFalse(os.path.samefile(local_run / "config/planner.yaml", self.m.P2B / "baseline_config/planner.yaml"))
        runner = "lite3_sim_bridge/run_pct_scan_building.py"
        self.assertFalse(os.path.samefile(local_run / "bridge" / runner, self.m.BRIDGE_REF / runner))
        # Existing gates: local reload and the remote worker's manifest check both pass.
        load_args = self.m.build_parser().parse_args(["--run-id", "linked_run", "--local-runs-root", str(self.root / "runs")])
        self.m.load_prepared_run(load_args)
        worker = types.ModuleType("remote_worker_linked_test")
        exec(compile(self.m.remote_worker_source(), "remote_worker_linked_test.py", "exec"), worker.__dict__)
        worker.verify_manifest(local_run, json.loads((local_run / "inputs/package_manifest.json").read_text(encoding="utf-8")))
        self.assertEqual(self.frozen_sources(), before)

    def test_link_failure_falls_back_to_copy_and_still_verifies(self):
        before = self.frozen_sources()
        with mock.patch.object(self.m.os, "link", side_effect=OSError(18, "Invalid cross-device link")):
            _, local_run, _ = self.prepare("copied_run")
        storage = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))["package_storage"]
        self.assertEqual(storage["linked_count"], 0)
        self.assertEqual(storage["copied_count"], len(before))
        self.assertIn("Invalid cross-device link", storage["copy_reasons"][0])
        self.assertFalse(os.path.samefile(local_run / "inputs/new_building.pickle", self.m.P2B / "inputs/new_building.pickle"))
        load_args = self.m.build_parser().parse_args(["--run-id", "copied_run", "--local-runs-root", str(self.root / "runs")])
        self.m.load_prepared_run(load_args)
        self.assertEqual(self.frozen_sources(), before)

    def test_linked_file_check_refuses_hash_drift(self):
        run_dir = self.root / "pkg"
        (run_dir / "inputs").mkdir(parents=True)
        src = self.root / "src.bin"
        src.write_bytes(b"frozen")
        (run_dir / "inputs/src.bin").write_bytes(b"frozen")
        manifest = {"files": [{"path": "inputs/src.bin", "sha256": digest(src)}]}
        pairs = [(str(src), str(run_dir / "inputs/src.bin"))]
        self.assertEqual(self.m.check_linked_package_files(run_dir, manifest, pairs, {}), 1)
        with self.assertRaisesRegex(RuntimeError, "differs from its frozen source"):
            self.m.check_linked_package_files(run_dir, manifest, pairs, {"inputs/src.bin": "1" * 64})

    def test_remote_only_prepare_adds_steps_without_touching_default_commands(self):
        _, default_run, default_commands = self.prepare("default_run")
        _, local_run, commands = self.prepare("bulk_run", "--remote-only-bulk")
        remote_run = str(self.remote_root) + "/bulk_run"

        def normal(value, run):
            return json.loads(json.dumps(value).replace(run, "RUN"))

        added = {"remote_only_record", "walk_review", "collect_extras", "collect_sequence", "remote_only_bulk"}
        self.assertEqual(set(commands) - set(default_commands), added)
        for key in set(default_commands) - {"sync", "sync_whitelist", "collect"}:
            self.assertEqual(normal(commands[key], "bulk_run"), normal(default_commands[key], "default_run"), key)
        self.assertEqual(commands["collect_sequence"], ["collect", "remote_only_record", "walk_review", "collect_extras"])
        self.assertEqual(commands["collect"][:4], ["rsync", "-a", "--exclude=/runner_output/clouds.jsonl",
                                                   "--exclude=/runner_output/third_person_master.mp4"])
        self.assertEqual(normal(commands["collect"][4:], "bulk_run"), normal(default_commands["collect"][2:], "default_run"))
        sync = commands["sync"]
        self.assertLess(sync.index("--include=/make_walk_review.py"), sync.index("--exclude=*"))
        self.assertIn("make_walk_review.py", commands["sync_whitelist"])
        render = commands["walk_review"][-1]
        for part in ("conda activate isaaclab", remote_run + "/make_walk_review.py", "--encoder h264_nvenc",
                     "--fallback-encoder libx264", "--artifacts-dir " + remote_run + "/artifacts",
                     "--video " + remote_run + "/artifacts/runner_output/third_person_master.mp4",
                     "--output " + remote_run + "/walk_review/walk_review.mp4", 'FFMPEG_BIN="$(command -v ffmpeg)"'):
            self.assertIn(part, render)
        self.assertEqual(commands["remote_only_record"][-1], "python3 - <<'PY'\n" + self.m.remote_only_record_source(remote_run) + "PY")
        self.assertIn("--include=/walk_review/***", commands["collect_extras"])
        self.assertEqual(commands["collect_extras"][-1], str(local_run) + "/")
        self.assertEqual(digest(local_run / "make_walk_review.py"), digest(self.m.WALK_REVIEW_SCRIPT))
        manifest = json.loads((local_run / "inputs/package_manifest.json").read_text(encoding="utf-8"))
        self.assertIn("make_walk_review.py", [item["path"] for item in manifest["files"]])
        request = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))
        self.assertIs(request["remote_only_bulk"], True)
        self.assertEqual(request["remote_only_bulk_detail"]["remote_only_files"], list(self.m.REMOTE_ONLY_BULK_FILES))
        self.assertIn("--remote-only-bulk", (local_run / "RUNBOOK.md").read_text(encoding="utf-8"))
        self.assertNotIn("--remote-only-bulk", (default_run / "RUNBOOK.md").read_text(encoding="utf-8"))
        self.assertFalse((default_run / "make_walk_review.py").exists())

    def test_remote_only_record_source_hashes_host_files(self):
        remote_run = self.root / "host_run"
        artifacts = make_remote_artifacts(remote_run)
        source = self.m.remote_only_record_source(str(remote_run))
        proc = subprocess.run([sys.executable, "-"], input=source, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        record = json.loads((remote_run / "remote_only_artifacts.json").read_text(encoding="utf-8"))
        self.assertTrue(record["all_match"])
        self.assertEqual([item["path"] for item in record["files"]], list(self.m.REMOTE_ONLY_BULK_FILES))
        self.assertEqual(record["files"][0]["bytes"], len(FAKE_ARTIFACTS["runner_output/clouds.jsonl"]))
        (artifacts / "runner_output/clouds.jsonl").write_bytes(b"changed after the manifest")
        proc = subprocess.run([sys.executable, "-"], input=source, text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(json.loads((remote_run / "remote_only_artifacts.json").read_text(encoding="utf-8"))["all_match"])
        (artifacts / "runner_output/clouds.jsonl").unlink()
        proc = subprocess.run([sys.executable, "-"], input=source, text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)

    def remote_only_package(self):
        remote_run = self.root / "host_run"
        make_remote_artifacts(remote_run)
        proc = subprocess.run([sys.executable, "-"], input=self.m.remote_only_record_source(str(remote_run)), text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        local_run = self.root / "local_run"
        pull_artifacts(remote_run, local_run, skip=self.m.REMOTE_ONLY_BULK_FILES)
        shutil.copy2(remote_run / "remote_only_artifacts.json", local_run / "remote_only_artifacts.json")
        return remote_run, local_run

    def test_remote_only_verification_accepts_exactly_the_listed_files(self):
        remote_run, local_run = self.remote_only_package()
        verdict = self.m.verify_returned_artifacts(local_run, remote_only=True)
        self.assertTrue(verdict["returned_hashes_match"], verdict)
        self.assertEqual(verdict["remote_only_accepted"], sorted(self.m.REMOTE_ONLY_BULK_FILES))
        # Default mode still requires every manifest file.
        self.assertFalse(self.m.verify_returned_artifacts(local_run)["returned_hashes_match"])

        metrics = local_run / "returned_artifacts/runner_output/metrics.jsonl"
        metrics.unlink()
        verdict = self.m.verify_returned_artifacts(local_run, remote_only=True)
        self.assertFalse(verdict["returned_hashes_match"])
        self.assertEqual(verdict["missing_not_remote_only"], ["runner_output/metrics.jsonl"])
        metrics.write_bytes(FAKE_ARTIFACTS["runner_output/metrics.jsonl"])

        extra = local_run / "returned_artifacts/unlisted.log"
        extra.write_text("x\n", encoding="utf-8")
        self.assertEqual(self.m.verify_returned_artifacts(local_run, remote_only=True)["unexpected"], ["unlisted.log"])
        extra.unlink()

        record_path = local_run / "remote_only_artifacts.json"
        original = record_path.read_text(encoding="utf-8")
        record = json.loads(original)
        record["files"].append({"path": "runner_output/metrics.jsonl", "bytes": 1,
                                "sha256": digest(metrics), "manifest_sha256": digest(metrics)})
        record_path.write_text(json.dumps(record), encoding="utf-8")
        metrics.unlink()
        verdict = self.m.verify_returned_artifacts(local_run, remote_only=True)
        self.assertFalse(verdict["returned_hashes_match"])
        self.assertEqual(verdict["missing_not_remote_only"], ["runner_output/metrics.jsonl"])
        self.assertTrue(any("differ from the fixed list" in e for e in verdict["remote_only_record"]["errors"]))
        metrics.write_bytes(FAKE_ARTIFACTS["runner_output/metrics.jsonl"])

        record = json.loads(original)
        record["files"][1]["sha256"] = "f" * 64
        record_path.write_text(json.dumps(record), encoding="utf-8")
        self.assertFalse(self.m.verify_returned_artifacts(local_run, remote_only=True)["returned_hashes_match"])
        record_path.unlink()
        verdict = self.m.verify_returned_artifacts(local_run, remote_only=True)
        self.assertFalse(verdict["returned_hashes_match"])
        self.assertIn("remote_only_artifacts.json was not returned", verdict["remote_only_record"]["errors"])

    def fake_walk_review(self, remote_run, guard_allowed=True):
        out = Path(remote_run) / "walk_review"
        out.mkdir(parents=True, exist_ok=True)
        (out / "render_guard.json").write_text(json.dumps({"render_allowed": guard_allowed, "problems": []}), encoding="utf-8")
        (out / "walk_review.mp4").write_bytes(b"rendered review")
        artifacts = Path(remote_run) / "artifacts"
        inputs = {name: {"sha256": digest(artifacts / rel)} for name, rel in (
            ("video", "runner_output/third_person_master.mp4"), ("camera_frames", "runner_output/camera_frames.jsonl"),
            ("metrics", "runner_output/metrics.jsonl"), ("pilot_journal", "pilot_journal.json"))}
        sidecar = {"inputs": inputs, "encoder": {"used": "h264_nvenc"},
                   "output": {"sha256": digest(out / "walk_review.mp4"), "frames": 1}}
        (out / "walk_review.json").write_text(json.dumps(sidecar), encoding="utf-8")

    def run_execute(self, run_id, *extra, walk_review_fails=False):
        args, local_run, commands = self.prepare(run_id, *extra)
        remote_run = self.remote_root / run_id
        labels = []

        def fake_run_command(label, command, log_path, timeout=1800):
            labels.append(label)
            log_path.write_text("fake %s\n" % label, encoding="utf-8")
            if label == "mkdir":
                remote_run.mkdir(parents=True)
            elif label == "run":
                make_remote_artifacts(remote_run)
            elif label == "collect":
                skip = [a.removeprefix("--exclude=/") for a in command if a.startswith("--exclude=/")]
                pull_artifacts(remote_run, local_run, skip=skip)
            elif label == "remote_only_record":
                source = command[-1].removeprefix("python3 - <<'PY'\n").removesuffix("PY")
                subprocess.run([sys.executable, "-"], input=source, text=True, check=True, capture_output=True)
            elif label == "walk_review":
                if walk_review_fails:
                    raise RuntimeError("walk_review failed with exit 1: No module named matplotlib")
                self.fake_walk_review(remote_run)
            elif label == "collect_extras":
                shutil.copy2(remote_run / "remote_only_artifacts.json", local_run / "remote_only_artifacts.json")
                if (remote_run / "walk_review").is_dir():
                    shutil.copytree(remote_run / "walk_review", local_run / "walk_review")

        args = self.m.build_parser().parse_args([
            "--run-id", run_id, "--local-runs-root", str(self.root / "runs"), "--remote-root", str(self.remote_root),
            "--execute", "--lead-authorized-execute", "--remote-scan-workspace", self.remote, *extra,
        ])
        with mock.patch.object(self.m, "run_command", fake_run_command):
            try:
                self.m.execute(args, local_run, commands)
                error = None
            except RuntimeError as exc:
                error = exc
        verdict = json.loads((local_run / "return_verdict.json").read_text(encoding="utf-8"))
        return labels, verdict, error

    def test_execute_default_collects_as_before(self):
        labels, verdict, error = self.run_execute("exec_default")
        self.assertIsNone(error)
        self.assertEqual(labels, ["mkdir", "sync", "run", "collect"])
        self.assertEqual(set(verdict), {"remote_worker_started", "host_wall_seconds", "returned_hashes_match", "expected_count", "actual_count"})
        self.assertTrue(verdict["returned_hashes_match"])

    def test_execute_remote_only_runs_sequence_and_verifies(self):
        labels, verdict, error = self.run_execute("exec_bulk", "--remote-only-bulk")
        self.assertIsNone(error)
        self.assertEqual(labels, ["mkdir", "sync", "run", "collect", "remote_only_record", "walk_review", "collect_extras"])
        self.assertTrue(verdict["returned_hashes_match"])
        self.assertEqual(verdict["remote_only_accepted"], sorted(self.m.REMOTE_ONLY_BULK_FILES))
        self.assertTrue(verdict["walk_review"]["ok"], verdict["walk_review"])
        self.assertEqual(verdict["collect_step_errors"], {})
        self.assertFalse((self.root / "runs/exec_bulk/returned_artifacts/runner_output/clouds.jsonl").exists())

    def test_execute_remote_only_reports_missing_walk_review_after_collecting(self):
        labels, verdict, error = self.run_execute("exec_bulk_fail", "--remote-only-bulk", walk_review_fails=True)
        self.assertEqual(labels[-1], "collect_extras")
        self.assertRegex(str(error), "walk review was not returned")
        self.assertTrue(verdict["returned_hashes_match"])
        self.assertIn("walk_review", verdict["collect_step_errors"])
        self.assertFalse(verdict["walk_review"]["ok"])

    def test_walk_review_command_runs_guard_before_render(self):
        _, _, commands = self.prepare("guard_cmd", "--remote-only-bulk")
        command = commands["walk_review"][-1]
        guard_end = command.index(" && FFMPEG_BIN=")
        self.assertTrue(command.startswith("python3 -c "))
        self.assertLess(guard_end, command.index("make_walk_review.py"))
        self.assertIn("render_guard.json", command[:guard_end])

    def test_walk_review_guard_requires_finished_worker_and_dead_process_groups(self):
        remote_run = self.root / "guard_run"
        (remote_run / "artifacts").mkdir(parents=True)
        source = self.m.walk_review_guard_source(str(remote_run))
        record_path = remote_run / "walk_review/render_guard.json"

        def guard():
            proc = subprocess.run([sys.executable, "-c", source], text=True, capture_output=True)
            return proc, json.loads(record_path.read_text(encoding="utf-8"))

        proc, record = guard()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("artifacts/result.json is missing", record["problems"])
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(lambda: sleeper.poll() is None and sleeper.kill())
        result = {"last_result_write_phase": "after_container_cleanup", "cleanup_errors": [],
                  "process_cleanup": [{"name": "runner", "pid": sleeper.pid, "ok": True}]}
        (remote_run / "artifacts/result.json").write_text(json.dumps(result), encoding="utf-8")
        proc, record = guard()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("remote worker has not written its final result", record["problems"])
        self.assertEqual(record["alive_process_groups"], [sleeper.pid])
        result["last_result_write_phase"] = "final"
        (remote_run / "artifacts/result.json").write_text(json.dumps(result), encoding="utf-8")
        proc, record = guard()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("walk review not started", proc.stderr)
        sleeper.kill()
        sleeper.wait()
        proc, record = guard()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(record["render_allowed"])
        self.assertEqual(record["alive_process_groups"], [])
        result["cleanup_errors"] = [{"container": "x", "ok": False}]
        (remote_run / "artifacts/result.json").write_text(json.dumps(result), encoding="utf-8")
        proc, record = guard()
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(record["render_allowed"])

    def test_walk_review_verification_requires_passing_guard(self):
        remote_run, local_run = self.remote_only_package()
        self.fake_walk_review(remote_run, guard_allowed=False)
        shutil.copytree(remote_run / "walk_review", local_run / "walk_review")
        verdict = self.m.verify_walk_review(local_run)
        self.assertFalse(verdict["ok"])
        self.assertIn("walk review has no passing render_guard.json", verdict["errors"])
        (local_run / "walk_review/render_guard.json").write_text('{"render_allowed": true, "problems": []}', encoding="utf-8")
        self.assertTrue(self.m.verify_walk_review(local_run)["ok"])

    def test_execute_refuses_cancel_value_that_differs_from_package(self):
        _, local_run, commands = self.prepare("cancel_mismatch", "--cancel-displacement-m", "0.55")
        for extra in ([], ["--cancel-displacement-m", "0.45"]):
            args = self.m.build_parser().parse_args([
                "--run-id", "cancel_mismatch", "--local-runs-root", str(self.root / "runs"), "--execute",
                "--lead-authorized-execute", "--remote-scan-workspace", self.remote, *extra,
            ])
            with self.assertRaisesRegex(RuntimeError, "cancel-displacement-m .* differs from the prepared package"):
                self.m.execute(args, local_run, commands)
        self.assertFalse((local_run / "host_logs").exists())

    def test_remote_worker_fails_when_post_run_scan_gate_fails(self):
        src = self.m.remote_worker_source()
        exit_check = src.index('if (result.get("scan_workspace_gate_after") or {}).get("passed") is not True:')
        self.assertLess(src.index('finalize_result_artifacts(artifacts, result, "final")'), exit_check)
        self.assertLess(exit_check, src.index('if __name__ == "__main__":'))
        self.assertIn('raise SystemExit("SCAN workspace hash gate failed after the run', src[exit_check:])

    def test_stance_hold_auto_reaches_runner_scope_request_and_runbook(self):
        _, local_run, commands = self.prepare("stance_auto", "--stance-hold", "auto")
        tokens = shlex.split(commands["run"][-1])
        argv = json.loads(tokens[tokens.index("--runner-argv-json") + 1])
        self.assertEqual(argv[argv.index("--stance-hold") + 1], "auto")
        scope = json.loads((local_run / "inputs/two_goal_scope.json").read_text(encoding="utf-8"))
        self.assertEqual(scope["execution_configuration"]["stance_hold"], "auto")
        runner = self.m.import_runner(local_run / "bridge" / RUNNER_REL)
        self.assertEqual(runner.execution_configuration(runner.build_parser().parse_args(argv)),
                         scope["execution_configuration"])
        request = json.loads((local_run / "run_request.json").read_text(encoding="utf-8"))
        self.assertEqual(request["stance_hold"], "auto")
        self.assertIn("--stance-hold auto", (local_run / "RUNBOOK.md").read_text(encoding="utf-8"))
        _, off_run, _ = self.prepare("stance_off")
        self.assertNotIn("Stance hold", (off_run / "RUNBOOK.md").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            self.m.build_runner_argv(types.SimpleNamespace(stance_hold="on", remote_v12_runtime="r",
                                                           remote_checkpoint="c", telemetry_port=1, command_port=2),
                                     "/remote", "run", json.loads((self.m.P2B / "inputs/pilot.json").read_text()))

    def test_execute_refuses_stance_hold_that_differs_from_package(self):
        _, local_run, commands = self.prepare("stance_mismatch", "--stance-hold", "auto")
        for extra in ([], ["--stance-hold", "off"]):
            args = self.m.build_parser().parse_args([
                "--run-id", "stance_mismatch", "--local-runs-root", str(self.root / "runs"), "--execute",
                "--lead-authorized-execute", "--remote-scan-workspace", self.remote, *extra,
            ])
            with self.assertRaisesRegex(RuntimeError, "--stance-hold 'off' differs from the prepared package"):
                self.m.execute(args, local_run, commands)
        self.assertFalse((local_run / "host_logs").exists())
        # A package prepared before the flag existed counts as off.
        request_path = local_run / "run_request.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        del request["stance_hold"]
        request_path.write_text(json.dumps(request), encoding="utf-8")
        args = self.m.build_parser().parse_args([
            "--run-id", "stance_mismatch", "--local-runs-root", str(self.root / "runs"), "--execute",
            "--lead-authorized-execute", "--remote-scan-workspace", self.remote, "--stance-hold", "auto",
        ])
        with self.assertRaisesRegex(RuntimeError, "--stance-hold 'auto' differs from the prepared package .*'off'"):
            self.m.execute(args, local_run, commands)

    def test_execute_refuses_flag_that_differs_from_package(self):
        args, local_run, commands = self.prepare("flag_mismatch")
        args = self.m.build_parser().parse_args([
            "--run-id", "flag_mismatch", "--local-runs-root", str(self.root / "runs"), "--execute",
            "--lead-authorized-execute", "--remote-scan-workspace", self.remote, "--remote-only-bulk",
        ])
        with self.assertRaisesRegex(RuntimeError, "differs from the prepared package"):
            self.m.execute(args, local_run, commands)
        self.assertFalse((local_run / "host_logs").exists())


if __name__ == "__main__":
    unittest.main()
