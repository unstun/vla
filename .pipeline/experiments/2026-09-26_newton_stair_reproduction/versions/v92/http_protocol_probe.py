"""Real Nav2/PCT service/plugin/gateway chain with explicitly synthetic algorithms.

The RPC peer returns a straight fixture route; splines, map and safety verdicts
are test inputs. Controller hold is real, and measured-stop evidence comes from
the kinematic plant. This does not reproduce PCT or native SCAN navigation.
"""
import argparse
import concurrent.futures
import urllib.request
from types import SimpleNamespace
import copy
import json
import math
import os
from pathlib import Path
import signal
import socketserver
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Point, PoseStamped, TransformStamped, Twist
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid, Odometry
from tf2_msgs.msg import TFMessage
from scan_planner_msgs.msg import Bspline, P2BRoute, P2BAdmission, P2BExecutionSafety, P2BStampedTwist
from backend_adapter.contracts import NativeRoute
from backend_adapter.pct_ipc import make_route_id
from backend_adapter.pct_worker import PctWorkerServer, NativePctPlanner, NativePctConfig
from p2b_backend_ros.config import DEFAULT_CONFIG
from lite3_nav2_bridge.profile import write_profile


def identity(a, b):
    for key in ('run_id','epoch','request_id','goal_id','route_id','command_id','generation','map_epoch','map_revision'):
        setattr(b, key, getattr(a, key))


class FixturePct:
    def __init__(self, native=None): self.delay = 0.0; self.calls = []; self.native = native
    def plan(self, request):
        self.calls.append(request.to_wire())
        time.sleep(self.delay)
        if self.native is not None: return self.native.plan(request)
        start, goal = request.start_xyz_m, request.target_xyz_m
        points = tuple((start[0]+(goal[0]-start[0])*i/10, start[1]+(goal[1]-start[1])*i/10,
                        start[2]+(goal[2]-start[2])*i/10+0.42) for i in range(11))
        return NativeRoute(make_route_id(request, points),request.goal_id,request.frame_id,
                           request.map_epoch,request.map_revision,points)


