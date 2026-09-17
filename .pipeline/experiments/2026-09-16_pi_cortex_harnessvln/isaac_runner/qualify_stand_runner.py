#!/usr/bin/env python3
"""Prepare or execute the P2B patched-runner stand-only qualification.

Default mode is local-only: create an immutable run package and write the exact
remote commands for the parent. Pass --execute to sync to gpu5070ti, run the
real Foxy bridge plus the patched Isaac runner, collect artifacts, and verify
returned hashes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
from typing import Dict, Iterable, List, Tuple


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
BRIDGE_REF = (
    ROOT
    / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/"
    "machine-dog-nav/integration/lite3_sim_bridge"
)
ACQUISITION = ROOT / "references/upstream/2026-09-16_lite3_isaac_harness_backend/acquisition.json"
V12_REF = ROOT / "references/upstream/2026-09-11_lite3_v12_locomotion"
FOXY_IMAGE_ID = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
DEFAULT_REMOTE_ROOT = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/runner_qualification"
DEFAULT_REMOTE_V12 = "/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12"
DEFAULT_REMOTE_CHECKPOINT = (
    "/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/"
    "source/checkpoint/model_149999.pt"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copytree_clean(src: Path, dst: Path) -> None:
    def ignore(_dir, names):
        return {
            name
            for name in names
            if name in {"__pycache__", ".pytest_cache"} or name.endswith(".pyc")
        }

    shutil.copytree(src, dst, ignore=ignore)


def load_materializer():
    spec = importlib.util.spec_from_file_location(
        "materialize_runner_patch", str(HERE / "materialize_runner_patch.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def verify_input_manifest() -> dict:
    manifest = json.loads((P2B / "input_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = P2B / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError("input manifest mismatch: " + item["path"])
    return manifest


def verify_bridge_source() -> dict:
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    expected = {
        name.removeprefix("integration/lite3_sim_bridge/"): digest
        for name, digest in acquisition["sha256"].items()
    }
    for rel, digest in expected.items():
        if sha256(BRIDGE_REF / rel) != digest:
            raise RuntimeError("frozen bridge source drift: " + rel)
    return expected


def verify_v12_reference() -> Dict[str, str]:
    expected = {}
    for line in (V12_REF / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        path = V12_REF / name
        if sha256(path) != digest:
            raise RuntimeError("local V12 reference drift: " + name)
        expected[name] = digest
    return expected


def bridge_manifest(bridge_dir: Path, remote_bridge_dir: str) -> dict:
    files = []
    for path in sorted(p for p in bridge_dir.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(bridge_dir).as_posix()
        files.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": 1, "root": remote_bridge_dir, "files": files}


def files_hashes(root: Path, rels: Iterable[str]) -> Dict[str, str]:
    return {rel: sha256(root / rel) for rel in sorted(rels)}


def import_runner(runner_path: Path):
    spec = importlib.util.spec_from_file_location("patched_run_pct_scan_building", str(runner_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def make_route_artifact(pilot: dict) -> dict:
    start = [float(v) for v in pilot["spawn_ground_xyz_m"]]
    points = [start, list(start)]
    geometry_sha = hashlib.sha256(
        json.dumps(points, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "route_id": "stand_probe_spawn_metadata",
        "semantics": "terrain_ground_xyz_m",
        "body_height_applied": False,
        "points_xyz_m": points,
        "geometry_sha256": geometry_sha,
        "statistics": {"arc_length_xy_m": 0.0},
        "note": (
            "Stand-only metadata route for runner spawn/legacy metrics. In "
            "external-goal mode this is not a commanded target."
        ),
    }


def make_bridge_config(path: Path, telemetry_port: int, command_port: int) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            /**:
              ros__parameters:
                telemetry_host: 127.0.0.1
                telemetry_port: {telemetry_port}
                command_host: 127.0.0.1
                command_port: {command_port}
                connect_timeout_seconds: 1.0
                reconnect_delay_seconds: 0.2
                command_rate_hz: 50.0
                source_command_timeout_seconds: 0.25
                use_sim_time: false
                publish_clock: true
                clock_topic: /clock
                require_dual_cloud_sensor_frame: true
                max_body_state_age_seconds: 0.05
                require_complete_body_state: true
                body_state_identity_topic: /quad_0/body_state_identity
                trial_fault_topic: /quad_0/trial_fault
                require_fresh_simulation_feedback: true
                max_simulation_stall_seconds: 0.25
                publish_twist_validity: true
                max_vx: 0.30
                max_vy: 0.30
                max_wz: 0.8
                max_horizontal_command_norm: 0.30
                world_frame: world
                base_frame: base
                sensor_frame: lidar
                body_pose_topic: /quad_0/body_pose
                sensor_pose_topic: /quad_0/lidar_pose
                cloud_topic: /quad_0/cloud
                raw_cloud_topic: /quad_0/cloud_raw
                cmd_vel_topic: /quad_0/cmd_vel
            """
        ),
        encoding="utf-8",
    )


