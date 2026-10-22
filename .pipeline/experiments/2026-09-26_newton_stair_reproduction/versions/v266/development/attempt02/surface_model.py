"""Experimental finite surface model, independent of occupied voxel records.

The horizontal margin is the exact radial clearance to surfaces intersecting
the finite cylinder's vertical interval. It is not a 3-D Euclidean SDF.
Terrain removal uses actual finite upward caps and affine height, not an
infinite fitted plane, voxel label, or blanket exemption of low triangles.
"""
import math
import numpy as np
from shapely import STRtree, union_all
from shapely.geometry import Point, MultiPoint, GeometryCollection

EPS=1e-10

def clip(poly,normal,offset,inside=True):
    """Clip a convex 3-D polygon to n.p <= offset (or its complement)."""
    if not poly:return []
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=float(normal@a-offset);db=float(normal@b-offset)
        ia=da<=0 if inside else da>=0;ib=db<=0 if inside else db>=0
        if ia:out.append(a)
        if ia!=ib:out.append(a+(b-a)*(da/(da-db)))
    return out

def projected(poly):
    return MultiPoint(np.asarray(poly)[:,:2]).convex_hull if poly else GeometryCollection()

def cap_halfspaces(triangle):
    # Normalize orientation in XY; all admitted caps have upward normals.
    t=triangle
    result=[]
    for a,b in zip(t,np.roll(t,-1,axis=0)):
        e=b-a;n=np.array([e[1],-e[0],0.])
        result.append((n,float(n@a)))
    n=np.cross(t[1]-t[0],t[2]-t[0])
    result.append((n,float(n@t[0]))) # Below the actual affine cap.
    return result

def remove_cap(poly,halfspaces):
    """Exact convex difference, retaining outside pieces without a union."""
    pending=poly;result=[]
    for n,d in halfspaces:
        distances=[float(n@p-d) for p in pending]
        if max(distances)<=EPS:continue
        if min(distances)>EPS:
            result.append(pending);break
        outside=clip(pending,n,d,False)
        if outside:result.append(outside)
        pending=clip(pending,n,d,True)
        if not pending:break
    return result

