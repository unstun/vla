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
import threading
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


def scan_tree_hashes(workspace, subdir):
    """Hash regular files under workspace/subdir, keyed relative to workspace.

    Python bytecode caches are listed as excluded instead of hashed; the
    recorded scan_03 install identity contains none although the Foxy build
    ran compileall on the installed message package.
    """
    workspace = Path(workspace)
    files = {}
    excluded = []
    base = workspace / subdir
    if base.is_dir():
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = path.relative_to(workspace)
            if "__pycache__" in rel.parts or path.suffix in (".pyc", ".pyo"):
                excluded.append(rel.as_posix())
                continue
            files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files, excluded


def compare_hash_maps(expected, actual):
    shared = set(expected) & set(actual)
    return {
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing": sorted(set(expected) - set(actual)),
        "unexpected": sorted(set(actual) - set(expected)),
        "mismatched": sorted(k for k in shared if expected[k] != actual[k]),
        "match": bool(expected) and expected == actual,
    }


def scan_workspace_gate(workspace, identity):
    """Compare a SCAN workspace with an accepted build identity; returns a record."""
    workspace = Path(workspace)
    identity = identity or {}
    record = {"schema_version": 1, "workspace": str(workspace), "passed": False, "errors": []}
    gate = identity.get("workspace_gate")
    if not isinstance(gate, dict):
        record["errors"].append("accepted SCAN identity lacks workspace_gate")
        return record
    expected_remote = gate.get("expected_remote_workspace")
    record["expected_remote_workspace"] = expected_remote
    if expected_remote is not None and expected_remote != str(workspace):
        record["errors"].append("workspace path differs from the build identity")
    source, source_excluded = scan_tree_hashes(workspace, "src")
    record["source"] = compare_hash_maps(gate.get("expected_source_files") or {}, source)
    record["source"]["excluded"] = source_excluded
    if not record["source"]["match"]:
        record["errors"].append("SCAN src/ differs from source_sha256.json")
    installed_expected = (identity.get("install_identity") or {}).get("installed_files")
    if installed_expected:
        installed, install_excluded = scan_tree_hashes(workspace, "install")
        record["install_checked"] = True
        record["install"] = compare_hash_maps(installed_expected, installed)
        record["install"]["excluded"] = install_excluded
        if not record["install"]["match"]:
            record["errors"].append("SCAN install/ differs from install_identity.json")
    elif gate.get("allow_missing_install_identity") is True:
        record["install_checked"] = False
        record["install_dir_exists"] = (workspace / "install").is_dir()
        if not record["install_dir_exists"]:
            record["errors"].append("SCAN workspace lacks install/")
    else:
        record["errors"].append("install identity missing and not explicitly allowed")
    record["passed"] = not record["errors"]
    return record


GPU_SAMPLE_INTERVAL_S = 1.0


def query_gpus(timeout_s=2.0):
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("nvidia-smi exit %d: %s" % (proc.returncode, proc.stderr.strip()[-500:]))
    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        values = [value.strip() for value in line.split(",")]
        try:
            utilization = float(values[3])
        except ValueError:
            utilization = None
        rows.append({"index": int(values[0]), "memory_used_mib": float(values[1]), "memory_total_mib": float(values[2]), "utilization_percent": utilization})
    if not rows:
        raise RuntimeError("nvidia-smi returned no GPU rows")
    return rows


