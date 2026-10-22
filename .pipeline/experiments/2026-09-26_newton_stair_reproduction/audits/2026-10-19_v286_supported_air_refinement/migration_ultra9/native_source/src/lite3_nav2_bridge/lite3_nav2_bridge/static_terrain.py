"""Publish all static terrain roles from one loaded, immutable package."""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2, PointField

from .terrain_bundle import TerrainBundle, ClockGate, TOPICS, FIELDS


class StaticTerrain(Node):
    def __init__(self, **kwargs):
        super().__init__('static_terrain', **kwargs)
        self.bundle = TerrainBundle(self.declare_parameter('terrain_manifest', '').value)
        self.gate = ClockGate()
        self.messages, self.publishers_by_role = {}, {}
        qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        for role, data in self.bundle.load_clouds().items():
            message = PointCloud2()
            message.header.frame_id = self.bundle.metadata['frame']
            message.height = 1
            message.width = len(data) // 16
            message.point_step, message.row_step = 16, len(data)
            message.is_bigendian = message.is_dense = False
            message.fields = [PointField(name=n, offset=o, datatype=t, count=c) for n, o, t, c in FIELDS]
            message.data = data
            self.messages[role] = message
            self.publishers_by_role[role] = self.create_publisher(PointCloud2, TOPICS[role], qos)
        if self.get_parameter('use_sim_time').value:
            self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        else:
            self.wall_timer = self.create_timer(0.1, self.on_wall_time)
        self.get_logger().info('Loaded one static terrain package: ' + str(self.bundle.path))

    def on_clock(self, clock):
        self.publish_at(int(clock.clock.sec) * 1000000000 + int(clock.clock.nanosec))

    def on_wall_time(self):
        if self.publish_at(self.get_clock().now().nanoseconds()):
            self.wall_timer.cancel()

    def publish_at(self, clock_ns):
        stamp = self.gate.observe(clock_ns)
        if stamp is None:
            return False
        for role, message in self.messages.items():
            message.header.stamp.sec, message.header.stamp.nanosec = divmod(stamp, 1000000000)
            self.publishers_by_role[role].publish(message)
        return True


def main():
    rclpy.init()
    node = None
    try:
        node = StaticTerrain()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