class SurfaceModel:
    def __init__(self,triangles,radius=.35,offset=.18,clearance=.3,up=.55,down=.35,step=.26,tolerance=.12):
        self.tri=np.asarray(triangles,dtype=float)
        if not np.isfinite(self.tri).all():raise ValueError('Nonfinite source geometry')
        self.normal=np.cross(self.tri[:,1]-self.tri[:,0],self.tri[:,2]-self.tri[:,0])
        self.normal/=np.maximum(np.linalg.norm(self.normal,axis=1)[:,None],1e-30)
        self.upward=self.normal[:,2]>32*np.finfo(np.float32).eps
        self.low=self.tri.min(axis=1);self.high=self.tri.max(axis=1)
        self.radius=radius;self.offset=offset;self.clearance=clearance;self.up=up;self.down=down;self.step=step;self.tolerance=tolerance
        self.projections=[projected(list(t)) for t in self.tri]
        self.tree=STRtree(self.projections);self.views={}

    def vertical_hits(self,x,y):
        p=Point(x,y);ids=self.tree.query(p)
        out=[]
        for i in ids:
            t=self.tri[i];a=t[0];u=t[1]-a;v=t[2]-a;d=u[0]*v[1]-u[1]*v[0]
            if abs(d)<1e-14:continue
            uu=((x-a[0])*v[1]-(y-a[1])*v[0])/d;vv=(u[0]*(y-a[1])-u[1]*(x-a[0]))/d
            if uu>=-EPS and vv>=-EPS and uu+vv<=1+EPS:
                out.append((float(a[2]+uu*u[2]+vv*v[2]),float(self.normal[i,2]),int(i)))
        return sorted(out)

    def view(self,ground):
        ground=float(ground)
        if ground in self.views:return self.views[ground]
        zlo=ground+self.clearance-self.up;zhi=ground+self.clearance+self.down
        caps=[]
        for i in np.flatnonzero(self.upward&(self.high[:,2]>ground-self.step)&(self.low[:,2]<ground+self.step)):
            p=clip(list(self.tri[i]),np.array([0.,0.,-1.]),-(ground-self.step))
            p=clip(p,np.array([0.,0.,1.]),ground+self.step)
            q=projected(p)
            if q.area>EPS:
                caps.append((int(i),p,q,cap_halfspaces(self.tri[i])))
        cap_tree=STRtree([c[2] for c in caps]);pieces=[];source_ids=[]
        for i in np.flatnonzero((self.high[:,2]>=zlo)&(self.low[:,2]<=zhi)):
            p=clip(list(self.tri[i]),np.array([0.,0.,-1.]),-zlo)
            p=clip(p,np.array([0.,0.,1.]),zhi)
            if not p:continue
            remaining=[p]
            for j in cap_tree.query(projected(p),predicate='intersects'):
                remaining=[part for before in remaining for part in remove_cap(before,caps[int(j)][3])]
                if not remaining:break
            for part in remaining:
                q=projected(part)
                if not q.is_empty:pieces.append(part);source_ids.append(int(i))
        geometry=[projected(p) for p in pieces]
        result=dict(pieces=pieces,source_ids=source_ids,tree=STRtree(geometry),caps=caps,
                    floor=union_all([c[2] for c in caps],grid_size=1e-8),zlo=zlo,zhi=zhi)
        self.views[ground]=result;return result

    def occupied_axis_interval(self,x,y,ground,view):
        """Containment check: a cylinder wholly inside material meets no faces.

        Use oriented source intersections rather than treating a hollow BVH as
        a filled solid. Coincident duplicated faces remain additive; intervals
        under an actual near-floor cap retain the same terrain semantics.
        """
        hits=self.vertical_hits(x,y);events={}
        for z,n,i in hits:
            # Keep source intersection heights continuous. Rounding an event
            # above its own terrain cap creates a fictitious occupied sliver.
            events[z]=events.get(z,0)+(1 if n>0 else -1)
        cap_heights=[z for z,n,i in hits if n>0 and abs(z-ground)<self.step]
        terrain_top=max(cap_heights,default=-math.inf)
        levels=sorted(events,reverse=True);winding=0;previous=math.inf
        for z in levels:
            lo=max(z,view['zlo'],terrain_top);hi=min(previous,view['zhi'])
            if winding>0 and hi>lo+EPS:return True
            winding+=events[z];previous=z
        if winding>0 and min(previous,view['zhi'])>max(view['zlo'],terrain_top)+EPS:return True
        return False

    def assess(self,x,y,ground,yaw,check_support=True):
        if not all(map(math.isfinite,(x,y,ground,yaw))):raise ValueError('Nonfinite surface query')
        view=self.view(ground);edge=solid=math.inf;witness=None
        heights=[z for z,n,i in self.vertical_hits(x,y) if n>0]
        if check_support and (not heights or min(abs(z-ground) for z in heights)>=self.tolerance):
            return dict(free=False,reason='unknown_or_wrong_height',edge=-math.inf,solid=-math.inf,witness=None)
        for side in (-1,1):
            c=Point(x+side*self.offset*math.cos(yaw),y+side*self.offset*math.sin(yaw))
            if check_support:
                if not view['floor'].covers(c):edge=-math.inf
                else:edge=min(edge,view['floor'].boundary.distance(c)-self.radius)
            if len(view['pieces']):
                j=int(view['tree'].nearest(c));distance=view['tree'].geometries[j].distance(c)-self.radius
                if distance<solid:solid=distance;witness=view['source_ids'][j]
            if self.occupied_axis_interval(c.x,c.y,ground,view):solid=min(solid,-self.radius)
        reason='support_edge' if edge<=0 else 'source_solid' if solid<=0 else 'free'
        return dict(free=reason=='free',reason=reason,edge=edge,solid=solid,witness=witness)
