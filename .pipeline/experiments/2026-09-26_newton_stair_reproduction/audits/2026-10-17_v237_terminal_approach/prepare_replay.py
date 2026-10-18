"""Export original v237 full-prefix inputs; no physics, resampling or map waivers."""
import bisect
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009')
RUN = TASK/'trials/v237_linux_full_attempt01/runs/v237_linux_full_attempt01'
OUT = TASK/'terminal_approach_v238/input05'
sys.path.insert(0, str(BASE/'versions/v196'))
from analyze_remote import Capture

def numbers(values):
    return ' '.join(format(float(x), '.17g') for x in values)

def pose(data):
    p, q = data['pose']['pose']['position'], data['pose']['pose']['orientation']
    return numbers([*[p[k] for k in ('x','y','z')], *[q[k] for k in ('x','y','z','w')]])+'\n'

def main():
    OUT.mkdir(parents=True, exist_ok=False)
    capture = Capture(RUN)
    events = capture.rows('artifacts/reactive_observations.jsonl')
    bodies = [e for e in events if e['event']=='body_pose_observer']
    times = [e['clock_ns'] for e in bodies]
    splines=[e for e in events if e['event']=='bspline']
    spline_times=[e['clock_ns'] for e in splines]
    route = next(e for e in events if e['event']=='pct_route')['data']
    (OUT/'route.txt').write_text('\n'.join(numbers([p['pose']['position'][k] for k in ('x','y','z')]) for p in route['poses'])+'\n')
    sensors = json.loads((RUN/'sensor_manifest.json').read_text())
    published = {r['timestamp_ns'] for r in capture.rows('bridge_scan_audit.jsonl') if r['outcome']=='published_sequentially'}
    scans = [s for s in sensors if s['stamp_ns'] in published and s['sim_time_s']<114.6]
    listing=[]
    archive = __import__('zipfile').ZipFile(RUN/'raw_capture.zip')
    for i,s in enumerate(scans):
        path=RUN/s['file']; raw=path.read_bytes() if path.is_file() else archive.read(s['file'])
        assert hashlib.sha256(raw).hexdigest()==s['sha256']
        points=np.asarray(np.load(io.BytesIO(raw),allow_pickle=False)['sensor_points'],dtype='<f4')
        (OUT/f'cloud_{i:05d}.f32').write_bytes(points.tobytes())
        for optical, role in [(False,'body'),(True,'sensor')]:
            d=s['body_sensor']; w,x,y,z=d['sensor_quaternion' if optical else 'quaternion']
            (OUT/f'{role}_{i:05d}.txt').write_text(numbers([*d['sensor_position' if optical else 'position'],x,y,z,w])+'\n')
        listing.append(f"{i} {s['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
    (OUT/'scans.txt').write_text('\n'.join(listing)+'\n')
    terrain=TASK/'callback_failure_v232/fixtures/building'
    manifest=json.loads((terrain/'terrain.json').read_text())
    for role in ('navigation','surface','physical_floor'):
        entry=manifest['clouds'][role]; raw=(terrain/entry['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        (OUT/f'{role}.f32').write_bytes(raw)
    frames=[]; cutoff=None; next_stair=45.; next_tail=109.;current=None
    for line in capture.read('nav2.log').splitlines():
        if current is not None and 'V48_WARM_SEED selected=' in line and 'warm_eligible' not in current:
            current['warm_eligible']='V48_WARM_SEED selected=1' in line
        hint=re.search(r'V47_WINDOW_HINT projected=([0-9.]+) nominal=([0-9.]+) selected=([0-9.]+) span=([0-9.]+) growth=([01]) measured=([0-9.]+)',line)
        if current is not None and hint:
            current['hint']=[float(hint[i]) for i in (1,3,4,6)]
        match=re.search(r'V82_MAP_SNAPSHOT .*cloud_stamp=([0-9.]+)',line)
        if match: cutoff=float(match[1])
        match=re.search(r'nominal_replan .*ros_s=([0-9.]+)',line)
        if not match:continue
        current=None
        t=float(match[1]); stair=45<=t<=55 and t>=next_stair; tail=109<=t<=114.5 and t>=next_tail
        if not(stair or tail) or cutoff is None:continue
        if stair:next_stair=t+.195
        if tail:next_tail=t+.025
        s=min(scans,key=lambda s:abs(s['sim_time_s']-cutoff));assert abs(s['sim_time_s']-cutoff)<1.1e-6
        ns=round(t*1e9);body=bodies[bisect.bisect_right(times,ns)-1]['data']
        bn=body['header']['stamp']['sec']*10**9+body['header']['stamp']['nanosec']
        i=len(frames);(OUT/f'query_{i:04d}.txt').write_text(pose(body))
        si=bisect.bisect_right(spline_times,ns)-1;assert si>=0
        source=splines[si]['data'];controls=[[p[k] for k in ('x','y','z')] for p in source['pos_pts']];knots=source['knots']
        origin=source['start_time']['sec']+source['start_time']['nanosec']*1e-9
        (OUT/f'curve_{i:04d}.txt').write_text(numbers([origin,len(controls),len(knots)])+'\n'+'\n'.join(numbers(p) for p in controls)+'\n'+numbers(knots)+'\n')
        frames.append(dict(index=i,query_ns=ns,body_ns=bn,cutoff_ns=s['stamp_ns'],time_s=t,cloud_age_s=t-s['sim_time_s']))
        current=frames[-1];current['spline_event_clock_ns']=splines[si]['clock_ns'];current['emergency_curve']=source['emergency_stop']
    for f in frames:
        hint=f.get('hint',[0,0,0,0])
        (OUT/f"state_{f['index']:04d}.txt").write_text(numbers([int(f.get('warm_eligible',False) and not f['emergency_curve']),int('hint' in f),*hint])+'\n')
    # Supplemental due-message stream for an advancing-clock native executor.
    # Keep original observer receive-clock order, source stamps and all clouds.
    scan_by_stamp={s['stamp_ns']:i for i,s in enumerate(scans)}
    stream=[];body_index=0
    for e in events:
        clock=e.get('clock_ns',0)
        if not(44.6e9<=clock<=55.05e9 or 108.7e9<=clock<=114.55e9):continue
        kind=e['event'];data=e['data']
        if kind=='body_pose_observer':
            name=f'live_body_{body_index:05d}.txt';body_index+=1
            twist=data['twist']['twist'];stamp=data['header']['stamp']['sec']*10**9+data['header']['stamp']['nanosec']
            (OUT/name).write_text(pose(data).strip()+' '+numbers([*[twist['linear'][k] for k in ('x','y','z')],*[twist['angular'][k] for k in ('x','y','z')]])+'\n')
            stream.append((clock,0,stamp,name))
        elif kind in ('lidar_pose','cloud'):
            stamp=(data['header']['stamp']['sec']*10**9+data['header']['stamp']['nanosec']) if kind=='lidar_pose' else data['stamp_ns']
            if stamp not in scan_by_stamp:continue
            i=scan_by_stamp[stamp];tag=1 if kind=='lidar_pose' else 2
            stream.append((clock,tag,stamp,f'sensor_{i:05d}.txt' if tag==1 else f'cloud_{i:05d}.f32'))
    stream.sort(key=lambda row:row[0])
    (OUT/'stream.txt').write_text('\n'.join(' '.join(map(str,row)) for row in stream)+'\n')
    (OUT/'frames.txt').write_text('\n'.join(f"{f['index']} {f['query_ns']} {f['body_ns']} {f['cutoff_ns']}" for f in frames)+'\n')
    (OUT/'identity.json').write_text(json.dumps(dict(frames=frames,scans=len(scans),sources=capture.sources,
        scope='Full chronological published scan prefix; recorded snapshot cutoff and due body. Native DDS batching/asynchronous snapshot history is not exactly restored.'),indent=2)+'\n')
    print(json.dumps(dict(frames=len(frames),scans=len(scans),output=str(OUT))))

if __name__=='__main__': main()
