"""Passive stamped-cloud receipt audit; publishes no ROS data."""

import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import PointCloud2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Node('p2b_live_cloud_audit')
    stream = args.output.open('w', buffering=1)
    sequence = 0

    def received(msg):
        nonlocal sequence
        sequence += 1
        stream.write(json.dumps({
            'receipt_index': sequence,
            'monotonic_ns': time.monotonic_ns(),
            'source_stamp_ns': msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec,
            'frame_id': msg.header.frame_id,
            'points': msg.width * msg.height,
            'point_step': msg.point_step,
            'payload_bytes': len(msg.data),
        }, sort_keys=True) + '\n')

    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)
    subscription = node.create_subscription(PointCloud2, '/quad_0/cloud_raw', received, qos)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stream.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
