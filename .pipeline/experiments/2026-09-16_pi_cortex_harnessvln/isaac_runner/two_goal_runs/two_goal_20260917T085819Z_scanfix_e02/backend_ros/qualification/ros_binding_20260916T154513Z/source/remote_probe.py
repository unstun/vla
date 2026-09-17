import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path("/qualification")
RESULT = ROOT / "result"
RESULT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "source"
CONFIG = ROOT / "runtime_config.json"
HTTP = "http://127.0.0.1:18765"

def write(name, data):
    (RESULT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def get_json(path):
    with urllib.request.urlopen(HTTP + path, timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))

def post_json(path, payload):
    req = urllib.request.Request(
        HTTP + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))

env = dict(os.environ)
env["PYTHONPATH"] = "/qualification/source/backend_ros:/qualification/source/backend_adapter:" + env.get("PYTHONPATH", "")
cmd = [
    sys.executable,
    "-m",
    "p2b_backend_ros.node",
    "--config",
    str(CONFIG),
    "--run-id",
    "ros-bind-qual",
    "--run-epoch-ns",
    "987654321",
    "--applied-snapshot",
    "/qualification/missing_current_command.json",
    "--http-port",
    "18765",
    "--pct-port",
    "47631",
    "--ros-args",
    "-r",
    "__node:=p2b_backend_ros_qual",
]
proc = subprocess.Popen(cmd, cwd=str(SOURCE), env=env, stdout=(RESULT / "node.stdout.log").open("w"), stderr=(RESULT / "node.stderr.log").open("w"))
summary = {"node_command": cmd, "checks": []}
try:
    deadline = time.monotonic() + 8.0
    state = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("node_exited_before_http:%s" % proc.returncode)
        try:
            state = get_json("/state")
            break
        except Exception:
            time.sleep(0.1)
    if state is None:
        raise RuntimeError("http_state_not_ready")
    write("state_initial.json", state)
    assert state["readiness"]["body_pose_ready"] is False
    assert state["readiness"]["applied_snapshot"]["configured"] is True
    assert state["readiness"]["applied_snapshot"]["ready"] is False
    summary["checks"].append("initial_state_missing_body_and_snapshot")

    invalid_status, invalid = post_json("/goal", {"request_id": "bad", "goal_id": "bad"})
    write("invalid_goal_response.json", {"http_status": invalid_status, "body": invalid})
    assert invalid_status == 400
    assert invalid["ok"] is False
    summary["checks"].append("invalid_goal_structured_refusal")

    valid_status, valid = post_json("/goal", {
        "request_id": "req-no-body",
        "goal_id": "goal-no-body",
        "target_ground_xyz": [1.0, 0.0, 0.0],
        "frame": "world",
        "map_epoch": "flat_nominal",
        "map_revision": 1,
    })
    write("valid_goal_no_body_initial_response.json", {"http_status": valid_status, "body": valid})
    assert valid_status == 202
    time.sleep(0.5)
    after_goal = get_json("/state")
    write("state_after_valid_goal_without_body.json", after_goal)
    jobs = list(after_goal["jobs"].values())
    assert jobs and jobs[-1]["status"] == "failed"
    assert jobs[-1]["error"] == "body_pose_not_ready"
    summary["checks"].append("valid_goal_fails_explicitly_without_body_or_pct")

    import rclpy
    from geometry_msgs.msg import Twist
    from scan_planner_msgs.msg import P2BStampedTwist

    received = []
    rclpy.init(args=None)
    probe = rclpy.create_node("p2b_backend_ros_cpu_probe")
    sub = probe.create_subscription(Twist, "/quad_0/cmd_vel", lambda msg: received.append([msg.linear.x, msg.linear.y, msg.angular.z]), 20)
    pub = probe.create_publisher(P2BStampedTwist, "/quad_0/raw_scan_cmd_vel", 20)
    raw = P2BStampedTwist()
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not received:
        pub.publish(raw)
        rclpy.spin_once(probe, timeout_sec=0.05)
    probe.destroy_node()
    rclpy.shutdown()
    assert proc.poll() is None
    assert received, "no_zero_cmd_vel_received"
    assert abs(received[-1][0]) < 1.0e-9 and abs(received[-1][1]) < 1.0e-9 and abs(received[-1][2]) < 1.0e-9
    write("cmd_vel_zero_probe.json", {"received": received[:20], "sample_count": len(received)})
    summary["checks"].append("invalid_raw_identity_zero_output_and_node_alive")

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
    write("summary.json", summary)
