import json,subprocess
from pathlib import Path
out=Path('/attempt');results=[]
for name,override in [('minimum_above_maximum','manager.min_cruise_speed:=1.1'),('negative_minimum','manager.min_cruise_speed:=-0.1'),('invalid_acceleration','manager.max_acc:=0.0')]:
 cmd=['ros2','run','scan_planner','scan_planner_node','--ros-args','--params-file','/version/flat_planner.yaml','-p',override]
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
 text=p.stdout+p.stderr;(out/(name+'.log')).write_text(text)
 results.append({'case':name,'exit_code':p.returncode,'passed':p.returncode!=0 and 'Invalid minimum cruise speed or nominal dynamic limits' in text})
(out/'checks.json').write_text(json.dumps({'passed':all(r['passed'] for r in results),'cases':results},indent=2)+'\n')
assert all(r['passed'] for r in results),results
