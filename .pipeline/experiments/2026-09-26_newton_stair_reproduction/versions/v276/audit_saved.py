"""Derive a new material audit from immutable saved samples; no new planning."""
from pathlib import Path
import csv,hashlib,json,sys,time
import numpy as np
from registered_point_oracle import activate,margin,association,HERE,BASE,frozen,sha
activate();cohort,cid=sys.argv[1:];SOURCE=BASE/'source_benchmark_v273'/cohort/cid;OUT=BASE/'source_point_volume_audit_v276/audited'/cohort/cid
OUT.mkdir(parents=True,exist_ok=False);receipt=dict(cohort=cohort,case_id=cid,scope='Derived audit of saved v273 curves; original ledger retained',
    source_pcd_sha256=sha(frozen.pc),source_geometry_sha256=sha(frozen.tp),model='bounded3Dsource-material association; frozen raw-point distance code',
    raw_coordinates_unchanged=True,requested_poses_unchanged=True,hard_radius_m=.35,planning_calls=0,physics_steps=0)
started=time.monotonic()
for stem in ['route_margins','local_samples_checked']:
    p=SOURCE/(stem+'.csv')
    if not p.exists():continue
    rows=list(csv.DictReader(p.open()));values=[];negative=[];changed=0
    for index,row in enumerate(rows):
        body=np.array([float(row[k]) for k in ['x','y','z']]);value,witness=margin(body,float(row['yaw']));old=float(row['raw_solid_margin'])
        assert value>=old-1e-12,(cohort,cid,stem,index,value,old)
        changed+=value!=old;row['raw_solid_margin_v273']=row['raw_solid_margin'];row['raw_solid_margin']=value;values.append(value)
        if value< -1e-10 and len(negative)<12:
            record=np.asarray(witness['record'],np.float32);matches=association.matches(record)
            negative.append(dict(sample=index,body=body.tolist(),yaw=float(row['yaw']),margin=value,witness=witness,source_matches=[dict(m,eligible=association.material_match(m,body[2]-.3)) for m in matches]))
        if index%500==0:print(json.dumps(dict(cohort=cohort,case_id=cid,channel=stem,samples=index+1,elapsed_s=time.monotonic()-started)),flush=True)
    if not rows:continue
    dest=OUT/(stem+'.csv')
    with dest.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    receipt[stem]=dict(queries=len(rows),minimum_raw_margin=min(values),negative_samples=sum(v< -1e-10 for v in values),changed_margin_samples=changed,
        input_sha256=sha(p),output_sha256=sha(dest),source_remote_path=str(p),first_negative_witnesses=negative)
receipt['elapsed_s']=time.monotonic()-started;receipt['registered_point_cache_entries']=len(association.cache)
(OUT/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('route_margins','local_samples_checked')}),flush=True)
