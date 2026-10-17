from pathlib import Path
import json
found=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\0')
  if not args or not args[0].endswith(b'/controller_server'):continue
  libraries=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/libscan_nav2_controller.so' in line))
  native=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/libscan_native_core.so' in line))
  found.append({'pid':int(cmd.parent.name),'libraries':libraries,'native_libraries':native})
 except (FileNotFoundError,PermissionError):pass
assert found, 'No actual ControllerServer process'
expected='/task/recovery_v196/install/scan_nav2_controller/lib/libscan_nav2_controller.so'
assert all(r['libraries']==[expected] for r in found),found
assert all(r['native_libraries']==['/task/recovery_v196/install/scan_planner/lib/libscan_native_core.so'] for r in found),found
scan=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\0')
  if not args or not args[0].endswith(b'/scan_planner_node'):continue
  scan.append({'pid':int(cmd.parent.name),'exe':args[0].decode()})
 except (FileNotFoundError,PermissionError):pass
assert not scan, ('SCAN must run inside ControllerServer, not a competing standalone process',scan)
bridge=[]
for cmd in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=cmd.read_bytes().split(b'\0')
  if b'/task/recovery_v196/install/lite3_nav2_bridge/lib/lite3_nav2_bridge/mission_bridge' not in args:continue
  libs=sorted(set(line.split()[-1] for line in (cmd.parent/'maps').read_text().splitlines() if '/pct_planner/lib/ele_planner.' in line))
  bridge.append({'pid':int(cmd.parent.name),'libraries':libs})
 except (FileNotFoundError,PermissionError):pass
assert bridge and all(x['libraries'] and all(p.startswith('/task/recovery_v174/install/pct_planner/') for p in x['libraries']) for x in bridge),bridge
import time
import rclpy
from lifecycle_msgs.srv import GetState
from rcl_interfaces.srv import GetParameters
rclpy.init()
node=rclpy.create_node('v196_preflight_inspector')
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
 client=node.create_client(GetParameters,'/quad_0/scan_planner_node/get_parameters')
 assert client.wait_for_service(timeout_sec=5.0)
 request=GetParameters.Request();request.names=['grid_map.reactive_cloud_max_age']
 future=client.call_async(request)
 rclpy.spin_until_future_complete(node,future,timeout_sec=5.0)
 assert future.done() and future.result() is not None
 cloud_age=future.result().values[0].double_value
 assert cloud_age==0.35,cloud_age
 assert topics['/pct_path']==['nav_msgs/msg/Path'],topics
 assert topics['/quad_0/planning/bspline']==['scan_planner_msgs/msg/Bspline'],topics
 assert topics['/quad_0/cmd_vel']==['geometry_msgs/msg/Twist'],topics
 assert not any('P2B' in kind for kinds in topics.values() for kind in kinds),topics
 assert '/lite3_nav2_gateway' not in nodes,nodes
 print(json.dumps({'passed':True,'processes':found,'scan_processes':scan,
                   'scan_execution':'embedded_native_worker','bridge_processes':bridge,
                   'reactive_cloud_max_age_s':cloud_age,'lifecycle_states':states,'nodes':nodes,'topics':topics}))
finally:
 node.destroy_node()
 rclpy.shutdown()
