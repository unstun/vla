"""Actual DDS subscriptions and installed FSM work-boundary regression."""
from pathlib import Path
import argparse,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;TASK=Path('/data/sun/vla_mppi_20261009')
def main():
    p=argparse.ArgumentParser();p.add_argument('--version',choices=['v134','v136'],required=True);a=p.parse_args()
    out=TASK/('results/mission_inbox_contract/'+a.version+'_02');out.mkdir(parents=True,exist_ok=False);(out/'ros_logs').mkdir()
    source='/repo/'+str(HERE.relative_to(TASK/'repo'));remote=lambda p:'/task/'+str(p.relative_to(TASK))
    receipt=json.loads((TASK/f'results/recovery_{a.version}/candidate_receipt.json').read_text())
    script=f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_{a.version}/install/setup.bash
cmake -S {source} -B {remote(out)}/build -DVERSIONS_ROOT={source}/../..
cmake --build {remote(out)}/build -j2
{remote(out)}/build/inbox_probe --ros-args --params-file {source}/../building_planner.yaml --log-level error
'''
    (out/'run.sh').write_text(script)
    cmd=['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
        '-e','ROS_DOMAIN_ID=196','-e','ROS_LOCALHOST_ONLY=1','-e','ROS_LOG_DIR='+remote(out/'ros_logs'),
        '-e','REPLAY_INPUT=/task/mission_inbox_replay/input','-e','EXPECTED_FIXED='+('0' if a.version=='v134' else '1'),
        '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro','--entrypoint','/bin/bash',receipt['image_id'],remote(out/'run.sh')]
    with (out/'run.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    lines=[s for s in (out/'run.log').read_text().splitlines() if s.startswith('INBOX_CASE')]
    assert len(lines)==(3 if a.version=='v134' else 4)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    r={'passed':True,'native':a.version,'cases':lines,'input_identity_sha256':sha(TASK/'mission_inbox_replay/input/identity.json'),
       'probe_sha256':sha(HERE/'inbox_probe.cpp'),'log_sha256':sha(out/'run.log'),
       'boundary':'Actual DDS queue and installed FSM explicit work ticks, with original recorded geometry. Executor load order is deliberately controlled; no physical result claimed.'}
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
