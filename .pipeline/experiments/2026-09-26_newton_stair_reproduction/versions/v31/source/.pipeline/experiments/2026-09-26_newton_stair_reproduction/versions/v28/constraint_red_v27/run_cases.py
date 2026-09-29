from pathlib import Path
import json,subprocess
p=Path('/attempt');cases=['zero_then_valid_empty','valid_then_zero_empty','initial_zero_empty','empty_route','no_intersection','stale_intersection','zero_direction','rebound_stale_intersection','rebound_zero_direction','valid_then_zero','valid_constraints','no_collision','short_segment'];results={}
for case in cases:
 r=subprocess.run([str(p/'build/contract'),case],capture_output=True,text=True,timeout=10)
 (p/(case+'.log')).write_text(r.stdout+r.stderr);results[case]={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
(p/'case_results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({k:v['exit_code'] for k,v in results.items()},indent=2))
