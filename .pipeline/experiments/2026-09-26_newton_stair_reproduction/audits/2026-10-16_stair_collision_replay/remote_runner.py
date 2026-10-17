"""Bounded execution of task-owned offline diagnostics on gpu5070ti."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import subprocess

ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
TASK=ROOT.parent


def run(name,command,timeout=600):
    log=ROOT/'logs'/(name+'.log')
    if log.exists():raise ValueError('Preserve existing attempt: '+str(log))
    with log.open('w') as f:
        result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    print(json.dumps({'stage':name,'exit_code':result.returncode,'tail':log.read_text()[-4500:]}),flush=True)
    return result.returncode


def docker(image,command):
    return ['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
        '--user',str(os.getuid())+':'+str(os.getgid()),
        '-e','ROS_LOG_DIR=/audit/ros_logs','-e','ROS_HOME=/audit/ros_home',
        '-e','ROS_DOMAIN_ID=223','-e','REPLAY_INPUT=/audit/input','-e','REPLAY_OUTPUT=/audit/output/native',
        '-v',str(TASK)+':/task:ro','-v',str(TASK/'starvation_recovery_v219')+':/work:ro',
        '-v',str(ROOT)+':/audit:rw','--entrypoint','/bin/bash',image,*command]


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['prepare_build','probe'],required=True);p.add_argument('--attempt',default='01');a=p.parse_args()
    s=ROOT/'source'
    for n,h in json.loads((s/'source_manifest.json').read_text()).items():
        assert hashlib.sha256((s/n).read_bytes()).hexdigest()==h,n
    for n in ['ros_logs','ros_home','logs','output']:(ROOT/n).mkdir(exist_ok=True)
    image=subprocess.check_output(['docker','image','inspect','5a41a25fb20b','--format','{{.Id}}'],text=True).strip()
    (ROOT/'environment.json').write_text(json.dumps({'image':image,'host':'gpu5070ti'},indent=2)+'\n')
    if a.stage=='prepare_build':
        commands=[('prepare'+a.attempt,['/home/sun/vla_exec/envs/newton_worker/bin/python',str(s/'prepare_inputs.py'),'--output',str(ROOT/'input')]),
                  ('build'+a.attempt,docker(image,['/audit/source/build.sh']))]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda x:run(*x),commands))
        raise SystemExit(max(results))
    script='source /opt/ros/foxy/setup.bash\nsource /task/command_continuity_v206_20261015/install/setup.bash\nsource /task/starvation_recovery_v219/install/setup.bash\n/audit/build/collision_probe --ros-args --params-file /audit/input/planner.yaml --log-level error\n'
    (s/'run_probe.sh').write_text('set -eo pipefail\n'+script)
    raise SystemExit(run('probe'+a.attempt,docker(image,['/audit/source/run_probe.sh']),900))


if __name__=='__main__':main()
