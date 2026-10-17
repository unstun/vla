"""Exercise the real Mac Docker graph before advancing any physics (Option B direct Nav2 + SCAN)."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
import yaml

from run_mac_full import BASE, HERE, PYTHON, container_command, validate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = validate_task(args.task_root)
    for filename in ('v192_overlay_loaded.json', 'v192_native_graph_preflight.json'):
        (task / 'evidence' / filename).unlink(missing_ok=True)
    trial = task / 'v192_overlay_preflight'
    if trial.exists():
        raise ValueError('Preserve the previous preflight directory before retrying')
    run = 'v192_overlay_graph_probe'
    out = trial / 'runs' / run
    (out / 'artifacts/external_episode').mkdir(parents=True, exist_ok=False)
    evidence = trial / 'evidence'
    (evidence / 'ros_logs').mkdir(parents=True)
    (evidence / 'ros_home').mkdir()
    (out / 'episode_request.json').write_text(json.dumps({
        'integration_version': 'v192', 'native_variant': 'candidate', 'probe': True,
        'run_epoch_ns': time.time_ns(), 'scene': 'building_full', 'geometry_obstacles': True,
        'applied_transport': 'shared', 'building_route_profile': 'historical_full',
        'goal_wall_budget_s': 1500, 'startup_mode': 'factory_pd'}) + '\n')
    shutil.copyfile(HERE / 'building_planner.yaml', out / 'planner.yaml')
    subprocess.run([str(PYTHON), str(HERE / 'derive_mac_floor.py'), '--output',
                    str(trial / 'physical_floor.f32')], check=True)
    image = (task / 'evidence/image_id.txt').read_text().strip()
    name = 'vla-v192-overlay-preflight'
    command = container_command(task, trial, evidence, name, image, run)
    made = False
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        made = True
        # Exercise both directions of the real trial bind mount without a
        # simulated command, navigation goal, or physics step.
        mount_probe = out / 'shared_mount_probe.json'
        mount_probe.write_text(json.dumps({'host': 'v192', 'sequence': 1}))
        mount_code = """import json,sys
