"""Correlate source-aged safety vetoes and stalled motion without new physics."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import numpy as np

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'versions/v177'))
from analyze_remote import Capture


def stamp(x):
    return x['sec']+x['nanosec']/1e9


def run(task, first, output):
    output.mkdir(parents=True,exist_ok=False)
    for attempt in range(1,6):
        previous=json.loads((first/f'attempt{attempt:02d}.json').read_text())
        c=Capture(task/'trials'/previous['run']/'runs'/previous['run'])
        rows=c.rows('artifacts/reactive_observations.jsonl');lines=c.read('nav2.log').splitlines()
        anchors=[(float(re.search(r'\[(\d+\.\d+)\]',o['revocation_log'])[1]),o['cancel']['sim_s']) for o in previous['owners']]
        real=[x[0] for x in anchors];sim=[x[1] for x in anchors]
        # ROS log headers use realtime, events use ROS simulation time. This
        # approximate index only selects context; cause ages use message stamps.
        log_times=[];t=real[0]
        for l in lines:
            m=re.search(r'\[(\d+\.\d+)\]',l)
            if m:t=float(m[1])
            mapped=t-real[0]+sim[0] if t<real[0] else (t-real[-1]+sim[-1] if t>real[-1] else float(np.interp(t,real,sim)))
            log_times.append(mapped)
        groups=collections.defaultdict(list)
        for i,r in enumerate(rows,1):r['source_line']=i;groups[r['event']].append(r)
        sensors=c.rows('sensor.jsonl')
        report=[]
        for o in previous['owners']:
            stop=o['cancel']['sim_s'];g=o['generation'];active=int(re.search(r'trajectory=(\d+)',o['revocation_log'])[1])
            candidates=[r for r in groups['execution_safety'] if r['data']['binding']['generation']==g
                        and r['data']['binding']['traj_id']==active and not r['data']['clear']
                        and stop-.15<=r['clock_ns']/1e9<=stop+.035]
            first_bad=candidates[0] if candidates else None
            proof=None
            if first_bad:
                d=first_bad['data'];proof={'line':first_bad['source_line'],'checked_s':stamp(d['stamp']),
                    'event_s':first_bad['clock_ns']/1e9,'cloud_s':d['observation_stamp_s'],
                    'cloud_age_s':stamp(d['stamp'])-d['observation_stamp_s'],
                    'map_revision':d['local_map_revision'],'trajectory':active}
            independent=[x for x in o['log_context'] if 'SCAN evidence rejected now=' in x['text']]
            if independent:
                d=dict(re.findall(r'(\w+)=([-0-9.]+)',independent[0]['text']))
                proof={'line':independent[0]['line'],'source':'nav2.log controller proof',
                       'checked_s':float(d['proof_stamp']),'event_s':float(d['now']),
                       'cloud_s':float(d['observation_stamp']), 'cloud_age_s':float(d['observation_age']),
                       'trajectory':int(d['active'])}
            cloud=[r for r in groups['cloud'] if r['wall_monotonic_ns']/1e9<=o['cancel']['wall_s']]
            latest=cloud[-1] if cloud else None
            context=[{'line':i+1,'sim_approx_s':log_times[i],'text':l} for i,l in enumerate(lines)
                     if stop-.65<=log_times[i]<=stop+.15 and any(s in l for s in
                       ('reactive_collision_blocked','input_refresh','Obstacle discovered','V82_MAP_SNAPSHOT',
                        'safety','SAFETY','initial_spline_collision','final_spline_rejected','reference_prefix_rejected'))]
            report.append({'generation':g,'stop_s':stop,'reason':o['cancel']['data']['reason'],
                           'proof':proof,'latest_received_cloud':None if not latest else {
                               'source_s':latest['data']['stamp_ns']/1e9,'received_sim_s':latest['clock_ns']/1e9,
                               'age_at_stop_s':stop-latest['data']['stamp_ns']/1e9,'line':latest['source_line']},
                           'context':context})
        pauses=[]
        for p in previous['pauses']:
            start,end=p['start_sim_s'],p['end_sim_s']
            curve=[r for r in groups['bspline'] if not r['data'].get('emergency_stop') and start-1<=r['clock_ns']/1e9<=end]
            before=[r for r in groups['bspline'] if not r['data'].get('emergency_stop') and r['clock_ns']/1e9<start-1]
            if before:curve.insert(0,before[-1])
            cmds=[r for r in groups['raw_command'] if start<=r['clock_ns']/1e9<=end]
            body=[r for r in sensors if start<=r['sim_time_s']<=end]
            curve_info=[]
            for r in curve:
                d=r['data'];pts=np.array([[p[k] for k in 'xyz'] for p in d['pos_pts']]);n=len(pts)
                curve_info.append({'sim_s':r['clock_ns']/1e9,'traj':d['traj_id'],'generation':d['generation'],
                    'reverse':d.get('reverse_motion'),'duration':d['knots'][n]-d['knots'][3],
                    'start':list(pts[0]),'end':list(pts[-1]),'polygon_length':float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum())})
            grouped=collections.Counter(r['data']['traj_id'] for r in cmds)
            counts=collections.Counter();examples={}
            patterns=['target_connector','reference_prefix_rejected','reference path rejected','initial_spline_collision',
                      'reactive_collision_blocked','V167_STEERING_PREFIX','final_spline_rejected','reactive_stair_seed_search_failed',
                      'Obstacle discovered','start_to_free','no_route','occupied','waiting_for_fresh','V48_WARM_RESULT accepted=0']
            for i,l in enumerate(lines):
                if not start-1<=log_times[i]<=end:continue
                for k in patterns:
                    if k in l:
                        counts[k]+=1
                        examples.setdefault(k,[])
                        if len(examples[k])<3:examples[k].append({'line':i+1,'sim_approx_s':log_times[i],'text':l})
            pauses.append({'index':p['index'],'start':start,'end':end,'generation':p['active_generation_at_start'],
                           'displacement_m':math.dist(body[0]['body_sensor']['position'],body[-1]['body_sensor']['position']),
                           'command_trajectory_counts':dict(grouped),'curve_count':len(curve_info),
                           'curves':curve_info if len(curve_info)<30 else curve_info[:8]+curve_info[-8:],
                           'max_linear_command':max((math.hypot(r['data']['twist']['linear']['x'],r['data']['twist']['linear']['y']) for r in cmds),default=0),
                           'max_yaw_command':max((abs(r['data']['twist']['angular']['z']) for r in cmds),default=0),
                           'log_counts':dict(counts),'log_examples':examples})
        result={'run':previous['run'],'stops':report,'pauses':pauses,'sources':c.sources,
                'context_clock_note':'Log contexts use piecewise realtime-to-sim interpolation through matched cancellation anchors; exact source ages use message stamps.'}
        (output/f'windows{attempt:02d}.json').write_text(json.dumps(result,indent=2)+'\n')
        print(previous['run'],len(report),flush=True)
    files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in output.glob('windows*.json')}
    (output/'manifest.json').write_text(json.dumps({'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':files},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',type=Path,default=Path('/data/sun/vla_mppi_20261009'));p.add_argument('--first',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.task,a.first,a.output)
