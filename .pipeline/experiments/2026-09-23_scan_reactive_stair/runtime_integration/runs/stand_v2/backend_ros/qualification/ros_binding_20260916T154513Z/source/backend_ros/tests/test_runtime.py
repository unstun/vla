import pathlib
import sys
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = ROOT.parent / "backend_adapter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER))

from backend_adapter.contracts import MeasuredState
from p2b_backend_ros.config import load_runtime_config, render_wire_contract
from p2b_backend_ros.runtime import GoalWire, NavigationHttpRuntime, RequestedTarget, TerminalLedger, parse_goal_payload, pct_start_from_body_pose


class RuntimeContractTests(unittest.TestCase):
    def test_accepts_adapter_config_and_renders_contract(self):
        config_path = ADAPTER / "config/p2b_adapter.example.json"
        config = load_runtime_config(config_path, {"http": {"port": 9876}})
        self.assertEqual(config["http"]["host"], "127.0.0.1")
        self.assertEqual(config["http"]["port"], 9876)
        contract = render_wire_contract(config)
        self.assertEqual(contract["schema"], "p2b_backend_ros_wire_contract_v1")
        self.assertEqual(contract["semantics"]["admission"], "route accepted only from matching P2BAdmission consumer=fsm")

    def test_rejects_non_loopback_http_host(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            handle.write('{"schema":"p2b_backend_ros_config_v1","http":{"host":"0.0.0.0"}}')
            handle.flush()
            with self.assertRaises(ValueError):
                load_runtime_config(pathlib.Path(handle.name))

    def test_goal_payload_requires_ground_xyz_and_map_identity(self):
        config = load_runtime_config(ROOT / "config/p2b_backend_ros.example.json")
        goal = parse_goal_payload({
            "request_id": "req-a",
            "goal_id": "goal-a",
            "target_ground_xyz": [1.0, 2.0, 0.0],
            "map_epoch": "flat_nominal",
            "map_revision": 1,
        }, config)
        self.assertEqual(goal.target_ground_xyz, (1.0, 2.0, 0.0))
        self.assertEqual(goal.frame_id, "world")
        with self.assertRaises(Exception):
            parse_goal_payload({"request_id": "bad", "goal_id": "g", "target_ground_xyz": [1.0, float("nan"), 0.0]}, config)

    def test_pct_start_subtracts_nominal_height_without_touching_body_measurement(self):
        body = MeasuredState(1, 10.0, (2.0, 3.0, 1.91), (0.1, 0.0, 0.0), "flat_nominal", 1)
        ground = pct_start_from_body_pose(body, 0.35)
        self.assertEqual(ground.position_world_m, (2.0, 3.0, 1.56))
        self.assertEqual(body.position_world_m, (2.0, 3.0, 1.91))
        self.assertIn("minus_nominal_height", ground.source)

    def test_terminal_ledger_keeps_request_causes(self):
        ledger = TerminalLedger(max_records=2, clock=lambda: 42.0)
        ledger.append("req-a", "goal-a", "arrived", "arrived_after_quiescence", "route-a")
        ledger.append("req-b", "goal-b", "cancelled", "http_cancel", "route-b")
        ledger.append("req-c", "goal-c", "failed", "planner_timeout")
        self.assertIsNone(ledger.latest_for("req-a"))
        self.assertEqual(ledger.latest_for("req-b")["cause"], "http_cancel")
        self.assertEqual(ledger.snapshot()[-1]["status"], "failed")

    def test_state_exposes_missing_applied_snapshot_as_not_ready(self):
        from p2b_backend_ros.runtime import NavigationHttpRuntime

        class Service:
            active_owner = None
            def state(self):
                return {"active_owner": None}

        class Adapter:
            class Gate:
                def snapshot(self):
                    return {}
            gate = Gate()
            class Reader:
                path = pathlib.Path("/missing/current_command.json")
                def read(self):
                    raise RuntimeError("applied_snapshot_missing")
            applied_reader = Reader()

        class ScanPort:
            def measurement_provider(self):
                raise RuntimeError("body_pose_not_ready")
            def snapshot(self):
                return {}

        runtime = NavigationHttpRuntime(Service(), Adapter(), ScanPort(), {"run_id": "run", "run_epoch_ns": 1})
        try:
            readiness = runtime.state()["readiness"]
            self.assertFalse(readiness["body_pose_ready"])
            self.assertTrue(readiness["applied_snapshot"]["configured"])
            self.assertFalse(readiness["applied_snapshot"]["ready"])
            self.assertEqual(readiness["applied_snapshot"]["error"], "applied_snapshot_missing")
        finally:
            runtime.shutdown()


class StopFlowRuntimeTests(unittest.TestCase):
    def _runtime(self, adapter, scan_port, service=None, clock=None):
        runtime = NavigationHttpRuntime(
            service or FakeService(),
            adapter,
            scan_port,
            {
                "run_id": "run1",
                "run_epoch_ns": 10,
                "map": {"epoch": "mapA", "revision": 1, "nominal_body_height_m": 0.35},
                "arrival": {"xy_tolerance_m": 0.25, "z_tolerance_m": 0.2, "monitor_period_s": 10.0},
                "service": {"stop_completion_timeout_s": 1.0, "body_ready_timeout_s": 0.01},
            },
            clock=clock or time.monotonic,
        )
        return runtime

    def test_noninstant_stop_records_terminal_only_after_poll_confirms_stop(self):
        service = FakeService()
        owner = service.set_owner()
        adapter = FakeAdapter(["pending", "pending", "stopped"])
        runtime = self._runtime(adapter, FakeScanPort(), service)
        try:
            result = runtime.cancel({"reason": "pilot_cancel"})
            self.assertEqual(result["status"], "stop_pending")
            self.assertEqual(service.cancel_active_calls, 0)
            self.assertEqual(runtime.ledger.snapshot(), [])
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and not runtime.ledger.snapshot():
                time.sleep(0.02)
            self.assertEqual(adapter.stop_calls, 1)
            self.assertGreaterEqual(adapter.poll_calls, 1)
            self.assertEqual(runtime.ledger.snapshot()[-1]["status"], "cancelled")
            self.assertIsNone(service.active_owner)
        finally:
            runtime.shutdown()

    def test_cancel_promotes_simultaneous_arrival_flow(self):
        service = FakeService()
        owner = service.set_owner()
        adapter = FakeAdapter(["pending", "stopped"])
        runtime = self._runtime(adapter, FakeScanPort(position=(1.0, 0.0, 0.35)), service)
        runtime.requested_targets[owner.route_id] = RequestedTarget(owner.request_id, owner.goal_id, owner.route_id, owner.command_id, (1.0, 0.0, 0.0), (1.0, 0.0, 0.35))
        try:
            first = runtime._request_stop_flow(owner, "arrival", "arrived_hold")
            second = runtime.cancel({"reason": "pilot_cancel"})
            self.assertEqual(first["status"], "stop_pending")
            self.assertEqual(second["intent"], "cancel")
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and not runtime.ledger.snapshot():
                time.sleep(0.02)
            self.assertEqual(runtime.ledger.snapshot()[-1]["status"], "cancelled")
        finally:
            runtime.shutdown()

    def test_arrival_drift_after_stop_does_not_claim_arrived(self):
        service = FakeService()
        owner = service.set_owner()
        adapter = FakeAdapter(["stopped"])
        scan_port = FakeScanPort(position=(2.0, 0.0, 0.35))
        runtime = self._runtime(adapter, scan_port, service)
        runtime.requested_targets[owner.route_id] = RequestedTarget(owner.request_id, owner.goal_id, owner.route_id, owner.command_id, (1.0, 0.0, 0.0), (1.0, 0.0, 0.35))
        try:
            runtime._request_stop_flow(owner, "arrival", "arrived_hold")
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and not runtime.ledger.snapshot():
                time.sleep(0.02)
            record = runtime.ledger.snapshot()[-1]
            self.assertEqual(record["status"], "stopped")
            self.assertEqual(record["cause"], "arrival_geometry_drift_after_stop")
        finally:
            runtime.shutdown()

    def test_goal_worker_refuses_stale_body_pose_before_pct(self):
        service = FakeService()
        adapter = FakeAdapter(["stopped"])
        scan_port = FakeScanPort(stale=True)
        runtime = self._runtime(adapter, scan_port, service)
        try:
            goal = GoalWire("req-a", "goal-a", (1.0, 0.0, 0.0), "world", "mapA", 1, "obs-a")
            runtime._goal_worker("job-a", goal)
            self.assertEqual(runtime.ledger.latest_for("req-a")["status"], "failed")
            self.assertEqual(service.submit_goal_calls, 0)
        finally:
            runtime.shutdown()


class FakeGate:
    def snapshot(self):
        return {"closed_reason": "open"}
    def clear_owner_if_quiescent(self):
        return True


class FakeAdapter:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.stop_calls = 0
        self.poll_calls = 0
        self.gate = FakeGate()
        self.applied_reader = None

    def stop(self, command, reason):
        self.stop_calls += 1
        return self._outcome(command)

    def poll_stop(self, command):
        self.poll_calls += 1
        return self._outcome(command)

    def _outcome(self, command):
        p2a = __import__("p2b_backend_ros.runtime", fromlist=["load_p2a_core"]).load_p2a_core()
        status = self.outcomes.pop(0) if self.outcomes else "stopped"
        return p2a.BackendOutcome(status, status, route_id=command.route_id)


class FakeScanPort:
    def __init__(self, position=(0.0, 0.0, 0.35), stale=False):
        self.position = position
        self.stale = stale

    def measurement_provider(self):
        if self.stale:
            raise RuntimeError("body_pose_stale")
        return MeasuredState(1, time.monotonic(), self.position, (0.0, 0.0, 0.0), "mapA", 1)

    def wait_body_ready(self, timeout_s):
        try:
            self.measurement_provider()
            return True
        except Exception:
            return False

    def snapshot(self):
        return {}


class FakeService:
    def __init__(self):
        self.p2a = __import__("p2b_backend_ros.runtime", fromlist=["load_p2a_core"]).load_p2a_core()
        self.run_id = "run1"
        self.epoch = 1
        self.map_epoch = "mapA"
        self.map_revision = 1
        self.active_owner = None
        self.cancel_active_calls = 0
        self.submit_goal_calls = 0

    def set_owner(self):
        command = self.p2a.BackendCommand("run1", 1, "req-a", "goal-a", "route-a", "cmd-a")
        owner = self.p2a.CommandOwner(command, "req-a", "goal-a", "route-a", "cmd-a", "accepted", time.monotonic())
        self.active_owner = owner
        return owner

    def cancel_active(self, reason):
        self.cancel_active_calls += 1
        raise AssertionError("runtime_cancel_must_not_call_sync_cancel_active")

    def submit_goal(self, request):
        self.submit_goal_calls += 1
        return {"ok": False, "status": "failed", "error": "not_used"}

    def receive_feedback(self, feedback):
        if self.active_owner is None:
            return {"ok": False, "status": "ignored", "error": "no_active_owner"}
        self.active_owner.last_feedback_seq = feedback.feedback_seq
        if feedback.status in {"arrived", "cancelled", "stopped"}:
            self.active_owner = None
            return {"ok": True, "status": "ok", "data": {"terminal_cause": feedback.status}}
        return {"ok": False, "status": "failed", "error": feedback.status}

    def state(self):
        return {"active_owner": None if self.active_owner is None else self.active_owner.route_id}


if __name__ == "__main__":
    unittest.main()
