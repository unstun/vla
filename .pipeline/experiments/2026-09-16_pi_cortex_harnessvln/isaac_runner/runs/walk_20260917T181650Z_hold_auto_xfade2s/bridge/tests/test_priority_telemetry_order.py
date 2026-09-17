"""Priority scheduling must satisfy the unchanged receiver's wire-order gate."""
import socket
import threading
import time

from lite3_sim_bridge.protocol import (
    BodyStateV2, DualCloudSensorFrameV1, MessageType, SequenceTracker,
    decode_body_state_v2_payload, decode_frame, encode_body_state_v2_payload,
    encode_dual_cloud_sensor_payload, encode_frame, pack_xyz_points, recv_frame,
)
from lite3_sim_bridge.transport import TelemetryPublisherServer


def wait_for(predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError("transport condition timed out")


def cloud(sequence):
    count, points = pack_xyz_points([(1., 2., 3.)])
    payload = encode_dual_cloud_sensor_payload(DualCloudSensorFrameV1(
        body_position=(0., 0., .35), body_quaternion_xyzw=(0., 0., 0., 1.),
        sensor_position=(0., 0., .5), sensor_quaternion_xyzw=(0., 0., 0., 1.),
        config_sha256=b'\0' * 32, scan_id=sequence,
        raw_point_count=count, raw_points_xyz_f32_be=points,
        planner_point_count=count, planner_points_xyz_f32_be=points,
        filtered_ground_point_count=0, conservative_retained_point_count=0))
    return encode_frame(MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, sequence, sequence*100, payload)


def body(sequence):
    payload = encode_body_state_v2_payload(BodyStateV2(
        position_world=(0., 0., .35), orientation_world_xyzw=(0., 0., 0., 1.),
        linear_velocity_world=(.3, 0., 0.), angular_velocity_world=(0., 0., 0.),
        linear_velocity_body=(.3, 0., 0.), angular_velocity_body=(0., 0., 0.),
        simulation_time_ns=sequence*100, state_sequence=sequence,
        run_epoch_ns=1700000000000000000))
    return encode_frame(MessageType.BODY_STATE_V2, sequence, sequence*100, payload)


def test_priority_overtaking_preserves_receiver_order_payload_and_reconnect():
    server = TelemetryPublisherServer(port=0, priority_send=True)
    entered, release = threading.Event(), threading.Event()
    original_send = server._send_now

    def hold_first(connection, data):
        if not entered.is_set():
            entered.set()
            assert release.wait(3)
        return original_send(connection, data)

    server._send_now = hold_first
    server.start()
    client = socket.create_connection(server.endpoint, timeout=3)
    replacement = None
    try:
        wait_for(lambda: server.stats().accepted_connections == 1)
        frames = [cloud(1), cloud(2), cloud(3), body(4)]
        assert server.publish(frames[0])
        assert entered.wait(3)
        for frame in frames[1:]:
            assert server.publish(frame)
        release.set()
        received = [recv_frame(client) for _ in frames]
        assert [f.header.message_type for f in received] == [
            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, MessageType.BODY_STATE_V2,
            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, MessageType.SENSOR_FRAME_DUAL_CLOUD_V1]
        tracker = SequenceTracker()
        for actual, expected_bytes in zip(received, [frames[i] for i in [0, 3, 1, 2]]):
            tracker.observe(actual.header.sequence)
            expected = decode_frame(expected_bytes)
            assert actual.payload == expected.payload
            assert actual.header.timestamp_ns == expected.header.timestamp_ns
            assert actual.header.payload_crc32 == expected.header.payload_crc32
        assert tracker.gap_count == 0
        state = decode_body_state_v2_payload(received[1].payload)
        assert state.state_sequence == 4
        assert state.run_epoch_ns == 1700000000000000000
        assert server.queue_metrics()['low_frames_overtaken_by_high'] >= 2

        # The bridge retains its SequenceTracker when the TCP connection resets.
        client.close()
        replacement = socket.create_connection(server.endpoint, timeout=3)
        wait_for(lambda: server.stats().accepted_connections == 2)
        assert server.publish(body(5))
        after = recv_frame(replacement)
        tracker.observe(after.header.sequence)
        assert tracker.gap_count == 0
        assert decode_body_state_v2_payload(after.payload).state_sequence == 5
        assert server.drain(3)
        assert server.queue_metrics()['send_failures'] == 0
    finally:
        release.set()
        if replacement is not None:
            replacement.close()
        client.close()
        server.stop()
