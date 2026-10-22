"""Finite local data selection for the frozen independent Python geometry.

The query pose and height remain unchanged. Trim source triangles only outside
a tile expanded beyond both cylinders plus the reported 0.15m margin cap.
All vertical intersections over the real cylinder axes remain present. This
avoids a global polygon overlay for every distinct continuous ground height.
"""
import math
import numpy as np
from shapely.geometry import box
from surface_model import SurfaceModel,clip

class LocalReference:
    def __init__(self,triangles):
        self.source=SurfaceModel(triangles);self.tiles={}
    def assess(self,x,y,ground,yaw,check_support=False):
        if check_support:raise ValueError('Local reference certifies capped solids only')
        pitch=2.;key=(math.floor(x/pitch),math.floor(y/pitch))
        if key not in self.tiles:
            reach=.35+.18+.15+1e-8
            lo=np.array(key)*pitch-reach;hi=(np.array(key)+1)*pitch+reach
            ids=self.source.tree.query(box(*lo,*hi));parts=[]
            for i in np.sort(ids):
                p=list(self.source.tri[i])
                for n,d in (([1,0,0],hi[0]),([-1,0,0],-lo[0]),([0,1,0],hi[1]),([0,-1,0],-lo[1])):
                    p=clip(p,np.array(n,float),d)
                    if not p:break
                for j in range(1,len(p)-1):
                    t=np.array([p[0],p[j],p[j+1]])
                    if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-20:parts.append(t)
            self.tiles[key]=SurfaceModel(np.asarray(parts).reshape(-1,3,3))
        return self.tiles[key].assess(x,y,ground,yaw,check_support=False)
