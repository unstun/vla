"""Binary protocol shared by the Foxy and Isaac bridge processes.

All fixed-width values use network byte order. Sensor point bytes are packed as
network-order ``float32 x,y,z`` triples. Quaternions use ``(x,y,z,w)``.
"""

from dataclasses import dataclass
from enum import IntEnum
import math
import socket
import struct
from typing import Iterable, Optional, Sequence, Tuple
import zlib


MAGIC = b"L3NV"
PROTOCOL_VERSION = 1
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_POINT_COUNT = 1_000_000
POINT_STRIDE_BYTES = 12
POINT_FORMAT_XYZ_F32_BE = 1
MAX_JOINT_COUNT = 64
MAX_JOINT_NAME_BYTES = 255

# magic, version, message type, flags, header bytes, payload bytes, sequence,
# timestamp ns, reserved, payload crc32
HEADER_STRUCT = struct.Struct("!4sBBHIIQQII")
HEADER_SIZE = HEADER_STRUCT.size
SENSOR_PREFIX_STRUCT = struct.Struct("!14d32sIHBB")
# poses, config hash, scan id, four audit counts, two explicit byte lengths,
# point stride, point format, reserved
DUAL_CLOUD_SENSOR_PREFIX_STRUCT = struct.Struct("!14d32sQIIIIIIHBB")
COMMAND_STRUCT = struct.Struct("!3f")
STATUS_STRUCT = struct.Struct("!4fIIIII")
# sequence-identified body twist in both frames plus the simulation clock.
# Additive message; every existing payload encoding is unchanged.
BODY_STATE_STRUCT = struct.Struct("!12dQQ")
# Complete base state sampled from one physics update: pose *and* twist, plus
# the sample identity and the identity of the run that produced it. Additive:
# BODY_STATE_V1 above keeps ID 7, "!12dQQ" and 112 bytes exactly.
#
#   position_world[3]              f64  world frame, metres
#   orientation_world_xyzw[4]      f64  world frame, unit quaternion (x,y,z,w)
#   linear_velocity_world[3]       f64  world frame, m/s
#   angular_velocity_world[3]      f64  world frame, rad/s
#   linear_velocity_body[3]        f64  base frame, m/s
#   angular_velocity_body[3]       f64  base frame, rad/s
#   simulation_time_ns             u64  absolute simulation clock, nanoseconds
#   state_sequence                 u64  one increment per completed update
#   run_epoch_ns                   u64  constant run identity
BODY_STATE_V2_STRUCT = struct.Struct("!19dQQQ")
JOINT_STATE_HEADER_STRUCT = struct.Struct("!HH")
JOINT_NAME_LENGTH_STRUCT = struct.Struct("!B")
JOINT_STATE_VALUE_STRUCT = struct.Struct("!2f")


class MessageType(IntEnum):
    SENSOR_FRAME_V1 = 1
    STATUS_V1 = 2
    CMD_VEL_V1 = 3
    HEARTBEAT_V1 = 4
    JOINT_STATE_V1 = 5
    SENSOR_FRAME_DUAL_CLOUD_V1 = 6
    BODY_STATE_V1 = 7
    BODY_STATE_V2 = 8
    EXECUTION_STATE_V1 = 9


class StatusFlag(IntEnum):
    CONTACT_SUPPORTED = 1 << 0
    COLLISION = 1 << 1
    TERMINATED = 1 << 2
    RESET_OCCURRED = 1 << 3
    NAN_DETECTED = 1 << 4


class ProtocolError(ValueError):
    """Raised when bytes violate the v1 wire contract."""


class SequenceTracker:
    """Single owner for increasing sequence validation and gap accounting."""

    def __init__(self) -> None:
        self._last_sequence = None  # type: Optional[int]
        self._gap_count = 0

    @property
    def last_sequence(self):  # type: () -> Optional[int]
        return self._last_sequence

    @property
    def gap_count(self) -> int:
        return self._gap_count

    def observe(self, sequence: int) -> int:
        _require_uint("sequence", sequence, 64)
        if self._last_sequence is not None and sequence <= self._last_sequence:
            raise ProtocolError("sequence is not increasing")
        gap = 0
        if self._last_sequence is not None and sequence > self._last_sequence + 1:
            gap = sequence - self._last_sequence - 1
            self._gap_count += gap
        self._last_sequence = sequence
        return gap