def build_runner_argv(args, remote_run: str, external_run_id: str) -> List[str]:
    return [
        "--scene",
        remote_run + "/inputs/building.usda",
        "--runtime",
        args.remote_v12_runtime,
        "--checkpoint",
        args.remote_checkpoint,
        "--route-artifact",
        remote_run + "/inputs/stand_route_artifact.json",
        "--scope",
        remote_run + "/inputs/stand_scope.json",
        "--execution-manifest",
        remote_run + "/inputs/execution_manifest.json",
        "--output",
        remote_run + "/artifacts/runner_output",
        "--case",
        "stand_probe",
        "--duration-seconds",
        "8.0",
        "--telemetry-host",
        "127.0.0.1",
        "--telemetry-port",
        str(args.telemetry_port),
        "--command-host",
        "127.0.0.1",
        "--command-port",
        str(args.command_port),
        "--max-vx",
        "0.30",
        "--max-vy",
        "0.30",
        "--max-wz",
        "0.8",
        "--max-horizontal-norm",
        "0.30",
        "--speed-profile",
        "conservative_0p3",
        "--contact-policy",
        "native_v12",
        "--unfiltered-planner-cloud",
        "--goal-tolerance-m",
        "0.25",
        "--terminal-window-seconds",
        "2.0",
        "--terminal-command-norm",
        "0.01",
        "--terminal-speed-mps",
        "0.10",
        "--terminal-yaw-rate-radps",
        "0.15",
        "--connection-ready-timeout-seconds",
        "120.0",
        "--max-wall-seconds",
        "600.0",
        "--video-fps",
        "12.5",
        "--camera-capture-stride",
        "4",
        "--complete-body-state",
        "--priority-telemetry",
        "--async-recording",
        "--freeze-gc",
        "--external-goal-mode",
        "--external-run-id",
        external_run_id,
        "--external-control-dir",
        remote_run + "/artifacts/external_episode",
        "--external-finish-stillness-seconds",
        "1.0",
        "--external-status-freshness-seconds",
        "2.0",
        "--seed",
        "42",
        "--device",
        "cuda:0",
    ]


