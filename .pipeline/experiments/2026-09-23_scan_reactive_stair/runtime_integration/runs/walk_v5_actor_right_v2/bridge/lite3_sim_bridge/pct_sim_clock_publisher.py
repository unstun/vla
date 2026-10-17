"""One-shot PCT terrain sidecar published only after a positive /clock sample.

Run in a ROS environment with the pinned Building pickle mounted. This does
not edit or launch pct_planner.planner_node and performs no robot actuation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (QoSProfile, QoSReliabilityPolicy,
                       QoSDurabilityPolicy, qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2, PointField

from pct_sim_clock_core import (DEFAULT_MAP, SimClockGate, cloud_payload,
                                load_pinned_map, selected_ground_points)


class PctSimClockPublisher(Node):
    def __init__(self):
        super().__init__("pct_sim_clock_ground_publisher")
        map_path = Path(str(self.declare_parameter("map_path", str(DEFAULT_MAP)).value))
        frame = str(self.declare_parameter("frame_id", "world").value)
        coord_mode = str(self.declare_parameter("coord_mode", "identity").value)
        topic = str(self.declare_parameter("tomogram_topic", "/pct_tomogram").value)
        visual_offset = float(self.declare_parameter("tomogram_visual_z_offset", 0.03).value)
        if frame != "world" or topic != "/pct_tomogram":
            raise ValueError("sidecar frame/topic must match SCAN world and /pct_tomogram")
        source = load_pinned_map(map_path)
        self._points = selected_ground_points(source, coord_mode, visual_offset)
        self._point_sha = hashlib.sha256(self._points.astype("<f4").tobytes()).hexdigest()
        self._frame = frame
        self._gate = SimClockGate()
        qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self._publisher = self.create_publisher(PointCloud2, topic, qos)
        self.create_subscription(Clock, "/clock", self._on_clock, qos_profile_sensor_data)
        self.get_logger().info(
            f"Loaded {len(self._points)} pinned selected ground cells; waiting for two advancing nonzero /clock samples"
        )

    def _on_clock(self, clock: Clock):
        stamp_ns = int(clock.clock.sec) * 1_000_000_000 + int(clock.clock.nanosec)
        ready_stamp = self._gate.observe(stamp_ns)
        if ready_stamp is None:
            return
        payload = cloud_payload(self._points, ready_stamp, self._frame)
        msg = PointCloud2()
        msg.header.stamp.sec = payload.stamp_ns // 1_000_000_000
        msg.header.stamp.nanosec = payload.stamp_ns % 1_000_000_000
        msg.header.frame_id = payload.frame
        msg.height = payload.height
        msg.width = payload.width
        msg.fields = [PointField(name=name, offset=offset, datatype=datatype, count=count)
                      for name, offset, datatype, count in payload.fields]
        msg.is_bigendian = False
        msg.point_step = payload.point_step
        msg.row_step = payload.row_step
        msg.data = payload.data
        # Match the pinned Humble sensor_msgs_py.create_cloud metadata. All
        # float32 records were independently checked finite before packaging.
        msg.is_dense = False
        self._publisher.publish(msg)
        self.get_logger().info(
            f"Published /pct_tomogram at simulation stamp {ready_stamp} ns; "
            f"points={payload.width} payload_sha256={self._point_sha}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PctSimClockPublisher()
        try:
            rclpy.spin(node)
        except (ExternalShutdownException, KeyboardInterrupt):
            pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
