#!/usr/bin/env python3
"""Receive one clock-gated PCT map in a CPU-only isolated ROS domain."""
from __future__ import annotations

import hashlib
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2


EXPECTED_PAYLOAD_SHA = "71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577"


def main() -> int:
    rclpy.init()
    node = Node("pct_sidecar_probe_driver")
    clock_pub = node.create_publisher(Clock, "/clock", QoSProfile(depth=1))
    map_qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
    received = []
    node.create_subscription(PointCloud2, "/pct_tomogram", received.append, map_qos)
    deadline = time.monotonic() + 18
    tick = 0
    try:
        while time.monotonic() < deadline and not received:
            msg = Clock()
            simulation_ns = 1_000_000_000 + max(0, tick - 14) * 10_000_000
            msg.clock.sec = simulation_ns // 1_000_000_000
            msg.clock.nanosec = simulation_ns % 1_000_000_000
            clock_pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.1)
            tick += 1
        if not received:
            print(json.dumps({"passed": False, "reason": "no terrain topic received", "clock_ticks": tick}))
            return 1
        terrain = received[0]
        stamp_ns = terrain.header.stamp.sec * 1_000_000_000 + terrain.header.stamp.nanosec
        payload_sha = hashlib.sha256(bytes(terrain.data)).hexdigest()
        result = {
            "passed": stamp_ns > 0 and terrain.header.frame_id == "world" and
                      terrain.width == 86775 and terrain.point_step == 16 and
                      payload_sha == EXPECTED_PAYLOAD_SHA,
            "stamp_ns": stamp_ns,
            "frame": terrain.header.frame_id,
            "points": terrain.width,
            "point_step": terrain.point_step,
            "is_dense": terrain.is_dense,
            "payload_sha256": payload_sha,
            "clock_ticks": tick,
        }
        print(json.dumps(result))
        return 0 if result["passed"] else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