class ScanIdTracker:
    """Validate a scan identity independently of transport reconnects/sequences."""

    def __init__(self) -> None:
        self._last_scan_id = None  # type: Optional[int]

    @property
    def last_scan_id(self):  # type: () -> Optional[int]
        return self._last_scan_id

    def observe(self, scan_id: int) -> None:
        _require_uint("scan_id", scan_id, 64)
        if self._last_scan_id is not None and scan_id <= self._last_scan_id:
            raise ProtocolError("scan ID is not increasing")
        self._last_scan_id = scan_id


@dataclass(frozen=True)
class Header:
    message_type: MessageType
    flags: int
    payload_length: int
    sequence: int
    timestamp_ns: int
    payload_crc32: int


@dataclass(frozen=True)
class Frame:
    header: Header
    payload: bytes


@dataclass(frozen=True)
class CommandV1:
    vx: float
    vy: float
    wz: float


@dataclass(frozen=True)
class SensorFrameV1:
    body_position: Tuple[float, float, float]
    body_quaternion_xyzw: Tuple[float, float, float, float]
    sensor_position: Tuple[float, float, float]
    sensor_quaternion_xyzw: Tuple[float, float, float, float]
    config_sha256: bytes
    point_count: int
    points_xyz_f32_be: bytes


@dataclass(frozen=True)
class DualCloudSensorFrameV1:
    body_position: Tuple[float, float, float]
    body_quaternion_xyzw: Tuple[float, float, float, float]
    sensor_position: Tuple[float, float, float]
    sensor_quaternion_xyzw: Tuple[float, float, float, float]
    config_sha256: bytes
    scan_id: int
    raw_point_count: int
    raw_points_xyz_f32_be: bytes
    planner_point_count: int
    planner_points_xyz_f32_be: bytes
    filtered_ground_point_count: int
    conservative_retained_point_count: int


@dataclass(frozen=True)
class BodyStateV1:
    """Measured base twist in both frames, with its own sample identity.

    `linear_velocity_world` and `angular_velocity_world` are the simulator's
    world-frame base velocities. `linear_velocity_body` and
    `angular_velocity_body` are the same velocities expressed in the base frame,
    which is what `nav_msgs/Odometry` twist means when `child_frame_id` is the
    base. Both are transmitted so a consumer never has to guess which frame it
    received, and so a world/body confusion is detectable.
    """

    linear_velocity_world: Tuple[float, float, float]
    angular_velocity_world: Tuple[float, float, float]
    linear_velocity_body: Tuple[float, float, float]
    angular_velocity_body: Tuple[float, float, float]
    simulation_time_ns: int
    state_sequence: int


@dataclass(frozen=True)
class BodyStateV2:
    """Complete base state from one physics update, with its own identity.

    `BodyStateV1` carries velocity only, so a consumer had to pair it with a
    pose taken from a point-cloud frame that was sampled at a different time.
    That pairing is what produced `odometry_twist_not_ready` and a body pose
    published at the point-cloud cadence. This message removes the pairing:
    position, orientation and both twist representations are copied from the
    same completed physics update and travel together.

    `simulation_time_ns` and `state_sequence` advance only on an actual physics
    update. A heartbeat, a retransmission or a reconnect never advances either,
    so a stalled simulator cannot be mistaken for a running one.

    `run_epoch_ns` identifies the producing run. A consumer latches the first
    epoch it observes and refuses every later frame carrying a different one,
    so a packet replayed from an earlier run can never become fresh state.
    """

    position_world: Tuple[float, float, float]
    orientation_world_xyzw: Tuple[float, float, float, float]
    linear_velocity_world: Tuple[float, float, float]
    angular_velocity_world: Tuple[float, float, float]
    linear_velocity_body: Tuple[float, float, float]
    angular_velocity_body: Tuple[float, float, float]
    simulation_time_ns: int
    state_sequence: int
    run_epoch_ns: int


@dataclass(frozen=True)
class JointStateV1:
    names: Tuple[str, ...]
    positions: Tuple[float, ...]
    velocities: Tuple[float, ...]


@dataclass(frozen=True)
class StatusV1:
    physics_hz: float
    policy_hz: float
    sensor_hz: float
    bridge_latency_ms: float
    contact_count: int
    dropped_frames: int
    watchdog_events: int
    flags: int
    termination_code: int


