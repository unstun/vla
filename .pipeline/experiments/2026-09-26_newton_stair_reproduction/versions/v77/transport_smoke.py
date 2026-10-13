"""Exercise actual native upstream admission and existing cancel/hold interface."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from scan_planner_msgs.msg import P2BRoute, P2BCancel, P2BAdmission, Bspline

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(exist_ok=True)
    rclpy.init();node=rclpy.create_node('upstream_transport_smoke')
    admissions=[];splines=[];processes=[];handles=[]
    a=node.create_subscription(P2BAdmission,'/p2b/scan_admission',admissions.append,20)
    b=node.create_subscription(Bspline,'/planning/bspline',splines.append,20)
    odom_pub=node.create_publisher(Odometry,'/quad_0/body_pose',qos_profile_sensor_data)
    route_pub=node.create_publisher(P2BRoute,'/p2b/route',10)
    cancel_pub=node.create_publisher(P2BCancel,'/p2b/scan_cancel',10)
    identity=dict(run_id='v71-native-smoke',epoch=71,request_id='request',goal_id='goal',
        route_id='route',command_id='command',generation=71,map_epoch='map',map_revision=0)
    def identify(msg):
        for k,v in identity.items():setattr(msg,k,v)
        return msg
    odom=Odometry();odom.header.frame_id='world';odom.pose.pose.orientation.w=1.
    odom.pose.pose.position.z=.35
    route=identify(P2BRoute());route.path.header.frame_id='world'
    for x in (0.,.5,1.):
        pose=PoseStamped();pose.header.frame_id='world';pose.pose.orientation.w=1.
        pose.pose.position.x=x;pose.pose.position.z=.35;route.path.poses.append(pose)
    route.has_goal_pose=True;route.goal_pose=route.path.poses[-1].pose
    cancel=identify(P2BCancel());cancel.reason='native_smoke_hold'
    result={'passed':False,'kind':'actual_native_transport_not_navigation'}
    def pump(seconds,publish=None):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            odom.header.stamp=node.get_clock().now().to_msg();odom_pub.publish(odom)
            if publish:publish()
            rclpy.spin_once(node,timeout_sec=.02)
    try:
        for executable in ('scan_planner_node','closed_loop_controller'):
            log=(args.output/(executable+'.smoke.log')).open('w');handles.append(log)
            config='building_planner.yaml' if executable=='scan_planner_node' else 'controller.yaml'
            processes.append(subprocess.Popen(['ros2','run','scan_planner',executable,'--ros-args',
                '--params-file',str(HERE/config),'-p','use_sim_time:=false','-r','body_pose:=/quad_0/body_pose'],
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        pump(3.)
        route_pub.publish(route);pump(2.)
        assert any(x.consumer=='fsm' and x.status=='accepted' and x.command_id==identity['command_id'] for x in admissions), 'No actual native FSM admission'
        cancel_pub.publish(cancel);pump(2.)
        for consumer in ('fsm','controller'):
            assert any(x.consumer==consumer and x.status=='stopped' and x.hold_confirmed and not x.measured_stillness_confirmed
                and x.command_id==identity['command_id'] and x.generation==71 for x in admissions), consumer+' missing cancel hold'
        assert any(x.emergency_stop and x.command_id==identity['command_id'] and x.generation==71 for x in splines), 'No identity-bearing native emergency hold curve'
        # Late cancelled input must not be accepted; the original high-water
        # gate is tested through the real ROS callback rather than source text.
        admissions.clear();route_pub.publish(route);pump(.5)
        assert any(x.consumer=='fsm' and x.status=='rejected' and x.generation==71 for x in admissions)
        result['passed']=True
        result['checks']=['actual_fsm_route_admission','fsm_cancel_hold','controller_cancel_hold',
            'hold_does_not_claim_physical_stillness','identity_bearing_emergency_curve','cancelled_generation_route_rejected']
    except Exception as error:
        result['error']=repr(error)
    finally:
        for process in processes:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
        for log in handles:log.close()
        node.destroy_node();rclpy.shutdown()
        args.output.joinpath('native_transport_smoke.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
