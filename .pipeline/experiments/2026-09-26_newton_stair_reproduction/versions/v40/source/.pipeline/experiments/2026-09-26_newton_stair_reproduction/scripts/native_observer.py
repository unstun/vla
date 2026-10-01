"""Original sensor/curve recorder with an independent body-pose observation."""
import argparse
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from lite3_sim_bridge.reactive_health import Recorder

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--run-id", required=True)
parser.add_argument("--epoch", type=int, required=True)
args, ros_args = parser.parse_known_args()
rclpy.init(args=ros_args)
node = Recorder(args)
node.create_subscription(Odometry, "/quad_0/body_pose",
    lambda message: node.event("body_pose_observer", message_to_ordereddict(message)), qos_profile_sensor_data)
try:
    rclpy.spin(node)
finally:
    node.log.close()
    node.destroy_node()
    rclpy.shutdown()