def _require_uint(name: str, value: int, bits: int) -> None:
    maximum = (1 << bits) - 1
    if not isinstance(value, int) or value < 0 or value > maximum:
        raise ProtocolError("{} must be an unsigned {}-bit integer".format(name, bits))


def _require_finite(name: str, values: Sequence[float]) -> Tuple[float, ...]:
    converted = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in converted):
        raise ProtocolError("{} contains a non-finite value".format(name))
    return converted


def _require_pose(
    position: Sequence[float], quaternion_xyzw: Sequence[float], name: str
) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    if len(position) != 3 or len(quaternion_xyzw) != 4:
        raise ProtocolError("{} pose must contain 3 position and 4 quaternion values".format(name))
    checked_position = _require_finite(name + " position", position)
    checked_quaternion = _require_finite(name + " quaternion", quaternion_xyzw)
    norm = math.sqrt(sum(value * value for value in checked_quaternion))
    if abs(norm - 1.0) > 1.0e-3:
        raise ProtocolError("{} quaternion must be unit length".format(name))
    return checked_position, checked_quaternion


def encode_frame(
    message_type: MessageType,
    sequence: int,
    timestamp_ns: int,
    payload: bytes,
    flags: int = 0,
) -> bytes:
    """Encode one complete v1 frame."""

    try:
        checked_type = MessageType(message_type)
    except ValueError as exc:
        raise ProtocolError("unknown message type") from exc
    _require_uint("sequence", sequence, 64)
    _require_uint("timestamp_ns", timestamp_ns, 64)
    _require_uint("flags", flags, 16)
    if flags != 0:
        raise ProtocolError("v1 flags must be zero")
    if not isinstance(payload, bytes):
        raise ProtocolError("payload must be bytes")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("payload exceeds v1 limit")
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    header = HEADER_STRUCT.pack(
        MAGIC,
        PROTOCOL_VERSION,
        int(checked_type),
        flags,
        HEADER_SIZE,
        len(payload),
        sequence,
        timestamp_ns,
        0,
        checksum,
    )
    return header + payload


def decode_header(data: bytes, max_payload_bytes: int = MAX_PAYLOAD_BYTES) -> Header:
    """Validate and decode one fixed v1 header."""

    if len(data) != HEADER_SIZE:
        raise ProtocolError("header length mismatch")
    (
        magic,
        version,
        message_type,
        flags,
        header_length,
        payload_length,
        sequence,
        timestamp_ns,
        reserved,
        payload_crc32,
    ) = HEADER_STRUCT.unpack(data)
    if magic != MAGIC:
        raise ProtocolError("bad magic")
    if version != PROTOCOL_VERSION:
        raise ProtocolError("unsupported protocol version")
    if flags != 0:
        raise ProtocolError("unknown required flags")
    if header_length != HEADER_SIZE:
        raise ProtocolError("unsupported header length")
    if reserved != 0:
        raise ProtocolError("reserved header field must be zero")
    if payload_length > max_payload_bytes:
        raise ProtocolError("payload length exceeds configured limit")
    try:
        checked_type = MessageType(message_type)
    except ValueError as exc:
        raise ProtocolError("unknown message type") from exc
    return Header(
        message_type=checked_type,
        flags=flags,
        payload_length=payload_length,
        sequence=sequence,
        timestamp_ns=timestamp_ns,
        payload_crc32=payload_crc32,
    )


def decode_frame(data: bytes, max_payload_bytes: int = MAX_PAYLOAD_BYTES) -> Frame:
    """Decode exactly one complete frame and reject trailing bytes."""

    if len(data) < HEADER_SIZE:
        raise ProtocolError("truncated frame header")
    header = decode_header(data[:HEADER_SIZE], max_payload_bytes=max_payload_bytes)
    expected_length = HEADER_SIZE + header.payload_length
    if len(data) != expected_length:
        raise ProtocolError("frame length mismatch")
    payload = data[HEADER_SIZE:]
    if zlib.crc32(payload) & 0xFFFFFFFF != header.payload_crc32:
        raise ProtocolError("payload CRC32 mismatch")
    return Frame(header=header, payload=payload)


