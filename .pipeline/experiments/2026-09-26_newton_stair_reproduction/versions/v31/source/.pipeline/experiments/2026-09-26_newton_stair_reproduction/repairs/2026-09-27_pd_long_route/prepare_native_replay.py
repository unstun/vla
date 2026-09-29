"""Original empty-run events for the existing full native SCAN replay."""
import hashlib,importlib.util,json,os,pickle,sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[2]
run=BASE/'runs/empty_long_route05';out=Path(os.environ['NEWTON_RUN_DIR'])/'inputs';out.mkdir()
events=[];arrays={}
spec=importlib.util.spec_from_file_location('empty_replay_pct_core',BASE/'references/pct_sim_clock_core.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
with (run/'inputs/flat_floor.pickle').open('rb') as f:arrays['ground']=m.selected_ground_points(pickle.load(f))
for r in map(json.loads,(run/'telemetry.jsonl').read_text().splitlines()):
 b=r['body_sensor'];events.append({'stamp':round(r['physics_time_s']*1e9),'kind':'body','data':{'position':b['position'],'quaternion':b['quaternion'],'linear':b['linear_world'],'angular':b['angular_world'],'linear_body':b['linear_body'],'angular_body':b['angular_body']}})
for i,r in enumerate(json.loads((run/'sensor_manifest.json').read_text())):
 path=run/r['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
 with np.load(path) as d:arrays[f'cloud_{i}']=d['sensor_points']
 b=r['body_sensor'];events.append({'stamp':r['stamp_ns'],'kind':'cloud','data':{'array':f'cloud_{i}','position':b['sensor_position'],'quaternion':b['sensor_quaternion']}})
for r in map(json.loads,(run/'artifacts/reactive_observations.jsonl').read_text().splitlines()):
 if r['event']=='pct_route':events.append({'stamp':r['clock_ns'],'kind':'pct_route','data':r['data']})
events.sort(key=lambda e:(e['stamp'],{'body':0,'cloud':1,'pct_route':2}[e['kind']]))
np.savez_compressed(out/'points.npz',**arrays)
(out/'events.json').write_text(json.dumps(events)+'\n');(out/'planner.yaml').write_bytes((run/'planner.yaml').read_bytes())
(out/'input_manifest.json').write_text(json.dumps({'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()},'source_run':run.name,'claim':'Recorded measured body/cloud events and original native PCT route; no synthetic navigation input'},indent=2)+'\n')
