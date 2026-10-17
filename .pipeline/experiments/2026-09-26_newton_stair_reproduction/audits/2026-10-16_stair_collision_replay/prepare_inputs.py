"""Extract exact archived inputs; no simulator or planner is executed."""
from pathlib import Path
import argparse
import bisect
import hashlib
import io
import json
import re
import shutil
import zipfile
import numpy as np

TASK = Path('/data/sun/vla_mppi_20261009')
RUN = TASK/'trials/v217_linux_full_attempt01/runs/v217_linux_full_attempt01'
TERRAIN = TASK/'starvation_recovery_v219/fixtures/building'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def numbers(values):
    return ' '.join(format(float(x), '.17g') for x in values)


def sensor_pose(row, optical=False):
    d = row['body_sensor']
    p = d['sensor_position' if optical else 'position']
    w, x, y, z = d['sensor_quaternion' if optical else 'quaternion']
    return numbers([*p, x, y, z, w])+'\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    archive = zipfile.ZipFile(RUN/'raw_capture.zip')
    raw_index = json.loads((RUN/'raw_capture_manifest.json').read_text())['members']
    source_hashes = {}

    def read(name):
        f = RUN/name
        data = f.read_bytes() if f.is_file() else archive.read(name)
        if name in raw_index:
            assert sha(data) == raw_index[name]['sha256'], name
        source_hashes[name] = sha(data)
        return data

    events = [json.loads(x) for x in read('artifacts/reactive_observations.jsonl').splitlines()]
    routes = [x for x in events if x['event'] == 'pct_route']
    bodies = [x for x in events if x['event'] == 'body_pose_observer']
    route_times = [x['clock_ns'] for x in routes]
    body_times = [x['clock_ns'] for x in bodies]
    sensors = json.loads((RUN/'sensor_manifest.json').read_text())
    audit = [json.loads(x) for x in read('bridge_scan_audit.jsonl').splitlines()]
    published = {x['timestamp_ns'] for x in audit if x['outcome'] == 'published_sequentially'}
    log = read('nav2.log').decode().splitlines()
    frames = []
    latest_cloud = None
    latest_seed = None
    latest_curve = None
    next_frame = 42.0
    interesting = []
    for line_index, line in enumerate(log):
        match = re.search(r'V82_MAP_SNAPSHOT .*cloud_stamp=([0-9.]+)', line)
        if match:
            latest_cloud = float(match[1])
        if 'spline_seed_capture {' in line:
            try:
                latest_seed = json.loads(line.split('spline_seed_capture ', 1)[1])
            except ValueError:
                pass
        if 'spline_curve_capture {' in line:
            try:
                latest_curve = json.loads(line.split('spline_curve_capture ', 1)[1])
            except ValueError:
                pass
        m = re.search(r'nominal_replan .*ros_s=([0-9.]+)', line)
        if m:
            t = float(m[1])
            if t >= next_frame and t <= 62.0 and latest_cloud is not None:
                ns = round(t*1e9)
                bi = bisect.bisect_right(body_times, ns)-1
                ri = bisect.bisect_right(route_times, ns)-1
                assert bi >= 0 and ri >= 0
                last = min(sensors, key=lambda x: abs(x['sim_time_s']-latest_cloud))
                assert abs(last['sim_time_s']-latest_cloud) < 1.1e-6
                frames.append(dict(index=len(frames), time_s=t, query_ns=ns,
                    last_cloud_stamp_ns=last['stamp_ns'], cloud_file=last['file'],
                    route_index=ri, body_event=bodies[bi], route=routes[ri],
                    last_seed=latest_seed, last_curve=latest_curve, log_line=line_index+1))
                next_frame = t+.195
        if frames and 42.0 <= frames[-1]['time_s'] <= 62.0 and any(k in line.lower() for k in
            ['initial_spline','first three','control points','reference_prefix','local_trajectory_starvation','reactive_collision_blocked']):
            interesting.append({'last_frame_s':frames[-1]['time_s'],'line':line_index+1,'text':line})
    assert len(frames) >= 40, (len(frames), latest_cloud)
    selected = [s for s in sensors if s['stamp_ns'] <= frames[-1]['last_cloud_stamp_ns'] and s['stamp_ns'] in published]
    listing = []
    for i, s in enumerate(selected):
        data = read(s['file'])
        assert sha(data) == s['sha256']
        points = np.asarray(np.load(io.BytesIO(data), allow_pickle=False)['sensor_points'],dtype='<f4')
        assert points.shape == (s['sensor']['point_count'], 3)
        (out/f'cloud_{i:05d}.f32').write_bytes(points.tobytes())
        (out/f'body_{i:05d}.txt').write_text(sensor_pose(s))
        (out/f'sensor_{i:05d}.txt').write_text(sensor_pose(s,True))
        listing.append(f"{i} {s['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
    (out/'scans.txt').write_text('\n'.join(listing)+'\n')
    terrain = json.loads((TERRAIN/'terrain.json').read_text())
    for role in ('navigation','surface','physical_floor'):
        entry = terrain['clouds'][role]
        data = (TERRAIN/entry['file']).read_bytes()
        assert sha(data) == entry['sha256']
        (out/(role+'.f32')).write_bytes(data)
    (out/'terrain.json').write_text(json.dumps(terrain,indent=2)+'\n')
    shutil.copyfile(TERRAIN/'support_gap.txt',out/'support_gap.txt')
    shutil.copyfile(RUN/'planner.yaml',out/'planner.yaml')
    surface = np.fromfile(out/'surface.f32',dtype='<f4').reshape(-1,4)
    roi = surface[(surface[:,0]>5.5)&(surface[:,0]<10.0)&(surface[:,1]>-6)&(surface[:,1]<-2)&(surface[:,2]>.8)&(surface[:,2]<2.9)]
    frame_list=[]
    for f in frames:
        i=f['index'];body=f['body_event']['data'];p=body['pose']['pose']['position'];q=body['pose']['pose']['orientation']
        bp=np.array([p[k] for k in ('x','y','z')]);yaw=float(np.arctan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)))
        bn=body['header']['stamp']['sec']*10**9+body['header']['stamp']['nanosec']
        assert 0<=f['query_ns']-bn<=100000000
        (out/f'query_body_{i:04d}.txt').write_text(numbers([*bp,*[q[k] for k in ('x','y','z','w')]])+'\n')
        route=np.array([[x['pose']['position'][k] for k in ('x','y','z')] for x in f['route']['data']['poses']])
        np.save(out/f'route_{i:04d}.npy',route)
        queries=[(0,0,*bp,yaw)]
        idx=int(np.argmin(np.linalg.norm(route-bp,axis=1)))
        lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(route[idx:],axis=0),axis=1))]
        for point in route[idx:][lengths<=3.5]:queries.append((len(queries),1,*point,yaw))
        # Field is explicitly a sampled surface at the current measured yaw.
        for point in roi:
            if abs(point[2]-.03-(bp[2]-.30))>.55:continue
            queries.append((len(queries),2,float(point[0]),float(point[1]),float(point[2]-.03+.35),yaw))
        seed=f.get('last_seed')
        if isinstance(seed,dict):
            for point in seed.get('points',[]):
                if len(point)==3 and np.linalg.norm(np.asarray(point)-bp)<4:
                    queries.append((len(queries),3,*point,yaw))
        (out/f'queries_{i:04d}.txt').write_text('\n'.join(numbers(x) for x in queries)+'\n')
        frame_list.append(f"{i} {f['query_ns']} {bn} {f['last_cloud_stamp_ns']} query_body_{i:04d}.txt queries_{i:04d}.txt")
        f.update(body_xyz=bp.tolist(),body_yaw=yaw,body_stamp_ns=bn,queries=len(queries))
    (out/'frames.txt').write_text('\n'.join(frame_list)+'\n')
    (out/'frames.json').write_text(json.dumps(frames,indent=2)+'\n')
    (out/'rejection_log.json').write_text(json.dumps(interesting,indent=2)+'\n')
    result={'run':RUN.name,'frames':len(frames),'scans':len(selected),
        'time_range':[frames[0]['time_s'],frames[-1]['time_s']], 'source_hashes':source_hashes,
        'files':{p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()},
        'scope':'Identical recorded sensors, due body/reference and original snapshot source-stamp cutoff; ordered map reconstruction, not asynchronous schedule restoration.'}
    (out/'identity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('run','frames','scans','time_range')}),flush=True)


if __name__=='__main__':main()
