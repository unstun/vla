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
                                load_pinned_map, load_paired_elevations, selected_ground_points,
                                load_surface_cost, surface_evidence_points, load_dense_surface_points)


class PctSimClockPublisher(Node):
    def __init__(self):
        super().__init__("pct_sim_clock_ground_publisher")
        map_path = Path(str(self.declare_parameter("map_path", str(DEFAULT_MAP)).value))
        frame = str(self.declare_parameter("frame_id", "world").value)
        coord_mode = str(self.declare_parameter("coord_mode", "identity").value)
        mode = str(self.declare_parameter("ground_mode", "navigation_selected").value)
        topics = {"navigation_selected": "/pct_tomogram", "tracking_physical": "/tracker_ground",
                  "surface_evidence": "/pct_ground_surface"}
        if mode not in topics:
            raise ValueError("unsupported ground publication mode")
        topic = str(self.declare_parameter("tomogram_topic", topics[mode]).value)
        visual_offset = float(self.declare_parameter("tomogram_visual_z_offset", 0.03).value)
        if frame != "world" or topic != topics[mode]:
            raise ValueError("sidecar frame/topic differs from its ground-mode contract")
        if mode == "tracking_physical" and (coord_mode != "identity" or visual_offset != 0.03):
            raise ValueError("physical ground must use the pinned raw Building frame and offset")
        source = load_pinned_map(map_path)
        elevation_path = str(self.declare_parameter("elevation_path", "").value)
        paired_elevations = None
        if elevation_path:
            if mode not in ("navigation_selected", "surface_evidence"):
                raise ValueError("Original precision is only supported for selected navigation terrain")
            paired_elevations = load_paired_elevations(Path(elevation_path), source)
        surface_path = str(self.declare_parameter("surface_cost_path", "").value)
        dense_path = str(self.declare_parameter("dense_surface_path", "").value)
        if mode == "surface_evidence":
            if bool(surface_path) == bool(dense_path) or paired_elevations is None or coord_mode != "identity" or visual_offset != 0.03:
                raise ValueError("Surface evidence requires exactly one paired pinned Building source")
            self._points = (load_dense_surface_points(Path(dense_path)) if dense_path else
                            surface_evidence_points(source, paired_elevations,
                                                    load_surface_cost(Path(surface_path), source)))
        else:
            if surface_path or dense_path:
                raise ValueError("Surface sources are only valid for the surface evidence topic")
            self._points = selected_ground_points(source, coord_mode, visual_offset,
                                                  cost_limit=None if mode == "tracking_physical" else 20.0,
                                                  paired_elevations=paired_elevations)
        self._point_sha = hashlib.sha256(self._points.astype("<f4").tobytes()).hexdigest()
        self._frame = frame
        self._topic = topic
        self._gate = SimClockGate()
        qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self._publisher = self.create_publisher(PointCloud2, topic, qos)
        self.create_subscription(Clock, "/clock", self._on_clock, qos_profile_sensor_data)
        self.get_logger().info(
            f"Loaded {len(self._points)} pinned {mode} ground cells; waiting for two advancing nonzero /clock samples"
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
            f"Published {self._topic} at simulation stamp {ready_stamp} ns; "
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
