"""Passive SCAN occupancy receipts. Optional frozen-AABB count; no new detector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import aabb_hit_marker


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
    if setup is not None:
        record["aabb_hits"] = aabb_hit_marker.count_in_aabb(
            points, setup["min_xyz_m"], setup["max_xyz_m"]
        )
        record["detected"] = record["aabb_hits"] > 0
    return record


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
    setup = aabb_hit_marker.load_setup(args.setup) if args.setup else None

    def received(msg):
        nonlocal sequence
        sequence += 1
        stream.write(json.dumps(occupancy_record(msg, sequence, setup), sort_keys=True) + "\n")

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
