#!/usr/bin/env python3
"""Build and replay a bounded native SCAN diagnostic in an isolated container."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


ROOT = Path(__file__).resolve().parent
SCAN = Path('/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03')
IMAGE = 'e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8'
OUTPUT = ROOT / 'artifacts'
NAME = 'vla-scan-diagnosis-' + ROOT.name.lower().replace('_', '-')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(cmd, log, timeout):
    started = time.monotonic()
    with log.open('w') as stream:
        result = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    return {'command': cmd, 'returncode': result.returncode, 'wall_seconds': time.monotonic() - started}


def main():
    OUTPUT.mkdir(exist_ok=False)
    result = {'scope': 'Native SCAN dynamics-only minimized replay; no Isaac, controller or physical driver'}
    try:
        package = json.loads((ROOT / 'package_manifest.json').read_text())
        assert all(digest(ROOT / p) == h for p, h in package.items()), 'package source mismatch'
        native = json.loads((ROOT / 'inputs/scan_source_identity.json').read_text())
        installed = json.loads((ROOT / 'inputs/scan_install_identity.json').read_text())['installed_files']
        assert all(digest(SCAN / p) == h for p, h in native.items()), 'SCAN source mismatch'
        assert all(digest(SCAN / p) == h for p, h in installed.items()), 'SCAN installed library mismatch'
        result['source_gate'] = {'package_files': len(package), 'scan_source_files': len(native),
                                 'scan_installed_files': len(installed), 'all_match': True}
        work = ROOT / 'work'
        (work / 'src').mkdir(parents=True)
        shutil.copytree(ROOT / 'native_repro/scan_replan_native_repro', work / 'src/scan_replan_native_repro')
        common = ['podman', 'run', '--rm', '--pull=never', '--network=none', '--name', NAME,
                  '-e', 'CMAKE_BUILD_PARALLEL_LEVEL=2', '-e', 'MAKEFLAGS=-j2',
                  '-v', str(work) + ':/ws:rw', '-v', str(SCAN) + ':/scan_03:ro',
                  '-v', str(ROOT / 'inputs') + ':/inputs:ro',
                  '-v', str(ROOT / 'manager') + ':/manager:ro',
                  '-v', str(OUTPUT) + ':/out:rw',
                  '-v', str(ROOT / 'container_cases.py') + ':/container_cases.py:ro']
        build = '''set -e
source /opt/ros/foxy/setup.bash
source /scan_03/install/setup.bash
cd /ws
colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DSCAN03_SOURCE_ROOT=/scan_03 -DSCAN_MANAGER_CPP=/manager/planner_manager.cpp
'''
        result['build'] = command(common + [IMAGE, 'bash', '-lc', build], OUTPUT / 'build.log', 180)
        if result['build']['returncode'] != 0:
            raise RuntimeError('Native diagnostic build failed')
        exe = work / 'install/scan_replan_native_repro/lib/scan_replan_native_repro/rebound_replan_repro'
        result['executable_sha256'] = digest(exe)
        run = '''set -e
source /opt/ros/foxy/setup.bash
source /scan_03/install/setup.bash
source /ws/install/setup.bash
export ROS_DOMAIN_ID=96
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
python3 /container_cases.py
'''
        result['replay'] = command(common + [IMAGE, 'bash', '-lc', run], OUTPUT / 'replay.log', 120)
        result['replay_completed'] = result['replay']['returncode'] == 0
        result['scan_source_unchanged'] = all(digest(SCAN / p) == h for p, h in native.items())
        result['package_source_unchanged'] = all(digest(ROOT / p) == h for p, h in package.items())
    except Exception as error:
        result['error'] = repr(error)
    finally:
        removal = subprocess.run(['podman', 'rm', '-f', '-t', '2', NAME], capture_output=True, text=True, timeout=15)
        result['cleanup'] = {'returncode': removal.returncode, 'stderr': removal.stderr}
        remains = subprocess.run(['podman', 'container', 'exists', NAME], capture_output=True, text=True)
        result['owned_container_absent'] = remains.returncode == 1
        write_json(OUTPUT / 'result.json', result)
        hashes = {str(p.relative_to(OUTPUT)): digest(p) for p in OUTPUT.rglob('*') if p.is_file()}
        write_json(OUTPUT / 'artifact_hashes.json', hashes)
    print(json.dumps({k: v for k, v in result.items() if k not in {'build', 'replay'}}, indent=2), flush=True)
    return 0 if result.get('replay_completed') and result.get('owned_container_absent') else 1


if __name__ == '__main__':
    raise SystemExit(main())
