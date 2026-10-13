"""Measure physical/curve phase error and command speed from original captures.

The decomposed controller expression uses a round-start seed and interpolated
body pose, not reconstructed internal controller callback state.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[2]
sys.path.insert(0,str(BASE/'versions/v51'))
import artifacts
from analyze import stats


def text(run,name):
    with artifacts.open_text(run,name) as f:return f.read()


def process(run_name):
    run=BASE/'runs'/run_name
    points=[json.loads(s) for s in text(run,'sensor.jsonl').splitlines()]
    times=np.array([p['sim_time_s'] for p in points])
    xyz=np.array([p['body_sensor']['position'] for p in points])
    video=json.loads((run/'video_states.json').read_text())
    timed=[p for p in video if 'wall_monotonic_s' in p]
    vw=[p['wall_monotonic_s'] for p in timed];vs=[p['physics_time_s'] for p in timed]
    commands=[json.loads(s) for s in text(run,'command_frequencies.jsonl').splitlines()]
    raw=[r for r in commands if r['topic']=='/quad_0/raw_scan_cmd_vel']
    for r in raw:r['sim_s']=float(np.interp(r['wall_monotonic_s'],vw,vs))
    lines=text(run,'scan.log').splitlines()
    rounds=json.loads((BASE/'versions/v58/analysis'/(run_name+'_rounds.json')).read_text())
    rows=[]
    for r in rounds:
        if not 55<=r['ros_s']<90 or not r['success'] or r['rebound_attempts']!=1:continue
        seeds=[json.loads(s.split('spline_seed_capture ',1)[1]) for s in lines[r['start_line']-1:r['end_line']] if 'spline_seed_capture ' in s]
        if not seeds:continue
        seed=seeds[0];start=np.array(seed['points'][0]);velocity=np.array(seed['derivatives'][0])
        body=np.array([np.interp(r['ros_s'],times,xyz[:,i]) for i in range(3)])
        error=(start-body)[:2];speed=np.linalg.norm(velocity[:2])
        unit=velocity[:2]/speed if speed>1e-9 else np.zeros(2)
        along=float(error@unit)
        rows.append(dict(sim_s=r['ros_s'],solve_ms=r['wall_s']*1000,position_error_xy_m=float(np.linalg.norm(error)),
            along_error_m=along,planned_speed_xy_mps=float(speed),position_feedback_along_mps=.8*along,
            start_state_command_along_mps=float(speed)+.8*along,start=start.tolist(),body=body.tolist()))
    bands={}
    for lo,hi in [(55,65),(65,70),(70,75),(75,80),(80,85),(85,90)]:
        group=[r for r in rows if lo<=r['sim_s']<hi]
        cmd=[r for r in raw if lo<=r['sim_s']<hi]
        physical=[p for p in points if lo<=p['sim_time_s']<hi]
        bands[f'{lo}-{hi}']=dict(position_error_xy_m=stats([r['position_error_xy_m'] for r in group]),
            along_error_m=stats([r['along_error_m'] for r in group]),
            planned_speed_xy_mps=stats([r['planned_speed_xy_mps'] for r in group]),
            position_feedback_along_mps=stats([r['position_feedback_along_mps'] for r in group]),
            raw_command_speed_mps=stats([float(np.hypot(r['vx'],r['vy'])) for r in cmd]),
            raw_command_hz=(len(cmd)-1)/(cmd[-1]['wall_monotonic_s']-cmd[0]['wall_monotonic_s']),
            raw_command_zero_translation=int(sum(np.hypot(r['vx'],r['vy'])<1e-6 for r in cmd)),
            physical_speed_mps=stats([float(np.linalg.norm(p['body_sensor']['linear_world'][:2])) for p in physical]))
    samples=[min(rows,key=lambda r:abs(r['sim_s']-t)) for t in [65,70,75,80,85,89]]
    summary=dict(run=run_name,bands=bands,samples=samples,
        scope='Exact logged initial PVA and body pose interpolated between 10 Hz physical samples; raw commands are measured separately. kp_pos=0.8 decomposition explains sign/scale but is not an exact reconstruction of controller internal exec_time.',
        native_controller_source='runtime/scan79_goal_endpoint_evidence_v58/src/plan_manage/src/closed_loop_controller.cpp',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (HERE/(run_name+'_motion.json')).write_text(json.dumps(summary,indent=2)+'\n')
    with (HERE/(run_name+'_motion.csv')).open('w') as f:
        fields=[k for k in rows[0] if k not in ['start','body']]
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print(run_name,json.dumps(bands['85-90']),flush=True)


for run in ['v58_realtime_trial01']:
    process(run)
