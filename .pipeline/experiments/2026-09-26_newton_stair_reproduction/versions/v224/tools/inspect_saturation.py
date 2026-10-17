from pathlib import Path
import csv,json
import numpy as np
from scipy.spatial import cKDTree
root=Path('/data/sun/vla_mppi_20261009');work=root/'environment_score_v224'
with (work/'fixtures/building/environment.env').open() as stream:
 header=stream.readline().split();n=int(stream.readline().split()[1]);floor=np.loadtxt([next(stream) for _ in range(n)])
 n=int(stream.readline().split()[1]);solid=np.loadtxt(stream)
rows=list(csv.DictReader((work/'field_probe_output/legacy_route.csv').open()))
cloud=np.fromfile(root/'stair_collision_replay_20261016/input/surface.f32',dtype='<f4').reshape(-1,4)
tree=cKDTree(solid);result=[]
for index in [0,100,500,1000,2000,3000]:
 r=rows[index];p=np.array([float(r[k]) for k in ('x','y','z')]);yaw=float(r['yaw']);direction=np.array([np.cos(yaw),np.sin(yaw),0]);best=(1e9,None)
 for sign in [-1,1]:
  center=p+sign*.18*direction;points=solid[tree.query_ball_point(center,1.)]
  radial=np.linalg.norm(points[:,:2]-center[:2],axis=1)-.35
  vertical=np.abs(points[:,2]-center[2]+.1)-.45
  d=np.hypot(np.maximum(radial,0),np.maximum(vertical,0))+np.minimum(np.maximum(radial,vertical),0)-np.sqrt(3)*.025
  i=np.argmin(d)
  if d[i]<best[0]:best=(d[i],points[i])
 witness=best[1];nearest=np.argsort(np.linalg.norm(cloud[:,:2]-witness[:2],axis=1))[:8]
 result.append({'pose':p.tolist(),'yaw':yaw,'margin':float(best[0]),'solid_witness':witness.tolist(),'near_surface_xyz_label':cloud[nearest].tolist()})
(work/'saturation_inspection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
