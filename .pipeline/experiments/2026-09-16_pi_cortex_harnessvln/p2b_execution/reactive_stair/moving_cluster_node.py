"""Foxy ROS intake for sensor-derived moving-cluster track candidates.

Requires the paired bridge /quad_0/cloud and /quad_0/lidar_pose stamps plus
the static /pct_tomogram publisher. This is not validated human recognition.
"""
from __future__ import annotations

from collections import OrderedDict
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSProfile, QoSReliabilityPolicy,
                       QoSDurabilityPolicy, qos_profile_sensor_data)
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from scan_planner_msgs.msg import TrackedPerson, TrackedPersonSnapshot

from scan_reactive_tracker.core import (CloudFrame, MovingClusterTracker,
                                        PoseObservation, Snapshot)
from scan_reactive_tracker.io import decode_float32_cloud, terrain_from_pct_records


def stamp_ns(stamp) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


class MovingClusterNode(Node):
    def __init__(self):
        super().__init__("scan_reactive_moving_cluster_tracker")
        self._tracker = MovingClusterTracker()
        self._terrain = None
        self._poses = OrderedDict()
        self._pending_clouds = OrderedDict()
        self._last_processed_ns = None
        self._pub = self.create_publisher(
            TrackedPersonSnapshot, "/tracked_person_snapshot", qos_profile_sensor_data
        )
        pct_qos = QoSProfile(depth=1,
                             reliability=QoSReliabilityPolicy.RELIABLE,
                             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(PointCloud2, "/pct_tomogram", self._on_terrain, pct_qos)
        self.create_subscription(Odometry, "/quad_0/lidar_pose", self._on_pose,
                                 qos_profile_sensor_data)
        self.create_subscription(PointCloud2, "/quad_0/cloud", self._on_cloud,
                                 qos_profile_sensor_data)
        self.create_timer(0.1, self._watchdog)

    def _now_ns(self) -> int:
        return self.get_clock().now().nanoseconds

    def _fields(self, msg):
        names = [field.name for field in msg.fields]
        if len(names) != len(set(names)):
            raise ValueError("duplicate PointCloud2 fields")
        return {field.name: (field.offset, field.datatype, field.count)
                for field in msg.fields}

    def _on_terrain(self, msg: PointCloud2):
        try:
            if not msg.is_dense or msg.header.frame_id != "world":
                raise ValueError("invalid PCT frame or density")
            records = decode_float32_cloud(
                bytes(msg.data), msg.width, msg.height, msg.point_step, msg.row_step,
                msg.is_bigendian, self._fields(msg), ("x", "y", "z", "intensity")
            )
            if any(not all(math.isfinite(value) for value in record) for record in records):
                raise ValueError("non-finite PCT point")
            self._terrain = terrain_from_pct_records(
                records, bytes(msg.data), msg.header.frame_id, stamp_ns(msg.header.stamp)
            )
        except ValueError as error:
            self._terrain = None
            self.get_logger().error(f"PCT support rejected: {error}")
            self._publish_incomplete("invalid_pct_support")

    def _on_pose(self, msg: Odometry):
        key = stamp_ns(msg.header.stamp)
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        pose = PoseObservation(
            key, msg.header.frame_id, msg.child_frame_id,
            (position.x, position.y, position.z),
            (orientation.x, orientation.y, orientation.z, orientation.w),
        )
        self._poses[key] = pose
        while len(self._poses) > 8:
            self._poses.popitem(last=False)
        pending = self._pending_clouds.pop(key, None)
        if pending is not None:
            self._process_cloud(pending, pose)

    def _on_cloud(self, msg: PointCloud2):
        key = stamp_ns(msg.header.stamp)
        pose = self._poses.get(key)
        if pose is not None:
            self._process_cloud(msg, pose)
            return
        self._pending_clouds[key] = msg
        while len(self._pending_clouds) > 4:
            self._pending_clouds.popitem(last=False)
        self._publish_incomplete("waiting_for_exact_pose")

    def _process_cloud(self, msg: PointCloud2, pose: PoseObservation):
        try:
            if not msg.is_dense or msg.width == 0:
                raise ValueError("empty or non-dense LiDAR sweep")
            points = decode_float32_cloud(
                bytes(msg.data), msg.width, msg.height, msg.point_step, msg.row_step,
                msg.is_bigendian, self._fields(msg), ("x", "y", "z")
            )
            if any(not all(math.isfinite(value) for value in point) for point in points):
                raise ValueError("non-finite LiDAR point")
            result = self._tracker.process(
                CloudFrame(stamp_ns(msg.header.stamp), msg.header.frame_id, points),
                pose, self._terrain, self._now_ns()
            )
        except ValueError as error:
            self.get_logger().error(f"LiDAR sweep rejected: {error}")
            self._publish_incomplete("invalid_lidar_sweep")
            return
        self._last_processed_ns = result.stamp_ns if result.complete else None
        self._publish(result)

    def _publish(self, snapshot: Snapshot):
        msg = TrackedPersonSnapshot()
        msg.header.stamp.sec = snapshot.stamp_ns // 1_000_000_000
        msg.header.stamp.nanosec = snapshot.stamp_ns % 1_000_000_000
        msg.header.frame_id = snapshot.frame or "world"
        msg.source_id = snapshot.source_id
        msg.complete = snapshot.complete
        for track in snapshot.tracks:
            person = TrackedPerson()
            person.id = track.id
            person.observed_at.sec = track.stamp_ns // 1_000_000_000
            person.observed_at.nanosec = track.stamp_ns % 1_000_000_000
            person.center.x, person.center.y, person.center.z = track.center
            person.radius_m = float(track.radius_m)
            msg.tracks.append(person)
        self._pub.publish(msg)

    def _publish_incomplete(self, reason: str):
        self._publish(Snapshot(
            self._now_ns(), "world", MovingClusterTracker.SOURCE_ID,
            False, (), reason
        ))

    def _watchdog(self):
        now = self._now_ns()
        if self._last_processed_ns is None or now < self._last_processed_ns or \
           now - self._last_processed_ns > self._tracker.p.max_cloud_age_ns:
            self._publish_incomplete("missing_or_stale_paired_sweep")


def main(args=None):
    rclpy.init(args=args)
    node = MovingClusterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
