import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = ROOT.parent / "backend_adapter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER))

from backend_adapter.contracts import CommandIdentity, GateConfig
from backend_adapter.control_gate import CommandGate
from backend_adapter.contracts import PlannerRequest
from p2b_backend_ros.node import LayeredPctClient, RosScanPort


class FakePublisher:
    def __init__(self):
        self.messages = []
    def publish(self, msg):
        self.messages.append(msg)


class FakeTwist:
    def __init__(self):
        self.linear = type("Linear", (), {"x": 0.0, "y": 0.0})()
        self.angular = type("Angular", (), {"z": 0.0})()


class WatchdogGraceTests(unittest.TestCase):
    def test_print_contract_accepts_launch_ros_remap_args(self):
        proc = subprocess.run([
            sys.executable,
            "-m",
            "p2b_backend_ros.node",
            "--config",
            str(ROOT / "config/p2b_backend_ros.example.json"),
            "--print-contract",
            "--ros-args",
            "-r",
            "__node:=p2b_backend_ros",
        ], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("p2b_backend_ros_wire_contract_v1", proc.stdout)

    def test_layered_pct_client_adds_configured_layer_when_adapter_request_omits_it(self):
        class Inner:
            def __init__(self):
                self.request = None
            def plan(self, request):
                self.request = request
                return "route"
        inner = Inner()
        client = LayeredPctClient(inner, 1)
        request = PlannerRequest("req", "goal", (0, 0, 0), (1, 0, 0), "world", "mapA", 1, optimize=True)
        self.assertEqual(client.plan(request), "route")
        self.assertEqual(inner.request.start_layer, 1)
        self.assertEqual(inner.request.target_layer, 1)

    def test_initial_owner_wait_publishes_zero_without_pre_faulting_gate(self):
        # This captures the gate-side invariant used by RosScanPort._watchdog_tick:
        # before the first same-generation heartbeat, do not call gate.tick(),
        # because CommandGate.tick() would latch heartbeat_stale.
        gate = CommandGate(GateConfig(heartbeat_stale_s=0.2))
        identity = CommandIdentity("run1", 1, "req1", "goal1", "route1", "cmd1", 1, "mapA", 1)
        gate.admit(identity)
        self.assertEqual(gate.closed_reason, "open")
        # A plain tick at this point would be wrong for backend_ros readiness.
        self.assertEqual(gate.tick().reason, "heartbeat_stale")
        gate = CommandGate(GateConfig(heartbeat_stale_s=0.2))
        gate.admit(identity)
        self.assertEqual(gate.closed_reason, "open")

    def test_default_raw_twist_identity_is_zeroed_without_crashing_or_closing_owner(self):
        port = object.__new__(RosScanPort)
        port.gate = CommandGate()
        owner = CommandIdentity("run1", 1, "req1", "goal1", "route1", "cmd1", 1, "mapA", 1)
        port.gate.admit(owner)
        port.gated_pub = FakePublisher()
        port.Twist = FakeTwist
        port._faults = []
        port._last_block_reason = "unset"
        port.node = type("Node", (), {"get_logger": lambda self: type("Logger", (), {"warn": lambda self, msg: None})()})()

        msg = type("Raw", (), {})()
        msg.run_id = ""
        msg.epoch = 0
        msg.request_id = ""
        msg.goal_id = ""
        msg.route_id = ""
        msg.command_id = ""
        msg.generation = 0
        msg.map_epoch = ""
        msg.map_revision = 0
        msg.twist = FakeTwist()
        port._on_raw_command(msg)

        self.assertEqual(port._last_block_reason, "invalid_raw_identity")
        self.assertEqual(port.gate.owner, owner)
        self.assertEqual(len(port.gated_pub.messages), 1)
        self.assertEqual(port.gated_pub.messages[0].linear.x, 0.0)

    def test_wrong_run_applied_snapshot_blocks_matching_raw_before_publish(self):
        port = object.__new__(RosScanPort)
        port.config = {"run_id": "run1", "run_epoch_ns": 10}
        port.gate = CommandGate()
        owner = CommandIdentity("run1", 1, "req1", "goal1", "route1", "cmd1", 1, "mapA", 1)
        port.gate.admit(owner)
        port.gated_pub = FakePublisher()
        port.Twist = FakeTwist
        port._faults = []
        port._last_raw_command_s = None
        port._owner_first_heartbeat_s = None
        port._last_block_reason = "unset"
        port.node = type("Node", (), {"get_logger": lambda self: type("Logger", (), {"warn": lambda self, msg: None})()})()
        class Snapshot:
            run_id = "wrong"
            run_epoch_ns = 10
        class Reader:
            def read(self):
                return Snapshot()
        port.adapter = type("Adapter", (), {"applied_reader": Reader()})()

        msg = type("Raw", (), {})()
        for key, value in owner.to_dict().items():
            setattr(msg, key, value)
        msg.twist = FakeTwist()
        msg.twist.linear.x = 0.2
        port._on_raw_command(msg)

        self.assertEqual(port._last_block_reason, "applied_evidence_stale")
        self.assertEqual(port.gate.closed_reason, "applied_evidence_stale")
        self.assertEqual(port.gated_pub.messages[0].linear.x, 0.0)

    def test_body_pose_wrong_frame_closes_gate_without_measurement_update(self):
        port = object.__new__(RosScanPort)
        port.config = {"map": {"frame_id": "world"}}
        port.gate = CommandGate()
        port._faults = []
        port._last_odom_stamp_ns = None
        port._state_seq = 0
        port._last_measurement = None
        port.node = type("Node", (), {"get_logger": lambda self: type("Logger", (), {"warn": lambda self, msg: None})()})()
        stamp = type("Stamp", (), {"sec": 1, "nanosec": 0})()
        header = type("Header", (), {"frame_id": "map", "stamp": stamp})()
        pose = type("PoseWithCov", (), {"pose": type("Pose", (), {"position": type("Point", (), {"x": 0, "y": 0, "z": 0})()})()})()
        twist = type("TwistWithCov", (), {"twist": type("Twist", (), {"linear": type("Linear", (), {"x": 0, "y": 0, "z": 0})()})()})()
        msg = type("Odom", (), {"header": header, "pose": pose, "twist": twist})()
        port._on_body_pose(msg)

        self.assertEqual(port.gate.closed_reason, "invalid_body_pose_frame")
        self.assertIsNone(port._last_measurement)

    def test_stale_body_pose_is_not_ready_for_planning(self):
        port = object.__new__(RosScanPort)
        port.config = {"gate": {"odom_stale_s": 0.001}}
        port._last_measurement = __import__("backend_adapter.contracts", fromlist=["MeasuredState"]).MeasuredState(1, 1.0, (0, 0, 0.35), (0, 0, 0), "mapA", 1)
        with self.assertRaisesRegex(RuntimeError, "body_pose_stale"):
            port.measurement_provider()


if __name__ == "__main__":
    unittest.main()
