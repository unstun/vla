"""Diagnostic only: existing Trimesh samples -> unchanged pinned CPU PCT."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,pickle,sys,time
import numpy as np
from scipy import ndimage
import trimesh
from pxr import Usd,UsdGeom
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
REF=ROOT/'references/upstream/2026-09-27_pct_ground_cost_reference'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
ref=ROOT/'references/upstream/2026-09-27_trimesh_surface_sampling'
assert trimesh.__version__=='5.1.0'
for name in ['sample.py','util.py']:
 assert sha(Path(trimesh.__file__).parent/name)==sha(ref/'trimesh'/name)
generator=module('pinned_generator_dense',REF/'source/scripts/generate_pct_tomogram.py')
assert sha(REF/'source/scripts/generate_pct_tomogram.py')=='6de22d1dd7fb3b2295d1d570011ede8b2f16dbcf72b48b1118e5270c300a55b0'
original=json.loads((REF/'historical_generation.json').read_text())
pcd=ROOT/'references/upstream/2026-09-26_pct_building_static_background/source/building2_9.pcd'
assert sha(pcd)==original['input_sha256']
with pcd.open('rb') as f:
 while not f.readline().startswith(b'DATA '):pass
 original_points=np.frombuffer(f.read(),dtype='<f4').reshape(-1,6)[:,:3].copy()
mesh_path=BASE/'inputs/building.usda';assert sha(mesh_path)=='e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39'
stage=Usd.Stage.Open(str(mesh_path));m=next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
assert np.array_equal(np.array(UsdGeom.Xformable(m).ComputeLocalToWorldTransform(Usd.TimeCode.Default())),np.eye(4))
vertices=np.asarray(m.GetPointsAttr().Get(),dtype=np.float32);faces=np.asarray(m.GetFaceVertexIndicesAttr().Get(),dtype=np.int32).reshape(-1,3)
mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
start=time.monotonic();parts=[original_points]
for i in range(8):
 pts,fi=trimesh.sample.sample_surface(mesh,1_000_000,seed=20260927+i);parts.append(pts.astype(np.float32));print('batch',i,flush=True)
points=np.concatenate(parts);np.save(HERE/'augmented_points.npy',points,allow_pickle=False)
config=generator.make_config(SimpleNamespace(**original['config']));lo,hi=original_points.min(0),original_points.max(0);center=(lo[:2]+hi[:2])/2
nx,ny=(np.ceil((hi[:2]-lo[:2])/config.map.resolution).astype(int)+4).tolist();count=int(np.ceil((hi[2]-config.map.ground_h)/config.map.slice_dh));h0=config.map.ground_h+config.map.slice_dh
result=generator.cpu_point2map(points,center,nx,ny,count,h0,config,np,ndimage)
old=pickle.loads((BASE/'inputs/new_building.pickle').read_bytes());data=np.stack(result[:5]).astype(np.float32)
new=dict(old);new['data']=data.astype(np.float16)
assert new['data'].shape[2:]==old['data'].shape[2:]  # Upstream may remove a newly redundant slice.
with (HERE/'map.pickle').open('wb') as f:pickle.dump(new,f)
np.savez_compressed(HERE/'map_float32.npz',data=data,**{k:v for k,v in old.items() if k!='data'})
publisher=module('dense_publisher',BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py')
selected=publisher.selected_ground_points(new,paired_elevations=data[3]);selected.astype('<f4').tofile(HERE/'ground.f32')
report={'original_points':len(original_points),'added_points':len(points)-len(original_points),'total_mesh_area_m2':float(mesh.area),'seed_sequence':list(range(20260927,20260935)),'trimesh_version':trimesh.__version__,'trimesh_commit':'fcf660feb0a14c68fd3945789e8ed77e260f9167','sampler_sha256':sha(ref/'trimesh/sample.py'),'generator_sha256':sha(REF/'source/scripts/generate_pct_tomogram.py'),'source_pcd_sha256':sha(pcd),'building_sha256':sha(mesh_path),'grid_center':center.tolist(),'selected_points':len(selected),'shape':list(data.shape),'config':original['config'],'seconds':time.monotonic()-start,'files':{n:sha(HERE/n) for n in ['augmented_points.npy','map.pickle','map_float32.npz','ground.f32']},'claim':'Offline diagnostic with all original points retained, all static surfaces eligible, unchanged PCT algorithm/config/cost threshold. No production map, dynamic actor data, or obstacle mask altered.'}
(HERE/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
