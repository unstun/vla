"""Capture native SCAN voxel topics as timestamped, renderable snapshots."""

from __future__ import annotations

import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from scan_planner_msgs.msg import Bspline
from sensor_msgs.msg import PointCloud2
from visualization_msgs.msg import Marker

from .trajectory_review import sample_uniform_bspline
from .voxel_review import _stamp_ns, pointcloud2_xyz, transform_sensor_points


def _yaw_from_odometry(message: Odometry) -> float:
    orientation = message.pose.pose.orientation
    x = float(orientation.x)
    y = float(orientation.y)
    z = float(orientation.z)
    w = float(orientation.w)
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class VoxelCaptureNode(Node):
    """Persist raw/inflated PointCloud2 payloads without scene-truth geometry."""

    def __init__(self) -> None:
        super().__init__("lite3_voxel_capture")
        self._output_dir = Path(
            self.declare_parameter("output_dir", "/tmp/lite3_voxel_snapshots").value
        )
        self._metadata_path = Path(
            self.declare_parameter(
                "metadata_path", "/tmp/lite3_voxel_frames.jsonl"
            ).value
        )
        self._summary_path = Path(
            self.declare_parameter(
                "summary_path", "/tmp/lite3_voxel_capture_summary.json"
            ).value
        )
        period_seconds = float(
            self.declare_parameter("capture_period_seconds", 0.1).value
        )
        if not math.isfinite(period_seconds) or period_seconds <= 0.0:
            raise ValueError("capture_period_seconds must be positive and finite")
        self._capture_period_ns = int(round(period_seconds * 1.0e9))
        self._output_dir.mkdir(parents=True, exist_ok=False)
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self._summary_path.parent.mkdir(parents=True, exist_ok=True)
        self._metadata = self._metadata_path.open("x", encoding="utf-8")
        self._raw_points = None
        self._raw_stamp_ns = None
        self._raw_receipt_ns = None
        self._live_points_world = None
        self._live_stamp_ns = None
        self._sensor_position = None
        self._sensor_quaternion_xyzw = None
        self._body_position = None
        self._body_yaw_rad = 0.0
        self._body_stamp_ns = None
        self._bbox_points = np.empty((0, 3), dtype=np.float32)
        self._plan_points = np.empty((0, 3), dtype=np.float32)
        self._trajectory_id = -1
        self._last_saved_body_stamp_ns = None
        self._frame_count = 0
        self._raw_counts = []
        self._inflated_counts = []
        self._live_counts = []
        self._body_stamps = []
        self._trajectory_ids = set()
        self._decode_errors = 0
        self._closed = False

        self.create_subscription(
            PointCloud2, "/quad_0/cloud_raw", self._live_cloud, qos_profile_sensor_data
        )
        self.create_subscription(
            Odometry, "/quad_0/lidar_pose", self._sensor_pose, qos_profile_sensor_data
        )
        self.create_subscription(
            PointCloud2,
            "/grid_map/occupancy",
            self._raw_occupancy,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            PointCloud2,
            "/grid_map/occupancy_inflate",
            self._inflated_occupancy,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            Marker, "/grid_map/sliding_map_bbox", self._sliding_bounds, 10
        )
        self.create_subscription(
            Odometry, "/quad_0/body_pose", self._body_pose, qos_profile_sensor_data
        )
        self.create_subscription(Bspline, "/planning/bspline", self._bspline, 20)
        self.get_logger().info(
            f"Capturing native SCAN voxels into {self._output_dir}"
        )

    def _raw_occupancy(self, message: PointCloud2) -> None:
        try:
            self._raw_points = pointcloud2_xyz(message)
            self._raw_stamp_ns = _stamp_ns(message)
            self._raw_receipt_ns = time.monotonic_ns()
        except ValueError as error:
            self._decode_errors += 1
            self.get_logger().error(f"Reject raw occupancy cloud: {error}")

    def _sensor_pose(self, message: Odometry) -> None:
        position = message.pose.pose.position
        orientation = message.pose.pose.orientation
        self._sensor_position = np.asarray(
            [float(position.x), float(position.y), float(position.z)], dtype=np.float64
        )
        self._sensor_quaternion_xyzw = np.asarray(
            [
                float(orientation.x),
                float(orientation.y),
                float(orientation.z),
                float(orientation.w),
            ],
            dtype=np.float64,
        )

    def _live_cloud(self, message: PointCloud2) -> None:
        if self._sensor_position is None or self._sensor_quaternion_xyzw is None:
            return
        try:
            points = pointcloud2_xyz(message)
            self._live_points_world = transform_sensor_points(
                points, self._sensor_position, self._sensor_quaternion_xyzw
            )
            self._live_stamp_ns = _stamp_ns(message)
        except ValueError as error:
            self._decode_errors += 1
            self.get_logger().error(f"Reject live sensor cloud: {error}")

    def _inflated_occupancy(self, message: PointCloud2) -> None:
        try:
            inflated = pointcloud2_xyz(message)
        except ValueError as error:
            self._decode_errors += 1
            self.get_logger().error(f"Reject inflated occupancy cloud: {error}")
            return
        self._capture(inflated, _stamp_ns(message), time.monotonic_ns())

    def _body_pose(self, message: Odometry) -> None:
        position = message.pose.pose.position
        values = np.asarray(
            [float(position.x), float(position.y), float(position.z)],
            dtype=np.float32,
        )
        if not np.isfinite(values).all():
            return
        self._body_position = values
        self._body_yaw_rad = _yaw_from_odometry(message)
        self._body_stamp_ns = _stamp_ns(message)

    def _sliding_bounds(self, message: Marker) -> None:
        points = np.asarray(
            [[float(point.x), float(point.y), float(point.z)] for point in message.points],
            dtype=np.float32,
        )
        if points.ndim == 2 and points.shape[1:] == (3,) and np.isfinite(points).all():
            self._bbox_points = points

    def _bspline(self, message: Bspline) -> None:
        control_points = [
            (float(point.x), float(point.y), float(point.z))
            for point in message.pos_pts
        ]
        try:
            sampled = sample_uniform_bspline(
                int(message.order),
                [float(value) for value in message.knots],
                control_points,
                sample_count=160,
            )
        except ValueError as error:
            self.get_logger().error(f"Reject malformed B-spline: {error}")
            return
        self._plan_points = np.asarray(sampled, dtype=np.float32)
        self._trajectory_id = int(message.traj_id)
        self._trajectory_ids.add(self._trajectory_id)

    def _capture(
        self, inflated: np.ndarray, inflated_stamp_ns: int, inflated_receipt_ns: int
    ) -> None:
        if (
            self._raw_points is None
            or self._live_points_world is None
            or len(self._live_points_world) == 0
            or len(self._raw_points) == 0
            or len(inflated) == 0
            or self._body_position is None
            or self._body_stamp_ns is None
            or self._raw_stamp_ns is None
            or self._raw_receipt_ns is None
        ):
            return
        if self._last_saved_body_stamp_ns is not None:
            elapsed = self._body_stamp_ns - self._last_saved_body_stamp_ns
            if elapsed < self._capture_period_ns:
                return
        if self._last_saved_body_stamp_ns is not None and (
            self._body_stamp_ns <= self._last_saved_body_stamp_ns
        ):
            return

        snapshot_name = f"frame_{self._frame_count:06d}.npz"
        snapshot_path = self._output_dir / snapshot_name
        np.savez(
            snapshot_path,
            raw_points=self._raw_points.astype(np.float32, copy=False),
            live_points=self._live_points_world.astype(np.float32, copy=False),
            inflated_points=inflated.astype(np.float32, copy=False),
            body_position=self._body_position,
            body_yaw_rad=np.asarray(self._body_yaw_rad, dtype=np.float64),
            bbox_points=self._bbox_points,
            plan_points=self._plan_points,
            trajectory_id=np.asarray(self._trajectory_id, dtype=np.int64),
            body_stamp_ns=np.asarray(self._body_stamp_ns, dtype=np.int64),
            raw_stamp_ns=np.asarray(self._raw_stamp_ns, dtype=np.int64),
            live_stamp_ns=np.asarray(self._live_stamp_ns, dtype=np.int64),
            inflated_stamp_ns=np.asarray(inflated_stamp_ns, dtype=np.int64),
        )
        record = {
            "schema_version": 2,
            "frame_index": self._frame_count,
            "snapshot_file": snapshot_name,
            "body_stamp_ns": self._body_stamp_ns,
            "raw_header_stamp_ns": self._raw_stamp_ns,
            "inflated_header_stamp_ns": inflated_stamp_ns,
            "raw_receipt_monotonic_ns": self._raw_receipt_ns,
            "inflated_receipt_monotonic_ns": inflated_receipt_ns,
            "raw_point_count": len(self._raw_points),
            "live_point_count": len(self._live_points_world),
            "inflated_point_count": len(inflated),
            "bbox_point_count": len(self._bbox_points),
            "trajectory_id": self._trajectory_id,
            "plan_point_count": len(self._plan_points),
            "body_position": self._body_position.tolist(),
            "body_yaw_rad": self._body_yaw_rad,
        }
        self._metadata.write(json.dumps(record, sort_keys=True) + "\n")
        self._metadata.flush()
        self._raw_counts.append(len(self._raw_points))
        self._live_counts.append(len(self._live_points_world))
        self._inflated_counts.append(len(inflated))
        self._body_stamps.append(self._body_stamp_ns)
        self._last_saved_body_stamp_ns = self._body_stamp_ns
        self._frame_count += 1

    def finalize(self) -> None:
        if self._closed:
            return
        self._metadata.close()
        checks = {
            "captured_frames": self._frame_count > 0,
            "raw_occupancy_nonempty": bool(self._raw_counts) and min(self._raw_counts) > 0,
            "live_sensor_cloud_nonempty": bool(self._live_counts) and min(self._live_counts) > 0,
            "inflated_occupancy_nonempty": bool(self._inflated_counts)
            and min(self._inflated_counts) > 0,
            "body_time_advances": len(set(self._body_stamps)) > 1,
            "bspline_observed": bool(self._trajectory_ids),
            "decode_errors_zero": self._decode_errors == 0,
        }
        summary = {
            "schema_version": 2,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "claim_boundary": (
                "native live sensor cloud plus SCAN PointCloud2 occupancy capture; no Isaac scene-truth voxels"
            ),
            "topics": [
                "/grid_map/occupancy",
                "/grid_map/occupancy_inflate",
                "/quad_0/cloud_raw",
                "/quad_0/lidar_pose",
                "/grid_map/sliding_map_bbox",
                "/quad_0/body_pose",
                "/planning/bspline",
            ],
            "checks": checks,
            "frame_count": self._frame_count,
            "capture_period_seconds": self._capture_period_ns / 1.0e9,
            "first_body_stamp_ns": min(self._body_stamps, default=None),
            "last_body_stamp_ns": max(self._body_stamps, default=None),
            "raw_point_count_min": min(self._raw_counts, default=None),
            "raw_point_count_max": max(self._raw_counts, default=None),
            "live_point_count_min": min(self._live_counts, default=None),
            "live_point_count_max": max(self._live_counts, default=None),
            "inflated_point_count_min": min(self._inflated_counts, default=None),
            "inflated_point_count_max": max(self._inflated_counts, default=None),
            "trajectory_ids": sorted(self._trajectory_ids),
            "decode_error_count": self._decode_errors,
        }
        self._summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._closed = True

    def destroy_node(self):
        self.finalize()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VoxelCaptureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
