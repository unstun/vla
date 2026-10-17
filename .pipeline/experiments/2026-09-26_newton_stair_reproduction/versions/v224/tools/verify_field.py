"""Independent unpartitioned SciPy/numpy oracle for real-map shared score outputs."""
from pathlib import Path
import csv,json,hashlib,sys
import numpy as np
from scipy.spatial import cKDTree
work=Path('/data/sun/vla_mppi_20261009/environment_score_v224')
path=work/'fixtures/building/environment03.env'
with path.open() as stream:
 h=next(stream).split();assert h[0]=='ENV224B'
 res,ox,oy,radius,offset,up,down,clearance,target,half=map(float,h[1:])
 n=int(next(stream).split()[1]);floor=np.loadtxt([next(stream) for _ in range(n)])
 n=int(next(stream).split()[1]);solid=np.loadtxt(stream);assert len(solid)==n
cells={}
for x,y,z,edge,terrain in floor:cells.setdefault((int(x),int(y)),[]).append((z,edge,terrain))
points=solid[:,:3].astype(np.float32).astype(float);tree=cKDTree(points)

def sample_floor(x,y,z):
 gx=(x-ox)/res-.5;gy=(y-oy)/res-.5;ix=int(np.floor(gx));iy=int(np.floor(gy));edge=terrain=0.
 for dx in (0,1):
  for dy in (0,1):
   w=(gx-ix if dx else 1-gx+ix)*(gy-iy if dy else 1-gy+iy)
   if w<1e-12:continue
   values=cells.get((ix+dx,iy+dy),[]);candidates=sorted((abs(a-z),b,c) for a,b,c in values)
   if not candidates or candidates[0][0]>.260000001 or (len(candidates)>1 and abs(candidates[0][0]-candidates[1][0])<=1e-9):terrain+=w
   else:edge+=w*candidates[0][1];terrain+=w*candidates[0][2]
 return edge,terrain

def oracle(p,yaw):
 edge=solid_margin=target;terrain=0.;direction=np.array([np.cos(yaw),np.sin(yaw),0.])
 for sign in (-1,1):
  center=p+sign*offset*direction;e,t=sample_floor(*center[:2],p[2]-clearance)
  edge=min(edge,e-radius);terrain=max(terrain,t)
  middle=center+np.array([0,0,(down-up)/2]);reach=np.hypot(radius,(up+down)/2)+target+np.sqrt(3)*half
  ids=np.array(tree.query_ball_point(middle,reach+1e-6),dtype=int)
  if not len(ids):continue
  ground=p[2]-clearance
  skip=(solid[ids,3]>-1e90)&(abs(solid[ids,3]-ground)<.26)&(abs(solid[ids,4]-ground)<.26)
  q=points[ids[~skip]]
  if not len(q):continue
  radial=np.linalg.norm(q[:,:2]-center[:2],axis=1)-radius
  vertical=abs(q[:,2]-middle[2])-(up+down)/2
  distances=np.hypot(np.maximum(radial,0),np.maximum(vertical,0))+np.minimum(np.maximum(radial,vertical),0)-np.sqrt(3)*half
  solid_margin=min(solid_margin,float(distances.min()))
 cost=np.clip((target-edge)/target,0,1)**2+np.clip((target-solid_margin)/target,0,1)**2+.25*terrain**2
 return np.array([edge,solid_margin,cost])
maximum=0.;count=0;bad=[]
directory=work/(sys.argv[1] if len(sys.argv)>1 else 'field_probe_output06')
names=['legacy_graph.csv','shared_graph.csv','legacy_route.csv','shared_route.csv']
for name in names:
 rows=list(csv.DictReader((directory/name).open()))
 for i in np.linspace(0,len(rows)-1,160,dtype=int):
  r=rows[i];p=np.array([float(r[k]) for k in ['x','y','z']]);actual=np.array([float(r[k]) for k in ['edge_margin','solid_margin','cost']])
  expected=oracle(p,float(r['yaw']));error=float(np.max(abs(actual-expected)));maximum=max(maximum,error);count+=1
  if error>1e-5:bad.append({'file':name,'row':int(i),'actual':actual.tolist(),'expected':expected.tolist()})
result={'oracle':'independent unpartitioned scipy cKDTree and numpy geometry','samples':count,'maximum_absolute_error':maximum,'mismatches':bad,'tolerance':1e-5,'field_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'physics_steps':0,
 'input_directory':str(directory),'input_sha256':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in names}}
(work/'field_oracle_final.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not bad
