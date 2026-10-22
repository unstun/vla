"""Independent unpartitioned SciPy/Numpy original-cloud geometry oracle.

Runtime uses partitioned PCL trees and C++ analytic SDF; this evaluator uses a
single double-precision SciPy tree and vectorized formulas, including the two
independent same-floor material evidence bands. No runtime query is imported.
"""
from pathlib import Path
import csv,hashlib,json,math,sys
import numpy as np
from scipy.spatial import cKDTree
import scipy
BASE=Path('/data/sun/vla_mppi_20261009');FIELD=BASE/'source_height_envelope_v279/native/fixtures/building/static_solids.env'
with FIELD.open() as f:
 header=f.readline().split();assert header[0]=='SOLID256B'
 res,ox,oy,radius,offset,up,down,clearance,target,half=map(float,header[1:])
 for _ in range(int(f.readline().split()[1])):f.readline()
 n=int(f.readline().split()[1]);data=np.loadtxt(f);assert data.shape==(n,7)
points=data[:,:3].astype(np.float32).astype(float);tree=cKDTree(points)
def oracle(body,yaw):
 ground=body[2]-clearance;answer=target;heading=np.array([math.cos(yaw),math.sin(yaw),0.])
 for side in (-1,1):
  center=body+side*offset*heading;middle=center+np.array([0.,0.,.5*(down-up)])
  reach=math.hypot(radius,.5*(up+down))+target+math.sqrt(3)*half
  ids=np.asarray(tree.query_ball_point(middle,reach+1e-6),dtype=int)
  if not len(ids):continue
  floor=data[ids,3:];original=(floor[:,0]>-1e90)&(abs(floor[:,0]-ground)<.26)&(abs(floor[:,1]-ground)<.26)
  actual=(floor[:,2]>-1e90)&(abs(floor[:,2]-ground)<.26)&(abs(floor[:,3]-ground)<.26)
  q=points[ids[~(original|actual)]]
  if not len(q):continue
  radial=np.linalg.norm(q[:,:2]-center[:2],axis=1)-radius;vertical=abs(q[:,2]-middle[2])-.5*(up+down)
  distance=np.hypot(np.maximum(radial,0),np.maximum(vertical,0))+np.minimum(np.maximum(radial,vertical),0)-math.sqrt(3)*half
  answer=min(answer,float(distance.min()))
 return answer
mode=sys.argv[1];folder=Path(sys.argv[2]);source=folder/('poses.csv' if mode=='parity' else 'route_margins.csv')
rows=list(csv.DictReader(source.open()));errors=[];independent=[]
for r in rows:
 body=np.array([float(r[k]) for k in ('x','y','z')]);value=oracle(body,float(r['yaw']));independent.append(value);errors.append(abs(value-float(r['native_solid_margin'])))
 if 'legacy_raw_solid_margin' in r:assert value>=float(r['legacy_raw_solid_margin'])-1e-6,('revoked previous floor-volume exemption',r,value)
 if mode=='route':r['raw_solid_margin']=value
assert rows and max(errors)<1e-6,(len(rows),max(errors,default=None))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(numpy_version=np.__version__,scipy_version=scipy.__version__,python=sys.version,oracle='unpartitioned scipy cKDTree + vectorized Numpy; no runtime code',queries=len(rows),max_margin_error=max(errors),mismatches=sum(e>1e-6 for e in errors),tolerance=1e-6,field_sha256=sha(FIELD),native_samples_sha256=sha(source),minimum_independent_margin=min(independent))
if mode=='parity':
 with (folder/'metrics.txt').open('a') as f:f.write(f"raw_oracle_mismatch={receipt['mismatches']}\nmax_margin_error={max(errors):.17g}\n")
else:
 source.rename(folder/'route_margins_native.csv')
 with source.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 receipt['checked_samples_sha256']=sha(source)
 receipt['legacy_raw_minimum']=min(float(r['legacy_raw_solid_margin']) for r in rows)
(folder/'independent_solid_audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
