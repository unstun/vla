"""Read-only ROS health and correction recorder; no actor-truth subscription."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from scan_planner_msgs.msg import TrackedPersonSnapshot, P2BAdmission, P2BRoute, P2BStampedTwist, Bspline, P2BCancel, P2BExecutionSafety, P2BStopEvidence
from rosidl_runtime_py.convert import message_to_ordereddict


def ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class Recorder(Node):
    def __init__(self, args):
        super().__init__("reactive_stair_health")
        self.args = args
        self.stamps = {}
        self.complete = False
        self.tracks = []
        self.source = None
        self.log = (args.output.parent / "reactive_observations.jsonl").open("w")
        latched = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Clock, "/clock", self.clock, qos_profile_sensor_data)
        self.create_subscription(PointCloud2, "/pct_tomogram", lambda msg: self.cloud("pct_tomogram", msg), latched)
        self.create_subscription(PointCloud2, "/tracker_ground", lambda msg: self.cloud("tracker_ground", msg), latched)
        self.create_subscription(PointCloud2, "/quad_0/cloud", lambda msg: self.cloud("cloud", msg), qos_profile_sensor_data)
        self.create_subscription(Odometry, "/quad_0/lidar_pose", self.pose, qos_profile_sensor_data)
        self.create_subscription(TrackedPersonSnapshot, "/tracked_person_snapshot", self.track, qos_profile_sensor_data)
        for topic, message_type, name in (("/p2b/scan_admission", P2BAdmission, "scan_admission"),
                                         ("/p2b/route", P2BRoute, "pct_route"),
                                         ("/quad_0/planning/bspline", Bspline, "bspline"),
                                         ("/p2b/scan_cancel", P2BCancel, "scan_cancel"),
                                         ("/nav2_scan/stop_evidence", P2BStopEvidence, "measured_stop_proof"),
                                         ("/quad_0/planning/execution_safety", P2BExecutionSafety, "execution_safety"),
                                         ("/quad_0/raw_scan_cmd_vel", P2BStampedTwist, "raw_command"),
                                         ("/quad_0/cmd_vel", Twist, "gated_command")):
            self.create_subscription(message_type, topic, lambda msg, key=name: self.event(key, message_to_ordereddict(msg)), 50)
        self.create_timer(0.05, self.flush)

    def event(self, name, data):
        self.log.write(json.dumps({"event": name, "clock_ns": self.stamps.get("clock"),
                                   "wall_monotonic_ns": time.monotonic_ns(), "data": data}) + "\n")
        self.log.flush()

    def clock(self, msg):
        self.stamps["clock"] = ns(msg.clock)

    def cloud(self, name, msg):
        self.stamps[name] = ns(msg.header.stamp)
        self.event(name, {"stamp_ns": ns(msg.header.stamp), "frame": msg.header.frame_id,
                          "width": msg.width, "height": msg.height, "dense": msg.is_dense})

    def pose(self, msg):
        self.stamps["lidar_pose"] = ns(msg.header.stamp)
        self.event("lidar_pose", message_to_ordereddict(msg))

    def track(self, msg):
        self.stamps["tracked_person_snapshot"] = ns(msg.header.stamp)
        self.complete = msg.complete
        self.source = msg.source_id
        self.tracks = [message_to_ordereddict(t) for t in msg.tracks]
        self.event("tracks", message_to_ordereddict(msg))

    def flush(self):
        data = {"schema_version": 1, "run_id": self.args.run_id,
                "run_epoch_ns": self.args.epoch, "wall_monotonic_ns": time.monotonic_ns(),
                "stamps_ns": self.stamps, "tracked_person_count": len(self.tracks),
                "tracks_complete": self.complete, "track_source_id": self.source,
                "tracks": self.tracks}
        tmp = self.args.output.with_suffix(".tmp")
        tmp.write_text(json.dumps(data) + "\n")
        tmp.replace(self.args.output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--epoch", type=int, required=True)
    args, ros_args = parser.parse_known_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init(args=ros_args)
    node = Recorder(args)
    try:
        rclpy.spin(node)
    finally:
        node.log.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
