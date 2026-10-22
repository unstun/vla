"""Exact local evaluation of the frozen v266 finite geometry predicate.

Uses GEOS projection/intersection/distance and the frozen independent clipper;
no Boost, native query code, cell-centre substitution or global polygon overlay.
"""
import math
import numpy as np
from shapely.geometry import Point,box
from surface_model import SurfaceModel,clip,projected,remove_cap,cap_halfspaces,EPS

class DirectReference:
    def __init__(self,triangles):self.source=SurfaceModel(triangles)
    def assess(self,x,y,ground,yaw,check_support=False):
        if check_support:raise ValueError('Capped solid reference only')
        s=self.source;zlo=ground+.3-.55;zhi=ground+.3+.35;answer=.15
        for side in (-1,1):
            cx=x+side*.18*math.cos(yaw);cy=y+side*.18*math.sin(yaw);c=Point(cx,cy);reach=.5
            roi=box(cx-reach,cy-reach,cx+reach,cy+reach)
            ids=np.sort(s.tree.query(roi));caps=[]
            for i in ids:
                if not s.upward[i] or s.high[i,2]<=ground-.26 or s.low[i,2]>=ground+.26:continue
                p=clip(list(s.tri[i]),np.array([0.,0.,-1.]),-(ground-.26));p=clip(p,np.array([0.,0.,1.]),ground+.26)
                q=projected(p)
                if q.area>EPS:caps.append((q,cap_halfspaces(p,s.tri[i])))
            for i in ids:
                if s.high[i,2]<zlo or s.low[i,2]>zhi:continue
                p=list(s.tri[i])
                for n,d in (([1,0,0],cx+reach),([-1,0,0],-(cx-reach)),([0,1,0],cy+reach),([0,-1,0],-(cy-reach)),([0,0,1],zhi),([0,0,-1],-zlo)):
                    p=clip(p,np.array(n,float),d)
                    if not p:break
                if not p:continue
                parts=[p]
                for q,planes in caps:
                    parts=[after for before in parts for after in (remove_cap(before,planes) if projected(before).intersects(q) else [before])]
                    if not parts:break
                for part in parts:answer=min(answer,projected(part).distance(c)-.35)
                if answer<=-.35:return dict(solid=-.35)
            if s.occupied_axis_interval(cx,cy,ground,dict(zlo=zlo,zhi=zhi)):return dict(solid=-.35)
        return dict(solid=answer)
