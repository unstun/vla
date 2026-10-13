"""Packaged Nav2 launch with native PCT/SCAN and recorded sensor inputs.

No navigation goal, synthetic safety verdict, actuator or physical simulator is
started. Original scan/pose times drive /clock; map projection must preserve them.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped
from lifecycle_msgs.srv import GetState, ChangeState
from nav_msgs.msg import Odometry, OccupancyGrid
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2, PointField
from tf2_msgs.msg import TFMessage
from scan_planner_msgs.msg import P2BStampedTwist
from p2b_backend_ros.config import DEFAULT_CONFIG


def stamp(ns):
    msg=Time(); msg.sec,msg.nanosec=divmod(int(ns),1000000000); return msg


def pose(path,ns):
    data=[float(x) for x in path.read_text().split()]
    msg=Odometry();msg.header.frame_id='world';msg.header.stamp=stamp(ns);msg.child_frame_id='base_link'
    p,q=msg.pose.pose.position,msg.pose.pose.orientation
    p.x,p.y,p.z,q.x,q.y,q.z,q.w=data[:7]
    return msg


def cloud(path,ns,ground=False):
    msg=PointCloud2();msg.header.frame_id='world' if ground else 'lidar';msg.header.stamp=stamp(ns)
    msg.point_step=16 if ground else 12;msg.data=path.read_bytes()
    msg.width=len(msg.data)//msg.point_step;msg.height=1;msg.row_step=len(msg.data);msg.is_dense=True
    for i,name in enumerate(['x','y','z','intensity'] if ground else ['x','y','z']):
        msg.fields.append(PointField(name=name,offset=4*i,datatype=7,count=1))
    return msg


class Replay(Node):
    def __init__(self,inputs):
        super().__init__('nav2_recorded_launch_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
        self.inputs=inputs;self.slices=[];self.commands=[];self.sent=[]
        self.rows=[line.split() for line in (inputs/'scans.txt').read_text().splitlines()]
        self.clock=self.create_publisher(Clock,'/clock',10)
        self.tf=self.create_publisher(TFMessage,'/tf',10)
        self.body=self.create_publisher(Odometry,'/quad_0/body_pose',10)
        self.odom=self.create_publisher(Odometry,'/odom',10)
        self.sensor=self.create_publisher(Odometry,'/quad_0/lidar_pose',10)
        self.cloud=self.create_publisher(PointCloud2,'/quad_0/cloud',10)
        qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.support=[]
        for name,topic in [('navigation.f32','/pct_tomogram'),('surface.f32','/pct_ground_surface'),('physical_floor.f32','/pct_physical_floor')]:
            pub=self.create_publisher(PointCloud2,topic,qos);pub.publish(cloud(inputs/name,1000000000,True));self.support.append(pub)
        self.create_subscription(OccupancyGrid,'/nav2_scan/terrain_slice',self.slices.append,10)
        self.create_subscription(P2BStampedTwist,'/quad_0/raw_scan_cmd_vel',self.commands.append,20)
        self.ns=int(self.rows[0][1]);self.body_pose=pose(inputs/self.rows[0][2],self.ns)
        self.create_timer(0.02,self.frames,clock=rclpy.clock.Clock(clock_type=rclpy.clock.ClockType.STEADY_TIME))

    def frames(self):
        self.clock.publish(Clock(clock=stamp(self.ns)))
        transform=TransformStamped();transform.header=self.body_pose.header;transform.child_frame_id='base_link'
        p=self.body_pose.pose.pose.position
        transform.transform.translation.x=p.x;transform.transform.translation.y=p.y;transform.transform.translation.z=p.z
        transform.transform.rotation=self.body_pose.pose.pose.orientation
        self.tf.publish(TFMessage(transforms=[transform]))

    def wait(self,predicate,timeout=10):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=0.01)
            if predicate():return
        raise TimeoutError('Native launch wait')

    def pause(self,seconds):
        end=time.monotonic()+seconds;self.wait(lambda:time.monotonic()>=end,seconds+1)

    def active(self,name):
        client=self.create_client(GetState,'/'+name+'/get_state')
        self.wait(client.service_is_ready,20)
        for _ in range(100):
            f=client.call_async(GetState.Request());self.wait(f.done)
            if f.result().current_state.id==3:
                self.destroy_client(client);return
            self.pause(0.1)
        raise TimeoutError(name+' inactive')

    def sample(self,row):
        self.ns=int(row[1]);self.sent.append(self.ns)
        self.body_pose=pose(self.inputs/row[2],self.ns)
        self.frames();self.body.publish(self.body_pose);self.odom.publish(self.body_pose)
        self.sensor.publish(pose(self.inputs/row[3],self.ns))
        self.cloud.publish(cloud(self.inputs/row[4],self.ns))


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--native-config',required=True)
    p.add_argument('--pct-map',required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    config=copy.deepcopy(DEFAULT_CONFIG);config.update(run_id='native-launch',run_epoch_ns=1)
    config['map'].update(epoch='building',revision=1,pct_layer=None,nominal_body_height_m=0.30)
    config['pct_worker']['port']=47791
    config['gate'].update(odom_time_base='simulation',odom_wall_backstop_s=2.0)
    config['applied_evidence']['current_command_path']='/dev/shm/nav2-native-unused-applied.json'
    cfg=args.output/'backend.json';cfg.write_text(json.dumps(config,indent=2))
    rclpy.init();node=Replay(args.inputs)
    log=(args.output/'launch.log').open('w')
    command=['ros2','launch','lite3_nav2_bridge','navigation.launch.py',
        'native_planner_config:='+args.native_config,'backend_config:='+str(cfg),
        'generated_params:='+str(args.output/'nav2.yaml'),'pct_map:='+args.pct_map,'use_sim_time:=true']
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    report={'scope':'actual packaged PCT/SCAN/Nav2 lifecycle and recorded map projection; zero goals','passed':False}
    try:
        for name in ('controller_server','planner_server','nav2_internal/bt_navigator'):node.active(name)
        node.wait(lambda:node.cloud.get_subscription_count()>0 and node.sensor.get_subscription_count()>0)
        for row in node.rows[:40]:node.sample(row);node.pause(0.1)
        node.pause(0.2)
        assert len(node.slices)>=5,'Native SCAN did not publish completed map slices'
        projected=[m.header.stamp.sec*1000000000+m.header.stamp.nanosec for m in node.slices]
        assert all(min(abs(value-original) for original in node.sent)<=1000 for value in projected)
        assert all(m.info.width>0 and len(m.data)==m.info.width*m.info.height for m in node.slices)
        assert not node.commands,'Native plugin emitted a command without a mission'
        report.update(passed=True,lifecycle_active=True,original_scans=40,native_map_slices=len(node.slices),
                      preserved_scan_stamps=True,raw_commands=0,robot_actuation=False)
    except Exception as exc:
        report['error']=repr(exc);raise
    finally:
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        log.close();node.destroy_node();rclpy.shutdown()
    print(json.dumps(report))


if __name__=='__main__':main()
