"""Bounded original-spatial-start Mac trial with unchanged native v147."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
PYTHON = BASE.parent / '2026-09-26_newton_macos_policy/runtime/.venv/bin/python'


def validate_task(path):
    path = path.resolve()
    if path.parent != Path('/private/tmp') or not path.name.startswith('vla_newton_v149_'):
        raise ValueError('Expected the explicitly owned v167 Mac temporary root')
    return path


def container_command(task, trial, evidence, container, image, run):
    return ['docker', 'run', '-d', '--rm', '--pull=never', '--platform=linux/arm64',
            '--name', container, '--memory=6g', '--cpus=6',
            '-e', 'ROS_DOMAIN_ID=192', '-e', 'ROS_LOCALHOST_ONLY=1',
            '-e', 'ROS_LOG_DIR=' + str(evidence / 'ros_logs'),
            '-e', 'ROS_HOME=' + str(evidence / 'ros_home'),
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'OPENBLAS_NUM_THREADS=1',
            '-e', 'OMP_NUM_THREADS=1',
            '-p', '127.0.0.1:46202:46202', '-p', '127.0.0.1:46203:46203',
            '-v', f'{ROOT}:{ROOT}:ro', '-v', f'{ROOT}:/repo:ro',
            '-v', f'{task}:/task:ro', '-v', f'{trial}:{trial}:rw',
            '--tmpfs', str(trial / 'runs' / run / 'artifacts/external_episode') + ':rw,size=8m',
            '--entrypoint', '/bin/bash', image, '-c', 'exec sleep infinity']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    task = validate_task(args.task_root)
    assert args.attempt > 0
    subprocess.run([str(PYTHON), str(HERE / 'freeze_host.py'), 'verify'], check=True)
    assert shutil.disk_usage(task).free >= 10 * 1024**3
    for port in (46200, 46201, 46202, 46203, 8785):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    run = f'v167_mac_full_attempt{args.attempt:02d}'
    trial = task / run
    trial.mkdir(exist_ok=False)
    (trial / 'scripts').mkdir()
    (trial / 'scripts/run_bounded.py').symlink_to(HERE / 'mac_supervisor.py')
    (trial / 'runs' / run / 'artifacts/external_episode').mkdir(parents=True)
    evidence = trial / 'evidence'
    (evidence / 'ros_logs').mkdir(parents=True)
    (evidence / 'ros_home').mkdir()
    shutil.copyfile(task / 'evidence/v167_native_receipt.json', evidence / 'build_receipt.json')
    receipt = json.loads((evidence / 'build_receipt.json').read_text())
    assert receipt['platform'] == 'linux/arm64' and receipt['native_version'] == 'v167'
    image = receipt['image_id']
    container = run.replace('_', '-')
    env = os.environ.copy()
    env.update(DOCKER_CONTEXT='desktop-linux', PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
               V167_EXECUTION_IMAGE=image, V167_VARIANT='candidate', V167_TEMP_ROOT=str(trial),
               V167_NATIVE_CONTAINER=container, V167_BUILD_EVIDENCE=str(evidence),
               V167_PHYSICAL_FLOOR=str(trial / 'physical_floor.f32'),
               PYTHONPATH=str(task / 'host_python') + ':' + str(BASE / 'runtime_sources/bridge'))
    command = container_command(task, trial, evidence, container, image, run)
    (evidence / 'request.json').write_text(json.dumps({
        'integration_version': 'v167', 'native_version': 'v167', 'host': 'Mac ARM64',
        'physics_device': 'cpu', 'scene': 'original Building historical_full',
        'command': command, 'task_root': str(task),
        'manifest_sha256': hashlib.sha256((HERE / 'manifest.json').read_bytes()).hexdigest(),
        'claim': 'Separate Mac cohort; not a continuation of Linux attempts08–13.'}, indent=2) + '\n')
    created = False
    started = time.monotonic()
    result = {'passed': False, 'run': run}
    try:
        subprocess.run(command, env=env, check=True, capture_output=True, timeout=30)
        created = True
        subprocess.run([str(PYTHON), str(HERE / 'derive_mac_floor.py'), '--output',
                        env['V167_PHYSICAL_FLOOR']], env=env, check=True, timeout=30)
        episode = [str(PYTHON), str(HERE / 'mac_managed.py'), '--run-id', run,
                   '--deadline', '900', '--retention', 'archive', '--',
                   str(PYTHON), str(HERE / 'run_local_episode.py'), '--backend-executor', 'single',
                   '--applied-transport', 'zmq', '--geometry-obstacles', '--scene', 'building_full',
                   '--building-route', 'historical_full', '--goal-wall-budget', '1500',
                   '--startup-mode', 'factory_pd', '--stance-hold', '--integration-version', 'v167',
                   '--real-time-factor', '1', '--recording-sim-seconds', '600']
        with (evidence / 'execution.log').open('w') as stream:
            child = subprocess.run(episode, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=940)
        result.update(passed=child.returncode == 0, exit_code=child.returncode)
    except BaseException as exc:
        result['error'] = repr(exc)
        raise
    finally:
        if created:
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=30)
        result.update(wall_s=time.monotonic() - started, raw_root=str(trial / 'runs' / run),
                      claim='Process execution only; original-route and recovery acceptance require capture review.')
        (evidence / 'execution.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
