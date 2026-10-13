"""Vertical triangle intersections at native rejected support query coordinates.

This diagnoses static scene geometry; it does not replace native support admission.
Bulk mesh and floor samples stay on gpu5070ti.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from pxr import Usd, UsdGeom

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
path = BASE/'inputs/building.usda'
stage = Usd.Stage.Open(str(path))
mesh = next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
assert np.array_equal(np.asarray(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default())), np.eye(4))
assert all(x == 3 for x in mesh.GetFaceVertexCountsAttr().Get())
vertices = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1,3)
triangles = vertices[faces]
queries = [('front_planned',7.626103372497891,-4.12886475244738),
           ('rear_planned',7.3593334522742175,-4.3705956144899725),
           ('planned_body',7.492718412386054,-4.249730183468676),
           ('front_measured',7.700993793424825,-4.057547483254827)]
guard_result = json.loads((HERE/'attempt04/result.json').read_text())
guard_query = next(x for x in guard_result['probes'] if x['kind']=='point' and
                   x['case']==2 and x['label']=='live_collision_planned')
queries += [(f'guard_drop_{i}', *x['xy']) for i,x in
            enumerate(guard_query['caps'][0]['nearby_drop_examples'])]
out = []
for name,x,y in queries:
    mask = ((triangles[:,:,0].min(1)<=x+1e-9)&(triangles[:,:,0].max(1)>=x-1e-9)&
            (triangles[:,:,1].min(1)<=y+1e-9)&(triangles[:,:,1].max(1)>=y-1e-9))
    ids=np.flatnonzero(mask);t=triangles[mask];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0]
    det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    valid=abs(det)>1e-12;ids=ids[valid];t=t[valid];a=a[valid];b=b[valid];det=det[valid]
    dx=x-t[:,0,0];dy=y-t[:,0,1]
    u=(dx*b[:,1]-dy*b[:,0])/det;v=(a[:,0]*dy-a[:,1]*dx)/det
    hit=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)
    z=t[:,0,2]+u*a[:,2]+v*b[:,2]
    out.append(dict(name=name,xy=[x,y],intersections=[dict(face=int(i),z=float(h))
                   for i,h in zip(ids[hit],z[hit])],
                   near_navigation_floor=bool(np.any(hit & (z>1.3) & (z<1.9)))))
result=dict(mesh_path=str(path),mesh_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    probes=out,scope='Exact vertical intersections with frozen static triangle mesh; separate from native sensed support verdict.')
result['limitations'] = 'Triangle intersections do not validate whole-footprint clearance; upstream dense PCT intermediate products are absent from this execution copy.'
(HERE/'mesh_probe_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
