"""Twelve-second actual ROS graph check with v232 install, zero physics."""
from pathlib import Path
import json,os,shutil,socket,subprocess,time
REMOTE=Path('/data/sun/vla_mppi_20261009');WORK=REMOTE/'callback_failure_v232'
REPO=REMOTE/'repo';BASE=REPO/'.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSION=BASE/'versions/v232';OUT=WORK/'graph_probe01'
IMAGE='sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'
CONTAINER='v232-native-offline-probe01'
for port in (24602,8785):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
OUT.mkdir(exist_ok=False);(OUT/'artifacts/external_episode').mkdir(parents=True)
(OUT/'ros_logs').mkdir();(OUT/'ros_home').mkdir()
request=dict(integration_version='v232',native_variant='candidate',probe=True,
 run_epoch_ns=time.time_ns(),scene='building_full',geometry_obstacles=True,applied_transport='shared',
 building_route_profile='historical_full',goal_wall_budget_s=1500,startup_mode='factory_pd')
(OUT/'episode_request.json').write_text(json.dumps(request,indent=2)+'\n')
shutil.copyfile(BASE/'versions/v196/building_planner.yaml',OUT/'planner.yaml')
command=['docker','run','-d','--rm','--pull=never','--network=host','--user',f'{os.getuid()}:{os.getgid()}',
 '-e','ROS_DOMAIN_ID=235','-e','ROS_LOCALHOST_ONLY=1','-e','PYTHONDONTWRITEBYTECODE=1',
 '-e','ROS_LOG_DIR='+str(OUT/'ros_logs'),'-e','ROS_HOME='+str(OUT/'ros_home'),
 '--add-host','host.docker.internal:127.0.0.1','--name',CONTAINER,
 '-v',str(REMOTE)+':/task:ro','-v',str(REPO)+':'+str(REPO)+':ro','-v',str(WORK)+':/work:ro',
 '-v',str(OUT)+':'+str(OUT)+':rw','--entrypoint','bash',IMAGE,'-c','exec sleep infinity']
setup='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && '
subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
process=None
try:
 preflight=subprocess.check_output(['docker','exec',CONTAINER,'bash','-c',setup+'python3 '+str(BASE/'versions/v231/preflight.py')],text=True)
 (OUT/'native_preflight.json').write_text(preflight)
 with (OUT/'graph.log').open('w') as log:
  shell=setup+'exec python3 '+str(VERSION/'native_graph.py')+' --output '+str(OUT)+' --terrain-manifest /work/fixtures/building/terrain.json --environmental-manifest /work/fixtures/building/environment225.json'
  process=subprocess.Popen(['docker','exec',CONTAINER,'bash','-c',shell],stdout=log,stderr=subprocess.STDOUT)
  start=time.monotonic()
  while time.monotonic()-start<12:
   assert process.poll() is None,'Actual native graph exited'
   assert not (OUT/'native_failure.json').exists(),'Direct/native child failure'
   assert not (OUT/'native_process_failure.json').exists(),'Critical launch child failure'
   time.sleep(.2)
  subprocess.run(['docker','exec',CONTAINER,'pkill','-TERM','-f',str(VERSION/'native_graph.py')],check=True)
  assert process.wait(timeout=20)==0
  assert not (OUT/'native_process_failure.json').exists(),'Intentional shutdown incorrectly reported failure'
 report=dict(passed=True,physics_steps=0,seconds=12,navigation='v232',native_packages=14,
             actual_graph_stayed_alive=True,intentional_shutdown_without_fault=True,
             source_inventory=str(WORK/'source_inventory.json'),output=str(OUT))
 (WORK/'graph_gate.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
finally:
 subprocess.run(['docker','rm','-f',CONTAINER],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if process and process.poll() is None:process.wait(timeout=5)
