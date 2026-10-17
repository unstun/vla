from pathlib import Path
import importlib.util,json,pickle,sys
import numpy as np
H=Path(__file__).resolve().parent;B=H.parents[1]
p=B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';sp=importlib.util.spec_from_file_location('split_publisher',p);m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
old=pickle.loads((B/'inputs/new_building.pickle').read_bytes());raw=np.load(B/'audits/2026-09-27_pct_raw_cost/raw_cost_observation.npz')['raw_cost'];elev=m.load_paired_elevations(B/'inputs/new_building_original_precision.npz',old)
shadow=dict(old);shadow['data']=old['data'].copy();shadow['data'][0]=raw.astype(np.float16)
pts=m.selected_ground_points(shadow,paired_elevations=elev);pts.astype('<f4').tofile(H/'raw_ground.f32');print(len(pts))
