"""Build/test the private v291 overlay on ultra9; never launch physics."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path('/home/ubuntu/sun/vla_v291_20261022')
PARENT = Path('/home/ubuntu/sun/vla_v290_20261021')
FIXTURES = Path('/home/ubuntu/sun/vla_v289_20261020/native/component_fixtures03')
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'


def main():
    tag = sys.argv[1]
    evidence = ROOT / 'evidence' / tag
    evidence.mkdir(parents=True, exist_ok=False)
    native = ROOT / 'native'
    if not native.exists():
        shutil.copytree(PARENT / 'native', native, symlinks=True)
    shutil.copytree(ROOT / 'source/src', native / 'src', dirs_exist_ok=True)
    inventory = {str(p.relative_to(native)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (native / 'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (evidence / 'source_inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    prefix = ('source /opt/ros/foxy/setup.bash && '
              'export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 '
              'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MAKEFLAGS=-j2 ROS_DOMAIN_ID=161 ROS_LOCALHOST_ONLY=1 '
              'ROS_HOME=/work/ros_home ROS_LOG_DIR=/work/ros_logs && ')
    report = {'physics_steps': 0, 'stage': 'running', 'checks': [], 'image': IMAGE}
    for label, shell in [
        ('build', 'export CMAKE_PREFIX_PATH=/work/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-} && '
         'cd /work && colcon --log-base logs/v291-'+tag+' build --base-paths src --executor sequential '
         '--cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON '
         '-DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -g1 -fno-omit-frame-pointer" '
         '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DPython3_EXECUTABLE=/usr/bin/python3'),
        ('unit', 'source /work/install/setup.bash && '
         'export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct '
         'TERRAIN_TEST_MANIFEST=/work/fixtures/building/terrain.json TERRAIN_TEST_DIRECTORY=/work/fixtures/building '
         'TERRAIN_NATIVE_CONFIG=/work/fixtures/building_planner.yaml TERRAIN_NATIVE_PROFILE=/work/fixtures/component.scan.yaml '
         'TERRAIN_TEST_PROFILE=/work/fixtures/component.yaml FEEDBACK_OUTPUT=/evaluation/feedback_output && '
         'cd /work && colcon --log-base logs/v291-test-'+tag+' test --base-paths src --executor sequential '
         '--event-handlers console_direct+ --return-code-on-test-failure --ctest-args -E "^(cpplint|uncrustify|xmllint)$"')]:
        (ROOT / 'evaluation').mkdir(exist_ok=True)
        cmd = ['docker', 'run', '--rm', '--pull=never', '--name', 'v291-'+tag+'-'+label,
               '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g', '--network=host',
               '-v', str(native)+':/work:rw', '-v', str(FIXTURES)+':/work/fixtures:ro',
               '-v', str(ROOT/'evaluation')+':/evaluation:rw',
               '-v', '/home/ubuntu/sun/vla_v289_20261020/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v224:/task/source_v224:ro',
               '--entrypoint', '/bin/bash', IMAGE, '-c', prefix+shell]
        began = time.monotonic()
        with (evidence / (label+'.log')).open('x') as stream:
            code = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT).returncode
        report['checks'].append({'name':label,'returncode':code,'wall_s':time.monotonic()-began,'command':cmd})
        report['stage'] = label+'-passed' if code==0 else label+'-failed'
        (evidence/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
        print(label,code,flush=True)
        if code:
            raise SystemExit(code)
    report['stage']='passed'
    (evidence/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
