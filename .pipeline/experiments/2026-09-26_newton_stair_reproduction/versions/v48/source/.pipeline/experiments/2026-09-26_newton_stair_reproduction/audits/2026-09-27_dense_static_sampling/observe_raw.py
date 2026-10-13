"""Observe the same pinned generator on the fixed all-surface dense samples."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,pickle,sys
import numpy as np,scipy
from scipy import ndimage
H=Path(__file__).resolve().parent;B=H.parents[1];R=B.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m
receipt=json.loads((H/'receipt.json').read_text());assert sha(H/'augmented_points.npy')==receipt['files']['augmented_points.npy']
gen_path=R/'references/upstream/2026-09-27_pct_ground_cost_reference/source/scripts/generate_pct_tomogram.py';assert sha(gen_path)==receipt['generator_sha256']
gen=load('dense_cost_generator',gen_path);publisher=load('dense_surface_publisher',B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py');source=pickle.loads((H/'map.pickle').read_bytes());points=np.load(H/'augmented_points.npy')
old_count=receipt['original_points'];original=points[:old_count];hi=original.max(0);cfg=gen.make_config(SimpleNamespace(**receipt['config']));count=int(np.ceil((hi[2]-cfg.map.ground_h)/cfg.map.slice_dh));h0=cfg.map.ground_h+cfg.map.slice_dh;capture={}
def observe(frame,event,arg):
 if event=='return' and frame.f_code is gen.cpu_point2map.__code__:
  f=frame.f_locals;capture['raw_cost']=f['trav_cost'][f['idx_simp']].copy();capture['idx_simp']=list(f['idx_simp'])
sys.setprofile(observe)
try:r=gen.cpu_point2map(points,np.array(receipt['grid_center'],np.float32),source['data'].shape[2],source['data'].shape[3],count,h0,cfg,np,ndimage)
finally:sys.setprofile(None)
data=np.stack(r[:5]).astype(np.float32);expected=np.load(H/'map_float32.npz')['data'];assert np.array_equal(data,expected,equal_nan=True)
shadow=dict(source);shadow['data']=source['data'].copy();shadow['data'][0]=capture['raw_cost'].astype(np.float16)
ground=publisher.selected_ground_points(shadow,paired_elevations=data[3]);ground.astype('<f4').tofile(H/'raw_ground.f32');np.save(H/'raw_surface_points.npy',ground.astype('<f4'),allow_pickle=False)
np.savez_compressed(H/'raw_cost_observation.npz',raw_cost=capture['raw_cost'],idx_simp=capture['idx_simp'])
report={'numpy':np.__version__,'scipy':scipy.__version__,'original_map_sha256':sha(B/'inputs/new_building.pickle'),'original_precision_sha256':sha(B/'inputs/new_building_original_precision.npz'),'building_sha256':receipt['building_sha256'],'augmented_points_sha256':sha(H/'augmented_points.npy'),'generator_sha256':sha(gen_path),'trimesh_commit':receipt['trimesh_commit'],'idx_simp':capture['idx_simp'],'points':len(ground),'files':{n:sha(H/n) for n in ['raw_ground.f32','raw_surface_points.npy','raw_cost_observation.npz']},'claim':'Unmodified upstream PCT CPU calculation on the already recorded 2M+8M static samples; navigation selected map is not replaced. New payload is unscored sensor-ground evidence only.'};(H/'raw_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
