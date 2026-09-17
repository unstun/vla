import pathlib
import socketserver
import sys
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend_adapter.adapter_core import P2BBackendAdapter
from backend_adapter.contracts import MeasuredState, NativeRoute, PlannerRequest, ScanAdmission, encode_json_line, decode_json_line
from backend_adapter.control_gate import CommandGate
from backend_adapter.p2a_bridge import load_p2a_core
from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig, PlannerUnavailable, ok_response
from backend_adapter.pct_worker import NativePctPlanner


class Clock:
    def __init__(self, t=100.0):
        self.t = t
    def __call__(self):
        return self.t
    def step(self, dt):
        self.t += dt


class FakePctClient:
    def __init__(self, route):
        self.route = route
        self.requests = []
    def plan(self, request):
        self.requests.append(request)
        return self.route


class FakeScanPort:
    def __init__(self, status="accepted", gate=None, clock=None):
        self.status = status
        self.submitted = []
        self.stopped = []
        self.gate = gate
        self.clock = clock
    def submit_route(self, identity, route):
        self.submitted.append((identity, route))
        return ScanAdmission(self.status, identity, "fake")
    def request_stop(self, identity, reason):
        self.stopped.append((identity, reason))
        if self.gate is not None and self.clock is not None:
            self.gate.confirm_consumer_hold(identity)
            self.clock.step(0.1)
            self.gate.observe_measurement(MeasuredState(2, self.clock(), (0, 0, 0.35), (0, 0, 0), identity.map_epoch, identity.map_revision))
            self.clock.step(0.5)
            self.gate.observe_measurement(MeasuredState(3, self.clock(), (0, 0, 0.35), (0, 0, 0), identity.map_epoch, identity.map_revision))
        return ScanAdmission("stopped", identity, "hold", hold_confirmed=True, measured_stillness_confirmed=True)


def p2a_request(p2a, clock):
    return p2a.GoalRequest(
        request_id="req1",
        goal_id="goal1",
        target=p2a.SpatialTarget(1.0, 0.0, 0.35, None, "world", "m"),
        evidence=p2a.EvidenceSnapshot("obs1", clock(), "world", "m", "mapA", 2, 1, True, "diagnostic_sim_truth"),
        model_arguments={},
    )

class FakeAppliedReader:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.reads = 0
    def read(self):
        self.reads += 1
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


def applied_snapshot(sim_time_s, state_sequence, source_ns=1_000_000_000, command_sequence=1):
    from backend_adapter.applied_evidence import AppliedCommandSnapshot
    return AppliedCommandSnapshot(
        run_id="run1",
        run_epoch_ns=123,
        sim_step=state_sequence,
        sim_time_s=sim_time_s,
        wall_monotonic_ns=source_ns + state_sequence,
        command_source_timestamp_ns=source_ns,
        max_reader_age_s=10.0,
        applied_command=(0.0, 0.0, 0.0),
        admitted_command=(0.0, 0.0, 0.0),
        raw_command=(0.0, 0.0, 0.0),
        command_sequence=command_sequence,
        command_stale=False,
        command_reason="active",
        horizontal_speed_mps=0.0,
        yaw_rate_radps=0.0,
        base_xyz=(0.0, 0.0, 0.35),
        base_quat_wxyz=(1.0, 0.0, 0.0, 0.0),
        command_obs_error=0.0,
        state_sequence=state_sequence,
        telemetry_sequence=state_sequence,
    )


