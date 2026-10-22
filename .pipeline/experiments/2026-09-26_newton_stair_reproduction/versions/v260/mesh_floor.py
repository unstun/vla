"""Finite original triangle raster, independent of tomogram cost and slice cuts."""
import math,numpy as np

def mesh_floors(triangles,res,ox,oy,body_top=.65):
 tri=np.asarray(triangles,dtype=float)
 n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);scale=np.maximum(np.linalg.norm(n,axis=1),1e-30)
 upward=n[:,2]/scale>32*np.finfo(np.float32).eps
 hits={};up={};eps=1e-5
 for i,t in enumerate(tri):
  a=t[0];u=t[1]-a;v=t[2]-a;det=u[0]*v[1]-u[1]*v[0]
  if abs(det)<1e-14:continue
  lo=np.ceil((t[:,:2].min(axis=0)-[ox,oy])/res-.5-1e-9).astype(int)
  hi=np.floor((t[:,:2].max(axis=0)-[ox,oy])/res-.5+1e-9).astype(int)
  for ix in range(lo[0],hi[0]+1):
   x=ox+(ix+.5)*res
   for iy in range(lo[1],hi[1]+1):
    y=oy+(iy+.5)*res;uu=((x-a[0])*v[1]-(y-a[1])*v[0])/det;vv=(u[0]*(y-a[1])-u[1]*(x-a[0]))/det
    if uu< -1e-9 or vv< -1e-9 or uu+vv>1+1e-9:continue
    z=float(a[2]+uu*u[2]+vv*v[2]);hits.setdefault((ix,iy),[]).append(z)
    if upward[i]:up.setdefault((ix,iy),[]).append(z)
 records=[]
 for key,zs in sorted(up.items()):
  previous=-math.inf
  for z in sorted(zs):
   if z-previous<eps:continue
   previous=z;above=[h for h in hits[key] if h>z+eps]
   headroom=min(above)-z if above else math.inf
   records.append((*key,z,headroom,headroom>body_top))
 return records
