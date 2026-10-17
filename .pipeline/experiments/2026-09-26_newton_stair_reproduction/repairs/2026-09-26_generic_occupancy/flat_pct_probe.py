from pathlib import Path
import json
from dataclasses import asdict
from backend_adapter.pct_worker import NativePctConfig, NativePctPlanner
from backend_adapter.contracts import PlannerRequest
base=Path("/repro")
scene=base/"repairs/2026-09-26_generic_occupancy/flat_inputs_v2/flat_floor.pickle"
planner=NativePctPlanner(NativePctConfig(base/"runtime_sources/pct_runtime/python", "/repro/inputs",tomogram_path=str(scene)), reference_height_m=.3)
route=planner.plan(PlannerRequest("flat-map-probe","goal",(0.,0.,0.),(3.,0.,0.),"world","flat",1,start_layer=0,target_layer=0,optimize=True))
assert len(route.waypoints_m)>=2
assert abs(route.waypoints_m[-1][0]-3)<.11
assert all(abs(p[2]-.3)<1e-6 for p in route.waypoints_m)
print("FLAT_PCT_RESULT "+json.dumps({"passed":True,"route":asdict(route)}))
