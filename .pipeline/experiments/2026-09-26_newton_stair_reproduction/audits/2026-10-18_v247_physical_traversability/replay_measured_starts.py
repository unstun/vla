"""Read-only actual installed A* replay: nominal and measured post-PD poses."""
from pathlib import Path
import hashlib,json,math,os,re,subprocess,sys
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1]
BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'physical_traversability_v247/native'
OUT=BASE/'generalization_v248/measured_start_replay01';OUT.mkdir(exist_ok=False)
sys.path.insert(0,str(EXP/'versions/v196'))
from analyze_remote import Capture
inputs=[];requests=[]
for cid in ('A02','G07','R11'):
 cap=Capture(BASE/f'trials/v248_{cid}_attempt01/runs/v248_{cid}_attempt01')
 scenario=cap.json('inputs/stair_scenario.json');driver=cap.json('artifacts/stair_driver_result.json')
 snap=next(r for r in driver['journal'] if r['event']=='goal_request')['initial_snapshot']
 w,x,y,z=snap['measured']['base_quat_wxyz'];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
 goal=list(scenario['goal_ground_xyz_m']);goal[2]+=.3
 nominal=list(scenario['spawn_ground_xyz_m']);nominal[2]+=.3
 for label,start,heading in [('nominal',nominal,scenario['spawn_yaw_rad']),('measured',snap['measured']['base_xyz'],yaw)]:
  p=OUT/(cid+'_'+label+'.txt');p.write_text(' '.join(map(str,start+goal+[heading]))+'\n');inputs.append('/evaluation/'+p.name)
  requests.append(dict(case_id=cid,label=label,start_body_xyz=start,yaw=heading,goal_body_xyz=goal,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(OUT/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /work/install/setup.bash && export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 && /task/physical_traversability_v247/evaluation/build/graph_probe '+' '.join(inputs)
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=6','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(WORK)+':/work:ro','-v',str(OUT)+':/evaluation:rw','-v',str(BASE/'physical_traversability_v247/evaluation/support')+':/evaluation/support:ro','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]
with (OUT/'stdout.log').open('x') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
text=(OUT/'stdout.log').read_text();summary=dict(exit_code=result.returncode,requests=requests,graph_results=re.findall(r'^GRAPH .*$',text,re.M),endpoint_results=re.findall(r'^ENDPOINT .*$',text,re.M),diagnostic_only=True,physics_steps=0,source='Unmodified v247 installed graph_probe and native libraries')
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if result.returncode:raise SystemExit(result.returncode)
