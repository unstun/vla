"""Actual raw PCD point distances, with separate frozen voxel-control columns.

Source-surface radial clearance is a different domain from the former padded
voxel SDF. Do not assert equality between those quantities. Native source
conformance is tested independently against the finite 3-D reference.
"""
from pathlib import Path
import csv,hashlib,json,sys,time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v276'))
from registered_point_oracle import activate,margin,frozen
activate();pc=frozen.pc;tp=frozen.tp;points=frozen.points
folder=Path(sys.argv[2]);assert sys.argv[1]=='route'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(oracle='Original unvoxelized PCD + independent finite source-floor association',
    source_pcd_sha256=sha(pc),source_triangles_sha256=sha(tp),raw_points=len(points),radius_m=.35,
    native_domain='finite source surfaces; radial margins are not equal to legacy voxel SDF',
    material_rule='Frozen v276 bounded 3D material correspondence; original raw XYZ distances unchanged',
    yaw_protocol='Installed GridMap::collision_heading_lookahead_s for local samples',
    planning_calls=0,physics_steps=0)
started=time.monotonic()
for stem,output in [('route_margins','route_margins'),('local_samples','local_samples_checked')]:
    source=folder/(stem+'.csv')
    if not source.exists():continue
    rows=list(csv.DictReader(source.open()));values=[];witnesses=[]
    for index,row in enumerate(rows):
        p=np.array([float(row[k]) for k in ('x','y','z')]);v,w=margin(p,float(row['yaw']));values.append(v)
        row['raw_solid_margin']=v
        if v<=0:witnesses.append(dict(sample=index,body=p.tolist(),yaw=float(row['yaw']),margin=v,witness=w))
    if not rows:continue
    receipt[stem]=dict(queries=len(rows),minimum_raw_point_margin=min(values),negative_samples=sum(v<=0 for v in values),
        native_margin_min=min(float(r['native_solid_margin']) for r in rows),voxel_control_min=min(float(r['voxel_solid_margin']) for r in rows),
        input_sha256=sha(source),first_negative_witnesses=witnesses[:12])
    if stem=='route_margins':source.rename(folder/'route_margins_native.csv')
    with (folder/(output+'.csv')).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    receipt[stem]['output_sha256']=sha(folder/(output+'.csv'))
receipt.update(queries=receipt['route_margins']['queries'],minimum_independent_margin=receipt['route_margins']['minimum_raw_point_margin'],
    local_queries=receipt.get('local_samples',{}).get('queries',0),local_solid_margin_min=receipt.get('local_samples',{}).get('minimum_raw_point_margin'),wall_s=time.monotonic()-started)
(folder/'independent_solid_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
