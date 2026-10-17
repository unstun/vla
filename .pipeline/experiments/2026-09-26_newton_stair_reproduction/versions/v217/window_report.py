"""Compare archived navigation/stance evidence; never run physics or inference."""
from pathlib import Path
import sys,json,math,re
from collections import Counter
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'v196'))
from analyze_remote import Capture,core
ROOT=Path('/data/sun/vla_mppi_20261009/trials')
OUT=HERE/'results';OUT.mkdir(exist_ok=True)

def analyze(version):
    raw=ROOT/(version+'_linux_full_attempt01')/'runs'/(version+'_linux_full_attempt01')
    c=Capture(raw);rows=c.rows('telemetry.jsonl');log=c.read('nav2.log')
    class Log:
        def read_text(self):return log
    _,rounds=core.parse_rounds(Log())
    events=c.rows('artifacts/reactive_observations.jsonl')
    def stamp(r):return r.get('physics_time_s',r.get('time_s'))
    def subset(lo,hi):
        part=[r for r in rows if lo<=stamp(r)<hi]
        rr=[r for r in rounds if lo<=r.get('ros_s',-1)<hi and r.get('completed')]
        if not part:return None
        forces=np.array([r['foot_forces_n'] for r in part]);tilts=np.degrees(np.arccos(np.clip([r['base_up_z'] for r in part],-1,1)))
        commands=np.array([r['effective_command'] for r in part])
        per_second={}
        for sec in range(math.floor(lo),math.ceil(hi)):
            rs=[r for r in rr if sec<=r['ros_s']<sec+1]
            per_second[str(sec)]={'success':sum(bool(r['success']) for r in rs),'attempts':len(rs)}
        return dict(time_window_s=[lo,hi],actual_last_sample_s=stamp(part[-1]),samples=len(part),
            successful_rounds=sum(bool(r['success']) for r in rr),completed_rounds=len(rr),
            success_fraction=sum(bool(r['success']) for r in rr)/len(rr) if rr else None,
            per_second=per_second,stance_samples=dict(Counter(r['stance_mode'] for r in part)),
            foot_order=['FL','FR','HL','HR'],foot_force_min_n=forces.min(axis=0).tolist(),
            foot_force_mean_n=forces.mean(axis=0).tolist(),foot_force_max_n=forces.max(axis=0).tolist(),
            tilt_max_deg=float(tilts.max()),tilt_p95_deg=float(np.quantile(tilts,.95)),
            exact_zero_command_samples=int(np.sum(np.max(np.abs(commands),axis=1)<=.001)),
            xy_command_max_mps=float(np.max(np.linalg.norm(commands[:,:2],axis=1))))
    entries=[];previous=None
    for r in rows:
        if r['stance_mode']=='STAND_TRANSITION' and previous!='STAND_TRANSITION':
            entries.append(dict(physics_s=stamp(r),forces_n=r['foot_forces_n'],
                tilt_deg=math.degrees(math.acos(float(np.clip(r['base_up_z'],-1,1)))),
                all_feet_at_least_10n=bool(min(r['foot_forces_n'])>=10)))
        previous=r['stance_mode']
    region=[r for r in rows if 6.7<=r['joint_q'][0]<=8.8 and -4.8<=r['joint_q'][1]<=-2.8 and 1.3<=r['joint_q'][2]<=2.3]
    spatial_window=subset(stamp(region[0]),stamp(region[-1])+.001) if region else None
    route_events=[e for e in events if e['event']=='pct_route']
    failures=[l for l in log.splitlines() if 'local_trajectory_starvation' in l or 'Failed to make progress' in l]
    status=c.json('stance_status.json')
    return dict(version=version,raw_root=str(raw),window_45_55=subset(45.,55.),
        staircase_spatial_window=spatial_window,pd_entries=entries,
        route_deliveries=len(route_events),route_delivery_times_s=[e['clock_ns']/1e9 for e in route_events],
        starvation_and_progress_messages=failures,stance_status=status,
        note='Force minima during walking include normal unloaded swing feet; PD entry is checked separately. Spatial region is analysis only, never runtime logic.')

versions=sys.argv[1:] or ['v210','v212','v217']
reports={v:analyze(v) for v in versions}
(OUT/'staircase_comparison.json').write_text(json.dumps(reports,indent=2)+'\n')
for v,r in reports.items():
    print(json.dumps({'version':v,'window':r['window_45_55'],'spatial':r['staircase_spatial_window'],
      'route_deliveries':r['route_deliveries'],'entries':r['pd_entries'],'recovery_messages':r['starvation_and_progress_messages']}))