def recv_exact(sock: socket.socket, byte_count: int) -> bytes:
    """Read exactly ``byte_count`` bytes or raise ``EOFError``."""

    if byte_count < 0:
        raise ValueError("byte_count must be non-negative")
    chunks = []
    remaining = byte_count
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EOFError("socket closed with {} bytes remaining".format(remaining))
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def recv_frame(sock: socket.socket, max_payload_bytes: int = MAX_PAYLOAD_BYTES) -> Frame:
    """Receive one framed message from a stream socket."""

    header_bytes = recv_exact(sock, HEADER_SIZE)
    header = decode_header(header_bytes, max_payload_bytes=max_payload_bytes)
    payload = recv_exact(sock, header.payload_length)
    if zlib.crc32(payload) & 0xFFFFFFFF != header.payload_crc32:
        raise ProtocolError("payload CRC32 mismatch")
    return Frame(header=header, payload=payload)


def send_frame(sock: socket.socket, frame_bytes: bytes) -> None:
    """Send one already encoded frame."""

    # Decode before transmitting so callers cannot bypass the shared boundary.
    decode_frame(frame_bytes)
    sock.sendall(frame_bytes)


def pack_xyz_points(points: Iterable[Sequence[float]]) -> Tuple[int, bytes]:
    """Pack an iterable of XYZ triples into network-order float32 bytes."""

    flat = []
    count = 0
    for point in points:
        if len(point) != 3:
            raise ProtocolError("each point must contain x, y, z")
        checked = _require_finite("point", point)
        flat.extend(checked)
        count += 1
        if count > MAX_POINT_COUNT:
            raise ProtocolError("point count exceeds v1 limit")
    if not flat:
        return 0, b""
    return count, struct.pack("!{}f".format(len(flat)), *flat)


def unpack_xyz_points(point_count: int, data: bytes) -> Tuple[Tuple[float, float, float], ...]:
    """Decode network-order XYZ bytes. Intended for tests and small samples."""

    _validate_xyz_point_bytes(point_count, data)
    if point_count == 0:
        return tuple()
    values = struct.unpack("!{}f".format(point_count * 3), data)
    return tuple(
        (values[index], values[index + 1], values[index + 2])
        for index in range(0, len(values), 3)
    )


def xyz_f32_be_to_le(data: bytes) -> bytes:
    """Convert network-order float32 bytes to explicit little-endian ROS bytes."""

    if len(data) % 4 != 0:
        raise ProtocolError("float32 point bytes must be four-byte aligned")
    converted = bytearray(len(data))
    for offset in range(0, len(data), 4):
        converted[offset : offset + 4] = data[offset : offset + 4][::-1]
    return bytes(converted)


def _validate_xyz_point_bytes(point_count: int, data: bytes) -> None:
    """Validate a point buffer without expanding it into Python tuples."""

    _require_uint("point_count", point_count, 32)
    if point_count > MAX_POINT_COUNT:
        raise ProtocolError("point count exceeds v1 limit")
    expected = point_count * POINT_STRIDE_BYTES
    if len(data) != expected:
        raise ProtocolError("point byte length mismatch")
    for (value,) in struct.iter_unpack("!f", data):
        if not math.isfinite(value):
            raise ProtocolError("point payload contains a non-finite value")


def encode_sensor_payload(sensor: SensorFrameV1) -> bytes:
    body_position, body_quaternion = _require_pose(
        sensor.body_position, sensor.body_quaternion_xyzw, "body"
    )
    sensor_position, sensor_quaternion = _require_pose(
        sensor.sensor_position, sensor.sensor_quaternion_xyzw, "sensor"
    )
    if not isinstance(sensor.config_sha256, bytes) or len(sensor.config_sha256) != 32:
        raise ProtocolError("config_sha256 must contain 32 raw bytes")
    _require_uint("point_count", sensor.point_count, 32)
    if sensor.point_count > MAX_POINT_COUNT:
        raise ProtocolError("point count exceeds v1 limit")
    expected_point_bytes = sensor.point_count * POINT_STRIDE_BYTES
    if len(sensor.points_xyz_f32_be) != expected_point_bytes:
        raise ProtocolError("point byte length does not match point_count")
    # Validate all point values before they cross the trust boundary.
    _validate_xyz_point_bytes(sensor.point_count, sensor.points_xyz_f32_be)
    prefix = SENSOR_PREFIX_STRUCT.pack(
        *(body_position + body_quaternion + sensor_position + sensor_quaternion),
        sensor.config_sha256,
        sensor.point_count,
        POINT_STRIDE_BYTES,
        POINT_FORMAT_XYZ_F32_BE,
        0,
    )
    payload = prefix + sensor.points_xyz_f32_be
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("sensor payload exceeds v1 limit")
    return payload


