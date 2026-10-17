import unittest

from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
from lite3_sim_bridge.protocol import CommandV1, ProtocolError


class CommandStateTest(unittest.TestCase):
    def setUp(self):
        self.state = LatestCommandState(
            CommandLimits(max_vx=0.75, max_vy=0.35, max_wz=1.0),
            timeout_ns=250,
            max_source_age_ns=100,
            max_future_skew_ns=10,
        )

    def test_clamps_and_tracks_increasing_sequence(self):
        snapshot = self.state.update(CommandV1(9.0, -9.0, 2.0), 1, 950, 1000)
        self.assertEqual(snapshot.command, CommandV1(0.75, -0.35, 1.0))
        self.assertFalse(snapshot.stale)
        with self.assertRaises(ProtocolError):
            self.state.update(CommandV1(0.0, 0.0, 0.0), 1, 1000, 1000)

    def test_counts_sequence_gaps(self):
        self.state.update(CommandV1(0.1, 0.0, 0.0), 3, 1000, 1000)
        snapshot = self.state.update(CommandV1(0.2, 0.0, 0.0), 6, 1001, 1001)
        self.assertEqual(snapshot.sequence_gaps, 2)

    def test_rejects_stale_and_future_timestamp(self):
        with self.assertRaises(ProtocolError):
            self.state.update(CommandV1(0.0, 0.0, 0.0), 1, 899, 1000)
        with self.assertRaises(ProtocolError):
            self.state.update(CommandV1(0.0, 0.0, 0.0), 1, 1011, 1000)

    def test_batch_coalesces_stale_intermediate_but_rejects_stale_latest(self):
        active = self.state.update_batch(
            (
                (CommandV1(0.1, 0.0, 0.0), 1, 800, 1000),
                (CommandV1(0.2, 0.0, 0.0), 2, 950, 1000),
            )
        )
        self.assertEqual(active.command, CommandV1(0.2, 0.0, 0.0))
        self.assertEqual(active.sequence, 2)
        self.assertEqual(active.sequence_gaps, 0)

        with self.assertRaisesRegex(ProtocolError, "timestamp is stale"):
            self.state.update_batch(
                (
                    (CommandV1(0.3, 0.0, 0.0), 3, 950, 1100),
                    (CommandV1(0.4, 0.0, 0.0), 4, 999, 1100),
                )
            )
        self.assertEqual(self.state.snapshot(1000).sequence, 2)

    def test_batch_sequence_validation_is_atomic(self):
        self.state.update(CommandV1(0.1, 0.0, 0.0), 1, 1000, 1000)
        with self.assertRaisesRegex(ProtocolError, "sequence is not increasing"):
            self.state.update_batch(
                (
                    (CommandV1(0.2, 0.0, 0.0), 2, 1001, 1001),
                    (CommandV1(0.3, 0.0, 0.0), 2, 1002, 1002),
                )
            )
        snapshot = self.state.snapshot(1002)
        self.assertEqual(snapshot.sequence, 1)
        self.assertEqual(snapshot.sequence_gaps, 0)

    def test_watchdog_zeroes_once(self):
        self.state.update(CommandV1(0.2, 0.0, 0.0), 1, 1000, 1000)
        self.assertFalse(self.state.snapshot(1250).stale)
        expired = self.state.snapshot(1251)
        self.assertTrue(expired.stale)
        self.assertEqual(expired.command, CommandV1(0.0, 0.0, 0.0))
        self.assertEqual(expired.watchdog_events, 1)
        self.assertEqual(self.state.snapshot(2000).watchdog_events, 1)

    def test_disconnect_fails_closed(self):
        self.state.update(CommandV1(0.2, 0.0, 0.0), 1, 1000, 1000)
        disconnected = self.state.mark_disconnected()
        self.assertTrue(disconnected.stale)
        self.assertEqual(disconnected.reason, "disconnected")
        self.assertEqual(disconnected.command, CommandV1(0.0, 0.0, 0.0))
        self.assertEqual(disconnected.watchdog_events, 1)
        self.assertEqual(self.state.mark_disconnected().watchdog_events, 1)

    def test_invalid_limits_and_nonfinite_command(self):
        with self.assertRaises(ValueError):
            CommandLimits(max_vx=0.0)
        with self.assertRaises(ProtocolError):
            self.state.update(CommandV1(float("nan"), 0.0, 0.0), 1, 1000, 1000)


if __name__ == "__main__":
    unittest.main()


def test_horizontal_norm_limit_defaults_to_legacy_per_axis_behaviour():
    from lite3_sim_bridge.command_state import CommandLimits
    from lite3_sim_bridge.protocol import CommandV1

    legacy = CommandLimits(0.75, 0.35, 1.0)
    assert legacy.max_horizontal_norm is None
    clamped = legacy.clamp(CommandV1(2.0, 2.0, 2.0))
    assert (clamped.vx, clamped.vy, clamped.wz) == (0.75, 0.35, 1.0)


def test_horizontal_norm_limit_caps_combined_axis_saturation():
    import math

    from lite3_sim_bridge.command_state import CommandLimits
    from lite3_sim_bridge.protocol import CommandV1

    limits = CommandLimits(0.30, 0.30, 0.8, 0.30)
    clamped = limits.clamp(CommandV1(1.0, 1.0, 2.0))
    assert math.isclose(math.hypot(clamped.vx, clamped.vy), 0.30, rel_tol=0.0, abs_tol=1e-12)
    # Direction is preserved while the magnitude is reduced.
    assert math.isclose(clamped.vx, clamped.vy, rel_tol=0.0, abs_tol=1e-12)
    assert clamped.wz == 0.8
    # A command already inside the limit is untouched.
    inside = limits.clamp(CommandV1(0.2, 0.1, 0.1))
    assert (inside.vx, inside.vy, inside.wz) == (0.2, 0.1, 0.1)
    # Sign is preserved in every quadrant.
    for sx, sy in ((1, -1), (-1, 1), (-1, -1)):
        out = limits.clamp(CommandV1(sx * 0.30, sy * 0.30, 0.0))
        assert math.copysign(1, out.vx) == sx and math.copysign(1, out.vy) == sy
        assert math.isclose(math.hypot(out.vx, out.vy), 0.30, abs_tol=1e-12)


def test_horizontal_norm_limit_rejects_invalid_value():
    import pytest

    from lite3_sim_bridge.command_state import CommandLimits

    with pytest.raises(ValueError):
        CommandLimits(0.30, 0.30, 0.8, 0.0)
    with pytest.raises(ValueError):
        CommandLimits(0.30, 0.30, 0.8, float("inf"))


def test_latest_command_state_applies_the_norm_limit_on_admission():
    import math

    from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
    from lite3_sim_bridge.protocol import CommandV1

    state = LatestCommandState(CommandLimits(0.30, 0.30, 0.8, 0.30))
    snapshot = state.update(CommandV1(0.30, 0.30, 0.0), 1, 1_000, 1_000)
    assert math.isclose(
        math.hypot(snapshot.command.vx, snapshot.command.vy), 0.30, abs_tol=1e-12
    )
