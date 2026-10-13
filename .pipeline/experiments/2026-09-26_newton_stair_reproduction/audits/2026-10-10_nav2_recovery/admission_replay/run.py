"""Run isolated recorded-route geometry/clock counterfactuals after timed trials."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    assert not subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).strip()
    out = TASK / f'results/recovery_route_diagnosis/replay{args.attempt:02d}'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ros_logs').mkdir()
    source = '/repo/' + str(HERE.relative_to(TASK / 'repo'))
    remote = lambda p: '/task/' + str(p.relative_to(TASK))
    receipt = json.loads((TASK / 'results/recovery_v131/candidate_receipt.json').read_text())
    script = f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v131/install/setup.bash
cmake -S {source} -B {remote(out)}/build -DVERSIONS_ROOT={source}/../../../versions
cmake --build {remote(out)}/build -j2
{remote(out)}/build/admission_probe --ros-args --params-file {source}/../../../versions/v131/building_planner.yaml --log-level error
'''
    (out / 'run.sh').write_text(script)
    command = ['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
               '-e','ROS_DOMAIN_ID=197','-e','ROS_LOG_DIR='+remote(out/'ros_logs'),
               '-e','REPLAY_INPUT=/task/recovery_admission_replay/input',
               '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro',
               '--entrypoint','/bin/bash',receipt['image_id'],remote(out/'run.sh')]
    with (out / 'run.log').open('w') as stream:
        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
    lines = [s for s in (out/'run.log').read_text().splitlines() if s.startswith('ADMISSION_')]
    assert len([s for s in lines if s.startswith('ADMISSION_CASE')]) == 6
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = {'completed': True, 'cases': lines, 'image_id': receipt['image_id'],
              'input_identity_sha256': sha(TASK/'recovery_admission_replay/input/identity.json'),
              'probe_sha256': sha(HERE/'admission_probe.cpp'), 'script_sha256': sha(Path(__file__)),
              'scope': 'Reconstructed geometry and explicit clock counterfactuals. Not original asynchronous DDS scheduling or navigation acceptance.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
