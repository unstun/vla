"""Execute the frozen v196 methods, using fixed optimizer outputs, without ROS nodes."""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import threading
from types import SimpleNamespace, MethodType
import yaml
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from lite3_nav2_interfaces.srv import PlanRoute


def pose(xyz, yaw=0., frame='world'):
    p=PoseStamped();p.header.frame_id=frame
    p.pose.position.x,p.pose.position.y,p.pose.position.z=map(float,xyz)
    p.pose.orientation.z,p.pose.orientation.w=math.sin(yaw/2),math.cos(yaw/2)
    return p


def run(source):
    spec=importlib.util.spec_from_file_location('frozen_v196_mission',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    initial=[[0.,0.,.35],[4.05,3.1,.5],[4.05,4.1,.65]]
    changed=[[0.,0.,.35],[4.,3.2,.6],[4.1,4.1,.7]]
    scenarios=[]
    for yaw in (None,0.,.7):
        scenarios.append(dict(name='heading_'+str(yaw),yaw=yaw,steps=[dict(points=initial),dict(points=changed)]))
    scenarios += [dict(name='retention',yaw=None,steps=[
        dict(points=initial),dict(reason='pct_no_route'),dict(points=[[0.,0.,.35]]),
        dict(points=[[0.,0.,.35],[10.,10.,.4],[11.,11.,.5]]),
        dict(points=changed,start=[4.05,3.2,.65]),
        dict(points=changed,body=[4.05,3.2,.65]),
        dict(points=changed,body=[0.,0.,.35]),
        dict(points=[[0.,0.,.35],[float('nan'),1.,.4]]),
        dict(points=changed,goal=[8.,8.,.6]),
        dict(points=changed,frame='map'),
        dict(points=changed,new_session=True),dict(points=changed)]),
      dict(name='no_cache',yaw=None,steps=[dict(reason='pct_no_route'),dict(points=[[0.,0.,.35]])]),
      dict(name='no_heading',yaw=None,steps=[dict(points=[[4.,4.,.3],[4.,4.,.6]])]),
      dict(name='tiny_tail',yaw=None,steps=[dict(points=initial+[[4.0500001,4.1,.65]])]),
      dict(name='canonical_goal_request',yaw=None,steps=[dict(points=initial),dict(points=changed,goal=[4.05,4.1,.65])]),
      dict(name='cancel_during_solve',yaw=None,steps=[dict(points=initial),dict(points=changed,during='cancel')]),
      dict(name='replace_during_solve',yaw=None,steps=[dict(points=initial),dict(points=changed,during='replace')])]
    for scenario in scenarios:
        obj=SimpleNamespace(frame_id='world',reference_height_m=.35,_lock=threading.RLock(),
            _planner_lock=threading.Lock(),jobs={},current_owner=None,measurement_body_pose=None,_dispatch=[])
        for name in ('plan_route','submit_goal','_mission_is_current','_retain_cached_path'):
            setattr(obj,name,MethodType(getattr(module.MissionBridge,name),obj))
        obj.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=1000000000+tick[0]))
        obj.get_logger=lambda:SimpleNamespace(error=lambda _:None)
        obj._path_pub=SimpleNamespace(publish=lambda _:None)
        serial=[0];calls=[0];tick=[0];step_ref=[None]
        def begin():
            serial[0]+=1
            data=dict(request_id=str(serial[0]),goal_id=str(serial[0]),target_ground_xyz=[4.,4.,.25],
                frame='world',map_epoch='fixed',map_revision=1)
            if scenario['yaw'] is not None:data['target_yaw_rad']=scenario['yaw']
            obj.submit_goal(data)
        begin()
        def solve(*args,**kwargs):
            calls[0]+=1;s=step_ref[0]
            if s.get('during')=='cancel':obj.jobs[str(serial[0])]['cancel_requested']=True
            if s.get('during')=='replace':begin()
            if s.get('reason')=='pct_no_route':return None
            return s['points']
        obj._planner=SimpleNamespace(plan=solve,use_quintic=True,
            planner=SimpleNamespace(get_trajectory_optimizer_wnoj=lambda:SimpleNamespace(
                get_heights=lambda:[p[2] for p in step_ref[0].get('points',[])])))
        for s in scenario['steps']:
            tick[0]+=100000000;step_ref[0]=s
            if s.get('new_session'):begin()
            if 'body' in s:obj.measurement_body_pose=dict(zip(('x','y','z'),s['body']),frame_id='world')
            request=PlanRoute.Request();request.start=pose(s.get('start',[0.,0.,.35]),frame=s.get('frame','world'))
            request.goal=pose(s.get('goal',[4.,4.,.6]),scenario['yaw'] or 0.)
            response=obj.plan_route(request,PlanRoute.Response())
            job=obj.jobs[str(serial[0])]
            s['expected']=dict(accepted=response.accepted,message=response.message,calls=calls[0],
                retained_count=job['retained_count'],refresh_status=job['refresh_status'],
                path=[[p.pose.position.x,p.pose.position.y,p.pose.position.z,p.pose.orientation.x,
                       p.pose.orientation.y,p.pose.orientation.z,p.pose.orientation.w] for p in response.path.poses])
    return scenarios

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();data=run(args.source)
    args.output.write_text(yaml.safe_dump(data,sort_keys=False))
    print(json.dumps(dict(scenarios=len(data),comparisons=sum(len(s['steps']) for s in data))))
