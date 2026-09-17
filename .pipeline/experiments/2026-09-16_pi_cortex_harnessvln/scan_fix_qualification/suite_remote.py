#!/usr/bin/env python3
"""Remote worker: hash gate, build original and candidate variants, replay the suite, return hashes.

Runs on the execution host from a synced run package (modelled on
scan_replan_diagnosis/native_worker.py). Both variants compile the suite executable against the
same accepted scan_03 headers and installed static libraries; only planner_manager.cpp differs.
No Isaac process, controller, sensor publisher or GPU workload is started.
"""

import hashlib
import json
from pathlib import Path
import shutil
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parent
VARIANTS = ('original', 'candidate')
BUILD_FLAGS = ('-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=OFF', '-DSCAN03_SOURCE_ROOT=/scan_03')
PACKAGE = 'scan_fix_native_suite'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def container_name(run_id, stage, variant):
    return 'vla-scan-fixq-%s-%s-%s' % (stage, variant, run_id.lower().replace('_', '-'))


def mounts(run_root, scan_root, variant):
    run_root = Path(run_root)
    return ['-v', str(run_root / ('work_' + variant)) + ':/ws:rw',
            '-v', str(scan_root) + ':/scan_03:ro',
            '-v', str(run_root / 'inputs') + ':/inputs:ro',
            '-v', str(run_root / 'managers') + ':/managers:ro',
            '-v', str(run_root / 'artifacts' / variant) + ':/out:rw',
            '-v', str(run_root / 'container_suite.py') + ':/container_suite.py:ro']


def build_script(variant):
    return ('set -e\n'
            'source /opt/ros/foxy/setup.bash\n'
            'source /scan_03/install/setup.bash\n'
            'cd /ws\n'
            'colcon build --base-paths src --executor sequential --event-handlers console_direct+ '
            '--cmake-args ' + ' '.join(BUILD_FLAGS) +
            ' -DSCAN_MANAGER_CPP=/managers/%s/planner_manager.cpp\n' % variant)


def replay_script(variant):
    return ('set -e\n'
            'source /opt/ros/foxy/setup.bash\n'
            'source /scan_03/install/setup.bash\n'
            'source /ws/install/setup.bash\n'
            'export ROS_DOMAIN_ID=96\n'
            'export ROS_LOCALHOST_ONLY=1\n'
            'export PYTHONDONTWRITEBYTECODE=1\n'
            'python3 /container_suite.py --build %s\n' % variant)


def podman_command(run_id, run_root, scan_root, image, variant, stage):
    common = ['podman', 'run', '--rm', '--pull=never', '--network=none',
              '--name', container_name(run_id, stage, variant),
              '-e', 'CMAKE_BUILD_PARALLEL_LEVEL=2', '-e', 'MAKEFLAGS=-j2']
    script = build_script(variant) if stage == 'build' else replay_script(variant)
    return common + mounts(run_root, scan_root, variant) + [image, 'bash', '-lc', script]


def command(cmd, log, timeout):
    started = time.monotonic()
    try:
        with Path(log).open('w') as stream:
            result = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    return {'command': cmd, 'returncode': code, 'wall_seconds': time.monotonic() - started, 'ceiling_s': timeout}


def check_hashes(root, expected):
    mismatched = sorted(p for p, h in expected.items() if not (Path(root) / p).is_file() or digest(Path(root) / p) != h)
    return {'files': len(expected), 'mismatched': mismatched[:20], 'all_match': not mismatched}


def source_gate(request):
    package = json.loads((ROOT / 'package_manifest.json').read_text())
    original_scan = Path(request['remote_original_build'])
    candidate_scan = Path(request['remote_candidate_build'])
    original_source = json.loads((ROOT / 'inputs/scan_source_identity.json').read_text())
    installed = json.loads((ROOT / 'inputs/scan_install_identity.json').read_text())['installed_files']
    candidate_source = json.loads((ROOT / 'inputs/candidate_source_identity.json').read_text())
    managers = json.loads((ROOT / 'managers/manager_identity.json').read_text())
    manager_rel = 'src/plan_manage/src/planner_manager.cpp'
    gate = {
        'package': check_hashes(ROOT, package),
        'original_scan_source': check_hashes(original_scan, original_source),
        'original_scan_install': check_hashes(original_scan, installed),
        'candidate_scan_source': check_hashes(candidate_scan, candidate_source),
        'original_manager_equals_scan_03': digest(ROOT / 'managers/original/planner_manager.cpp')
        == managers['original']['sha256'] == original_source[manager_rel],
        'candidate_manager_equals_scan_04': digest(ROOT / 'managers/candidate/planner_manager.cpp')
        == managers['candidate']['sha256'] == candidate_source[manager_rel],
    }
    gate['all_match'] = all(v['all_match'] if isinstance(v, dict) else v for v in gate.values())
    return gate, package, original_source, installed, candidate_source


