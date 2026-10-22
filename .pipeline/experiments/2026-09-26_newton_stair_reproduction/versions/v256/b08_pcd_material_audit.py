"""Independent original PCD surface-normal evidence, not a runtime classifier."""
from pathlib import Path
import hashlib,json,math
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v256';p=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
with p.open('rb') as f:
 while True:
  line=f.readline()
  if line.startswith(b'DATA '):break
 assert line.split()[1]==b'binary'
 a=np.fromfile(f,dtype='<f4').reshape(-1,6).astype(float)
body=np.array([-6.045314788818359,-3.1868112087249756,4.833031196594238]);yaw=-2.872806690561133
voxel=a[(a[:,0]>=-6.45)&(a[:,0]<-6.4)&(a[:,1]>=-3.25)&(a[:,1]<-3.2)&(a[:,2]>=4.5)&(a[:,2]<4.55)]
q=a[(np.linalg.norm(a[:,:2]-body[:2],axis=1)<.9)&(abs(a[:,2]-body[2])<.9)&(abs(a[:,5])<.3)];best=None
for side in (-1,1):
 center=body+side*.18*np.array([math.cos(yaw),math.sin(yaw),0]);r=np.linalg.norm(q[:,:2]-center[:2],axis=1)-.35;v=abs(q[:,2]-center[2]+.1)-.45
 distance=np.hypot(np.maximum(r,0),np.maximum(v,0))+np.minimum(np.maximum(r,v),0);i=int(np.argmin(distance));item=dict(side=side,point=q[i,:3].tolist(),normal=q[i,3:].tolist(),uninflated_point_margin=float(distance[i]),radial=float(r[i]),vertical=float(v[i]))
 if best is None or item['uninflated_point_margin']<best['uninflated_point_margin']:best=item
assert best['uninflated_point_margin']<0 and abs(best['normal'][2])<.3
receipt=dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),body=body.tolist(),yaw=yaw,radius_m=.35,offset_m=.18,up_m=.55,down_m=.35,voxel_padding_m=0.,raw_reference_min_voxel_points=voxel.tolist(),true_vertical_witness=best,nearby_vertical_points=len(q),interpretation='Original -0.1869 minimum voxel contains horizontal floor points with mixed below-floor association labels. Those labels are not height extents. Separate actual vertical original points prove true solid intrusion without padding. Original normals also support pure-upward source material correction; online queries introduce no slope or clearance threshold.')
(OUT/'b08_original_material.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
