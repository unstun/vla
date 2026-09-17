#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import time


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(root, manifest):
    root = Path(root)
    for entry in manifest["files"]:
        path = root / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError("manifest mismatch: " + entry["path"])


def verify_v12_runtime(remote_runtime, expected):
    remote_runtime = Path(remote_runtime)
    for rel, digest in expected.items():
        path = remote_runtime / rel
        if sha256(path) != digest:
            raise RuntimeError("remote V12 runtime SHA-256 mismatch: " + rel)


def artifact_hashes(root):
    root = Path(root)
    result = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        result[rel] = sha256(path)
    return result


def ensure_tcp_port_free(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(port)))
    except OSError as exc:
        raise RuntimeError("TCP port is not free on 127.0.0.1:%s (%s)" % (port, exc))
    finally:
        sock.close()


def ensure_container_absent(name):
    if subprocess.run(["podman", "container", "exists", name]).returncode == 0:
        raise RuntimeError("refusing to reuse existing container: " + name)


def wait_snapshot(path, run_id, min_sim_s, timeout_s=600.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = read_json(path)
        except Exception:
            time.sleep(0.05)
            continue
        last = snap
        if snap.get("run_id") == run_id and int(snap.get("run_epoch_ns", 0)) > 0 and float(snap.get("sim_time_s", 0.0)) >= min_sim_s:
            return snap
        time.sleep(0.05)
    raise RuntimeError("runner snapshot not ready; last=%r" % (last,))


def conda_python_script(command, pythonpath, ros_domain_id):
    env_exports = [
        "export PYTHONPATH=" + shlex.quote(pythonpath),
        "export PYTHONDONTWRITEBYTECODE=1",
        "export ROS_DOMAIN_ID=" + shlex.quote(str(ros_domain_id)),
        "export ROS_LOCALHOST_ONLY=1",
    ]
    return " && ".join([
        "source /home/sun/miniconda3/etc/profile.d/conda.sh",
        "conda activate isaaclab",
    ] + env_exports + [command])


def terminate_proc(proc, name, grace=20):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)


