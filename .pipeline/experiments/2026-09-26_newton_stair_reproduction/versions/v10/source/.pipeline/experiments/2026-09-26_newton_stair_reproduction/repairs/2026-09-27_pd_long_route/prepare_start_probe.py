"""Reuse measured-map fixtures to diagnose the empty-scene initial search."""
import hashlib, importlib.util, json, math, os, pickle, sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'repairs/2026-09-26_generic_occupancy'))
from prepare_recorded_map_probe import pose, sha
source=BASE/'references/pct_sim_clock_core.py'
spec=importlib.util.spec_from_file_location('empty_pct_core',source)
core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
out=Path(os.environ['NEWTON_RUN_DIR'])
run=BASE/'runs/empty_long_route05'
manifest=json.loads((run/'sensor_manifest.json').read_text())
with (run/'inputs/flat_floor.pickle').open('rb') as f: ground=core.selected_ground_points(pickle.load(f))
cases=[]
for cutoff, condition, goal_height in ((12.5,'pct',.3-3.5e-7),(12.5,'exact',.3),(17.5,'exact',.3)):
 case=out/f'start_{cutoff:g}s_{condition}';case.mkdir()
 np.asarray(ground,dtype='<f4').tofile(case/'ground.f32')
 selected=[r for r in manifest if r['sim_time_s']<=cutoff+.001]
 clouds=[]; poses=[]
 for i,r in enumerate(selected):
  path=run/r['file'];assert sha(path)==r['sha256']
  name=f'cloud_{i:04d}.f32'
  with np.load(path) as d: np.asarray(d['sensor_points'],dtype='<f4').tofile(case/name)
  b=r['body_sensor'];body=f'body_{i:04d}.txt';sensor=f'sensor_{i:04d}.txt'
  pose(case/body,b['position'],b['quaternion']);pose(case/sensor,b['sensor_position'],b['sensor_quaternion'])
  clouds.append(name);poses.append(f"{r['stamp_ns']+1_000_000_000} {body} {sensor}")
 b=selected[0]['body_sensor'];pose(case/'body_pose.txt',b['position'],b['quaternion']);pose(case/'sensor_pose.txt',b['sensor_position'],b['sensor_quaternion'])
 (case/'clouds.txt').write_text('\n'.join(clouds)+'\n');(case/'poses.txt').write_text('\n'.join(poses)+'\n')
 start=selected[-1]['body_sensor']['position']
 queries=[f'{x:.8f} {y:.8f} {z:.12f} 0 q_{x:.2f}_{y:.2f}_{z:.9f}' for z in (.3-3.5e-7,.3-1e-8,.3,.32,start[2]) for x in np.arange(-.1,2.51,.1) for y in (0.,)]
 (case/'queries.txt').write_text('\n'.join(queries)+'\n')
 (case/'start_goal.txt').write_text(' '.join(map(str,[*start,1.,0.,goal_height]))+'\n')
 cases.append({'case':case.name,'source_run':run.name,'cutoff_s':cutoff,'sha256':{p.name:sha(p) for p in case.iterdir()}})
(out/'result.json').write_text(json.dumps({'cases':cases,'claim':'Original measured clouds and paired poses; query height is a read-only diagnostic, not a modified robot state.'},indent=2)+'\n')
