from pathlib import Path
import json,math
from backend_adapter.pct_worker import NativePctPlanner,NativePctConfig
from backend_adapter.contracts import PlannerRequest
base=Path('/base')
planner=NativePctPlanner(NativePctConfig(base/'runtime_sources/pct_runtime/python',str(base/'inputs'),tomogram_path=str(base/'inputs/new_building.pickle')),reference_height_m=.30)
start=(-5.545314788818359,6.01318883895874,.05804443359375)
goal=(1.954685200623011,-2.9868112220934897,4.5330305099487305)
results={}
for label,layer in [('fixed_one',1),('native_auto',None)]:
 try:
  request=PlannerRequest('full-'+label,'goal',start,goal,'world','stair_reactive',1,optimize=True,start_layer=layer,target_layer=layer)
  route=planner.plan(request);pts=route.waypoints_m
  results[label]={'points':len(pts),'xy_length_m':sum(math.dist(x[:2],y[:2]) for x,y in zip(pts,pts[1:])),'first':pts[0],'last':pts[-1],'target_body_height_error_m':abs(pts[-1][2]-goal[2]-.30),'waypoints':pts}
 except Exception as exc:results[label]={'error':str(exc)}
Path('/audit/result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if x!='waypoints'} for k,v in results.items()},indent=2))
