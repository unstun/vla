import ast
import importlib.util
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
        external = materializer.apply_patch_text(source, include_stance_hold=False)
        module = materializer.load_stance_hold_module()
        removed = self.data["patched_text"]
        for item in reversed(materializer._stance_hold_replacements(module)):
            self.assertEqual(removed.count(item["new"]), 1, item["name"])
            removed = removed.replace(item["new"], item["old"], 1)
        self.assertEqual(removed, external)

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

        rows = self.drive(runtime, env, robot, contact, term, 30)
        entry = next(i for i, r in enumerate(rows) if r["row"]["stance_mode"] == "STAND_TRANSITION")
        for r in rows[:entry]:
            self.assertIs(r["applied"], r["actions"])
            self.assertTrue(r["row"]["policy_owns_joints"])
            self.assertFalse(r["row"]["stance_gains_written"])
        e = rows[entry]
        self.assertIsNot(e["applied"], e["actions"])
        self.assertTrue(e["row"]["stance_gains_written"])
        self.assertTrue(torch_all_equal(hip.stiffness, 60.0) and torch_all_equal(knee.damping, 1.0))
        np.testing.assert_allclose(e["target"], np.asarray(e["row"]["applied_target"]), atol=2e-6)
        # Torque continuity in robot joint order: the previous step applied the policy target at Kp 20.
        policy_robot = rows[entry - 1]["target"]
        np.testing.assert_allclose(60.0 * (e["target"] - q), 20.0 * (policy_robot - q), atol=1e-4)
        self.assertGreater(float(np.max(np.abs(20.0 * (policy_robot - q)))), 0.4)
        # The delayed-target estimate is the torque of Kp 60 on the previous (policy) target.
        effort = np.array([24.0] * 8 + [36.0] * 4)
        self.assertAlmostEqual(e["row"]["delayed_target_torque_max_ratio_estimate"],
                               float(np.max(np.abs(60.0 * (policy_robot - q)) / effort)), places=5)
        self.assertEqual(runtime["gain_writes"], 1)
        self.assertEqual(runtime["physx_after_first_gain_write"]["problems"], [])
        version = hip.stiffness._version
        rows += self.drive(runtime, env, robot, contact, term, 110, start=30)
        self.assertEqual(rows[-1]["row"]["stance_mode"], "FIXED_STAND")
        self.assertEqual(hip.stiffness._version, version)
        np.testing.assert_allclose(rows[-1]["target"], e["target"], atol=2e-6)

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


def torch_all_equal(tensor, value):
    return bool((tensor == value).all())


if __name__ == "__main__":
    unittest.main()
