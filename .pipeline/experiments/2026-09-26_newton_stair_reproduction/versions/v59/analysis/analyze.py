"""Read original v57 traces on the execution host; export compact diagnostics."""
from pathlib import Path
from collections import Counter
import bisect
import csv
import hashlib
import json
import math
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
sys.path.insert(0, str(BASE/'versions/v51'))
import artifacts


def save(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2)+'\n')


def read(run, name):
    with artifacts.open_text(run, name) as f:
        return f.read()


def stats(values):
    values = sorted(values)
    if not values:
        return None
    def pct(q):
        x = (len(values)-1)*q
        i = int(x)
        return values[i]+(values[min(i+1, len(values)-1)]-values[i])*(x-i)
    return dict(n=len(values), mean=statistics.mean(values), median=pct(.5),
                minimum=values[0], p95=pct(.95), maximum=values[-1])


def analyze(run_name):
    run = BASE/'runs'/run_name
    inputs = {}
    def original(name):
        text = read(run, name)
        inputs[name] = hashlib.sha256(text.encode()).hexdigest()
        return text
    rows_path = BASE/'versions/v59/analysis'/(run_name+'_rounds.json')
    rows = json.loads(rows_path.read_text())
    lines = original('scan.log').splitlines()
    points = [json.loads(s) for s in original('sensor.jsonl').splitlines()]
    obs = [json.loads(s) for s in original('artifacts/reactive_observations.jsonl').splitlines()]
    routes = [e for e in obs if e['event']=='pct_route' and e['data'].get('path', {}).get('poses')]
    route_walls = [e['wall_monotonic_ns']*1e-9 for e in routes]
    point_times = [p['sim_time_s'] for p in points]
    records, evidence = [], []
    for r in rows:
        if not 55 <= r['ros_s'] < 90:
            continue
        segment = lines[r['start_line']-1:r['end_line']]
        profile = r['profile'][0]
        refresh = []
        for line in segment:
            m = re.search(r'input_refresh site=(\S+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+) fsm_odom=(-?\d+) cloud_age=([-.\d]+)->([-.\d]+) body_age=([-.\d]+)->([-.\d]+)', line)
            if m:
                refresh.append(dict(site=m[1], clouds=int(m[3]), body_poses=int(m[4]),
                    cloud_before=float(m[6]), cloud_after=float(m[7]),
                    body_before=float(m[8]), body_after=float(m[9])))
        seeds = [json.loads(s.split('spline_seed_capture ', 1)[1]) for s in segment if 'spline_seed_capture ' in s]
        start = seeds[0]['points'][0] if seeds else None
        route = routes[max(0, bisect.bisect_right(route_walls, r['start_wall_s'])-1)]
        poses = route['data']['path']['poses']
        goal = [poses[-1]['pose']['position'][k] for k in ('x','y','z')]
        i = min(len(points)-1, bisect.bisect_left(point_times, r['ros_s']))
        point = points[i]
        record = dict(sim_s=r['ros_s'], wall_s=r['start_wall_s'], solve_ms=r['wall_s']*1000,
            success=r['success'], warm=r['warm_accepts']>0, attempts=r['rebound_attempts'],
            skipped_slots=r['skipped_slots'], start_line=r['start_line'], end_line=r['end_line'],
            pool_rejected=any('Ran out of pool' in s for s in segment),
            proof_rejected=any('V50_GOAL_REGION_EMPTY' in s or 'V58_GOAL_ENDPOINT_EMPTY' in s for s in segment),
            neighbor_selected=any('reference_goal_neighbor ' in s for s in segment),
            frontier_selected=any('reference_frontier ' in s for s in segment),
            seed_nodes=len(seeds[0]['points']) if seeds else None, start=start, goal=goal,
            body=point['body_sensor']['position'], speed_xy=math.hypot(*point['body_sensor']['linear_world'][:2]),
            sensor_points=point['sensor']['point_count'], profile=profile, refresh=refresh,
            route_points=len(poses), route_clock_s=route['clock_ns']*1e-9)
        records.append(record)
    cases = []
    for t in [65,68,69,70,72,74,75,80,85,89]:
        r=min((r for r in records if r['success'] and r['warm'] and r['attempts']==1 and r['start']),key=lambda r:abs(r['sim_s']-t))
        cases.append(r)
        evidence.append(dict(requested_s=t, sim_s=r['sim_s'], lines=[dict(line=j+1,text=lines[j]) for j in range(r['start_line']-1,r['end_line']) if not any(tag in lines[j] for tag in ['spline_seed_capture','spline_curve_capture'])]))
    bands={}
    for lo,hi in [(55,65),(65,70),(70,75),(75,80),(80,85),(85,90)]:
        group=[r for r in records if lo<=r['sim_s']<hi]
        stages={k:stats([r['profile'][k]['wall_ms'] for r in group]) for k in group[0]['profile']}
        refresh=[s for r in group for s in r['refresh']]
        no_cloud=[r for r in group if r['warm'] and r['attempts']==1 and r['profile']['cloud']['calls']==0]
        cloud=[r for r in group if r['warm'] and r['attempts']==1 and r['profile']['cloud']['calls']>0]
        bands[f'{lo}-{hi}']=dict(rounds=len(group), successes=sum(r['success'] for r in group),warm=sum(r['warm'] for r in group),
            pool_rejections=sum(r['pool_rejected'] for r in group), proof_rejections=sum(r['proof_rejected'] for r in group),
            neighbors=sum(r['neighbor_selected'] for r in group),frontiers=sum(r['frontier_selected'] for r in group),
            skipped_slots=sum(r['skipped_slots'] for r in group),solve_ms=stats([r['solve_ms'] for r in group]),
            stage_wall_ms=stages,goal_cpu_over_wall=sum(r['profile']['goal_search']['cpu_ms'] for r in group)/sum(r['profile']['goal_search']['wall_ms'] for r in group),
            no_cloud_solve_ms=stats([r['solve_ms'] for r in no_cloud]),cloud_solve_ms=stats([r['solve_ms'] for r in cloud]),
            cloud_ms_per_callback=stats([r['profile']['cloud']['wall_ms']/r['profile']['cloud']['calls'] for r in cloud]),
            cloud_callbacks_per_round=stats([r['profile']['cloud']['calls'] for r in group]),
            cloud_age_before=stats([s['cloud_before'] for s in refresh]),cloud_age_after=stats([s['cloud_after'] for s in refresh]),
            measured_speed_xy=stats([r['speed_xy'] for r in group]),point_count=stats([r['sensor_points'] for r in group]),
            warm_seed_nodes=stats([r['seed_nodes'] for r in group if r['seed_nodes']]))
    onset=next((r for r in records if r['sim_s']>=65 and not r['pool_rejected'] and not r['proof_rejected'] and r['profile']['goal_search']['wall_ms']>1),None)
    summary=dict(run=run_name, inputs=inputs, derived_rounds_sha256=artifacts.digest(rows_path),bands=bands,
                 first_expensive_goal_after65=onset,cases=cases,
                 scope='Measured complete rounds. Nested timers overlap; recorded input reuse is not a new physical trial.')
    save(run_name+'_summary.json',summary)
    save(run_name+'_cases.json',cases)
    save(run_name+'_evidence.json',evidence)
    fields=['sim_s','solve_ms','warm','success','pool_rejected','proof_rejected','neighbor_selected','frontier_selected','skipped_slots','speed_xy','sensor_points','seed_nodes']
    stages=['goal_search','target','inputs','cloud','warm_seed','optimizer','final_check']
    with (HERE/(run_name+'_stages.csv')).open('w') as f:
        w=csv.writer(f);w.writerow(fields+[s+'_ms' for s in stages]+['cloud_calls'])
        for r in records:w.writerow([r[k] for k in fields]+[r['profile'][s]['wall_ms'] for s in stages]+[r['profile']['cloud']['calls']])
    print(run_name,'onset',onset['sim_s'] if onset else None,'last85-90',json.dumps(bands['85-90']),flush=True)


if __name__=='__main__':
    for run in ['v58_realtime_trial02','v59_realtime_trial01']:
        analyze(run)
