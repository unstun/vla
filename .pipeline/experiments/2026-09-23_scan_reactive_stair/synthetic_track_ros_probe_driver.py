#!/usr/bin/env python3
"""Synthetic LiDAR/pose transport probe for the current-only tracker.

This uses an artificial moving cluster on a pinned Building floor. It is not
human recognition, an Isaac actor, SCAN collision evaluation, or robot motion.
"""
from __future__ import annotations

import json
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSProfile, QoSReliabilityPolicy,
                       QoSDurabilityPolicy, qos_profile_sensor_data)
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from scan_planner_msgs.msg import TrackedPersonSnapshot
from sensor_msgs.msg import PointCloud2, PointField


def set_stamp(message, stamp_ns):
    message.header.stamp.sec = stamp_ns // 1_000_000_000
    message.header.stamp.nanosec = stamp_ns % 1_000_000_000


def cluster_cloud(stamp_ns: int, center_x: float) -> PointCloud2:
    points = [(center_x + dx, 0.1 + dy, height)
              for dx in (-0.1, 0.0, 0.1) for dy in (-0.08, 0.08)
              for height in (0.45, 0.8, 1.2, 1.55)]
    msg = PointCloud2()
    set_stamp(msg, stamp_ns)
    msg.header.frame_id = "lidar"
    msg.height = 1
    msg.width = len(points)
    msg.fields = [PointField(name=name, offset=4 * index,
                             datatype=PointField.FLOAT32, count=1)
                  for index, name in enumerate(("x", "y", "z"))]
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = 12 * len(points)
    msg.data = b"".join(struct.pack("<fff", *point) for point in points)
    msg.is_dense = True
    return msg


def lidar_pose(stamp_ns: int) -> Odometry:
    msg = Odometry()
    set_stamp(msg, stamp_ns)
    msg.header.frame_id = "world"
    msg.child_frame_id = "lidar"
    msg.pose.pose.position.x = -1.5
    msg.pose.pose.position.y = -4.5
    msg.pose.pose.position.z = 1.56
    msg.pose.pose.orientation.w = 1.0
    return msg


def main() -> int:
    rclpy.init()
    node = Node("scan09_synthetic_track_probe")
    clock_pub = node.create_publisher(Clock, "/clock", QoSProfile(depth=1))
    pose_pub = node.create_publisher(Odometry, "/quad_0/lidar_pose", qos_profile_sensor_data)
    cloud_pub = node.create_publisher(PointCloud2, "/quad_0/cloud", qos_profile_sensor_data)
    pct_qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
    terrain = []
    snapshots = []
    node.create_subscription(PointCloud2, "/pct_tomogram", terrain.append, pct_qos)
    node.create_subscription(TrackedPersonSnapshot, "/tracked_person_snapshot",
                             snapshots.append, qos_profile_sensor_data)

    def clock_at(stamp_ns):
        msg = Clock()
        msg.clock.sec = stamp_ns // 1_000_000_000
        msg.clock.nanosec = stamp_ns % 1_000_000_000
        clock_pub.publish(msg)

    try:
        deadline = time.monotonic() + 15
        tick = 0
        while time.monotonic() < deadline and not terrain:
            clock_at(1_000_000_000 + tick * 10_000_000)
            rclpy.spin_once(node, timeout_sec=0.1)
            tick += 1
        if not terrain:
            print(json.dumps({"passed": False, "reason": "no PCT terrain received", "ticks": tick}))
            return 1
        # Let the tracker consume its own latched terrain subscription.
        for _ in range(10):
            clock_at(1_500_000_000)
            rclpy.spin_once(node, timeout_sec=0.1)
        for index in range(6):
            stamp_ns = 2_000_000_000 + index * 100_000_000
            clock_at(stamp_ns)
            rclpy.spin_once(node, timeout_sec=0.1)
            pose_pub.publish(lidar_pose(stamp_ns))
            cloud_pub.publish(cluster_cloud(stamp_ns, 0.5 + index * 0.12))
            for _ in range(4):
                rclpy.spin_once(node, timeout_sec=0.1)
        for _ in range(20):
            rclpy.spin_once(node, timeout_sec=0.1)
        complete_tracks = [s for s in snapshots if s.complete and len(s.tracks) == 1]
        centers = [round(s.tracks[0].center.x, 3) for s in complete_tracks]
        ids = [s.tracks[0].id for s in complete_tracks]
        result = {
            "passed": terrain[0].width == 86775 and bool(complete_tracks) and len(set(ids)) == 1 and
                      any(abs(x - (-0.88)) < 0.08 for x in centers) and
                      max(centers) > min(centers) + 0.20,
            "terrain_points": terrain[0].width,
            "snapshot_count": len(snapshots),
            "complete_track_count": len(complete_tracks),
            "track_ids": sorted(set(ids)),
            "current_centers_x": centers,
            "source_ids": sorted(set(s.source_id for s in snapshots)),
        }
        print(json.dumps(result))
        return 0 if result["passed"] else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
