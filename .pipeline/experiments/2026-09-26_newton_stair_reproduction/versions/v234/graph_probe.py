"""Run the actual source-bound ROS graph for 12 seconds without physics."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import time

import run_native
from source_gate import verify_source
from verify_profile import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    assert args.attempt.isdecimal()
    identity = verify_source(run_native.WORK)
    for port in (24600, 24601, 24602, 8785):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    output = run_native.PREFIX / 'evidence' / ('graph' + args.attempt)
    output.mkdir(exist_ok=False)
    (output / 'artifacts/external_episode').mkdir(parents=True)
    request = dict(integration_version='v234', native_variant='candidate', probe=True,
                   run_epoch_ns=time.time_ns(), scene='building_full', geometry_obstacles=True,
                   applied_transport='shared', building_route_profile='historical_full',
                   goal_wall_budget_s=1500, startup_mode='factory_pd')
    (output / 'episode_request.json').write_text(json.dumps(request, indent=2) + '\n')
    shutil.copyfile(run_native.VERSIONS / 'v196/building_planner.yaml', output / 'planner.yaml')
    name = 'v234-graph-' + args.attempt
    graph = str(run_native.HERE / 'native_graph.py')
    shell = ('source /opt/ros/foxy/setup.bash; source /work/install/setup.bash; python3 ' +
             shlex.quote(str(run_native.HERE / 'preflight.py')) + '; exec python3 ' + shlex.quote(graph) + ' '
             '--output ' + shlex.quote(str(output)) +
             ' --terrain-manifest /work/fixtures/building/terrain.json '
             '--environmental-manifest /work/fixtures/building/environment225.json')
    command = run_native.command(name, output, shell)
    (output / 'request.json').write_text(json.dumps(dict(command=command, source_gate=identity), indent=2) + '\n')
    with (output / 'execution.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                assert process.poll() is None, 'Graph/container exited early'
                assert not (output / 'native_failure.json').exists(), 'Graph child failure'
                time.sleep(.25)
            profile = verify(output)
            commands = json.loads((output / 'native_commands.json').read_text())
            assert {'nav2', 'bridge', 'health', 'body_tf'}.issubset(commands)
            for path in output.glob('*.log'):
                assert 'Traceback (most recent call last)' not in path.read_text(errors='replace'), path
            subprocess.run(['/usr/bin/docker', 'exec', name, 'pkill', '-TERM', '-f',
                            'python3 ' + graph], check=True, timeout=10)
            process.wait(timeout=15)
            assert process.returncode == 0, process.returncode
            assert not (output / 'native_process_failure.json').exists(), 'False fault on orderly stop'
            report = dict(passed=True, seconds=12, physics_steps=0, returncode=process.returncode,
                          generated_profile_passed=profile['passed'], navigation='frozen v232',
                          driver_source_sha256=hashlib.sha256(
                              (run_native.VERSIONS / 'v232/long_route_driver.py').read_bytes()).hexdigest())
            (output / 'gate.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report, indent=2))
        finally:
            subprocess.run(['/usr/bin/docker', 'rm', '-f', name], capture_output=True, timeout=30)
            if process.poll() is None:
                process.wait(timeout=15)


if __name__ == '__main__':
    main()
