"""Exercise the actual surface sidecar through ROS publication and clock gating."""
from pathlib import Path
import hashlib,json,sys,time
B=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(B/'runtime_sources/bridge/lite3_sim_bridge'))
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,QoSReliabilityPolicy,QoSDurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2
from pct_sim_clock_publisher import PctSimClockPublisher
rclpy.init(args=['--ros-args','-p','use_sim_time:=true','-p','ground_mode:=surface_evidence','-p','map_path:='+str(B/'inputs/new_building.pickle'),'-p','elevation_path:='+str(B/'inputs/new_building_original_precision.npz'),'-p','dense_surface_path:='+str(B/'inputs/new_building_dense_surface.npy')])
publisher=PctSimClockPublisher();observer=Node('surface_publisher_test');received=[]
qos=QoSProfile(depth=1,reliability=QoSReliabilityPolicy.RELIABLE,durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
observer.create_subscription(PointCloud2,'/pct_ground_surface',received.append,qos)
clock=observer.create_publisher(Clock,'/clock',10)
def spin(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  rclpy.spin_once(publisher,timeout_sec=.01);rclpy.spin_once(observer,timeout_sec=.01)
spin(.3)
for sec,nsec in [(10,0),(10,100000000)]:
 msg=Clock();msg.clock.sec=sec;msg.clock.nanosec=nsec;clock.publish(msg);spin(.3)
spin(.3);assert len(received)==1,len(received)
m=received[0];actual=hashlib.sha256(bytes(m.data)).hexdigest();assert actual=='b68527dd9d2ea8a4647c64aaf59b884da16364e41b146943c03f2c6da68cfa56'
assert m.width==126659 and m.height==1 and m.point_step==16 and m.row_step==m.width*16 and not m.is_bigendian
print(json.dumps({'surface_topic':'/pct_ground_surface','points':m.width,'payload_sha256':actual,'two_clock_gate':True}))
publisher.destroy_node();observer.destroy_node();rclpy.shutdown()
