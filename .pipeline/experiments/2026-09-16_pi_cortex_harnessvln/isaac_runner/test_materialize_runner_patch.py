import ast
import contextlib
import importlib.util
import io
import json
import math
import py_compile
import sys
import tempfile
import textwrap
import time
import types
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np

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
        self.assertEqual(args.stance_hold, "off")
        self.assertEqual(module.execution_configuration(args)["stance_hold"], "off")
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



EXECUTED_E03_RUNNER = (
    Path(__file__).resolve().parent
    / "two_goal_runs/two_goal_20260917T090126Z_scanfix_e03/returned_artifacts/runner_output/"
    "executed_run_pct_scan_building.py"
)
ROBOT_JOINTS = ["%s_%s_joint" % (leg, kind) for kind in ("HipX", "HipY", "Knee") for leg in ("FL", "FR", "HL", "HR")]
ACTION_JOINTS = ["%s_%s_joint" % (leg, kind) for leg in ("FL", "FR", "HL", "HR") for kind in ("HipX", "HipY", "Knee")]
DEFAULT_BY_KIND = {"HipX": 0.0, "HipY": -0.8, "Knee": 1.6}
FOOT_IDS = [4, 8, 12, 16]


class DelayedPDActuator:
    pass


class Lite3Actuator(DelayedPDActuator):
    def __init__(self, ids, effort, lag=2):
        import torch
        count = len(ids)
        self.joint_indices = torch.tensor(ids)
        self.stiffness = torch.full((1, count), 20.0)
        self.damping = torch.full((1, count), 0.5)
        self.effort_limit = torch.full((1, count), float(effort))
        self.positions_delay_buffer = types.SimpleNamespace(time_lags=torch.tensor([lag], dtype=torch.int32))
        self.cfg = types.SimpleNamespace(min_delay=0, max_delay=4)


class ImplicitActuator:
    def __init__(self, ids):
        import torch
        count = len(ids)
        self.joint_indices = torch.tensor(ids)
        self.stiffness = torch.full((1, count), 20.0)
        self.damping = torch.full((1, count), 0.5)
        self.effort_limit = torch.full((1, count), 24.0)


class LostWriteActuator(Lite3Actuator):
    """Every read returns a fresh copy, so gain writes never reach the actuator."""

    @property
    def stiffness(self):
        return self._stiffness.clone()

    @stiffness.setter
    def stiffness(self, value):
        self._stiffness = value


LostWriteActuator.__name__ = "Lite3Actuator"


class FakeView:
    def __init__(self):
        import torch
        self.stiffness = torch.zeros(1, 12)
        self.damping = torch.zeros(1, 12)

    def get_dof_stiffnesses(self):
        return self.stiffness

    def get_dof_dampings(self):
        return self.damping


def fake_isaac(actuator_factory=None):
    import torch
    hip = [i for i, name in enumerate(ROBOT_JOINTS) if "_Hip" in name]
    knee = [i for i, name in enumerate(ROBOT_JOINTS) if "_Knee" in name]
    default = torch.tensor([[DEFAULT_BY_KIND[name.split("_")[1]] for name in ROBOT_JOINTS]])
    limits = torch.stack([torch.full((12,), -3.0), torch.full((12,), 3.0)], dim=-1).unsqueeze(0)
    data = types.SimpleNamespace(
        joint_pos=default.clone() + torch.linspace(-0.02, 0.02, 12),
        joint_vel=torch.zeros(1, 12),
        default_joint_pos=default,
        root_lin_vel_w=torch.tensor([[0.01, 0.0, 0.0]]),
        root_ang_vel_w=torch.tensor([[0.0, 0.0, 0.05]]),
        projected_gravity_b=torch.tensor([[0.0, 0.0, -1.0]]),
        applied_torque=torch.zeros(1, 12),
        computed_torque=torch.zeros(1, 12),
        joint_stiffness=torch.zeros(1, 12),
        joint_damping=torch.zeros(1, 12),
        joint_pos_limits=limits,
    )
    factory = actuator_factory or (lambda ids, effort: Lite3Actuator(ids, effort))
    robot = types.SimpleNamespace(
        joint_names=list(ROBOT_JOINTS),
        data=data,
        actuators={"Hip": factory(hip, 24.0), "Knee": factory(knee, 36.0)},
        root_physx_view=FakeView(),
    )
    action_ids = [ROBOT_JOINTS.index(name) for name in ACTION_JOINTS]
    term = types.SimpleNamespace(
        _joint_ids=action_ids,
        _offset=default[:, action_ids].clone(),
        _scale=torch.full((1, 12), 0.25),
        _clip=torch.tensor([[[-100.0, 100.0]] * 12]),
    )

    def get_term(name):
        if name != "joint_pos":
            raise ValueError("unknown action term " + name)
        return term

    env = types.SimpleNamespace(action_manager=types.SimpleNamespace(get_term=get_term),
                                sim=types.SimpleNamespace(current_time=0.0))
    wrapped = types.SimpleNamespace(clip_actions=None)
    forces = torch.zeros(1, 17, 3)
    for index in FOOT_IDS:
        forces[0, index, 2] = 30.0
    contact = types.SimpleNamespace(data=types.SimpleNamespace(net_forces_w=forces))
    return env, robot, wrapped, contact, term


def processed_robot_target(term, action):
    """What the V12 JointPositionAction sets as the joint target, in robot order."""
    import numpy as np
    processed = (action * term._scale + term._offset)[0].numpy().astype(np.float64)
    target = np.empty(12)
    target[term._joint_ids] = processed
    return target


