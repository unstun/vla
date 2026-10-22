"""Compare missing native layers with original Newton triangles and raw PCD."""
from pathlib import Path
import hashlib,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v256/native'
OUT=BASE/'generic_mechanisms_v259/diagnosis';OUT.mkdir(exist_ok=True)
tri=np.fromfile(BASE/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3)
pcd=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
data=pcd.read_bytes();marker=b'DATA binary\n';points=np.frombuffer(data[data.index(marker)+len(marker):],dtype='<f4').reshape(-1,6)
sources={name:np.fromfile(WORK/'fixtures/building'/f'{name}.f32',dtype='<f4').reshape(-1,4) for name in ('navigation','surface','physical_floor')}
def vertical_hits(x,y):
 a=tri[:,0];b=tri[:,1]-a;c=tri[:,2]-a;det=b[:,0]*c[:,1]-b[:,1]*c[:,0];ok=abs(det)>1e-12
 u=np.zeros(len(tri));v=np.zeros(len(tri));u[ok]=((x-a[ok,0])*c[ok,1]-(y-a[ok,1])*c[ok,0])/det[ok];v[ok]=(b[ok,0]*(y-a[ok,1])-b[ok,1]*(x-a[ok,0]))/det[ok]
 hit=ok&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
 return sorted(set(np.round((a[:,2]+u*b[:,2]+v*c[:,2])[hit],8)))
samples=[]
for x,y in [(8.5,4),(8.5,5),(8.5,5.5),(8.5,5.8),(8.5,6),(8.5,6.2),(8.5,6.5),(7.5,5.5),(5,5.5),(4,5.2),(4,5.5),(3,5.5),(0,5.5)]:
 cell=(np.abs(points[:,0]-x)<.07)&(np.abs(points[:,1]-y)<.07)
 nearby=points[cell];ground=nearby[(abs(nearby[:,2]-.0580303)<.03)&(nearby[:,5]>.9)]
 layers={}
 for name,p in sources.items():
  q=p[(abs(p[:,0]-x)<.071)&(abs(p[:,1]-y)<.071)]
  layers[name]=q.tolist()
 samples.append(dict(x=x,y=y,original_mesh_vertical_intersections=vertical_hits(x,y),original_upward_ground_points=len(ground),ground_source_z_range=[float(ground[:,2].min()),float(ground[:,2].max())] if len(ground) else None,sources=layers))
result=dict(original_pcd=str(pcd),original_pcd_sha256=hashlib.sha256(data).hexdigest(),samples=samples)
(OUT/'floor_sources.json').write_text(json.dumps(result,indent=2)+'\n')
for s in samples:print(json.dumps(s))
