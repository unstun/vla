"""Spatial construction from original selected physical floors; no route solver."""
from pathlib import Path
import hashlib,json,math,shlex
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257';WORK=BASE/'generic_mechanisms_v256/native'
OUT.mkdir(exist_ok=True);D=OUT/'discovery';D.mkdir(exist_ok=True)
p=WORK/'fixtures/building/native.support';rows=p.read_text().splitlines();h=shlex.split(rows[0]);res=float(h[1]);ox=float(h[2]);oy=float(h[3]);clearance=float(h[7]);assert res==.1 and clearance==.3
poses=[];seen=set()
for line in rows[1:]:
 ix,iy,z,raw,scored=line.split();ix=int(ix);iy=int(iy);z=float(z)
 if scored!='1':continue
 # Half-metre lattice, all actual selected levels below the second floor.
 if ix%5 or iy%5 or z>4.65:continue
 x=ox+(ix+.5)*res+.013;y=oy+(iy+.5)*res-.017
 key=(round(x,6),round(y,6),round(z,6))
 if key in seen:continue
 seen.add(key)
 for k in range(8):
  yaw=-math.pi+k*math.pi/4;poses.append(dict(id=f'P{len(poses):05d}',ground=[x,y,z],yaw=yaw))
(D/'candidates.json').write_text(json.dumps(poses,indent=2)+'\n')
(D/'poses.txt').write_text(''.join(r['id']+' '+' '.join(map(str,r['ground'][:2]+[r['ground'][2]+.3,r['yaw']]))+'\n' for r in poses))
(D/'construction.json').write_text(json.dumps(dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),candidates=len(poses),spatial_poses=len(seen),grid_step_m=.5,continuous_offsets_m=[.013,-.017],route_solver_used=False),indent=2)+'\n')
print(len(poses),len(seen))
