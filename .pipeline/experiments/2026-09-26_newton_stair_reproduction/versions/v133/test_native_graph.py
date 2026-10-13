"""Start the actual native graph with the Linux run mounts, before physics."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
TASK = ROOT.parent
check = TASK/'checks'/f'native_graph_{time.time_ns()}'
check.mkdir(parents=True)
(check/'ros_logs').mkdir()
(check/'external').mkdir()
fixture = TASK/'trials/v124_baseline_attempt01/runs/v124_baseline_attempt01'
request = json.loads((fixture/'episode_request.json').read_text())
request.update(integration_version='v133', probe=True)
(check/'episode_request.json').write_text(json.dumps(request)+'\n')
shutil.copyfile(HERE/'building_planner.yaml', check/'planner.yaml')
shutil.copyfile(TASK/'trials/v124_baseline_attempt01/physical_floor.f32', check/'physical_floor.f32')
(check/'artifacts/external_episode').mkdir(parents=True)
image = json.loads((TASK/'results/recovery_v133/candidate_receipt.json').read_text())['image_id']
name = f'vla-mppi-native-graph-check-{os.getpid()}'
command = ['docker', 'run', '-d', '--rm', '--name', name, '--network', 'host',
           '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'ROS_DOMAIN_ID=194',
           '-e', 'ROS_LOCALHOST_ONLY=1', '-e', 'ROS_LOG_DIR='+str(check/'ros_logs'),
           '-e', 'PYTHONDONTWRITEBYTECODE=1',
           '-e', 'V133_PHYSICAL_FLOOR='+str(check/'physical_floor.f32'),
           '--add-host', 'host.docker.internal:127.0.0.1',
           '-v', f'{ROOT}:{ROOT}:ro', '-v', f'{ROOT}:/repo:ro',
           '-v', f'{TASK}:/task:ro', '-v', f'{check}:{check}:rw',
           '--entrypoint', '/bin/bash', image, '-c', 'exec sleep infinity']
created = False
try:
    subprocess.run(command, check=True, capture_output=True, timeout=30)
    created = True
    # Same environment and installed baseline as the actual episode.
    script = '\n'.join(['set -e', 'source /opt/ros/foxy/setup.bash',
        'source /task/recovery_v133/install/setup.bash',
        'export PYTHONPATH='+str(BASE/'runtime_sources/bridge')+':${PYTHONPATH:-}',
        'exec python3 '+str(HERE/'native_graph.py')+' --output '+str(check)])
    (check/'inside.sh').write_text(script+'\n')
    with (check/'graph.log').open('w') as stream:
        process = subprocess.Popen(['docker', 'exec', name, '/bin/bash', str(check/'inside.sh')],
                                   stdout=stream, stderr=subprocess.STDOUT)
        time.sleep(10)
        if process.poll() is not None or (check/'native_failure.json').exists():
            raise RuntimeError('Native graph exited; inspect '+str(check))
        commands = json.loads((check/'native_commands.json').read_text())
        assert 'nav2' in commands and 'pct_support' in commands
        for path in check.glob('*.log'):
            if 'Traceback (most recent call last)' in path.read_text(errors='replace'):
                raise RuntimeError('Child exception: '+str(path))
        result = {'passed': True, 'duration_s': 10, 'probe': True, 'physics_advanced': False,
                  'graph_root': str(check), 'image_id': image, 'children': list(commands)}
        (TASK/'results/recovery_v133/native_graph_preflight.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
finally:
    if created:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
