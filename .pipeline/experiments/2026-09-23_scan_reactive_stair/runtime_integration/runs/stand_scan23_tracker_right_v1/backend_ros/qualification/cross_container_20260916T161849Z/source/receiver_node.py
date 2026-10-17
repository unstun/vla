import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

scenario = os.environ["P2B_SCENARIO"]
result = pathlib.Path("/qualification/result") / scenario
result.mkdir(parents=True, exist_ok=True)
(result / "receiver_effective_env.json").write_text(json.dumps({
    "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID"),
    "ROS_LOCALHOST_ONLY": os.environ.get("ROS_LOCALHOST_ONLY"),
    "RMW_IMPLEMENTATION": os.environ.get("RMW_IMPLEMENTATION"),
    "CYCLONEDDS_URI": os.environ.get("CYCLONEDDS_URI"),
    "FASTRTPS_DEFAULT_PROFILES_FILE": os.environ.get("FASTRTPS_DEFAULT_PROFILES_FILE"),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

env = dict(os.environ)
env["PYTHONPATH"] = "/qualification/source/backend_ros:/qualification/source/backend_adapter:" + env.get("PYTHONPATH", "")
http_port = os.environ.get("P2B_HTTP_PORT", "18765")
http = "http://127.0.0.1:%s" % http_port

def write(name, data):
    (result / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def get_state():
    with urllib.request.urlopen(http + "/state", timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))

cmd = [
    sys.executable, "-m", "p2b_backend_ros.node",
    "--config", "/qualification/runtime_config.json",
    "--run-id", "ros-cross-qual",
    "--run-epoch-ns", "246813579",
    "--applied-snapshot", "/qualification/missing_current_command.json",
    "--http-port", http_port,
    "--pct-port", "47631",
    "--ros-args", "-r", "__node:=p2b_backend_ros_cross_" + scenario,
]
proc = subprocess.Popen(cmd, env=env, stdout=(result / "node.stdout.log").open("w"), stderr=(result / "node.stderr.log").open("w"))
summary = {"node_command": cmd, "checks": []}
try:
    initial = None
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("node_exited_before_http:%s" % proc.returncode)
        try:
            initial = get_state()
            break
        except Exception:
            time.sleep(0.1)
    if initial is None:
        raise RuntimeError("http_not_ready")
    write("state_initial.json", initial)
    summary["checks"].append("http_ready")

    observed = None
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("node_exited_during_wait:%s" % proc.returncode)
        state = get_state()
        if state["readiness"]["body_pose_ready"] is True:
            observed = state
            break
        time.sleep(0.1)
    if observed is None:
        write("state_timeout.json", get_state())
        raise RuntimeError("body_pose_not_observed_cross_container")
    write("state_observed.json", observed)
    pos = observed["measurement_body_pose"]["position_world_m"]
    if abs(pos[0] - 0.42) > 1e-6 or abs(pos[1] + 0.24) > 1e-6 or abs(pos[2] - 0.35) > 1e-6:
        raise RuntimeError("unexpected_body_pose:%r" % (pos,))
    age = observed["scan_port"]["last_body_pose_age_s"]
    if age is None or age >= 0.25:
        raise RuntimeError("body_pose_not_fresh:%r" % age)
    summary["checks"].append("best_effort_odom_cross_container_observed")
    summary["ok"] = True
except Exception as exc:
    summary["ok"] = False
    summary["error"] = str(exc)
    raise
finally:
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=4.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4.0)
    summary["node_returncode"] = proc.returncode
    write("receiver_summary.json", summary)