def main():
    request = json.loads((ROOT / 'request.json').read_text())
    run_id = request['run_id']
    image = request['image_id']
    original_scan = Path(request['remote_original_build'])
    candidate_scan = Path(request['remote_candidate_build'])
    output = ROOT / 'artifacts'
    output.mkdir(exist_ok=False)
    result = {'run_id': run_id, 'scope': request['scope'], 'variants': {}}
    names = [container_name(run_id, stage, v) for v in VARIANTS for stage in ('build', 'replay')]

    def terminate(signum, _frame):
        raise TimeoutError('terminated by signal %d' % signum)

    signal.signal(signal.SIGTERM, terminate)
    try:
        gate, package, original_source, installed, candidate_source = source_gate(request)
        result['source_gate'] = gate
        if not gate['all_match']:
            raise RuntimeError('source gate failed')
        for variant in VARIANTS:
            (output / variant).mkdir()
            work = ROOT / ('work_' + variant)
            (work / 'src').mkdir(parents=True)
            shutil.copytree(ROOT / 'native_suite' / PACKAGE, work / 'src' / PACKAGE)
            entry = {}
            result['variants'][variant] = entry
            entry['build'] = command(podman_command(run_id, ROOT, original_scan, image, variant, 'build'),
                                     output / ('build_%s.log' % variant), request['build_ceiling_s'])
            if entry['build']['returncode'] != 0:
                raise RuntimeError('native suite build failed for ' + variant)
            exe = work / 'install' / PACKAGE / 'lib' / PACKAGE / 'rebound_replan_suite'
            entry['executable_sha256'] = digest(exe)
            entry['replay'] = command(podman_command(run_id, ROOT, original_scan, image, variant, 'replay'),
                                      output / ('replay_%s.log' % variant), request['replay_ceiling_s'])
            entry['replay_completed'] = entry['replay']['returncode'] == 0
        result['replay_completed'] = all(result['variants'][v].get('replay_completed') for v in VARIANTS)
        result['after_run'] = {
            'package_unchanged': check_hashes(ROOT, package)['all_match'],
            'original_scan_source_unchanged': check_hashes(original_scan, original_source)['all_match'],
            'original_scan_install_unchanged': check_hashes(original_scan, installed)['all_match'],
            'candidate_scan_source_unchanged': check_hashes(candidate_scan, candidate_source)['all_match'],
        }
    except BaseException as error:  # noqa: BLE001 - preserve the failure and still release containers
        result['error'] = repr(error)
    finally:
        cleanup = {}
        for name in names:
            try:
                removal = subprocess.run(['podman', 'rm', '-f', '-t', '2', name], capture_output=True, text=True, timeout=30)
                remains = subprocess.run(['podman', 'container', 'exists', name], capture_output=True, text=True, timeout=30)
                cleanup[name] = {'rm_returncode': removal.returncode, 'absent': remains.returncode == 1}
            except Exception as error:  # noqa: BLE001 - record and keep writing the result
                cleanup[name] = {'error': repr(error), 'absent': False}
        result['cleanup'] = cleanup
        result['owned_containers_absent'] = all(v['absent'] for v in cleanup.values())
        write_json(output / 'result.json', result)
        hashes = {p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*'))
                  if p.is_file() and p.name != 'artifact_hashes.json'}
        write_json(output / 'artifact_hashes.json', hashes)
    print(json.dumps({k: v for k, v in result.items() if k != 'variants'}, indent=2), flush=True)
    ok = result.get('replay_completed') and result.get('owned_containers_absent') and all(
        result.get('after_run', {}).values() or [False])
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
