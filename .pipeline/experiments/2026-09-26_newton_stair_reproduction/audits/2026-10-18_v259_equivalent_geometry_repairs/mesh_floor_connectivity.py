"""Original finite upward-face portals; step adjacency is local and symmetric."""
import math,numpy as np
from shapely import STRtree,union_all,get_coordinates
from shapely.geometry import Polygon,box,Point
from shapely.ops import nearest_points
class FloorConnectivity:
 def __init__(self,tri,upward,step=.26):
  self.tri=tri[np.flatnonzero(upward)];self.polygons=[Polygon(t[:,:2]) for t in self.tri]
  self.tree=STRtree(self.polygons);self.step=step;self.eps=1e-5;self.graph=[[] for p in self.polygons];self.cache={}
  self.planes=[]
  for t in self.tri:self.planes.append(np.linalg.solve(np.c_[t[:,:2],np.ones(3)],t[:,2]))
  for i,p in enumerate(self.polygons):
   for j in self.tree.query(p.buffer(self.eps)):
    j=int(j)
    if j<=i:continue
    q=self.polygons[j];portal=p.intersection(q)
    if portal.is_empty:
     if p.distance(q)>self.eps:continue
     a,b=nearest_points(p,q);portal=a
    xy=get_coordinates(portal)
    d=np.c_[xy,np.ones(len(xy))]@(self.planes[i]-self.planes[j])
    if d.min()>=step-self.eps or d.max()<=-step+self.eps:continue
    self.graph[i].append((j,portal));self.graph[j].append((i,portal))
 def floor(self,x,y,ground,reach=.53,tolerance=.12):
  # Expanded cell box keeps cache conservative with respect to local reach;
  # it certifies geometric support connectivity, not future leg placements.
  ix=math.floor(x/.1);iy=math.floor(y/.1)
  roi=box(ix*.1-reach,iy*.1-reach,(ix+1)*.1+reach,(iy+1)*.1+reach)
  p=Point(x,y)
  near=self.tree.query(box(x-self.eps,y-self.eps,x+self.eps,y+self.eps))
  roots={int(i) for i in near if self.polygons[int(i)].distance(p)<=self.eps and abs(np.array([x,y,1.])@self.planes[int(i)]-ground)<tolerance-self.eps}
  key=(ix,iy,tuple(sorted(roots)))
  if key in self.cache:return self.cache[key]
  ids=set(map(int,self.tree.query(roi,predicate='intersects')))
  visited=set(roots);todo=list(roots)
  while todo:
   i=todo.pop()
   for j,portal in self.graph[i]:
    if j in ids and j not in visited and portal.intersects(roi):visited.add(j);todo.append(j)
  floor=union_all([self.polygons[i] for i in visited],grid_size=1e-8).buffer(self.eps)
  self.cache[key]=floor;return floor
