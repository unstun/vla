"""Real installed PCT route feasibility before any physical deployment."""
from pathlib import Path
import json,hashlib
import pct_planner
from backend_adapter.pct_worker import NativePctPlanner,NativePctConfig
from backend_adapter.contracts import PlannerRequest
BASE=Path('/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction')
TASK=Path('/task');out=TASK/'global_coverage_v135_foxy'
result=[]
for name,path in [('original',BASE/'inputs/new_building.pickle'),('coverage',out/'map.pickle')]:
    planner=NativePctPlanner(NativePctConfig(Path(pct_planner.__file__).resolve().parents[1],str(path.parent),tomogram_path=str(path)),.3)
    request=PlannerRequest('probe','goal',(6.52730942,-5.91718912,3.39219332-.3),
        (1.954685200623011,-2.9868112220934897,4.5330305099487305),'world','stair_reactive',1,None,None,True)
    try:
        route=planner.plan(request);row={'variant':name,'route_found':True,'points':route.waypoints_m}
    except Exception as e:row={'variant':name,'route_found':False,'error':repr(e)}
    result.append(row)
report={'cases':result,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'claim':'Actual PCT feasibility; not physical navigation or native SCAN acceptance.'}
assert not (out/'pct_result.json').exists();(out/'pct_result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='points'} for r in result]))
