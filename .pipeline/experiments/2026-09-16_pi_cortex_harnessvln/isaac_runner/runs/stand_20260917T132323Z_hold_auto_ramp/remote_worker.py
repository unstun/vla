#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import subprocess
import sys
import time


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_log(cmd, log_path, env=None, timeout=None, check=True):
    with open(log_path, "w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, text=True,
                              env=env, timeout=timeout)
    if check and proc.returncode:
        raise RuntimeError("%s failed with exit %s" % (" ".join(cmd), proc.returncode))
    return proc.returncode


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


def runner_arg_value(argv, name):
    for idx, item in enumerate(argv):
        if item == name and idx + 1 < len(argv):
            return argv[idx + 1]
    raise RuntimeError("runner argument missing: " + name)


def ensure_tcp_port_free(port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(port)))
    except OSError as exc:
        raise RuntimeError("TCP port is not free on 127.0.0.1: %s (%s)" % (port, exc))
    finally:
        sock.close()


def ensure_container_absent(container_name):
    proc = subprocess.run(["podman", "container", "exists", container_name])
    if proc.returncode == 0:
        raise RuntimeError("refusing to reuse existing container: " + container_name)


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--foxy-image-id", required=True)
    parser.add_argument("--remote-v12-runtime", required=True)
    parser.add_argument("--remote-checkpoint", required=True)
    parser.add_argument("--runner-argv-json", required=True)
    parser.add_argument("--ros-domain-id", type=int, required=True)
    parser.add_argument("--finish-after-sim-seconds", type=float, default=2.0)
    args = parser.parse_args()

    run_root = Path(args.run_root)
    artifacts = run_root / "artifacts"
    logs = artifacts / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    result = {
        "passed": False,
        "claim": "stand-only patched runner plus real Foxy bridge; no navigation",
        "isaac_run": True,
        "foxy_bridge": True,
        "scan_started": False,
        "motion_publisher_started": False,
        "physical_actuation": False,
    }
    bridge_proc = None
    runner_proc = None
    owned_container_started = False
    container_name = "vla-p2b-stand-" + run_root.name.lower().replace("_", "-")
    try:
        verify_manifest(run_root / "bridge", json.loads((run_root / "inputs/execution_manifest.json").read_text()))
        verify_manifest(run_root, json.loads((run_root / "inputs/package_manifest.json").read_text()))
        source_env = json.loads((run_root / "source_env_hashes.json").read_text())
        if sha256(Path(args.remote_checkpoint)) != source_env["v12_checkpoint_sha256"]:
            raise RuntimeError("remote checkpoint SHA-256 mismatch")
        verify_v12_runtime(args.remote_v12_runtime, source_env["v12_runtime_expected"])

        image_id = subprocess.check_output([
            "podman", "image", "inspect", "--format", "{{.Id}}", args.foxy_image_id
        ], text=True).strip()
        normalized = image_id.removeprefix("sha256:")
        if normalized != args.foxy_image_id:
            raise RuntimeError("Foxy image identity mismatch: " + image_id)
        (artifacts / "env_identity.json").write_text(json.dumps({
            "foxy_image_id": normalized,
            "isaac_python": "conda activate isaaclab; python",
            "remote_v12_runtime": args.remote_v12_runtime,
            "remote_checkpoint": args.remote_checkpoint,
            "ros_domain_id": args.ros_domain_id,
            "ros_localhost_only": 1,
            "network": "host TCP, ROS localhost-only",
            "hardware_devices": "none mounted into Foxy container",
            "runner_pythonpath_policy": [
                "<run_root>/bridge",
                "<remote_v12_runtime>/source/rsl_rl",
                "<remote_v12_runtime>/source/robot_lab",
            ],
        }, indent=2) + "\n")

        runner_argv = json.loads(args.runner_argv_json)
        stance_hold = runner_arg_value(runner_argv, "--stance-hold")
        result["stance_hold"] = stance_hold
        result["finish_after_sim_seconds"] = args.finish_after_sim_seconds
        ensure_container_absent(container_name)
        ensure_tcp_port_free(runner_arg_value(runner_argv, "--telemetry-port"))
        ensure_tcp_port_free(runner_arg_value(runner_argv, "--command-port"))

        bridge_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host",
            "--name", container_name,
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
            + " --ros-args --params-file /config/foxy_bridge_stand.yaml",
        ]
        (artifacts / "bridge_command.json").write_text(json.dumps(bridge_cmd, indent=2) + "\n")
        bridge_log = open(logs / "foxy_bridge.log", "w", encoding="utf-8")
        bridge_proc = subprocess.Popen(bridge_cmd, stdout=bridge_log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        owned_container_started = True
        time.sleep(2.0)
        if bridge_proc.poll() is not None:
            raise RuntimeError("Foxy bridge exited early")

        runtime_source = Path(args.remote_v12_runtime) / "source"
        pythonpath_parts = [
            str(run_root / "bridge"),
            str(runtime_source / "rsl_rl"),
            str(runtime_source / "robot_lab"),
        ]
        if os.environ.get("PYTHONPATH"):
            pythonpath_parts.append(os.environ["PYTHONPATH"])
        runner_pythonpath = ":".join(pythonpath_parts)
        import_check = """
import importlib.util
import json
import os
import sys
from pathlib import Path

def spec_origin(name):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(name + ' spec not found')
    return str(Path(spec.origin).resolve())

expected_robot = str(Path(os.environ['EXPECTED_ROBOT_LAB_ROOT']).resolve())
expected_rsl = str(Path(os.environ['EXPECTED_RSL_RL_ROOT']).resolve())
robot_origin = spec_origin('robot_lab')
rsl_origin = spec_origin('rsl_rl')
if not robot_origin.startswith(expected_robot + os.sep):
    raise SystemExit('robot_lab spec from unexpected path: ' + robot_origin)
if not rsl_origin.startswith(expected_rsl + os.sep):
    raise SystemExit('rsl_rl spec from unexpected path: ' + rsl_origin)
print(json.dumps({
    'check_mode': 'find_spec_no_module_execution',
    'sys_executable': sys.executable,
    'conda_prefix': os.environ.get('CONDA_PREFIX'),
    'robot_lab_spec_origin': robot_origin,
    'rsl_rl_spec_origin': rsl_origin,
}, sort_keys=True))
"""
        check_env = os.environ.copy()
        check_env["EXPECTED_ROBOT_LAB_ROOT"] = str(runtime_source / "robot_lab")
        check_env["EXPECTED_RSL_RL_ROOT"] = str(runtime_source / "rsl_rl")
        import_check_cmd = [
            "bash",
            "-lc",
            conda_python_script("python -c " + shlex.quote(import_check), runner_pythonpath, args.ros_domain_id),
        ]
        (artifacts / "isaac_import_check_command.json").write_text(json.dumps(import_check_cmd, indent=2) + "\n")
        import_check_log = subprocess.check_output(import_check_cmd, text=True, env=check_env, stderr=subprocess.STDOUT)
        (logs / "isaac_import_check.log").write_text(import_check_log, encoding="utf-8")
        import_identity = json.loads(import_check_log.strip().splitlines()[-1])
        write_json(artifacts / "isaac_import_identity.json", import_identity)

        runner_cmd = [
            "bash",
            "-lc",
            conda_python_script(
                "exec python -m lite3_sim_bridge.run_pct_scan_building " + shlex.join(runner_argv),
                runner_pythonpath,
                args.ros_domain_id,
            ),
        ]
        (artifacts / "runner_command.json").write_text(json.dumps(runner_cmd, indent=2) + "\n")
        runner_log = open(logs / "patched_isaac_runner.log", "w", encoding="utf-8")
        runner_proc = subprocess.Popen(runner_cmd, stdout=runner_log, stderr=subprocess.STDOUT,
                                       env=os.environ.copy(), start_new_session=True)

        status_path = run_root / "artifacts/external_episode/current_command.json"
        deadline = time.monotonic() + 600.0
        last_snapshot = None
        while time.monotonic() < deadline:
            if runner_proc.poll() is not None:
                raise RuntimeError("runner exited before current_command.json")
            if status_path.exists():
                try:
                    snapshot = json.loads(status_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    time.sleep(0.05)
                    continue
                last_snapshot = snapshot
                if (snapshot.get("run_id") == run_root.name
                        and float(snapshot.get("sim_time_s", 0.0)) >= args.finish_after_sim_seconds):
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("current_command.json did not reach %g sim seconds" % args.finish_after_sim_seconds)
        finish = {
            "schema_version": 1,
            "run_id": run_root.name,
            "request_id": "stand-finish-" + run_root.name,
            "observed_run_epoch_ns": int(last_snapshot["run_epoch_ns"]),
            "requested_at_monotonic_ns": time.monotonic_ns(),
            "backend_terminal_status": "FINISHED",
            "note": "stand-only qualification finish after >=%g sim seconds" % args.finish_after_sim_seconds,
        }
        write_json(run_root / "artifacts/external_episode/finish_request.json", finish)
        result["finish_request"] = finish
        exit_code = runner_proc.wait(timeout=660.0)
        result["runner_exit_code"] = exit_code
        if exit_code != 0:
            raise RuntimeError("runner exit code %s" % exit_code)
        summary = json.loads((run_root / "artifacts/runner_output/summary.json").read_text())
        result["summary_status"] = summary.get("status")
        result["summary"] = {
            "status": summary.get("status"),
            "sim_seconds": summary.get("sim_seconds"),
            "record_count": summary.get("record_count"),
            "max_admitted_command_norm_mps": summary.get("max_admitted_command_norm_mps"),
            "max_horizontal_speed_mps": summary.get("max_horizontal_speed_mps"),
            "case_failed": summary.get("case_failed"),
            "stance_hold": summary.get("stance_hold"),
        }
        if summary.get("status") != "EXTERNAL_EPISODE_FINISHED":
            raise RuntimeError("unexpected summary status: " + str(summary.get("status")))
        if (summary.get("stance_hold") or {}).get("mode") != stance_hold:
            raise RuntimeError("runner summary stance_hold mode differs from --stance-hold " + stance_hold)
        result["passed"] = True
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        if runner_proc is not None and runner_proc.poll() is None:
            os.killpg(runner_proc.pid, signal.SIGTERM)
            try:
                runner_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(runner_proc.pid, signal.SIGKILL)
        if owned_container_started:
            subprocess.run(["podman", "rm", "-f", container_name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        if bridge_proc is not None and bridge_proc.poll() is None:
            try:
                os.killpg(bridge_proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        write_json(artifacts / "result.json", result)
        write_json(artifacts / "artifact_hashes.json", artifact_hashes(artifacts))


if __name__ == "__main__":
    main()
