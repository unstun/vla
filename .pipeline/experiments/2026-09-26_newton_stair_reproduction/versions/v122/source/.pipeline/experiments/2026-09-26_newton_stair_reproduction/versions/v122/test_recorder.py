"""Actual Foxy DDS regression: original recorder misses the namespaced curve."""
from pathlib import Path
import argparse,json,tempfile,time
from types import SimpleNamespace
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from scan_planner_msgs.msg import Bspline,P2BCancel,P2BExecutionSafety
from geometry_msgs.msg import Point
from rosgraph_msgs.msg import Clock
from rosidl_runtime_py.convert import message_to_ordereddict
from lite3_sim_bridge.reactive_health import Recorder as PreviousRecorder
from nav2_recorder import Recorder

rclpy.init();root=Path(tempfile.mkdtemp(prefix='v122-recorder-',dir='/task'))
nodes=[];executor=SingleThreadedExecutor()
try:
 for name,kind in [('previous',PreviousRecorder),('candidate',Recorder)]:
  (root/name).mkdir();node=kind(SimpleNamespace(output=root/name/'health.json',run_id='recording-test',epoch=1));nodes.append(node);executor.add_node(node)
 source=Node('v122_observer_test_source');nodes.append(source);executor.add_node(source)
 curve=source.create_publisher(Bspline,'/quad_0/planning/bspline',10)
 stop=source.create_publisher(P2BCancel,'/p2b/scan_cancel',10)
 proof=source.create_publisher(P2BExecutionSafety,'/quad_0/planning/execution_safety',10)
 clock=source.create_publisher(Clock,'/clock',10)
 end=time.monotonic()+3
 while time.monotonic()<end and curve.get_subscription_count()!=1:executor.spin_once(timeout_sec=.01)
 assert curve.get_subscription_count()==1
 m=Bspline();m.traj_id=42;m.order=3;m.start_time.sec=10;m.run_id='recording-test';m.generation=1
 m.pos_pts=[Point(x=float(i),y=float(i*i),z=.3) for i in range(4)];m.knots=[float(i) for i in range(8)]
 c=Clock();c.clock.sec=10;clock.publish(c)
 for i in range(3):
  curve.publish(m);stop.publish(P2BCancel());proof.publish(P2BExecutionSafety())
  end=time.monotonic()+.1
  while time.monotonic()<end:executor.spin_once(timeout_sec=.005)
 rows={name:[json.loads(x) for x in (root/name/'reactive_observations.jsonl').read_text().splitlines()] for name in ['previous','candidate']}
 old=[x for x in rows['previous'] if x['event']=='bspline'];new=[x for x in rows['candidate'] if x['event']=='bspline']
 assert not old and len(new)==3
 assert all(x['data']==message_to_ordereddict(m) and x['clock_ns']==10_000_000_000 for x in new)
 assert sum(x['event']=='scan_cancel' for x in rows['candidate'])==3
 assert sum(x['event']=='execution_safety' for x in rows['candidate'])==3
 print(json.dumps({'passed':True,'old_namespaced_curves':len(old),'new_exact_curves':len(new),'cancel_and_safety_events':True,'raw_root':str(root)}))
finally:
 for node in nodes:node.log.close() if hasattr(node,'log') else None;executor.remove_node(node);node.destroy_node()
 executor.shutdown();rclpy.shutdown()
