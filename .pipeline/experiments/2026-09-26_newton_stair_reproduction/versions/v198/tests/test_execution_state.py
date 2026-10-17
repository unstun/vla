import importlib.util
from dataclasses import replace
from pathlib import Path
import socket
import struct
import sys
import time
import unittest

VERSION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VERSION / "runtime/bridge"))
from lite3_sim_bridge import protocol
from lite3_sim_bridge.execution_state import (
    ExecutionStateV1, StanceMode, decode_execution_state_payload,
    encode_execution_state_payload, from_robot_sample)
from lite3_sim_bridge.state_stream import CompleteStateStream
from lite3_sim_bridge.transport import TelemetryPublisherServer, FrameStreamClient


def sample(**changes):
    return replace(ExecutionStateV1(
        3_000_000_000, 150, 800, 90, StanceMode.FIXED_STAND,
        False, True, False, (0.01, -0.02, 0.03), (0.0, 0.0, 0.04),
        (0.0, 0.0, 0.0)), **changes)


class ExecutionStateTests(unittest.TestCase):
    def test_wire_layout_and_roundtrip_all_modes(self):
        for mode in StanceMode:
            state = sample(stance_mode=mode)
            wire = encode_execution_state_payload(state)
            self.assertEqual(len(wire), 108)
            self.assertEqual(wire[:32], struct.pack("!4Q", 3_000_000_000, 150, 800, 90))
            self.assertEqual(wire[32:36], bytes([int(mode), 0, 1, 0]))
            self.assertEqual(decode_execution_state_payload(wire), state)

    def test_invalid_payloads_are_rejected(self):
        payload = encode_execution_state_payload(sample())
        cases = [payload[:-1], payload + b"\0",
                 payload[:32] + bytes([255]) + payload[33:],
                 payload[:33] + bytes([2]) + payload[34:],
                 payload[:36] + struct.pack("!d", float("nan")) + payload[44:]]
        for data in cases:
            with self.subTest(data=data.hex()), self.assertRaises(protocol.ProtocolError):
                decode_execution_state_payload(data)
        for state in (sample(run_epoch_ns=0), sample(command_sequence=-1),
                      sample(policy_owns_joints=1), sample(linear_velocity_body=(1.,))):
            with self.assertRaises(protocol.ProtocolError):
                encode_execution_state_payload(state)

    def test_zero_command_does_not_imply_pd_ownership(self):
        row = {"stance_mode": "RL", "policy_owns_joints": True,
               "effective_command": [0., 0., 0.]}
        pose = {"linear_body": [0.2, -0.1, 0.03], "angular_body": [0., 0., 0.3]}
        state = from_robot_sample(row, pose, simulation_time_ns=100, state_sequence=4,
            run_epoch_ns=90, command_sequence=None, command_stale=True, navigation_ready=True)
        self.assertEqual(state.stance_mode, StanceMode.RL)
        self.assertTrue(state.policy_owns_joints)
        self.assertEqual(state.linear_velocity_body, (0.2, -0.1, 0.03))
        self.assertEqual(state.command_sequence, 0)

    def test_consume_once_duplicate_reorder_and_foreign_run(self):
        stream = CompleteStateStream()
        self.assertTrue(stream.offer(sample(), 123))
        self.assertEqual(stream.take(), (sample(), 123))
        self.assertIsNone(stream.take())
        for state in [sample(), sample(state_sequence=149),
                      sample(state_sequence=151, simulation_time_ns=2),
                      sample(state_sequence=151, run_epoch_ns=801)]:
            self.assertFalse(stream.offer(state, 124))
            self.assertIsNone(stream.take())
        self.assertTrue(stream.offer(sample(state_sequence=151, simulation_time_ns=3_020_000_000), 125))

    def test_legacy_payloads_and_frame_bytes_match_v196(self):
        path = VERSION.parents[1] / "runtime_sources/bridge/lite3_sim_bridge/protocol.py"
        if not path.exists():
            self.skipTest("Legacy source comparison runs on the host")
        spec = importlib.util.spec_from_file_location("v196_protocol", path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old
        spec.loader.exec_module(old)
        args = ((1., 2., 3.), (0., 0., 0., 1.), (0.1, 0.2, 0.3),
                (0.01, 0.02, 0.03), (0.2, 0.1, 0.3), (0.02, 0.01, 0.03), 1000, 4, 90)
        for mod in (old, protocol):
            payload = mod.encode_body_state_v2_payload(mod.BodyStateV2(*args))
            frame = mod.encode_frame(mod.MessageType.BODY_STATE_V2, 5, 1000, payload)
            if mod is old:
                expected = frame
            else:
                self.assertEqual(frame, expected)
        self.assertEqual(protocol.encode_command_payload(protocol.CommandV1(0.25, -0.5, 1.)),
                         old.encode_command_payload(old.CommandV1(0.25, -0.5, 1.)))

    def test_real_priority_socket_transports_execution_state(self):
        server = TelemetryPublisherServer(port=0, priority_send=True)
        server.start()
        client = FrameStreamClient(*server.endpoint, timeout_seconds=2.)
        try:
            client.connect()
            deadline = time.monotonic() + 2
            while server.stats().accepted_connections == 0 and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertEqual(server.stats().accepted_connections, 1)
            state = sample()
            server.publish(protocol.encode_frame(protocol.MessageType.EXECUTION_STATE_V1,
                1, state.simulation_time_ns, encode_execution_state_payload(state)))
            frame = client.receive()
            self.assertEqual(frame.header.message_type, protocol.MessageType.EXECUTION_STATE_V1)
            self.assertEqual(decode_execution_state_payload(frame.payload), state)
            self.assertEqual(server.queue_metrics()["high_enqueued"], 1)
        finally:
            client.close()
            server.stop()


if __name__ == "__main__":
    unittest.main()
