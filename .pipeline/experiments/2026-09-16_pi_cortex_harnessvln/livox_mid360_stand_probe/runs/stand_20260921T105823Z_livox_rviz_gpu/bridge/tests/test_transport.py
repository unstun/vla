import importlib.util
import json
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
from lite3_sim_bridge.protocol import (
    CommandV1,
    DualCloudSensorFrameV1,
    MessageType,
    encode_command_payload,
    encode_dual_cloud_sensor_payload,
    encode_frame,
    pack_xyz_points,
)
from lite3_sim_bridge.transport import (
    CommandClient,
    CommandReceiverServer,
    FrameStreamClient,
    TelemetryPublisherServer,
)


def wait_until(predicate, timeout_seconds=2.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("condition did not become true")


class TransportTest(unittest.TestCase):
    def test_telemetry_publish_and_reconnect(self):
        server = TelemetryPublisherServer(port=0, io_timeout_seconds=0.05)
        server.start()
        first_client = FrameStreamClient(*server.endpoint, timeout_seconds=0.5)
        first_client.connect()
        wait_until(lambda: server.stats().accepted_connections == 1)
        first = encode_frame(MessageType.HEARTBEAT_V1, 1, 1, b"")
        self.assertTrue(server.publish(first))
        self.assertEqual(first_client.receive().header.sequence, 1)
        first_client.close()

        # The next write discovers the closed peer and clears the active slot.
        server.publish(encode_frame(MessageType.HEARTBEAT_V1, 2, 2, b""))
        second_client = FrameStreamClient(*server.endpoint, timeout_seconds=0.5)
        second_client.connect()
        wait_until(lambda: server.stats().accepted_connections == 2)
        third = encode_frame(MessageType.HEARTBEAT_V1, 3, 3, b"")
        wait_until(lambda: server.publish(third))
        self.assertEqual(second_client.receive().header.sequence, 3)
        self.assertGreaterEqual(server.stats().frames_sent, 2)
        second_client.close()
        server.stop()

    def test_telemetry_accepts_joint_state_frame(self):
        server = TelemetryPublisherServer(port=0, io_timeout_seconds=0.05)
        server.start()
        client = FrameStreamClient(*server.endpoint, timeout_seconds=0.5)
        client.connect()
        wait_until(lambda: server.stats().accepted_connections == 1)
        frame = encode_frame(MessageType.JOINT_STATE_V1, 1, 10, b"joint-bytes")
        self.assertTrue(server.publish(frame))
        self.assertEqual(client.receive().header.message_type, MessageType.JOINT_STATE_V1)
        client.close()
        server.stop()

    def test_telemetry_accepts_dual_cloud_sensor_frame(self):
        server = TelemetryPublisherServer(port=0, io_timeout_seconds=0.05)
        server.start()
        client = FrameStreamClient(*server.endpoint, timeout_seconds=0.5)
        client.connect()
        wait_until(lambda: server.stats().accepted_connections == 1)
        frame = encode_frame(MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, 1, 10, b"dual")
        self.assertTrue(server.publish(frame))
        self.assertEqual(
            client.receive().header.message_type,
            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
        )
        client.close()
        server.stop()

    @unittest.skipUnless(importlib.util.find_spec("rclpy"), "requires ROS 2")
    def test_foxy_bridge_publishes_dual_clouds_with_same_stamp_and_frame(self):
        import rclpy
        from rclpy.executors import MultiThreadedExecutor
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import PointCloud2

        from lite3_sim_bridge.foxy_bridge_node import FoxyBridgeNode

        telemetry = TelemetryPublisherServer(port=0, io_timeout_seconds=0.05)
        telemetry.start()
        state = LatestCommandState(CommandLimits())
        command = CommandReceiverServer(state, port=0, io_timeout_seconds=0.05)
        command.start()
        with tempfile.TemporaryDirectory() as directory:
            audit_path = f"{directory}/scan.jsonl"
            rclpy.init(
                args=[
                    "--ros-args",
                    "-p", f"telemetry_port:={telemetry.endpoint[1]}",
                    "-p", f"command_port:={command.endpoint[1]}",
                    "-p", "require_dual_cloud_sensor_frame:=true",
                    "-p", f"scan_audit_path:={audit_path}",
                ]
            )
            bridge = FoxyBridgeNode()
            observer = Node("dual_cloud_contract_observer")
            received = {}
            observer.create_subscription(
                PointCloud2,
                "/quad_0/cloud_raw",
                lambda message: received.setdefault("raw", message),
                qos_profile_sensor_data,
            )
            observer.create_subscription(
                PointCloud2,
                "/quad_0/cloud",
                lambda message: received.setdefault("planner", message),
                qos_profile_sensor_data,
            )
            executor = MultiThreadedExecutor(num_threads=2)
            executor.add_node(bridge)
            executor.add_node(observer)
            spin_thread = threading.Thread(target=executor.spin, daemon=True)
            spin_thread.start()
            try:
                wait_until(lambda: telemetry.stats().accepted_connections == 1, 5.0)
                raw_count, raw_bytes = pack_xyz_points(
                    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.5))
                )
                planner_count, planner_bytes = pack_xyz_points(((1.0, 0.0, 0.5),))
                payload = encode_dual_cloud_sensor_payload(
                    DualCloudSensorFrameV1(
                        body_position=(0.0, 0.0, 0.4),
                        body_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
                        sensor_position=(0.0, 0.0, 0.7),
                        sensor_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
                        config_sha256=b"f" * 32,
                        scan_id=1,
                        raw_point_count=raw_count,
                        raw_points_xyz_f32_be=raw_bytes,
                        planner_point_count=planner_count,
                        planner_points_xyz_f32_be=planner_bytes,
                        filtered_ground_point_count=1,
                        conservative_retained_point_count=0,
                    )
                )
                self.assertTrue(
                    telemetry.publish(
                        encode_frame(
                            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
                            1,
                            123_456_789,
                            payload,
                        )
                    )
                )
                wait_until(lambda: len(received) == 2, 5.0)
                raw = received["raw"]
                planner = received["planner"]
                self.assertEqual(raw.header.stamp, planner.header.stamp)
                self.assertEqual(raw.header.frame_id, planner.header.frame_id)
                self.assertEqual(raw.width, 2)
                self.assertEqual(planner.width, 1)
                wait_until(lambda: __import__("pathlib").Path(audit_path).is_file(), 2.0)
                row = json.loads(open(audit_path, encoding="utf-8").readline())
                self.assertEqual(row["scan_id"], 1)
                self.assertEqual(row["outcome"], "published_sequentially")
            finally:
                executor.shutdown()
                observer.destroy_node()
                bridge.destroy_node()
                spin_thread.join(timeout=2.0)
                if rclpy.ok():
                    rclpy.shutdown()
        telemetry.stop()
        command.stop()

    def test_command_receive_disconnect_and_reconnect(self):
        limits = CommandLimits(0.75, 0.35, 1.0)
        state = LatestCommandState(
            limits,
            timeout_ns=500_000_000,
            max_source_age_ns=500_000_000,
            max_future_skew_ns=50_000_000,
        )
        server = CommandReceiverServer(state, port=0, io_timeout_seconds=0.05)
        server.start()
        first_client = CommandClient(*server.endpoint, limits=limits, timeout_seconds=0.5)
        first_client.connect()
        sent = first_client.send_command(CommandV1(9.0, -9.0, 2.0))
        self.assertEqual(sent, CommandV1(0.75, -0.35, 1.0))
        active = wait_until(lambda: not server.snapshot().stale and server.snapshot())
        self.assertAlmostEqual(active.command.vx, sent.vx)
        self.assertAlmostEqual(active.command.vy, sent.vy)
        self.assertAlmostEqual(active.command.wz, sent.wz)
        first_client.close()
        wait_until(lambda: server.snapshot().reason == "disconnected")

        second_client = CommandClient(
            *server.endpoint,
            limits=limits,
            timeout_seconds=0.5,
            initial_sequence=first_client.sequence,
        )
        second_client.connect()
        second_client.send_command(CommandV1(0.1, 0.0, 0.0))
        reconnected = wait_until(
            lambda: server.snapshot().sequence == 2 and not server.snapshot().stale and server.snapshot()
        )
        self.assertAlmostEqual(reconnected.command.vx, 0.1)
        self.assertEqual(server.stats().reconnects, 1)
        second_client.close()
        server.stop()

    def test_command_protocol_error_fails_closed(self):
        limits = CommandLimits()
        state = LatestCommandState(limits)
        server = CommandReceiverServer(state, port=0, io_timeout_seconds=0.05)
        server.start()
        client = FrameStreamClient(*server.endpoint, timeout_seconds=0.5)
        client.connect()
        client.send(encode_frame(MessageType.STATUS_V1, 1, time.monotonic_ns(), b""))
        wait_until(lambda: server.stats().protocol_errors == 1)
        self.assertTrue(server.snapshot().stale)
        self.assertEqual(
            server.stats().last_protocol_error,
            "command stream received a non-command frame",
        )
        client.close()
        server.stop()

    def test_command_backlog_applies_only_fresh_latest_frame(self):
        limits = CommandLimits(0.75, 0.35, 1.0)
        state = LatestCommandState(
            limits,
            timeout_ns=250_000_000,
            max_source_age_ns=50_000_000,
            max_future_skew_ns=25_000_000,
        )
        server = CommandReceiverServer(state, port=0, io_timeout_seconds=0.05)
        server.start()
        client = socket.create_connection(server.endpoint, timeout=0.5)
        now_ns = time.monotonic_ns()
        frames = []
        for sequence in range(1, 6):
            timestamp_ns = now_ns if sequence == 5 else now_ns - 200_000_000
            frames.append(
                encode_frame(
                    MessageType.CMD_VEL_V1,
                    sequence,
                    timestamp_ns,
                    encode_command_payload(CommandV1(0.1 * sequence, 0.0, 0.0)),
                )
            )
        client.sendall(b"".join(frames))

        active = wait_until(
            lambda: server.snapshot().sequence == 5
            and not server.snapshot().stale
            and server.snapshot()
        )
        self.assertAlmostEqual(active.command.vx, 0.5)
        self.assertEqual(active.sequence_gaps, 0)
        self.assertEqual(active.watchdog_events, 0)
        self.assertEqual(server.stats().protocol_errors, 0)
        self.assertEqual(server.stats().coalesced_frames, 4)
        client.close()
        server.stop()

    def test_command_receive_treats_closed_socket_select_race_as_eof(self):
        state = LatestCommandState(CommandLimits())
        server = CommandReceiverServer(state, port=0, io_timeout_seconds=0.05)
        receiver, sender = socket.socketpair()
        try:
            sender.sendall(
                encode_frame(
                    MessageType.CMD_VEL_V1,
                    1,
                    time.monotonic_ns(),
                    encode_command_payload(CommandV1(0.1, 0.0, 0.0)),
                )
            )
            with mock.patch(
                "lite3_sim_bridge.transport.select.select",
                side_effect=ValueError("file descriptor cannot be negative"),
            ):
                server._receive_connection(receiver)
        finally:
            receiver.close()
            sender.close()


