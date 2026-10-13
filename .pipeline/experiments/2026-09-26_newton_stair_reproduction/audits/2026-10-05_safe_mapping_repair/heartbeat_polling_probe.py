"""Offline real ROS callback/gate test under compact HTTP polling."""
from pathlib import Path
from types import SimpleNamespace as NS
import json
import sys
import threading
import time
import urllib.request

BASE = Path('/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction')
sys.path[:0] = [str(BASE/'versions/v79/backend_ros'),str(BASE/'runtime_sources/backend_adapter')]
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from backend_adapter.contracts import CommandIdentity, GateConfig
from backend_adapter.control_gate import CommandGate
from p2b_backend_ros.node import RosScanPort
from p2b_backend_ros.plan_history import PlanHistory
from p2b_backend_ros.runtime import start_http_server

original=json.loads((BASE/'versions/v68/mac_trials/attempt02/v68_mac_trial01_attempt02/result.json').read_text())['last_backend']
history=PlanHistory('/task/results/v79_polling_attempt02_history.jsonl',{'run_id':'offline-http-ros-test'})
for record in original['pct']['plan_history']:history.append(record)
received=[]
raw_callback=RosScanPort._on_raw_command
def observed(self,message):
    raw_callback(self,message)
    received.append(time.monotonic())
RosScanPort._on_raw_command=observed
rclpy.init()
node=rclpy.create_node('safe_mapping_backend_callback_test')
publisher=rclpy.create_node('safe_mapping_command_test_source')
topics={'raw_cmd_topic':'/offline_safe_mapping/raw','gated_cmd_topic':'/offline_safe_mapping/gated',
        'body_pose_topic':'/offline_safe_mapping/body','route_topic':'/offline_safe_mapping/route',
        'cancel_topic':'/offline_safe_mapping/cancel','admission_topic':'/offline_safe_mapping/admission'}
config={'map':{'epoch':'map','revision':1,'frame_id':'world'},'topics':topics}
gate=CommandGate(GateConfig())
port=RosScanPort(node,config,gate)
port.watchdog_timer.cancel()
identity=CommandIdentity('offline',1,'request','goal','route','command',1,'map',1)
raw_pub=publisher.create_publisher(port.P2BStampedTwist,topics['raw_cmd_topic'],50)
body_pub=publisher.create_publisher(port.Odometry,topics['body_pose_topic'],qos_profile_sensor_data)
stop=threading.Event();raw_enabled=threading.Event();raw_enabled.set()
def publish():
    next_raw=next_body=time.monotonic()
    while not stop.is_set():
        now=time.monotonic()
        if now>=next_body:
            message=port.Odometry();message.header.frame_id='world'
            message.header.stamp=publisher.get_clock().now().to_msg()
            message.pose.pose.orientation.w=1.0
            body_pub.publish(message);next_body=now+1/50
        if now>=next_raw:
            if raw_enabled.is_set():
                message=port.P2BStampedTwist();port._fill_identity(message,identity)
                message.stamp=publisher.get_clock().now().to_msg()
                message.twist.linear.x=.1
                raw_pub.publish(message)
            next_raw=now+1/30
        stop.wait(.001)
thread=threading.Thread(target=publish,daemon=True);thread.start()
executor=SingleThreadedExecutor();executor.add_node(node)
def spin_for(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:executor.spin_once(timeout_sec=.005)
spin_for(.5)
assert gate.last_measurement is not None
# Match the real admission contract: body readiness precedes owner admission.
# A raw command admitted before the first body pose correctly latches odom_stale.
gate.admit(identity);port._mark_owner_admitted(identity)
spin_for(.1)
assert gate.last_heartbeat_s is not None and gate.closed_reason=='open',gate.snapshot()
port.watchdog_timer.reset()
def state(include_history=False):
    return dict(original,pct=history.snapshot(include_history),gate=gate.snapshot(),scan_port=port.snapshot())
server=start_http_server(NS(state=state),'127.0.0.1',0)
polls=[];errors=[]
def poll():
    try:
        for unused in range(360):
            started=time.monotonic()
            with urllib.request.urlopen('http://127.0.0.1:%d/state'%server.server_address[1],timeout=2) as response:
                payload=response.read();data=json.loads(payload)
                assert data['pct']['history_detail']=='summary'
            polls.append({'elapsed_s':time.monotonic()-started,'bytes':len(payload)})
            time.sleep(max(0,1/30-(time.monotonic()-started)))
    except Exception as error:errors.append(str(error))
poll_thread=threading.Thread(target=poll);poll_thread.start()
while poll_thread.is_alive():executor.spin_once(timeout_sec=.005)
poll_thread.join()
assert not errors,errors
assert len(polls)==360
if gate.closed_reason!='open' or errors:
    Path('/task/results/v79_polling_failure.json').write_text(json.dumps({'passed':False,'gate':gate.snapshot(),'events':gate.events,'errors':errors,'received':received,'polls':polls},indent=2)+'\n')
    stop.set();thread.join();server.shutdown();server.server_close();executor.shutdown()
    node.destroy_node();publisher.destroy_node();rclpy.shutdown()
    raise RuntimeError('Loaded callback test failed: '+gate.closed_reason)
gaps=[b-a for a,b in zip(received,received[1:])]
healthy={'polls':len(polls),'raw_callbacks':len(received),'maximum_callback_gap_ms':max(gaps)*1000,
         'maximum_http_ms':max(row['elapsed_s'] for row in polls)*1000,
         'maximum_http_bytes':max(row['bytes'] for row in polls),'gate':gate.closed_reason}
raw_enabled.clear();spin_for(.35)
assert gate.closed_reason=='heartbeat_stale'
raw_enabled.set();spin_for(.35)
assert gate.closed_reason=='heartbeat_stale'
result={'passed':True,'healthy':healthy,'original_200ms_missing_heartbeat_fault_retained':True,
        'latched_fault_does_not_reopen':True,'executor':'SingleThreadedExecutor',
        'identity_and_watchdog_and_control_handlers':'unchanged v59 via frozen v79',
        'claim':'Real local ROS callback and HTTP polling test; no physics, robot actuation or applied-file I/O stress.'}
Path('/task/results/v79_heartbeat_polling.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
stop.set();thread.join();server.shutdown();server.server_close();executor.shutdown()
node.destroy_node();publisher.destroy_node();rclpy.shutdown()