class StanceHoldPatchTests(unittest.TestCase):
    def setUp(self):
        self.data = materializer.load_and_patch(materializer.REPO_ROOT / materializer.SOURCE_REL)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        runner = self.tmp / "run_pct_scan_building.py"
        runner.write_text(self.data["patched_text"], encoding="utf-8")
        spec = importlib.util.spec_from_file_location("patched_runner_stance", str(runner))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    # -- off path equivalence -------------------------------------------------
    def test_external_only_anchors_reproduce_the_executed_runner(self):
        self.assertEqual(self.data["external_only_sha256"], materializer.EXTERNAL_ONLY_PATCHED_SHA256)
        if EXECUTED_E03_RUNNER.is_file():
            self.assertEqual(materializer.sha256_file(EXECUTED_E03_RUNNER), materializer.EXTERNAL_ONLY_PATCHED_SHA256)
        checks = materializer.verify_patch(self.data)
        self.assertTrue(checks["external_only_matches_executed_runner"])
        self.assertEqual(checks["duplicate_top_level_definitions"], [])

    def test_stance_anchors_are_the_only_other_differences(self):
        source = self.data["source_text"]
        external = materializer.apply_patch_text(source, include_stance_hold=False, include_scripted_walk=False)
        module = materializer.load_stance_hold_module()
        script_module = materializer.load_command_script_module()
        removed = self.data["patched_text"]
        # Undo the scripted-walk group first (it anchors on stance-hold output), then the stance group.
        groups = (materializer._scripted_walk_replacements(script_module),
                  materializer._stance_hold_replacements(module))
        for group in groups:
            for item in reversed(group):
                self.assertEqual(removed.count(item["new"]), 1, item["name"])
                removed = removed.replace(item["new"], item["old"], 1)
            if group is groups[0]:
                self.assertEqual(removed, materializer.apply_patch_text(source, include_scripted_walk=False))
        self.assertEqual(removed, external)
        with self.assertRaises(ValueError):
            materializer.apply_patch_text(source, include_stance_hold=False)

    def test_off_branch_is_todays_statement_right_after_the_policy(self):
        text = self.data["patched_text"]
        expected = (
            "                    status = \"NONFINITE\"\n"
            "                    break\n"
            + materializer.STANCE_HOLD_STEP_BRANCH
            + "\n                sim_time = float(env.sim.current_time) - initial_sim_time\n"
        )
        self.assertIn(expected, text)
        self.assertTrue(materializer.STANCE_HOLD_STEP_BRANCH.endswith(
            "                else:\n                    previous_actions = actions\n"))
        self.assertEqual(text.count("previous_actions = "), 3)
        self.assertEqual(self.data["source_text"].count("previous_actions = "), 2)

    def test_hold_calls_are_reachable_only_through_the_active_branch(self):
        tree = ast.parse(self.data["patched_text"])
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_run")
        calls = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id.startswith("_stance_hold_"):
                calls.setdefault(node.func.id, []).append(node)

        def enclosing_function(node):
            while node in parents:
                node = parents[node]
                if isinstance(node, ast.FunctionDef):
                    return node.name
            return None

        def guarded(node):
            while node in parents:
                parent = parents[node]
                if isinstance(parent, ast.If) and node in parent.body and ast.unparse(parent.test) == "stance_hold_runtime['active']":
                    return True
                node = parent
            return False

        step_calls = calls["_stance_hold_control_step"]
        self.assertEqual(len(step_calls), 1)
        self.assertEqual(enclosing_function(step_calls[0]), "_run")
        self.assertTrue(guarded(step_calls[0]))
        self.assertEqual({enclosing_function(n) for n in calls["_stance_hold_write_gains"]}, {"_stance_hold_control_step"})
        in_run = sorted({name for name, nodes in calls.items() for n in nodes if enclosing_function(n) == "_run"})
        self.assertEqual(in_run, ["_stance_hold_control_step", "_stance_hold_row", "_stance_hold_setup", "_stance_hold_summary"])
        self.assertIsNotNone(run)

    def run_branch(self, runtime, control_step, steps=3):
        body = textwrap.indent(textwrap.dedent(materializer.STANCE_HOLD_STEP_BRANCH), " " * 8)
        source = (
            "def probe(stance_hold_runtime, robot, contact, foot_ids, actions, command, env, initial_sim_time):\n"
            "    status = 'RUNNING'\n"
            "    previous_actions = None\n"
            "    for step in range(%d):\n" % steps
            + body
            + "    return previous_actions, status\n"
        )
        namespace = {"_stance_hold_control_step": control_step, "StanceHoldError": self.module.StanceHoldError}
        exec(compile(source, "stance_step_branch", "exec"), namespace)
        env = types.SimpleNamespace(sim=types.SimpleNamespace(current_time=1.5))
        return namespace["probe"](runtime, "robot", "contact", FOOT_IDS, "actions", (0.0, 0.0, 0.0), env, 0.5)

    def test_off_branch_executes_todays_assignment_only(self):
        def must_not_run(*args, **kwargs):
            raise AssertionError("control step called in off mode")

        actions = object()
        body = textwrap.indent(textwrap.dedent(materializer.STANCE_HOLD_STEP_BRANCH), " " * 4)
        namespace = {"_stance_hold_control_step": must_not_run, "StanceHoldError": self.module.StanceHoldError,
                     "stance_hold_runtime": {"active": False}, "actions": actions}
        exec(compile("for step in range(4):\n" + body, "off_branch", "exec"), namespace)
        self.assertIs(namespace["previous_actions"], actions)
        self.assertEqual(namespace["stance_hold_runtime"], {"active": False})

    def test_auto_branch_uses_control_step_and_stops_on_hold_error(self):
        calls = []

        def control_step(*args):
            calls.append(args)
            return "applied-%d" % len(calls)

        runtime = {"active": True, "failure": None}
        previous, status = self.run_branch(runtime, control_step)
        self.assertEqual((previous, status), ("applied-3", "RUNNING"))
        self.assertEqual(calls[0], (runtime, "robot", "contact", FOOT_IDS, "actions", (0.0, 0.0, 0.0), 1.0))

        def failing(*args):
            raise self.module.StanceHoldError("joint_pos is not finite")

        previous, status = self.run_branch(runtime, failing)
        self.assertEqual((previous, status), (None, "NONFINITE"))
        self.assertEqual(runtime["failure"], {"type": "StanceHoldError", "message": "joint_pos is not finite", "step": 0})

    # -- runner glue with fake Isaac objects -----------------------------------
    def test_off_setup_records_contract_and_never_writes_gains(self):
        env, robot, wrapped, contact, term = fake_isaac()
        versions = {name: (a.stiffness._version, a.damping._version) for name, a in robot.actuators.items()}
        runtime = self.module._stance_hold_setup("off", env, robot, wrapped, self.tmp)
        self.assertFalse(runtime["active"])
        record = json.loads((self.tmp / "stance_hold_setup.json").read_text())
        self.assertEqual(record["mode"], "off")
        self.assertIsNone(record["inspection_error"])
        self.assertEqual(record["inspection"]["action_term"]["joint_names"], ACTION_JOINTS)
        self.assertEqual(record["inspection"]["actuators"]["Hip"]["position_delay_time_lags"], [2])
        self.assertEqual(record["module"]["sha256"], self.data["stance_hold_module"]["sha256"])
        robot.data.applied_torque[0, 11] = 18.0
        robot.data.computed_torque[0, 11] = 40.0
        robot.data.computed_torque[0, 11 - 1] = 0.5
        for _ in range(5):
            row = self.module._stance_hold_row(runtime, robot)
        self.assertEqual(row["stance_hold"], "off")
        self.assertEqual(row["stance_mode"], "OFF")
        self.assertTrue(row["policy_owns_joints"])
        self.assertAlmostEqual(row["applied_torque_max_ratio"], 0.5)
        self.assertEqual(row["torque_clip_joint_count"], 2)
        self.assertNotIn("applied_target", row)
        summary = self.module._stance_hold_summary(runtime)
        self.assertEqual((summary["mode"], summary["gain_writes"], summary["fsm"]), ("off", 0, None))
        self.assertEqual(versions, {name: (a.stiffness._version, a.damping._version) for name, a in robot.actuators.items()})

    def test_off_setup_tolerates_a_broken_contract(self):
        env, robot, wrapped, contact, term = fake_isaac(lambda ids, effort: ImplicitActuator(ids))
        env.action_manager.get_term = lambda name: (_ for _ in ()).throw(KeyError(name))
        runtime = self.module._stance_hold_setup("off", env, robot, wrapped, self.tmp)
        record = json.loads((self.tmp / "stance_hold_setup.json").read_text())
        self.assertIn("KeyError", record["inspection_error"])
        self.assertIsNone(runtime["effort_limit"])
        self.assertEqual(self.module._stance_hold_row(runtime, robot), {
            "stance_hold": "off", "stance_mode": "OFF", "policy_owns_joints": True})

    def test_auto_setup_fails_closed(self):
        import torch

        def stiff(env, robot, wrapped, term):
            robot.actuators["Hip"].stiffness[0, 0] = 25.0

        def implicit(env, robot, wrapped, term):
            robot.actuators["Knee"] = ImplicitActuator(robot.actuators["Knee"].joint_indices.tolist())

        def physx(env, robot, wrapped, term):
            robot.data.joint_stiffness[0, 3] = 20.0

        def scale(env, robot, wrapped, term):
            term._scale = torch.full((1, 12), 0.5)

        def order(env, robot, wrapped, term):
            term._joint_ids = [0] * 12

        def limits(env, robot, wrapped, term):
            del robot.data.joint_pos_limits

        def group(env, robot, wrapped, term):
            robot.actuators["Legs"] = robot.actuators.pop("Knee")

        def clip(env, robot, wrapped, term):
            wrapped.clip_actions = float("nan")

        def delayed_base(env, robot, wrapped, term):
            robot.actuators["Hip"] = types.SimpleNamespace(**vars(robot.actuators["Hip"]))

        cases = {"stiffness": stiff, "not an explicit": implicit, "PhysX joint drive": physx,
                 "action scale": scale, "not a permutation": order, "limits are unavailable": limits,
                 "actuator groups": group, "clip_actions": clip, "expected Lite3Actuator": delayed_base}
        for expected, mutate in cases.items():
            with self.subTest(case=expected):
                env, robot, wrapped, contact, term = fake_isaac()
                mutate(env, robot, wrapped, term)
                out = self.tmp / expected.replace(" ", "_")
                out.mkdir()
                with self.assertRaisesRegex(self.module.AdapterFailure, expected):
                    self.module._stance_hold_setup("auto", env, robot, wrapped, out)
                record = json.loads((out / "stance_hold_setup.json").read_text())
                self.assertTrue(any(expected in problem for problem in record["validation_problems"]))
        with self.assertRaises(self.module.AdapterFailure):
            self.module._stance_hold_setup("on", *fake_isaac()[:3], self.tmp)

    def drive(self, runtime, env, robot, contact, term, steps, command=(0.0, 0.0, 0.0), action_value=0.1, start=0):
        import torch
        rows = []
        for step in range(start, start + steps):
            actions = torch.full((1, 12), action_value)
            now = 0.02 * (step + 1)
            prev_kp = {name: a.stiffness.clone() for name, a in robot.actuators.items()}
            applied = self.module._stance_hold_control_step(runtime, robot, contact, FOOT_IDS, actions, command, now)
            row = self.module._stance_hold_row(runtime, robot)
            rows.append({"step": step, "now": now, "actions": actions, "applied": applied, "row": row,
                         "prev_kp": prev_kp, "target": processed_robot_target(term, applied)})
        return rows

    def test_auto_hold_maps_joint_orders_writes_gains_and_rejoins(self):
        import numpy as np
        env, robot, wrapped, contact, term = fake_isaac()
        runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, self.tmp)
        record = json.loads((self.tmp / "stance_hold_setup.json").read_text())
        self.assertEqual(record["validation_problems"], [])
        np.testing.assert_allclose(runtime["applied_target"], robot.data.default_joint_pos[0].numpy())
        hip, knee = robot.actuators["Hip"], robot.actuators["Knee"]
        q = robot.data.joint_pos[0].numpy().astype(np.float64)

        # Stop at the entry step so the actuator state can be checked there.
        rows = []
        while not rows or rows[-1]["row"]["stance_mode"] != "STAND_TRANSITION":
            self.assertLess(len(rows), 30)
            rows += self.drive(runtime, env, robot, contact, term, 1, start=len(rows))
        entry = len(rows) - 1
        for r in rows[:entry]:
            self.assertIs(r["applied"], r["actions"])
            self.assertTrue(r["row"]["policy_owns_joints"])
            self.assertFalse(r["row"]["stance_gains_written"])
        e = rows[entry]
        policy_robot = rows[entry - 1]["target"]
        effort = np.array([24.0] * 8 + [36.0] * 4)
        base_ratio = float(np.max(np.abs(20.0 * (policy_robot - q)) / effort))
        # Entry step (PRD D4 gain ramp at blend 0): the hold owns the joints but
        # repeats the previous applied target at the V12 gains, so nothing is written.
        # Before D4 this step already wrote Kp 60 / Kd 1.
        self.assertIsNot(e["applied"], e["actions"])
        self.assertFalse(e["row"]["stance_gains_written"])
        self.assertEqual(e["row"]["applied_kp_mean"], 20.0)
        self.assertTrue(torch_all_equal(hip.stiffness, 20.0) and torch_all_equal(knee.damping, 0.5))
        np.testing.assert_allclose(e["target"], policy_robot, atol=2e-6)
        np.testing.assert_allclose(e["target"], np.asarray(e["row"]["applied_target"]), atol=2e-6)
        self.assertGreater(float(np.max(np.abs(20.0 * (policy_robot - q)))), 0.4)
        self.assertAlmostEqual(e["row"]["delayed_target_torque_max_ratio_estimate"], base_ratio, places=5)
        self.assertEqual(runtime["gain_writes"], 0)
        ramp_end_step = entry + 26
        rows += self.drive(runtime, env, robot, contact, term, ramp_end_step - len(rows), start=len(rows))
        ramp = rows[entry + 1: entry + 26]
        self.assertEqual([r["row"]["stance_reason"] for r in ramp], ["entry_gain_ramp"] * 24 + ["entry_gain_ramp_complete"])
        previous_kp = 20.0
        for r in ramp:
            # Every ramp step writes gains, and Kp * (target - q0) stays the entry stiffness
            # torque in robot joint order (the fake joints do not move, so q0 = q).
            self.assertTrue(r["row"]["stance_gains_written"])
            kp = r["row"]["applied_kp_mean"]
            self.assertGreater(kp, previous_kp)
            np.testing.assert_allclose(kp * (r["target"] - q), 20.0 * (policy_robot - q), atol=1e-4)
            # Kp_k on the delayed previous target: within the step-ratio bound of the ramp.
            self.assertLessEqual(r["row"]["delayed_target_torque_max_ratio_estimate"], base_ratio * 1.0729 + 1e-6)
            previous_kp = kp
        self.assertEqual(runtime["gain_writes"], 25)
        self.assertEqual(runtime["physx_after_first_gain_write"]["problems"], [])
        end = ramp[-1]
        self.assertTrue(torch_all_equal(hip.stiffness, 60.0) and torch_all_equal(knee.damping, 1.0))
        np.testing.assert_allclose(60.0 * (end["target"] - q), 20.0 * (policy_robot - q), atol=1e-4)
        self.assertLessEqual(max(r["row"]["delayed_target_torque_max_ratio_estimate"] for r in rows[entry:]),
                             base_ratio * 1.0729 + 1e-6)
        version = hip.stiffness._version
        after = self.drive(runtime, env, robot, contact, term, 140 - ramp_end_step, start=ramp_end_step)
        rows += after
        self.assertEqual(rows[-1]["row"]["stance_mode"], "FIXED_STAND")
        self.assertFalse(any(r["row"]["stance_gains_written"] for r in after))
        self.assertEqual(runtime["gain_writes"], 25)
        self.assertEqual(hip.stiffness._version, version)
        np.testing.assert_allclose(rows[-1]["target"], end["target"], atol=2e-6)

        move = self.drive(runtime, env, robot, contact, term, 16, command=(0.3, 0.0, 0.0), action_value=-0.2, start=140)
        modes = [r["row"]["stance_mode"] for r in move]
        self.assertEqual(modes[0], "REJOIN")
        self.assertEqual(modes[-3:], ["RL", "RL", "RL"])
        final = move[modes.index("RL")]
        self.assertIs(final["applied"], final["actions"])
        self.assertTrue(torch_all_equal(hip.stiffness, 20.0) and torch_all_equal(knee.damping, 0.5))
        self.assertGreater(runtime["gain_writes"], 10)
        summary = self.module._stance_hold_summary(runtime)
        pairs = [(t["from"], t["to"]) for t in summary["fsm"]["transitions"]]
        self.assertEqual(pairs, [("RL", "STAND_SETTLING"), ("STAND_SETTLING", "STAND_TRANSITION"),
                                 ("STAND_TRANSITION", "FIXED_STAND"), ("FIXED_STAND", "REJOIN"), ("REJOIN", "RL")])
        self.assertLessEqual(summary["gain_readback_max_abs_error"], 1e-5)
        json.dumps(summary)
        json.dumps([r["row"] for r in rows + move])

    def test_entry_kd_variants_in_the_runner_glue(self):
        import numpy as np
        for variant, entry_kd in (("ramp", 0.5), ("step1", 1.0), ("step2p5", 2.5)):
            with self.subTest(variant=variant):
                env, robot, wrapped, contact, term = fake_isaac()
                out = self.tmp / variant
                out.mkdir()
                runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, out, entry_kd=variant)
                self.assertEqual(json.loads((out / "stance_hold_setup.json").read_text())["entry_kd"], variant)
                hip, knee = robot.actuators["Hip"], robot.actuators["Knee"]
                rows = []
                while not rows or rows[-1]["row"]["stance_mode"] != "STAND_TRANSITION":
                    self.assertLess(len(rows), 30)
                    rows += self.drive(runtime, env, robot, contact, term, 1, start=len(rows))
                entry = rows[-1]["row"]
                # ramp writes nothing at entry; the step variants write a Kd-only change.
                self.assertEqual(entry["stance_gains_written"], variant != "ramp")
                self.assertEqual(runtime["gain_writes"], 0 if variant == "ramp" else 1)
                self.assertEqual(entry["applied_kp_mean"], 20.0)
                self.assertAlmostEqual(entry["applied_kd_mean"], entry_kd)
                self.assertTrue(torch_all_equal(hip.stiffness, 20.0) and torch_all_equal(knee.stiffness, 20.0))
                self.assertTrue(torch_all_equal(hip.damping, entry_kd) and torch_all_equal(knee.damping, entry_kd))
                np.testing.assert_allclose(rows[-1]["target"], rows[-2]["target"], atol=2e-6)
                start = len(rows)
                rows += self.drive(runtime, env, robot, contact, term, 101, start=start)
                modes = [r["row"]["stance_mode"] for r in rows[start:]]
                self.assertEqual(modes[-1], "FIXED_STAND")
                self.assertEqual(modes.count("STAND_TRANSITION"), 99)
                self.assertTrue(torch_all_equal(hip.stiffness, 60.0) and torch_all_equal(knee.damping, 1.0))
                kds = [r["row"]["applied_kd_mean"] for r in rows[start - 1:]]
                if variant == "step1":
                    self.assertEqual(set(kds), {1.0})
                if variant == "step2p5":
                    self.assertEqual(kds[:25], [2.5] * 25)
                    self.assertEqual(kds[-1], 1.0)
                summary = self.module._stance_hold_summary(runtime)
                self.assertEqual((summary["entry_kd"], summary["fsm"]["entry_kd"]), (variant, variant))
        with self.assertRaisesRegex(self.module.AdapterFailure, "stance-entry-kd"):
            self.module._stance_hold_setup("auto", *fake_isaac()[:3], self.tmp, entry_kd="step3")
        off = self.module._stance_hold_setup("off", *fake_isaac()[:3], self.tmp)
        self.assertEqual(self.module._stance_hold_summary(off)["entry_kd"], "ramp")

    def test_auto_hold_fails_on_lost_gain_write_and_physx_drift(self):
        env, robot, wrapped, contact, term = fake_isaac(lambda ids, effort: LostWriteActuator(ids, effort))
        runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, self.tmp)
        with self.assertRaisesRegex(self.module.AdapterFailure, "read-back"):
            self.drive(runtime, env, robot, contact, term, 30)

        env, robot, wrapped, contact, term = fake_isaac()
        runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, self.tmp)
        robot.root_physx_view.stiffness[0, 0] = 60.0
        with self.assertRaisesRegex(self.module.AdapterFailure, "PhysX joint drive"):
            self.drive(runtime, env, robot, contact, term, 30)

    def test_auto_hold_nonfinite_state_and_clip_bound(self):
        env, robot, wrapped, contact, term = fake_isaac()
        runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, self.tmp)
        self.drive(runtime, env, robot, contact, term, 3)
        robot.data.joint_vel[0, 5] = float("nan")
        with self.assertRaises(self.module.StanceHoldError):
            self.drive(runtime, env, robot, contact, term, 1, start=3)

        env, robot, wrapped, contact, term = fake_isaac()
        wrapped.clip_actions = 0.05
        runtime = self.module._stance_hold_setup("auto", env, robot, wrapped, self.tmp)
        with self.assertRaisesRegex(self.module.AdapterFailure, "clip_actions"):
            self.drive(runtime, env, robot, contact, term, 30, action_value=0.8)

    def test_materializer_check_records_both_anchor_groups(self):
        payload = materializer.write_outputs(Namespace(
            source=None, output=self.tmp / "runner.py", patch=self.tmp / "p.patch",
            hashes=self.tmp / "h.json", allow_source_sha=False, check=True))
        self.assertEqual(payload["verification"]["external_only_matches_executed_runner"], True)
        self.assertIn("stance_hold_step", payload["anchor_groups"]["stance_hold"])
        self.assertIn("stand_probe_duration_cap_60s", payload["anchor_groups"]["stance_hold"])
        self.assertEqual(payload["stance_hold_default"], "off")
        self.assertEqual(materializer.sha256_file(self.tmp / "runner.py"), payload["patched_sha256"])
        self.assertIn("scripted_walk_command", payload["anchor_groups"]["scripted_walk"])
        self.assertEqual((payload["stance_entry_kd_default"], payload["camera_heading_mode_default"],
                          payload["command_script_default"]), ("ramp", "body", None))
        self.assertEqual(payload["command_script_module"]["sha256"],
                         materializer.sha256_file(materializer.COMMAND_SCRIPT_MODULE))
        for key in ("scripted_walk_command_branch_present", "default_camera_heading_body",
                    "default_stance_entry_kd_ramp", "default_command_script_none"):
            self.assertTrue(payload["verification"][key], key)


