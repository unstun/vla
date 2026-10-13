"""Measure actual policy commands; keep explicit stops distinct from low walking."""
import argparse
from bisect import bisect_right
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
FLOOR = .6
ZERO = 1e-6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def groups(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def stamp(data):
    return data['sec'] + data['nanosec'] / 1e9


def boundary_distance(speed, minimum=.6, acceleration=.5, jerk=4.):
    dv = max(0., minimum-speed)
    duration = dv/acceleration + acceleration/jerk if dv >= acceleration**2/jerk else 2*np.sqrt(dv/jerk)
    return (speed+minimum)*.5*duration


def prepare_curve(data):
    points = np.array([[p[k] for k in 'xyz'] for p in data['pos_pts']])
    knots = np.asarray(data['knots'])
    curve = BSpline(knots, points, data['order'], extrapolate=False)
    duration = float(knots[len(points)]-knots[data['order']])
    grid = np.linspace(0., duration, max(2, int(np.ceil(duration/.01))+1))
    positions = curve(grid)
    speed = np.linalg.norm(curve.derivative()(grid)[:, :2], axis=1)
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(positions[:, :2], axis=0), axis=1))]
    entry = boundary_distance(speed[0]); exit_distance = boundary_distance(speed[-1])
    eligible = (distance >= entry) & (distance[-1]-distance >= exit_distance)
    return dict(curve=curve, duration=duration, start=stamp(data['start_time']), grid=grid,
        speed=speed, distance=distance, entry=entry, exit=exit_distance,
        cruise_samples=int(eligible.sum()), endpoint=positions[-1, :2])


