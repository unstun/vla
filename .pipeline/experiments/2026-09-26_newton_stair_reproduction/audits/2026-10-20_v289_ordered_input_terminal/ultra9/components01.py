"""Qualify the rebuilt native components before new-host input/scored gates."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v289_20261020')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSION = EXP / 'versions/v289'
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    tag = os.environ.get('V289_COMPONENTS_ID', '01')
    assert len(tag) == 2 and tag.isdigit()
    output = ROOT / 'evidence' / ('components' + tag + '.json')
    assert not output.exists()
    assert json.loads((ROOT / 'evidence/build02_closed.json').read_text())['passed']
    inventory = json.loads((ROOT / 'native/source_inventory.json').read_text())
    assert sha(ROOT / 'native/source_inventory.json') == sha(VERSION / 'source_inventory.json')
    for rel, expected in inventory.items():
        assert sha(ROOT / 'native' / rel) == expected, rel
    evaluation = ROOT / 'evaluation03'
    evaluation.mkdir(exist_ok=True)
    for name in ['ros_home', 'ros_logs']:
        (evaluation / name).mkdir(exist_ok=True)
    # Nested mounts need an existing destination under the read-only /task bind.
    (ROOT / 'generic_mechanisms_v259/native/fixtures').mkdir(parents=True, exist_ok=True)
    common = 'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && '
    common += 'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=154 ROS_LOCALHOST_ONLY=1 '
    common += 'ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct && '
    common += 'export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json TERRAIN_TEST_DIRECTORY=/work/fixtures/building TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml FEEDBACK_OUTPUT=/work/feedback_output && '
    commands = [('probe_build', 'cmake -S /source -B /evaluation/build '
        '-DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions '
        '-DCMAKE_BUILD_TYPE=Release && cmake --build /evaluation/build -j2'),
        ('field', '/evaluation/build/field_probe'),
        ('work', '/evaluation/build/work_probe'),
        ('repair', '/evaluation/build/repair_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'),
        ('terrain', '/evaluation/build/terrain_search_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'),
        ('continuity', '/evaluation/build/continuity_probe'),
        ('unit', 'cd /work && colcon --log-base logs/test01 test --base-paths src --executor sequential --event-handlers console_direct+ --return-code-on-test-failure && colcon test-result --verbose')]
    regression = (VERSION / 'native_regressions.sh').read_text()
    regression = '\n'.join(line for line in regression.splitlines()
        if not (line.startswith('source /task/') and line.endswith('/install/setup.bash')))
    script = evaluation / 'regressions.sh'
    script.write_text(regression + '\n')
    commands.append(('regressions', '/bin/bash /evaluation/regressions.sh'))
    result = dict(stage='running', physics_steps=0, source_files=len(inventory),
        source_inventory_sha256=sha(VERSION / 'source_inventory.json'), image=IMAGE,
        adapter_sha256=sha(Path(__file__)),
        source_unchanged=True, input_scope='Copied legacy fixtures for component tests only; immutable v288 final geometry and53 scored inputs reused; current binaries rechecked', checks=[])
    output.write_text(json.dumps(result, indent=2) + '\n')
    for name, shell in commands:
        log = ROOT / 'evidence' / ('components' + tag + '_' + name + '.log')
        command = ['docker', 'run', '--rm', '--pull=never', '--name', 'v289-ultra9-' + tag + '-' + name,
            '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g', '--network=host',
            '-e', 'ROS_HOME=/evaluation/ros_home', '-e', 'ROS_LOG_DIR=/evaluation/ros_logs',
            '-v', str(ROOT) + ':/task:ro', '-v', str(ROOT / 'native') + ':/work:rw',
            '-v', str(evaluation) + ':/evaluation:rw', '-v', str(VERSION) + ':/source:ro',
            '-v', str(EXP / 'versions/v224') + ':/task/source_v224:ro',
            '-v', str(ROOT / 'native/component_fixtures03') + ':/task/generic_mechanisms_v259/native/fixtures:ro',
            '-v', str(ROOT / 'native/component_fixtures03') + ':/work/fixtures:ro',
            '--entrypoint', '/bin/bash', IMAGE, '-c', common + shell]
        began = time.monotonic()
        with log.open('x') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
        result['checks'].append(dict(name=name, returncode=code, wall_s=time.monotonic() - began,
            log=str(log), sha256=sha(log)))
        result['stage'] = name if code == 0 else 'failed'
        output.write_text(json.dumps(result, indent=2) + '\n')
        if code:
            raise SystemExit(code)
    result.update(stage='passed', completed_utc_s=time.time())
    output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
