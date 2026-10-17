"""Original backend core with an explicit ROS executor diagnostic seam.

Single-threaded comparison follows ros2/rclpy issues1223/1452. All original
callbacks use the default mutually-exclusive group; algorithm code is imported
unchanged. Callback traces observe scheduling and never alter message content.
"""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from p2b_backend_ros.config import load_runtime_config
from p2b_backend_ros.node import RosScanPort, build_runtime
from p2b_backend_ros.runtime import start_http_server

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=Path, required=True)
parser.add_argument("--executor", choices=("multi", "single"), default="multi")
args = parser.parse_args()
config = load_runtime_config(args.config)
log = (args.config.parent / "backend_body_callbacks.jsonl").open("w")
original = RosScanPort._on_body_pose


def observed_body_callback(self, message):
    entered = time.monotonic_ns()
    original(self, message)
    log.write(json.dumps({"entered_ns": entered, "finished_ns": time.monotonic_ns(),
        "stamp_ns": message.header.stamp.sec * 1000000000 + message.header.stamp.nanosec,
        "accepted_sequence": self._state_seq}) + "\n")
    log.flush()


RosScanPort._on_body_pose = observed_body_callback
rclpy.init()
node = rclpy.create_node("p2b_backend_ros")
runtime = build_runtime(node, config)
server = start_http_server(runtime, config["http"]["host"], config["http"]["port"])
executor = MultiThreadedExecutor(num_threads=4) if args.executor == "multi" else SingleThreadedExecutor()
executor.add_node(node)
try:
    executor.spin()
finally:
    server.shutdown()
    executor.shutdown()
    node.destroy_node()
    log.close()
    rclpy.shutdown()