def analyze(run, stops):
    receipt = json.loads((run/'receipt.json').read_text())
    for name, identity in receipt['outputs'].items():
        assert sha(run/name) == identity['sha256']
    rows = [json.loads(x) for x in gzip.open(run/'telemetry.jsonl.gz','rt')]
    events = [json.loads(x) for x in gzip.open(run/'events.jsonl.gz','rt')]
    times = np.array([r['physics_time_s'] for r in rows])
    starts = np.r_[times[0]-.02, times[:-1]]
    dt = times-starts
    assert np.all((dt>0)&(dt<.025)), 'No classification across gaps'
    command = np.array([r['effective_command'] for r in rows])
    speed = np.linalg.norm(command[:, :2],axis=1)
    body = np.array([r['position'] for r in rows])
    actual = np.linalg.norm(np.array([r['linear_world'][:2] for r in rows]),axis=1)
    zero = np.max(np.abs(command),axis=1) <= ZERO
    turning = (speed <= ZERO) & ~zero
    low = (speed > ZERO) & (speed < FLOOR)
    high = speed >= FLOOR
    raw = sorted([r for r in events if r['event']=='raw_command'], key=lambda r: stamp(r['data']['stamp']))
    raw_times = np.array([stamp(r['data']['stamp']) for r in raw])
    raw_cmd = np.array([[r['data']['twist']['linear'][k] for k in ('x','y')]+[r['data']['twist']['angular']['z']] for r in raw])
    curves = {}
    for event in events:
        if event['event'] != 'bspline' or event['data']['emergency_stop']:
            continue
        data = event['data']; key = (data['generation'], data['traj_id'])
        if key not in curves:
            curves[key] = prepare_curve(data)
    # Raw messages carry the curve identity; equal command vectors within 0.3s
    # establish the source value, not a unique transport-message identity.
    matched = np.full(len(rows),-1,dtype=int)
    phase = np.full(len(rows),'unresolved',dtype=object)
    reference = np.full(len(rows),np.nan)
    curve_keys = [None]*len(rows)
    endpoint_error = np.full(len(rows),np.nan)
    endpoint_command_error = np.full(len(rows),np.nan)
    raw_phase = []
    paused = Counter(); previous_by_curve = {}
    for event, time, cmd in zip(raw, raw_times, raw_cmd):
        data=event['data']; key=(data['generation'],data['traj_id']); curve=curves.get(key)
        previous=previous_by_curve.get(key, time)
        if np.linalg.norm(cmd[:2]) <= ZERO and abs(cmd[2])>ZERO and 0<time-previous<=.2:
            paused[key] += time-previous
        previous_by_curve[key]=time
        raw_phase.append(max(0.,time-curve['start']-paused[key]) if curve else None)
    for i in range(len(rows)):
        if zero[i]:
            phase[i]='zero';continue
        if turning[i]:
            phase[i]='turn';continue
        right=bisect_right(raw_times,times[i]); left=bisect_right(raw_times,times[i]-.3)
        matches=[j for j in range(left,right) if np.max(np.abs(raw_cmd[j]-command[i]))<2e-7]
        if not matches:continue
        j=matches[-1]; matched[i]=j
        key=(raw[j]['data']['generation'],raw[j]['data']['traj_id']);curve_keys[i]=key
        curve=curves.get(key)
        if curve is None:continue
        elapsed=raw_phase[j]; clamped=min(curve['duration'],elapsed)
        reference[i]=float(np.interp(clamped,curve['grid'],curve['speed']))
        distance=float(np.interp(clamped,curve['grid'],curve['distance']))
        endpoint_error[i]=np.linalg.norm(curve['endpoint']-body[i,:2])
        # Current pose is up to one policy step after command computation;
        # terminal-fit errors are diagnostic, not an exact controller replay.
        q=rows[i]['quaternion'];w,x,y,z=q
        yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z)); c,s=np.cos(yaw),np.sin(yaw)
        correction=.8*(curve['endpoint']-body[i,:2])
        correction *= min(1.,1./max(np.linalg.norm(correction),1e-12))
        predicted=np.clip([c*correction[0]+s*correction[1],-s*correction[0]+c*correction[1]],[-1.,-.35],[1.,.35])
        endpoint_command_error[i]=float(np.linalg.norm(predicted-command[i,:2]))
        if elapsed>curve['duration']+.1:
            phase[i]='expired_endpoint'
        elif distance<curve['entry'] or curve['distance'][-1]-distance<curve['exit']:
            phase[i]='curve_boundary'
        else:
            phase[i]='curve_cruise'

    def metrics(i,j):
        pre=body[max(0,i-1),:2]
        return dict(start_s=float(starts[i]),end_s=float(times[j-1]),duration_s=float(dt[i:j].sum()),
            first_source_line=rows[i]['source_line'],last_source_line=rows[j-1]['source_line'],samples=int(j-i),
            command_min_mps=float(speed[i:j].min()),command_median_mps=float(np.median(speed[i:j])),
            command_max_mps=float(speed[i:j].max()),actual_median_mps=float(np.median(actual[i:j])),
            displacement_m=float(np.linalg.norm(body[j-1,:2]-pre)),
            maximum_excursion_m=float(np.linalg.norm(body[i:j,:2]-pre,axis=1).max()),
            actual_max_mps=float(actual[i:j].max()))

    intervals=[]
    for k,(i,j) in enumerate(groups(low),1):
        item=metrics(i,j); item['id']=f"{run.name}-L{k:03d}"
        if item['duration_s'] < .1:continue
        phases=Counter(phase[i:j]); terminal_time=float(dt[i:j][phase[i:j]=='expired_endpoint'].sum())
        terminal_fit=endpoint_command_error[i:j][phase[i:j]=='expired_endpoint']
        before='start' if i==0 else ('zero' if zero[i-1] else 'turn' if turning[i-1] else 'high')
        after='end' if j==len(rows) else ('zero' if zero[j] else 'turn' if turning[j] else 'high')
        if terminal_time>=.5 and len(terminal_fit) and np.nanmedian(terminal_fit)<.02:
            label='endpoint_correction'
        elif item['duration_s']<=2. and before in ('zero','turn','start') and after=='high':
            label='bounded_start'
        elif item['duration_s']<=2. and before=='high' and after in ('zero','turn','end'):
            label='bounded_brake'
        elif item['duration_s']<=2.:
            label='brief_adjustment'
        else:
            label='prolonged_low_review'
        ref=reference[i:j];valid=np.isfinite(ref)
        item.update(classification=label,before=before,after=after,phase_counts=dict(phases),
            raw_value_match_fraction=float(np.mean(matched[i:j]>=0)),
            matched_trajectories=[list(x) for x in sorted({x for x in curve_keys[i:j] if x is not None})],
            estimated_expired_endpoint_s=terminal_time,
            endpoint_command_fit_median_mps=float(np.nanmedian(terminal_fit)) if len(terminal_fit) else None,
            endpoint_position_error_median_m=float(np.nanmedian(endpoint_error[i:j][phase[i:j]=='expired_endpoint'])) if len(terminal_fit) else None,
            stance_modes=dict(Counter(r['stance_mode'] for r in rows[i:j])),
            stance_reasons=dict(Counter(r['stance_reason'] for r in rows[i:j])),
            matched_curve_stats=[dict(generation=k[0],trajectory=k[1],duration_s=curves[k]['duration'],
                path_length_m=float(curves[k]['distance'][-1]),cruise_samples=curves[k]['cruise_samples'])
                for k in sorted({x for x in curve_keys[i:j] if x is not None}) if k in curves],
            reference_speed_median_mps=float(np.median(ref[valid])) if valid.any() else None,
            reference_at_least_06_while_input_low_s=float(dt[i:j][valid & (ref>=FLOOR)].sum()))
        item['endpoint_subsegments']=[metrics(i+a,i+b) for a,b in groups(phase[i:j]=='expired_endpoint')]
        intervals.append(item)

    zeros=[]
    for k,(i,j) in enumerate(groups(zero),1):
        item=metrics(i,j);item['id']=f'{run.name}-Z{k:03d}'
        if item['duration_s'] < .1:continue
        late=np.flatnonzero(times[i:j]>=starts[i]+2.)+i
        item.update(mode_counts=dict(Counter(r['stance_mode'] for r in rows[i:j])),
            policy_owned_fraction=float(np.mean([r['policy_owns_joints'] for r in rows[i:j]])),
            late_after_2s_excursion_m=float(np.linalg.norm(body[late,:2]-body[late[0],:2],axis=1).max()) if len(late)>1 else None,
            late_after_2s_duration_s=float(times[j-1]-times[late[0]]) if len(late) else 0.)
        zeros.append(item)

    stops_out=[]
    for stop in stops:
        t=stop['time_s']; item=dict(stop)
        for window in (2.,5.,10.):
            overlap=np.maximum(0.,np.minimum(times,t)-np.maximum(starts,t-window))
            selected=overlap>0; moving_low=selected&low
            item[f'pre{int(window)}']=dict(nonzero_below06_s=float(overlap[low].sum()),
                zero_s=float(overlap[zero].sum()),in_place_turn_s=float(overlap[turning].sum()),
                at_least06_s=float(overlap[high].sum()),
                low_command_median_mps=float(np.median(speed[moving_low])) if moving_low.any() else None)
        item['preceding_low_intervals']=[r['id'] for r in intervals if r['end_s']>t-10 and r['start_s']<t]
        item['zero_episode']=next((z for z in zeros if z['start_s']<=t+.2 and z['end_s']>=t+.1),None)
        item['following_low_intervals']=[r['id'] for r in intervals if r['start_s']<t+10 and r['end_s']>t]
        stops_out.append(item)
    count=low|high
    return dict(run=run.name,source_run=receipt['run'],receipt=receipt,stops=stops_out,low_intervals=intervals,
        zero_episodes=zeros,summary=dict(samples=len(rows),duration_s=float(dt.sum()),
            nonzero_below06_s=float(dt[low].sum()),at_least06_s=float(dt[high].sum()),
            zero_s=float(dt[zero].sum()),in_place_turn_s=float(dt[turning].sum()),
            nonzero_raw_value_match_fraction=float(np.mean(matched[count]>=0)),
            long_counts_by_seconds={str(th):sum(r['duration_s']>=th for r in intervals) for th in (1.,2.,3.)},
            classification_counts=dict(Counter(r['classification'] for r in intervals))),
        plot=dict(time_s=times.tolist(),command=command.tolist(),actual_speed=actual.tolist(),
            position=body.tolist(),phase=phase.tolist(),endpoint_error_m=[float(x) if np.isfinite(x) else None for x in endpoint_error],reference_speed=[float(x) if np.isfinite(x) else None for x in reference]))


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    ledger_path=HERE.parent/'2026-10-12_v177_stop_causes/stop_ledger.json'
    ledger=json.loads(ledger_path.read_text());runs=[]
    for n in range(1,6):
        result=analyze(a.data/f'attempt{n:02d}',[s for s in ledger['stops'] if s['run']==n])
        plot=result.pop('plot')
        with gzip.open(a.output/f'plot{n:02d}.json.gz','wt') as f:json.dump(plot,f,separators=(',',':'))
        (a.output/f'attempt{n:02d}.json').write_text(json.dumps(result,indent=2)+'\n')
        print(result['run'],json.dumps(result['summary']),flush=True);runs.append(result)
    (a.output/'index.json').write_text(json.dumps(dict(analyzer_sha256=sha(Path(__file__)),
        ledger_sha256=sha(ledger_path),runs=[r['run'] for r in runs],
        scope='Recorded command analysis; curve phases estimated from message age minus observed yaw pauses; not an exact native replay.',
        classification='Zero and yaw separated; <=2s boundary transitions are bounded, not evidence of stable locomotion. Longer low commands require curve/context review.',
        outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in a.output.iterdir() if p.name!='index.json'}),indent=2)+'\n')


if __name__=='__main__':main()
