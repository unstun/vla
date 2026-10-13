"""Actual native PCT: recorded singleton rejection must not kill the worker."""
from pathlib import Path
import argparse,copy,json,sys
import numpy as np
from ament_index_python.packages import get_package_prefix
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'runtime_sources/backend_adapter'))
from backend_adapter.pct_worker import NativePctPlanner,NativePctConfig
from backend_adapter.contracts import PlannerRequest
from pct_planner.config import Config
from pct_planner.planner_wrapper import TomogramPlanner
p=argparse.ArgumentParser();p.add_argument('--old-crash',action='store_true');a=p.parse_args()
data=json.loads((Path(__file__).parent/'goal_failure_input.json').read_text())
root=Path(get_package_prefix('pct_planner'))/'lib/python3.8/site-packages';mp=Path('/task/global_coverage_v135_foxy/map.pickle')
worker=NativePctPlanner(NativePctConfig(root,'/task',tomogram_path=str(mp)),.3)
request=PlannerRequest('near-goal','goal',tuple(data['start_ground_xyz']),tuple(data['goal_ground_xyz']),'world','stair_reactive_coverage_v135',1,optimize=True)
worker._planner.plan(request.start_xyz_m,request.target_xyz_m,optimize=False)
points=worker._planner.planner.get_path_finder().get_result_matrix();assert len(points)==1
print('RECORDED_SINGLETON_NATIVE_ASTAR '+str(points.tolist()),flush=True)
if a.old_crash:
 worker.plan(request)
 raise RuntimeError('Old binary unexpectedly survived')
results=[]
for quintic in [True,False]:
 cfg=copy.deepcopy(Config());cfg.planner.use_quintic=quintic
 worker._planner=TomogramPlanner(cfg,'/task');worker._planner.loadTomogram(tomogram_path=str(mp))
 for position in [request.start_xyz_m,request.target_xyz_m]:
  q=PlannerRequest('short','goal',position,request.target_xyz_m,'world','stair_reactive_coverage_v135',1,optimize=True)
  try:worker.plan(q)
  except ValueError as e:assert str(e)=='pct_no_route',str(e)
  else:raise AssertionError('Degenerate route falsely accepted')
 original=(-5.545314788818359,6.01318883895874,0.05804443359375)
 q=PlannerRequest('full','goal',original,request.target_xyz_m,'world','stair_reactive_coverage_v135',1,optimize=True)
 route=worker.plan(q);assert len(route.waypoints_m)>2 and np.isfinite(route.waypoints_m).all()
 # A previous valid optimizer result must not leak through a subsequent rejection.
 try:worker.plan(request)
 except ValueError as e:assert str(e)=='pct_no_route',str(e)
 else:raise AssertionError('Stale optimizer result escaped')
 results.append({'quintic':quintic,'full_route_points':len(route.waypoints_m),'short_requests_rejected':3,'worker_survived':True})
print('PCT_DEGENERATE_REGRESSION_PASS '+json.dumps(results),flush=True)
