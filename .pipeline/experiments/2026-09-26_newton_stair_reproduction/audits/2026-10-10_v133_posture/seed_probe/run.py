from pathlib import Path
import hashlib,json,shutil,subprocess,sys
T=Path('/data/sun/vla_mppi_20261009');B=T/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';H=Path(__file__).resolve().parent
assert not subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).strip()
sys.path.insert(0,str(B/'versions/v127'))
from analyze_remote import Capture
out=T/'results/v133_posture/seed_probe02';out.mkdir(exist_ok=False);inp=out/'input'
shutil.copytree(T/'body_envelope_replay/input',inp)
c=Capture(T/'trials/v137_candidate_attempt03/runs/v137_candidate_attempt03');lines=c.read('nav2.log').splitlines();start=next(i for i,s in enumerate(lines) if 'V132_REFERENCE_ADMISSION generation=2' in s)
seed=None
for l in lines[start:]:
 if 'spline_seed_capture ' in l:seed=json.loads(l.split('spline_seed_capture ',1)[1])
 if 'final_spline_rejected' in l and seed:break
assert seed
(inp/'seed.txt').write_text(str(seed['interval'])+' '+str(len(seed['points']))+'\n'+'\n'.join(' '.join(map(str,p)) for p in seed['points']+seed['derivatives'])+'\n')
(out/'seed.json').write_text(json.dumps({'seed':seed,'rejection':l,'capture_sources':c.sources},indent=2)+'\n')
remote=lambda p:'/task/'+str(p.relative_to(T))
source=remote(H);versions=remote(B/'versions')
script='set -eo pipefail\nsource /opt/ros/foxy/setup.bash\nsource /task/recovery_v137/install/setup.bash\ncmake -S '+source+' -B '+remote(out/'build')+' -DVERSIONS_ROOT='+versions+'\ncmake --build '+remote(out/'build')+' -j2\n'+remote(out/'build/envelope_probe')+' --ros-args --params-file '+versions+'/v137/building_planner.yaml --log-level error\n'
(out/'run.sh').write_text(script)
receipt=json.loads((T/'results/recovery_v137/candidate_receipt.json').read_text())
cmd=['docker','run','--rm','--network=none','--cpus=4','--memory=8g','-e','ROS_DOMAIN_ID=197','-e','REPLAY_INPUT='+remote(inp),'-v',f'{T}:/task:rw','--entrypoint','/bin/bash',receipt['image_id'],remote(out/'run.sh')]
with (out/'run.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
print('\n'.join(l for l in (out/'run.log').read_text().splitlines() if l.startswith('SEED_RESULT')))
