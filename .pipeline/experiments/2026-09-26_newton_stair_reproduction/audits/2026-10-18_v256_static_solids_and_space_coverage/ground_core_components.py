"""Independent original-mesh ground enclosures; no runtime component rules.

A closed wall curtain at nominal standing height separates continuous XY paths.
An enclosure with no upward surface allowing a first <=.26 m height transition
cannot connect to another floor under the declared standing/step contract.
Open/nonmanifold mesh winding is NOT treated as an occupancy oracle.
"""
from pathlib import Path
import hashlib,json,math,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from pxr import Usd,UsdGeom
from shapely.geometry import LineString,Point,Polygon,mapping
from shapely.ops import unary_union,polygonize
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257'
path=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/building.usda';stage=Usd.Stage.Open(str(path));mesh=next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
assert UsdGeom.GetStageMetersPerUnit(stage)==1 and UsdGeom.GetStageUpAxis(stage)=='Z'
v=np.array(mesh.GetPointsAttr().Get(),dtype=float);t=np.array(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()));v=(np.c_[v,np.ones(len(v))]@t)[:,:3].astype(np.float32)
f=np.array(mesh.GetFaceVertexIndicesAttr().Get(),dtype=int).reshape(-1,3);tri=v[f].astype(float)
assert np.array_equal(tri,np.fromfile(BASE/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3))
norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-30)
vertical=tri[abs(norm[:,2])<1e-6];ground=.0580303;z=ground+.3;segments=[]
for a in vertical:
 if a[:,2].min()>z or a[:,2].max()<z:continue
 hits=[]
 for p,q in zip(a,np.roll(a,-1,axis=0)):
  if abs(p[2]-q[2])<1e-12:continue
  u=(z-p[2])/(q[2]-p[2])
  if -1e-10<=u<=1+1e-10:hits.append(tuple(np.round((p+u*(q-p))[:2],6)))
 hits=sorted(set(hits))
 if len(hits)==2 and math.dist(*hits)>1e-6:segments.append(LineString(hits))
wall_curtain=unary_union(segments)
def clip(poly,level,above):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=a[2]>=level if above else a[2]<=level;ib=b[2]>=level if above else b[2]<=level
  if ia:result.append(a)
  if ia!=ib:result.append(a+(b-a)*((level-a[2])/(b[2]-a[2])))
 return result
up=[]
for a in tri[norm[:,2]>1e-6]:
 p=clip(list(a),ground+1e-5,True)
 if p:p=clip(p,ground+.26,False)
 if len(p)>=3:
  q=Polygon(np.array(p)[:,:2])
  if q.is_valid and q.area>1e-10:up.append(q)
up_union=unary_union(up)
floor_polys=[]
for a in tri[norm[:,2]>1e-6]:
 p=clip(list(a),ground-.26,True)
 if p:p=clip(p,ground+.26,False)
 if len(p)>=3:
  q=Polygon(np.array(p)[:,:2])
  if q.is_valid and q.area>1e-10:floor_polys.append(q)
floor_union=unary_union(floor_polys)
# The union of the two radius-r circles at +/-offset contains a centred disk
# sqrt(r*r-offset*offset) at EVERY heading. Use an inscribed round buffer and
# a 1um smaller radius as a permissive necessary collision model, not a new rule.
core_radius=math.sqrt(.35**2-.18**2)-1e-6
free=floor_union.difference(wall_curtain.buffer(core_radius,quad_segs=16))
regions=sorted(list(free.geoms) if free.geom_type=='MultiPolygon' else [free],key=lambda p:-p.area)
region_rows=[]
for i,r in enumerate(regions):
 first_step_area=float(r.intersection(up_union).area)
 region_rows.append(dict(region=i,area=r.area,bounds=list(r.bounds),geometry=mapping(r),first_step_upward_surface_overlap_area_m2=first_step_area,no_first_legal_step=first_step_area<1e-8))
manifest=json.loads((OUT/'cases_manifest.json').read_text());rows=[]
for c in manifest['cases']:
 for which in ('start','goal'):
  xyz=c[which]['ground']
  if abs(xyz[2]-ground)>.08:continue
  containing=[i for i,r in enumerate(regions) if r.contains(Point(xyz[:2]))]
  rows.append(dict(case_id=c['case_id'],endpoint=which,xyz=xyz,containing_wall_regions=containing,
   closed_ground_enclosure_without_first_step=any(region_rows[i]['no_first_legal_step'] for i in containing)))
receipt=dict(role='Independent mesh diagnosis, not planner input or a score relabeling',physics_steps=0,source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),native_simulator_triangles_exactly_matched=True,nominal_standing_cross_section_z=z,legal_step_limit_m=.26,unavoidable_heading_independent_core_radius_m=core_radius,actual_shape_radius_m=.35,offset_m=.18,model='Permissive necessary condition using original wall curtains and un-eroded <=.26m floor projection; no added planner padding',wall_segments=len(segments),regions=region_rows,endpoints=rows,winding_is_not_occupancy='The source is an open architectural surface mesh; do not infer occupied volume from a half winding threshold.')
(OUT/'ground_core_components.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(wall_segments=len(segments),regions=[{k:v for k,v in r.items() if k!='geometry'} for r in region_rows],endpoints=rows),indent=2))