def decode_sensor_payload(payload: bytes) -> SensorFrameV1:
    if len(payload) < SENSOR_PREFIX_STRUCT.size:
        raise ProtocolError("truncated sensor payload")
    unpacked = SENSOR_PREFIX_STRUCT.unpack(payload[: SENSOR_PREFIX_STRUCT.size])
    pose_values = unpacked[:14]
    config_sha256 = unpacked[14]
    point_count = unpacked[15]
    point_stride = unpacked[16]
    point_format = unpacked[17]
    reserved = unpacked[18]
    if point_stride != POINT_STRIDE_BYTES:
        raise ProtocolError("unsupported point stride")
    if point_format != POINT_FORMAT_XYZ_F32_BE:
        raise ProtocolError("unsupported point format")
    if reserved != 0:
        raise ProtocolError("reserved sensor field must be zero")
    point_bytes = payload[SENSOR_PREFIX_STRUCT.size :]
    _validate_xyz_point_bytes(point_count, point_bytes)
    body_position, body_quaternion = _require_pose(pose_values[0:3], pose_values[3:7], "body")
    sensor_position, sensor_quaternion = _require_pose(
        pose_values[7:10], pose_values[10:14], "sensor"
    )
    return SensorFrameV1(
        body_position=body_position,
        body_quaternion_xyzw=body_quaternion,
        sensor_position=sensor_position,
        sensor_quaternion_xyzw=sensor_quaternion,
        config_sha256=config_sha256,
        point_count=point_count,
        points_xyz_f32_be=point_bytes,
    )


def _checked_dual_cloud_sensor(sensor: DualCloudSensorFrameV1):
    body_position, body_quaternion = _require_pose(
        sensor.body_position, sensor.body_quaternion_xyzw, "body"
    )
    sensor_position, sensor_quaternion = _require_pose(
        sensor.sensor_position, sensor.sensor_quaternion_xyzw, "sensor"
    )
    if not isinstance(sensor.config_sha256, bytes) or len(sensor.config_sha256) != 32:
        raise ProtocolError("config_sha256 must contain 32 raw bytes")
    _require_uint("scan_id", sensor.scan_id, 64)
    for name, value in (
        ("raw_point_count", sensor.raw_point_count),
        ("planner_point_count", sensor.planner_point_count),
        ("filtered_ground_point_count", sensor.filtered_ground_point_count),
        ("conservative_retained_point_count", sensor.conservative_retained_point_count),
    ):
        _require_uint(name, value, 32)
        if value > MAX_POINT_COUNT:
            raise ProtocolError("{} exceeds v1 limit".format(name))
    if sensor.raw_point_count != (
        sensor.filtered_ground_point_count + sensor.planner_point_count
    ):
        raise ProtocolError("raw count must equal filtered ground plus planner count")
    if sensor.conservative_retained_point_count > sensor.planner_point_count:
        raise ProtocolError("conservative retained count exceeds planner count")
    _validate_xyz_point_bytes(sensor.raw_point_count, sensor.raw_points_xyz_f32_be)
    _validate_xyz_point_bytes(
        sensor.planner_point_count, sensor.planner_points_xyz_f32_be
    )
    return body_position, body_quaternion, sensor_position, sensor_quaternion


def encode_dual_cloud_sensor_payload(sensor: DualCloudSensorFrameV1) -> bytes:
    """Encode two required point clouds produced by one audited scan."""

    body_position, body_quaternion, sensor_position, sensor_quaternion = (
        _checked_dual_cloud_sensor(sensor)
    )
    raw_byte_length = len(sensor.raw_points_xyz_f32_be)
    planner_byte_length = len(sensor.planner_points_xyz_f32_be)
    prefix = DUAL_CLOUD_SENSOR_PREFIX_STRUCT.pack(
        *(body_position + body_quaternion + sensor_position + sensor_quaternion),
        sensor.config_sha256,
        sensor.scan_id,
        sensor.raw_point_count,
        sensor.planner_point_count,
        sensor.filtered_ground_point_count,
        sensor.conservative_retained_point_count,
        raw_byte_length,
        planner_byte_length,
        POINT_STRIDE_BYTES,
        POINT_FORMAT_XYZ_F32_BE,
        0,
    )
    payload = prefix + sensor.raw_points_xyz_f32_be + sensor.planner_points_xyz_f32_be
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("dual-cloud sensor payload exceeds v1 limit")
    return payload


