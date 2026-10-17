"""Independent continuous XY distance and identity checks on actual plugin outputs."""
from pathlib import Path
import csv,hashlib,json,math,sys
work=Path(sys.argv[1]);folder=work/'feedback_output'
read=lambda name:[[float(r[k]) for k in ('x','y','z','yaw')] for r in csv.DictReader((folder/(name+'.csv')).open())]
first=read('first');witness=first[len(first)//2]
def distance(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
    u=max(0.,min(1.,((witness[0]-a[0])*dx+(witness[1]-a[1])*dy)/den)) if den else 0.
    return math.hypot(a[0]+u*dx-witness[0],a[1]+u*dy-witness[1])
result={'physics_steps':0,'fixture':'fixed multilayer PCT bundle; typed mock wire provider; actual installed PCT plugin','native_provider_scope':'separate recorded-window typed LIVE/binary parity','blocked_disk_radius_m':.15,'witness_xyz_yaw':witness,'routes':{}}
for name in ('first','blocked','unknown','cleared','new_mission'):
    rows=read(name);path=folder/(name+'.csv')
    result['routes'][name]={'poses':len(rows),'min_xy_distance_m':min(distance(a,b) for a,b in zip(rows,rows[1:])),'length_m':sum(math.dist(a[:3],b[:3]) for a,b in zip(rows,rows[1:])),'canonical_goal_error_m':math.dist(rows[-1][:3],first[-1][:3]),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    if name in ('blocked','unknown'):assert result['routes'][name]['min_xy_distance_m']>=.15-1e-10
    if name in ('cleared','new_mission'):assert rows==first
(work/'feedback_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
