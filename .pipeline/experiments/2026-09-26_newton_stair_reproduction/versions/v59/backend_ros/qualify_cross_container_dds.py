"""Cross-container Foxy DDS smoke for BEST_EFFORT body_pose delivery."""

from __future__ import annotations

import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import textwrap
import time
from typing import Dict, Iterable, List, Optional


ROOT = pathlib.Path(__file__).resolve().parent
EXPERIMENT = ROOT.parent
REMOTE_HOST = "gpu5070ti"
REMOTE_BASE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/ros_binding_cross_container"
SCAN02 = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_02"
FOXY_IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
ROS_DOMAIN_ID = "94"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(command: List[str], timeout: int = 120) -> Dict[str, object]:
    started = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return {
        "command": command,
        "returncode": proc.returncode,
        "elapsed_s": time.monotonic() - started,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def ssh(command: str, timeout: int = 120) -> Dict[str, object]:
    return run(["ssh", REMOTE_HOST, command], timeout=timeout)


def copy_file(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def should_skip(path: pathlib.Path) -> bool:
    return "__pycache__" in path.parts or "qualification" in path.parts or "checks" in path.parts


def copy_tree_files(src_root: pathlib.Path, dst_root: pathlib.Path, suffixes: Iterable[str]) -> None:
    suffix_set = set(suffixes)
    for path in src_root.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if suffix_set and path.suffix not in suffix_set:
            continue
        copy_file(path, dst_root / path.relative_to(src_root))


def write_probe_scripts(source: pathlib.Path) -> None:
    (source / "receiver_node.py").write_text(textwrap.dedent(
        r'''
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
        ''').lstrip(), encoding="utf-8")

    (source / "publisher_odom.py").write_text(textwrap.dedent(
        r'''
        import json
        import os
        import pathlib
        import time

        import rclpy
        from nav_msgs.msg import Odometry
        from rclpy.qos import qos_profile_sensor_data

        scenario = os.environ["P2B_SCENARIO"]
        result = pathlib.Path("/qualification/result") / scenario
        result.mkdir(parents=True, exist_ok=True)
        (result / "publisher_effective_env.json").write_text(json.dumps({
            "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID"),
            "ROS_LOCALHOST_ONLY": os.environ.get("ROS_LOCALHOST_ONLY"),
            "RMW_IMPLEMENTATION": os.environ.get("RMW_IMPLEMENTATION"),
            "CYCLONEDDS_URI": os.environ.get("CYCLONEDDS_URI"),
            "FASTRTPS_DEFAULT_PROFILES_FILE": os.environ.get("FASTRTPS_DEFAULT_PROFILES_FILE"),
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        summary = {"published": 0, "checks": []}
        rclpy.init(args=None)
        node = rclpy.create_node("p2b_cross_container_best_effort_publisher_" + scenario)
        pub = node.create_publisher(Odometry, "/quad_0/body_pose", qos_profile_sensor_data)
        try:
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                msg = Odometry()
                msg.header.frame_id = "world"
                msg.header.stamp = node.get_clock().now().to_msg()
                msg.pose.pose.position.x = 0.42
                msg.pose.pose.position.y = -0.24
                msg.pose.pose.position.z = 0.35
                pub.publish(msg)
                summary["published"] += 1
                rclpy.spin_once(node, timeout_sec=0.02)
                time.sleep(0.03)
            summary["checks"].append("best_effort_odom_published")
            summary["ok"] = summary["published"] > 0
        finally:
            node.destroy_node()
            rclpy.shutdown()
            (result / "publisher_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ''').lstrip(), encoding="utf-8")


def podman_cmd(name: str, remote_dir: str, scenario: str, port: str, script: str, ipc_arg: str = "") -> str:
    args = [
        "podman", "run",
        "--rm" if "publisher" in name else "-d",
        "--pull=never",
        "--network=host",
    ]
    if ipc_arg:
        args.append(ipc_arg)
    args += [
        "--name", name,
        "-e", "ROS_DOMAIN_ID=%s" % ROS_DOMAIN_ID,
        "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "P2B_SCENARIO=%s" % scenario,
        "-e", "P2B_HTTP_PORT=%s" % port,
        "-v", "%s:/qualification" % remote_dir,
        "-v", "%s:/workspace:ro" % SCAN02,
        FOXY_IMAGE,
        "bash", "-lc",
        "source /opt/ros/foxy/setup.bash && source /workspace/install/setup.bash && python3 /qualification/source/%s" % script,
    ]
    return " ".join(shlex.quote(x) for x in args)


def run_scenario(remote_dir: str, scenario: str, ipc_arg: str, port: str) -> Dict[str, object]:
    receiver = "p2b-cross-receiver-%s" % scenario.replace("_", "-")
    publisher = "p2b-cross-publisher-%s" % scenario.replace("_", "-")
    result_dir = "%s/result/%s" % (remote_dir, scenario)
    commands = {
        "prepare": ssh("mkdir -p %s && podman rm -f %s %s >/dev/null 2>&1 || true" % (shlex.quote(result_dir), shlex.quote(receiver), shlex.quote(publisher)), timeout=30),
        "receiver_start": ssh(podman_cmd(receiver, remote_dir, scenario, port, "receiver_node.py", ipc_arg), timeout=30),
    }
    time.sleep(3.0)
    commands["publisher_run"] = ssh(podman_cmd(publisher, remote_dir, scenario, port, "publisher_odom.py", ipc_arg), timeout=30)
    for _ in range(40):
        probe = ssh("test -f %s/receiver_summary.json" % shlex.quote(result_dir), timeout=10)
        if probe["returncode"] == 0:
            break
        time.sleep(0.25)
    commands["receiver_logs"] = ssh("podman logs %s > %s/receiver.podman.log 2> %s/receiver.podman.stderr.log || true" % (shlex.quote(receiver), shlex.quote(result_dir), shlex.quote(result_dir)), timeout=30)
    commands["receiver_rm"] = ssh("podman rm -f %s >/dev/null 2>&1 || true" % shlex.quote(receiver), timeout=30)
    commands["publisher_logs"] = ssh("podman logs %s > %s/publisher.podman.log 2> %s/publisher.podman.stderr.log || true" % (shlex.quote(publisher), shlex.quote(result_dir), shlex.quote(result_dir)), timeout=30)
    summary_probe = ssh("cat %s/receiver_summary.json 2>/dev/null || true; echo; cat %s/publisher_summary.json 2>/dev/null || true" % (shlex.quote(result_dir), shlex.quote(result_dir)), timeout=30)
    commands["summary_probe"] = summary_probe
    return {"scenario": scenario, "ipc_arg": ipc_arg, "port": port, "commands": commands}


def main() -> int:
    run_id = time.strftime("cross_container_%Y%m%dT%H%M%SZ", time.gmtime())
    qual_root = ROOT / "qualification" / run_id
    source = qual_root / "source"
    source.mkdir(parents=True)
    (qual_root / "result").mkdir(parents=True)

    copy_tree_files(ROOT, source / "backend_ros", {".py", ".xml", ".cfg", ".json", ".md"})
    copy_tree_files(EXPERIMENT / "backend_adapter" / "backend_adapter", source / "backend_adapter" / "backend_adapter", {".py"})
    copy_file(EXPERIMENT / "backend_adapter" / "config" / "p2b_adapter.example.json", source / "backend_adapter" / "config" / "p2b_adapter.example.json")
    copy_file(EXPERIMENT / "navigation_service" / "core.py", source / "navigation_service" / "core.py")
    write_probe_scripts(source)

    config = json.loads((ROOT / "config" / "p2b_backend_ros.example.json").read_text(encoding="utf-8"))
    config["run_id"] = "ros-cross-qual"
    config["run_epoch_ns"] = 246813579
    config["http"]["port"] = 18765
    config["service"]["body_ready_timeout_s"] = 0.1
    config["gate"]["initial_heartbeat_grace_s"] = 0.3
    config["applied_evidence"]["current_command_path"] = "/qualification/missing_current_command.json"
    config["applied_evidence"]["finish_request_path"] = "/qualification/finish_request.json"
    (qual_root / "runtime_config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    hashes = {str(path.relative_to(source)): sha256(path) for path in sorted(source.rglob("*")) if path.is_file()}
    (qual_root / "source_sha256.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    remote_dir = REMOTE_BASE + "/" + run_id
    preflight = ssh("mkdir -p %s" % shlex.quote(remote_dir), timeout=30)
    sync = run(["rsync", "-a", str(qual_root) + "/", "%s:%s/" % (REMOTE_HOST, remote_dir)], timeout=60)

    scenario_results = []
    default_result = run_scenario(remote_dir, "default_ipc", "", "18765")
    scenario_results.append(default_result)
    pull_default = run(["rsync", "-a", "%s:%s/" % (REMOTE_HOST, remote_dir), str(qual_root) + "/"], timeout=60)

    summaries = load_summaries(qual_root)
    positive = next((name for name, summary in summaries.items() if summary.get("receiver", {}).get("ok") and summary.get("publisher", {}).get("ok")), None)
    if positive is None:
        host_result = run_scenario(remote_dir, "host_ipc", "--ipc=host", "18766")
        scenario_results.append(host_result)

    pull = run(["rsync", "-a", "%s:%s/" % (REMOTE_HOST, remote_dir), str(qual_root) + "/"], timeout=60)
    remote_hash = ssh("cd %s/source && python3 - <<'PY'\nimport hashlib, json, pathlib\nout={}\nfor p in sorted(pathlib.Path('.').rglob('*')):\n    if p.is_file():\n        h=hashlib.sha256(); h.update(p.read_bytes()); out[str(p)]=h.hexdigest()\nprint(json.dumps(out, sort_keys=True))\nPY" % shlex.quote(remote_dir), timeout=30)
    if remote_hash["returncode"] == 0:
        (qual_root / "remote_source_sha256.json").write_text(str(remote_hash["stdout"]), encoding="utf-8")

    summaries = load_summaries(qual_root)
    positive = next((name for name, summary in summaries.items() if summary.get("receiver", {}).get("ok") and summary.get("publisher", {}).get("ok")), None)
    report = {
        "schema": "p2b_backend_ros_cross_container_dds_v1",
        "ok": positive is not None and preflight["returncode"] == 0 and sync["returncode"] == 0 and pull["returncode"] == 0,
        "positive_scenario": positive,
        "run_id": run_id,
        "local_dir": str(qual_root),
        "remote_dir": remote_dir,
        "image": FOXY_IMAGE,
        "scan02_mount": SCAN02,
        "ros_domain_id": ROS_DOMAIN_ID,
        "ros_localhost_only": "1",
        "preflight": preflight,
        "sync": sync,
        "pull_default": pull_default,
        "pull": pull,
        "scenario_results": scenario_results,
        "scenario_summaries": summaries,
        "claim": "Cross-container Foxy CPU DDS smoke only; no PCT worker, Isaac, GPU, control publishing, accepted C++ motion or robot claim.",
    }
    (qual_root / "cross_container_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(qual_root)
    return 0 if report["ok"] else 1


def load_summaries(qual_root: pathlib.Path) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    result_root = qual_root / "result"
    for path in sorted(result_root.glob("*/receiver_summary.json")):
        scenario = path.parent.name
        receiver = json.loads(path.read_text(encoding="utf-8"))
        publisher_path = path.parent / "publisher_summary.json"
        publisher = json.loads(publisher_path.read_text(encoding="utf-8")) if publisher_path.exists() else {}
        out[scenario] = {"receiver": receiver, "publisher": publisher}
    return out


if __name__ == "__main__":
    raise SystemExit(main())