class Plant(Node):
    def __init__(self, out):
        super().__init__('nav2_full_protocol_fixture')
        self.out = out
        # Linux-local evidence transport, as on Jetson. The Mac bind mount is
        # artifact storage, not the real-time applied-command channel.
        self.applied_path = Path('/dev/shm') / ('nav2-' + out.name + '-applied.json')
        self.x = 0.0
        self.command = Twist()
        self.command_at = 0.0
        self.command_ns = time.monotonic_ns()
        self.last = time.monotonic()
        self.start = self.last
        self.seq = self.curve_id = 0
        self.active = None
        self.last_curve = 0.0
        self.routes = []
        self.raw = []
        self.proofs = []
        self.tf = self.create_publisher(TFMessage,'/tf',10)
        self.odom = self.create_publisher(Odometry,'/odom',10)
        self.body = self.create_publisher(Odometry,'/quad_0/body_pose',10)
        self.terrain = self.create_publisher(OccupancyGrid,'/nav2_scan/terrain_slice',1)
        self.spline = self.create_publisher(Bspline,'/quad_0/planning/bspline',10)
        self.safety = self.create_publisher(P2BExecutionSafety,'/quad_0/planning/execution_safety',10)
        self.admission = self.create_publisher(P2BAdmission,'/p2b/scan_admission',10)
        self.create_subscription(P2BRoute,'/p2b/route',self.route,10)
        self.create_subscription(Twist,'/quad_0/cmd_vel',self.receive_command,20)
        self.create_subscription(P2BStampedTwist,'/quad_0/raw_scan_cmd_vel',self.raw.append,20)
        self.action = ActionClient(self,NavigateToPose,'/navigate_to_pose')
        self.timer = self.create_timer(0.02,self.tick)

    def receive_command(self,msg):
        self.command = msg; self.command_at = time.monotonic(); self.command_ns = time.monotonic_ns()

    def pose(self,x):
        msg=PoseStamped(); msg.header.frame_id='world'; msg.header.stamp=self.get_clock().now().to_msg()
        msg.pose.position.x=float(x); msg.pose.position.z=0.42; msg.pose.orientation.w=1.0
        return msg

    def route(self,msg):
        self.active=msg; self.routes.append(msg); self.last_curve=0
        accepted=P2BAdmission(); identity(msg,accepted)
        accepted.consumer='fsm'; accepted.status='accepted'; accepted.message='synthetic_native_planner_fixture'
        self.admission.publish(accepted)

    def tick(self):
        now=time.monotonic(); dt=min(now-self.last,0.1); self.last=now; self.seq+=1
        command=self.command if now-self.command_at<0.3 else Twist()
        self.x+=command.linear.x*dt
        pose=self.pose(self.x)
        transform=TransformStamped(); transform.header=pose.header; transform.child_frame_id='base_link'
        transform.transform.translation.x=self.x; transform.transform.translation.z=0.42
        transform.transform.rotation.w=1.0
        self.tf.publish(TFMessage(transforms=[transform]))
        odom=Odometry(); odom.header=pose.header; odom.child_frame_id='base_link'
        odom.pose.pose=pose.pose; odom.twist.twist=command
        self.odom.publish(odom); self.body.publish(odom)
        grid=OccupancyGrid(); grid.header=pose.header; grid.info.resolution=0.1
        grid.info.width=grid.info.height=60
        grid.info.origin.position.x=self.x-3; grid.info.origin.position.y=-3.0
        grid.info.origin.position.z=0.42; grid.info.origin.orientation.w=1.0
        grid.data=[0]*3600; self.terrain.publish(grid)
        if self.active is not None:
            if now-self.last_curve>0.5:
                self.curve_id+=1; self.last_curve=now
                curve=Bspline(); identity(self.active,curve); curve.order=3; curve.traj_id=self.curve_id
                curve.start_time=pose.header.stamp
                curve.pos_pts=[Point(x=self.x+i*0.3,y=0.0,z=0.42) for i in range(6)]
                curve.knots=[float(i) for i in range(-3,7)]; self.spline.publish(curve)
            safety=P2BExecutionSafety(); identity(self.active,safety.binding)
            safety.binding.consumer='native_safety'; safety.binding.traj_id=self.curve_id
            safety.stamp=pose.header.stamp; safety.observation_stamp_s=self.get_clock().now().nanoseconds/1e9
            safety.clear=True; safety.local_map_revision=self.seq; self.safety.publish(safety)
        snapshot={'schema_version':1,'run_id':'nav2-protocol','run_epoch_ns':1,
          'sim_step':self.seq,'sim_time_s':now-self.start,'wall_monotonic_ns':time.monotonic_ns(),
          'command_source_timestamp_ns':self.command_ns,'freshness':{'max_reader_age_s':0.2},
          'applied_command':{'vx':command.linear.x,'vy':command.linear.y,'wz':command.angular.z},
          'admitted_command':{'vx':command.linear.x,'vy':command.linear.y,'wz':command.angular.z},
          'raw_command':{'vx':command.linear.x,'vy':command.linear.y,'wz':command.angular.z},
          'command_sequence':self.seq,'command_stale':False,'command_reason':'active',
          'measured':{'horizontal_speed_mps':abs(command.linear.x),'yaw_rate_radps':command.angular.z,
            'base_xyz':[self.x,0.0,0.42],'base_quat_wxyz':[1.0,0.0,0.0,0.0],'command_obs_error':0.0},
          'state_epoch':{'state_sequence':self.seq,'telemetry_sequence':self.seq}}
        tmp=self.applied_path.with_suffix('.tmp'); tmp.write_text(json.dumps(snapshot)); tmp.replace(self.applied_path)

    def wait(self,predicate,timeout=10):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(self,timeout_sec=0.005)
            if predicate(): return
        raise TimeoutError('Full protocol fixture wait')

    def pause(self,seconds):
        end=time.monotonic()+seconds; self.wait(lambda:time.monotonic()>=end,seconds+1)

    def transition(self,name,state):
        client=self.create_client(ChangeState,'/'+name+'/change_state')
        self.wait(client.service_is_ready,15)
        req=ChangeState.Request(); req.transition.id=state
        future=client.call_async(req); self.wait(future.done,20)
        assert future.result().success,(name,state)
        self.destroy_client(client)

    def goal(self,x):
        rid='legacy-goal-'+str(len(self.routes)+1)+'-'+str(time.monotonic_ns())
        payload={'request_id':rid,'goal_id':'legacy-target','target_ground_xyz':[float(x),0.0,0.0],
                 'frame':'world','map_epoch':'flat','map_revision':1}
        response=http('/goal',payload)
        assert response['ok']
        return HttpGoal(rid)


