"""Reuse the frozen unmapped-box AABB as a live RViz marker on /quad_0/cloud_raw.

Runs inside the existing Foxy RViz container. Does not invent clustering or
SCAN occupancy: it transforms sensor-frame points with /quad_0/lidar_pose and
counts hits in the same 0.01 m pad AABB as unmapped_box.py.
"""

from __future__ import annotations

import argparse
import json
import struct
import time
from pathlib import Path


def rotate_xyzw(quat_xyzw, vector):
    qx, qy, qz, qw = (float(value) for value in quat_xyzw)
    vx, vy, vz = (float(value) for value in vector)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


def transform_points(points, position_xyz, quat_xyzw):
    px, py, pz = (float(value) for value in position_xyz)
    world = []
    for point in points:
        rotated = rotate_xyzw(quat_xyzw, point)
        world.append((rotated[0] + px, rotated[1] + py, rotated[2] + pz))
    return world


def unpack_xyz(payload, point_step, point_count):
    if point_step < 12 or point_count < 0 or len(payload) < point_count * point_step:
        raise ValueError("PointCloud2 payload is shorter than width times point_step")
    points = []
    for index in range(point_count):
        offset = index * point_step
        points.append(struct.unpack_from("<fff", payload, offset))
    return points


def count_in_aabb(points, min_xyz_m, max_xyz_m):
    lo = tuple(float(value) for value in min_xyz_m)
    hi = tuple(float(value) for value in max_xyz_m)
    hits = 0
    for point in points:
        if lo[0] <= point[0] <= hi[0] and lo[1] <= point[1] <= hi[1] and lo[2] <= point[2] <= hi[2]:
            hits += 1
    return hits


def load_setup(path):
    payload = json.loads(Path(path).read_text())
    aabb = payload["robot_overlap"]["box_aabb"]
    return {
        "center_xyz_m": tuple(payload["center_xyz_m"]),
        "size_xyz_m": tuple(payload["size_xyz_m"]),
        "min_xyz_m": tuple(aabb["min_xyz_m"]),
        "max_xyz_m": tuple(aabb["max_xyz_m"]),
        "prim": payload.get("prim", "/World/unmapped_box"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--setup", type=Path, required=True)
    args = parser.parse_args()

    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import PointCloud2
    from std_msgs.msg import ColorRGBA
    from visualization_msgs.msg import Marker, MarkerArray

    rclpy.init()
    node = Node("livox_aabb_hit_marker")
    stream = args.output.open("w", buffering=1)
    setup = {"value": None}
    pose = {"value": None}
    sequence = 0
    publisher = node.create_publisher(MarkerArray, "/review/unmapped_box_hits", 1)
    cloud_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                           durability=DurabilityPolicy.VOLATILE)

    def markers_for(hits, total_points):
        record = setup["value"]
        cube = Marker()
        cube.header.frame_id = "world"
        cube.ns = "unmapped_box"
        cube.id = 0
        cube.type = Marker.CUBE
        cube.action = Marker.ADD
        cube.pose.position.x = record["center_xyz_m"][0]
        cube.pose.position.y = record["center_xyz_m"][1]
        cube.pose.position.z = record["center_xyz_m"][2]
        cube.pose.orientation.w = 1.0
        cube.scale.x = record["size_xyz_m"][0]
        cube.scale.y = record["size_xyz_m"][1]
        cube.scale.z = record["size_xyz_m"][2]
        cube.color = ColorRGBA(r=0.15, g=0.95, b=0.35, a=0.35) if hits else ColorRGBA(
            r=0.95, g=0.25, b=0.15, a=0.25
        )
        label = Marker()
        label.header.frame_id = "world"
        label.ns = "unmapped_box"
        label.id = 1
        label.type = Marker.TEXT_VIEW_FACING
        label.action = Marker.ADD
        label.pose.position.x = record["center_xyz_m"][0]
        label.pose.position.y = record["center_xyz_m"][1]
        label.pose.position.z = record["center_xyz_m"][2] + record["size_xyz_m"][2] * 0.5 + 0.25
        label.pose.orientation.w = 1.0
        label.scale.z = 0.18
        label.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        label.text = "AABB hits %d / %d" % (hits, total_points)
        array = MarkerArray()
        array.markers.extend((cube, label))
        return array

    def maybe_load_setup():
        if setup["value"] is not None or not args.setup.is_file():
            return
        try:
            setup["value"] = load_setup(args.setup)
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return

    def on_pose(message):
        pose["value"] = (
            (
                message.pose.pose.position.x,
                message.pose.pose.position.y,
                message.pose.pose.position.z,
            ),
            (
                message.pose.pose.orientation.x,
                message.pose.pose.orientation.y,
                message.pose.pose.orientation.z,
                message.pose.pose.orientation.w,
            ),
        )

    def on_cloud(message):
        nonlocal sequence
        maybe_load_setup()
        if setup["value"] is None or pose["value"] is None:
            return
        points = unpack_xyz(bytes(message.data), message.point_step, message.width * message.height)
        world = transform_points(points, pose["value"][0], pose["value"][1])
        hits = count_in_aabb(world, setup["value"]["min_xyz_m"], setup["value"]["max_xyz_m"])
        sequence += 1
        stream.write(json.dumps({
            "receipt_index": sequence,
            "monotonic_ns": time.monotonic_ns(),
            "source_stamp_ns": message.header.stamp.sec * 1000000000 + message.header.stamp.nanosec,
            "frame_id": message.header.frame_id,
            "points": len(world),
            "aabb_hits": hits,
            "detected": hits > 0,
        }, sort_keys=True) + "\n")
        publisher.publish(markers_for(hits, len(world)))

    node.create_subscription(Odometry, "/quad_0/lidar_pose", on_pose, cloud_qos)
    node.create_subscription(PointCloud2, "/quad_0/cloud_raw", on_cloud, cloud_qos)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stream.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
