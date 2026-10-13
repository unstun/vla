"""Quantify time-aligned curve transitions; reject unmatched/frozen observations."""
from pathlib import Path
import bisect
import csv
import hashlib
import json
import sys
import numpy as np
from scipy.interpolate import BSpline

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'versions/v51'))
import artifacts
from analyze import stats


def process(run_name):
    run=BASE/'runs'/run_name
    with artifacts.open_text(run,'artifacts/reactive_observations.jsonl') as f:
        curves=[json.loads(s) for s in f if '"event": "bspline"' in s]
    # The original JSON encoder uses a spaced separator; verify selection against
    # the previously verified full observation-derived curve count.
    expected=json.loads((BASE/'versions/v57/analysis'/(run_name+'_metrics.json')).read_text())['observed_nonemergency_curves']
    curves=[e for e in curves if not e['data'].get('emergency_stop')]
    assert len(curves)==expected,(len(curves),expected)
    def convert(e):
        d=e['data'];k=d['knots'];p=d['order'];control=np.array([[q[x] for x in ('x','y','z')] for q in d['pos_pts']]);start=d['start_time']['sec']+d['start_time']['nanosec']*1e-9
        return dict(id=d['traj_id'],start=start,duration=k[-p-1]-k[p],spline=BSpline(k,control,p),zero=k[p],receipt_wall=e['wall_monotonic_ns']*1e-9)
    curves=[convert(e) for e in curves]
    rounds=json.loads((BASE/'versions/v57/analysis'/(run_name+'_rounds.json')).read_text());times=[r['ros_s'] for r in rounds]
    accepted=[];skipped={}
    def skip(why):skipped[why]=skipped.get(why,0)+1
    for old,new in zip(curves,curves[1:]):
        if not 65<=new['start']<90:continue
        # ROS time is quantized: the next round can share the previous publish
        # stamp. Match against recorded wall completion before checking geometry.
        r=min(rounds,key=lambda r:abs(r['start_wall_s']+r['wall_s']-new['receipt_wall']))
        if abs(r['start_wall_s']+r['wall_s']-new['receipt_wall'])>.02:skip('receipt_not_near_nominal_completion');continue
        if not r['success'] or not r['warm_accepts'] or r['rebound_attempts']!=1:skip('not_single_warm_success');continue
        if new['id']!=old['id']+1:skip('missing_curve_id');continue
        t0=r['ros_s']-old['start'];t1=new['start']-old['start']
        if not 0<=t0<=t1<=old['duration']:skip('outside_remaining_curve');continue
        new_start=new['spline'](new['zero'])
        old_start=old['spline'](old['zero']+t0)
        mismatch=np.linalg.norm(new_start-old_start)
        if mismatch>2e-5:skip('unmatched_or_clock_shifted');continue
        old_at_publish=old['spline'](old['zero']+t1)
        velocity=old['spline'].derivative()(old['zero']+t0)
        speed=np.linalg.norm(velocity[:2]);direction=velocity[:2]/speed if speed>1e-9 else np.zeros(2)
        shift=new_start-old_at_publish
        accepted.append(dict(sim_s=r['ros_s'],traj_id=new['id'],solve_ms=r['wall_s']*1000,
            stamp_delay_sim_ms=(new['start']-r['ros_s'])*1000,
            fixed_input_pva_position_error_m=float(mismatch),
            publication_position_step_xy_m=float(np.linalg.norm(shift[:2])),
            publication_step_along_m=float(shift[:2]@direction)))
    bands={}
    for lo,hi in [(65,70),(70,75),(75,80),(80,85),(85,90)]:
        g=[r for r in accepted if lo<=r['sim_s']<hi]
        bands[f'{lo}-{hi}']={key:stats([r[key] for r in g]) for key in ['stamp_delay_sim_ms','publication_position_step_xy_m','publication_step_along_m','fixed_input_pva_position_error_m']}
    summary=dict(run=run_name,matched_pairs=len(accepted),excluded_pairs=skipped,bands=bands,
        samples=[min(accepted,key=lambda r:abs(r['sim_s']-t)) for t in [65,70,75,80,85,89]],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Consecutive observed native curve IDs, single successful warm round and start-position agreement within 20 micrometers. Compare old curve at new native start stamp with new curve at t=0; controller receipt time is not reconstructed. Unmatched or clock-shifted cases are excluded.')
    (HERE/(run_name+'_phase_lag.json')).write_text(json.dumps(summary,indent=2)+'\n')
    with (HERE/(run_name+'_phase_lag.csv')).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(accepted[0]));w.writeheader();w.writerows(accepted)
    print(run_name,len(accepted),skipped,json.dumps(bands['85-90']),flush=True)


for run in ['v57_realtime_trial01','v57_realtime_trial02']:
    process(run)
