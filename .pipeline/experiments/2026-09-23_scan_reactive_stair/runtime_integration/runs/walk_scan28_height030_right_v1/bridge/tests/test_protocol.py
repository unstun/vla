import socket
import struct
import threading
import unittest

from lite3_sim_bridge.protocol import (
    HEADER_SIZE,
    HEADER_STRUCT,
    MAX_PAYLOAD_BYTES,
    CommandV1,
    DUAL_CLOUD_SENSOR_PREFIX_STRUCT,
    DualCloudSensorFrameV1,
    JointStateV1,
    MessageType,
    ProtocolError,
    ScanIdTracker,
    SequenceTracker,
    SensorFrameV1,
    StatusFlag,
    StatusV1,
    decode_command_payload,
    decode_frame,
    decode_dual_cloud_sensor_payload,
    decode_header,
    decode_joint_state_payload,
    decode_sensor_payload,
    decode_status_payload,
    encode_command_payload,
    encode_frame,
    encode_dual_cloud_sensor_payload,
    encode_joint_state_payload,
    encode_sensor_payload,
    encode_status_payload,
    pack_xyz_points,
    recv_frame,
    send_frame,
    unpack_xyz_points,
    xyz_f32_be_to_le,
)


class ProtocolTest(unittest.TestCase):
    def _dual_sensor(self, **overrides):
        raw_count, raw_bytes = pack_xyz_points(
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.4), (2.0, 0.0, 0.0))
        )
        planner_count, planner_bytes = pack_xyz_points(((1.0, 0.0, 0.4),))
        values = dict(
            body_position=(0.0, 0.0, 0.4),
            body_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            sensor_position=(0.0, 0.0, 0.7),
            sensor_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            config_sha256=b"d" * 32,
            scan_id=11,
            raw_point_count=raw_count,
            raw_points_xyz_f32_be=raw_bytes,
            planner_point_count=planner_count,
            planner_points_xyz_f32_be=planner_bytes,
            filtered_ground_point_count=2,
            conservative_retained_point_count=0,
        )
        values.update(overrides)
        return DualCloudSensorFrameV1(**values)

    def test_sequence_tracker_rejects_regression_and_counts_gaps(self):
        tracker = SequenceTracker()
        self.assertEqual(tracker.observe(4), 0)
        self.assertEqual(tracker.observe(7), 2)
        self.assertEqual(tracker.gap_count, 2)
        with self.assertRaises(ProtocolError):
            tracker.observe(7)

    def test_scan_id_tracker_rejects_duplicate_and_regression(self):
        tracker = ScanIdTracker()
        tracker.observe(4)
        tracker.observe(6)
        with self.assertRaisesRegex(ProtocolError, "scan ID is not increasing"):
            tracker.observe(6)
        with self.assertRaisesRegex(ProtocolError, "scan ID is not increasing"):
            tracker.observe(5)

    def test_dual_cloud_sensor_payload_round_trip(self):
        sensor = self._dual_sensor()
        timestamp_ns = 123456789
        wire = encode_frame(
            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
            9,
            timestamp_ns,
            encode_dual_cloud_sensor_payload(sensor),
        )
        frame = decode_frame(wire)
        decoded = decode_dual_cloud_sensor_payload(frame.payload)
        self.assertEqual(decoded, sensor)
        self.assertEqual(frame.header.timestamp_ns, timestamp_ns)
        self.assertEqual(
            unpack_xyz_points(decoded.raw_point_count, decoded.raw_points_xyz_f32_be)[0],
            (0.0, 0.0, 0.0),
        )

    def test_dual_cloud_rejects_count_length_partition_and_nonfinite(self):
        sensor = self._dual_sensor()
        invalid = (
            self._dual_sensor(raw_point_count=-1),
            self._dual_sensor(raw_point_count=2),
            self._dual_sensor(filtered_ground_point_count=1),
            self._dual_sensor(conservative_retained_point_count=2),
            self._dual_sensor(raw_points_xyz_f32_be=sensor.raw_points_xyz_f32_be[:-1]),
            self._dual_sensor(
                planner_points_xyz_f32_be=struct.pack("!3f", float("inf"), 0.0, 0.0)
            ),
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ProtocolError):
                encode_dual_cloud_sensor_payload(value)

        payload = bytearray(encode_dual_cloud_sensor_payload(sensor))
        fields = list(
            DUAL_CLOUD_SENSOR_PREFIX_STRUCT.unpack(
                payload[: DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size]
            )
        )
        fields[20] -= 12
        malformed = (
            DUAL_CLOUD_SENSOR_PREFIX_STRUCT.pack(*fields)
            + payload[DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size :]
        )
        with self.assertRaisesRegex(ProtocolError, "raw point byte length"):
            decode_dual_cloud_sensor_payload(malformed)

    def test_dual_cloud_requires_both_structural_cloud_sections(self):
        sensor = self._dual_sensor()
        payload = encode_dual_cloud_sensor_payload(sensor)
        with self.assertRaises(ProtocolError):
            decode_dual_cloud_sensor_payload(payload[:-12])

    def test_dual_cloud_rejects_combined_payload_over_protocol_limit(self):
        count = 700_000
        points = b"\x00" * (count * 12)
        sensor = self._dual_sensor(
            raw_point_count=count,
            raw_points_xyz_f32_be=points,
            planner_point_count=count,
            planner_points_xyz_f32_be=points,
            filtered_ground_point_count=0,
        )
        with self.assertRaisesRegex(ProtocolError, "exceeds v1 limit"):
            encode_dual_cloud_sensor_payload(sensor)


    def test_frame_round_trip(self):
        encoded = encode_frame(MessageType.CMD_VEL_V1, 7, 1000, b"payload")
        frame = decode_frame(encoded)
        self.assertEqual(frame.header.message_type, MessageType.CMD_VEL_V1)
        self.assertEqual(frame.header.sequence, 7)
        self.assertEqual(frame.header.timestamp_ns, 1000)
        self.assertEqual(frame.payload, b"payload")

    def test_header_rejects_magic_version_flags_reserved_and_oversize(self):
        encoded = bytearray(encode_frame(MessageType.HEARTBEAT_V1, 0, 0, b""))
        cases = []
        bad_magic = bytearray(encoded[:HEADER_SIZE])
        bad_magic[0:4] = b"BAD!"
        cases.append(bytes(bad_magic))
        bad_version = bytearray(encoded[:HEADER_SIZE])
        bad_version[4] = 2
        cases.append(bytes(bad_version))
        bad_flags = bytearray(encoded[:HEADER_SIZE])
        bad_flags[6:8] = b"\x00\x01"
        cases.append(bytes(bad_flags))
        fields = list(HEADER_STRUCT.unpack(encoded[:HEADER_SIZE]))
        fields[8] = 1
        cases.append(HEADER_STRUCT.pack(*fields))
        fields[8] = 0
        fields[5] = MAX_PAYLOAD_BYTES + 1
        cases.append(HEADER_STRUCT.pack(*fields))
        for header in cases:
            with self.subTest(header=header):
                with self.assertRaises(ProtocolError):
                    decode_header(header)

    def test_frame_rejects_truncation_trailing_bytes_and_crc_failure(self):
        encoded = encode_frame(MessageType.STATUS_V1, 2, 3, b"abc")
        with self.assertRaises(ProtocolError):
            decode_frame(encoded[:-1])
        with self.assertRaises(ProtocolError):
            decode_frame(encoded + b"extra")
        corrupted = bytearray(encoded)
        corrupted[-1] ^= 0xFF
        with self.assertRaises(ProtocolError):
            decode_frame(bytes(corrupted))

    def test_stream_handles_partial_and_coalesced_frames(self):
        sender, receiver = socket.socketpair()
        first = encode_frame(MessageType.HEARTBEAT_V1, 1, 10, b"")
        second = encode_frame(MessageType.CMD_VEL_V1, 2, 20, encode_command_payload(CommandV1(0.1, 0.2, 0.3)))
        combined = first + second

        def writer():
            for index in range(0, len(combined), 3):
                sender.sendall(combined[index : index + 3])
            sender.close()

        thread = threading.Thread(target=writer)
        thread.start()
        received_first = recv_frame(receiver)
        received_second = recv_frame(receiver)
        thread.join(timeout=1.0)
        receiver.close()
        self.assertEqual(received_first.header.sequence, 1)
        self.assertEqual(received_second.header.sequence, 2)
        self.assertAlmostEqual(decode_command_payload(received_second.payload).vy, 0.2)

    def test_send_frame_validates_before_write(self):
        sender, receiver = socket.socketpair()
        encoded = encode_frame(MessageType.HEARTBEAT_V1, 1, 2, b"")
        send_frame(sender, encoded)
        self.assertEqual(recv_frame(receiver).header.sequence, 1)
        with self.assertRaises(ProtocolError):
            send_frame(sender, encoded + b"x")
        sender.close()
        receiver.close()

    def test_sensor_payload_round_trip(self):
        point_count, point_bytes = pack_xyz_points(((1.0, 2.0, 3.0), (-1.5, 0.0, 4.5)))
        sensor = SensorFrameV1(
            body_position=(1.0, 2.0, 0.4),
            body_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            sensor_position=(1.1, 2.0, 0.7),
            sensor_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            config_sha256=b"a" * 32,
            point_count=point_count,
            points_xyz_f32_be=point_bytes,
        )
        decoded = decode_sensor_payload(encode_sensor_payload(sensor))
        self.assertEqual(decoded.body_position, sensor.body_position)
        self.assertEqual(decoded.config_sha256, sensor.config_sha256)
        self.assertEqual(unpack_xyz_points(decoded.point_count, decoded.points_xyz_f32_be), ((1.0, 2.0, 3.0), (-1.5, 0.0, 4.5)))

    def test_network_points_convert_to_explicit_little_endian_ros_bytes(self):
        _, network_bytes = pack_xyz_points(((1.0, -2.5, 3.25),))
        ros_bytes = xyz_f32_be_to_le(network_bytes)
        self.assertEqual(struct.unpack("<3f", ros_bytes), (1.0, -2.5, 3.25))
        self.assertNotEqual(network_bytes, ros_bytes)
        with self.assertRaisesRegex(ProtocolError, "four-byte aligned"):
            xyz_f32_be_to_le(b"bad")

    def test_sensor_rejects_bad_quaternion_point_length_and_nonfinite_point(self):
        count, points = pack_xyz_points(((1.0, 2.0, 3.0),))
        base = dict(
            body_position=(0.0, 0.0, 0.0),
            body_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            sensor_position=(0.0, 0.0, 0.0),
            sensor_quaternion_xyzw=(0.0, 0.0, 0.0, 1.0),
            config_sha256=b"b" * 32,
            point_count=count,
            points_xyz_f32_be=points,
        )
        with self.assertRaises(ProtocolError):
            encode_sensor_payload(SensorFrameV1(**dict(base, body_quaternion_xyzw=(0.0, 0.0, 0.0, 2.0))))
        with self.assertRaises(ProtocolError):
            encode_sensor_payload(SensorFrameV1(**dict(base, points_xyz_f32_be=b"")))
        with self.assertRaises(ProtocolError):
            pack_xyz_points(((float("nan"), 0.0, 0.0),))
        nan_points = struct.pack("!3f", float("nan"), 0.0, 0.0)
        with self.assertRaises(ProtocolError):
            decode_sensor_payload(
                encode_sensor_payload(SensorFrameV1(**dict(base, points_xyz_f32_be=points)))
                [:-len(points)]
                + nan_points
            )

    def test_joint_state_payload_round_trip_and_validation(self):
        joints = JointStateV1(
            names=("FL_HipX_joint", "FL_HipY_joint"),
            positions=(0.1, -0.8),
            velocities=(1.25, -2.5),
        )
        decoded = decode_joint_state_payload(encode_joint_state_payload(joints))
        self.assertEqual(decoded.names, joints.names)
        for actual, expected in zip(decoded.positions, joints.positions):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(decoded.velocities, joints.velocities):
            self.assertAlmostEqual(actual, expected)

        invalid = (
            JointStateV1((), (), ()),
            JointStateV1(("same", "same"), (0.0, 0.0), (0.0, 0.0)),
            JointStateV1(("joint",), (float("nan"),), (0.0,)),
            JointStateV1(("joint",), (0.0, 1.0), (0.0,)),
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ProtocolError):
                encode_joint_state_payload(value)
        encoded = encode_joint_state_payload(joints)
        with self.assertRaises(ProtocolError):
            decode_joint_state_payload(encoded[:-1])
        with self.assertRaises(ProtocolError):
            decode_joint_state_payload(encoded + b"x")

    def test_command_payload_rejects_invalid_values_and_length(self):
        decoded = decode_command_payload(encode_command_payload(CommandV1(0.1, -0.2, 0.3)))
        self.assertAlmostEqual(decoded.vy, -0.2)
        with self.assertRaises(ProtocolError):
            encode_command_payload(CommandV1(float("inf"), 0.0, 0.0))
        with self.assertRaises(ProtocolError):
            decode_command_payload(b"short")

    def test_status_payload_round_trip_and_unknown_flag(self):
        status = StatusV1(
            physics_hz=200.0,
            policy_hz=50.0,
            sensor_hz=10.0,
            bridge_latency_ms=4.0,
            contact_count=4,
            dropped_frames=2,
            watchdog_events=1,
            flags=int(StatusFlag.CONTACT_SUPPORTED),
            termination_code=0,
        )
        self.assertEqual(decode_status_payload(encode_status_payload(status)), status)
        with self.assertRaises(ProtocolError):
            encode_status_payload(StatusV1(**dict(status.__dict__, flags=1 << 20)))


