"""ROS 2 Foxy adapter for the versioned Lite3 simulation transport."""

import json
from pathlib import Path
import threading
import time
from typing import Optional

import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState, PointCloud2, PointField
from std_msgs.msg import Bool, String
from tf2_ros import TransformBroadcaster

from .pointcloud_rays import ray_cloud_data
from .command_state import CommandLimits
from .feedback_health import SimulationFeedbackMonitor, STALLED
from .state_stream import CompleteStateStream
from .protocol import (
    CommandV1,
    JointStateV1,
    MessageType,
    ProtocolError,
    ScanIdTracker,
    SequenceTracker,
    StatusFlag,
    decode_body_state_payload,
    decode_body_state_v2_payload,
    decode_dual_cloud_sensor_payload,
    decode_joint_state_payload,
    decode_sensor_payload,
    decode_status_payload,
    xyz_f32_be_to_le,
)
from .transport import CommandClient, FrameStreamClient


# /clock is published reliably at depth 1. A rclcpp time source subscribes with
# best-effort QoS, which a reliable publisher satisfies.
CLOCK_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
)


def _time_message(timestamp_ns: int) -> Time:
    if timestamp_ns < 0:
        raise ValueError("timestamp_ns must be non-negative")
    message = Time()
    message.sec = timestamp_ns // 1_000_000_000
    message.nanosec = timestamp_ns % 1_000_000_000
    return message


