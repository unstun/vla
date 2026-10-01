"""Run the real periodic runtime with native PCT IPC and a recorded goal fixture.

The route publisher is an observation sink; this is not robot/ROS integration.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import json
import os
import subprocess
import sys
import threading
import time

BASE = Path(os.environ["V36_EXPERIMENT_ROOT"])
sys.path[:0] = [str(BASE / "runtime/foreground_py310"), str(BASE / "runtime_sources/pct_runtime/python")]
from backend_adapter.contracts import CommandIdentity, MeasuredState
from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig
from p2b_backend_ros.runtime import NavigationHttpRuntime, RequestedTarget
from p2b_backend_ros.navigation_contract import PeriodicDeadline

out = Path("/attempt")
scenario = json.loads((BASE / "inputs/historical_full_building.json").read_text())
identity = CommandIdentity("component",1,"request","goal","route","command",2,"map",1)
owner = NS(request_id="request",goal_id="goal",route_id="route",command_id="command",command=object())
start = tuple(scenario["spawn_ground_xyz_m"])
target = tuple(scenario["goal_ground_xyz_m"])
runtime = NavigationHttpRuntime.__new__(NavigationHttpRuntime)
runtime.service = NS(active_owner=owner)
runtime._stop = False
runtime._stop_flow = None
runtime._stop_flow_lock = threading.Lock()
runtime._lock = threading.Lock()
runtime._global_frequency = 1.0
runtime._global_schedule = PeriodicDeadline(1)
runtime._global_owner_key = None
runtime._global_history = []
runtime.clock = time.monotonic
runtime.requested_targets = {"route":RequestedTarget("request","goal","route","command",target,(target[0],target[1],target[2]+.35))}
runtime.adapter = NS(gate=NS(owner=identity,cancel_pending=False,closed_reason="open"),frame_id="world",optimize=True,
    _identity_from_p2a_command=lambda _:identity,
    pct_client=PctIpcClient(PctIpcClientConfig(host="127.0.0.1",port=47653,response_timeout_s=5.)))
runtime.scan_port = NS(pct_start_provider=lambda:MeasuredState(1,time.monotonic(),start,(0.,0.,0.),"map",1,source="recorded_goal_fixture"),
    refresh_route=lambda identity,route:True)
faults=[]
runtime._request_stop_flow=lambda owner,intent,reason:faults.append(reason)
log=(out/"pct_worker.log").open("w")
worker=subprocess.Popen([sys.executable,"-m","backend_adapter.pct_worker","--host","127.0.0.1","--port","47653",
    "--pct-source-root",str(BASE/"runtime_sources/pct_runtime/python"),"--rsg-root",str(BASE/"inputs"),
    "--tomogram-path",str(BASE/"inputs/new_building.pickle"),"--reference-height-m","0.30"],stdout=log,stderr=subprocess.STDOUT)
thread=None
try:
    # Worker initialization is outside the frequency sample window.
    import socket
    deadline=time.monotonic()+20.
    while True:
        if worker.poll() is not None: raise RuntimeError("native_pct_worker_failed_to_start")
        try:
            with socket.create_connection(("127.0.0.1",47653),timeout=.1): break
        except OSError:
            if time.monotonic()>deadline: raise TimeoutError("native_pct_worker_start")
            time.sleep(.05)
    thread=threading.Thread(target=runtime._monitor_global)
    thread.start()
    deadline=time.monotonic()+12.
    while len(runtime._global_history)<5 and not faults:
        if time.monotonic()>deadline: raise TimeoutError("global_periodic_fixture")
        time.sleep(.02)
    runtime._stop=True
    thread.join(timeout=6.)
    history=runtime._global_history
    stamps=[row["started_wall_s"] for row in history]
    hz=(len(stamps)-1)/(stamps[-1]-stamps[0]) if len(stamps)>1 else 0.
    evidence={"native_pct":True,"physics":False,"publisher":"observation_sink",
        "samples":len(stamps),"measured_hz":hz,"clock":"monotonic_wall","history":history,"faults":faults,
        "passed":len(stamps)>=5 and .9<=hz<=1.1 and not faults and all(row["status"]=="published" for row in history)}
    (out/"global_native_result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(evidence,indent=2))
    if not evidence["passed"]: raise RuntimeError("native global frequency fixture failed")
finally:
    runtime._stop=True
    if thread is not None: thread.join(timeout=6.)
    worker.terminate()
    try: worker.wait(timeout=5.)
    except subprocess.TimeoutExpired: worker.kill(); worker.wait(timeout=3.)
    log.close()
