"""Measure applied commands and pauses from closed recordings; zero new physics."""
from pathlib import Path
import hashlib
import csv
import json
import math
import sys
import yaml

HERE=Path(__file__).resolve().parent
VERSION=HERE.parents[1]/'versions/v289'
sys.path.insert(0,str(VERSION.parent/'v196'))
from analyze_remote import Capture


def audit(case):
    raw=Path('/home/sun/vla_exec/physical_runs_v289')/f'v289_{case}_attempt01/runs/v289_{case}_attempt01'
    capture=Capture(raw)
    out=HERE/'physical'/case/'results'
    window=json.loads((out/'window_audit.json').read_text())
    lo,hi=window['windows']['navigation_since_goal_request']['measured']['window_s']
    scenario=capture.json('inputs/stair_scenario.json')
    goal=scenario['goal_ground_xyz_m']
    config=yaml.safe_load(capture.read('nav2_params.yaml'))['controller_server']['ros__parameters']['SCAN']
    xy=float(config['goal_xy_tolerance']);z=float(config['goal_z_tolerance'])
    body_offset=float(capture.json('backend_config.json')['map']['nominal_body_height_m'])
    rows=[r for r in capture.rows('telemetry.jsonl') if lo<=r['physics_time_s']<hi]
    episodes=[];active=None;settling=[]
    for index,row in enumerate(rows):
        time=row['physics_time_s'];command=row['effective_command'];body=row['body_sensor']
        terminal=math.dist(body['position'][:2],goal[:2])<=xy and abs(body['position'][2]-goal[2]-body_offset)<=z
        pure_yaw=not terminal and math.hypot(*command[:2])<=.01 and abs(command[2])>.1
        if pure_yaw:
            if active is None:active=dict(start_s=time,end_s=time,samples=0,max_abs_yaw=0.)
            active.update(end_s=time,samples=active['samples']+1,max_abs_yaw=max(active['max_abs_yaw'],abs(command[2])))
        if active is not None and (not pure_yaw or index==len(rows)-1):
            episodes.append(active);active=None
        if row.get('stance_mode')=='STAND_SETTLING':
            settling.append(dict(time_s=time,speed_m_s=math.hypot(*body['linear_world'][:2]),terminal_capture=terminal))
    for interval in episodes:interval['duration_s']=interval['end_s']-interval['start_s']
    motion=next((r['physics_time_s'] for r in rows if math.hypot(*r['effective_command'][:2])>.05),None)
    pauses=window['windows']['navigation_since_goal_request']['measured']['intervals']
    after_motion=[dict(start_s=max(r['start_s'],motion),end_s=r['end_s'],duration_s=r['end_s']-max(r['start_s'],motion))
        for r in pauses if motion is not None and r['end_s']>motion]

    references=[];original=None
    for line in capture.read('artifacts/reactive_observations.jsonl').splitlines():
        event=json.loads(line)
        if event.get('event')!='pct_route' or not lo<=event['clock_ns']*1e-9<hi:continue
        data=event['data'];poses=data.get('poses',[])
        if not poses:continue
        geometry=[tuple([pose['pose']['position'][k] for k in ('x','y','z')]+[pose['pose']['orientation'][k] for k in ('x','y','z','w')]) for pose in poses]
        if original is None:original=geometry
        suffix=any(geometry==original[i:] for i in range(len(original)) if original[i]==geometry[0])
        stamp=data['header']['stamp'];epoch=stamp['sec']*1000000000+stamp['nanosec']
        references.append(dict(publication_s=event['clock_ns']*1e-9,epoch_ns=epoch,poses=len(geometry),
            geometry_sha256=hashlib.sha256(json.dumps(geometry,separators=(',',':')).encode()).hexdigest(),
            original_geometry_or_suffix=suffix))

    reference_csv=out/'recorded_global_reference.csv'
    if original is not None:
        with reference_csv.open('w') as output:
            writer=csv.writer(output);writer.writerow(['x','y','z','qx','qy','qz','qw']);writer.writerows(original)

    log=capture.read('nav2.log')
    report=dict(case_id=case,physics_steps=0,window_s=[lo,hi],telemetry_samples=len(rows),
        terminal_capture_xy_m=xy,terminal_capture_z_m=z,body_ground_offset_m=body_offset,
        pure_yaw_definition='applied XY norm <=0.01 m/s, |yaw| >0.1 rad/s, outside existing terminal capture region',
        nonterminal_pure_yaw_intervals=episodes,
        maximum_nonterminal_pure_yaw_s=max((r['duration_s'] for r in episodes),default=0.),
        nonterminal_pure_yaw_samples=sum(r['samples'] for r in episodes),
        global_reference_csv_sha256=hashlib.sha256(reference_csv.read_bytes()).hexdigest() if original is not None else None,
        global_route_publications=references,
        global_route_epoch_count=len({r['epoch_ns'] for r in references}),
        global_reference_geometry_preserved=bool(references) and all(r['original_geometry_or_suffix'] for r in references),
        first_translation_command_s=motion,
        maximum_low_speed_pause_after_first_translation_s=max((r['duration_s'] for r in after_motion),default=0.),
        low_speed_pauses_ge_60s_after_translation=[r for r in after_motion if r['duration_s']>=60.],
        stand_settling_samples=len(settling),
        nonterminal_stand_settling_samples=sum(not r['terminal_capture'] for r in settling),
        maximum_stand_settling_speed_m_s=max((r['speed_m_s'] for r in settling),default=0.),
        endpoint_pose_rejected_lines=[r for r in log.splitlines() if 'pct_endpoint_pose_rejected' in r],
        shared_no_route_lines=[r for r in log.splitlines() if 'pct_shared_traversability_no_route' in r],
        live_feedback_update_lines=[r for r in log.splitlines() if 'pct_live_feedback session=' in r],
        recorded_parameter_sources=capture.sources,
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        raw_capture_manifest_sha256=hashlib.sha256((raw/'raw_capture_manifest.json').read_bytes()).hexdigest(),
        claim='Applied telemetry, not commanded-target or exact internal spline-phase replay. Intervals use recorded sample endpoints.')
    (out/'command_continuity.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(case_id=case,max_nonterminal_pure_yaw_s=report['maximum_nonterminal_pure_yaw_s'],
        nonterminal_settling_samples=report['nonterminal_stand_settling_samples'])),flush=True)


if __name__=='__main__':
    audit(sys.argv[1])
