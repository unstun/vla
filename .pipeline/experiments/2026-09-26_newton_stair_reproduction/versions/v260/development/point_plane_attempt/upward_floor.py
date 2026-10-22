"""Original-return plane extraction before tomogram cost/slice reduction."""
import numpy as np
def upward_planes(points,res,ox,oy,voxel):
 valid=np.isfinite(points).all(axis=1)&(points[:,5]>32*np.finfo(np.float32).eps)
 p=points[valid].astype(float)
 ix=np.floor((p[:,0]-ox)/res).astype(np.int64);iy=np.floor((p[:,1]-oy)/res).astype(np.int64)
 cx=ox+(ix+.5)*res;cy=oy+(iy+.5)*res
 z=p[:,2]-(p[:,3]*(cx-p[:,0])+p[:,4]*(cy-p[:,1]))/p[:,5]
 # A projected centre outside the existing legal local step band is not a
 # supported centre on that source plane. This also removes near-vertical
 # plane extrapolations without imposing a new slope threshold.
 keep=np.abs(z-p[:,2])<.26
 ix,iy,z=ix[keep],iy[keep],z[keep]
 keys=np.c_[ix,iy,np.floor(z/voxel).astype(np.int64)]
 unique,inverse=np.unique(keys,axis=0,return_inverse=True)
 count=np.bincount(inverse);height=np.bincount(inverse,weights=z)/count
 return np.c_[unique[:,:2],height,count]
