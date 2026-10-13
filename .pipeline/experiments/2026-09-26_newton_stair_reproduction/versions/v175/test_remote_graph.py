"""Exercise the real Mac Docker graph before advancing any physics."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
import yaml

import sys
from run_remote_full import BASE,HERE,ROOT,TASK
PYTHON=Path(sys.executable)
def validate_task(task):
    assert task.resolve()==TASK
    return task

def container_command(task,trial,evidence,container,image,run):
    return ['docker','run','-d','--rm','--pull=never','--platform=linux/amd64',
      '--name',container,'--user',f'{os.getuid()}:{os.getgid()}',
      '--memory=6g','--cpus=6','--network=host',
      '--add-host','host.docker.internal:127.0.0.1','-e','ROS_DOMAIN_ID=192',
      '-e','ROS_LOCALHOST_ONLY=1','-e','PYTHONDONTWRITEBYTECODE=1',
      '-e','ROS_LOG_DIR='+str(evidence/'ros_logs'),'-e','ROS_HOME='+str(evidence/'ros_home'),
      '-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
      '-v',f'{ROOT}:{ROOT}:ro','-v',f'{ROOT}:/repo:ro','-v',f'{task}:/task:ro',
      '-v',f'{trial}:{trial}:rw',
      '--tmpfs',str(trial/'runs'/run/'artifacts/external_episode')+f':rw,size=8m,uid={os.getuid()},gid={os.getgid()},mode=0700',
      '--entrypoint','/bin/bash',image,'-c','exec sleep infinity']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = validate_task(args.task_root)
    trial = task / 'v175_overlay_preflight'
    run = 'v175_overlay_graph_probe'
    out = trial / 'runs' / run
    (out / 'artifacts/external_episode').mkdir(parents=True, exist_ok=False)
    evidence = trial / 'evidence'
    (evidence / 'ros_logs').mkdir(parents=True)
    (evidence / 'ros_home').mkdir()
    (out / 'episode_request.json').write_text(json.dumps({
        'integration_version': 'v175', 'native_variant': 'candidate', 'probe': True,
        'run_epoch_ns': time.time_ns(), 'scene': 'building_full', 'geometry_obstacles': True,
        'applied_transport': 'zmq', 'building_route_profile': 'historical_full',
        'goal_wall_budget_s': 1500, 'startup_mode': 'factory_pd'}) + '\n')
    shutil.copyfile(HERE / 'building_planner.yaml', out / 'planner.yaml')
    subprocess.run([str(PYTHON), str(HERE / 'derive_mac_floor.py'), '--output',
                    str(trial / 'physical_floor.f32')], check=True)
    image = json.loads((task/'results/recovery_v175/candidate_receipt.json').read_text())['image_id']
    name = 'vla-v175-overlay-preflight'
    command = container_command(task, trial, evidence, name, image, run)
    made = False
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        made = True
        script = '\n'.join(['set -e', 'source /opt/ros/foxy/setup.bash',
                            'source /task/recovery_v175/install/setup.bash',
                            'export PYTHONPATH=' + str(BASE / 'runtime_sources/bridge') + ':${PYTHONPATH:-}',
                            'exec python3 ' + str(HERE / 'native_graph.py') + ' --output ' + str(out)])
        (out / 'inside.sh').write_text(script + '\n')
        with (out / 'graph.log').open('w') as stream:
            process = subprocess.Popen(['docker', 'exec', '-e',
                'V175_PHYSICAL_FLOOR=' + str(trial / 'physical_floor.f32'), name,
                '/bin/bash', str(out / 'inside.sh')], stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None or (out / 'native_failure.json').exists():
                    raise RuntimeError('Native graph exited; inspect ' + str(out))
                time.sleep(0.5)
            for path in out.glob('*.log'):
                assert 'Traceback (most recent call last)' not in path.read_text(errors='replace'), path
            inspect_code = """from pathlib import Path
import json
found=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\\0')
  if not args or not args[0].endswith(b'/controller_server'):continue
  libraries=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/libscan_nav2_controller.so' in line))
  found.append({'pid':int(cmd.parent.name),'libraries':libraries})
 except (FileNotFoundError,PermissionError):pass
assert found, 'No actual ControllerServer process'
expected='/task/recovery_v175/install/scan_nav2_controller/lib/libscan_nav2_controller.so'
assert all(r['libraries']==[expected] for r in found),found
bt=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\\0')
  if not args or not args[0].endswith(b'/bt_navigator'):continue
  libs=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/liblite3_bind_route_bt_node.so' in line))
  bt.append({'pid':int(cmd.parent.name),'libraries':libs})
 except (FileNotFoundError,PermissionError):pass
expected_bt='/task/recovery_v175/install/lite3_nav2_plugins/lib/liblite3_bind_route_bt_node.so'
assert bt and all(x['libraries']==[expected_bt] for x in bt),bt
pct=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\\0')
  if b'backend_adapter.pct_worker' not in args:continue
  libs=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/pct_planner/lib/ele_planner.' in line))
  pct.append({'pid':int(cmd.parent.name),'libraries':libs})
 except (FileNotFoundError,PermissionError):pass
assert pct and all(x['libraries'] and all(p.startswith('/task/recovery_v175/install/pct_planner/') for p in x['libraries']) for x in pct),pct
print(json.dumps({'passed':True,'processes':found,'bt_processes':bt,'pct_processes':pct}))
"""
            loaded = subprocess.check_output(['docker','exec',name,'python3','-c',inspect_code],text=True)
            overlay = json.loads(loaded)
            (task / 'results/host_v175/overlay_loaded.json').write_text(json.dumps(overlay,indent=2)+'\n')
            frame_node=ET.parse(out/'nav2_params.bt.xml').getroot().find('./BehaviorTree/MeasuredProgressRecovery')
            assert frame_node is not None and frame_node.get('robot_base_frame')=='base'
            assert frame_node.get('global_frame')=='world'
            profile=yaml.safe_load((out/'nav2_params.yaml').read_text())
            assert profile['/nav2_internal/bt_navigator']['ros__parameters']['robot_base_frame']=='base'
            commands = json.loads((out / 'native_commands.json').read_text())
            selected = json.loads((out / 'selected_route_map.json').read_text())
            backend = json.loads((out / 'backend_config.json').read_text())
            assert selected['sha256'] == json.loads((HERE / 'global_map_input.json').read_text())['map_sha256']
            assert backend['map']['epoch'] == 'stair_reactive_coverage_v135'
            latest = json.loads((out / 'backend_latest.json').read_text())
            assert latest['navigation_authority'] == 'Nav2'
            result = {'passed': True, 'duration_s': 15, 'physics_advanced': False, 'recovery_body_frame': 'base',
                      'graph_root': str(out), 'children': list(commands), 'selected_route_map': selected}
            (task / 'results/host_v175/native_graph_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
    finally:
        if made:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)


if __name__ == '__main__':
    main()