class FoxyBridgeNode(Node):
    """Publish Isaac telemetry to ROS and forward latest bounded Twist."""

    ZERO = CommandV1(0.0, 0.0, 0.0)

    def __init__(self) -> None:
        super().__init__("lite3_sim_bridge")
        self._telemetry_host = self.declare_parameter("telemetry_host", "127.0.0.1").value
        self._telemetry_port = int(self.declare_parameter("telemetry_port", 46000).value)
        self._command_host = self.declare_parameter("command_host", "127.0.0.1").value
        self._command_port = int(self.declare_parameter("command_port", 46001).value)
        self._connect_timeout = float(
            self.declare_parameter("connect_timeout_seconds", 5.0).value
        )
        self._telemetry_receive_timeout = float(
            self.declare_parameter("telemetry_receive_timeout_seconds", 10.0).value
        )
        self._reconnect_delay = float(
            self.declare_parameter("reconnect_delay_seconds", 0.2).value
        )
        command_rate_hz = float(self.declare_parameter("command_rate_hz", 50.0).value)
        source_timeout_seconds = float(
            self.declare_parameter("source_command_timeout_seconds", 0.25).value
        )
        if (
            command_rate_hz <= 0.0
            or source_timeout_seconds <= 0.0
            or self._connect_timeout <= 0.0
            or self._telemetry_receive_timeout <= 0.0
        ):
            raise ValueError("bridge rates and timeouts must be positive")
        self._command_period = 1.0 / command_rate_hz
        self._source_timeout_ns = int(source_timeout_seconds * 1_000_000_000)
        # A non-positive horizontal-norm limit keeps the original per-axis-only
        # clamp, so every legacy profile behaves exactly as before.
        horizontal_norm = float(
            self.declare_parameter("max_horizontal_command_norm", 0.0).value
        )
        self._limits = CommandLimits(
            max_vx=float(self.declare_parameter("max_vx", 0.75).value),
            max_vy=float(self.declare_parameter("max_vy", 0.35).value),
            max_wz=float(self.declare_parameter("max_wz", 1.0).value),
            max_horizontal_norm=horizontal_norm if horizontal_norm > 0.0 else None,
        )
        self._world_frame = self.declare_parameter("world_frame", "world").value
        self._base_frame = self.declare_parameter("base_frame", "base").value
        self._sensor_frame = self.declare_parameter("sensor_frame", "lidar").value
        body_pose_topic = self.declare_parameter(
            "body_pose_topic", "/quad_0/body_pose"
        ).value
        sensor_pose_topic = self.declare_parameter(
            "sensor_pose_topic", "/quad_0/lidar_pose"
        ).value
        cloud_topic = self.declare_parameter("cloud_topic", "/quad_0/cloud").value
        raw_cloud_topic = self.declare_parameter(
            "raw_cloud_topic", "/quad_0/cloud_raw"
        ).value
        self._require_dual_cloud = bool(
            self.declare_parameter("require_dual_cloud_sensor_frame", False).value
        )
        publish_ray_cloud = bool(self.declare_parameter("publish_ray_cloud", False).value)
        ray_cloud_topic = self.declare_parameter("ray_cloud_topic", "/quad_0/cloud_rays").value
        if publish_ray_cloud and (not self._require_dual_cloud or not ray_cloud_topic
                                  or ray_cloud_topic in (cloud_topic, raw_cloud_topic)):
            raise ValueError("ray cloud requires paired clouds and a distinct nonempty topic")
        self._ray_cloud_publisher = (self.create_publisher(PointCloud2, ray_cloud_topic,
                                    qos_profile_sensor_data) if publish_ray_cloud else None)
        scan_audit_path = self.declare_parameter("scan_audit_path", "").value
        # Simulation clock republication. Off by default so existing profiles are
        # byte-for-byte unchanged.
        self._publish_clock = bool(self.declare_parameter("publish_clock", False).value)
        clock_topic = self.declare_parameter("clock_topic", "/clock").value
        self._max_body_state_age_ns = int(
            float(self.declare_parameter("max_body_state_age_seconds", 0.05).value)
            * 1_000_000_000
        )
        if self._max_body_state_age_ns <= 0:
            raise ValueError("max_body_state_age_seconds must be positive")
        # F4: command arrival alone cannot prove the simulator is still running.
        # When enabled, motion is admitted only while simulation time keeps
        # advancing, measured on the local monotonic clock so a stopped
        # simulation clock cannot hide its own stall. Off by default, so every
        # legacy profile behaves exactly as before.
        self._require_fresh_feedback = bool(
            self.declare_parameter("require_fresh_simulation_feedback", False).value
        )
        max_stall_seconds = float(
            self.declare_parameter("max_simulation_stall_seconds", 0.25).value
        )
        if max_stall_seconds <= 0.0:
            raise ValueError("max_simulation_stall_seconds must be positive")
        self._feedback_monitor = SimulationFeedbackMonitor(
            int(max_stall_seconds * 1_000_000_000)
        )
        self._feedback_blocked_commands = 0
        # F3: an unavailable twist previously reached the planner as an
        # all-zero, normal-looking measured velocity. When enabled, the twist
        # covariance carries the ROS convention for an unmeasured quantity
        # (leading element -1) so a consumer can tell "not measured" from
        # "measured zero". Off by default: the legacy zero-twist profiles keep
        # their exact previous message content.
        self._publish_twist_validity = bool(
            self.declare_parameter("publish_twist_validity", False).value
        )
        # Complete body state at the control cadence. When required, pose and
        # twist always come from the same physics update and odometry no longer
        # inherits the point-cloud cadence. Off by default, so every legacy
        # profile keeps its exact previous behaviour.
        self._require_complete_body_state = bool(
            self.declare_parameter("require_complete_body_state", False).value
        )
        body_state_identity_topic = self.declare_parameter(
            "body_state_identity_topic", "/quad_0/body_state_identity"
        ).value
        trial_fault_topic = self.declare_parameter(
            "trial_fault_topic", "/quad_0/trial_fault"
        ).value
        if not cloud_topic or not raw_cloud_topic or cloud_topic == raw_cloud_topic:
            raise ValueError("raw and planning cloud topics must be distinct and non-empty")
        joint_state_topic = self.declare_parameter(
            "joint_state_topic", "/quad_0/joint_states"
        ).value
        cmd_vel_topic = self.declare_parameter(
            "cmd_vel_topic", "/quad_0/cmd_vel"
        ).value

        self._body_pose_publisher = self.create_publisher(
            Odometry, body_pose_topic, qos_profile_sensor_data
        )
        self._sensor_pose_publisher = self.create_publisher(
            Odometry, sensor_pose_topic, qos_profile_sensor_data
        )
        self._cloud_publisher = self.create_publisher(
            PointCloud2, cloud_topic, qos_profile_sensor_data
        )
        self._raw_cloud_publisher = self.create_publisher(
            PointCloud2, raw_cloud_topic, qos_profile_sensor_data
        )
        self._joint_state_publisher = self.create_publisher(
            JointState, joint_state_topic, 20
        )
        self._clock_publisher = (
            self.create_publisher(Clock, clock_topic, CLOCK_QOS)
            if self._publish_clock
            else None
        )
        # Diagnostics for the complete-state stream. std_msgs/String carrying
        # JSON, matching the existing `planning/trajectory_activation`
        # convention, so no new interface package dependency is introduced.
        self._body_state_identity_publisher = (
            self.create_publisher(String, body_state_identity_topic, 20)
            if self._require_complete_body_state
            else None
        )
        # Latched fatal trial fault. Once true it is never republished false:
        # a reconnect, recovered feedback or a new trajectory must not be able
        # to clear a collision or a terminated trial.
        self._trial_fault_publisher = self.create_publisher(
            Bool,
            trial_fault_topic,
            QoSProfile(
                depth=1,
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                history=HistoryPolicy.KEEP_LAST,
            ),
        )
        self._trial_fault_latched = False
        self._collision_is_fatal = bool(
            self.declare_parameter("collision_is_fatal", True).value
        )
        self._transform_broadcaster = TransformBroadcaster(self)
        self._command_subscription = self.create_subscription(
            Twist, cmd_vel_topic, self._on_twist, 20
        )

        self._latest_lock = threading.Lock()
        self._latest_sensor = None
        self._latest_joint_state = None  # type: Optional[tuple]
        self._latest_status = None
        self._latest_command = self.ZERO
        self._latest_command_monotonic_ns = None  # type: Optional[int]
        self._telemetry_tracker = SequenceTracker()
        self._scan_id_tracker = ScanIdTracker()
        self._telemetry_overwrites = 0
        self._latest_body_state = None  # type: Optional[tuple]
        self._complete_state = CompleteStateStream()
        self._legacy_body_state_frames = 0
        self._published_simulation_time_ns = None  # type: Optional[int]
        self._backward_simulation_time_events = 0
        self._stale_body_state_events = 0
        self._missing_body_state_events = 0
        self._scan_audit_lock = threading.Lock()
        self._scan_audit_file = None
        if scan_audit_path:
            audit_path = Path(scan_audit_path).expanduser()
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            self._scan_audit_file = audit_path.open("a", encoding="utf-8")
        self._stop_event = threading.Event()
        self._telemetry_thread = threading.Thread(
            target=self._telemetry_loop,
            name="foxy-telemetry-client",
            daemon=True,
        )
        self._command_thread = threading.Thread(
            target=self._command_loop,
            name="foxy-command-client",
            daemon=True,
        )
        self._telemetry_thread.start()
        self._command_thread.start()
        self._publish_timer = self.create_timer(0.01, self._publish_latest)
        self.get_logger().info(
            "Lite3 bridge ready: "
            f"telemetry {self._telemetry_host}:{self._telemetry_port}, "
            f"command {self._command_host}:{self._command_port}"
        )

    def _on_twist(self, message: Twist) -> None:
        try:
            checked = self._limits.clamp(
                CommandV1(message.linear.x, message.linear.y, message.angular.z)
            )
        except ProtocolError as error:
            self.get_logger().error(f"Rejecting invalid Twist: {error}")
            return
        with self._latest_lock:
            self._latest_command = checked
            self._latest_command_monotonic_ns = time.monotonic_ns()

    def _telemetry_loop(self) -> None:
        client = FrameStreamClient(
            self._telemetry_host,
            self._telemetry_port,
            self._telemetry_receive_timeout,
        )
        connected = False
        while not self._stop_event.is_set():
            if not connected:
                try:
                    client.connect()
                    connected = True
                    self.get_logger().info("Telemetry stream connected")
                except OSError:
                    self._stop_event.wait(self._reconnect_delay)
                    continue
            try:
                frame = client.receive()
                self._telemetry_tracker.observe(frame.header.sequence)
                if frame.header.message_type == MessageType.SENSOR_FRAME_V1:
                    if self._require_dual_cloud:
                        raise ProtocolError("dual-cloud sensor frame is required")
                    decoded = decode_sensor_payload(frame.payload)
                    with self._latest_lock:
                        if self._latest_sensor is not None:
                            self._telemetry_overwrites += 1
                        self._latest_sensor = (frame.header, decoded)
                elif frame.header.message_type == MessageType.SENSOR_FRAME_DUAL_CLOUD_V1:
                    decoded = decode_dual_cloud_sensor_payload(frame.payload)
                    self._scan_id_tracker.observe(decoded.scan_id)
                    with self._latest_lock:
                        if self._latest_sensor is not None:
                            self._telemetry_overwrites += 1
                            old_header, old_sensor = self._latest_sensor
                            if hasattr(old_sensor, "scan_id"):
                                self._write_scan_audit(
                                    old_header, old_sensor, "overwritten_before_publish"
                                )
                        self._latest_sensor = (frame.header, decoded)
                elif frame.header.message_type == MessageType.STATUS_V1:
                    decoded_status = decode_status_payload(frame.payload)
                    with self._latest_lock:
                        self._latest_status = (frame.header, decoded_status)
                elif frame.header.message_type == MessageType.JOINT_STATE_V1:
                    decoded_joints = decode_joint_state_payload(frame.payload)
                    with self._latest_lock:
                        self._latest_joint_state = (frame.header, decoded_joints)
                elif frame.header.message_type == MessageType.BODY_STATE_V2:
                    decoded_complete = decode_body_state_v2_payload(frame.payload)
                    receive_monotonic_ns = time.monotonic_ns()
                    verdict = self._feedback_monitor.observe(
                        decoded_complete.simulation_time_ns,
                        decoded_complete.state_sequence,
                        receive_monotonic_ns,
                        run_epoch_ns=decoded_complete.run_epoch_ns,
                    )
                    accepted = self._complete_state.offer(
                        decoded_complete, receive_monotonic_ns, verdict.accepted
                    )
                    if not accepted:
                        self.get_logger().warning(
                            "Rejecting a complete body state sample: "
                            f"{self._complete_state.last_rejection} sim_time_ns="
                            f"{decoded_complete.simulation_time_ns} sequence="
                            f"{decoded_complete.state_sequence} run_epoch_ns="
                            f"{decoded_complete.run_epoch_ns}"
                        )
                elif frame.header.message_type == MessageType.BODY_STATE_V1:
                    if self._require_complete_body_state:
                        # A legacy velocity-only sample is not the complete
                        # state this profile requires. It is counted and
                        # ignored; it never becomes freshness evidence.
                        self._legacy_body_state_frames += 1
                        continue
                    decoded_body_state = decode_body_state_payload(frame.payload)
                    verdict = self._feedback_monitor.observe(
                        decoded_body_state.simulation_time_ns,
                        decoded_body_state.state_sequence,
                        time.monotonic_ns(),
                    )
                    if not verdict.accepted:
                        # Out-of-order or backward state is never promoted to
                        # the latest valid sample; keeping it would publish a
                        # plausible measured value under a wrong identity.
                        self.get_logger().warning(
                            "Rejecting a body state sample: "
                            f"{verdict.reason} sim_time_ns="
                            f"{decoded_body_state.simulation_time_ns} sequence="
                            f"{decoded_body_state.state_sequence}"
                        )
                        continue
                    with self._latest_lock:
                        self._latest_body_state = (frame.header, decoded_body_state)
                elif frame.header.message_type != MessageType.HEARTBEAT_V1:
                    raise ProtocolError("unexpected telemetry message type")
            except (EOFError, OSError, ProtocolError) as error:
                if connected:
                    self.get_logger().warning(f"Telemetry stream reset: {error}")
                connected = False
                # Losing telemetry is losing feedback: motion must stop now,
                # not after the next freshness deadline expires.
                self._feedback_monitor.mark_disconnected()
                client.close()
                self._stop_event.wait(self._reconnect_delay)
        client.close()

    def _command_loop(self) -> None:
        client = CommandClient(
            self._command_host,
            self._command_port,
            limits=self._limits,
            timeout_seconds=self._connect_timeout,
        )
        connected = False
        while not self._stop_event.is_set():
            loop_started = time.monotonic()
            if not connected:
                try:
                    client.connect()
                    connected = True
                    self.get_logger().info("Command stream connected")
                except OSError:
                    self._stop_event.wait(self._reconnect_delay)
                    continue
            now_ns = time.monotonic_ns()
            with self._latest_lock:
                command = self._latest_command
                received_ns = self._latest_command_monotonic_ns
            if received_ns is None or now_ns - received_ns > self._source_timeout_ns:
                command = self.ZERO
            if self._trial_fault_latched:
                command = self.ZERO
            if self._require_fresh_feedback or self._require_complete_body_state:
                verdict = self._feedback_monitor.evaluate(now_ns)
                # Native execution omits the project wall-age stopping policy.
                # A disconnected/invalid input or explicit terminal status is
                # still an interface fault, not an instruction to keep driving.
                block_feedback = not verdict.healthy and (
                    self._require_fresh_feedback or verdict.reason != STALLED)
                if block_feedback and command != self.ZERO:
                    self._feedback_blocked_commands += 1
                    self.get_logger().warning(
                        f"Commanding zero: simulator feedback is {verdict.reason}"
                    )
                    command = self.ZERO
            try:
                client.send_command(command, timestamp_ns=now_ns)
            except (ConnectionError, OSError, ProtocolError) as error:
                if connected:
                    self.get_logger().warning(f"Command stream reset: {error}")
                connected = False
                client.close()
            elapsed = time.monotonic() - loop_started
            self._stop_event.wait(max(0.0, self._command_period - elapsed))
        client.close()

    def _publish_simulation_clock(self, timestamp_ns: int) -> None:
        """Republish Isaac simulation time, strictly non-decreasing.

        This node keeps system time itself: its publish timer must keep running
        before any `/clock` message exists, otherwise the first clock
        publication would depend on the clock it is supposed to start. Only the
        planner and controller consume `use_sim_time`.
        """
        if self._clock_publisher is None:
            return
        if (
            self._published_simulation_time_ns is not None
            and timestamp_ns < self._published_simulation_time_ns
        ):
            self._backward_simulation_time_events += 1
            self.get_logger().warning(
                "Dropping a backward simulation timestamp: "
                f"{timestamp_ns} < {self._published_simulation_time_ns}"
            )
            return
        if timestamp_ns == self._published_simulation_time_ns:
            return
        message = Clock()
        message.clock = _time_message(timestamp_ns)
        self._clock_publisher.publish(message)
        self._published_simulation_time_ns = timestamp_ns

    def _publish_latest(self) -> None:
        with self._latest_lock:
            latest_sensor = self._latest_sensor
            self._latest_sensor = None
            latest_status = self._latest_status
            self._latest_status = None
            latest_joint_state = self._latest_joint_state
            self._latest_joint_state = None
            latest_body_state = self._latest_body_state
        if self._require_complete_body_state:
            self._publish_complete_state()
        elif latest_body_state is not None:
            # The body state carries the newest simulation sample, so it sets the
            # clock before any stamped message is published against it.
            self._publish_simulation_clock(latest_body_state[1].simulation_time_ns)
        if latest_sensor is not None:
            header, sensor = latest_sensor
            self._publish_simulation_clock(header.timestamp_ns)
            stamp = _time_message(header.timestamp_ns)
            if not self._require_complete_body_state:
                # Legacy pairing path. In complete-state mode the body pose is
                # published from its own stream instead, so a sensor frame can
                # never contribute a pose sampled at a different time from the
                # twist beside it.
                self._body_pose_publisher.publish(
                    self._odometry_message(
                        stamp,
                        self._base_frame,
                        sensor.body_position,
                        sensor.body_quaternion_xyzw,
                        twist=self._paired_body_twist(
                            header.timestamp_ns, latest_body_state
                        ),
                    )
                )
            sensor_odometry = self._odometry_message(
                stamp,
                self._sensor_frame,
                sensor.sensor_position,
                sensor.sensor_quaternion_xyzw,
            )
            self._sensor_pose_publisher.publish(sensor_odometry)
            self._transform_broadcaster.sendTransform(
                self._transform_message(
                    stamp,
                    self._sensor_frame,
                    sensor.sensor_position,
                    sensor.sensor_quaternion_xyzw,
                )
            )
            if hasattr(sensor, "scan_id"):
                raw_cloud = self._cloud_message(
                    stamp, sensor.raw_point_count, sensor.raw_points_xyz_f32_be
                )
                planner_cloud = self._cloud_message(
                    stamp,
                    sensor.planner_point_count,
                    sensor.planner_points_xyz_f32_be,
                )
                # Both messages come from this one decoded payload and share the
                # exact stamp/frame. ROS publication itself remains sequential.
                self._raw_cloud_publisher.publish(raw_cloud)
                self._cloud_publisher.publish(planner_cloud)
                if self._ray_cloud_publisher is not None:
                    rays = self._cloud_message(stamp, sensor.raw_point_count,
                                               sensor.raw_points_xyz_f32_be)
                    rays.fields.append(PointField(name="occupancy_hit", offset=12,
                                       datatype=PointField.UINT8, count=1))
                    rays.point_step = 16
                    rays.row_step = 16 * sensor.raw_point_count
                    rays.data = ray_cloud_data(sensor.raw_points_xyz_f32_be,
                                               sensor.planner_points_xyz_f32_be)
                    self._ray_cloud_publisher.publish(rays)
                self._write_scan_audit(header, sensor, "published_sequentially")
            else:
                self._cloud_publisher.publish(
                    self._cloud_message(
                        stamp, sensor.point_count, sensor.points_xyz_f32_be
                    )
                )
        if latest_joint_state is not None:
            header, joints = latest_joint_state
            self._joint_state_publisher.publish(
                self._joint_state_message(_time_message(header.timestamp_ns), joints)
            )
        if latest_status is not None:
            _, status = latest_status
            self._observe_status_flags(status.flags)
            if status.flags:
                self.get_logger().debug(
                    "Isaac status "
                    f"flags={status.flags} contacts={status.contact_count} "
                    f"drops={status.dropped_frames} "
                    f"watchdog={status.watchdog_events}"
                )

    def _publish_complete_state(self) -> None:
        """Publish clock, odometry and identity from one complete state sample.

        `take()` returns a sample at most once, keyed on its state sequence, so
        a producer that has stopped stepping cannot be republished as if it kept
        producing new state.
        """
        taken = self._complete_state.take()
        if taken is None:
            return
        state, receive_monotonic_ns = taken
        self._publish_simulation_clock(state.simulation_time_ns)
        stamp = _time_message(state.simulation_time_ns)
        self._body_pose_publisher.publish(
            self._odometry_message(
                stamp,
                self._base_frame,
                state.position_world,
                state.orientation_world_xyzw,
                twist=(state.linear_velocity_body, state.angular_velocity_body),
            )
        )
        publish_monotonic_ns = time.monotonic_ns()
        if self._body_state_identity_publisher is not None:
            message = String()
            message.data = json.dumps(
                {
                    "schema_version": 1,
                    "state_sequence": state.state_sequence,
                    "simulation_time_ns": state.simulation_time_ns,
                    "run_epoch_ns": state.run_epoch_ns,
                    "receive_monotonic_ns": receive_monotonic_ns,
                    "publish_monotonic_ns": publish_monotonic_ns,
                    "bridge_hold_ns": publish_monotonic_ns - receive_monotonic_ns,
                },
                sort_keys=True,
            )
            self._body_state_identity_publisher.publish(message)

    def _observe_status_flags(self, flags: int) -> None:
        """Latch a fatal trial fault. Latched is terminal for this process."""
        fatal = int(StatusFlag.TERMINATED) | int(StatusFlag.NAN_DETECTED)
        if self._collision_is_fatal:
            fatal |= int(StatusFlag.COLLISION)
        if self._trial_fault_latched or not (flags & fatal):
            return
        self._trial_fault_latched = True
        message = Bool()
        message.data = True
        self._trial_fault_publisher.publish(message)
        self.get_logger().error(
            f"Latched a fatal trial fault from status flags {flags}; "
            "execution cannot resume in this trial"
        )

    def diagnostics(self) -> dict:
        """Measured behaviour of the feedback path, for the run record."""
        record = {
            "require_complete_body_state": self._require_complete_body_state,
            "legacy_body_state_frames_ignored": self._legacy_body_state_frames,
            "stale_body_state_events": self._stale_body_state_events,
            "missing_body_state_events": self._missing_body_state_events,
            "backward_simulation_time_events": self._backward_simulation_time_events,
            "telemetry_overwrites": self._telemetry_overwrites,
            "trial_fault_latched": self._trial_fault_latched,
            "collision_is_fatal": self._collision_is_fatal,
        }
        record.update(self._feedback_monitor.counters())
        record.update(self._complete_state.counters())
        return record

    def _paired_body_twist(self, sensor_timestamp_ns: int, latest_body_state):
        """Body-frame twist paired with this sensor sample, or None.

        `nav_msgs/Odometry` twist is expressed in `child_frame_id`, which is the
        base frame here, so the body-frame velocity is the correct field. A body
        state whose simulation time is too far from the sensor stamp is refused
        rather than relabelled with a newer time.
        """
        if latest_body_state is None:
            self._missing_body_state_events += 1
            return None
        _, state = latest_body_state
        age_ns = abs(sensor_timestamp_ns - state.simulation_time_ns)
        if age_ns > self._max_body_state_age_ns:
            self._stale_body_state_events += 1
            self.get_logger().warning(
                "Body state is stale relative to the sensor sample: "
                f"{age_ns} ns > {self._max_body_state_age_ns} ns"
            )
            return None
        return (state.linear_velocity_body, state.angular_velocity_body)

    def _odometry_message(self, stamp, child_frame, position, quaternion, twist=None):
        message = Odometry()
        message.header.stamp = stamp
        message.header.frame_id = self._world_frame
        message.child_frame_id = child_frame
        message.pose.pose.position.x = position[0]
        message.pose.pose.position.y = position[1]
        message.pose.pose.position.z = position[2]
        message.pose.pose.orientation.x = quaternion[0]
        message.pose.pose.orientation.y = quaternion[1]
        message.pose.pose.orientation.z = quaternion[2]
        message.pose.pose.orientation.w = quaternion[3]
        if twist is not None:
            linear, angular = twist
            message.twist.twist.linear.x = float(linear[0])
            message.twist.twist.linear.y = float(linear[1])
            message.twist.twist.linear.z = float(linear[2])
            message.twist.twist.angular.x = float(angular[0])
            message.twist.twist.angular.y = float(angular[1])
            message.twist.twist.angular.z = float(angular[2])
        if self._publish_twist_validity:
            # nav_msgs/Odometry carries no validity flag, so the standard ROS
            # marker for an unmeasured quantity is used: a leading covariance
            # element of -1. A measured sample reports 0.
            message.twist.covariance[0] = 0.0 if twist is not None else -1.0
        return message

    def _transform_message(self, stamp, child_frame, position, quaternion):
        message = TransformStamped()
        message.header.stamp = stamp
        message.header.frame_id = self._world_frame
        message.child_frame_id = child_frame
        message.transform.translation.x = position[0]
        message.transform.translation.y = position[1]
        message.transform.translation.z = position[2]
        message.transform.rotation.x = quaternion[0]
        message.transform.rotation.y = quaternion[1]
        message.transform.rotation.z = quaternion[2]
        message.transform.rotation.w = quaternion[3]
        return message

    def _cloud_message(self, stamp, point_count, point_bytes):
        message = PointCloud2()
        message.header.stamp = stamp
        message.header.frame_id = self._sensor_frame
        message.height = 1
        message.width = point_count
        message.fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        # The TCP payload is network-order. Publish explicit little-endian data
        # for the x86 Foxy/PCL boundary instead of relying on implicit swapping.
        message.is_bigendian = False
        message.point_step = 12
        message.row_step = point_count * 12
        message.data = xyz_f32_be_to_le(point_bytes)
        message.is_dense = True
        return message

    def _write_scan_audit(self, header, sensor, outcome) -> None:
        if self._scan_audit_file is None:
            return
        row = {
            "scan_id": sensor.scan_id,
            "ray_cloud_published": self._ray_cloud_publisher is not None,
            "ray_cloud_point_count": sensor.raw_point_count if self._ray_cloud_publisher is not None else 0,
            "ray_cloud_occupied_endpoints": sensor.planner_point_count if self._ray_cloud_publisher is not None else 0,
            "timestamp_ns": header.timestamp_ns,
            "frame_id": self._sensor_frame,
            "raw_point_count": sensor.raw_point_count,
            "filtered_ground_point_count": sensor.filtered_ground_point_count,
            "planning_point_count": sensor.planner_point_count,
            "conservative_retained_point_count": sensor.conservative_retained_point_count,
            "outcome": outcome,
            "telemetry_overwrite_count": self._telemetry_overwrites,
        }
        with self._scan_audit_lock:
            self._scan_audit_file.write(json.dumps(row, sort_keys=True) + "\n")
            self._scan_audit_file.flush()

    @staticmethod
    def _joint_state_message(stamp, joints: JointStateV1) -> JointState:
        message = JointState()
        message.header.stamp = stamp
        message.name = list(joints.names)
        message.position = list(joints.positions)
        message.velocity = list(joints.velocities)
        return message

    def destroy_node(self):
        self._stop_event.set()
        self._telemetry_thread.join(timeout=2.0)
        self._command_thread.join(timeout=2.0)
        self.get_logger().info("BRIDGE_DIAGNOSTICS " + json.dumps(self.diagnostics(), sort_keys=True))
        if self._scan_audit_file is not None:
            self._scan_audit_file.close()
            self._scan_audit_file = None
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FoxyBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
