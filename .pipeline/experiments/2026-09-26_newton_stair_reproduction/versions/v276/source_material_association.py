"""Bounded raw-source material registration; original distance points never move.

The bound accounts for two float32 affine/barycentric arithmetic paths:
three coefficient casts, three multiplies and two adds (gamma_8), plus the
respective final float32 rounding. It is a source-association error model,
not robot clearance, a geometric dilation, or permission for unknown points.
Only mutually consistent, normal-compatible source matches can add material
classification. The original finite-cap predicate is retained as direct evidence.
"""
from pathlib import Path
import sys,importlib.util
import numpy as np
import shapely,trimesh
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v267'))
from finite_floor_material import floor_material
_spec=importlib.util.spec_from_file_location('source_cap_geometry266',Path(__file__).resolve().parent.parent/'v266/surface_model.py')
_geometry=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_geometry)
U=np.finfo(np.float32).eps/2
GAMMA8=8*U/(1-8*U)
NORMAL_UP=32*np.finfo(np.float32).eps
AREA_MIN=1e-10

def rounding(v):
    x=np.asarray(v,dtype=np.float32)
    return .5*np.maximum(np.nextafter(x,np.full_like(x,np.inf)).astype(float)-x,
                         x-np.nextafter(x,np.full_like(x,-np.inf)).astype(float))
def cross_bound(a,b):
    return np.stack([a[...,1]*b[...,2]+a[...,2]*b[...,1],a[...,2]*b[...,0]+a[...,0]*b[...,2],a[...,0]*b[...,1]+a[...,1]*b[...,0]],axis=-1)

class SourceMaterialAssociation:
    def __init__(self,original,normalized,labels=None):
        self.tri=np.asarray(normalized,float);self.original=np.asarray(original,float)
        assert self.tri.shape==self.original.shape and self.tri.shape[1:]==(3,3)
        self.low=self.tri.min(axis=1);self.high=self.tri.max(axis=1)
        edge1=self.tri[:,1]-self.tri[:,0];edge2=self.tri[:,2]-self.tri[:,0]
        cross=np.cross(edge1,edge2);length=np.linalg.norm(cross,axis=1)
        self.normals=cross/np.maximum(length[:,None],1e-30)
        old=np.cross(self.original[:,1]-self.original[:,0],self.original[:,2]-self.original[:,0])
        self.original_normals=old/np.maximum(np.linalg.norm(old,axis=1)[:,None],1e-30)
        self.area=abs(cross[:,2])*.5
        # Coordinate-wise forward-error envelope, before taking a 3-D norm.
        self.vertex_error=GAMMA8*np.max(abs(self.tri),axis=1)+np.max(rounding(self.tri),axis=1)
        delta=2*self.vertex_error
        error=np.linalg.norm(cross_bound(abs(edge1),delta)+cross_bound(delta,abs(edge2))+cross_bound(delta,delta),axis=1)
        self.normal_bound=np.where(error<length,2*error/np.maximum(length-error,1e-30),np.inf)+8*U
        self.recall=2*np.max(np.linalg.norm(self.vertex_error,axis=1))+1e-12
        self.tree=shapely.STRtree(shapely.box(self.low[:,0],self.low[:,1],self.high[:,0],self.high[:,1]))
        up=self.original_normals[:,2]>NORMAL_UP
        self.up=self.original[up];self.up_tree=shapely.STRtree([shapely.Polygon(t[:,:2]) for t in self.up])
        self.labels=np.full(len(self.tri),-1,dtype=int) if labels is None else np.asarray(labels,dtype=int)
        assert self.labels.shape==(len(self.tri),)
        self.cache={};self.cap_cache={}
    def matches(self,record):
        key=np.asarray(record,dtype=np.float32).tobytes()
        if key in self.cache:return self.cache[key]
        r=np.array(record,dtype=float,copy=True);p=r[:3];normal=r[3:];nlen=np.linalg.norm(normal)
        if not np.isfinite(r).all() or nlen==0:return []
        normal/=nlen
        recall=self.recall+np.linalg.norm(GAMMA8*abs(p)+rounding(p))
        ids=np.asarray(self.tree.query(shapely.box(p[0]-recall,p[1]-recall,p[0]+recall,p[1]+recall)),dtype=int)
        if not len(ids):self.cache[key]=[];return []
        point_error=GAMMA8*abs(p)+rounding(p);bounds=np.linalg.norm(self.vertex_error[ids]+point_error,axis=1)
        near=(self.low[ids,2]-bounds<=p[2])&(self.high[ids,2]+bounds>=p[2])
        ids=ids[near];bounds=bounds[near]
        if not len(ids):self.cache[key]=[];return []
        # An unresolved normal is not source correspondence evidence.
        nd=np.minimum(np.linalg.norm(self.original_normals[ids]-normal,axis=1),np.linalg.norm(self.original_normals[ids]+normal,axis=1))
        good=(self.normal_bound[ids]<1.)&(nd<=self.normal_bound[ids])
        ids=ids[good];bounds=bounds[good]
        if not len(ids):self.cache[key]=[];return []
        nearest=trimesh.triangles.closest_point(self.tri[ids],np.broadcast_to(p,(len(ids),3)))
        distances=np.linalg.norm(nearest-p,axis=1);good=distances<=bounds
        result=[dict(face=int(i),distance=float(d),error_bound=float(b),associated_xyz=q.tolist()) for i,d,b,q in zip(ids[good],distances[good],bounds[good],nearest[good])]
        self.cache[key]=result;return result
    def material_match(self,match,ground):
        # The point is associated with a source face, but terrain may cover it
        # from a different upward face. Test the finite cap volume itself.
        q=np.asarray(match['associated_xyz'],float)
        recall=64*np.finfo(float).eps*max(1.,float(abs(q).max()))
        ids=self.tree.query(shapely.box(q[0]-recall,q[1]-recall,q[0]+recall,q[1]+recall))
        for i in ids:
            i=int(i)
            if self.normals[i,2]<=NORMAL_UP or self.high[i,2]<=ground-.26 or self.low[i,2]>=ground+.26:continue
            key=(i,float(ground))
            if key not in self.cap_cache:
                t=self.tri[i]
                p=_geometry.clip(list(t),np.array([0.,0.,-1.]),-(ground-.26))
                p=_geometry.clip(p,np.array([0.,0.,1.]),ground+.26)
                self.cap_cache[key]=_geometry.cap_halfspaces(p,t) if _geometry.projected(p).area>AREA_MIN else None
            planes=self.cap_cache[key]
            if planes is not None and all(float(n@q-d)<=_geometry.EPS for n,d in planes):return True
        return False
    def classify(self,records,ground):
        records=np.asarray(records)
        base=floor_material(records,self.up,self.up_tree,ground)
        result=base.copy()
        for i in np.flatnonzero(~base):
            # Out-of-band points cannot belong to wholly exempt source material.
            if records[i,2]>=ground+.26:continue
            matches=self.matches(records[i])
            if matches and all(self.material_match(m,ground) for m in matches):result[i]=True
        return result