class GpuSampler:
    """Device-wide nvidia-smi sampling in a background thread, one JSONL row per interval."""

    def __init__(self, path, interval_s):
        self.path = Path(path)
        self.interval_s = float(interval_s)
        self.stop_event = threading.Event()
        self.thread = None
        self.started = None
        self.summary = {
            "interval_s": self.interval_s,
            "samples_path": self.path.name,
            "scope": "device-wide nvidia-smi memory.used; includes any process on the GPU, not only this run",
            "sample_count": 0,
            "error_count": 0,
            "errors": [],
            "first_sample": None,
            "peak_memory_used_mib": None,
            "peak_elapsed_s": None,
            "peak_by_gpu": {},
        }

    def start(self):
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._loop, name="gpu-sampler", daemon=True)
        self.thread.start()

    def _record(self, row):
        summary = self.summary
        if summary["first_sample"] is None:
            summary["first_sample"] = row
        for gpu in row["gpus"]:
            peak = summary["peak_by_gpu"].setdefault(str(gpu["index"]), {"memory_used_mib": None})
            if peak["memory_used_mib"] is None or gpu["memory_used_mib"] > peak["memory_used_mib"]:
                peak.update(memory_used_mib=gpu["memory_used_mib"], memory_total_mib=gpu["memory_total_mib"], elapsed_s=row["elapsed_s"])
            if summary["peak_memory_used_mib"] is None or gpu["memory_used_mib"] > summary["peak_memory_used_mib"]:
                summary["peak_memory_used_mib"] = gpu["memory_used_mib"]
                summary["peak_elapsed_s"] = row["elapsed_s"]

    def _loop(self):
        with self.path.open("w", encoding="utf-8") as stream:
            while True:
                row = {"monotonic_ns": time.monotonic_ns(), "wall_time_ns": time.time_ns(), "elapsed_s": time.monotonic() - self.started}
                try:
                    row["gpus"] = query_gpus()
                    self._record(row)
                except Exception as exc:
                    row["error"] = "%s: %s" % (exc.__class__.__name__, exc)
                    self.summary["error_count"] += 1
                    if len(self.summary["errors"]) < 5:
                        self.summary["errors"].append(row["error"])
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                self.summary["sample_count"] += 1
                if self.stop_event.wait(self.interval_s):
                    return

    def stop(self):
        if self.thread is None:
            return dict(self.summary, started=False)
        self.stop_event.set()
        self.thread.join(timeout=5.0)
        return dict(self.summary, started=True, stopped=not self.thread.is_alive(), sampled_wall_s=time.monotonic() - self.started)


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


def wait_snapshot(path, run_id, min_sim_s, timeout_s=600.0, runner_proc=None):
    path = Path(path)
    runtime_error_path = path.parents[1] / "runner_output/runtime_error.json"
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        if runtime_error_path.exists():
            raise RuntimeError("runner_runtime_error_before_snapshot: " + runtime_error_path.read_text(encoding="utf-8")[:1000])
        if runner_proc is not None:
            exit_code = runner_proc.poll()
            if exit_code is not None:
                raise RuntimeError("runner_exited_before_snapshot: exit_code=%s last=%r" % (exit_code, last))
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
    record = {"name": name, "pid": getattr(proc, "pid", None), "action": "none", "ok": True}
    if proc is None:
        record["reason"] = "missing"
        return record
    if proc.poll() is not None:
        record["reason"] = "already_exited"
        record["returncode"] = proc.poll()
        return record
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        record["action"] = "sigterm"
    except ProcessLookupError:
        record["reason"] = "process_lookup_error"
        return record
    try:
        proc.wait(timeout=grace)
        record["returncode"] = proc.poll()
        return record
    except subprocess.TimeoutExpired:
        record["action"] = "sigkill"
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5.0)
            record["returncode"] = proc.poll()
            return record
        except BaseException as exc:
            record["ok"] = False
            record["error_type"] = exc.__class__.__name__
            record["error"] = str(exc)
            return record
    except BaseException as exc:
        record["ok"] = False
        record["error_type"] = exc.__class__.__name__
        record["error"] = str(exc)
        return record


def cleanup_container(container, timeout_s=20.0):
    record = {"container": container, "timeout_s": timeout_s, "ok": False}
    try:
        proc = subprocess.run(["podman", "rm", "-f", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, check=False)
        record.update({"returncode": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:], "ok": proc.returncode == 0})
    except subprocess.TimeoutExpired as exc:
        record.update({"timeout": True, "error_type": "TimeoutExpired", "error": str(exc)})
    except BaseException as exc:
        record.update({"error_type": exc.__class__.__name__, "error": str(exc)})
    return record