class AdapterIpcTests(unittest.TestCase):
    def test_missing_pct_worker_fails_explicitly(self):
        client = PctIpcClient(PctIpcClientConfig(port=9, connect_timeout_s=0.01, response_timeout_s=0.01))
        req = PlannerRequest("req", "goal", (0, 0, 0.35), (1, 0, 0.35), "world", "mapA", 2)
        with self.assertRaises(PlannerUnavailable):
            client.plan(req)

    def test_adapter_uses_measured_start_and_scan_ack_before_gate_opens(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        scan = FakeScanPort(gate=gate, clock=clock)
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock)
        service = p2a.PersistentNavigationService("run1", "mapA", 2, backend=adapter, clock=clock, max_evidence_age_s=10)
        result = service.submit_goal(p2a_request(p2a, clock))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(scan.submitted[0][0].route_id, "routeA")
        self.assertEqual(scan.submitted[0][1].waypoints_m[-1], (1, 0, 0.35))
        gate.observe_heartbeat(clock())
        gate.observe_measurement(measure())
        self.assertTrue(gate.gate_raw_command(scan.submitted[0][0], (0.1, 0, 0)).allowed)

    def test_scan_rejection_does_not_open_gate(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        scan = FakeScanPort(status="rejected")
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock)
        service = p2a.PersistentNavigationService("run1", "mapA", 2, backend=adapter, clock=clock, max_evidence_age_s=10)
        result = service.submit_goal(p2a_request(p2a, clock))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(gate.owner)

    def test_cancel_releases_only_after_scan_hold_and_measured_stillness(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        scan = FakeScanPort(gate=gate, clock=clock)
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock)
        service = p2a.PersistentNavigationService("run1", "mapA", 2, backend=adapter, clock=clock, max_evidence_age_s=10)
        self.assertTrue(service.submit_goal(p2a_request(p2a, clock))["ok"])
        result = service.cancel_active("test_cancel")
        self.assertTrue(result["ok"])
        self.assertIsNone(gate.owner)

    def test_stop_continuation_does_not_resend_cancel_or_reset_gate_window(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        class HoldOnlyScan(FakeScanPort):
            def request_stop(self, identity, reason):
                self.stopped.append((identity, reason))
                return ScanAdmission("stopped", identity, "hold", hold_confirmed=True)
        scan = HoldOnlyScan()
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock)
        service = p2a.PersistentNavigationService("run1", "mapA", 2, backend=adapter, clock=clock, max_evidence_age_s=10)
        self.assertTrue(service.submit_goal(p2a_request(p2a, clock))["ok"])
        command = service.active_owner.identity()
        first = adapter.stop(command, "http_cancel")
        self.assertEqual(first.status, "pending")
        self.assertEqual(len(scan.stopped), 1)
        clock.step(0.1)
        gate.observe_measurement(MeasuredState(2, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2))
        self.assertEqual(adapter.poll_stop(command).status, "pending")
        self.assertEqual(len(scan.stopped), 1)
        clock.step(0.5)
        gate.observe_measurement(MeasuredState(3, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2))
        self.assertEqual(adapter.poll_stop(command).status, "stopped")
        self.assertEqual(len(scan.stopped), 1)
        self.assertIsNone(gate.owner)

    def test_applied_stop_dwell_accumulates_across_poll_without_resending_cancel(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        scan = FakeScanPort(status="accepted")
        reader = FakeAppliedReader([
            applied_snapshot(10.0, 10, source_ns=9_000_000_000_000_000_000, command_sequence=5),
            applied_snapshot(10.4, 11, source_ns=9_000_000_000_000_000_001, command_sequence=5),
            applied_snapshot(11.05, 12, source_ns=9_000_000_000_000_000_002, command_sequence=5),
        ])
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock, applied_reader=reader, expected_run_epoch_ns=123)
        service = p2a.PersistentNavigationService("run1", "mapA", 2, backend=adapter, clock=clock, max_evidence_age_s=10)
        self.assertTrue(service.submit_goal(p2a_request(p2a, clock))["ok"])
        command = service.active_owner.identity()
        first = adapter.stop(command, "http_cancel")
        self.assertEqual(first.status, "pending")
        self.assertEqual(len(scan.stopped), 1)
        self.assertEqual(adapter.poll_stop(command).status, "pending")
        self.assertEqual(len(scan.stopped), 1)
        self.assertEqual(adapter.poll_stop(command).status, "stopped")
        self.assertEqual(len(scan.stopped), 1)
        self.assertIsNone(gate.owner)

    def test_stop_uses_stored_identity_when_gate_owner_missing_after_uncertain_submit(self):
        p2a = load_p2a_core()
        clock = Clock()
        route = NativeRoute("routeA", "goal1", "world", "mapA", 2, ((0, 0, 0.35), (1, 0, 0.35)))
        gate = CommandGate(clock=clock)
        class PendingScan(FakeScanPort):
            def submit_route(self, identity, route):
                self.submitted.append((identity, route))
                return ScanAdmission("pending", identity, "pending")
        scan = PendingScan()
        measure = lambda: MeasuredState(1, clock(), (0, 0, 0.35), (0, 0, 0), "mapA", 2)
        adapter = P2BBackendAdapter(FakePctClient(route), scan, gate, measure, clock=clock)
        command = p2a.BackendCommand("run1", 1, "req1", "goal1", "routeA", "cmd1")
        p2a_route = adapter._to_p2a_route(route)
        adapter.submit_route(command, p2a_route)
        outcome = adapter.stop(command, "uncertain_submit_cleanup")
        self.assertIn(outcome.status, {"pending", "stopped"})
        self.assertEqual(scan.stopped[0][0].map_epoch, "mapA")
        self.assertEqual(scan.stopped[0][0].map_revision, 2)


if __name__ == "__main__":
    unittest.main()
