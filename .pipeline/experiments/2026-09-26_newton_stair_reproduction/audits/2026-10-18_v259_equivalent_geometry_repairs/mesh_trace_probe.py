"""Diagnostic mesh-oracle checks, separate from clean case construction."""
from pathlib import Path
import csv,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from mesh_geometry import MeshGeometry
BASE=Path('/data/sun/vla_mppi_20261009');tri=np.fromfile(BASE/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3)
mesh=MeshGeometry(tri);out=BASE/'generic_mechanisms_v260/mesh_diagnosis';out.mkdir(exist_ok=True)
results=[]
for cid in ('A04','G05','U14','M01'):
 rows=list(csv.DictReader((BASE/'space_coverage_v257/scored'/cid/'static_request_1.csv').open()));checked=0;first=None
 for i,row in enumerate(rows):
  if i%10 and i not in (0,len(rows)-1):continue
  pose=[float(row[k]) for k in ('x','y','z','yaw')];pose[2]-=.3;v=mesh.pose(*pose);checked+=1
  if not v[0]:first=dict(index=i,pose=pose,mesh=list(v));break
 result=dict(case_id=cid,checked=checked,first_rejection=first);results.append(result);print(json.dumps(result),flush=True)
(out/'trace_probe.json').write_text(json.dumps(results,indent=2)+'\n')
