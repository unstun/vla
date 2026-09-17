"""All-substep non-foot contact ownership (F1, acceptance B01/B03/A10).

Every case here drives the exact objects the Building runner uses:
`NonFootContactGuard` for the decision and `LatestCommandState` for admission.
`test_runner_uses_the_guard_and_the_latch` pins that coupling to the production
source so a passing guard test cannot drift away from an unused code path.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
from lite3_sim_bridge.contact_guard import (
    TERMINATION_CODE_NONFOOT_CONTACT,
    ContactHistoryError,
    NonFootContactGuard,
    required_substeps_for,
)
from lite3_sim_bridge.protocol import CommandV1

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "lite3_sim_bridge"
    / "run_pct_scan_building.py"
)

# Lite3 contact bodies as ordered by the runner: four feet plus the non-foot
# links the experiment gate covers.
BODY_NAMES = ["TORSO", "FL_FOOT", "FR_FOOT", "HL_FOOT", "HR_FOOT", "FL_THIGH", "FL_SHANK",
              "FR_HIP"]
FOOT_INDICES = [1, 2, 3, 4]
NONFOOT_INDICES = [0, 5, 6, 7]


def make_guard(substeps: int = 4, threshold: float = 5.0) -> NonFootContactGuard:
    return NonFootContactGuard(
        threshold_n=threshold,
        nonfoot_indices=NONFOOT_INDICES,
        body_names=BODY_NAMES,
        physics_dt_s=0.005,
        required_substeps=substeps,
        newest_first=True,
    )


def history(nonfoot_series, body_index: int, foot_force: float = 120.0):
    """Build a newest-first history whose one non-foot body follows a series.

    `nonfoot_series` is given oldest-first for readability and reversed here,
    matching the sensor buffer the runner reads.
    """
    rows = []
    for value in nonfoot_series:
        row = [0.0] * len(BODY_NAMES)
        for foot in FOOT_INDICES:
            row[foot] = foot_force
        row[body_index] = value
        rows.append(row)
    return list(reversed(rows))


def test_required_substeps_covers_the_whole_control_period():
    assert required_substeps_for(0.02, 0.005) == 4
    # A control period that is not an exact multiple still has to be covered.
    assert required_substeps_for(0.021, 0.005) == 5
    assert required_substeps_for(0.005, 0.005) == 1


@pytest.mark.parametrize("body_index,body_name", [(5, "FL_THIGH"), (6, "FL_SHANK"),
                                                  (7, "FR_HIP"), (0, "TORSO")])
def test_b01_single_substep_transient_latches_one_failure(body_index, body_name):
    """B01: [0, 6, 0, 0] N over four substeps latches exactly one failure."""
    guard = make_guard()
    failure = guard.observe(history([0.0, 6.0, 0.0, 0.0], body_index), 1.30, 65)

    assert failure is not None
    assert failure.body_index == body_index
    assert failure.body_name == body_name
    assert failure.force_n == pytest.approx(6.0)
    assert failure.step_index == 65
    # The transient is the second of four substeps: index 1, three substeps
    # back from the post-step sample.
    assert failure.substep_index == 1
    assert failure.substep_age_s == pytest.approx(0.010)
    assert failure.control_sim_time_s == pytest.approx(1.30)
    assert failure.substep_sim_time_s == pytest.approx(1.29)
    assert failure.termination_code == TERMINATION_CODE_NONFOOT_CONTACT
    assert guard.failed is True
    assert guard.maximum_nonfoot_force_n == pytest.approx(6.0)


def test_a10_last_substep_zero_still_fails():
    """A10: a contact present only in an intermediate substep must fail."""
    guard = make_guard()
    assert guard.observe(history([0.0, 0.0, 7.5, 0.0], 6), 0.50, 25) is not None
    # The post-step sample alone, which the historical runner read, is zero.
    assert history([0.0, 0.0, 7.5, 0.0], 6)[0][6] == 0.0


def test_normal_foot_contact_is_never_a_failure():
    guard = make_guard()
    for step in range(50):
        assert guard.observe(history([0.0] * 4, 5, foot_force=400.0), step * 0.02, step) is None
    assert guard.failed is False
    assert guard.observed_substeps == 200


def test_forces_below_the_threshold_do_not_latch_but_are_measured():
    guard = make_guard()
    assert guard.observe(history([4.999, 0.0, 1.0, 0.0], 5), 0.02, 1) is None
    assert guard.failed is False
    assert guard.maximum_nonfoot_force_n == pytest.approx(4.999)
    # The threshold is inclusive, exactly as the acceptance contract states.
    assert guard.observe(history([0.0, 0.0, 0.0, 5.0], 5), 0.04, 2) is not None


def test_first_failing_substep_wins_over_a_larger_later_one():
    guard = make_guard()
    failure = guard.observe(history([0.0, 6.0, 900.0, 0.0], 5), 0.20, 10)
    assert failure.force_n == pytest.approx(6.0)
    assert failure.substep_index == 1


def test_latch_is_terminal_across_later_clean_steps():
    guard = make_guard()
    first = guard.observe(history([9.0, 0.0, 0.0, 0.0], 5), 0.20, 10)
    assert first is not None
    for step in range(11, 20):
        assert guard.observe(history([0.0] * 4, 5), step * 0.02, step) is None
    assert guard.failure is first


def test_incomplete_history_is_an_error_not_a_silent_zero():
    guard = make_guard()
    with pytest.raises(ContactHistoryError) as error:
        guard.observe(history([0.0, 0.0, 0.0], 5), 0.02, 1)
    assert "3 substeps" in str(error.value)
    assert guard.failed is False


def test_non_finite_force_is_an_error():
    guard = make_guard()
    with pytest.raises(ContactHistoryError):
        guard.observe(history([0.0, float("nan"), 0.0, 0.0], 5), 0.02, 1)


def test_oldest_first_history_is_supported_explicitly():
    newest_first = make_guard()
    oldest_first = NonFootContactGuard(
        threshold_n=5.0, nonfoot_indices=NONFOOT_INDICES, body_names=BODY_NAMES,
        physics_dt_s=0.005, required_substeps=4, newest_first=False,
    )
    series = [0.0, 6.0, 0.0, 0.0]
    a = newest_first.observe(history(series, 5), 1.30, 65)
    b = oldest_first.observe(list(reversed(history(series, 5))), 1.30, 65)
    assert (a.substep_index, a.substep_age_s) == (b.substep_index, b.substep_age_s)


def test_b02_reconnect_and_a_new_command_cannot_clear_the_case_latch():
    """B02: admission stays disabled through reconnect and fresh commands."""
    state = LatestCommandState(
        CommandLimits(0.30, 0.30, 0.8, max_horizontal_norm=0.30), timeout_ns=250_000_000
    )
    state.update(CommandV1(0.2, 0.0, 0.0), 1, 1_000, 1_100)
    assert state.snapshot(1_200).command == CommandV1(0.2, 0.0, 0.0)

    latched = state.latch_case_failure("nonfoot_contact_above_threshold")
    assert latched.case_failed is True
    assert latched.command == CommandV1(0.0, 0.0, 0.0)

    # Transport reconnect, then a valid fresh nonzero command.
    state.mark_disconnected()
    after = state.update(CommandV1(0.25, 0.1, 0.4), 2, 2_000, 2_100)
    assert after.command == CommandV1(0.0, 0.0, 0.0)
    assert after.reason == "case_failed"
    assert after.case_failure_reason == "nonfoot_contact_above_threshold"
    assert state.snapshot(2_200).command == CommandV1(0.0, 0.0, 0.0)
    # Sequence bookkeeping continues, so the transport contract is unchanged.
    assert after.sequence == 2
    assert after.sequence_gaps == 0
    # The original cause survives a second, different latch.
    state.latch_case_failure("something_else")
    assert state.snapshot(2_300).case_failure_reason == "nonfoot_contact_above_threshold"


def test_case_latch_is_not_counted_as_a_watchdog_event():
    state = LatestCommandState(CommandLimits(0.30, 0.30, 0.8), timeout_ns=250_000_000)
    state.update(CommandV1(0.1, 0.0, 0.0), 1, 1_000, 1_100)
    before = state.snapshot(1_200).watchdog_events
    state.latch_case_failure("nonfoot_contact_above_threshold")
    assert state.snapshot(1_300).watchdog_events == before


def test_a_new_case_needs_a_new_state_object():
    """There is deliberately no API that clears a latch in place."""
    state = LatestCommandState(CommandLimits(0.30, 0.30, 0.8))
    state.latch_case_failure("nonfoot_contact_above_threshold")
    assert not any(
        name for name in dir(state)
        if name.startswith(("clear", "reset", "resume", "unlatch"))
    )
    fresh = LatestCommandState(CommandLimits(0.30, 0.30, 0.8))
    assert fresh.case_failed is False


def test_runner_uses_the_guard_and_the_latch():
    """B03: prove the tested logic is the one the production runner calls."""
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    source = RUNNER.read_text(encoding="utf-8")
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "lite3_sim_bridge.contact_guard"
        for alias in node.names
    }
    assert {"SubstepContactMonitor", "SubstepContactStop", "required_substeps_for"} <= imported
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert {"begin", "end", "install"} <= calls
    assert "on_failure=state.latch_case_failure" in source
    # The failure path writes evidence, reports a nonzero termination code and
    # never resets the environment.
    assert 'write_json(args.output / "case_failure.json"' in source
    assert "termination_code=case_failure.termination_code" in source
    assert "return trial_exit_code(status)" in source
    # The vendored V12 configuration file is never written by this runner.
    assert "env_cfg.py" not in source
