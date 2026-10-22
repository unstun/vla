from pathlib import Path
import json,numpy as np
from registered_point_oracle import association,activate,deactivate,margin,frozen,sha,HERE,BASE
OUT=BASE/'source_point_volume_audit_v276'
inputs=json.loads((BASE/'source_surface_v266/source_inspection.json').read_text())['rows']
queries=[dict(case_id=r['case_id'],body=r['body'],yaw=r['yaw']) for r in inputs]
for cohort,cid,channel in [('original52','A04','route_margins'),('original52','M03','local_samples'),('clean50','CU02','local_samples')]:
    r=json.loads((BASE/'source_benchmark_v273'/cohort/cid/'independent_solid_audit.json').read_text())[channel]['first_negative_witnesses'][0]
    record=np.array([r['witness']['record']],dtype=np.float32);before=record.copy()
    assert association.classify(record,r['body'][2]-.3)[0]
    assert np.array_equal(before,record)
    queries.append(dict(case_id=cid+'_'+channel,body=r['body'],yaw=r['yaw'],source_matches=association.matches(record[0])))
for cid in ['A04','G05','M03']:
    r=json.loads((BASE/'source_point_diagnosis_v275/audited/original52'/cid/'audit.json').read_text())['route_margins']['first_negative_witnesses'][0]
    record=np.array([r['witness']['record']],dtype=np.float32);before=record.copy()
    assert association.classify(record,r['body'][2]-.3)[0],cid
    assert np.array_equal(before,record)
    queries.append(dict(case_id=cid+'_registered_vertical_riser',body=r['body'],yaw=r['yaw'],source_matches=association.matches(record[0])))
deactivate()
for r in queries:r['old_margin']=margin(np.array(r['body']),r['yaw'])[0]
activate()
for r in queries:
    r['registered_margin'],r['witness']=margin(np.array(r['body']),r['yaw'])
    assert r['registered_margin']>=r['old_margin']-1e-12
    if r['case_id']=='B08':assert r['registered_margin']==r['old_margin'] and r['registered_margin']<-.13
    else:assert r['registered_margin']>0,r
receipt=dict(queries=queries,source_registration='gamma_8 float32 3-D affine/barycentric envelope; compatible normals; all matched materials agree',
    raw_points_moved=False,body_poses_moved=False,hard_radius_changed=False,native_model_changed=False,
    original_point_distance_code_sha256=sha(HERE.parent/'v272/raw_source_oracle.py'),registration_code_sha256=sha(HERE/'source_material_association.py'),
    source_pcd_sha256=sha(frozen.pc),source_triangles_sha256=sha(frozen.tp),planning_calls=0,physics_steps=0)
(OUT/'witness_controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps([dict(case_id=r['case_id'],old=r['old_margin'],registered=r['registered_margin']) for r in queries]),flush=True)