def decode_dual_cloud_sensor_payload(payload: bytes) -> DualCloudSensorFrameV1:
    """Decode one atomic dual-cloud payload and reject ambiguous boundaries."""

    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("dual-cloud sensor payload exceeds v1 limit")
    if len(payload) < DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size:
        raise ProtocolError("truncated dual-cloud sensor payload")
    unpacked = DUAL_CLOUD_SENSOR_PREFIX_STRUCT.unpack(
        payload[: DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size]
    )
    pose_values = unpacked[:14]
    config_sha256 = unpacked[14]
    scan_id = unpacked[15]
    raw_count, planner_count, ground_count, conservative_count = unpacked[16:20]
    raw_byte_length, planner_byte_length = unpacked[20:22]
    point_stride, point_format, reserved = unpacked[22:25]
    if point_stride != POINT_STRIDE_BYTES:
        raise ProtocolError("unsupported point stride")
    if point_format != POINT_FORMAT_XYZ_F32_BE:
        raise ProtocolError("unsupported point format")
    if reserved != 0:
        raise ProtocolError("reserved dual-cloud sensor field must be zero")
    if raw_byte_length != raw_count * POINT_STRIDE_BYTES:
        raise ProtocolError("raw point byte length does not match raw point count")
    if planner_byte_length != planner_count * POINT_STRIDE_BYTES:
        raise ProtocolError("planner point byte length does not match planner point count")
    expected_length = (
        DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size + raw_byte_length + planner_byte_length
    )
    if len(payload) != expected_length:
        raise ProtocolError("dual-cloud sensor payload length mismatch")
    raw_start = DUAL_CLOUD_SENSOR_PREFIX_STRUCT.size
    planner_start = raw_start + raw_byte_length
    sensor = DualCloudSensorFrameV1(
        body_position=pose_values[0:3],
        body_quaternion_xyzw=pose_values[3:7],
        sensor_position=pose_values[7:10],
        sensor_quaternion_xyzw=pose_values[10:14],
        config_sha256=config_sha256,
        scan_id=scan_id,
        raw_point_count=raw_count,
        raw_points_xyz_f32_be=payload[raw_start:planner_start],
        planner_point_count=planner_count,
        planner_points_xyz_f32_be=payload[planner_start:],
        filtered_ground_point_count=ground_count,
        conservative_retained_point_count=conservative_count,
    )
    body_position, body_quaternion, sensor_position, sensor_quaternion = (
        _checked_dual_cloud_sensor(sensor)
    )
    return DualCloudSensorFrameV1(
        body_position=body_position,
        body_quaternion_xyzw=body_quaternion,
        sensor_position=sensor_position,
        sensor_quaternion_xyzw=sensor_quaternion,
        config_sha256=config_sha256,
        scan_id=scan_id,
        raw_point_count=raw_count,
        raw_points_xyz_f32_be=sensor.raw_points_xyz_f32_be,
        planner_point_count=planner_count,
        planner_points_xyz_f32_be=sensor.planner_points_xyz_f32_be,
        filtered_ground_point_count=ground_count,
        conservative_retained_point_count=conservative_count,
    )


def _checked_joint_state(joints: JointStateV1):
    names = tuple(joints.names)
    positions = _require_finite("joint positions", joints.positions)
    velocities = _require_finite("joint velocities", joints.velocities)
    if not names or len(names) > MAX_JOINT_COUNT:
        raise ProtocolError(
            "joint state count must be within [1, {}]".format(MAX_JOINT_COUNT)
        )
    if len(positions) != len(names) or len(velocities) != len(names):
        raise ProtocolError("joint names, positions, and velocities must have equal length")
    encoded_names = []
    for name in names:
        if not isinstance(name, str) or not name or "\x00" in name:
            raise ProtocolError("joint names must be non-empty strings without NUL")
        encoded = name.encode("utf-8")
        if len(encoded) > MAX_JOINT_NAME_BYTES:
            raise ProtocolError("joint name exceeds encoded byte limit")
        encoded_names.append(encoded)
    if len(set(names)) != len(names):
        raise ProtocolError("joint names must be unique")
    return names, positions, velocities, tuple(encoded_names)


