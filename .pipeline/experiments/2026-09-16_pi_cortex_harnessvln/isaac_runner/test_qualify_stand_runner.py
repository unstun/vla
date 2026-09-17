import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import qualify_stand_runner as qualify


class StandRunnerPackageTests(unittest.TestCase):
    def test_prepare_dry_run_package_uses_exact_parser_configuration(self):
        run_id = "stand_unit_package"
        with tempfile.TemporaryDirectory() as tmp:
            args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--remote-root", "/remote/root",
                "--remote-v12-runtime", "/remote/v12",
                "--remote-checkpoint", "/remote/checkpoint/model.pt",
            ])
            local_run, commands = qualify.prepare(args)
            self.assertTrue((local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py").exists())
            self.assertTrue((local_run / "inputs/stand_scope.json").exists())
            self.assertTrue((local_run / "inputs/execution_manifest.json").exists())
            self.assertTrue((local_run / "remote_worker.py").exists())
            scope = json.loads((local_run / "inputs/stand_scope.json").read_text())
            runner = qualify.import_runner(local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py")
            parsed = runner.build_parser().parse_args(qualify.build_runner_argv(
                args, "/remote/root/" + run_id, run_id
            ))
            self.assertEqual(scope["execution_configuration"], runner.execution_configuration(parsed))
            self.assertEqual(scope["execution_configuration"]["case"], "stand_probe")
            self.assertTrue(scope["execution_configuration"]["external_goal_mode"])
            self.assertTrue(scope["execution_configuration"]["complete_body_state"])
            self.assertEqual(commands["remote_run"], "/remote/root/" + run_id)
            self.assertIn("--include=/bridge/***", commands["sync"])
            self.assertNotIn("full_route", scope)
            source_hashes = json.loads((local_run / "source_env_hashes.json").read_text())
            self.assertGreater(source_hashes["v12_runtime_expected_file_count"], 10)
            self.assertIn("resources/lite3/urdf/lite3.urdf", source_hashes["v12_runtime_expected"])
            manifest = json.loads((local_run / "inputs/package_manifest.json").read_text())
            self.assertIn("source_env_hashes.json", [entry["path"] for entry in manifest["files"]])
            worker_source = (local_run / "remote_worker.py").read_text()
            self.assertIn("verify_v12_runtime(args.remote_v12_runtime", worker_source)
            self.assertIn('str(runtime_source / "rsl_rl")', worker_source)
            self.assertIn('str(runtime_source / "robot_lab")', worker_source)
            self.assertIn("conda activate isaaclab", worker_source)
            self.assertIn("importlib.util.find_spec", worker_source)
            self.assertIn("find_spec_no_module_execution", worker_source)
            self.assertIn("robot_lab spec from unexpected path", worker_source)
            self.assertIn("ensure_container_absent(container_name)", worker_source)
            self.assertIn("ensure_tcp_port_free", worker_source)
            self.assertIn("if owned_container_started", worker_source)

    def test_prepare_refuses_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "runs/existing"
            run_dir.mkdir(parents=True)
            args = qualify.build_parser().parse_args([
                "--run-id", "existing",
                "--local-runs-root", str(Path(tmp) / "runs"),
            ])
            with self.assertRaises(FileExistsError):
                qualify.prepare(args)

    def test_execute_can_load_existing_prepared_package_without_rewriting(self):
        run_id = "stand_existing_execute"
        with tempfile.TemporaryDirectory() as tmp:
            args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--remote-root", "/remote/root",
            ])
            local_run, commands = qualify.prepare(args)
            source_env_before = (local_run / "source_env_hashes.json").read_text()
            exec_args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--execute",
            ])
            loaded_run, loaded_commands = qualify.load_prepared_run(exec_args)
            self.assertEqual(loaded_run, local_run)
            self.assertEqual(loaded_commands, commands)
            self.assertEqual((local_run / "source_env_hashes.json").read_text(), source_env_before)

    def test_execute_collects_and_hash_verifies_after_remote_run_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_run = Path(tmp) / "run"
            local_run.mkdir()
            calls = []

            def fake_run_command(label, command, log_path, timeout=1800):
                calls.append(label)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(label, encoding="utf-8")
                if label == "run":
                    raise RuntimeError("remote worker failed")
                if label == "collect":
                    returned = local_run / "returned_artifacts"
                    returned.mkdir()
                    (returned / "result.json").write_text("{}", encoding="utf-8")
                    qualify.write_json(returned / "artifact_hashes.json", {
                        "result.json": qualify.sha256(returned / "result.json")
                    })

            commands = {
                "mkdir": ["mkdir"],
                "sync": ["sync"],
                "run": ["run"],
                "collect": ["collect"],
            }
            with mock.patch.object(qualify, "run_command", side_effect=fake_run_command):
                with self.assertRaisesRegex(RuntimeError, "remote worker failed"):
                    qualify.execute(local_run, commands)

            self.assertEqual(calls, ["mkdir", "sync", "run", "collect"])
            verdict = json.loads((local_run / "return_verdict.json").read_text())
            self.assertTrue(verdict["remote_worker_started"])
            self.assertIn("remote worker failed", verdict["run_error"])
            self.assertTrue(verdict["returned_hashes_match"])


if __name__ == "__main__":
    unittest.main()
