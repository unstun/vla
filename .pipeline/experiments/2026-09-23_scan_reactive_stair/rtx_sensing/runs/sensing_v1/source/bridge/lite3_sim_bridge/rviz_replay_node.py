"""Convert recorded SCAN trajectories into standard paths for Humble RViz."""

from __future__ import annotations

import bisect
import json
from pathlib import Path
import time

import numpy as np
import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point, PoseStamped, TransformStamped
from nav_msgs.msg import Odometry, Path as NavPath
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from scan_planner_msgs.msg import Bspline
from sensor_msgs.msg import PointCloud2, PointField
from visualization_msgs.msg import Marker
from tf2_ros import TransformBroadcaster

from .rviz_replay_core import ReplayAuditState
from .trajectory_review import sample_uniform_bspline


def _stamp_ns(stamp) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def _time_from_ns(stamp_ns: int) -> Time:
    stamp = Time()
    stamp.sec, stamp.nanosec = divmod(int(stamp_ns), 1_000_000_000)
    return stamp


def _pointcloud2_xyz(points: np.ndarray, stamp_ns: int, frame_id: str) -> PointCloud2:
    checked_points = np.asarray(points, dtype=np.float32)
    if (
        checked_points.ndim != 2
        or checked_points.shape[1:] != (3,)
        or len(checked_points) == 0
        or not np.isfinite(checked_points).all()
    ):
        raise ValueError("replayed PointCloud2 coordinates must be finite Nx3 values")
    padded_points = np.zeros((len(checked_points), 4), dtype=np.float32)
    padded_points[:, :3] = checked_points
    message = PointCloud2()
    message.header.stamp = _time_from_ns(stamp_ns)
    message.header.frame_id = frame_id
    message.height = 1
    message.width = len(checked_points)
    message.fields = [
        PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    message.is_bigendian = False
    message.point_step = 16
    message.row_step = message.point_step * message.width
    message.data = padded_points.tobytes(order="C")
    message.is_dense = True
    return message


class RvizReplayNode(Node):
    """Publish exact recorded B-splines and body poses as standard ROS paths."""

    def __init__(self) -> None:
        super().__init__("lite3_humble_rviz_replay")
        self._frame_id = str(self.declare_parameter("frame_id", "world").value)
        self._source_mode = str(
            self.declare_parameter("source_mode", "replay").value
        )
        self._robot_root_frame = str(
            self.declare_parameter("robot_root_frame", "").value
        )
        self._sample_count = int(self.declare_parameter("sample_count", 160).value)
        if not self._frame_id:
            raise ValueError("frame_id must not be empty")
        if self._source_mode not in ("replay", "live"):
            raise ValueError("source_mode must be replay or live")
        if self._robot_root_frame == self._frame_id:
            raise ValueError("robot_root_frame must differ from frame_id")
        if self._source_mode == "live" and not self._robot_root_frame:
            raise ValueError("live source_mode requires robot_root_frame")
        if self._sample_count < 2:
            raise ValueError("sample_count must be at least two")
        audit_value = str(self.declare_parameter("audit_path", "").value)
        self._audit_path = Path(audit_value).expanduser() if audit_value else None
        metadata_value = str(self.declare_parameter("voxel_metadata_path", "").value)
        snapshot_value = str(self.declare_parameter("voxel_snapshot_dir", "").value)
        self._voxel_metadata_path = (
            Path(metadata_value).expanduser() if metadata_value else None
        )
        self._voxel_snapshot_dir = (
            Path(snapshot_value).expanduser() if snapshot_value else None
        )
        self._bbox_records = self._load_bbox_records()
        self._bbox_stamps = [record[0] for record in self._bbox_records]
        self._last_bbox_snapshot = None
        self._preload_first_snapshot = bool(
            self.declare_parameter("preload_first_snapshot", True).value
        )
        self._require_live_lidar = bool(
            self.declare_parameter("require_live_lidar", False).value
        )
        self._audit = ReplayAuditState(
            sample_count=self._sample_count,
            source_mode=self._source_mode,
            require_live_lidar=self._require_live_lidar,
            require_voxel_snapshots=self._source_mode == "replay",
            require_root_transform=bool(self._robot_root_frame),
        )
        self._actual_path = NavPath()
        self._actual_path.header.frame_id = self._frame_id
        self._closed = False

        review_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._planned_path_publisher = self.create_publisher(
            NavPath, "/review/scan_planned_path", review_qos
        )
        self._actual_path_publisher = self.create_publisher(
            NavPath, "/review/lite3_actual_path", review_qos
        )
        self._current_pose_publisher = self.create_publisher(
            PoseStamped, "/review/lite3_current_pose", review_qos
        )
        self._transform_broadcaster = (
            TransformBroadcaster(self) if self._robot_root_frame else None
        )
        self._bbox_publisher = self.create_publisher(
            Marker, "/review/sliding_map_bbox", review_qos
        )
        self._raw_voxel_publisher = self.create_publisher(
            PointCloud2, "/review/occupancy", review_qos
        )
        self._live_lidar_publisher = self.create_publisher(
            PointCloud2, "/review/live_lidar", review_qos
        )
        self._inflated_voxel_publisher = self.create_publisher(
            PointCloud2, "/review/occupancy_inflate", review_qos
        )
        self.create_subscription(
            Odometry,
            "/quad_0/body_pose",
            self._body_pose,
            qos_profile_sensor_data,
        )
        self.create_subscription(Bspline, "/planning/bspline", self._bspline, 20)
        if self._source_mode == "live":
            self.create_subscription(
                PointCloud2,
                "/quad_0/cloud_raw",
                self._live_lidar,
                qos_profile_sensor_data,
            )
        if self._preload_first_snapshot and self._bbox_records:
            first_snapshot_file = self._bbox_records[0][1]
            self._publish_snapshot_file(first_snapshot_file, None)
            self._audit.record_preloaded_snapshot(first_snapshot_file)
        self.get_logger().info(
            f"{self._source_mode} visualization adapter ready; "
            "it republishes paths and robot pose but does not plan"
        )

    def _load_bbox_records(self) -> tuple[tuple[int, str], ...]:
        if self._voxel_metadata_path is None and self._voxel_snapshot_dir is None:
            return ()
        if self._voxel_metadata_path is None or self._voxel_snapshot_dir is None:
            raise ValueError(
                "voxel_metadata_path and voxel_snapshot_dir must be provided together"
            )
        if not self._voxel_metadata_path.is_file():
            raise FileNotFoundError(self._voxel_metadata_path)
        if not self._voxel_snapshot_dir.is_dir():
            raise FileNotFoundError(self._voxel_snapshot_dir)
        records = []
        for line in self._voxel_metadata_path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            snapshot_file = str(row["snapshot_file"])
            if not (self._voxel_snapshot_dir / snapshot_file).is_file():
                raise FileNotFoundError(self._voxel_snapshot_dir / snapshot_file)
            records.append((int(row["body_stamp_ns"]), snapshot_file))
        if not records:
            raise ValueError("voxel metadata contains no replay snapshots")
        records.sort()
        if len({stamp for stamp, _ in records}) != len(records):
            raise ValueError("voxel metadata body stamps must be unique")
        return tuple(records)

    def _body_pose(self, message: Odometry) -> None:
        stamp_ns = _stamp_ns(message.header.stamp)
        if not self._audit.accept_body_stamp(stamp_ns):
            self.get_logger().warning(
                f"Reject non-increasing body stamp {stamp_ns} during replay"
            )
            return
        pose = PoseStamped()
        pose.header.stamp = message.header.stamp
        pose.header.frame_id = self._frame_id
        pose.pose = message.pose.pose
        self._actual_path.header.stamp = message.header.stamp
        self._actual_path.poses.append(pose)
        self._actual_path_publisher.publish(self._actual_path)
        self._current_pose_publisher.publish(pose)
        root_transform_published = False
        if self._transform_broadcaster is not None:
            transform = TransformStamped()
            transform.header = message.header
            transform.header.frame_id = self._frame_id
            transform.child_frame_id = self._robot_root_frame
            transform.transform.translation.x = message.pose.pose.position.x
            transform.transform.translation.y = message.pose.pose.position.y
            transform.transform.translation.z = message.pose.pose.position.z
            transform.transform.rotation = message.pose.pose.orientation
            self._transform_broadcaster.sendTransform(transform)
            root_transform_published = True
        self._audit.accept_current_pose(
            root_transform_published=root_transform_published
        )
        self._publish_snapshot(stamp_ns, message.header.stamp)

    def _live_lidar(self, message: PointCloud2) -> None:
        """Observe the same cloud RViz receives; never mutate or republish it."""

        declared_point_count = int(message.width) * int(message.height)
        expected_data_size = int(message.row_step) * int(message.height)
        point_count = (
            declared_point_count
            if declared_point_count > 0
            and int(message.point_step) > 0
            and expected_data_size > 0
            and len(message.data) >= expected_data_size
            else 0
        )
        self._audit.accept_live_lidar_message(
            stamp_ns=_stamp_ns(message.header.stamp),
            point_count=point_count,
            wall_time_ns=time.monotonic_ns(),
        )

    def _publish_snapshot(self, body_stamp_ns: int, header_stamp) -> None:
        if not self._bbox_records:
            return
        insertion = bisect.bisect_left(self._bbox_stamps, body_stamp_ns)
        candidates = []
        if insertion < len(self._bbox_records):
            candidates.append(self._bbox_records[insertion])
        if insertion > 0:
            candidates.append(self._bbox_records[insertion - 1])
        _, snapshot_file = min(
            candidates, key=lambda record: abs(record[0] - body_stamp_ns)
        )
        if snapshot_file == self._last_bbox_snapshot:
            return
        self._publish_snapshot_file(snapshot_file, header_stamp)

    def _publish_snapshot_file(self, snapshot_file: str, header_stamp) -> None:
        snapshot_path = self._voxel_snapshot_dir / snapshot_file
        with np.load(snapshot_path) as snapshot:
            live_points = np.asarray(
                snapshot["live_points"]
                if "live_points" in snapshot
                else np.empty((0, 3), dtype=np.float32),
                dtype=np.float32,
            )
            raw_points = np.asarray(snapshot["raw_points"], dtype=np.float32)
            inflated_points = np.asarray(
                snapshot["inflated_points"], dtype=np.float32
            )
            bbox_points = np.asarray(snapshot["bbox_points"], dtype=np.float64)
            live_stamp_ns = int(
                snapshot["live_stamp_ns"]
                if "live_stamp_ns" in snapshot
                else snapshot["raw_stamp_ns"]
            )
            raw_stamp_ns = int(snapshot["raw_stamp_ns"])
            inflated_stamp_ns = int(snapshot["inflated_stamp_ns"])
        if (
            bbox_points.ndim != 2
            or bbox_points.shape[1:] != (3,)
            or len(bbox_points) == 0
            or not np.isfinite(bbox_points).all()
        ):
            raise ValueError(f"invalid bbox_points in {snapshot_path}")

        self._raw_voxel_publisher.publish(
            _pointcloud2_xyz(raw_points, raw_stamp_ns, self._frame_id)
        )
        if len(live_points) > 0:
            self._live_lidar_publisher.publish(
                _pointcloud2_xyz(live_points, live_stamp_ns, self._frame_id)
            )
        self._inflated_voxel_publisher.publish(
            _pointcloud2_xyz(inflated_points, inflated_stamp_ns, self._frame_id)
        )

        marker = Marker()
        marker.header.stamp = (
            header_stamp if header_stamp is not None else _time_from_ns(raw_stamp_ns)
        )
        marker.header.frame_id = self._frame_id
        marker.ns = "scan_sliding_map_bbox"
        marker.id = 0
        marker.type = Marker.LINE_LIST
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.scale.x = 0.02
        marker.color.r = 0.1
        marker.color.g = 0.7
        marker.color.b = 1.0
        marker.color.a = 0.45
        marker.points = [
            Point(x=float(x), y=float(y), z=float(z))
            for x, y, z in bbox_points
        ]
        self._bbox_publisher.publish(marker)
        self._audit.accept_bbox_snapshot(snapshot_file)
        self._audit.accept_voxel_snapshot(
            snapshot_file,
            len(raw_points),
            len(inflated_points),
            len(live_points),
        )
        self._last_bbox_snapshot = snapshot_file

    def _bspline(self, message: Bspline) -> None:
        control_points = [
            (float(point.x), float(point.y), float(point.z))
            for point in message.pos_pts
        ]
        try:
            sampled_points = sample_uniform_bspline(
                int(message.order),
                [float(value) for value in message.knots],
                control_points,
                sample_count=self._sample_count,
            )
        except ValueError as error:
            self._audit.reject_bspline()
            self.get_logger().error(f"Reject malformed recorded B-spline: {error}")
            return

        path = NavPath()
        path.header.stamp = message.start_time
        path.header.frame_id = self._frame_id
        for x, y, z in sampled_points:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = z
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self._audit.accept_bspline(
            int(message.traj_id), len(path.poses), _stamp_ns(message.start_time)
        )
        self._planned_path_publisher.publish(path)

    def finalize(self) -> None:
        if self._closed:
            return
        if self._audit_path is not None:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self._audit_path.with_suffix(
                self._audit_path.suffix + ".tmp"
            )
            temporary_path.write_text(
                json.dumps(self._audit.summary(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self._audit_path)
        self._closed = True

    def destroy_node(self):
        self.finalize()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RvizReplayNode()
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
