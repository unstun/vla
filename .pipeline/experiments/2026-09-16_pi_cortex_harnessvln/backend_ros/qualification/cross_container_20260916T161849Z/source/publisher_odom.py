import json
import os
import pathlib
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data

scenario = os.environ["P2B_SCENARIO"]
result = pathlib.Path("/qualification/result") / scenario
result.mkdir(parents=True, exist_ok=True)
(result / "publisher_effective_env.json").write_text(json.dumps({
    "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID"),
    "ROS_LOCALHOST_ONLY": os.environ.get("ROS_LOCALHOST_ONLY"),
    "RMW_IMPLEMENTATION": os.environ.get("RMW_IMPLEMENTATION"),
    "CYCLONEDDS_URI": os.environ.get("CYCLONEDDS_URI"),
    "FASTRTPS_DEFAULT_PROFILES_FILE": os.environ.get("FASTRTPS_DEFAULT_PROFILES_FILE"),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

summary = {"published": 0, "checks": []}
rclpy.init(args=None)
node = rclpy.create_node("p2b_cross_container_best_effort_publisher_" + scenario)
pub = node.create_publisher(Odometry, "/quad_0/body_pose", qos_profile_sensor_data)
try:
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        msg = Odometry()
        msg.header.frame_id = "world"
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.pose.pose.position.x = 0.42
        msg.pose.pose.position.y = -0.24
        msg.pose.pose.position.z = 0.35
        pub.publish(msg)
        summary["published"] += 1
        rclpy.spin_once(node, timeout_sec=0.02)
        time.sleep(0.03)
    summary["checks"].append("best_effort_odom_published")
    summary["ok"] = summary["published"] > 0
finally:
    node.destroy_node()
    rclpy.shutdown()
    (result / "publisher_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
