"""Publish pinned physical-floor presence on a distinct static input role."""
from pathlib import Path
import hashlib,json,sys,os
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile,QoSReliabilityPolicy,QoSDurabilityPolicy,qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2,PointField
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'runtime_sources/bridge/lite3_sim_bridge'))
from pct_sim_clock_core import SimClockGate,cloud_payload
class PhysicalFloorPublisher(Node):
    def __init__(self):
        super().__init__('pct_physical_floor_publisher')
        info=json.loads((HERE/'physical_floor_input.json').read_text())
        assert info['role']=='physical_floor_presence_only' and not info['traversal_authority'] and not info['terrain_return_classification_authority']
        data=Path(os.environ['V169_PHYSICAL_FLOOR']).read_bytes();assert hashlib.sha256(data).hexdigest()==info['files']['physical_floor.f32']['sha256']
        self.points=np.frombuffer(data,dtype='<f4').reshape(-1,4)
        assert len(self.points)==info['files']['physical_floor.f32']['points'] and np.isfinite(self.points).all()
        self.gate=SimClockGate();qos=QoSProfile(depth=1,reliability=QoSReliabilityPolicy.RELIABLE,durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher=self.create_publisher(PointCloud2,'/pct_physical_floor',qos)
        self.create_subscription(Clock,'/clock',self.on_clock,qos_profile_sensor_data)
        self.get_logger().info(f'Pinned physical-floor presence ready: {len(self.points)} records, payload_sha256={info["files"]["physical_floor.f32"]["sha256"]}')
    def on_clock(self,clock):
        ns=self.gate.observe(int(clock.clock.sec)*10**9+int(clock.clock.nanosec))
        if ns is None:return
        payload=cloud_payload(self.points,ns,'world');msg=PointCloud2()
        msg.header.frame_id=payload.frame;msg.header.stamp.sec=ns//10**9;msg.header.stamp.nanosec=ns%10**9
        msg.height=payload.height;msg.width=payload.width;msg.point_step=payload.point_step;msg.row_step=payload.row_step;msg.is_bigendian=False;msg.is_dense=False
        msg.fields=[PointField(name=name,offset=offset,datatype=kind,count=count) for name,offset,kind,count in payload.fields];msg.data=payload.data
        self.publisher.publish(msg);self.get_logger().info(f'Published physical-floor presence at simulation stamp {ns} ns')
def main():
    rclpy.init();node=None
    try:
        node=PhysicalFloorPublisher()
        try:rclpy.spin(node)
        except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=='__main__':main()