def make_scope(
    runner_module,
    runner_argv: List[str],
    execution_manifest_sha: str,
    patched_runner_sha: str,
    pilot: dict,
    baseline_scope: dict,
) -> dict:
    parsed = runner_module.build_parser().parse_args(runner_argv)
    execution_configuration = runner_module.execution_configuration(parsed)
    spawn = [float(v) for v in pilot["spawn_ground_xyz_m"]]
    return {
        "schema_version": 1,
        "revision": "p2b-stand-only-runner-qualification-r1",
        "profile": "diagnostic_simulator_truth_known_map_stand_only",
        "execution_source_sha256": patched_runner_sha,
        "execution_manifest_sha256": execution_manifest_sha,
        "execution_configuration": execution_configuration,
        "frozen_assets": baseline_scope["frozen_assets"],
        "platform_segment": {
            "start_ground_xyz_m": spawn,
            "goal_ground_xyz_m": spawn,
            "nominal_body_height_m": float(pilot["nominal_body_height_m"]),
            "start_tangent_yaw_radians": float(pilot["spawn_yaw_rad"]),
            "semantics": "terrain_ground_xyz_m",
            "arc_length_xy_m": 0.0,
            "geometry_sha256": hashlib.sha256(
                json.dumps(spawn, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        },
        "resource_ceiling": {"simulation_seconds": 8.0, "wall_seconds": 600.0},
        "ros_domain_id": 94,
        "tcp_ports": {"telemetry": 46240, "command": 46241},
        "claim": (
            "Stand-only qualification of patched runner plus real Foxy bridge "
            "transport. No SCAN, no PCT motion command publisher, no navigation."
        ),
    }


def remote_worker_source() -> str:
    return r'''#!/usr/bin/env python3
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
                if snapshot.get("run_id") == run_root.name and float(snapshot.get("sim_time_s", 0.0)) >= 2.0:
                    break
            time.sleep(0.05)
        else:
            raise RuntimeError("current_command.json did not reach 2 sim seconds")
        finish = {
            "schema_version": 1,
            "run_id": run_root.name,
            "request_id": "stand-finish-" + run_root.name,
            "observed_run_epoch_ns": int(last_snapshot["run_epoch_ns"]),
            "requested_at_monotonic_ns": time.monotonic_ns(),
            "backend_terminal_status": "FINISHED",
            "note": "stand-only qualification finish after >=2 sim seconds",
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
        }
        if summary.get("status") != "EXTERNAL_EPISODE_FINISHED":
            raise RuntimeError("unexpected summary status: " + str(summary.get("status")))
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
'''


def package_manifest(run_dir: Path) -> dict:
    files = []
    for rel in [
        "inputs/building.usda",
        "inputs/pilot.json",
        "inputs/input_manifest.json",
        "inputs/stand_route_artifact.json",
        "inputs/stand_scope.json",
        "inputs/execution_manifest.json",
        "config/foxy_bridge_stand.yaml",
        "remote_worker.py",
        "source_env_hashes.json",
    ]:
        path = run_dir / rel
        files.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": 1, "root": str(run_dir), "files": files}


def prepare(args) -> Tuple[Path, dict]:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("stand_%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", run_id):
        raise ValueError("run_id must be filesystem and shell friendly")
    local_run = Path(args.local_runs_root) / run_id
    if local_run.exists():
        raise FileExistsError("local run already exists: " + str(local_run))
    remote_run = args.remote_root.rstrip("/") + "/" + run_id

    verify_input_manifest()
    bridge_expected = verify_bridge_source()
    v12_expected = verify_v12_reference()
    pilot = json.loads((P2B / "inputs/pilot.json").read_text(encoding="utf-8"))
    baseline_scope = json.loads(
        (P2B / "baseline_config/native_nominal_scope.json").read_text(encoding="utf-8")
    )

    (local_run / "inputs").mkdir(parents=True)
    (local_run / "config").mkdir()
    (local_run / "artifacts").mkdir()
    shutil.copy2(P2B / "inputs/building.usda", local_run / "inputs/building.usda")
    shutil.copy2(P2B / "inputs/pilot.json", local_run / "inputs/pilot.json")
    shutil.copy2(P2B / "input_manifest.json", local_run / "inputs/input_manifest.json")
    copytree_clean(BRIDGE_REF, local_run / "bridge")

    materializer = load_materializer()
    patched_runner = local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py"
    materializer.main([
        "--output",
        str(patched_runner),
        "--patch",
        str(local_run / "runner_external_episode.patch"),
        "--hashes",
        str(local_run / "runner_source_hashes.json"),
    ])
    patched_runner_sha = sha256(patched_runner)

    execution_manifest = bridge_manifest(local_run / "bridge", remote_run + "/bridge")
    write_json(local_run / "inputs/execution_manifest.json", execution_manifest)
    execution_manifest_sha = sha256(local_run / "inputs/execution_manifest.json")

    route = make_route_artifact(pilot)
    write_json(local_run / "inputs/stand_route_artifact.json", route)
    make_bridge_config(local_run / "config/foxy_bridge_stand.yaml", args.telemetry_port, args.command_port)

    runner_argv = build_runner_argv(args, remote_run, run_id)
    runner_module = import_runner(patched_runner)
    scope = make_scope(
        runner_module,
        runner_argv,
        execution_manifest_sha,
        patched_runner_sha,
        pilot,
        baseline_scope,
    )
    write_json(local_run / "inputs/stand_scope.json", scope)

    worker = remote_worker_source()
    worker_path = local_run / "remote_worker.py"
    worker_path.write_text(worker, encoding="utf-8")
    os.chmod(worker_path, 0o755)

    v12_runtime_expected = {
        rel.removeprefix("source/v12_runtime/"): digest
        for rel, digest in v12_expected.items()
        if rel.startswith("source/v12_runtime/")
    }
    source_hashes = {
        "bridge_reference_expected": bridge_expected,
        "bridge_materialized": {
            rel: sha256(local_run / "bridge" / rel)
            for rel in bridge_expected
            if (local_run / "bridge" / rel).exists()
        },
        "patched_runner_sha256": patched_runner_sha,
        "execution_manifest_sha256": execution_manifest_sha,
        "input_manifest_sha256": sha256(P2B / "input_manifest.json"),
        "pilot_sha256": sha256(P2B / "inputs/pilot.json"),
        "v12_local_reference_file_count": len(v12_expected),
        "v12_runtime_expected": v12_runtime_expected,
        "v12_runtime_expected_file_count": len(v12_runtime_expected),
        "v12_checkpoint_sha256": sha256(V12_REF / "source/checkpoint/model_149999.pt"),
        "foxy_image_id": FOXY_IMAGE_ID,
    }
    write_json(local_run / "source_env_hashes.json", source_hashes)

    manifest = package_manifest(local_run)
    write_json(local_run / "inputs/package_manifest.json", manifest)

    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", args.host]
    runner_argv_json = json.dumps(runner_argv, separators=(",", ":"))
    commands = {
        "remote_run": remote_run,
        "sync_whitelist": [
            "bridge/",
            "inputs/",
            "config/",
            "remote_worker.py",
            "source_env_hashes.json",
        ],
        "mkdir": ssh + [
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            f"p=Path({remote_run!r})\n"
            "assert not p.exists(), p\n"
            "p.mkdir(parents=True)\n"
            "PY"
        ],
        "sync": [
            "rsync",
            "-a",
            "--delete",
            "--include=/bridge/***",
            "--include=/inputs/***",
            "--include=/config/***",
            "--include=/remote_worker.py",
            "--include=/source_env_hashes.json",
            "--exclude=*",
            str(local_run) + "/",
            f"{args.host}:{remote_run}/",
        ],
        "run": ssh + [
            shlex.join([
                "python3",
                remote_run + "/remote_worker.py",
                "--run-root",
                remote_run,
                "--foxy-image-id",
                FOXY_IMAGE_ID,
                "--remote-v12-runtime",
                args.remote_v12_runtime,
                "--remote-checkpoint",
                args.remote_checkpoint,
                "--runner-argv-json",
                runner_argv_json,
                "--ros-domain-id",
                str(args.ros_domain_id),
            ])
        ],
        "collect": [
            "rsync",
            "-a",
            f"{args.host}:{remote_run}/artifacts/",
            str(local_run / "returned_artifacts") + "/",
        ],
    }
    write_json(local_run / "commands.json", commands)
    write_json(local_run / "run_request.json", {
        "schema_version": 1,
        "run_id": run_id,
        "local_run": str(local_run),
        "remote_run": remote_run,
        "default_execute": False,
        "case": "stand_probe",
        "contact_policy": "native_v12",
        "duration_seconds": 8.0,
        "max_wall_seconds": 600.0,
        "telemetry_port": args.telemetry_port,
        "command_port": args.command_port,
        "ros_domain_id": args.ros_domain_id,
        "claim_boundary": (
            "If executed and passed, this qualifies patched runner + real Foxy "
            "bridge stand-only physics/transport. It is not PCT/SCAN navigation."
        ),
    })
    return local_run, commands


def run_command(label: str, command: List[str], log_path: Path, timeout: int = 1800) -> None:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=timeout)
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}: {result.stdout[-3000:]}")


