import importlib.util
import json
import math
import py_compile
import sys
import tempfile
import time
import types
import unittest
from argparse import Namespace
from pathlib import Path

import materialize_runner_patch as materializer


class RunnerPatchTests(unittest.TestCase):
    def _load_module(self):
        source = materializer.REPO_ROOT / materializer.SOURCE_REL
        data = materializer.load_and_patch(source)
        tmp = tempfile.TemporaryDirectory()
        runner = Path(tmp.name) / "run_pct_scan_building.py"
        runner.write_text(data["patched_text"], encoding="utf-8")
        py_compile.compile(str(runner), doraise=True)
        spec = importlib.util.spec_from_file_location("patched_runner", str(runner))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.addCleanup(tmp.cleanup)
        return module

    def test_materializes_from_hash_gated_source(self):
        source = materializer.REPO_ROOT / materializer.SOURCE_REL
        data = materializer.load_and_patch(source)
        self.assertEqual(data["source_sha256"], materializer.EXPECTED_SOURCE_SHA256)
        self.assertIn("--external-goal-mode", data["patched_text"])
        self.assertIn('"execution_manifest", "external_control_dir"', data["patched_text"])
        self.assertIn("EXTERNAL_EPISODE_FINISHED", data["patched_text"])
        self.assertIn("_validate_runtime_module_origins(args.runtime)", data["patched_text"])
        self.assertIn("runtime_import_identity.json", data["patched_text"])
        self.assertIn('"runtime_import_identity": runtime_import_identity', data["patched_text"])
        self.assertIn("legacy_fixed_goal_auto_termination_disabled", data["patched_text"])
        self.assertIn("not args.external_goal_mode", data["patched_text"])
        self.assertIn("run_pct_scan_building.py.external_episode", data["patch_text"])

    def test_runtime_module_origin_helper_rejects_unpinned_imports(self):
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "v12"
            robot_root = runtime / "source/robot_lab/robot_lab"
            rsl_root = runtime / "source/rsl_rl/rsl_rl"
            robot_root.mkdir(parents=True)
            rsl_root.mkdir(parents=True)
            old_robot = sys.modules.get("robot_lab")
            old_rsl = sys.modules.get("rsl_rl")
            try:
                sys.modules["robot_lab"] = types.SimpleNamespace(__file__=str(robot_root / "__init__.py"))
                sys.modules["rsl_rl"] = types.SimpleNamespace(__file__=str(rsl_root / "__init__.py"))
                identity = module._validate_runtime_module_origins(runtime)
                self.assertTrue(identity["robot_lab_file"].endswith("robot_lab/__init__.py"))
                sys.modules["robot_lab"] = types.SimpleNamespace(__file__="/opt/other/robot_lab/__init__.py")
                with self.assertRaises(module.AdapterFailure):
                    module._validate_runtime_module_origins(runtime)
            finally:
                if old_robot is None:
                    sys.modules.pop("robot_lab", None)
                else:
                    sys.modules["robot_lab"] = old_robot
                if old_rsl is None:
                    sys.modules.pop("rsl_rl", None)
                else:
                    sys.modules["rsl_rl"] = old_rsl

    def test_materialized_runner_compiles_and_finish_schema_validates(self):
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            finish = Path(tmp) / "finish_request.json"
            now = time.monotonic_ns()
            finish.write_text(json.dumps({
                "schema_version": 1,
                "run_id": "pilot-a",
                "request_id": "req-1",
                "observed_run_epoch_ns": 123,
                "requested_at_monotonic_ns": now,
                "backend_terminal_status": "FINISHED",
            }), encoding="utf-8")
            result = module._external_finish_request(finish, "pilot-a", 123, now, 2.0)
            self.assertTrue(result["requested"])
            self.assertEqual(result["status"], "EXTERNAL_EPISODE_FINISHED")

            mismatch = module._external_finish_request(finish, "other", 123, now, 2.0)
            self.assertFalse(mismatch["requested"])
            self.assertEqual(mismatch["reason"], "run_id_mismatch")

            stale = module._external_finish_request(finish, "pilot-a", 123, now + 3_000_000_000, 2.0)
            self.assertFalse(stale["requested"])
            self.assertEqual(stale["reason"], "finish_request_stale")

    def test_finish_request_rejects_malformed_without_crashing(self):
        module = self._load_module()
        with tempfile.TemporaryDirectory() as tmp:
            finish = Path(tmp) / "finish_request.json"
            now = time.monotonic_ns()
            cases = [
                ([], "request_not_object"),
                ({
                    "schema_version": 1,
                    "run_id": "pilot-a",
                    "request_id": "",
                    "observed_run_epoch_ns": 123,
                    "requested_at_monotonic_ns": now,
                    "backend_terminal_status": "FINISHED",
                }, "invalid_request_id"),
                ({
                    "schema_version": 1,
                    "run_id": "pilot-a",
                    "request_id": "req-1",
                    "observed_run_epoch_ns": "123",
                    "requested_at_monotonic_ns": now,
                    "backend_terminal_status": "FINISHED",
                }, "invalid_observed_run_epoch_ns"),
                ({
                    "schema_version": 1,
                    "run_id": "pilot-a",
                    "request_id": "req-1",
                    "observed_run_epoch_ns": 123,
                    "requested_at_monotonic_ns": True,
                    "backend_terminal_status": "FINISHED",
                }, "missing_requested_at_monotonic_ns"),
            ]
            for payload, reason in cases:
                finish.write_text(json.dumps(payload), encoding="utf-8")
                result = module._external_finish_request(finish, "pilot-a", 123, now, 2.0)
                self.assertFalse(result["requested"])
                self.assertEqual(result["reason"], reason)

            finish.write_text("{bad json", encoding="utf-8")
            result = module._external_finish_request(finish, "pilot-a", 123, now, 2.0)
            self.assertFalse(result["requested"])
            self.assertTrue(result["reason"].startswith("invalid_json"))

    def test_finish_latches_once_and_survives_low_rtf_dwell(self):
        module = self._load_module()
        first = {
            "requested": True,
            "status": "EXTERNAL_EPISODE_FINISHED",
            "request": {
                "run_id": "pilot-a",
                "request_id": "req-1",
                "observed_run_epoch_ns": 123,
                "backend_terminal_status": "FINISHED",
            },
        }
        latched, dwell_start, status = module._external_finish_step(
            None, first, True, True, 10.0, 1.0
        )
        self.assertIsNotNone(latched)
        self.assertEqual(dwell_start, 10.0)
        self.assertIsNone(status)

        expired_if_rechecked = {
            "requested": False,
            "reason": "finish_request_stale",
            "request": {
                "run_id": "pilot-a",
                "request_id": "req-1",
            },
        }
        latched, dwell_start, status = module._external_finish_step(
            latched, expired_if_rechecked, True, True, 11.1, 1.0
        )
        self.assertEqual(status, "EXTERNAL_EPISODE_FINISHED")
        self.assertEqual(dwell_start, 10.0)

    def test_nonzero_command_interrupts_external_dwell(self):
        module = self._load_module()
        finish = {
            "requested": True,
            "status": "EXTERNAL_EPISODE_FINISHED",
            "request": {
                "run_id": "pilot-a",
                "request_id": "req-1",
                "observed_run_epoch_ns": 123,
                "backend_terminal_status": "FINISHED",
            },
        }
        latched, dwell_start, status = module._external_finish_step(
            None, finish, True, True, 1.0, 1.0
        )
        self.assertEqual(dwell_start, 1.0)
        self.assertIsNone(status)
        latched, dwell_start, status = module._external_finish_step(
            latched, {"requested": True, "status": "EXTERNAL_EPISODE_FINISHED"}, False, True, 1.5, 1.0
        )
        self.assertIsNone(dwell_start)
        self.assertIsNone(status)
        latched, dwell_start, status = module._external_finish_step(
            latched, {"requested": True, "status": "EXTERNAL_EPISODE_FINISHED"}, True, True, 2.0, 1.0
        )
        self.assertEqual(dwell_start, 2.0)
        self.assertIsNone(status)
        latched, dwell_start, status = module._external_finish_step(
            latched, {"requested": True, "status": "EXTERNAL_EPISODE_FINISHED"}, True, True, 3.0, 1.0
        )
        self.assertEqual(status, "EXTERNAL_EPISODE_FINISHED")

    def test_zero_command_uses_horizontal_norm_boundary(self):
        module = self._load_module()
        self.assertTrue(module._external_zero_command((0.006, 0.008, 0.01), 0.01))
        self.assertFalse(module._external_zero_command((0.008, 0.008, 0.0), 0.01))
        self.assertFalse(module._external_zero_command((0.0, 0.0, 0.011), 0.01))

    def test_dwell_does_not_start_before_valid_request_identity(self):
        module = self._load_module()
        latched, dwell_start, status = module._external_finish_step(
            None, {"requested": False, "reason": "run_id_mismatch"}, True, True, 1.0, 1.0
        )
        self.assertIsNone(latched)
        self.assertIsNone(dwell_start)
        self.assertIsNone(status)
        valid = {
            "requested": True,
            "status": "EXTERNAL_EPISODE_FINISHED",
            "request": {
                "run_id": "pilot-a",
                "request_id": "req-2",
                "observed_run_epoch_ns": 123,
                "backend_terminal_status": "FINISHED",
            },
        }
        latched, dwell_start, status = module._external_finish_step(
            None, valid, True, True, 2.0, 1.0
        )
        self.assertEqual(dwell_start, 2.0)
        self.assertIsNone(status)

    def test_external_args_reject_nan_and_infinite_bounds(self):
        module = self._load_module()
        base = dict(
            external_goal_mode=True,
            external_run_id="pilot-a",
            external_finish_stillness_seconds=1.0,
            external_status_freshness_seconds=2.0,
            terminal_command_norm=0.01,
            terminal_speed_mps=0.10,
            terminal_yaw_rate_radps=0.15,
        )
        module._validate_external_goal_args(Namespace(**base))
        for key, value in [
            ("external_finish_stillness_seconds", math.nan),
            ("external_status_freshness_seconds", math.inf),
            ("terminal_command_norm", -0.01),
            ("terminal_speed_mps", math.nan),
            ("terminal_yaw_rate_radps", math.inf),
        ]:
            bad = dict(base)
            bad[key] = value
            with self.assertRaises(ValueError):
                module._validate_external_goal_args(Namespace(**bad))

    def test_request_identity_and_exit_codes(self):
        module = self._load_module()
        check = {
            "requested": True,
            "status": "EXTERNAL_EPISODE_FAILED",
            "request": {
                "run_id": "pilot-a",
                "request_id": "req-7",
                "observed_run_epoch_ns": 123,
                "backend_terminal_status": "FAILED",
            },
        }
        self.assertEqual(module._external_request_identity(check), {
            "run_id": "pilot-a",
            "request_id": "req-7",
            "observed_run_epoch_ns": 123,
            "backend_terminal_status": "FAILED",
        })
        self.assertEqual(module._external_exit_code("EXTERNAL_EPISODE_FINISHED", lambda status: 99), 0)
        self.assertEqual(module._external_exit_code("EXTERNAL_EPISODE_FAILED", lambda status: 99), 3)
        self.assertEqual(module._external_exit_code("DURATION_REACHED", lambda status: 0), 0)

    def test_parser_default_preserves_legacy_mode(self):
        module = self._load_module()
        args = module.build_parser().parse_args([
            "--scene", "building.usda",
            "--runtime", "runtime",
            "--checkpoint", "policy.pt",
            "--route-artifact", "route.json",
            "--scope", "scope.json",
            "--execution-manifest", "manifest.json",
            "--output", "run",
            "--case", "flat_nominal",
            "--duration-seconds", "10",
        ])
        self.assertFalse(args.external_goal_mode)
        self.assertIsNone(args.external_run_id)
        self.assertIsNone(args.external_control_dir)
        args.external_finish_stillness_seconds = math.nan
        module._validate_external_goal_args(args)

    def test_default_mode_is_explicitly_false(self):
        data = materializer.load_and_patch(materializer.REPO_ROOT / materializer.SOURCE_REL)
        self.assertIn(
            'parser.add_argument("--external-goal-mode", action="store_true", default=False,',
            data["patched_text"],
        )
        self.assertIn(
            '"route_artifact_role": (',
            data["patched_text"],
        )
        self.assertIn(
            "spawn and legacy metric metadata only; it is not a command target in external-goal mode",
            data["patched_text"],
        )
        self.assertIn("legacy fixed-goal metric and terminal target", data["patched_text"])
        self.assertIn('"base_xyz": [float(v) for v in position]', data["patched_text"])
        self.assertIn('"base_quat_wxyz": [qw, qx, qy, qz]', data["patched_text"])
        self.assertIn('"command_obs_error": command_obs_error', data["patched_text"])
        bottom_order = (
            'status = "EXCESSIVE_TILT"\n'
            "                    break\n"
            "                if external_finish_ready_status is not None:\n"
            "                    status = external_finish_ready_status\n"
            "                    break\n"
        )
        self.assertIn(bottom_order, data["patched_text"])


if __name__ == "__main__":
    unittest.main()