def encode_joint_state_payload(joints: JointStateV1) -> bytes:
    """Encode named measured joint positions and velocities for RViz/TF."""

    names, positions, velocities, encoded_names = _checked_joint_state(joints)
    chunks = [JOINT_STATE_HEADER_STRUCT.pack(len(names), 0)]
    for encoded_name, position, velocity in zip(
        encoded_names, positions, velocities
    ):
        chunks.append(JOINT_NAME_LENGTH_STRUCT.pack(len(encoded_name)))
        chunks.append(encoded_name)
        chunks.append(JOINT_STATE_VALUE_STRUCT.pack(position, velocity))
    payload = b"".join(chunks)
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("joint state payload exceeds v1 limit")
    return payload


def decode_joint_state_payload(payload: bytes) -> JointStateV1:
    """Decode one complete named joint-state payload and reject trailing bytes."""

    if len(payload) < JOINT_STATE_HEADER_STRUCT.size:
        raise ProtocolError("truncated joint state payload")
    joint_count, reserved = JOINT_STATE_HEADER_STRUCT.unpack(
        payload[: JOINT_STATE_HEADER_STRUCT.size]
    )
    if reserved != 0:
        raise ProtocolError("reserved joint state field must be zero")
    if joint_count == 0 or joint_count > MAX_JOINT_COUNT:
        raise ProtocolError("joint state count is outside the supported range")
    offset = JOINT_STATE_HEADER_STRUCT.size
    names = []
    positions = []
    velocities = []
    for _ in range(joint_count):
        if offset + JOINT_NAME_LENGTH_STRUCT.size > len(payload):
            raise ProtocolError("truncated joint name length")
        (name_length,) = JOINT_NAME_LENGTH_STRUCT.unpack_from(payload, offset)
        offset += JOINT_NAME_LENGTH_STRUCT.size
        value_end = offset + name_length + JOINT_STATE_VALUE_STRUCT.size
        if name_length == 0 or value_end > len(payload):
            raise ProtocolError("truncated or empty joint state record")
        name_bytes = payload[offset : offset + name_length]
        offset += name_length
        try:
            name = name_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ProtocolError("joint name is not valid UTF-8") from error
        position, velocity = JOINT_STATE_VALUE_STRUCT.unpack_from(payload, offset)
        offset += JOINT_STATE_VALUE_STRUCT.size
        names.append(name)
        positions.append(position)
        velocities.append(velocity)
    if offset != len(payload):
        raise ProtocolError("joint state payload contains trailing bytes")
    joints = JointStateV1(tuple(names), tuple(positions), tuple(velocities))
    checked_names, checked_positions, checked_velocities, _ = _checked_joint_state(
        joints
    )
    return JointStateV1(checked_names, checked_positions, checked_velocities)


def _checked_body_state(state: BodyStateV1) -> BodyStateV1:
    for name in (
        "linear_velocity_world",
        "angular_velocity_world",
        "linear_velocity_body",
        "angular_velocity_body",
    ):
        values = getattr(state, name)
        if len(values) != 3:
            raise ProtocolError("{} must have three components".format(name))
        _require_finite(name, values)
    _require_uint("simulation_time_ns", state.simulation_time_ns, 64)
    _require_uint("state_sequence", state.state_sequence, 64)
    return state


def encode_body_state_payload(state: BodyStateV1) -> bytes:
    checked = _checked_body_state(state)
    return BODY_STATE_STRUCT.pack(
        *checked.linear_velocity_world,
        *checked.angular_velocity_world,
        *checked.linear_velocity_body,
        *checked.angular_velocity_body,
        checked.simulation_time_ns,
        checked.state_sequence,
    )


def decode_body_state_payload(payload: bytes) -> BodyStateV1:
    if len(payload) != BODY_STATE_STRUCT.size:
        raise ProtocolError("body state payload length is invalid")
    values = BODY_STATE_STRUCT.unpack(payload)
    return _checked_body_state(
        BodyStateV1(
            linear_velocity_world=tuple(values[0:3]),
            angular_velocity_world=tuple(values[3:6]),
            linear_velocity_body=tuple(values[6:9]),
            angular_velocity_body=tuple(values[9:12]),
            simulation_time_ns=values[12],
            state_sequence=values[13],
        )
    )


