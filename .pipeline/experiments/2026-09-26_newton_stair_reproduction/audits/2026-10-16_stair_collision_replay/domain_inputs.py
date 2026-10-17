"""A common floor grid for PCT/native-SCAN region comparison, without prefiltering by PCT cost."""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys
import numpy as np
from prepare_inputs import numbers

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
BASE=ROOT.parent/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
out=ROOT/'domain_input';out.mkdir(exist_ok=False)
source=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py'
spec=importlib.util.spec_from_file_location('domain_pct',source);core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
m=core.load_pinned_map(BASE/'inputs/new_building.pickle');e=core.load_paired_elevations(BASE/'inputs/new_building_original_precision.npz',m)
all_points=core.selected_ground_points(m,cost_limit=None,paired_elevations=e)
bounds=[6.55,8.95,-4.85,-2.55];height_band=[1.20,2.60];reference_floor=1.5580305
p=all_points[(all_points[:,0]>=bounds[0])&(all_points[:,0]<=bounds[1])&(all_points[:,1]>=bounds[2])&(all_points[:,1]<=bounds[3])]
p=p[(p[:,2]-.03>=height_band[0])&(p[:,2]-.03<=height_band[1])]
columns={}
for row in p:
    key=(round(float(row[0]),4),round(float(row[1]),4))
    if key not in columns or abs(float(row[2])-.03-reference_floor)<abs(float(columns[key][2])-.03-reference_floor):columns[key]=row
points=np.array([columns[k] for k in sorted(columns)],dtype=np.float32)
assert len(points)>300
# Both SCAN variants query every retained floor cell, including PCT-rejected cells.
for p in (ROOT/'input').iterdir():
    if p.name.startswith(('cloud_','body_','sensor_','query_body_')) or p.name in ('scans.txt','navigation.f32','surface.f32','physical_floor.f32','support_gap.txt','planner.yaml'):
        (out/p.name).symlink_to(Path('../input')/p.name)
frames=json.loads((ROOT/'input/frames.json').read_text())
for f in frames:
    yaw=f['body_yaw'];rows=[(i,2,float(p[0]),float(p[1]),float(p[2])-.03+.30,yaw) for i,p in enumerate(points)]
    (out/f'queries_{f["index"]:04d}.txt').write_text('\n'.join(numbers(x) for x in rows)+'\n')
(out/'frames.txt').write_bytes((ROOT/'input/frames.txt').read_bytes())
np.save(out/'domain_floor.npy',points)
result={'bounds_xy':bounds,'floor_height_band_m':height_band,'column_selection':'Nearest original floor to 1.5580305 m within the fixed band; one layer per XY, same selection throughout the clip.','cell_resolution_m':.1,'cells':len(points),'pct_pass_cells':int((points[:,3]<=20).sum()),'pct_rejected_cells':int((points[:,3]>20).sum()),'scan_query_clearance_m':.30,'scan_yaw':'Recorded measured body yaw, shared by both SCAN variants.','frames':len(frames),'queries':len(frames)*len(points),'source_identity_sha256':hashlib.sha256((ROOT/'input/identity.json').read_bytes()).hexdigest(),'floor_grid_sha256':hashlib.sha256((out/'domain_floor.npy').read_bytes()).hexdigest(),'query_files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('queries_*.txt')}}
(out/'identity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
