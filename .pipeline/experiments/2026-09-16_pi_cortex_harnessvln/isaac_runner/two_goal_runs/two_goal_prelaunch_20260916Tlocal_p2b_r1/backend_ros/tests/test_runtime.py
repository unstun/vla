import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = ROOT.parent / "backend_adapter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER))

from backend_adapter.contracts import MeasuredState
from p2b_backend_ros.config import load_runtime_config, render_wire_contract
from p2b_backend_ros.runtime import TerminalLedger, parse_goal_payload, pct_start_from_body_pose


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


if __name__ == "__main__":
    unittest.main()