def load_prepared_run(args) -> Tuple[Path, dict]:
    run_id = args.run_id
    if not run_id:
        raise ValueError("--execute with an existing package requires --run-id")
    local_run = Path(args.local_runs_root) / run_id
    if not local_run.exists():
        raise FileNotFoundError("prepared local run does not exist: " + str(local_run))
    manifest = json.loads((local_run / "inputs/package_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = local_run / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError("prepared package hash mismatch: " + entry["path"])
    execution_manifest = json.loads((local_run / "inputs/execution_manifest.json").read_text(encoding="utf-8"))
    for entry in execution_manifest["files"]:
        path = local_run / "bridge" / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError("prepared bridge hash mismatch: " + entry["path"])
    commands = json.loads((local_run / "commands.json").read_text(encoding="utf-8"))
    return local_run, commands


def verify_returned_artifacts(local_run: Path) -> dict:
    returned = local_run / "returned_artifacts"
    expected = json.loads((returned / "artifact_hashes.json").read_text(encoding="utf-8"))
    actual = {
        path.relative_to(returned).as_posix(): sha256(path)
        for path in sorted(p for p in returned.rglob("*") if p.is_file())
        if path.relative_to(returned).as_posix() != "artifact_hashes.json"
    }
    expected_no_self = {k: v for k, v in expected.items() if k != "artifact_hashes.json"}
    return {
        "returned_hashes_match": actual == expected_no_self,
        "expected_count": len(expected_no_self),
        "actual_count": len(actual),
    }


def execute(local_run: Path, commands: dict) -> None:
    logs = local_run / "host_logs"
    logs.mkdir(exist_ok=True)
    remote_worker_started = False
    original_error = None
    collect_error = None
    verdict = {"remote_worker_started": False}
    try:
        run_command("mkdir", commands["mkdir"], logs / "00_mkdir.log")
        run_command("sync", commands["sync"], logs / "01_sync.log")
        remote_worker_started = True
        verdict["remote_worker_started"] = True
        run_command("run", commands["run"], logs / "02_remote_worker.log", timeout=1200)
    except Exception as exc:  # noqa: BLE001 - preserve failed run evidence path
        original_error = exc
        verdict["run_error"] = str(exc)
    finally:
        if remote_worker_started:
            try:
                run_command("collect", commands["collect"], logs / "03_collect.log")
                verdict.update(verify_returned_artifacts(local_run))
            except Exception as exc:  # noqa: BLE001 - preserve collect failure too
                collect_error = exc
                verdict["collect_error"] = str(exc)
    write_json(local_run / "return_verdict.json", verdict)
    if original_error is not None:
        if collect_error is not None:
            raise RuntimeError(
                "remote run failed and artifact collection also failed; "
                f"run_error={original_error}; collect_error={collect_error}"
            ) from original_error
        raise original_error
    if collect_error is not None:
        raise collect_error
    if not verdict.get("returned_hashes_match"):
        raise RuntimeError("returned artifact hashes do not match")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--host", default="gpu5070ti")
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--remote-v12-runtime", default=DEFAULT_REMOTE_V12)
    parser.add_argument("--remote-checkpoint", default=DEFAULT_REMOTE_CHECKPOINT)
    parser.add_argument("--local-runs-root", type=Path, default=HERE / "runs")
    parser.add_argument("--telemetry-port", type=int, default=46240)
    parser.add_argument("--command-port", type=int, default=46241)
    parser.add_argument("--ros-domain-id", type=int, default=94)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        local_run, commands = prepare(args)
    except FileExistsError:
        if not args.execute:
            raise
        local_run, commands = load_prepared_run(args)
    if args.execute:
        execute(local_run, commands)
    print(json.dumps({
        "local_run": str(local_run),
        "remote_run": commands["remote_run"],
        "execute": bool(args.execute),
        "commands_file": str(local_run / "commands.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