def http(path,payload=None):
    request=urllib.request.Request('http://127.0.0.1:8765'+path,
        data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=3) as response:return json.load(response)


class HttpGoal:
    def __init__(self,rid):self.rid=rid
    def get_result_async(self):
        future=concurrent.futures.Future()
        def poll():
            try:
                end=time.monotonic()+30
                while time.monotonic()<end:
                    state=http('/state');job=state['jobs'][self.rid]
                    code={'arrived':4,'cancelled':5,'failed':6,'rejected':6}.get(job['status'])
                    if code is not None:
                        future.set_result(SimpleNamespace(status=code));return
                    time.sleep(0.03)
                raise TimeoutError('HTTP terminal result')
            except Exception as exc:future.set_exception(exc)
        threading.Thread(target=poll,daemon=True).start();return future
    def cancel_goal_async(self):
        future=concurrent.futures.Future()
        try:future.set_result(http('/cancel',{'request_id':'cancel-'+self.rid,'target_request_id':self.rid}))
        except Exception as exc:future.set_exception(exc)
        return future


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native-config',required=True)
    parser.add_argument('--native-pct-map',type=Path)
    args=parser.parse_args()
    out=args.output; out.mkdir(parents=True,exist_ok=False)
    config=copy.deepcopy(DEFAULT_CONFIG)
    config.update(run_id='nav2-protocol',run_epoch_ns=1)
    config['map'].update(epoch='flat',revision=1,nominal_body_height_m=0.42,pct_layer=None)
    native=None
    if args.native_pct_map:
        import pct_planner
        native=NativePctPlanner(NativePctConfig(Path(pct_planner.__file__).resolve().parents[1],
            str(out),tomogram_path=str(args.native_pct_map)),0.42)
    fixture=FixturePct(native); server=PctWorkerServer(('127.0.0.1',0),fixture)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    config['pct_worker']['port']=server.server_address[1]
    config['applied_evidence']['current_command_path']=str(Path('/dev/shm')/('nav2-'+out.name+'-applied.json'))
    config['service']['command_timeout_s']=20.0
    (out/'backend.json').write_text(json.dumps(config,indent=2))
    params=write_profile(out/'nav2.yaml',args.native_config,False,external_planner=True)
    processes=[]; logs=[]
    rclpy.init(); plant=Plant(out)
    report={'scope':'real Nav2 stack; synthetic PCT/spline/map/safety; kinematic applied evidence','passed':False}
    if native is not None:
        report['scope']='real Nav2 stack and ARM64/Foxy native PCT; synthetic SCAN spline/map/safety; kinematic applied evidence'
    try:
        commands=[['ros2','run','lite3_nav2_bridge','mission_gateway','--ros-args','-p','config_path:='+str(out/'backend.json'),'-p','legacy_http:=true']]
        for pkg,exe in [('nav2_controller','controller_server'),('nav2_planner','planner_server'),('nav2_bt_navigator','bt_navigator')]:
            command=['ros2','run',pkg,exe,'--ros-args','-r','__node:='+exe,'--params-file',params]
            if exe=='bt_navigator':command+=['-r','__ns:=/nav2_internal']
            commands.append(command)
        for i,command in enumerate(commands):
            log=(out/f'node{i}.log').open('w'); logs.append(log)
            processes.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        for name in ('controller_server','planner_server','nav2_internal/bt_navigator'):
            plant.transition(name,1); plant.transition(name,3)
        plant.wait(plant.action.server_is_ready)
        plant.pause(0.3)
        from rclpy.action import get_action_server_names_and_types_by_node
        report['action_servers'] = {ns + '/' + name: get_action_server_names_and_types_by_node(plant,name,ns)
            for name,ns in plant.get_node_names_and_namespaces()}
        handle=plant.goal(2.0); future=handle.get_result_async(); plant.wait(future.done,25)
        report['requested_goal_xyz']=[2.0,0.0,0.42]
        report['goal_status']=future.result().status; report['goal_error_m']=abs(plant.x-2.0)
        assert report['goal_status']==4 and report['goal_error_m']<=0.25,report
        assert plant.routes[-1].goal_pose.position.z==0.42
        report['original_goal_height_preserved']=True
        handle=plant.goal(3.0); before=plant.x
        plant.wait(lambda:plant.x>before+0.15,10)
        cancel_at=time.monotonic(); cancel=handle.cancel_goal_async(); plant.wait(cancel.done)
        future=handle.get_result_async(); plant.wait(future.done,10)
        report['cancel_status']=future.result().status
        report['cancel_wait_s']=time.monotonic()-cancel_at
        x=plant.x; plant.pause(0.4)
        report['post_cancel_motion_m']=abs(plant.x-x)
        assert report['cancel_status']==5 and report['cancel_wait_s']>=1.0
        assert report['post_cancel_motion_m']<1e-5
        fixture.delay=1.0; routes=len(plant.routes); calls=len(fixture.calls)
        handle=plant.goal(3.0); plant.wait(lambda:len(fixture.calls)>calls)
        cancel=handle.cancel_goal_async(); plant.wait(cancel.done)
        future=handle.get_result_async(); plant.wait(future.done,10); plant.pause(1.1)
        report['cancel_during_planning_status']=future.result().status
        report['late_route_dispatches']=len(plant.routes)-routes
        assert future.result().status==5 and len(plant.routes)==routes
        fixture.delay=0.0
        yaw_request='legacy-goal-yaw-contract'
        before=len(plant.routes)
        http('/goal',{'request_id':yaw_request,'goal_id':'legacy-target',
            'target_ground_xyz':[3.0,0.0,0.0],'target_yaw_rad':0.7,
            'frame':'world','map_epoch':'flat','map_revision':1})
        plant.wait(lambda:len(plant.routes)>before)
        q=plant.routes[-1].goal_pose.orientation
        assert abs(q.z-math.sin(0.35))<1e-12 and abs(q.w-math.cos(0.35))<1e-12
        handle=HttpGoal(yaw_request);handle.cancel_goal_async()
        future=handle.get_result_async();plant.wait(future.done,10)
        assert future.result().status==5
        report['explicit_heading_preserved']=True
        try:
            http('/goal',{'request_id':'legacy-invalid-map','goal_id':'legacy-target',
                'target_ground_xyz':[3.0,0.0,0.0],'frame':'world','map_epoch':'wrong','map_revision':1})
            raise AssertionError('Wrong map accepted')
        except urllib.error.HTTPError as exc:
            assert exc.code==400
        report['wrong_map_rejected']=True
        report['pct_queries']=fixture.calls
        report['tagged_commands']=len(plant.raw)
        report['legacy_http']=True
        assert all(route.request_id.startswith('legacy-goal-') and route.goal_id=='legacy-target' for route in plant.routes)
        report['passed']=True
    except Exception as exc:
        report['error']=repr(exc)
        raise
    finally:
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        for p in processes:
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        for p in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        for log in logs:log.close()
        if plant.applied_path.exists():
            (out/'last_applied.json').write_bytes(plant.applied_path.read_bytes())
            plant.applied_path.unlink()
        plant.action.destroy();plant.destroy_node();rclpy.shutdown()
        server.shutdown();server.server_close();thread.join()
    print(json.dumps(report))


if __name__=='__main__':main()