D5_SCRIPT = Path(__file__).resolve().parent / "command_scripts/walk_stop_start_stop_v1.json"
LEGACY_ARGV = [
    "--scene", "building.usda", "--runtime", "runtime", "--checkpoint", "policy.pt",
    "--route-artifact", "route.json", "--scope", "scope.json", "--execution-manifest", "manifest.json",
    "--output", "run", "--duration-seconds", "10",
]
NATIVE_LIMIT_ARGV = ["--max-vx", "1.0", "--max-vy", "0.35", "--max-wz", "1.0", "--max-horizontal-norm", "1.0",
                     "--speed-profile", "speed_1p0"]


def extract_block(text, start, end):
    """Dedented source from the line containing `start` up to (not including) the line containing `end`."""
    first = text.index(start)
    first = text.rindex("\n", 0, first) + 1
    last = text.index(end, first)
    last = text.rindex("\n", 0, last) + 1
    return textwrap.dedent(text[first:last])


class ScriptedWalkPatchTests(unittest.TestCase):
    """PRD D5 anchors on the materialized runner, with fake inputs only."""

    def setUp(self):
        self.data = materializer.load_and_patch(materializer.REPO_ROOT / materializer.SOURCE_REL)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        runner = self.tmp / "run_pct_scan_building.py"
        runner.write_text(self.data["patched_text"], encoding="utf-8")
        spec = importlib.util.spec_from_file_location("patched_runner_walk", str(runner))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def parse(self, *extra, case="scripted_walk"):
        return self.module.build_parser().parse_args(LEGACY_ARGV + ["--case", case] + list(extra))

    def walk_args(self, *extra):
        return self.parse(*NATIVE_LIMIT_ARGV, "--command-script", str(D5_SCRIPT), *extra)

    def test_defaults_keep_the_previous_configuration(self):
        args = self.parse(case="flat_nominal")
        self.assertEqual((args.camera_heading_mode, args.stance_entry_kd, args.command_script),
                         ("body", "ramp", None))
        config = self.module.execution_configuration(args)
        self.assertNotIn("command_script", config)
        self.assertEqual((config["camera_heading_mode"], config["stance_entry_kd"]), ("body", "ramp"))
        self.module._scripted_walk_validate_args(args)
        self.assertEqual(self.module.CASES[-1], "scripted_walk")
        self.assertEqual(self.module.CASES[:4], ("stand_probe", "flat_nominal", "full_nominal", "native_nominal"))
        self.assertIsNone(self.module._scripted_walk_setup(args, {}))
        self.assertIsNone(self.module._scripted_walk_summary(None))
        # The command branch still zeroes stand_probe and leaves other cases alone.
        self.assertIn(materializer.SCRIPTED_WALK_COMMAND_BRANCH, self.data["patched_text"])
        self.assertEqual(self.data["patched_text"].count("script_segment, command = command_script_at("), 1)
        self.assertEqual(self.module.STANCE_ENTRY_KD_MODES, ("ramp", "step1", "step2p5"))
        self.assertEqual(self.module.SCRIPTED_WALK_CASE, "scripted_walk")

    def test_duration_caps(self):
        validate = self.module.validate_run_duration
        for case, cap in (("scripted_walk", 60.0), ("stand_probe", 60.0), ("flat_nominal", 45.0),
                          ("full_nominal", 180.0), ("native_nominal", 600.0)):
            with self.subTest(case=case):
                validate(case, cap)
                with self.assertRaises(ValueError):
                    validate(case, cap + 0.5)
        with self.assertRaises(ValueError):
            validate("scripted_walk", 0.0)

    def test_pre_isaac_validation(self):
        args = self.walk_args("--stance-hold", "auto", "--stance-entry-kd", "step2p5",
                              "--camera-heading-mode", "initial")
        self.module._scripted_walk_validate_args(args)
        self.module.validate_run_duration(args.case, 26.0)
        self.module.validate_motion_profile(args)
        bad = {
            "requires --command-script": self.parse(*NATIVE_LIMIT_ARGV),
            "only with --case scripted_walk": self.parse("--command-script", str(D5_SCRIPT), case="flat_nominal"),
            "exceeds the runner limit": self.parse("--command-script", str(D5_SCRIPT)),
            "applies only with --stance-hold auto": self.walk_args("--stance-entry-kd", "step1"),
        }
        for message, parsed in bad.items():
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.module._scripted_walk_validate_args(parsed)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.walk_args("--camera-heading-mode", "world")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.walk_args("--stance-entry-kd", "step2")
        main_text = extract_block(self.data["patched_text"], "    args = build_parser().parse_args(argv)\n",
                                  "    from .feedback_dropout import FeedbackDropout\n")
        self.assertLess(main_text.index("_scripted_walk_validate_args(args)"),
                        main_text.index("if args.case == \"native_nominal\""))

    def test_setup_binds_the_script_to_the_scope_and_records_it(self):
        args = self.walk_args("--output", str(self.tmp / "out"))
        (self.tmp / "out").mkdir()
        sha = materializer.sha256_file(D5_SCRIPT)
        with self.assertRaisesRegex(self.module.AdapterFailure, "differs from the frozen scope"):
            self.module._scripted_walk_setup(args, {"command_script_sha256": "0" * 64})
        with self.assertRaisesRegex(self.module.AdapterFailure, "differs from the frozen scope"):
            self.module._scripted_walk_setup(args, {})
        loaded = self.module._scripted_walk_setup(args, {"command_script_sha256": sha})
        self.assertEqual(loaded["sha256"], sha)
        self.assertEqual((self.tmp / "out/command_script.json").read_bytes(), D5_SCRIPT.read_bytes())
        record = json.loads((self.tmp / "out/scripted_walk_setup.json").read_text())
        self.assertEqual(record["command_script"]["sha256"], sha)
        self.assertEqual(record["module"]["sha256"], self.data["command_script_module"]["sha256"])
        self.assertEqual([s["t_start_s"] for s in record["script"]["segments"]], [0.0, 4.0, 7.0, 12.0, 14.5])
        self.assertEqual(self.module._scripted_walk_summary(loaded), record)
        json.dumps(self.module._scripted_walk_summary(loaded), allow_nan=False)
        stray = self.parse("--command-script", str(D5_SCRIPT), case="stand_probe")
        with self.assertRaisesRegex(self.module.AdapterFailure, "only with --case scripted_walk"):
            self.module._scripted_walk_setup(stray, {})
        invalid = self.parse("--command-script", str(D5_SCRIPT), "--output", str(self.tmp / "out"))
        with self.assertRaisesRegex(self.module.AdapterFailure, "command script is invalid"):
            self.module._scripted_walk_setup(invalid, {"command_script_sha256": sha})

    def run_command_block(self, args, scripted_walk, sim_times, snapshot_command=(0.25, 0.0, 0.1)):
        """Execute the patched loop-top command block as the runner does, with fake transport."""
        import torch
        block = extract_block(self.data["patched_text"],
                              "                snapshot = command_server.snapshot(time.monotonic_ns())\n",
                              "                contact_guard.begin(step)\n")
        self.assertIn("term.commands[:, 2] = command[2]", block)
        term = types.SimpleNamespace(commands=torch.zeros(1, 3))
        snapshot = types.SimpleNamespace(command=types.SimpleNamespace(
            vx=snapshot_command[0], vy=snapshot_command[1], wz=snapshot_command[2]))
        namespace = {
            "args": args, "scripted_walk": scripted_walk, "math": math, "time": time,
            "command_script_at": self.module.command_script_at, "AdapterFailure": self.module.AdapterFailure,
            "command_server": types.SimpleNamespace(snapshot=lambda now: snapshot),
            "env": types.SimpleNamespace(command_manager=types.SimpleNamespace(get_term=lambda name: term)),
            "first_nonzero_command_s": None,
        }
        code = compile(block, "command_block", "exec")
        results = []
        for sim_time in sim_times:
            namespace["sim_time"] = sim_time
            exec(code, namespace)
            actual = term.commands.clone()
            # The runner's post-step parity check, with a command manager that keeps the written command.
            expected = actual.new_tensor([namespace["command"]])
            self.assertTrue(torch.allclose(actual, expected, atol=1e-6, rtol=0.0))
            results.append((namespace["script_segment"], tuple(namespace["command"]),
                            namespace["horizontal_norm"], actual[0].tolist()))
        return results, namespace

    def test_scripted_command_replaces_tcp_command_before_admission_and_term_write(self):
        sha = materializer.sha256_file(D5_SCRIPT)
        args = self.walk_args("--output", str(self.tmp / "out"))
        (self.tmp / "out").mkdir()
        loaded = self.module._scripted_walk_setup(args, {"command_script_sha256": sha})
        times = [round(k * 0.02, 9) for k in range(1100)]
        results, namespace = self.run_command_block(args, loaded, times)
        segments = [r[0] for r in results]
        self.assertEqual([k for k in range(1, len(segments)) if segments[k] != segments[k - 1]], [200, 350, 600, 725])
        for k, (segment, command, norm, written) in enumerate(results):
            want = (0.6, 0.0, 0.0) if segment in (1, 3) else (0.0, 0.0, 0.0)
            self.assertEqual(command, want)
            self.assertAlmostEqual(norm, want[0])
            self.assertEqual(written, [float(np.float32(v)) for v in want])
        self.assertEqual(namespace["first_nonzero_command_s"], 4.0)
        # Other cases keep the TCP command; stand_probe keeps zeroing it.
        flat = self.parse(*NATIVE_LIMIT_ARGV, case="flat_nominal")
        results, _ = self.run_command_block(flat, None, [0.0, 4.0])
        self.assertEqual([r[:2] for r in results], [(None, (0.25, 0.0, 0.1))] * 2)
        stand = self.parse(case="stand_probe")
        results, namespace = self.run_command_block(stand, None, [0.0, 4.0])
        self.assertEqual([r[:2] for r in results], [(None, (0.0, 0.0, 0.0))] * 2)
        self.assertIsNone(namespace["first_nonzero_command_s"])
        # The unchanged admission check still guards the scripted command.
        tight = self.walk_args("--output", str(self.tmp / "out"))
        tight.max_horizontal_norm = 0.3
        with self.assertRaisesRegex(self.module.AdapterFailure, "exceeds the limit"):
            self.run_command_block(tight, loaded, [4.0])

    def test_scripted_finish_dwell_sees_the_zero_command_after_the_last_start(self):
        script = self.module.load_command_script(D5_SCRIPT, self.module._scripted_walk_limits(self.walk_args()))
        finish = {"requested": True, "status": "EXTERNAL_EPISODE_FINISHED", "request": {"request_id": "r"}}
        latched, status = None, None
        for k in range(1000, 1100):
            now = k * 0.02
            _segment, command = self.module.command_script_at(script["script"], now)
            zero = self.module._external_zero_command(command, 0.01)
            self.assertTrue(zero)
            latched, _start, status = self.module._external_finish_step(latched, finish, zero, True, now, 1.0)
            if status:
                break
        self.assertEqual(status, "EXTERNAL_EPISODE_FINISHED")
        self.assertAlmostEqual(now, 21.0)
        self.assertFalse(self.module._external_zero_command(
            self.module.command_script_at(script["script"], 13.0)[1], 0.01))

    def test_metrics_row_and_summary_anchors(self):
        text = self.data["patched_text"]
        self.assertIn(
            "                row.update(_stance_hold_row(stance_hold_runtime, robot))\n"
            "                if scripted_walk is not None:\n"
            "                    row[\"script_segment\"] = script_segment\n"
            "                # ---- complete body state, every control step ---------------\n", text)
        self.assertIn("            \"scripted_walk\": _scripted_walk_summary(scripted_walk),\n", text)
        self.assertIn("    scripted_walk = _scripted_walk_setup(args, scope)\n", text)
        self.assertLess(text.index("    scripted_walk = _scripted_walk_setup(args, scope)\n"),
                        text.index("    cfg = load_cfg_from_registry(v12.DEFAULT_TASK, \"env_cfg_entry_point\")\n"))
        self.assertIn("entry_kd=args.stance_entry_kd)", text)
        self.assertIn('"heading_mode": args.camera_heading_mode,\n                "heading_yaw_rad": camera_heading_yaw,',
                      text)
        run = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == "_run")
        assigned = {name.id for node in ast.walk(run) if isinstance(node, ast.Assign)
                    for target in node.targets for name in ast.walk(target) if isinstance(name, ast.Name)}
        self.assertTrue({"scripted_walk", "script_segment", "camera_heading_yaw", "view_yaw"} <= assigned)

    def test_camera_view_yaw_modes(self):
        view = self.module._camera_view_yaw
        yaw = 0.057418473165896385
        self.assertIs(view("body", None, yaw)[0], yaw)
        self.assertEqual(view("body", None, yaw), (yaw, None))
        self.assertEqual(view("initial", None, yaw), (yaw, yaw))
        self.assertEqual(view("initial", yaw, 0.4), (yaw, yaw))
        with self.assertRaises(self.module.AdapterFailure):
            view("world", None, yaw)

    def test_camera_block_body_mode_matches_the_frozen_vectors_and_initial_mode_is_fixed(self):
        import numpy as np
        old = extract_block(self.data["source_text"], "                if step % capture_stride == 0:\n",
                            "                    camera_eye = (\n")
        new = extract_block(self.data["patched_text"], "                if step % capture_stride == 0:\n",
                            "                    camera_eye = (\n")
        self.assertNotEqual(old, new)
        yaws = [0.057418473165896385, 0.08, -0.2, 0.3, 0.3]

        def run(code, mode):
            args = types.SimpleNamespace(camera_heading_mode=mode)
            namespace = {"np": np, "math": math, "args": args, "capture_stride": 2,
                         "camera_heading_yaw": None, "_camera_view_yaw": self.module._camera_view_yaw}
            vectors = []
            for step, yaw in enumerate(yaws):
                namespace.update(step=step * 2, yaw=yaw)
                exec(compile(code + "    pass\n", "camera", "exec"), namespace)
                vectors.append((namespace["heading"].tobytes(), namespace["side"].tobytes()))
            return vectors, namespace

        frozen, _ = run(old, "body")
        body, namespace = run(new, "body")
        self.assertEqual(body, frozen)
        self.assertIsNone(namespace["camera_heading_yaw"])
        initial, namespace = run(new, "initial")
        self.assertEqual(len(set(initial)), 1)
        self.assertEqual(initial[0], frozen[0])
        self.assertEqual(namespace["camera_heading_yaw"], yaws[0])
        self.assertEqual(namespace["view_yaw"], yaws[0])
        # side = lateral -1.25 is the robot's right-hand side for the latched heading.
        side = np.frombuffer(initial[0][1])
        heading = np.frombuffer(initial[0][0])
        self.assertAlmostEqual(float(np.cross(heading, -1.25 * side)[2]), -1.25)


def torch_all_equal(tensor, value):
    return bool((tensor == value).all())


if __name__ == "__main__":
    unittest.main()
