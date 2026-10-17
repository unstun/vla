"""Passive SCAN occupancy receipts. Optional frozen-AABB count; no new detector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import aabb_hit_marker


def axis_stats(values):
    ordered = sorted(float(value) for value in values)
    return {
        "min": ordered[0],
        "max": ordered[-1],
        "median": ordered[len(ordered) // 2],
    }


def xyz_extent(points):
    if not points:
        return None
    xs, ys, zs = zip(*((float(p[0]), float(p[1]), float(p[2])) for p in points))
    return {"x": axis_stats(xs), "y": axis_stats(ys), "z": axis_stats(zs)}


def count_in_aabb_xy(points, min_xyz_m, max_xyz_m):
    lo = tuple(float(value) for value in min_xyz_m)
    hi = tuple(float(value) for value in max_xyz_m)
    hits = 0
    for point in points:
        if lo[0] <= point[0] <= hi[0] and lo[1] <= point[1] <= hi[1]:
            hits += 1
    return hits


def count_in_aabb_z(points, min_xyz_m, max_xyz_m):
    lo_z = float(min_xyz_m[2])
    hi_z = float(max_xyz_m[2])
    hits = 0
    for point in points:
        if lo_z <= point[2] <= hi_z:
            hits += 1
    return hits


def miss_class(aabb_hits, aabb_xy_hits, aabb_z_hits, points):
    if points == 0:
        return "empty"
    if aabb_hits > 0:
        return "overlap"
    if aabb_xy_hits > 0:
        return "z-band"
    if aabb_z_hits > 0:
        return "xy-range"
    return "both"


def occupancy_record(message, sequence, setup=None):
    points = aabb_hit_marker.unpack_xyz(
        bytes(message.data), message.point_step, message.width * message.height
    )
    record = {
        "receipt_index": sequence,
        "monotonic_ns": time.monotonic_ns(),
        "source_stamp_ns": message.header.stamp.sec * 1000000000 + message.header.stamp.nanosec,
        "frame_id": message.header.frame_id,
        "points": len(points),
        "point_step": message.point_step,
        "payload_bytes": len(message.data),
    }
    extent = xyz_extent(points)
    if extent is not None:
        record["xyz_min"] = [extent["x"]["min"], extent["y"]["min"], extent["z"]["min"]]
        record["xyz_max"] = [extent["x"]["max"], extent["y"]["max"], extent["z"]["max"]]
        record["xyz_median"] = [
            extent["x"]["median"], extent["y"]["median"], extent["z"]["median"]
        ]
    if setup is not None:
        record["aabb_hits"] = aabb_hit_marker.count_in_aabb(
            points, setup["min_xyz_m"], setup["max_xyz_m"]
        )
        record["aabb_xy_hits"] = count_in_aabb_xy(
            points, setup["min_xyz_m"], setup["max_xyz_m"]
        )
        record["aabb_z_hits"] = count_in_aabb_z(
            points, setup["min_xyz_m"], setup["max_xyz_m"]
        )
        record["detected"] = record["aabb_hits"] > 0
        record["miss_class"] = miss_class(
            record["aabb_hits"], record["aabb_xy_hits"], record["aabb_z_hits"], record["points"]
        )
    return record


def load_setup_if_ready(path):
    if path is None or not Path(path).is_file():
        return None
    try:
        return aabb_hit_marker.load_setup(path)
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--setup", type=Path)
    args = parser.parse_args()

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import PointCloud2

    rclpy.init()
    node = Node("p2b_scan_occupancy_audit")
    stream = args.output.open("w", buffering=1)
    sequence = 0
    setup = {"value": None}

    def received(msg):
        nonlocal sequence
        if setup["value"] is None:
            setup["value"] = load_setup_if_ready(args.setup)
        sequence += 1
        stream.write(json.dumps(occupancy_record(msg, sequence, setup["value"]), sort_keys=True) + "\n")

    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)
    node.create_subscription(PointCloud2, "/grid_map/occupancy", received, qos)
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
