"""Observe unmodified pinned CPU PCT internals; compare all five old channels."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,pickle,sys,time
import numpy as np
from scipy import ndimage
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
REF=ROOT/'references/upstream/2026-09-27_pct_ground_cost_reference'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
provenance=json.loads((REF/'provenance.json').read_text())
for r in provenance['files']:assert sha(REF/r['path'])==r['sha256']
generator=module('pinned_pct_generator',REF/'source/scripts/generate_pct_tomogram.py')
original=json.loads((REF/'historical_generation.json').read_text())
pcd=ROOT/'references/upstream/2026-09-26_pct_building_static_background/source/building2_9.pcd'
assert sha(pcd)==original['input_sha256']
with pcd.open('rb') as stream:
 header={}
 while True:
  line=stream.readline().decode().strip()
  if not line or line.startswith('#'):continue
  key,*values=line.split();header[key]=values
  if key=='DATA':break
 assert header['FIELDS']==['x','y','z','normal_x','normal_y','normal_z'] and header['DATA']==['binary']
 points=np.frombuffer(stream.read(),dtype='<f4').reshape(-1,6)[:,:3].copy()
config=generator.make_config(SimpleNamespace(**original['config']))
lo,hi=points.min(0),points.max(0);center=(lo[:2]+hi[:2])/2
nx,ny=(np.ceil((hi[:2]-lo[:2])/config.map.resolution).astype(int)+4).tolist()
count=int(np.ceil((hi[2]-config.map.ground_h)/config.map.slice_dh));h0=config.map.ground_h+config.map.slice_dh
capture={}
def observe(frame,event,arg):
 if event=='return' and frame.f_code is generator.cpu_point2map.__code__:
  f=frame.f_locals;capture['idx_simp']=list(f['idx_simp']);capture['raw_cost']=f['trav_cost'][f['idx_simp']].copy()
start=time.monotonic();sys.setprofile(observe)
try: result=generator.cpu_point2map(points,center,nx,ny,count,h0,config,np,ndimage)
finally:sys.setprofile(None)
elapsed=time.monotonic()-start
oldpath=BASE/'inputs/new_building.pickle';assert sha(oldpath)==original['tomogram_sha256']
old=pickle.loads(oldpath.read_bytes());generated=np.stack(result[:5]).astype(np.float16);expected=old['data']
comparison={}
for i,name in enumerate(['inflated_cost','gradient_x','gradient_y','ground','ceiling']):
 a=generated[i];b=expected[i];equal=(a==b)|(np.isnan(a)&np.isnan(b));finite=np.isfinite(a)&np.isfinite(b)
 comparison[name]={'equal_cells':int(equal.sum()),'total_cells':a.size,'exact':bool(equal.all()),'max_abs_delta':float(np.max(np.abs(a[finite].astype(float)-b[finite].astype(float)),initial=0.))}
assert all(comparison[name]['exact'] for name in ['inflated_cost','ground','ceiling']), comparison
np.savez_compressed(HERE/'raw_cost_observation.npz',raw_cost=capture['raw_cost'],idx_simp=capture['idx_simp'],generated=generated)
publisher=module('pinned_clock_core',BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py')
selected=publisher.selected_ground_points(old)
shadow=dict(old);shadow['data']=old['data'].copy();shadow['data'][0]=capture['raw_cost'].astype(np.float16)
raw_points=publisher.selected_ground_points(shadow)
# Preserve every previously selected elevation; raw-cost eligibility only adds.
key=lambda p:tuple(p[:3].view(np.uint32))
old_keys={key(p) for p in selected};raw_keys={key(p) for p in raw_points}
union={key(p):p.copy() for p in selected}
for row in raw_points:union.setdefault(key(row),row.copy())
qualified=np.asarray(list(union.values()),dtype='<f4');qualified.tofile(HERE/'qualified_ground.f32')
report={'source':provenance['commit'],'generator_sha256':sha(REF/'source/scripts/generate_pct_tomogram.py'),'map_sha256':sha(oldpath),'pcd_sha256':sha(pcd),'config':original['config'],'cpu_seconds':elapsed,'numpy_version':np.__version__,'idx_simp':capture['idx_simp'],'shape':list(generated.shape),'comparison':comparison,'selected_points':len(selected),'raw_qualified_points':len(raw_points),'union_points':len(qualified),'new_points':len(raw_keys-old_keys),'prior_selected_retained':old_keys<=set(union),'qualified_ground_sha256':sha(HERE/'qualified_ground.f32'),'claim':'CPU source identical to historical generator; source untouched; diagnostic ground candidate only. No navigation/support/runtime input changed.'}
(HERE/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
