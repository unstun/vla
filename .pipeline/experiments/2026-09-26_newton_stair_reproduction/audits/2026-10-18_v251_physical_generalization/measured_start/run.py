"""Fresh offline observation of the recorded A02 request; no physics or repair."""
from pathlib import Path
import hashlib,json,math,os,subprocess,sys
HERE=Path(__file__).resolve().parent;AUDIT=HERE.parent;EXP=AUDIT.parents[1]
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generalization_v252'/os.environ.get('MEASURED_TAG','measured_start01')
OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(EXP/'versions/v196'));from analyze_remote import Capture
raw=BASE/'trials/v252_A02_attempt01/runs/v252_A02_attempt01';capture=Capture(raw)
driver=capture.json('artifacts/stair_driver_result.json');event=next(r for r in driver['journal'] if r['event']=='goal_request')
measured=event['initial_snapshot']['measured'];w,x,y,z=measured['base_quat_wxyz']
yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
nominal=BASE/'generalization_v242/cases/A02/endpoints.txt';values=list(map(float,nominal.read_text().split()))
goal=[*event['payload']['target_ground_xyz']];goal[2]+=.3
assert max(abs(a-b) for a,b in zip(values[3:6],goal))<1e-5
(OUT/'input.txt').write_text('nominal '+' '.join(map(str,values))+'\nmeasured '+' '.join(map(str,measured['base_xyz']+goal+[yaw]))+'\n')
(OUT/'input_identity.json').write_text(json.dumps(dict(physical_run=str(raw),physics_steps=0,
 observer_files={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('run.py','measured_start.cpp','CMakeLists.txt')},
 source_driver_sha256=hashlib.sha256(capture.read('artifacts/stair_driver_result.json').encode()).hexdigest(),
 original_nominal_sha256=hashlib.sha256(nominal.read_bytes()).hexdigest(),
 recorded_goal_request=event),indent=2)+'\n')
source='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v251_physical_generalization/measured_start'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /task/physical_traversability_v247/native/install/setup.bash && source /work/install/setup.bash'
shell+=' && cmake -S '+source+' -B /output/build && cmake --build /output/build -j2 && /output/build/measured_start /output/input.txt /output'
raise SystemExit(subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=2','--memory=4g','-v',str(BASE)+':/task:ro','-v',str(BASE/'generic_mechanisms_v251/native')+':/work:ro',
 '-v',str(OUT)+':/output:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]).returncode)
