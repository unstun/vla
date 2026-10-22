"""Build the unchanged53 evaluator and check geometry/start contracts."""
from pathlib import Path
import csv
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
    tag=os.environ.get('V290_EVALUATORS_ID','01')
    receipt = R/f'evidence/evaluators{tag}.json'
    assert not receipt.exists()
    result = dict(physics_steps=0, checks=[], stage='running')
    commands = [('build', 'cmake --build /evaluation/build -j2 --target native_probe geometry_contract_probe spawn_margin'),
        ('geometry', '/evaluation/build/geometry_contract_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error'),
        ('starts', '/evaluation/build/spawn_margin /parent/cohort/queries.txt /evaluation/starts.csv')]
    for name, shell in commands:
        command = ['docker', 'run', '--rm', '--pull=never', '--name', 'v290-evaluators-'+tag+'-'+name,
            '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g', '--network=host',
            '-e', 'ROS_HOME=/evaluation/ros_home', '-e', 'ROS_LOG_DIR=/evaluation/ros_logs',
            '-v', str(R/'native')+':/work:ro', '-v', str(P)+':/parent:ro',
            '-v', str(P/'native/fixtures')+':/work/fixtures:ro', '-v', str(R/'source')+':/source:ro',
            '-v', str(R/'evaluation')+':/evaluation:rw',
            '-v', str(P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v224')+':/task/source_v224:ro',
            '--entrypoint', '/bin/bash', IMAGE, '-c',
            'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && '
            'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=157 ROS_LOCALHOST_ONLY=1 && '+shell]
        log = R/f'evidence/evaluators{tag}_{name}.log'
        began = time.monotonic()
        with log.open('x') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
        result['checks'].append(dict(name=name, returncode=code, wall_s=time.monotonic()-began,
            command=command, sha256=sha(log)))
        result['stage'] = name if code == 0 else 'failed'
        receipt.write_text(json.dumps(result, indent=2)+'\n')
        if code:
            raise SystemExit(code)
    rows = list(csv.DictReader((R/'evaluation/starts.csv').open()))
    assert len(rows) == 50
    assert all(int(x['support_verdict']) == 0 and min(float(x['edge_margin']), float(x['solid_margin'])) >= .1 for x in rows)
    result.update(stage='passed', legal_starts=50, minimum_extra_support_m=min(float(x['edge_margin']) for x in rows),
        minimum_extra_solid_m=min(float(x['solid_margin']) for x in rows), starts_sha256=sha(R/'evaluation/starts.csv'))
    receipt.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
