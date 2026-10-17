"""Replay actual logged initializer rejection queries, including their query yaw."""
import json
import re
import zipfile
from pathlib import Path
from prepare_inputs import numbers, RUN

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
out=ROOT/'critical_input'
out.mkdir(exist_ok=True)
for p in (ROOT/'input').iterdir():
    if p.name.startswith(('cloud_','body_','sensor_')) or p.name in ('scans.txt','navigation.f32','surface.f32','physical_floor.f32','support_gap.txt','planner.yaml'):
        link=out/p.name
        if link.is_symlink():link.unlink()
        link.symlink_to(Path('../input')/p.name)
with zipfile.ZipFile(RUN/'raw_capture.zip') as z:lines=z.read('nav2.log').decode().splitlines()
sensors=json.loads((RUN/'sensor_manifest.json').read_text())
rows=[];frames=[];latest_cloud=None;next_time=47.8
pattern=r'initial_spline_collision pos=\(([^)]+)\) yaw=([^ ]+) body=\(([^)]+)\) body_q=\(([^)]+)\) body_stamp=([^ ]+) now=([^ ]+)'
for li,line in enumerate(lines):
    m=re.search(r'V82_MAP_SNAPSHOT .*cloud_stamp=([0-9.]+)',line)
    if m:latest_cloud=float(m[1])
    m=re.search(pattern,line)
    if not m:continue
    pos,yaw,body,q,stamp,now=m.groups();now=float(now)
    if now<next_time or now>61.95:continue
    next_time=now+1
    p=[float(x) for x in pos.split(',')];b=[float(x) for x in body.split(',')];w,x,y,z=[float(x) for x in q.split(',')]
    sensor=min(sensors,key=lambda s:abs(s['sim_time_s']-latest_cloud))
    assert abs(sensor['sim_time_s']-latest_cloud)<1.1e-6
    i=len(rows)
    (out/f'query_body_{i:04d}.txt').write_text(numbers([*b,x,y,z,w])+'\n')
    (out/f'queries_{i:04d}.txt').write_text(numbers([0,4,*p,float(yaw)])+'\n')
    frames.append(f"{i} {round(now*1e9)} {round(float(stamp)*1e9)} {sensor['stamp_ns']} query_body_{i:04d}.txt queries_{i:04d}.txt")
    rows.append(dict(frame=i,time_s=now,body=b,query=p,query_yaw=float(yaw),cloud_ns=sensor['stamp_ns'],log_line=li+1,text=line))
assert len(rows)>2
(out/'frames.txt').write_text('\n'.join(frames)+'\n')
(out/'identity.json').write_text(json.dumps({'frames':rows,'coordinate_precision_m':1e-8,'time_precision_s':1e-8,'scope':'Exact logged rejection queries, original printed precision; same source cloud prefix.'},indent=2)+'\n')
print(json.dumps(rows),flush=True)
