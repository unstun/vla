"""Offline model comparison only. Does not change native geometry or admission."""
from pathlib import Path
import hashlib,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'saved_output_audit_v264'
source=HERE.parent/'v257/independent_solid_audit.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)==json.loads((source.parent/'manifest.json').read_text())['source_files']['independent_solid_audit.py']
context=dict(__file__=str(source),__name__='frozen_geometry_reference');exec(compile(source.read_text().split('\nmode=sys.argv[1];')[0],str(source),'exec'),context)
R=context['radius'];d=context['offset'];h=context['half'];H=.5*(context['up']+context['down']);mid=.5*(context['down']-context['up']);cap=context['target'];raw=context['data'];points=context['points'];tree=context['tree']
def cube_margin(body,yaw):
    ground=body[2]-context['clearance'];answer=cap
    for side in (-1,1):
        center=body+side*d*np.array([math.cos(yaw),math.sin(yaw),0.]);middle=center+np.array([0.,0.,mid])
        ids=np.asarray(tree.query_ball_point(middle,math.hypot(R,H)+cap+math.sqrt(3)*h+1e-6),dtype=int)
        if not len(ids):continue
        floor=raw[ids,3:];exempt=((floor[:,0]>-1e90)&(abs(floor[:,0]-ground)<.26)&(abs(floor[:,1]-ground)<.26))|((floor[:,2]>-1e90)&(abs(floor[:,2]-ground)<.26)&(abs(floor[:,3]-ground)<.26))
        p=points[ids[~exempt]]
        if not len(p):continue
        q=abs(p[:,:2]-center[:2])-h
        radial=np.linalg.norm(np.maximum(q,0.),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0.)-R
        vertical=abs(p[:,2]-middle[2])-(H+h)
        value=np.hypot(np.maximum(radial,0.),np.maximum(vertical,0.))+np.minimum(np.maximum(radial,vertical),0.)
        answer=min(answer,float(value.min()))
    return answer
receipt=json.loads((OUT/'endpoint_diagnosis.json').read_text());rows=[]
for row in receipt['rows']:
    if float(row['solid_margin'])>=0:continue
    body=np.array([float(row[k]) for k in ('x','y','z')]);yaw=float(row['yaw']);value=cube_margin(body,yaw)
    rows.append(dict(case_id=row['case_id'],endpoint=row['endpoint'],unchanged_sphere_margin=float(row['solid_margin']),exact_occupied_voxel_box_margin=value,
        point_margin_without_padding=row['independent_point_margin_without_padding'],original_mesh_margin=row['original_mesh_solid_margin'],support_verdict=int(row['support_verdict'])))
b08=np.array([-6.045314788818359,-3.1868112086791993,4.833031196594238]);witness=dict(case_id='B08_illegal_control',unchanged_sphere_margin=context['oracle'](b08,-2.872806690561133),exact_occupied_voxel_box_margin=cube_margin(b08,-2.872806690561133))
assert witness['exact_occupied_voxel_box_margin']<0
report=dict(production_model_changed=False,native_queries_changed=False,physical_attempts=0,planning_calls=0,
    scope='Alternative geometry calculation for review only; source material exemptions, 0.35m radius and voxel dimensions unchanged',
    radius_m=R,voxel_half_m=h,current_uncertainty='Circumscribed sphere of radius sqrt(3)*half',proposed_geometry='Exact occupied axis-aligned voxel box Minkowski sum with the same vertical cylinder',
    current_sphere_contains_box=True,source_sha256=sha(context['FIELD']),rows=rows,b08_control=witness)
(OUT/'voxel_model_comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
