"""Read-only receipt timestamps for actual controller and gated commands."""
import argparse
import json
from pathlib import Path
import time
import rclpy
from geometry_msgs.msg import Twist


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args, ros_args = parser.parse_known_args()
    rclpy.init(args=ros_args)
    node = rclpy.create_node("recording_frequency_observer")
    log = (args.output / "command_frequencies.jsonl").open("w")
    def record(topic, message):
        log.write(json.dumps({"topic":topic,"wall_monotonic_s":time.monotonic(),
            "vx":message.linear.x,"vy":message.linear.y,"wz":message.angular.z})+"\n")
        log.flush()
    subscriptions = [node.create_subscription(Twist, topic,
        lambda message, topic=topic: record(topic,message), 100)
        for topic in ("/quad_0/raw_scan_cmd_vel", "/quad_0/cmd_vel")]
    try:
        rclpy.spin(node)
    finally:
        log.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__": main()
