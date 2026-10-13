"""Actual ROS transport regression: exact pose/time; no duplicate/future restamp."""
import copy
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from body_tf_bridge import BodyTfBridge


def main():
    rclpy.init();relay=BodyTfBridge();io=Node('body_tf_fixture')
    executor=SingleThreadedExecutor();executor.add_node(relay);executor.add_node(io)
    values=[];io.create_subscription(TFMessage,'/tf',lambda msg:values.extend(msg.transforms),10)
    pub=io.create_publisher(Odometry,'/quad_0/body_pose',10)
    def spin(duration):
        end=time.monotonic()+duration
        while time.monotonic()<end:executor.spin_once(timeout_sec=0.005)
    spin(0.1)
    msg=Odometry();msg.header.frame_id='world';msg.child_frame_id='base'
    msg.header.stamp.sec=123;msg.header.stamp.nanosec=456
    msg.pose.pose.position.x=1.25;msg.pose.pose.position.z=3.42
    msg.pose.pose.orientation.w=1.0
    pub.publish(msg);spin(0.1)
    assert len(values)==1 and values[0].header==msg.header
    assert values[0].transform.translation.x==1.25 and values[0].transform.translation.z==3.42
    pub.publish(msg);spin(0.05);assert len(values)==1
    wrong=copy.deepcopy(msg);wrong.header.stamp.nanosec+=1;wrong.header.frame_id='wrong'
    pub.publish(wrong);spin(0.05);assert len(values)==1
    wrong.header.frame_id='world';wrong.pose.pose.orientation.w=0.0
    pub.publish(wrong);spin(0.05);assert len(values)==1
    msg.header.stamp.nanosec+=2;pub.publish(msg);spin(0.05)
    assert len(values)==2 and values[-1].header==msg.header
    executor.shutdown();relay.destroy_node();io.destroy_node();rclpy.shutdown()
    print(json.dumps({'passed':True,'checks':5,'source_stamps_preserved':True}))


if __name__=='__main__':main()
