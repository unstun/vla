"""Actual native parent/candidate checks in private zero-physics containers."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
VERSIONS = '/parent/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    tag = os.environ.get('V290_CHECK_ID', '01')
    out = R / f'evidence/components{tag}.json'
    assert not out.exists()
    report = dict(physics_steps=0, checks=[], stage='running',
        source_inventory_sha256=sha(R / 'source/source_inventory.json'), image=IMAGE)
    def run(label, shell, parent=False, expected_failure=False):
        evaluation = R / ('parent_control' if parent else 'evaluation')
        for name in ['ros_home', 'ros_logs']:
            (evaluation / name).mkdir(parents=True, exist_ok=True)
        work = P / 'native' if parent else R / 'native'
        common = 'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && '
        common += ('export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=155 ROS_LOCALHOST_ONLY=1 '
            'ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct '
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json '
            'TERRAIN_TEST_DIRECTORY=/work/fixtures/building TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml '
            'TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml '
            'FEEDBACK_OUTPUT=/evaluation/feedback_output && ')
        command = ['docker', 'run', '--rm', '--pull=never', '--name', 'v290-' + tag + '-' + label,
            '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g', '--network=host',
            '-e', 'ROS_HOME=/evaluation/ros_home', '-e', 'ROS_LOG_DIR=/evaluation/ros_logs',
            '-v', str(work) + (':/work:ro' if parent else ':/work:rw'),
            '-v', str(P) + ':/parent:ro', '-v', str(R / 'source') + ':/source:ro',
            '-v', str(evaluation) + ':/evaluation:rw',
            '-v', str(P / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v224') + ':/task/source_v224:ro',
            '-v', str(P / 'native/component_fixtures03') + ':/work/fixtures:ro',
            '--entrypoint', '/bin/bash', IMAGE, '-c', common + shell]
        log = R / f'evidence/components{tag}_{label}.log'
        began = time.monotonic()
        with log.open('x') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
        passed = (code != 0) if expected_failure else code == 0
        report['checks'].append(dict(name=label, passed=passed, returncode=code,
            expected_failure=expected_failure, wall_s=time.monotonic()-began,
            log=str(log), sha256=sha(log), command=command))
        report['stage'] = label if passed else 'failed'
        out.write_text(json.dumps(report, indent=2) + '\n')
        if not passed:
            raise SystemExit(1)
    build = ('cmake -S /source -B /evaluation/build -DCMAKE_BUILD_TYPE=Release -DVERSIONS_ROOT=' + VERSIONS +
        ' && cmake --build /evaluation/build -j2 --target terrain_search_probe repair_probe captured_search_probe captured_tracking_probe tracking_probe')
    run('build', build)
    params = ' --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error'
    for target in ['terrain_search_probe', 'repair_probe']:
        run(target, '/evaluation/build/' + target + params)
    run('tracking', '/evaluation/build/tracking_probe')
    run('unit', 'cd /work && colcon --log-base logs/test01 test --base-paths src --executor sequential '
        '--event-handlers console_direct+ --return-code-on-test-failure --ctest-args -E "^(cpplint|uncrustify|xmllint)$"')
    run('parent_build', build, parent=True)
    for target in ['terrain_search_probe', 'repair_probe']:
        run('parent_' + target, '/evaluation/build/' + target + params, parent=True, expected_failure=True)
    run('parent_tracking', '/evaluation/build/tracking_probe --gtest_filter=TrackingBehavior.TerminalApproachSlowsBeforeOriginalCaptureWithMatchedPhase',
        parent=True, expected_failure=True)
    report.update(stage='passed', finished_utc_s=time.time())
    out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
