"""Finite original-source witnesses; no planning or geometry modification."""
from pathlib import Path
import hashlib, json, math, os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from scipy.spatial import cKDTree

BASE=Path('/data/sun/vla_mppi_20261009')
EXP=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
OUT=BASE/'source_surface_v266';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tp=BASE/'support_coverage_v134/triangles.f64'
assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
t=np.fromfile(tp,dtype='<f8').reshape(-1,3,3)
n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-30)
a=t[:,0];u=t[:,1]-a;v=t[:,2]-a;det=u[:,0]*v[:,1]-u[:,1]*v[:,0]

def vertical(x,y):
    good=abs(det)>1e-14;uu=np.zeros(len(t));vv=uu.copy()
    uu[good]=((x-a[good,0])*v[good,1]-(y-a[good,1])*v[good,0])/det[good]
    vv[good]=(u[good,0]*(y-a[good,1])-u[good,1]*(x-a[good,0]))/det[good]
    ids=np.flatnonzero(good&(uu>=-1e-9)&(vv>=-1e-9)&(uu+vv<=1+1e-9))
    z=a[:,2]+uu*u[:,2]+vv*v[:,2]
    return [dict(triangle=int(i),height=float(z[i]),normal=n[i].tolist()) for i in ids[np.argsort(z[ids])]]

pc=EXP/'inputs/static_background/building2_9.pcd';raw=pc.read_bytes();mark=b'DATA binary\n'
assert sha(pc)=='8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae'
header,payload=raw.split(mark,1)
assert b'FIELDS x y z normal_x normal_y normal_z' in header
points=np.frombuffer(payload,dtype='<f4').reshape(-1,6)
tree=cKDTree(points[:,:3])
support=BASE/'generic_mechanisms_v261/native/fixtures/building/native.support'
h=support.open().readline().split();res,ox,oy=map(float,(h[1],h[5],h[6]))
old=json.loads((BASE/'saved_output_audit_v264/endpoint_diagnosis.json').read_text())
rows=[r for r in old['rows'] if float(r['solid_margin'])<0]
rows.append(dict(case='B08',endpoint='control',x=-6.0453147888,y=-3.1868112087,z=4.8330311966,yaw=-2.872806690561133,witness_x=-6.434781,witness_y=-3.252849,witness_z=4.931616))
out=[]
for r in rows:
    p=np.array([float(r[k]) for k in ('x','y','z')]);yaw=float(r['yaw']);w=np.array([float(r[k]) for k in ('witness_x','witness_y','witness_z')])
    xy=[('body',p[0],p[1]),('witness',w[0],w[1])]
    for side in (-1,1):xy.append((f'cylinder_{side}',p[0]+side*.18*math.cos(yaw),p[1]+side*.18*math.sin(yaw)))
    queries=[]
    for label,x,y in xy:
        cell=(math.floor((x-ox)/res),math.floor((y-oy)/res));cx=ox+(cell[0]+.5)*res;cy=oy+(cell[1]+.5)*res
        queries.append(dict(label=label,xy=[x,y],hits=vertical(x,y),cell=cell,cell_xy=[cx,cy],cell_hits=vertical(cx,cy)))
    ids=tree.query_ball_point(w,.055)
    # Exact voxel membership is distinct from a spherical neighbourhood.
    c=np.floor(w/.05)*.05+.025
    near=tree.query_ball_point(c,.025*math.sqrt(3)+1e-6)
    near=[i for i in near if np.all(abs(points[i,:3]-c)<=.025+1e-6)]
    lo=t.min(axis=1);hi=t.max(axis=1)
    tri_ids=np.flatnonzero(np.all(hi>=w-.075,axis=1)&np.all(lo<=w+.075,axis=1))
    out.append(dict(case_id=r.get('case_id',r.get('case')),endpoint=r.get('which',r.get('endpoint')),body=p.tolist(),yaw=yaw,ground=float(p[2]-.3),witness=w.tolist(),vertical_queries=queries,nearest_source_points=points[ids].astype(float).tolist(),voxel_source_points=points[near].astype(float).tolist(),nearby_triangles=[dict(id=int(i),vertices=t[i].tolist(),normal=n[i].tolist()) for i in tri_ids]))
receipt=dict(triangles_sha256=sha(tp),pcd_sha256=sha(pc),triangles=len(t),point_records=len(points),radius=.35,planning_calls=0,physics_steps=0,rows=out)
(OUT/'source_inspection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(queries=len(out),triangles=len(t),point_records=len(points),output=str(OUT/'source_inspection.json'))))