if __name__ == "__main__":
    unittest.main()


def test_body_state_round_trip_and_frame_separation():
    """BODY_STATE_V1 is additive and keeps the two frames distinguishable."""
    from lite3_sim_bridge.protocol import (
        BODY_STATE_STRUCT,
        BodyStateV1,
        MessageType,
        decode_body_state_payload,
        encode_body_state_payload,
    )

    state = BodyStateV1(
        linear_velocity_world=(0.21, -0.07, -0.004),
        angular_velocity_world=(0.0, 0.0, 0.11),
        linear_velocity_body=(0.22, 0.01, -0.004),
        angular_velocity_body=(0.0, 0.0, 0.11),
        simulation_time_ns=12_345_678_900,
        state_sequence=77,
    )
    payload = encode_body_state_payload(state)
    assert len(payload) == BODY_STATE_STRUCT.size == 112
    assert decode_body_state_payload(payload) == state
    # World and body velocity must not be interchangeable.
    assert state.linear_velocity_world != state.linear_velocity_body
    assert int(MessageType.BODY_STATE_V1) == 7


def test_body_state_rejects_non_finite_and_bad_width():
    import pytest

    from lite3_sim_bridge.protocol import (
        BodyStateV1,
        ProtocolError,
        decode_body_state_payload,
        encode_body_state_payload,
    )

    with pytest.raises(ProtocolError):
        encode_body_state_payload(
            BodyStateV1(
                (float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0), 1, 1,
            )
        )
    with pytest.raises(ProtocolError):
        encode_body_state_payload(
            BodyStateV1((0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1, 1)
        )
    with pytest.raises(ProtocolError):
        decode_body_state_payload(b"\x00" * 8)


def test_legacy_message_encodings_are_unchanged_by_the_addition():
    """Every pre-existing message type keeps its exact numeric value and size."""
    from lite3_sim_bridge.protocol import (
        COMMAND_STRUCT,
        DUAL_CLOUD_SENSOR_PREFIX_STRUCT,
        HEADER_STRUCT,
        MessageType,
        SENSOR_PREFIX_STRUCT,
        STATUS_STRUCT,
    )

    assert int(MessageType.SENSOR_FRAME_V1) == 1
    assert int(MessageType.STATUS_V1) == 2
    assert int(MessageType.CMD_VEL_V1) == 3
    assert int(MessageType.HEARTBEAT_V1) == 4
    assert int(MessageType.JOINT_STATE_V1) == 5
    assert int(MessageType.SENSOR_FRAME_DUAL_CLOUD_V1) == 6
    assert HEADER_STRUCT.format == "!4sBBHIIQQII"
    assert SENSOR_PREFIX_STRUCT.format == "!14d32sIHBB"
    assert DUAL_CLOUD_SENSOR_PREFIX_STRUCT.format == "!14d32sQIIIIIIHBB"
    assert COMMAND_STRUCT.format == "!3f"
    assert STATUS_STRUCT.format == "!4fIIIII"