def _checked_body_state_v2(state: BodyStateV2) -> BodyStateV2:
    _require_pose(state.position_world, state.orientation_world_xyzw, "body state")
    for name in (
        "linear_velocity_world",
        "angular_velocity_world",
        "linear_velocity_body",
        "angular_velocity_body",
    ):
        values = getattr(state, name)
        if len(values) != 3:
            raise ProtocolError("{} must have three components".format(name))
        _require_finite(name, values)
    for name in ("simulation_time_ns", "state_sequence", "run_epoch_ns"):
        _require_uint(name, getattr(state, name), 64)
    if state.run_epoch_ns == 0:
        raise ProtocolError("run_epoch_ns must be non-zero")
    return state


def encode_body_state_v2_payload(state: BodyStateV2) -> bytes:
    checked = _checked_body_state_v2(state)
    return BODY_STATE_V2_STRUCT.pack(
        *checked.position_world,
        *checked.orientation_world_xyzw,
        *checked.linear_velocity_world,
        *checked.angular_velocity_world,
        *checked.linear_velocity_body,
        *checked.angular_velocity_body,
        checked.simulation_time_ns,
        checked.state_sequence,
        checked.run_epoch_ns,
    )


def decode_body_state_v2_payload(payload: bytes) -> BodyStateV2:
    if len(payload) != BODY_STATE_V2_STRUCT.size:
        raise ProtocolError("body state v2 payload length is invalid")
    values = BODY_STATE_V2_STRUCT.unpack(payload)
    return _checked_body_state_v2(
        BodyStateV2(
            position_world=tuple(values[0:3]),
            orientation_world_xyzw=tuple(values[3:7]),
            linear_velocity_world=tuple(values[7:10]),
            angular_velocity_world=tuple(values[10:13]),
            linear_velocity_body=tuple(values[13:16]),
            angular_velocity_body=tuple(values[16:19]),
            simulation_time_ns=values[19],
            state_sequence=values[20],
            run_epoch_ns=values[21],
        )
    )


def encode_command_payload(command: CommandV1) -> bytes:
    values = _require_finite("command", (command.vx, command.vy, command.wz))
    return COMMAND_STRUCT.pack(*values)


def decode_command_payload(payload: bytes) -> CommandV1:
    if len(payload) != COMMAND_STRUCT.size:
        raise ProtocolError("command payload length mismatch")
    values = COMMAND_STRUCT.unpack(payload)
    checked = _require_finite("command", values)
    return CommandV1(vx=checked[0], vy=checked[1], wz=checked[2])


def encode_status_payload(status: StatusV1) -> bytes:
    rates = _require_finite(
        "status rates",
        (status.physics_hz, status.policy_hz, status.sensor_hz, status.bridge_latency_ms),
    )
    for name, value in (
        ("contact_count", status.contact_count),
        ("dropped_frames", status.dropped_frames),
        ("watchdog_events", status.watchdog_events),
        ("flags", status.flags),
        ("termination_code", status.termination_code),
    ):
        _require_uint(name, value, 32)
    known_flags = sum(int(flag) for flag in StatusFlag)
    if status.flags & ~known_flags:
        raise ProtocolError("status contains unknown flags")
    return STATUS_STRUCT.pack(
        *(rates
          + (
              status.contact_count,
              status.dropped_frames,
              status.watchdog_events,
              status.flags,
              status.termination_code,
          ))
    )


def decode_status_payload(payload: bytes) -> StatusV1:
    if len(payload) != STATUS_STRUCT.size:
        raise ProtocolError("status payload length mismatch")
    unpacked = STATUS_STRUCT.unpack(payload)
    status = StatusV1(
        physics_hz=unpacked[0],
        policy_hz=unpacked[1],
        sensor_hz=unpacked[2],
        bridge_latency_ms=unpacked[3],
        contact_count=unpacked[4],
        dropped_frames=unpacked[5],
        watchdog_events=unpacked[6],
        flags=unpacked[7],
        termination_code=unpacked[8],
    )
    # Reuse the encoder as the single semantic validator.
    encode_status_payload(status)
    return status
