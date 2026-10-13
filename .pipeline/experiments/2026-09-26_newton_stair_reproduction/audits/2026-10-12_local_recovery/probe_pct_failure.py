"""Read-only native PCT replay; snapped-start success is NOT a safe connector."""
from pathlib import Path
import hashlib,json,numpy as np
from pct_planner.config import Config
from pct_planner.planner_wrapper import TomogramPlanner
T=Path('/task');inp=T/'evidence/v162_failure01_pct_query.json';data=json.loads(inp.read_text())
p=TomogramPlanner(Config(),'/task');mp=T/'global_coverage_v135_foxy/map.pickle';p.loadTomogram(tomogram_path=str(mp));p.planner.set_reference_height(.3)
goal=[1.954685200623011,-2.9868112220934897,4.5330305099487305]
rows=[]
for row in data['poses']:
 pos=row['data']['pose']['pose']['position'];start=np.array([pos[k] for k in 'xyz']);start[2]-=.3
 original=p.plan(start,goal,optimize=True);cell=p.cell_info(start);snap=p.snap_to_traversable(start,radius_cells=3)
 result={'source_clock_ns':row['clock_ns'],'ground_start':start.tolist(),'cell':{k:v.tolist() if hasattr(v,'tolist') else v for k,v in cell.items()},'original_route':original is not None}
 if snap is not None:
  nearby=p.plan(snap[0],goal,optimize=True);result.update(snapped_start=snap[0].tolist(),snap_distance_m=float(snap[2]),snapped_route=nearby is not None)
 rows.append(result)
out={'map_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'rows':rows,'claim':'Real native PCT with recorded body samples; exact historical RPC schedule is not reconstructed. A route from a snapped start omits the physical connector and is diagnostic only.'}
(T/'evidence/v162_pct_replay.json').write_text(json.dumps(out,indent=2)+'\n');print('PCT_REPLAY '+json.dumps(out))