def tcp_port_free_record(port):
    try:
        ensure_tcp_port_free(port)
        return {"port": int(port), "free": True}
    except BaseException as exc:
        return {"port": int(port), "free": False, "error_type": exc.__class__.__name__, "error": str(exc)}


def finalize_result_artifacts(artifacts, result, phase):
    record = {"phase": phase, "ok": False, "monotonic_ns": time.monotonic_ns()}
    try:
        result["last_result_write_phase"] = phase
        write_json(artifacts / "result.json", result)
        hashes = artifact_hashes(artifacts)
        write_json(artifacts / "artifact_hashes.json", hashes)
        record.update({"ok": True, "artifact_count": len(hashes)})
    except BaseException as exc:
        record.update({"error_type": exc.__class__.__name__, "error": str(exc)})
    return record


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
    parser.add_argument("--cancel-displacement-m", type=float, required=True)
    args = parser.parse_args()

    started_monotonic = time.monotonic()
    run_root = Path(args.run_root)
    artifacts = run_root / "artifacts"
    logs = artifacts / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    result = {
        "passed": False,
        "claim": "bounded stair observation with actual RTX geometric sweeps and official human; no LLM/Cortex/SLAM/physical robot",
        "remote_scan_workspace": args.remote_scan_workspace,
        "cancel_displacement_m": args.cancel_displacement_m,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    idle = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
    if idle.returncode or idle.stdout.strip():
        raise RuntimeError("GPU must be idle before the bounded stair run")
    gpu_sampler = GpuSampler(artifacts / "gpu_samples.jsonl", GPU_SAMPLE_INTERVAL_S)
    scan_ws = None
    scan_identity = None
    processes = []
    owned_containers = []
    bridge_container = "vla-p2b-bridge-" + run_root.name.lower().replace("_", "-")
    backend_container = "vla-p2b-backend-" + run_root.name.lower().replace("_", "-")
    pct_container = "vla-p2b-pct-" + run_root.name.lower().replace("_", "-")
    try:
        gpu_sampler.start()
        verify_manifest(run_root, read_json(run_root / "inputs/package_manifest.json"))
        verify_manifest(run_root / "bridge", read_json(run_root / "inputs/execution_manifest.json"))
        source_env = read_json(run_root / "source_env_hashes.json")
        if sha256(Path(args.remote_checkpoint)) != source_env["v12_checkpoint_sha256"]:
            raise RuntimeError("remote checkpoint SHA-256 mismatch")
        verify_v12_runtime(args.remote_v12_runtime, source_env["v12_runtime_expected"])
        if not args.remote_scan_workspace:
            raise RuntimeError("accepted remote SCAN workspace is required")
        scan_ws = Path(args.remote_scan_workspace)
        scan_identity = source_env.get("accepted_scan_build_identity")
        scan_gate = scan_workspace_gate(scan_ws, scan_identity)
        write_json(artifacts / "scan_workspace_gate.json", scan_gate)
        result["scan_workspace_gate"] = {"passed": scan_gate["passed"], "errors": scan_gate["errors"], "record": "scan_workspace_gate.json"}
        if not scan_gate["passed"]:
            raise RuntimeError("remote SCAN workspace hash gate failed: " + "; ".join(scan_gate["errors"]))
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
            "ros_container_ipc": "host",
            "transport_qualification": "backend_ros/qualification/cross_container_20260916T161849Z: isolated IPC failed, host IPC passed",
            "ports": {"telemetry": args.telemetry_port, "command": args.command_port, "http": args.http_port, "pct": args.pct_port},
        })

        bridge_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host",
            "--ipc=host",
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
        first_snapshot = wait_snapshot(snapshot_path, run_root.name, 0.0, timeout_s=600.0, runner_proc=runner_proc)
        run_epoch_ns = int(first_snapshot["run_epoch_ns"])
        result["run_epoch_ns"] = run_epoch_ns

        pct_script = """set -eo pipefail
source /opt/ros/humble/setup.bash
export PYTHONPATH=/qualification/backend_adapter:/qualification/pct_runtime/python:/qualification/bridge/lite3_sim_bridge:${{PYTHONPATH:-}}
export LD_LIBRARY_PATH=/qualification/pct_runtime/lib:${{LD_LIBRARY_PATH:-}}
python3 /qualification/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py --ros-args -p map_path:=/qualification/inputs/new_building.pickle -p use_sim_time:=true >/logs/pct_support.log 2>&1 &
support_pid=$!
python3 /qualification/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py --ros-args -r __node:=pct_tracking_ground_publisher -p map_path:=/qualification/inputs/new_building.pickle -p ground_mode:=tracking_physical -p use_sim_time:=true >/logs/tracker_ground.log 2>&1 &
tracking_ground_pid=$!
python3 -m backend_adapter.pct_worker --host 127.0.0.1 --port {port} --pct-source-root /qualification/pct_runtime/python --rsg-root /qualification/inputs --tomogram-path /qualification/inputs/new_building.pickle --reference-height-m 0.30 &
worker_pid=$!
trap 'kill "$support_pid" "$worker_pid" "$tracking_ground_pid" 2>/dev/null || true' EXIT INT TERM
wait -n "$support_pid" "$worker_pid" "$tracking_ground_pid"
exit 1
""".format(port=args.pct_port)
        pct_cmd = ["podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host", "--name", pct_container,
                   "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "ROS_LOCALHOST_ONLY=1",
                   "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
                   "-v", str(run_root) + ":/qualification:ro", "-v", str(logs) + ":/logs:rw",
                   args.pct_image_id, "bash", "-lc", pct_script]
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
python3 /qualification/inputs/static_background/unpack_foreground_dependency.py --wheel /qualification/inputs/static_background/scipy.whl --manifest /qualification/inputs/static_background/dependency_manifest.json --destination /tmp/foreground_dependencies --receipt /logs/foreground_dependency_receipt.json
env OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/foreground_dependencies:${{PYTHONPATH:-}} ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args -p use_sim_time:=true -p static_background_pcd:=/qualification/inputs/static_background/building2_9.pcd > /logs/moving_cluster_tracker.log 2>&1 &
tracker_pid=$!
python3 -m lite3_sim_bridge.reactive_health --output {health_path} --run-id {run_id} --epoch {run_epoch_ns} --ros-args -p use_sim_time:=true > /logs/reactive_health.log 2>&1 &
health_pid=$!
cleanup() {{
  kill "$scan_pid" "$controller_pid" "$tracker_pid" "$health_pid" "$backend_pid" 2>/dev/null || true
}}
trap cleanup EXIT INT TERM
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.json --run-id {run_id} --run-epoch-ns {run_epoch_ns} --applied-snapshot {snapshot_path} --finish-request {finish_request_path} --pct-port {pct_port} --http-port {http_port} &
backend_pid=$!
wait -n "$scan_pid" "$controller_pid" "$tracker_pid" "$health_pid" "$backend_pid"
exit 1
""".format(
            ros_domain_id=args.ros_domain_id,
            health_path=shlex.quote(str(artifacts / "runtime_health.json")),
            run_id=shlex.quote(run_root.name),
            run_epoch_ns=run_epoch_ns,
            snapshot_path=shlex.quote(str(snapshot_path)),
            finish_request_path=shlex.quote(str(run_root / "artifacts/external_episode/finish_request.json")),
            pct_port=args.pct_port,
            http_port=args.http_port,
        )
        backend_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--name", backend_container,
            "--ipc=host",
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
            "-v", str(run_root) + ":/qualification:ro",
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

        driver_cmd = ["python3", str(run_root / "pilot_driver.py"), "--run-root", str(run_root), "--http-port", str(args.http_port), "--run-id", run_root.name, "--cancel-displacement-m", repr(args.cancel_displacement_m)]
        write_json(artifacts / "pilot_driver_command.json", driver_cmd)
        driver = start_popen(driver_cmd, logs / "pilot_driver.log")
        processes.append(("driver", driver))
        deadline = time.monotonic() + 900.0
        while driver.poll() is None:
            dead = [(name, proc.returncode) for name, proc in processes if name != "driver" and proc.poll() is not None]
            if dead:
                raise RuntimeError("required runtime process exited: " + repr(dead))
            if time.monotonic() > deadline:
                raise RuntimeError("stair driver wall deadline exceeded")
            time.sleep(0.1)
        result["pilot_driver_exit_code"] = driver.returncode
        if driver.returncode != 0:
            raise RuntimeError("stair driver failed with exit %d" % driver.returncode)
        runner_exit = runner_proc.wait(timeout=1200.0)
        result["runner_exit_code"] = runner_exit
        if runner_exit != 0:
            raise RuntimeError("runner exit code %s" % runner_exit)
        summary = read_json(run_root / "artifacts/runner_output/summary.json")
        result["runner_summary"] = summary
        if summary.get("status") != "EXTERNAL_EPISODE_FINISHED":
            raise RuntimeError("unexpected runner summary status: " + str(summary.get("status")))
        result["passed"] = True
    except BaseException as exc:
        result["error"] = str(exc)
        result["error_type"] = exc.__class__.__name__
        raise
    finally:
        cleanup_records = []
        finalization_records = []
        try:
            for _name, proc in reversed(processes):
                cleanup_records.append(terminate_proc(proc, _name))
        except BaseException as exc:
            cleanup_records.append({"scope": "process_cleanup", "ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        result["process_cleanup"] = cleanup_records
        finalization_records.append(finalize_result_artifacts(artifacts, result, "after_process_cleanup"))

        container_records = []
        for container in reversed(owned_containers):
            try:
                container_records.append(cleanup_container(container, timeout_s=20.0))
            except BaseException as exc:
                container_records.append({"container": container, "ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        result["container_cleanup"] = container_records
        result["post_cleanup_ports"] = {
            "telemetry": tcp_port_free_record(args.telemetry_port),
            "command": tcp_port_free_record(args.command_port),
            "http": tcp_port_free_record(args.http_port),
            "pct": tcp_port_free_record(args.pct_port),
        }
        try:
            result["gpu_memory"] = gpu_sampler.stop()
        except BaseException as exc:
            result["gpu_memory"] = {"ok": False, "error_type": exc.__class__.__name__, "error": str(exc)}
        if scan_ws is not None and (result.get("scan_workspace_gate") or {}).get("passed"):
            try:
                scan_gate_after = scan_workspace_gate(scan_ws, scan_identity)
                write_json(artifacts / "scan_workspace_gate_after.json", scan_gate_after)
                result["scan_workspace_gate_after"] = {"passed": scan_gate_after["passed"], "errors": scan_gate_after["errors"], "record": "scan_workspace_gate_after.json"}
            except BaseException as exc:
                result["scan_workspace_gate_after"] = {"passed": False, "error_type": exc.__class__.__name__, "error": str(exc)}
            if not result["scan_workspace_gate_after"]["passed"]:
                result["passed"] = False
        result["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result["remote_wall_seconds"] = time.monotonic() - started_monotonic
        result["remote_wall_seconds_scope"] = "remote_worker.py main() start to cleanup end, before the last result writes"
        result["cleanup_errors"] = [item for item in cleanup_records + container_records if item.get("ok") is False]
        result["artifact_finalization"] = finalization_records
        finalization_records.append(finalize_result_artifacts(artifacts, result, "after_container_cleanup"))
        result["artifact_finalization"] = finalization_records
        finalize_result_artifacts(artifacts, result, "final")
    # Reached only when the episode raised nothing: a post-run SCAN workspace
    # change must still fail the remote command instead of exiting 0.
    if (result.get("scan_workspace_gate_after") or {}).get("passed") is not True:
        raise SystemExit("SCAN workspace hash gate failed after the run; see artifacts/scan_workspace_gate_after.json")


if __name__ == "__main__":
    main()
