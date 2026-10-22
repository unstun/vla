from pathlib import Path
import os,json,math
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from shapely.geometry import Point
from mesh_geometry import MeshGeometry
B=Path('/data/sun/vla_mppi_20261009');m=MeshGeometry(np.fromfile(B/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3))
for x,y,g,yaw in [(-5.37023874109357,5.278340677155784,.19455200552940372,-1.8040617818620817),(-4.0323147888183595,-4.303810874938966,1.5830309104919433,math.pi/2)]:
 f,o=m.view(g);meta=m.obstacle_meta[round(g/m.height_quantum)];matches=[]
 for side in (-1,1):
  p=Point(x+side*.18*math.cos(yaw),y+side*.18*math.sin(yaw));d=np.array([a.distance(p) for a in o.geoms]);i=int(d.argmin());idx,lo,hi=meta[i];t=m.tri[idx];n=np.cross(t[1]-t[0],t[2]-t[0]);n/=np.linalg.norm(n)
  matches.append(dict(side=side,margin=d[i]-.35,tri_index=idx,triangle=t.tolist(),normal=n.tolist(),slab=[lo,hi],geometry=o.geoms[i].wkt))
 print(json.dumps(dict(pose=[x,y,g,yaw],floor_heights=m.heights(x,y),witnesses=matches)),flush=True)