def start_popen(cmd, log_path, env=None):
    log = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--foxy-image-id", required=True)
    parser.add_argument("--pct-image-id", required=True)
    parser.add_argument("--remote-v12-runtime", required=True)
    parser.add_argument("--remote-checkpoint", required=True)
    parser.add_argument("--remote-scan-workspace", required=True)
    parser.add_argument("--runner-argv-json", required=True)
    parser.add_argument("--ros-domain-id", type=int, required=True)
    parser.add_argument("--telemetry-port", type=int, required=True)
    parser.add_argument("--command-port", type=int, required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--pct-port", type=int, required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    artifacts = run_root / "artifacts"
    logs = artifacts / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    result = {
        "passed": False,
        "claim": "known-map truth-pose diagnostic two-goal pilot; no LLM/Cortex/SLAM/physical robot",
        "remote_scan_workspace": args.remote_scan_workspace,
    }
    processes = []
    owned_containers = []
    bridge_container = "vla-p2b-bridge-" + run_root.name.lower().replace("_", "-")
    backend_container = "vla-p2b-backend-" + run_root.name.lower().replace("_", "-")
    pct_container = "vla-p2b-pct-" + run_root.name.lower().replace("_", "-")
    try:
        verify_manifest(run_root, read_json(run_root / "inputs/package_manifest.json"))
        verify_manifest(run_root / "bridge", read_json(run_root / "inputs/execution_manifest.json"))
        source_env = read_json(run_root / "source_env_hashes.json")
        if sha256(Path(args.remote_checkpoint)) != source_env["v12_checkpoint_sha256"]:
            raise RuntimeError("remote checkpoint SHA-256 mismatch")
        verify_v12_runtime(args.remote_v12_runtime, source_env["v12_runtime_expected"])
        if not args.remote_scan_workspace:
            raise RuntimeError("accepted remote SCAN workspace is required")
        scan_ws = Path(args.remote_scan_workspace)
        if not (scan_ws / "install").exists():
            raise RuntimeError("remote SCAN workspace lacks install/: " + str(scan_ws))
        for port in [args.telemetry_port, args.command_port, args.http_port, args.pct_port]:
            ensure_tcp_port_free(port)
        for container in [bridge_container, backend_container, pct_container]:
            ensure_container_absent(container)

        runner_argv = json.loads(args.runner_argv_json)
        image_checks = {}
        for label, image_id in [("foxy", args.foxy_image_id), ("pct_humble", args.pct_image_id)]:
            inspected = subprocess.check_output(["podman", "image", "inspect", "--format", "{{.Id}}", image_id], text=True).strip().removeprefix("sha256:")
            if inspected != image_id:
                raise RuntimeError(label + " image identity mismatch: " + inspected)
            image_checks[label] = inspected
        write_json(artifacts / "env_identity.json", {
            "images": image_checks,
            "remote_v12_runtime": args.remote_v12_runtime,
            "remote_checkpoint": args.remote_checkpoint,
            "remote_scan_workspace": args.remote_scan_workspace,
            "ros_domain_id": args.ros_domain_id,
            "ros_localhost_only": 1,
            "ports": {"telemetry": args.telemetry_port, "command": args.command_port, "http": args.http_port, "pct": args.pct_port},
        })

        bridge_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host",
            "--name", bridge_container,
            "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
            "-e", "ROS_LOCALHOST_ONLY=1",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "PYTHONPATH=/bridge",
            "-v", str(run_root / "bridge") + ":/bridge:ro",
            "-v", str(run_root / "config") + ":/config:ro",
            args.foxy_image_id,
            "bash", "-lc",
            "source /opt/ros/foxy/setup.bash && exec python3 -c "
            + repr("from lite3_sim_bridge.foxy_bridge_node import main; main()")
            + " --ros-args --params-file /config/foxy_bridge_two_goal.yaml",
        ]
        write_json(artifacts / "bridge_command.json", bridge_cmd)
        bridge_proc = start_popen(bridge_cmd, logs / "foxy_bridge.log")
        processes.append(("bridge", bridge_proc))
        owned_containers.append(bridge_container)
        time.sleep(2.0)
        if bridge_proc.poll() is not None:
            raise RuntimeError("Foxy bridge exited early")

        runtime_source = Path(args.remote_v12_runtime) / "source"
        runner_pythonpath = ":".join([
            str(run_root / "bridge"),
            str(runtime_source / "rsl_rl"),
            str(runtime_source / "robot_lab"),
            os.environ.get("PYTHONPATH", ""),
        ])
        import_check = """
import importlib.util, json, os, sys
from pathlib import Path

def origin(name):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(name + ' spec not found')
    return str(Path(spec.origin).resolve())
robot = origin('robot_lab')
rsl = origin('rsl_rl')
expected_robot = str(Path(os.environ['EXPECTED_ROBOT_LAB_ROOT']).resolve())
expected_rsl = str(Path(os.environ['EXPECTED_RSL_RL_ROOT']).resolve())
if not robot.startswith(expected_robot + os.sep):
    raise SystemExit('robot_lab spec from unexpected path: ' + robot)
if not rsl.startswith(expected_rsl + os.sep):
    raise SystemExit('rsl_rl spec from unexpected path: ' + rsl)
print(json.dumps({'check_mode':'find_spec_no_module_execution','sys_executable':sys.executable,'conda_prefix':os.environ.get('CONDA_PREFIX'),'robot_lab_spec_origin':robot,'rsl_rl_spec_origin':rsl}, sort_keys=True))
"""
        env = os.environ.copy()
        env["EXPECTED_ROBOT_LAB_ROOT"] = str(runtime_source / "robot_lab")
        env["EXPECTED_RSL_RL_ROOT"] = str(runtime_source / "rsl_rl")
        import_cmd = ["bash", "-lc", conda_python_script("python -c " + shlex.quote(import_check), runner_pythonpath, args.ros_domain_id)]
        import_out = subprocess.check_output(import_cmd, text=True, stderr=subprocess.STDOUT, env=env)
        (logs / "isaac_import_check.log").write_text(import_out, encoding="utf-8")
        write_json(artifacts / "isaac_import_identity.json", json.loads(import_out.strip().splitlines()[-1]))

        runner_cmd = ["bash", "-lc", conda_python_script("exec python -m lite3_sim_bridge.run_pct_scan_building " + shlex.join(runner_argv), runner_pythonpath, args.ros_domain_id)]
        write_json(artifacts / "runner_command.json", runner_cmd)
        runner_proc = start_popen(runner_cmd, logs / "patched_isaac_runner.log", env=os.environ.copy())
        processes.append(("runner", runner_proc))
        snapshot_path = run_root / "artifacts/external_episode/current_command.json"
        first_snapshot = wait_snapshot(snapshot_path, run_root.name, 0.0, timeout_s=600.0)
        run_epoch_ns = int(first_snapshot["run_epoch_ns"])
        result["run_epoch_ns"] = run_epoch_ns

        pct_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--name", pct_container,
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", str(run_root) + ":/qualification:ro",
            args.pct_image_id,
            "bash", "-lc",
            "source /opt/ros/humble/setup.bash && "
            "export PYTHONPATH=/qualification/backend_adapter:/qualification/pct_runtime/python:${PYTHONPATH:-} && "
            "export LD_LIBRARY_PATH=/qualification/pct_runtime/lib:${LD_LIBRARY_PATH:-} && "
            "exec python3 -m backend_adapter.pct_worker "
            "--host 127.0.0.1 --port %d " % args.pct_port +
            "--pct-source-root /qualification/pct_runtime/python "
            "--rsg-root /qualification/inputs "
            "--tomogram-path /qualification/inputs/new_building.pickle "
            "--reference-height-m 0.35",
        ]
        write_json(artifacts / "pct_worker_command.json", pct_cmd)
        pct_proc = start_popen(pct_cmd, logs / "pct_worker.log")
        processes.append(("pct_worker", pct_proc))
        owned_containers.append(pct_container)
        time.sleep(2.0)
        if pct_proc.poll() is not None:
            raise RuntimeError("PCT worker exited early")

        backend_config_path = run_root / "config/p2b_backend_ros.two_goal.json"
        backend_cfg = read_json(backend_config_path)
        backend_cfg["run_epoch_ns"] = run_epoch_ns
        backend_cfg["applied_evidence"]["current_command_path"] = str(snapshot_path)
        backend_cfg["applied_evidence"]["finish_request_path"] = str(run_root / "artifacts/external_episode/finish_request.json")
        write_json(backend_config_path, backend_cfg)
        resolved_backend_config_path = artifacts / "resolved_backend_config.json"
        write_json(resolved_backend_config_path, {
            "schema_version": 1,
            "source_config": str(backend_config_path),
            "run_epoch_ns_source": "fresh runner current_command.json",
            "resolved_config": backend_cfg,
        })

        backend_script = """set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID={ros_domain_id}
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/backend_ros:/backend_adapter:/bridge:${{PYTHONPATH:-}}
ros2 run scan_planner scan_planner_node --ros-args --params-file /config/planner.yaml -r body_pose:=/quad_0/body_pose -r sensor_pose:=/quad_0/lidar_pose -r cloud:=/quad_0/cloud > /logs/scan_planner_node.log 2>&1 &
scan_pid=$!
ros2 run scan_planner closed_loop_controller --ros-args --params-file /config/controller.yaml -r body_pose:=/quad_0/body_pose > /logs/closed_loop_controller.log 2>&1 &
controller_pid=$!
cleanup() {{
  kill "$scan_pid" "$controller_pid" 2>/dev/null || true
}}
trap cleanup EXIT INT TERM
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.json --run-id {run_id} --run-epoch-ns {run_epoch_ns} --applied-snapshot {snapshot_path} --finish-request {finish_request_path} --pct-port {pct_port} --http-port {http_port}
""".format(
            ros_domain_id=args.ros_domain_id,
            run_id=shlex.quote(run_root.name),
            run_epoch_ns=run_epoch_ns,
            snapshot_path=shlex.quote(str(snapshot_path)),
            finish_request_path=shlex.quote(str(run_root / "artifacts/external_episode/finish_request.json")),
            pct_port=args.pct_port,
            http_port=args.http_port,
        )
        backend_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--name", backend_container,
            "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
            "-e", "ROS_LOCALHOST_ONLY=1",
            "-v", str(run_root / "backend_ros") + ":/backend_ros:ro",
            "-v", str(run_root / "backend_adapter") + ":/backend_adapter:ro",
            "-v", str(run_root / "navigation_service") + ":/navigation_service:ro",
            "-v", str(run_root / "bridge") + ":/bridge:ro",
            "-v", str(run_root / "config") + ":/config:rw",
            "-v", str(logs) + ":/logs:rw",
            "-v", str(run_root) + ":" + str(run_root) + ":rw",
            "-v", str(scan_ws) + ":/workspace:ro",
            args.foxy_image_id,
            "bash", "-lc", backend_script,
        ]
        write_json(artifacts / "backend_command.json", backend_cmd)
        backend_proc = start_popen(backend_cmd, logs / "backend_container.log")
        processes.append(("backend", backend_proc))
        owned_containers.append(backend_container)
        time.sleep(2.0)
        if backend_proc.poll() is not None:
            raise RuntimeError("backend/SCAN container exited early")

        driver_cmd = ["python3", str(run_root / "pilot_driver.py"), "--run-root", str(run_root), "--http-port", str(args.http_port), "--run-id", run_root.name]
        write_json(artifacts / "pilot_driver_command.json", driver_cmd)
        driver = subprocess.run(driver_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1200)
        (logs / "pilot_driver.log").write_text(driver.stdout, encoding="utf-8")
        result["pilot_driver_exit_code"] = driver.returncode
        if driver.returncode != 0:
            raise RuntimeError("pilot driver failed with exit %d" % driver.returncode)
        runner_exit = runner_proc.wait(timeout=1200.0)
        result["runner_exit_code"] = runner_exit
        if runner_exit != 0:
            raise RuntimeError("runner exit code %s" % runner_exit)
        summary = read_json(run_root / "artifacts/runner_output/summary.json")
        result["runner_summary"] = summary
        if summary.get("status") != "EXTERNAL_EPISODE_FINISHED":
            raise RuntimeError("unexpected runner summary status: " + str(summary.get("status")))
        result["passed"] = True
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        for _name, proc in reversed(processes):
            terminate_proc(proc, _name)
        for container in reversed(owned_containers):
            subprocess.run(["podman", "rm", "-f", container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        write_json(artifacts / "result.json", result)
        write_json(artifacts / "artifact_hashes.json", artifact_hashes(artifacts))


if __name__ == "__main__":
    main()