from pathlib import Path
p=Path(sys.argv[1])
assert json.loads(p.read_text())=={'host':'v192','sequence':1}
t=p.with_suffix('.tmp')
t.write_text(json.dumps({'container':'v192','sequence':2}))
t.replace(p)
"""
        subprocess.run(['docker', 'exec', name, 'python3', '-c', mount_code, str(mount_probe)],
                       check=True, timeout=15)
        assert json.loads(mount_probe.read_text()) == {'container': 'v192', 'sequence': 2}
        script = '\n'.join(['set -e', 'source /opt/ros/foxy/setup.bash',
                            'source /task/recovery_v176/install/setup.bash',
                            'source /task/recovery_v191/install/setup.bash',
                            'export PYTHONPATH=' + str(BASE / 'runtime_sources/bridge') + ':${PYTHONPATH:-}',
                            # A static identity TF permits lifecycle activation without a
                            # simulator, odometry, clock ticks, navigation goals or motion.
                            'ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 world base > '
                            + str(out / 'preflight_tf.log') + ' 2>&1 &',
                            'exec python3 ' + str(HERE / 'native_graph.py') + ' --output ' + str(out)])
        (out / 'inside.sh').write_text(script + '\n')
        with (out / 'graph.log').open('w') as stream:
            process = subprocess.Popen(['docker', 'exec', '-e',
                'V192_PHYSICAL_FLOOR=' + str(trial / 'physical_floor.f32'), name,
                '/bin/bash', str(out / 'inside.sh')], stdout=stream, stderr=subprocess.STDOUT)
            started = time.monotonic()
            deadline = started + 60
            while time.monotonic() < deadline:
                if process.poll() is not None or (out / 'native_failure.json').exists():
                    raise RuntimeError('Native graph exited; inspect ' + str(out))
                nav2_log = out / 'nav2.log'
                if nav2_log.exists() and 'Managed nodes are active' in nav2_log.read_text(errors='replace'):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError('Native lifecycle activation timed out; inspect ' + str(out))
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
  native=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/libscan_native_core.so' in line))
  found.append({'pid':int(cmd.parent.name),'libraries':libraries,'native_libraries':native})
 except (FileNotFoundError,PermissionError):pass
assert found, 'No actual ControllerServer process'
expected='/task/recovery_v191/install/scan_nav2_controller/lib/libscan_nav2_controller.so'
assert all(r['libraries']==[expected] for r in found),found
assert all(r['native_libraries']==['/task/recovery_v191/install/scan_planner/lib/libscan_native_core.so'] for r in found),found
scan=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\\0')
  if not args or not args[0].endswith(b'/scan_planner_node'):continue
  scan.append({'pid':int(cmd.parent.name),'exe':args[0].decode()})
 except (FileNotFoundError,PermissionError):pass
assert not scan, ('SCAN must run inside ControllerServer, not a competing standalone process',scan)
bridge=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\\0')
  if b'/task/recovery_v191/install/lite3_nav2_bridge/lib/lite3_nav2_bridge/mission_bridge' not in args:continue
  libs=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/pct_planner/lib/ele_planner.' in line))
  bridge.append({'pid':int(cmd.parent.name),'libraries':libs})
 except (FileNotFoundError,PermissionError):pass
assert bridge and all(x['libraries'] and all(p.startswith('/task/recovery_v174/install/pct_planner/') for p in x['libraries']) for x in bridge),bridge
import time
import rclpy
from lifecycle_msgs.srv import GetState
rclpy.init()
node=rclpy.create_node('v192_preflight_inspector')
states={}
try:
 for name in ('/controller_server','/planner_server','/recoveries_server','/nav2_internal/bt_navigator'):
  client=node.create_client(GetState,name+'/get_state')
  assert client.wait_for_service(timeout_sec=5.0),name
  future=client.call_async(GetState.Request())
  rclpy.spin_until_future_complete(node,future,timeout_sec=5.0)
  assert future.done() and future.result() is not None,name
  states[name]=future.result().current_state.label
 assert all(state=='active' for state in states.values()),states
 deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  nodes=sorted(ns.rstrip('/')+'/'+name for name,ns in node.get_node_names_and_namespaces())
  topics=dict(node.get_topic_names_and_types())
  if '/quad_0/scan_planner_node' in nodes and '/pct_path' in topics:break
  rclpy.spin_once(node,timeout_sec=0.1)
 assert '/quad_0/scan_planner_node' in nodes,nodes
 assert topics['/pct_path']==['nav_msgs/msg/Path'],topics
 assert topics['/quad_0/planning/bspline']==['scan_planner_msgs/msg/Bspline'],topics
 assert topics['/quad_0/cmd_vel']==['geometry_msgs/msg/Twist'],topics
 assert not any('P2B' in kind for kinds in topics.values() for kind in kinds),topics
 assert '/lite3_nav2_gateway' not in nodes,nodes
 print(json.dumps({'passed':True,'processes':found,'scan_processes':scan,
                   'scan_execution':'embedded_native_worker','bridge_processes':bridge,
                   'lifecycle_states':states,'nodes':nodes,'topics':topics}))
finally:
 node.destroy_node()
 rclpy.shutdown()
"""
            inspection = out / 'inspect_overlay.py'
            inspection.write_text(inspect_code)
            loaded = subprocess.check_output(['docker','exec',name,'/bin/bash','-c',
                'source /opt/ros/foxy/setup.bash && python3 ' + str(inspection)],text=True,timeout=45)
            overlay = json.loads(loaded)
            (task / 'evidence/v192_overlay_loaded.json').write_text(json.dumps(overlay,indent=2)+'\n')
            seq_node=ET.parse(out/'nav2_params.bt.xml').getroot().find('.//Sequence')
            assert seq_node is not None and seq_node.get('name')=='NavigateWithDirectRoute'
            wait_node = ET.parse(out/'nav2_params.bt.xml').getroot().find('.//Wait')
            assert wait_node is not None and wait_node.get('server_name') == '/wait'
            profile=yaml.safe_load((out/'nav2_params.yaml').read_text())
            assert profile['controller_server']['ros__parameters']['SCAN']['finish_dist']==0.02
            assert profile['controller_server']['ros__parameters']['SCAN']['command_topic']=='/quad_0/cmd_vel'
            assert profile['controller_server']['ros__parameters']['SCAN']['route_topic']=='/pct_path'
            assert profile['controller_server']['ros__parameters']['SCAN']['route_lookahead_heading_enabled'] is True
            assert profile['controller_server']['ros__parameters']['SCAN']['route_lookahead_dist']==0.5
            assert profile['/nav2_internal/bt_navigator']['ros__parameters']['robot_base_frame']=='base'
            commands = json.loads((out / 'native_commands.json').read_text())
            assert 'applied_receiver' not in commands
            selected = json.loads((out / 'selected_route_map.json').read_text())
            backend = json.loads((out / 'backend_config.json').read_text())
            assert selected['sha256'] == json.loads((HERE / 'global_map_input.json').read_text())['map_sha256']
            assert backend['map']['epoch'] == 'stair_reactive_coverage_v135'
            latest = json.loads((out / 'backend_latest.json').read_text())
            assert latest['navigation_authority'] == 'Nav2'
            result = {'passed': True, 'duration_s': time.monotonic() - started,
                      'applied_transport': 'shared', 'shared_mount_bidirectional_verified': True,
                      'physics_advanced': False, 'synthetic_fixture': 'static identity world->base TF only',
                      'navigation_goal_sent': False, 'scan_execution': overlay['scan_execution'],
                      'lifecycle_states': overlay['lifecycle_states'], 'recovery_body_frame': 'base',
                      'generated_finish_dist_m': 0.02, 'route_lookahead_heading_enabled': True, 'route_lookahead_dist': 0.5,
                      'command_topic': '/quad_0/cmd_vel', 'route_topic': '/pct_path',
                      'graph_root': str(out), 'children': list(commands), 'selected_route_map': selected}
            (task / 'evidence/v192_native_graph_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
    finally:
        if made:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
            if 'process' in locals():
                process.wait(timeout=10)


if __name__ == '__main__':
    main()
