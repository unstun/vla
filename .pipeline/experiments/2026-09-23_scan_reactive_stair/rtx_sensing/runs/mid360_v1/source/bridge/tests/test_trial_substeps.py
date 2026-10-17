import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from lite3_sim_bridge.contact_guard import SubstepContactMonitor, SubstepContactStop
from lite3_sim_bridge.trial_events import TrialEvents, TrialStateMutation, trial_exit_code

ROOT = Path(__file__).resolve().parents[3]
V12 = ROOT / "references/locomotion/2026-08-13_v12_model149999/source/v12_runtime_20260718_recovered/source/robot_lab/robot_lab/tasks/go2/env/go2_env.py"


@pytest.mark.parametrize("bad_substep", [0, 1, 2, 3, None])
def test_pinned_v12_loop_unwinds_before_next_physics_step(bad_substep):
    # Execute the exact pinned loop AST; replace only the simulator interfaces.
    tree = ast.parse(V12.read_text())
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "step")
    loop = next(n for n in method.body if isinstance(n, ast.For))
    code = compile(ast.fix_missing_locations(ast.Module(body=[loop], type_ignores=[])), str(V12), "exec")
    sim = SimpleNamespace(steps=0)
    sim.step = lambda **kwargs: setattr(sim, "steps", sim.steps + 1)
    scene = SimpleNamespace(update=lambda **kwargs: None, write_data_to_sim=lambda: None)
    env = SimpleNamespace(cfg=SimpleNamespace(decimation=4, sim=SimpleNamespace(render_interval=4)),
                          _sim_step_counter=0, sim=sim, scene=scene, physics_dt=0.005,
                          action_manager=SimpleNamespace(process_action_with_delay=lambda mask: None,
                                                         apply_action=lambda: None))
    reasons = []
    monitor = SubstepContactMonitor(
        read_forces=lambda: [100.0, 6.0 if sim.steps - 1 == bad_substep else 0.0],
        clock=lambda: sim.steps * 0.005, on_failure=reasons.append,
        required_substeps=4, threshold_n=5.0, nonfoot_indices=[1],
        body_names=["FL_FOOT", "FL_THIGH"], physics_dt_s=0.005)
    monitor.install(scene)
    monitor.begin(0)
    if bad_substep is None:
        exec(code, {"self": env, "actions_start_decimation": 0, "is_rendering": False})
        monitor.end()
        assert sim.steps == 4 and not reasons
        assert monitor.as_record()["observed_substeps"] == 4
    else:
        with pytest.raises(SubstepContactStop) as caught:
            exec(code, {"self": env, "actions_start_decimation": 0, "is_rendering": False})
        assert sim.steps == bad_substep + 1
        assert caught.value.failure.substep_index == bad_substep
        assert caught.value.failure.substep_sim_time_s == pytest.approx(sim.steps * 0.005)
        assert caught.value.failure.body_name == "FL_THIGH"
        assert reasons == ["nonfoot_contact_above_threshold"]
        with pytest.raises(SubstepContactStop):
            monitor.begin(1)
        assert sim.steps == bad_substep + 1
    monitor.restore()


def test_measured_state_mutation_boundaries_and_restore():
    calls = []
    env = SimpleNamespace(_reset_idx=lambda ids: calls.append("reset"))
    robot = SimpleNamespace(write_root_pose_to_sim=lambda value: calls.append("pose"))
    events = TrialEvents()
    events.install(env, robot)
    env._reset_idx([])
    with pytest.raises(TrialStateMutation):
        env._reset_idx([0])
    with pytest.raises(TrialStateMutation):
        robot.write_root_pose_to_sim([1, 2, 3])
    assert not calls
    assert events.as_record()["reset_attempts"] == 1
    assert events.as_record()["pose_write_attempts"] == 1
    assert events.as_record()["autoresets"] == 0
    assert events.as_record()["pose_injection_events"] == 0
    events.restore()
    env._reset_idx([0])
    assert calls == ["reset"]


@pytest.mark.parametrize("status", ["WALL_TIMEOUT", "TERMINATED", "NONFINITE", "EXCESSIVE_TILT",
                                   "CASE_FAILED_NONFOOT_CONTACT", "UNKNOWN"])
def test_every_failed_terminal_outcome_returns_nonzero(status):
    assert trial_exit_code(status) != 0


def test_qualifying_exit_statuses():
    assert trial_exit_code("GOAL_REACHED_AND_STOPPED") == 0
    assert trial_exit_code("DURATION_REACHED") == 0
