"""Independent original-mesh SE(2) witness search, never used by runtime PCT.

No planner admission results enter graph construction. All transitions carry
sampled original-mesh pose checks; start/goal XYZ and yaw remain exact. This is
geometric reachability under the declared body/step model, not an RL guarantee.
"""
from pathlib import Path
import heapq,math,time,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from mesh_geometry import MeshGeometry
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'versions/v260'))
from mesh_floor import mesh_floors
class MeshRouteCertificate:
 def __init__(self,tri,res=.2,ox=-7.9953147888183604,oy=-9.6368112564086914):
  self.mesh=MeshGeometry(tri);self.res=res;self.ox=ox;self.oy=oy;self.cells={};self.states={};self.edges={};self.pose_queries=0
  for ix,iy,z,headroom,clear in mesh_floors(tri,res,ox,oy):
   if clear and -.5<z<5.5:self.cells.setdefault((ix,iy),[]).append(float(z))
  self.directions=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
 def pose(self,key):
  x,y,l,h=key;return np.array([self.ox+(x+.5)*self.res,self.oy+(y+.5)*self.res,self.cells[x,y][l],h*math.pi/4])
 def free(self,key):
  if key not in self.states:self.states[key]=self.mesh.pose(*self.pose(key));self.pose_queries+=1
  return self.states[key][0]
 def edge(self,a,b):
  key=tuple(sorted((a,b)))
  if key in self.edges:return self.edges[key]
  ok=self.free(a) and self.free(b)
  if ok:ok=self.mesh.edge(self.pose(a),self.pose(b))[0]
  self.edges[key]=ok;return ok
 def near(self,p):
  ix=math.floor((p[0]-self.ox)/self.res);iy=math.floor((p[1]-self.oy)/self.res)
  for x in range(ix-1,ix+2):
   for y in range(iy-1,iy+2):
    for l,z in enumerate(self.cells.get((x,y),[])):
     if abs(z-p[2])>=.26:continue
     for h in range(8):
      k=(x,y,l,h)
      if self.free(k) and self.mesh.edge(p,self.pose(k))[0]:yield k
 def neighbours(self,k):
  x,y,l,h=k
  yield x,y,l,(h-1)%8
  yield x,y,l,(h+1)%8
  dx,dy=self.directions[h]
  for side in (-1,1):
   a,b=x+side*dx,y+side*dy
   for j,z in enumerate(self.cells.get((a,b),[])):
    if abs(z-self.cells[x,y][l])<.26:yield a,b,j,h
 def search(self,start,goal,budget=200000):
  started=time.monotonic();start=np.array(start,float);goal=np.array(goal,float)
  if not self.mesh.pose(*start)[0] or not self.mesh.pose(*goal)[0]:return dict(certified=False,reason='endpoint_mesh_pose',start=list(start),goal=list(goal))
  initial=list(self.near(start));terminal=set(self.near(goal));frontier=[];dist={};parent={};seen=set()
  for k in initial:dist[k]=float(np.linalg.norm(self.pose(k)[:3]-start[:3]));parent[k]=None;heapq.heappush(frontier,(dist[k]+np.linalg.norm(self.pose(k)[:3]-goal[:3]),k))
  end=None
  while frontier and len(seen)<budget:
   _,k=heapq.heappop(frontier)
   if k in seen:continue
   seen.add(k)
   if k in terminal:end=k;break
   for n in self.neighbours(k):
    if n in seen or not self.edge(k,n):continue
    p=self.pose(k);q=self.pose(n);step=float(np.linalg.norm(q[:3]-p[:3]))+.18*abs(math.remainder(q[3]-p[3],2*math.pi));d=dist[k]+step
    if d<dist.get(n,math.inf):dist[n]=d;parent[n]=k;heapq.heappush(frontier,(d+np.linalg.norm(q[:3]-goal[:3]),n))
   if len(seen)%1000==0:print('MESH_SEARCH',len(seen),'pose_queries',self.pose_queries,'wall_s',time.monotonic()-started,flush=True)
  if end is None:return dict(certified=False,reason='mesh_graph_exhausted' if not frontier else 'mesh_graph_budget',visited=len(seen),wall_s=time.monotonic()-started)
  keys=[]
  while end is not None:keys.append(end);end=parent[end]
  path=[start]+[self.pose(k) for k in keys[::-1]]+[goal];witness=[];edge=solid=math.inf
  for a,b in zip(path,path[1:]):
   ok,samples=self.mesh.edge(a,b)
   if not ok:raise RuntimeError('Mesh witness replay disagrees')
   witness.extend(samples);edge=min(edge,min(s[5] for s in samples));solid=min(solid,min(s[6] for s in samples))
  return dict(certified=True,source='original Newton triangles only',visited=len(seen),wall_s=time.monotonic()-started,min_edge_margin=edge,min_solid_margin=solid,path=[p.tolist() for p in path],samples=witness)
if __name__=='__main__':
 B=Path('/data/sun/vla_mppi_20261009');m=MeshRouteCertificate(np.fromfile(B/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3))
 cases=json.loads((B/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v257/cases_manifest.json').read_text())['cases'];out=B/'generic_mechanisms_v261/mesh_certificates';out.mkdir(parents=True,exist_ok=True)
 for cid in sys.argv[1:] or ['A04','G05']:
  c=next(c for c in cases if c['case_id']==cid);start=c['start']['ground']+[c['start']['yaw']];goal=c['goal']['ground']+[c['goal']['yaw']];r=m.search(start,goal);(out/(cid+'.json')).write_text(json.dumps(r,indent=2)+'\n');print('CERT',cid,{k:v for k,v in r.items() if k not in ('path','samples')},flush=True)
