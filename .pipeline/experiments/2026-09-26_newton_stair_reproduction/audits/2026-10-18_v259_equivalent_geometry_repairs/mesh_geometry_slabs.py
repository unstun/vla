"""Independent original-triangle geometric oracle for benchmark certificates.

Floor presence is obtained from original upward faces, never PCT costs or route
scores. Associated near-height floor material is exempted below its actual
surface; walls/columns above it remain body solids. The result is conservative:
sloping floor caps use their minimum height, and cached height bands shrink
support / enlarge body coverage. This is an offline witness oracle, not another
runtime traversal rule or a dynamics/leg-contact certificate.
"""
from mesh_floor_connectivity import FloorConnectivity
from pathlib import Path
import hashlib,math,time
import numpy as np
from shapely.geometry import Point,Polygon,LineString,GeometryCollection,MultiPoint
from shapely import union_all, difference,STRtree
def unary_union(parts):return union_all(parts,grid_size=1e-8)
def clip(poly,z,above):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  inside_a=a[2]>=z if above else a[2]<=z;inside_b=b[2]>=z if above else b[2]<=z
  if inside_a:out.append(a)
  if inside_a!=inside_b:out.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
 return out
def projection(poly):
 if not poly:return GeometryCollection()
 q=np.asarray(poly)[:,:2]
 return MultiPoint(q).convex_hull
class MeshGeometry:
 def __init__(self,triangles,radius=.35,offset=.18,clearance=.3,up=.55,down=.35,step=.26,tolerance=.12):
  self.tri=np.asarray(triangles,dtype=float);n=np.cross(self.tri[:,1]-self.tri[:,0],self.tri[:,2]-self.tri[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-30)
  self.upward=n[:,2]>32*np.finfo(np.float32).eps
  self.low=self.tri.min(axis=1);self.high=self.tri.max(axis=1)
  self.radius=radius;self.offset=offset;self.clearance=clearance;self.up=up;self.down=down;self.step=step;self.tolerance=tolerance
  self.floor_connectivity=FloorConnectivity(self.tri,self.upward,step)
  self.views={};self.obstacle_meta={};self.trees={};self.height_quantum=.005;self.eps=1e-7;self.height_queries={}
 def heights(self,x,y):
  key=(float(x),float(y))
  if key in self.height_queries:return self.height_queries[key]
  selected=self.upward&(self.low[:,0]<=x+self.eps)&(self.high[:,0]>=x-self.eps)&(self.low[:,1]<=y+self.eps)&(self.high[:,1]>=y-self.eps)
  t=self.tri[selected];a=t[:,0];u=t[:,1]-a;v=t[:,2]-a;det=u[:,0]*v[:,1]-u[:,1]*v[:,0];good=abs(det)>1e-15
  uu=np.zeros(len(t));vv=uu.copy();uu[good]=((x-a[good,0])*v[good,1]-(y-a[good,1])*v[good,0])/det[good];vv[good]=(u[good,0]*(y-a[good,1])-u[good,1]*(x-a[good,0]))/det[good]
  hit=good&(uu>=-1e-9)&(vv>=-1e-9)&(uu+vv<=1+1e-9)
  z=np.sort((a[:,2]+uu*u[:,2]+vv*v[:,2])[hit]);out=[]
  for h in z:
   if not out or abs(h-out[-1])>1e-6:out.append(float(h))
  self.height_queries[key]=out;return out
 def view(self,ground):
  key=round(float(ground)/self.height_quantum)
  if key in self.views:return self.views[key]
  started=time.monotonic();g=key*self.height_quantum;half=self.height_quantum*.500001
  floor_low=g-self.step+half+self.eps;floor_high=g+self.step-half-self.eps
  bottom=g+self.clearance-self.up-half;top=g+self.clearance+self.down+half
  floor=[];caps=[]
  for i in np.flatnonzero(self.upward&(self.high[:,2]>=floor_low)&(self.low[:,2]<=floor_high)):
   p=clip(list(self.tri[i]),floor_low,True)
   if p:p=clip(p,floor_high,False)
   q=projection(p)
   if q.area>1e-12:floor.append(q);caps.append(p)
  support=unary_union(floor)
  if support.is_empty:result=(support,GeometryCollection());self.views[key]=result;return result
  events=sorted(set([bottom,top]+[v[2] for p in caps for v in p if bottom<v[2]<top]+[h for h in (floor_low,floor_high) if bottom<h<top]))
  obstacles=[];metadata=[]
  for lo,hi in zip(events,events[1:]):
   cap_parts=[projection(clip(p,hi,True)) for p in caps]
   covered=unary_union([p for p in cap_parts if p.area>1e-12])
   ids=np.flatnonzero((self.high[:,2]>=lo)&(self.low[:,2]<=hi))
   for i in ids:
    if self.upward[i] and lo>=floor_low and hi<=floor_high:continue
    # Complete near-floor step material, not a clipped slice of a tall wall.
    if self.low[i,2]>=floor_low and self.high[i,2]<=floor_high:continue
    p=clip(list(self.tri[i]),lo,True)
    if p:p=clip(p,hi,False)
    q=projection(p)
    if not q.is_empty:
     if not covered.is_empty:q=difference(q,covered,grid_size=1e-8)
     if not q.is_empty:obstacles.append(q);metadata.append((int(i),lo,hi))
  obstacle=GeometryCollection(obstacles)  # Distance equals minimum over pieces, without mixed-dimension noding.
  result=(support,obstacle);self.views[key]=result;self.obstacle_meta[key]=metadata;self.trees[key]=STRtree(obstacles)
  print(f'MESH_VIEW ground={g:.4f} caps={len(caps)} slabs={len(events)-1} wall_s={time.monotonic()-started:.3f}',flush=True)
  return result
 def pose(self,x,y,ground,yaw):
  heights=self.heights(x,y)
  if not heights or min(abs(z-ground) for z in heights)>=self.tolerance-self.eps:return False,-math.inf,-math.inf,'body_height'
  _,obstacles=self.view(ground);floor=self.floor_connectivity.floor(x,y,ground,self.radius+self.offset,self.tolerance);edge=solid=math.inf
  for side in (-1,1):
   p=Point(x+side*self.offset*math.cos(yaw),y+side*self.offset*math.sin(yaw))
   if not floor.covers(p):return False,-math.inf,-math.inf,'missing_floor'
   edge=min(edge,floor.boundary.distance(p)-self.radius-2*self.floor_connectivity.eps)
   if not obstacles.is_empty:
    tree=self.trees[round(float(ground)/self.height_quantum)];nearest=tree.geometries[tree.nearest(p)]
    solid=min(solid,nearest.distance(p)-self.radius)
  return edge>self.eps and solid>self.eps,edge,solid,'free' if edge>self.eps and solid>self.eps else 'floor_edge' if edge<=self.eps else 'body_solid'
 def edge(self,a,b):
  # Samples use the same declared .025m/.05rad resolution, independently
  # computed from original mesh geometry and actual continuous endpoint poses.
  a=np.asarray(a,float);b=np.asarray(b,float);angle=math.remainder(b[3]-a[3],2*math.pi)
  if abs(b[2]-a[2])>=self.step:return False,[]
  n=max(1,math.ceil(np.linalg.norm(b[:3]-a[:3])/.025),math.ceil(abs(angle)/.05));samples=[]
  for i in range(n+1):
   u=i/n;p=a+u*(b-a);p[3]=a[3]+u*angle
   result=self.pose(*p);samples.append([*map(float,p),*result[:3],result[3]])
   if not result[0]:return False,samples
  return True,samples
