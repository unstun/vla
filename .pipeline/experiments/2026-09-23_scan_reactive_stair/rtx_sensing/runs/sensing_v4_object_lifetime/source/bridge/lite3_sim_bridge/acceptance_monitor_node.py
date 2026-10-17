"""Record ROS-side rates and synchronized closed-loop evidence."""

import json
from pathlib import Path
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from scan_planner_msgs.msg import Bspline, FeedbackRecoveryAck, FeedbackRecoveryRequest
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String

from .monitor_core import AcceptanceAccumulator, should_record_periodic_event
from .voxel_review import pointcloud2_xyz


def _stamp_ns(message) -> int:
    return int(message.header.stamp.sec) * 1_000_000_000 + int(
        message.header.stamp.nanosec
    )


class AcceptanceMonitorNode(Node):
    """Subscribe with matching QoS and persist a compact ROS-side trace."""

    def __init__(self) -> None:
        super().__init__("lite3_acceptance_monitor")
        event_path = Path(
            self.declare_parameter("event_log_path", "/tmp/lite3_acceptance_ros.jsonl").value
        )
        summary_path = Path(
            self.declare_parameter(
                "summary_path", "/tmp/lite3_acceptance_ros_summary.json"
            ).value
        )
        event_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        self._event_path = event_path
        self._summary_path = summary_path
        self._events = event_path.open("w", encoding="utf-8")
        self._lock = threading.Lock()
        self._accumulator = AcceptanceAccumulator()
        self._closed = False
        self._record_counts = {}
        self._started_ns = time.monotonic_ns()
        self._occupancy_sample_limit = int(
            self.declare_parameter("occupancy_sample_limit", 5000).value
        )
        occupancy_period_seconds = float(
            self.declare_parameter("occupancy_event_period_seconds", 0.1).value
        )
        if self._occupancy_sample_limit <= 0:
            raise ValueError("occupancy_sample_limit must be positive")
        if occupancy_period_seconds <= 0.0:
            raise ValueError("occupancy_event_period_seconds must be positive")
        self._occupancy_event_period_ns = int(occupancy_period_seconds * 1.0e9)
        self._last_occupancy_stamp_ns = 0
        self._latest_body_stamp_ns = 0
        self._latest_body_receipt_ns = 0

        self.create_subscription(
            Odometry, "/quad_0/body_pose", self._body_pose, qos_profile_sensor_data
        )
        self.create_subscription(
            Odometry, "/quad_0/lidar_pose", self._sensor_pose, qos_profile_sensor_data
        )
        self.create_subscription(
            PointCloud2, "/quad_0/cloud", self._cloud, qos_profile_sensor_data
        )
        self.create_subscription(Twist, "/quad_0/cmd_vel", self._command, 50)
        self.create_subscription(Bspline, "/planning/bspline", self._bspline, 20)
        self.create_subscription(
            PointCloud2,
            "/grid_map/occupancy_inflate",
            self._occupancy_inflate,
            qos_profile_sensor_data,
        )
        # Feedback stop/recovery causal chain. Recorded so a stop, its request,
        # the planner's answer and the trajectory that released it can be
        # reconciled from one file, on one receipt clock.
        self.create_subscription(
            String, "/planning/recovery_event", self._recovery_event, 50
        )
        self.create_subscription(
            FeedbackRecoveryRequest,
            "/planning/feedback_recovery_request",
            self._recovery_request,
            rclpy.qos.QoSProfile(depth=20, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE),
        )
        self.create_subscription(
            FeedbackRecoveryAck,
            "/planning/feedback_recovery_ack",
            self._recovery_ack,
            rclpy.qos.QoSProfile(depth=20, reliability=rclpy.qos.ReliabilityPolicy.RELIABLE),
        )
        self.create_subscription(
            String, "/quad_0/body_state_identity", self._body_state_identity,
            qos_profile_sensor_data,
        )
        self._write({"kind": "monitor_started", "schema_version": 2,
                     "receipt_monotonic_ns": self._started_ns,
                     "recovery_recording_enabled": True})
        self.get_logger().info(
            f"Acceptance monitor writing {event_path} and {summary_path}"
        )

    def _write(self, value) -> None:
        kind = value["kind"]
        self._record_counts[kind] = self._record_counts.get(kind, 0) + 1
        self._events.write(json.dumps(value, sort_keys=True) + "\n")
        self._events.flush()

    def _body_pose(self, message: Odometry) -> None:
        receipt = time.monotonic_ns()
        stamp = _stamp_ns(message)
        self._latest_body_stamp_ns = stamp
        self._latest_body_receipt_ns = receipt
        position = message.pose.pose.position
        values = (position.x, position.y, position.z)
        with self._lock:
            self._accumulator.observe_body_pose(receipt, stamp, values)
            self._write(
                {
                    "kind": "body_pose",
                    "receipt_monotonic_ns": receipt,
                    "stamp_ns": stamp,
                    "position": values,
                }
            )

    def _recovery_event(self, message: String) -> None:
        receipt = time.monotonic_ns()
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            payload = {"unparsed": message.data}
        with self._lock:
            self._write(
                {
                    "kind": "recovery_event",
                    "receipt_monotonic_ns": receipt,
                    "data": payload,
                }
            )

    def _recovery_request(self, message: FeedbackRecoveryRequest) -> None:
        receipt = time.monotonic_ns()
        with self._lock:
            self._write(
                {
                    "kind": "recovery_request",
                    "receipt_monotonic_ns": receipt,
                    "controller_epoch": message.controller_epoch,
                    "request_id": message.request_id,
                    "reason": message.reason,
                    "attempt": int(message.attempt),
                    "state_sequence": int(message.state_sequence),
                    "run_epoch_ns": int(message.run_epoch_ns),
                    "state_stamp_ns": int(message.state_stamp.sec) * 1_000_000_000
                    + int(message.state_stamp.nanosec),
                }
            )

    def _recovery_ack(self, message: FeedbackRecoveryAck) -> None:
        receipt = time.monotonic_ns()
        with self._lock:
            self._write(
                {
                    "kind": "recovery_ack",
                    "receipt_monotonic_ns": receipt,
                    "controller_epoch": message.controller_epoch,
                    "request_id": message.request_id,
                    "accepted": bool(message.accepted),
                    "reason": message.reason,
                    "traj_id": int(message.traj_id),
                    "state_sequence": int(message.state_sequence),
                    "plan_stamp_ns": int(message.plan_stamp.sec) * 1_000_000_000
                    + int(message.plan_stamp.nanosec),
                }
            )

    def _body_state_identity(self, message: String) -> None:
        receipt = time.monotonic_ns()
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            return
        with self._lock:
            self._write(
                {
                    "kind": "body_state_identity",
                    "receipt_monotonic_ns": receipt,
                    "data": payload,
                }
            )

    def _sensor_pose(self, message: Odometry) -> None:
        receipt = time.monotonic_ns()
        stamp = _stamp_ns(message)
        with self._lock:
            self._accumulator.observe_sensor_pose(receipt, stamp)
            self._write(
                {
                    "kind": "sensor_pose",
                    "receipt_monotonic_ns": receipt,
                    "stamp_ns": stamp,
                }
            )

    def _cloud(self, message: PointCloud2) -> None:
        receipt = time.monotonic_ns()
        stamp = _stamp_ns(message)
        count = int(message.width) * int(message.height)
        with self._lock:
            self._accumulator.observe_cloud(receipt, stamp, count)
            self._write(
                {
                    "kind": "cloud",
                    "receipt_monotonic_ns": receipt,
                    "stamp_ns": stamp,
                    "point_count": count,
                    "is_bigendian": bool(message.is_bigendian),
                }
            )

    def _command(self, message: Twist) -> None:
        receipt = time.monotonic_ns()
        command = (message.linear.x, message.linear.y, message.angular.z)
        with self._lock:
            self._accumulator.observe_command(receipt, command)
            self._write(
                {
                    "kind": "cmd_vel",
                    "receipt_monotonic_ns": receipt,
                    "command": command,
                }
            )

    def _bspline(self, message: Bspline) -> None:
        receipt = time.monotonic_ns()
        simulator_stamp = self._latest_body_stamp_ns
        simulator_stamp_receipt_age_s = (
            (receipt - self._latest_body_receipt_ns) * 1.0e-9
            if self._latest_body_receipt_ns > 0
            else None
        )
        start_time_ns = int(message.start_time.sec) * 1_000_000_000 + int(
            message.start_time.nanosec
        )
        control_points = [
            [float(point.x), float(point.y), float(point.z)]
            for point in message.pos_pts
        ]
        with self._lock:
            self._accumulator.observe_bspline(receipt, message.traj_id)
            self._write(
                {
                    "kind": "bspline",
                    "receipt_monotonic_ns": receipt,
                    "simulator_stamp_ns": simulator_stamp,
                    "simulator_stamp_receipt_age_s": simulator_stamp_receipt_age_s,
                    "trajectory_id": int(message.traj_id),
                    "start_time_ns": start_time_ns,
                    "order": int(message.order),
                    "knots": [float(value) for value in message.knots],
                    "control_points": control_points,
                    "control_point_count": len(control_points),
                    "yaw_points": [float(value) for value in message.yaw_pts],
                    "yaw_dt": float(message.yaw_dt),
                }
            )

    def _occupancy_inflate(self, message: PointCloud2) -> None:
        """Record a bounded sample of SCAN's real inflated occupancy output."""

        receipt = time.monotonic_ns()
        source_stamp = _stamp_ns(message)
        simulator_stamp = self._latest_body_stamp_ns
        if simulator_stamp <= 0:
            return
        if not should_record_periodic_event(
            self._last_occupancy_stamp_ns,
            simulator_stamp,
            self._occupancy_event_period_ns,
        ):
            return
        self._last_occupancy_stamp_ns = simulator_stamp
        points = pointcloud2_xyz(message)
        source_count = int(len(points))
        if source_count > self._occupancy_sample_limit:
            stride = max(1, source_count // self._occupancy_sample_limit)
            points = points[::stride][: self._occupancy_sample_limit]
        with self._lock:
            self._write(
                {
                    "kind": "occupancy_inflate",
                    "receipt_monotonic_ns": receipt,
                    "stamp_ns": simulator_stamp,
                    "source_stamp_ns": source_stamp,
                    "point_count": source_count,
                    "sample_count": int(len(points)),
                    "sample_stride": (
                        1
                        if source_count <= self._occupancy_sample_limit
                        else max(1, source_count // self._occupancy_sample_limit)
                    ),
                    "points_xyz": points.astype(float, copy=False).tolist(),
                }
            )

    def finalize(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._write({"kind": "monitor_finished", "schema_version": 2,
                         "receipt_monotonic_ns": time.monotonic_ns(),
                         "record_counts": dict(self._record_counts)})
            summary = self._accumulator.summary()
            summary["monitor_duration_seconds"] = (
                time.monotonic_ns() - self._started_ns
            ) / 1.0e9
            self._summary_path.write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._events.close()
            self._closed = True

    def destroy_node(self):
        self.finalize()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AcceptanceMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
