"""Exercise the real Mac Docker graph before advancing any physics."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import time

from run_mac_full import BASE, HERE, PYTHON, container_command, validate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = validate_task(args.task_root)
    trial = task / 'v167_graph_preflight'
    run = 'v167_graph_probe'
    out = trial / 'runs' / run
    (out / 'artifacts/external_episode').mkdir(parents=True, exist_ok=False)
    evidence = trial / 'evidence'
    (evidence / 'ros_logs').mkdir(parents=True)
    (evidence / 'ros_home').mkdir()
    (out / 'episode_request.json').write_text(json.dumps({
        'integration_version': 'v167', 'native_variant': 'candidate', 'probe': True,
        'run_epoch_ns': time.time_ns(), 'scene': 'building_full', 'geometry_obstacles': True,
        'applied_transport': 'zmq', 'building_route_profile': 'historical_full',
        'goal_wall_budget_s': 1500, 'startup_mode': 'factory_pd'}) + '\n')
    shutil.copyfile(HERE / 'building_planner.yaml', out / 'planner.yaml')
    subprocess.run([str(PYTHON), str(HERE / 'derive_mac_floor.py'), '--output',
                    str(trial / 'physical_floor.f32')], check=True)
    image = (task / 'evidence/image_id.txt').read_text().strip()
    name = 'vla-v167-graph-preflight'
    command = container_command(task, trial, evidence, name, image, run)
    made = False
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        made = True
        script = '\n'.join(['set -e', 'source /opt/ros/foxy/setup.bash',
                            'source /task/recovery_v167/install/setup.bash',
                            'export PYTHONPATH=' + str(BASE / 'runtime_sources/bridge') + ':${PYTHONPATH:-}',
                            'exec python3 ' + str(HERE / 'native_graph.py') + ' --output ' + str(out)])
        (out / 'inside.sh').write_text(script + '\n')
        with (out / 'graph.log').open('w') as stream:
            process = subprocess.Popen(['docker', 'exec', '-e',
                'V167_PHYSICAL_FLOOR=' + str(trial / 'physical_floor.f32'), name,
                '/bin/bash', str(out / 'inside.sh')], stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None or (out / 'native_failure.json').exists():
                    raise RuntimeError('Native graph exited; inspect ' + str(out))
                time.sleep(0.5)
            for path in out.glob('*.log'):
                assert 'Traceback (most recent call last)' not in path.read_text(errors='replace'), path
            commands = json.loads((out / 'native_commands.json').read_text())
            selected = json.loads((out / 'selected_route_map.json').read_text())
            backend = json.loads((out / 'backend_config.json').read_text())
            assert selected['sha256'] == json.loads((HERE / 'global_map_input.json').read_text())['map_sha256']
            assert backend['map']['epoch'] == 'stair_reactive_coverage_v135'
            latest = json.loads((out / 'backend_latest.json').read_text())
            assert latest['navigation_authority'] == 'Nav2'
            result = {'passed': True, 'duration_s': 15, 'physics_advanced': False,
                      'graph_root': str(out), 'children': list(commands), 'selected_route_map': selected}
            (task / 'evidence/v167_native_graph_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
    finally:
        if made:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)


if __name__ == '__main__':
    main()
