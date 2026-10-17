#!/usr/bin/env python3
"""Attach the 2026-09-16 GPU RViz observer to a livox_mid360 stand_probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
QUALIFY_SCRIPT = EXPERIMENT / "isaac_runner/qualify_stand_runner.py"
POINTCLOUD_DISPLAY = EXPERIMENT / "pointcloud_display"
P2B_PLANNER = EXPERIMENT / "p2b_execution/baseline_config/planner.yaml"
SCAN_IDENTITY = EXPERIMENT / "p2b_execution/builds/scan_04/install_identity.json"
RVIZ_IMAGE_ID = "980cec478c0659eaecc87b5bb79685bc3399135a2ce4033d5e815defe4478ed2"
DEFAULT_DURATION_SECONDS = 20.0
DEFAULT_FINISH_AFTER_SIM_SECONDS = 16.0
OBSERVER_EXTRA = (
    "aabb_hit_marker.py",
    "occupancy_audit.py",
    "scan_occupancy.py",
    "pointcloud.rviz",
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_qualify():
    spec = importlib.util.spec_from_file_location("qualify_stand_runner", QUALIFY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("observer insertion anchor is not unique: " + repr(old))
    return text.replace(old, new, 1)


def add_observer_hooks(text):
    text = replace_once(
        text,
        "import time\n",
        "import time\nfrom observer.session import DisplayProbe\n"
        "from observer.scan_occupancy import ScanOccupancy\n",
    )
    text = replace_once(
        text,
        "    run_root = Path(args.run_root)\n    artifacts = run_root / \"artifacts\"\n",
        "    run_root = Path(args.run_root)\n"
        "    probe = DisplayProbe(run_root)\n"
        "    scan_cfg = json.loads((run_root / \"observer/config.json\").read_text())\n"
        "    scan_occ = ScanOccupancy(\n"
        "        run_root, args.foxy_image_id, args.ros_domain_id,\n"
        "        scan_cfg[\"scan_workspace\"])\n"
        "    artifacts = run_root / \"artifacts\"\n",
    )
    text = replace_once(
        text,
        "        ensure_tcp_port_free(runner_arg_value(runner_argv, \"--command-port\"))\n\n"
        "        bridge_cmd = [\n",
        "        ensure_tcp_port_free(runner_arg_value(runner_argv, \"--command-port\"))\n\n"
        "        probe.start()\n\n"
        "        bridge_cmd = [\n",
    )
    text = replace_once(
        text,
        "        if bridge_proc.poll() is not None:\n"
        "            raise RuntimeError(\"Foxy bridge exited early\")\n",
        "        if bridge_proc.poll() is not None:\n"
        "            raise RuntimeError(\"Foxy bridge exited early\")\n"
        "        scan_occ.start()\n"
        "        time.sleep(2.0)\n"
        "        if scan_occ.exited_early():\n"
        "            raise RuntimeError(\"SCAN occupancy helper exited early\")\n"
        "        result[\"scan_started\"] = True\n",
    )
    # 09-16 GPU RViz received /quad_0/cloud_raw only when the Foxy bridge also
    # used --ipc=host. Stand qualify omits it; FastDDS SHM then never delivers.
    text = replace_once(
        text,
        '            "podman", "run", "--rm", "--pull=never", "--network=host",\n'
        '            "--name", container_name,\n',
        '            "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",\n'
        '            "--name", container_name,\n',
    )
    text = replace_once(
        text,
        "        runner_proc = subprocess.Popen(runner_cmd, stdout=runner_log, stderr=subprocess.STDOUT,\n"
        "                                       env=os.environ.copy(), start_new_session=True)\n",
        "        runner_proc = subprocess.Popen(runner_cmd, stdout=runner_log, stderr=subprocess.STDOUT,\n"
        "                                       env=os.environ.copy(), start_new_session=True)\n"
        "        probe.record_process(\"isaac\", runner_proc.pid)\n",
    )
    text = replace_once(
        text,
        "    finally:\n        if runner_proc is not None and runner_proc.poll() is None:\n",
        "    finally:\n        try:\n            result[\"observer\"] = probe.stop()\n"
        "        except BaseException as observer_error:\n"
        "            result[\"observer_error\"] = str(observer_error)\n"
        "        try:\n            result[\"scan_occupancy\"] = scan_occ.stop()\n"
        "        except BaseException as scan_error:\n"
        "            result[\"scan_occupancy_error\"] = str(scan_error)\n"
        "        if runner_proc is not None and runner_proc.poll() is None:\n",
    )
    compile(text, "remote_worker_with_observer.py", "exec")
    return text


def patch_observer_session(text):
    text = replace_once(
        text,
        "python3 /observer/cloud_audit.py --output /observer-out/cloud_receipts.jsonl &\n"
        "exec rviz2 --ogre-log -d ",
        "python3 /observer/cloud_audit.py --output /observer-out/cloud_receipts.jsonl &\n"
        "python3 /observer/aabb_hit_marker.py --output /observer-out/aabb_hits.jsonl "
        "--setup /run-artifacts/runner_output/unmapped_box_setup.json &\n"
        "python3 /observer/occupancy_audit.py --output /observer-out/occupancy_receipts.jsonl "
        "--setup /run-artifacts/runner_output/unmapped_box_setup.json &\n"
        "exec rviz2 --ogre-log -d ",
    )
    text = replace_once(
        text,
        "'-v', str(self.source) + ':/observer:ro',\n"
        "                   '-v', str(self.output) + ':/observer-out:rw']",
        "'-v', str(self.source) + ':/observer:ro',\n"
        "                   '-v', str(self.output) + ':/observer-out:rw',\n"
        "                   '-v', str(self.root / 'artifacts') + ':/run-artifacts:ro',\n"
        "                   '-v', str(self.root / 'inputs/sensor_rig') + ':/robot:ro']",
    )
    compile(text, "observer_session_with_aabb.py", "exec")
    return text


def attach_observer(local_run, commands, run_id, mode="rviz-gpu"):
    shutil.copytree(
        POINTCLOUD_DISPLAY / "observer",
        local_run / "observer",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in OBSERVER_EXTRA:
        shutil.copy2(HERE / "rviz_observer" / name, local_run / "observer" / name)
    shutil.copy2(P2B_PLANNER, local_run / "config/planner.yaml")
    scan_identity = json.loads(SCAN_IDENTITY.read_text())
    scan_workspace = scan_identity["remote_workspace"]
    write_json(local_run / "inputs/scan_04_identity.json", {
        "remote_workspace": scan_workspace,
        "image_id": scan_identity["image_id"],
        "source_file_count": scan_identity["source_file_count"],
        "source_matches": scan_identity["source_matches"],
        "planner_yaml_sha256": sha256(P2B_PLANNER),
        "planner_ground_height": 0.0,
    })
    session_path = local_run / "observer/session.py"
    session_path.write_text(patch_observer_session(session_path.read_text()))
    gpu_display = mode == "rviz-gpu"
    rviz_config_file = "pointcloud_" + run_id + ".rviz"
    shutil.copyfile(local_run / "observer/pointcloud.rviz", local_run / "observer" / rviz_config_file)
    config = {
        "mode": mode,
        "rviz_image_id": RVIZ_IMAGE_ID,
        "display": ":0",
        "xauthority": "/run/user/1000/gdm/Xauthority",
        "renderer_requested": (
            "NVIDIA hardware OpenGL; require NVIDIA RTX 5070 Ti in Ogre.log"
            if gpu_display else
            "Mesa software, LIBGL_ALWAYS_SOFTWARE=1; verify Ogre.log"
        ),
        "capture_encoder": "h264_nvenc" if gpu_display else "libx264",
        "gpu_display": gpu_display,
        "rviz_config_file": rviz_config_file,
        "viewer_cpu_limit_cores": 2,
        "viewer_memory_limit_bytes": 2147483648,
        "draw_rate_hz": 10,
        "decay_seconds": 0,
        "pointcloud_topic": "/quad_0/cloud_raw",
        "pointcloud_qos": "BEST_EFFORT KEEP_LAST depth 1",
        "capture_scope": "own RViz window only",
        "capture_time_basis": "wall time",
        "capture_in_display_condition_only": True,
        "aabb_hit_topic": "/review/unmapped_box_hits",
        "occupancy_topic": "/grid_map/occupancy",
        "scan_workspace": scan_workspace,
        "scan_image_id": scan_identity["image_id"],
        "robot_description_topic": "/robot_description",
        "run_id": run_id,
    }
    if gpu_display:
        config["nvidia_runtime"] = json.loads((POINTCLOUD_DISPLAY / "nvidia_runtime.json").read_text())
    write_json(local_run / "observer/config.json", config)
    original = (local_run / "remote_worker.py").read_text()
    updated = add_observer_hooks(original)
    (local_run / "remote_worker.py").write_text(updated)
    source = json.loads((local_run / "source_env_hashes.json").read_text())
    source["pointcloud_observer"] = {
        "qualify_packager_sha256": sha256(QUALIFY_SCRIPT),
        "wrapper_sha256": sha256(Path(__file__)),
        "original_remote_worker_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "observed_remote_worker_sha256": hashlib.sha256(updated.encode()).hexdigest(),
        "config": config,
        "source": {
            str(path.relative_to(local_run)): sha256(path)
            for path in (local_run / "observer").rglob("*") if path.is_file()
        },
    }
    write_json(local_run / "source_env_hashes.json", source)
    manifest = json.loads((local_run / "inputs/package_manifest.json").read_text())
    paths = {entry["path"] for entry in manifest["files"]}
    paths.update(str(path.relative_to(local_run)) for path in (local_run / "observer").rglob("*") if path.is_file())
    paths.add("config/planner.yaml")
    paths.add("inputs/scan_04_identity.json")
    manifest["files"] = [
        {"path": path, "sha256": sha256(local_run / path), "bytes": (local_run / path).stat().st_size}
        for path in sorted(paths)
    ]
    write_json(local_run / "inputs/package_manifest.json", manifest)
    commands["sync_whitelist"].append("observer/")
    commands["sync"].insert(commands["sync"].index("--exclude=*"), "--include=/observer/***")
    write_json(local_run / "commands.json", commands)
    request = json.loads((local_run / "run_request.json").read_text())
    request["pointcloud_display_mode"] = mode
    request["claim_boundary"] = (
        request.get("claim_boundary", "")
        + " GPU RViz records the Lite3 URDF mesh, live /quad_0/cloud_raw, and "
        "scan_04 /grid_map/occupancy while the dog stands. Occupancy visualization "
        "is not navigation success, not a physical MID-360, and does not amend 09-20 AC1."
    )
    write_json(local_run / "run_request.json", request)
    return local_run, commands


def prepare(mode, run_id, qualify, extra_argv=None):
    args = qualify.build_parser().parse_args([
        "--run-id", run_id,
        "--local-runs-root", str(HERE / "runs"),
        "--unmapped-box", "lidar",
        "--lidar-pattern-mode", "livox_mid360",
        "--stance-hold", "auto",
        "--duration-seconds", str(DEFAULT_DURATION_SECONDS),
        "--finish-after-sim-seconds", str(DEFAULT_FINISH_AFTER_SIM_SECONDS),
        *(extra_argv or []),
    ])
    local_run, commands = qualify.prepare(args)
    return attach_observer(local_run, commands, run_id, mode=mode), args


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["off", "rviz", "rviz-gpu"], default="rviz-gpu")
    parser.add_argument("--run-id")
    parser.add_argument("--execute", action="store_true")
    options = parser.parse_args(argv)
    run_id = options.run_id or datetime.now(timezone.utc).strftime(
        "stand_%Y%m%dT%H%M%SZ_livox_" + options.mode.replace("-", "_")
    )
    qualify = load_qualify()
    (local_run, commands), args = prepare(options.mode, run_id, qualify)
    if options.execute:
        args.execute = True
        qualify.check_prepared_request(args, local_run)
        qualify.execute(local_run, commands)
    print(json.dumps({
        "local_run": str(local_run),
        "remote_run": commands["remote_run"],
        "execute": bool(options.execute),
        "mode": options.mode,
        "commands_file": str(local_run / "commands.json"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
