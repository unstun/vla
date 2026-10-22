"""Conservative source-cap recall; the existing 3-D clip is authoritative."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v268'))
from surface_model import SurfaceModel as Parent,module as geometry

np=geometry.np
STRtree=geometry.STRtree
clip=geometry.clip
projected=geometry.projected
cap_halfspaces=geometry.cap_halfspaces
remove_cap=geometry.remove_cap
EPS=geometry.EPS

class SurfaceModel(Parent):
    def view(self,ground):
        ground=float(ground)
        if ground in self.views:return self.views[ground]
        zlo=ground+self.clearance-self.up;zhi=ground+self.clearance+self.down
        caps=[]
        for i in np.flatnonzero(self.upward&(self.high[:,2]>ground-self.step)&(self.low[:,2]<ground+self.step)):
            p=clip(list(self.tri[i]),np.array([0.,0.,-1.]),-(ground-self.step))
            p=clip(p,np.array([0.,0.,1.]),ground+self.step);q=projected(p)
            if q.area>EPS:caps.append((int(i),p,q,cap_halfspaces(p,self.tri[i])))
        cap_tree=STRtree([c[2] for c in caps]);pieces=[];source_ids=[]
        for i in np.flatnonzero((self.high[:,2]>=zlo)&(self.low[:,2]<=zhi)):
            p=clip(list(self.tri[i]),np.array([0.,0.,-1.]),-zlo)
            p=clip(p,np.array([0.,0.,1.]),zhi)
            if not p:continue
            remaining=[p]
            # Bbox candidates only: an exact projected intersection can lose
            # a shared edge after interpolation, before tolerant 3-D clipping.
            for j in cap_tree.query(projected(p)):
                remaining=[part for before in remaining for part in remove_cap(before,caps[int(j)][3])]
                if not remaining:break
            for part in remaining:
                if not projected(part).is_empty:pieces.append(part);source_ids.append(int(i))
        result=dict(pieces=pieces,source_ids=source_ids,tree=STRtree([projected(p) for p in pieces]),caps=caps,
            floor=geometry.union_all([c[2] for c in caps],grid_size=1e-8),zlo=zlo,zhi=zhi)
        self.views[ground]=result;return result