if __name__ == "__main__":
    unittest.main()
    encode_dual_cloud_sensor_payload,


def test_telemetry_publisher_accepts_body_state_and_rejects_commands():
    """BODY_STATE_V1 is telemetry; CMD_VEL_V1 must still be refused."""
    import pytest

    from lite3_sim_bridge.protocol import (
        BodyStateV1,
        CommandV1,
        MessageType,
        ProtocolError,
        encode_body_state_payload,
        encode_command_payload,
        encode_frame,
    )
    from lite3_sim_bridge.transport import TelemetryPublisherServer

    server = TelemetryPublisherServer("127.0.0.1", 0)
    body_state = encode_frame(
        MessageType.BODY_STATE_V1,
        1,
        1_000,
        encode_body_state_payload(
            BodyStateV1((0.1, 0.0, 0.0), (0.0, 0.0, 0.0), (0.1, 0.0, 0.0),
                        (0.0, 0.0, 0.0), 1_000, 1)
        ),
    )
    # No client is connected, so an accepted frame reports False rather than
    # raising. A refused type raises before the connection is even consulted.
    assert server.publish(body_state) is False
    command = encode_frame(
        MessageType.CMD_VEL_V1, 2, 1_000, encode_command_payload(CommandV1(0.1, 0.0, 0.0))
    )
    with pytest.raises(ProtocolError, match="command frame"):
        server.publish(command)
