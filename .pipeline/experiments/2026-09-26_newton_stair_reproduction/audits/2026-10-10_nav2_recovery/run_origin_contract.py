"""Test the actual native route callback against independent prior start states."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('parent', 'candidate'), required=True)
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    out = TASK / f'results/recovery_origin_contract/{args.variant}{args.attempt:02d}'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ros_logs').mkdir()
    workspace = 'recovery_v129' if args.variant == 'parent' else 'recovery_v130'
    receipt = json.loads((TASK / 'results' / workspace / 'candidate_receipt.json').read_text())
    remote = lambda p: '/task/' + str(p.relative_to(TASK))
    source = '/repo/' + str(HERE.relative_to(TASK / 'repo'))
    script = f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/{workspace}/install/setup.bash
cmake -S {source}/origin_contract -B {remote(out)}/build
cmake --build {remote(out)}/build -j2
set +e
{remote(out)}/build/origin_probe --ros-args --params-file {source}/../../versions/v128/building_planner.yaml --log-level error
code=$?
set -e
test "$code" = {1 if args.variant == 'parent' else 0}
'''
    (out / 'run.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--network=none', '--cpus=4', '--memory=8g',
               '-e', 'ROS_DOMAIN_ID=198', '-e', 'ROS_LOG_DIR=' + remote(out / 'ros_logs'),
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', f'{TASK}:/task:rw',
               '-v', f'{TASK}/repo:/repo:ro', '--entrypoint', '/bin/bash', receipt['image_id'], remote(out / 'run.sh')]
    with (out / 'run.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    text = (out / 'run.log').read_text()
    result = re.search(r'ORIGIN_RESULT matched=(\d+) cases=(\d+) unknown_map_rejected=1', text)
    assert result and int(result[1]) == (int(result[2]) if args.variant == 'candidate' else 0)
    report = {'passed': True, 'variant': args.variant, 'matched_current_body': int(result[1]),
              'cases': int(result[2]), 'unknown_map_still_rejected': True,
              'native_output': [line for line in text.splitlines() if line.startswith('ORIGIN_')],
              'source_sha256': hashlib.sha256((HERE / 'origin_contract/origin_probe.cpp').read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Actual native route admission and AStar origin witness with constructed prior-state inputs; no physical acceptance.'}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
