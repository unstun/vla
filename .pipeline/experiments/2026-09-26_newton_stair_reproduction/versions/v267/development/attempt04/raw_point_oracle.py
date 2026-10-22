"""Independent original unvoxelized PCD finite-cylinder clearance.

Finite upward triangle intersections classify below-floor material directly.
This does not use the C++ clipping, old voxel centres, old tomogram material
labels or circumscribed-voxel padding. Old padded margins remain separate.
"""
from pathlib import Path
import hashlib,json,math,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v267'
EXP=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pc=EXP/'inputs/static_background/building2_9.pcd';tp=BASE/'support_coverage_v134/triangles.f64'
assert sha(pc)=='8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae'
assert sha(tp)=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
raw=pc.read_bytes().split(b'DATA binary\n',1)[1];records=np.frombuffer(raw,dtype='<f4').reshape(-1,6);points=records[:,:3].astype(float)
kd=cKDTree(points);tri=np.fromfile(tp,dtype='<f8').reshape(-1,3,3)
n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-30)
up=tri[n[:,2]>32*np.finfo(np.float32).eps];tree=shapely.STRtree([Polygon(t[:,:2]) for t in up])
def margin(body,yaw):
    answer=.15;ground=body[2]-.3;witness=None
    for side in (-1,1):
        center=body+np.array([side*.18*math.cos(yaw),side*.18*math.sin(yaw),-.1])
        ids=kd.query_ball_point(center,math.hypot(.35,.45)+.15+1e-8);p=points[ids]
        possible=np.flatnonzero(p[:,2]<=ground+.26)
        terrain=np.zeros(len(p),dtype=bool)
        pair=tree.query(shapely.points(p[possible,:2]),predicate='intersects')
        if pair.size:
            pi=possible[pair[0]];t=up[pair[1]];a=t[:,0];u=t[:,1]-a;v=t[:,2]-a
            d=u[:,0]*v[:,1]-u[:,1]*v[:,0];x=p[pi,0];y=p[pi,1]
            uu=((x-a[:,0])*v[:,1]-(y-a[:,1])*v[:,0])/d;vv=(u[:,0]*(y-a[:,1])-u[:,1]*(x-a[:,0]))/d
            z=a[:,2]+uu*u[:,2]+vv*v[:,2]
            # Preserve v256's existing pure-upward actual-source-height rule,
            # now per raw point with a finite source-floor witness. A sampled
            # upward floor point need not be bit-identical to the asset plane.
            # Vertical/mixed/downward records get no upward exemption.
            source_up=(records[np.asarray(ids)[pi],5]>32*np.finfo(np.float32).eps)&(abs(p[pi,2]-ground)<.26)
            good=(abs(z-ground)<.26)&((p[pi,2]<=z+1e-10)|source_up)
            terrain[pi[good]]=True
        q=p[~terrain]-center
        if not len(q):continue
        radial=np.linalg.norm(q[:,:2],axis=1)-.35;vertical=abs(q[:,2])-.45
        distance=np.hypot(np.maximum(radial,0),np.maximum(vertical,0))+np.minimum(np.maximum(radial,vertical),0)
        j=int(distance.argmin())
        if float(distance[j])<answer:
            answer=float(distance[j]);record=records[np.asarray(ids)[~terrain][j]].astype(float)
            hits=[]
            for k in tree.query(shapely.Point(*record[:2]),predicate='intersects'):
                t=up[k];a=t[0];u=t[1]-a;v=t[2]-a;d=u[0]*v[1]-u[1]*v[0]
                uu=((record[0]-a[0])*v[1]-(record[1]-a[1])*v[0])/d;vv=(u[0]*(record[1]-a[1])-u[1]*(record[0]-a[0]))/d
                z=float(a[2]+uu*u[2]+vv*v[2])
                if abs(z-ground)<.26:hits.append(dict(floor_z=z,point_above_floor_m=float(record[2]-z)))
            witness=dict(record=record.tolist(),same_band_upward_hits=hits)
    return answer,witness
rows=[]
for r in json.loads((BASE/'source_surface_v266/source_inspection.json').read_text())['rows']:
    value,witness=margin(np.array(r['body']),r['yaw'])
    rows.append(dict(case_id=r['case_id'],endpoint=r['endpoint'],raw_pcd_surface_point_margin=value,collision=value<=0,witness=witness,original_body=r['body'],yaw=r['yaw']))
receipt=dict(source_pcd_sha256=sha(pc),source_triangles_sha256=sha(tp),raw_point_count=len(points),rows=rows,
    radius_m=.35,offset_m=.18,voxel_padding_used=False,old_voxel_material_labels_used=False,
    material_rule='Finite original cap below-floor volume OR v256 pure-upward actual-source-height association, at individual raw-point resolution; unchanged 0.26m band',
    scope='Endpoint checks only; finite raw source samples are not a complete continuous-surface certificate',planning_calls=0,physics_steps=0)
(OUT/'raw_point_oracle.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
assert all(r['raw_pcd_surface_point_margin']>0 for r in rows if r['case_id']!='B08')
assert next(r for r in rows if r['case_id']=='B08')['collision']
