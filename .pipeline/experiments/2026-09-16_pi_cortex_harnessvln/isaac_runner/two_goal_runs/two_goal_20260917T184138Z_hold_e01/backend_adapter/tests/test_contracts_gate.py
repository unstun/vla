import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend_adapter.contracts import CommandIdentity, ContractError, GateConfig, MeasuredState, NativeRoute, PlannerRequest, ScanAdmission
from backend_adapter.control_gate import CommandGate
from backend_adapter.pct_ipc import make_route_id
from backend_adapter.scan_wire import decode_admission, encode_route_metadata, validate_stop_admission


class Clock:
    def __init__(self, t=10.0):
        self.t = t
    def __call__(self):
        return self.t
    def step(self, dt):
        self.t += dt


def ident(generation=1, map_epoch="mapA", route_id="routeA"):
    return CommandIdentity(
        run_id="run1",
        epoch=1,
        request_id="req1",
        goal_id="goal1",
        route_id=route_id,
        command_id="cmd1",
        generation=generation,
        map_epoch=map_epoch,
        map_revision=2,
    )


def measured(seq, t, speed=0.0, map_epoch="mapA", map_revision=2):
    return MeasuredState(
        state_sequence=seq,
        monotonic_s=t,
        position_world_m=(0.0, 0.0, 0.35),
        velocity_world_mps=(speed, 0.0, 0.0),
        map_epoch=map_epoch,
        map_revision=map_revision,
    )


class ContractGateTests(unittest.TestCase):
    def test_nan_and_bad_identity_rejected_at_wire_boundary(self):
        with self.assertRaises(ContractError):
            MeasuredState(1, float("nan"), (0, 0, 0), (0, 0, 0), "mapA", 1)
        with self.assertRaises(ContractError):
            CommandIdentity("run 1", 1, "req", "goal", "route", "cmd", 1, "mapA", 1)
        with self.assertRaises(ContractError):
            NativeRoute("route", "goal", "world", "mapA", 0, ((0, 0, 0),))

    def test_route_id_derived_from_real_waypoints_and_z_semantics_preserved(self):
        req = PlannerRequest(
            request_id="req1",
            goal_id="goal1",
            start_xyz_m=(0.0, 0.0, 0.35),
            target_xyz_m=(1.0, 0.0, 0.35),
            frame_id="world",
            map_epoch="mapA",
            map_revision=2,
        )
        route_id_a = make_route_id(req, ((0.0, 0.0, 0.35), (1.0, 0.0, 0.35)))
        route_id_b = make_route_id(req, ((0.0, 0.0, 0.35), (2.0, 0.0, 0.35)))
        self.assertNotEqual(route_id_a, route_id_b)
        route = NativeRoute(route_id_a, "goal1", "world", "mapA", 2, ((0.0, 0.0, 0.35), (1.0, 0.0, 0.35)))
        self.assertEqual(route.z_semantics, "lite3_body_reference_no_display_offset")

    def test_gate_blocks_without_fresh_measurement_and_heartbeat(self):
        clock = Clock()
        gate = CommandGate(GateConfig(odom_stale_s=0.25, heartbeat_stale_s=0.2), clock=clock)
        gate.admit(ident())
        self.assertEqual(gate.gate_raw_command(ident(), (0.1, 0.0, 0.0)).reason, "heartbeat_stale")

        gate = CommandGate(GateConfig(odom_stale_s=0.25, heartbeat_stale_s=0.2), clock=clock)
        gate.admit(ident())
        gate.observe_heartbeat(clock())
        self.assertEqual(gate.gate_raw_command(ident(), (0.1, 0.0, 0.0)).reason, "odom_stale")

        gate = CommandGate(GateConfig(odom_stale_s=0.25, heartbeat_stale_s=0.2), clock=clock)
        gate.admit(ident())
        gate.observe_heartbeat(clock())
        gate.observe_measurement(measured(1, clock(), speed=0.0))
        self.assertTrue(gate.gate_raw_command(ident(), (0.1, 0.0, 0.0)).allowed)
        clock.step(0.21)
        self.assertEqual(gate.gate_raw_command(ident(), (0.1, 0.0, 0.0)).reason, "heartbeat_stale")

    def test_gate_suppresses_late_old_generation_and_map_change(self):
        clock = Clock()
        gate = CommandGate(clock=clock)
        current = ident(generation=2)
        old = ident(generation=1)
        gate.admit(current)
        gate.observe_heartbeat(clock())
        gate.observe_measurement(measured(1, clock()))
        self.assertEqual(gate.gate_raw_command(old, (0.1, 0.0, 0.0)).reason, "identity_mismatch")
        gate2 = CommandGate(clock=clock)
        gate2.admit(current)
        gate2.observe_heartbeat(clock())
        gate2.observe_measurement(measured(1, clock(), map_epoch="mapB"))
        self.assertEqual(gate2.gate_raw_command(current, (0.1, 0.0, 0.0)).reason, "measured_map_mismatch")

    def test_stop_requires_consumer_hold_and_measured_stillness_window(self):
        clock = Clock()
        gate = CommandGate(GateConfig(still_speed_mps=0.05, still_window_s=0.5), clock=clock)
        current = ident()
        gate.admit(current)
        gate.observe_heartbeat(clock())
        gate.observe_measurement(measured(1, clock(), speed=0.2))
        gate.request_cancel(current, "replace_goal")
        gate.confirm_consumer_hold(current)
        self.assertFalse(gate.stop_confirmed())
        clock.step(0.1)
        gate.observe_measurement(measured(2, clock(), speed=0.0))
        self.assertFalse(gate.stop_confirmed())
        clock.step(0.5)
        gate.observe_measurement(measured(3, clock(), speed=0.0))
        self.assertTrue(gate.stop_confirmed())
        self.assertTrue(gate.clear_owner_if_quiescent())

    def test_scan_admission_identity_and_stop_quiescence_are_validated(self):
        current = ident()
        payload = ScanAdmission("accepted", current, consumer="controller").to_wire()
        decoded = decode_admission(payload, current)
        self.assertEqual(decoded.status, "accepted")
        self.assertEqual(decoded.consumer, "controller")
        other = ident(route_id="routeB")
        with self.assertRaises(ContractError):
            decode_admission(payload, other)
        self.assertEqual(validate_stop_admission(ScanAdmission("stopped", current, hold_confirmed=True, measured_stillness_confirmed=False), current).status, "stopped")
        with self.assertRaises(ContractError):
            validate_stop_admission(ScanAdmission("stopped", current, hold_confirmed=False, measured_stillness_confirmed=True), current)

    def test_route_metadata_requires_matching_map_and_route(self):
        current = ident()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        encoded = encode_route_metadata(current, route)
        self.assertIn('"command_id":"cmd1"', encoded)
        with self.assertRaises(ContractError):
            encode_route_metadata(current, NativeRoute("routeB", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35))))


if __name__ == "__main__":
    unittest.main()
