"""Clock, ordering and disconnect gating for admitted motion (F4, B04-B06).

Time is injected, never slept, so the deadline itself is what is under test.
The 0.25 s watchdog value is used unchanged: nothing here relaxes it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lite3_sim_bridge.feedback_health import (
    ACTIVE,
    BACKWARD_TIME,
    DISCONNECTED,
    NO_FEEDBACK,
    SEQUENCE_REGRESSION,
    STALLED,
    SimulationFeedbackMonitor,
)

MS = 1_000_000
DEADLINE_NS = 250 * MS
BRIDGE = (
    Path(__file__).resolve().parents[1]
    / "lite3_sim_bridge"
    / "foxy_bridge_node.py"
)


def monitor() -> SimulationFeedbackMonitor:
    return SimulationFeedbackMonitor(DEADLINE_NS)


def test_no_sample_yet_is_not_healthy():
    assert monitor().evaluate(0).reason == NO_FEEDBACK
    assert monitor().evaluate(0).healthy is False


def test_progressing_feedback_is_healthy():
    m = monitor()
    for index in range(1, 11):
        verdict = m.observe(index * 20 * MS, index, index * 20 * MS)
        assert verdict.healthy is True
        assert verdict.reason == ACTIVE
    assert m.counters()["simulation_clock_stall_events"] == 0


def test_b04_repeated_clock_with_live_commands_stops_motion_at_the_deadline():
    """B04: 100 Hz Twist traffic cannot refresh feedback health."""
    m = monitor()
    m.observe(1_000 * MS, 1, 0)
    # The simulator keeps republishing the same sample while wall time runs on.
    # Twist arrival is deliberately not an input to this monitor at all.
    for wall_ms in range(10, 250, 10):
        verdict = m.observe(1_000 * MS, 1 + wall_ms // 10, wall_ms * MS)
        assert verdict.healthy is True, f"still inside the deadline at {wall_ms} ms"
    assert m.evaluate(250 * MS).healthy is True
    stalled = m.evaluate(251 * MS)
    assert stalled.healthy is False
    assert stalled.reason == STALLED
    assert stalled.stall_monotonic_ns == 251 * MS
    assert m.counters()["repeated_simulation_time_events"] == 24
    assert m.counters()["simulation_clock_stall_events"] == 1
    # Recovery needs an actually newer sample, not merely elapsed time.
    assert m.observe(1_020 * MS, 100, 300 * MS).healthy is True


def test_stall_events_count_once_per_stall_not_once_per_poll():
    m = monitor()
    m.observe(1_000 * MS, 1, 0)
    for wall_ms in (300, 400, 500):
        assert m.evaluate(wall_ms * MS).reason == STALLED
    assert m.counters()["simulation_clock_stall_events"] == 1
    m.observe(1_020 * MS, 2, 600 * MS)
    m.evaluate(900 * MS)
    assert m.counters()["simulation_clock_stall_events"] == 2


def test_b06_backward_simulation_time_is_rejected_not_accepted_as_zero():
    m = monitor()
    m.observe(1_000 * MS, 1, 0)
    verdict = m.observe(900 * MS, 2, 10 * MS)
    assert verdict.accepted is False
    assert verdict.healthy is False
    assert verdict.reason == BACKWARD_TIME
    # The rejected sample never becomes the reported state.
    assert verdict.simulation_time_ns == 1_000 * MS
    # It stays invalid until a strictly newer sample arrives.
    assert m.evaluate(20 * MS).healthy is False
    assert m.observe(1_020 * MS, 3, 30 * MS).healthy is True
    assert m.counters()["backward_simulation_time_events"] == 1
    assert m.counters()["rejected_feedback_samples"] == 1


def test_b06_state_sequence_regression_is_rejected():
    m = monitor()
    m.observe(1_000 * MS, 7, 0)
    verdict = m.observe(1_020 * MS, 7, 10 * MS)
    assert verdict.accepted is False
    assert verdict.reason == SEQUENCE_REGRESSION
    assert m.counters()["state_sequence_regression_events"] == 1
    assert m.evaluate(11 * MS).healthy is False


def test_b05_telemetry_disconnect_stops_motion_immediately():
    m = monitor()
    m.observe(1_000 * MS, 1, 0)
    assert m.evaluate(10 * MS).healthy is True
    m.mark_disconnected()
    verdict = m.evaluate(11 * MS)
    assert verdict.healthy is False
    assert verdict.reason == DISCONNECTED
    # No autonomous resumption: a reconnect alone is not enough, a new
    # progressing sample is required.
    assert m.observe(1_020 * MS, 2, 20 * MS).healthy is True


def test_constructor_rejects_a_non_positive_deadline():
    with pytest.raises(ValueError):
        SimulationFeedbackMonitor(0)


def test_observe_rejects_negative_or_non_integer_inputs():
    m = monitor()
    for bad in (-1, 1.5, "3"):
        with pytest.raises(ValueError):
            m.observe(bad, 1, 0)
        with pytest.raises(ValueError):
            m.observe(0, bad, 0)
        with pytest.raises(ValueError):
            m.observe(0, 1, bad)


def test_bridge_command_loop_consults_the_monitor():
    """Prove the production command path uses this gate, not just a helper."""
    source = BRIDGE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    loop = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_command_loop"
    )
    attributes = {
        node.attr for node in ast.walk(loop) if isinstance(node, ast.Attribute)
    }
    assert "_feedback_monitor" in attributes
    assert "evaluate" in attributes
    telemetry = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_telemetry_loop"
    )
    telemetry_attributes = {
        node.attr for node in ast.walk(telemetry) if isinstance(node, ast.Attribute)
    }
    assert "observe" in telemetry_attributes
    assert "mark_disconnected" in telemetry_attributes
    # The established 0.25 s command watchdog default is untouched.
    assert '"source_command_timeout_seconds", 0.25' in source
    # Clock republication still runs on the node's own system-time timer, so a
    # paused ROS clock cannot block the first /clock message or a stop.
    assert '"use_sim_time"' not in source
