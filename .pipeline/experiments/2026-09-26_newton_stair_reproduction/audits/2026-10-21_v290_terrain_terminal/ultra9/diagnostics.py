"""Run parent/candidate captured-map and actual-controller comparisons."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    tag = os.environ.get('V290_DIAGNOSTICS_ID', '01')
    receipt = R / f'evidence/diagnostics{tag}.json'
    assert not receipt.exists()
    assert json.loads((R / ('evidence/components03.json' if tag=='01' else 'evidence/components05.json')).read_text())['stage'] == 'passed'
    result = dict(physics_steps=0, checks=[], stage='running', image=IMAGE,
        source_inventory_sha256=sha(R / 'source/source_inventory.json'))
    for parent in ([True, False] if tag=='01' else [False]):
        label = 'parent' if parent else 'candidate'
        evaluation = R / ('parent_control' if parent else 'evaluation')
        work = P / 'native' if parent else R / 'native'
        for case in ['A04', 'G05', 'CU06', 'CM02', 'CD12']:
            out = R / ('captured_results' if tag=='01' else 'captured_results'+tag) / label / case
            out.mkdir(parents=True, exist_ok=False)
            common = ('source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && '
                'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=156 ROS_LOCALHOST_ONLY=1 && ')
            if case == 'CD12':
                shell = ('TRACKING_INPUT=/input/CD12/events.txt TRACKING_OUTPUT=/output/commands.csv '
                    '/evaluation/build/captured_tracking_probe --ros-args --params-file /input/CD12/profile.yaml --log-level error')
            else:
                shell = ('CAPTURE_INPUT=/input/' + case + ' CAPTURE_OUTPUT=/output '
                    '/evaluation/build/captured_search_probe --ros-args --params-file /input/' + case + '/profile.yaml --log-level error')
            command = ['docker', 'run', '--rm', '--pull=never', '--name', 'v290-diag-' + label + '-' + case,
                '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g', '--network=host',
                '-e', 'ROS_HOME=/evaluation/ros_home', '-e', 'ROS_LOG_DIR=/evaluation/ros_logs',
                '-v', str(work) + ':/work:ro', '-v', str(P / 'native/fixtures') + ':/work/fixtures:ro',
                '-v', str(evaluation) + ':/evaluation:rw', '-v', str(R / 'captured') + ':/input:ro',
                '-v', str(out) + ':/output:rw', '--entrypoint', '/bin/bash', IMAGE, '-c', common + shell]
            log = R / f'evidence/diagnostics{tag}_{label}_{case}.log'
            begin = time.monotonic()
            with log.open('x') as stream:
                code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
            result['checks'].append(dict(parent=parent, case_id=case, returncode=code,
                wall_s=time.monotonic()-begin, command=command, log=str(log), sha256=sha(log)))
            result['stage'] = label + '_' + case if code == 0 else 'failed'
            receipt.write_text(json.dumps(result, indent=2) + '\n')
            if code:
                raise SystemExit(code)
    result.update(stage='passed', finished_utc_s=time.time())
    receipt.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
