"""Bounded same-host baseline/candidate trial with unchanged CPU physics."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
TASK = ROOT.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('candidate',), required=True)
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or TASK != Path('/data/sun/vla_mppi_20261009'):
        raise ValueError('This port requires the declared gpu5070ti execution root')
    if args.attempt < 1:
        raise ValueError('Attempt must be positive')
    from resource_gate import admit
    from resource_gate import wait_for_ports
    port_wait=wait_for_ports()
    admission=admit()
    admission["port_wait_seconds"]=port_wait
    tag = f'v185_full_{args.variant}_attempt{args.attempt:02d}'
    temporary = TASK/'trials'/tag
    temporary.mkdir(parents=True, exist_ok=False)
    (temporary/'scripts').mkdir()
    (temporary/'scripts/run_bounded.py').symlink_to(HERE/'mac_supervisor.py')
    # Linux Docker creates missing bind/tmpfs parents as root; create owned empty
    # directories before the mount so the host supervisor can write its evidence.
    (temporary/'runs'/tag/'artifacts/external_episode').mkdir(parents=True)
    evidence = temporary/'evidence'
    evidence.mkdir()
    (evidence/'ros_logs').mkdir()
    (evidence/'ros_home').mkdir()
    shutil.copyfile(TASK/'results/recovery_v185'/f'{args.variant}_receipt.json', evidence/'build_receipt.json')
    receipt = json.loads((evidence/'build_receipt.json').read_text())
    container = tag.replace('_', '-')
    env = os.environ.copy()
    env.update(PATH=str(HERE)+':'+env['PATH'], PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
               V185_EXECUTION_IMAGE=receipt['image_id'], V185_VARIANT=args.variant,
               V185_TEMP_ROOT=str(temporary), V185_NATIVE_CONTAINER=container,
               V185_BUILD_EVIDENCE=str(evidence), V185_PHYSICAL_FLOOR=str(temporary/'physical_floor.f32'),
               PYTHONPATH=str(TASK/'host_python')+':'+str(BASE/'runtime_sources/bridge')+':'+env.get('PYTHONPATH', ''))
    for port in (24600, 24601, 24602, 24603, 24651, 8785):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    command = ['docker', 'run', '-d', '--rm', '--pull=never', '--platform=linux/amd64',
               '--name', container, '--user', f'{os.getuid()}:{os.getgid()}',
               '-e', 'ROS_LOG_DIR='+str(evidence/'ros_logs'),
               '-e', 'ROS_HOME='+str(evidence/'ros_home'), '--memory=6g', '--cpus=6', '--network=host',
               '--add-host', 'host.docker.internal:127.0.0.1', '-e', 'ROS_DOMAIN_ID=192',
               '-e', 'ROS_LOCALHOST_ONLY=1', '-e', 'PYTHONDONTWRITEBYTECODE=1',
               '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1',
               '-v', f'{ROOT}:{ROOT}:ro', '-v', f'{ROOT}:/repo:ro', '-v', f'{TASK}:/task:ro',
               '-v', f'{temporary}:{temporary}:rw',
               '--tmpfs', str(temporary/'runs'/tag/'artifacts/external_episode')+f':rw,size=8m,uid={os.getuid()},gid={os.getgid()},mode=0700',
               '--entrypoint', '/bin/bash', receipt['image_id'], '-c', 'exec sleep infinity']
    request = {'version': 'v185', 'native_version': 'v139' if args.variant == 'baseline' else 'v185',
               'variant': args.variant, 'host': 'gpu5070ti', 'physics_device': 'cpu',
               'scene': 'original Building historical_full', 'seconds': 600,
               'manifest_sha256': hashlib.sha256((HERE/'manifest.json').read_bytes()).hexdigest(),
               'command': command, 'bulk_root': str(temporary)}
    (evidence/'request.json').write_text(json.dumps(request, indent=2)+'\n')
    (evidence/'resource_admission.json').write_text(json.dumps(admission,indent=2)+'\n')
    created = False
    result = {'passed': False, 'claim': 'Execution only; navigation requires analysis.'}
    started = time.monotonic()
    try:
        subprocess.run(command, env=env, check=True, capture_output=True, text=True, timeout=30)
        created = True
        subprocess.run([sys.executable, str(HERE/'derive_mac_floor.py'), '--output', env['V185_PHYSICAL_FLOOR']],
                       env=env, check=True, timeout=30)
        episode = [sys.executable, str(HERE/'mac_managed.py'), '--run-id', tag,
                   '--deadline', '900', '--retention', 'archive', '--', sys.executable,
                   str(HERE/'run_local_episode.py'), '--backend-executor', 'single',
                   '--applied-transport', 'zmq', '--geometry-obstacles', '--scene', 'building_full',
                   '--building-route', 'historical_full', '--goal-wall-budget', '1500',
                   '--startup-mode', 'factory_pd', '--stance-hold', '--integration-version', 'v185',
                   '--real-time-factor', '1', '--recording-sim-seconds', '600']
        with (evidence/'execution.log').open('w') as stream:
            process = subprocess.run(episode, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=940)
        result.update(passed=process.returncode == 0, exit_code=process.returncode,
                      run_root=str(temporary/'runs'/tag))
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        if created:
            subprocess.run(['docker', 'rm', '-f', container], env=env, capture_output=True, timeout=30)
        result['wall_s'] = time.monotonic()-started
        (evidence/'execution.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
