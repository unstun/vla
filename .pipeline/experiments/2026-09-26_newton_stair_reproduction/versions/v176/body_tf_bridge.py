"""Expose measured simulator body odometry as TF without restamping or extrapolation."""
import copy
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class BodyTfBridge(Node):
    def __init__(self):
        super().__init__('nav2_measured_body_tf')
        self.last_stamp = 0
        self.broadcaster = TransformBroadcaster(self)
        self.create_subscription(Odometry,'/quad_0/body_pose',self.receive,qos_profile_sensor_data)

    def receive(self,msg):
        ns=msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
        p,q=msg.pose.pose.position,msg.pose.pose.orientation
        if (msg.header.frame_id!='world' or msg.child_frame_id!='base' or ns<=self.last_stamp
                or not all(math.isfinite(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w))
                or abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1.0)>1e-6):
            return
        transform=TransformStamped()
        transform.header=copy.deepcopy(msg.header)
        transform.child_frame_id=msg.child_frame_id
        transform.transform.translation.x=p.x
        transform.transform.translation.y=p.y
        transform.transform.translation.z=p.z
        transform.transform.rotation=copy.deepcopy(q)
        self.last_stamp=ns
        self.broadcaster.sendTransform(transform)


def main():
    rclpy.init();node=BodyTfBridge()
    try:rclpy.spin(node)
    finally:node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
