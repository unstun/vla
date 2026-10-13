"""Actual FSM fallback + original due-body queue under a controlled long search."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--version',choices=('v132','v133'),required=True)
    parser.add_argument('--attempt',type=int,default=1)
    args=parser.parse_args()
    out=TASK/f'results/recovery_refresh_contract/{args.version}_{args.attempt:02d}'
    out.mkdir(parents=True,exist_ok=False);(out/'ros_logs').mkdir()
    workspace='recovery_'+args.version
    receipt=json.loads((TASK/'results'/workspace/'candidate_receipt.json').read_text())
    remote=lambda p:'/task/'+str(p.relative_to(TASK))
    source='/repo/'+str(HERE.relative_to(TASK/'repo'))
    script=f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/{workspace}/install/setup.bash
cmake -S {source}/refresh_contract -B {remote(out)}/build -DVERSIONS_ROOT={source}/../../versions
cmake --build {remote(out)}/build -j2
for mode in 0 1 2; do
  REFRESH_CASE=$mode {remote(out)}/build/refresh_probe --ros-args --params-file {source}/../../versions/v131/building_planner.yaml --log-level error
done
'''
    (out/'run.sh').write_text(script)
    command=['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
             '-e','ROS_DOMAIN_ID=196','-e','ROS_LOG_DIR='+remote(out/'ros_logs'),
             '-e','REPLAY_INPUT=/task/recovery_admission_replay/input',
             '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro',
             '--entrypoint','/bin/bash',receipt['image_id'],remote(out/'run.sh')]
    with (out/'run.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    lines=[s for s in (out/'run.log').read_text().splitlines() if s.startswith('REFRESH_CASE')]
    assert len(lines)==3
    cases=[{k:float(v) for k,v in re.findall(r'(\w+)=([-\d.e+]+)',s)} for s in lines]
    expected=1 if args.version=='v133' else 0
    assert cases[0]['accepted']==expected and cases[0]['due_body_applied']==expected
    assert all(c['accepted']==0 and c['due_body_applied']==0 for c in cases[1:])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'passed':True,'version':args.version,'cases':cases,'input_identity_sha256':sha(TASK/'recovery_admission_replay/input/identity.json'),
            'probe_sha256':sha(HERE/'refresh_contract/refresh_probe.cpp'),'script_sha256':sha(Path(__file__)),
            'scope':'Actual installed FSM/helper/map/due-body queue; goal search is replaced by a controlled 120ms ROS-clock advance and failure. Constructed future body stays queued until due. This is a component regression, not physical acceptance.'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
