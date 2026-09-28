from pathlib import Path
import hashlib,json
import numpy as np
from pxr import Usd,UsdGeom
H=Path(__file__).resolve().parent;B=H.parents[1]
p=B/'inputs/building.usda';stage=Usd.Stage.Open(str(p));m=next(UsdGeom.Mesh(x) for x in stage.Traverse() if x.IsA(UsdGeom.Mesh))
assert np.array_equal(np.array(UsdGeom.Xformable(m).ComputeLocalToWorldTransform(Usd.TimeCode.Default())),np.eye(4))
v=np.asarray(m.GetPointsAttr().Get(),dtype=np.float64);f=np.asarray(m.GetFaceVertexIndicesAttr().Get(),dtype=np.int32).reshape(-1,3);t=v[f];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];det=a[:,0]*b[:,1]-a[:,1]*b[:,0];valid=np.abs(det)>1e-10;t=t[valid];a=a[valid];b=b[valid];det=det[valid];n=np.cross(a,b);nz=n[:,2]/np.linalg.norm(n,axis=1)
goal=np.array([1.954685200623011,-2.9868112220934897,4.5330305099487305]);rows=[]
for dx in np.linspace(-.6,.6,13):
 for dy in np.linspace(-.6,.6,13):
  xy=goal[:2]+[dx,dy];r=xy-t[:,0,:2];u=(r[:,0]*b[:,1]-r[:,1]*b[:,0])/det;w=(a[:,0]*r[:,1]-a[:,1]*r[:,0])/det;z=t[:,0,2]+u*a[:,2]+w*b[:,2];inside=(u>=-1e-8)&(w>=-1e-8)&(u+w<=1+1e-8);matches=inside&(np.abs(z-goal[2])<.01)&(nz>.99)
  rows.append({'xy':xy.tolist(),'same_flat_floor':bool(matches.any()),'z':z[matches].tolist()})
result={'goal_ground_xyz_m':goal.tolist(),'building_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'grid_half_width_m':.6,'samples':len(rows),'all_same_horizontal_floor':all(r['same_flat_floor'] for r in rows),'height_range_m':[min(z for r in rows for z in r['z']),max(z for r in rows for z in r['z'])],'claim':'Static horizontal floor coverage only; not a body-volume collision, contact or route validation.','rows':rows}
(H/'goal_surface.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
