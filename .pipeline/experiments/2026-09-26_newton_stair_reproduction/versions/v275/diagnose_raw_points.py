"""Read-only source/PCD material discrepancy witnesses from frozen v273."""
from pathlib import Path
import hashlib,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
import shapely,trimesh
from shapely.geometry import Polygon,Point
from shapely.ops import nearest_points
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_point_diagnosis_v275';OUT.mkdir(exist_ok=True)
raw=BASE/'support_coverage_v134/triangles.f64';fixed=BASE/'source_topology_v268/triangles_oriented.f64'
tri=np.fromfile(raw,dtype='<f8').reshape(-1,3,3);oriented=np.fromfile(fixed,dtype='<f8').reshape(-1,3,3)
assert len(tri)==len(oriented)==16448
norm=lambda t:np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
n0=norm(tri);n1=norm(oriented);n0/=np.maximum(np.linalg.norm(n0,axis=1)[:,None],1e-30);n1/=np.maximum(np.linalg.norm(n1,axis=1)[:,None],1e-30)
changed=np.flatnonzero(np.any(n0!=n1,axis=1));polygons=[Polygon(t[:,:2]) for t in tri];tree=shapely.STRtree(polygons)
rows=[]
for cohort,cid,channel in [('original52','A04','route_margins'),('original52','M03','local_samples'),('clean50','CU02','local_samples')]:
    source=BASE/'source_benchmark_v273'/cohort/cid/'independent_solid_audit.json';w=json.loads(source.read_text())[channel]['first_negative_witnesses'][0]
    point=np.array(w['witness']['record'][:3]);g=w['body'][2]-.3;p=Point(*point[:2]);r=np.float32(point[:2]);ulp=(np.nextafter(r,np.full_like(r,np.inf))-r).astype(float)
    closest=trimesh.triangles.closest_point(tri,np.broadcast_to(point,(len(tri),3)));distance=np.linalg.norm(closest-point,axis=1);near=np.argsort(distance)[:8]
    candidates=[]
    for k in tree.query(shapely.box(point[0]-1e-4,point[1]-1e-4,point[0]+1e-4,point[1]+1e-4)):
        k=int(k)
        if max(n0[k,2],n1[k,2])<=32*np.finfo(np.float32).eps:continue
        t=oriented[k];a=t[0];u=t[1]-a;v=t[2]-a;d=u[0]*v[1]-u[1]*v[0]
        if not d:continue
        z=a[2]+((point[0]-a[0])*v[1]-(point[1]-a[1])*v[0])/d*u[2]+(u[0]*(point[1]-a[1])-u[1]*(point[0]-a[0]))/d*v[2]
        if abs(z-g)>.4:continue
        q=np.array(nearest_points(p,polygons[k])[1].coords[0]);candidates.append(dict(face=k,original_nz=float(n0[k,2]),normalized_nz=float(n1[k,2]),plane_height_at_raw_xy=float(z),xy_distance=float(polygons[k].distance(p)),nearest_xy=q.tolist(),xy_delta_in_ulps=((point[:2]-q)/ulp).tolist(),triangle=t.tolist()))
    rows.append(dict(cohort=cohort,case_id=cid,channel=channel,original_witness=w,float32_xy_ulp=ulp.tolist(),nearest_source_faces=[dict(face=int(k),distance=float(distance[k]),closest=closest[k].tolist(),original_normal=n0[k].tolist(),normalized_normal=n1[k].tolist()) for k in near],upward_candidates=candidates))
receipt=dict(scope='Read-only material diagnosis; no new model, planner call or physics',normal_changed_face_ids=changed.tolist(),rows=rows,source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),normalized_sha256=hashlib.sha256(fixed.read_bytes()).hexdigest())
(OUT/'raw_source_diagnosis.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
