"""Raw-source material association, independent of native collision queries."""
import numpy as np
import shapely

def floor_material(records,upward_triangles,tree,ground):
    raw=np.asarray(records)
    if raw.dtype!=np.float32 or raw.ndim!=2 or raw.shape[1]!=6 or not np.isfinite(raw).all():
        raise ValueError('Finite original float32 XYZ/normal records required')
    p=raw[:,:3].astype(float);terrain=np.zeros(len(p),dtype=bool)
    possible=np.flatnonzero(p[:,2]<=ground+.26)
    xy=raw[possible,:2]
    lower=np.nextafter(xy,np.full_like(xy,-np.inf)).astype(float)
    upper=np.nextafter(xy,np.full_like(xy,np.inf)).astype(float)
    pair=tree.query(shapely.box(lower[:,0],lower[:,1],upper[:,0],upper[:,1]),predicate='intersects')
    if not pair.size:return terrain
    pi=possible[pair[0]];t=upward_triangles[pair[1]];a=t[:,0];u=t[:,1]-a;v=t[:,2]-a
    d=u[:,0]*v[:,1]-u[:,1]*v[:,0];x=p[pi,0];y=p[pi,1]
    uu=((x-a[:,0])*v[:,1]-(y-a[:,1])*v[:,0])/d;vv=(u[:,0]*(y-a[:,1])-u[:,1]*(x-a[:,0]))/d
    z=a[:,2]+uu*u[:,2]+vv*v[:,2]
    gx=(u[:,2]*v[:,1]-v[:,2]*u[:,1])/d;gy=(v[:,2]*u[:,0]-u[:,2]*v[:,0])/d
    dx=np.maximum(x-lower[pair[0],0],upper[pair[0],0]-x);dy=np.maximum(y-lower[pair[0],1],upper[pair[0],1]-y)
    dz=abs(gx)*dx+abs(gy)*dy
    source_up=(raw[pi,5]>32*np.finfo(np.float32).eps)&(abs(p[pi,2]-ground)<.26)
    good=(z-dz>ground-.26)&(z+dz<ground+.26)&((p[pi,2]<=z-dz+1e-10)|source_up)
    terrain[pi[good]]=True
    return terrain
