"""Independent original-mesh endpoint evidence; never feeds planner decisions."""
from pathlib import Path
import hashlib,json,math,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257'
source=BASE/'support_coverage_v134/triangles.f64';triangles=np.fromfile(source,dtype='<f8').reshape(-1,3,3)
normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-30)
def evidence(ground):
 p=np.array(ground,dtype=float);p[2]+=.3
 a=triangles[:,0]-p;b=triangles[:,1]-p;c=triangles[:,2]-p
 la=np.linalg.norm(a,axis=1);lb=np.linalg.norm(b,axis=1);lc=np.linalg.norm(c,axis=1)
 det=np.einsum('ij,ij->i',a,np.cross(b,c));den=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
 winding=float(np.arctan2(det,den).sum()/(2*math.pi))
 v=triangles[:,0];u=triangles[:,1]-v;w=triangles[:,2]-v;d=u[:,0]*w[:,1]-u[:,1]*w[:,0];keep=abs(d)>1e-10;ids=np.where(keep)[0]
 v,u,w,d=v[keep],u[keep],w[keep],d[keep];x,y=p[0]-v[:,0],p[1]-v[:,1]
 s=(x*w[:,1]-y*w[:,0])/d;t=(u[:,0]*y-u[:,1]*x)/d;hit=(s>=-1e-9)&(t>=-1e-9)&(s+t<=1+1e-9)
 heights=v[:,2]+s*u[:,2]+t*w[:,2]
 intersections=[dict(z=float(z),normal_z=float(normal[i,2]),triangle=int(i)) for z,i in zip(heights[hit],ids[hit])]
 return dict(body_xyz=p.tolist(),oriented_winding_number=winding,mesh_inside_by_abs_winding_gt_half=abs(winding)>.5,vertical_intersections=intersections,actual_upward_floor_within_008=any(abs(q['z']-ground[2])<.08 and q['normal_z']>.1 for q in intersections))
manifest=json.loads((OUT/'cases_manifest.json').read_text());rows=[]
for c in manifest['cases']:
 rows.append(dict(case_id=c['case_id'],stratum=c['stratum'],start=evidence(c['start']['ground']),goal=evidence(c['goal']['ground'])))
receipt=dict(physics_steps=0,simulator_started=False,role='independent geometry diagnosis only; not an input or override to the scored planner',triangles=str(source),triangles_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),triangles_count=len(triangles),cases=rows)
(OUT/'mesh_endpoint_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps([dict(id=r['case_id'],s_inside=r['start']['mesh_inside_by_abs_winding_gt_half'],g_inside=r['goal']['mesh_inside_by_abs_winding_gt_half'],s_upfloor=r['start']['actual_upward_floor_within_008'],g_upfloor=r['goal']['actual_upward_floor_within_008']) for r in rows],indent=2))
