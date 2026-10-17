#!/usr/bin/env python3
"""Run a bounded, CPU-only ROS transport smoke of the PCT clock sidecar."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
HERE = Path(__file__).resolve().parent
SUFFIX = os.environ.get("VLA_PCT_PROBE_SUFFIX", "")
if SUFFIX and not re.fullmatch(r"_[a-z0-9_]+", SUFFIX):
    raise ValueError("VLA_PCT_PROBE_SUFFIX must be a safe suffix")
OUT = HERE / ("pct_sidecar_ros_probe" + SUFFIX)
REMOTE_SIDE = "/home/sun/vla_exec/2026-09-23_scan_reactive_stair/pct_sidecar_probe"
REMOTE_MAP = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/qualification/pct_20260916T145741Z"
IMAGE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
MAP_SHA = "ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def run(command, timeout: int):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    OUT.mkdir(exist_ok=False)
    files = [P2B / "reactive_stair/pct_sim_clock_core.py",
             P2B / "reactive_stair/pct_sim_clock_publisher.py",
             HERE / "pct_sidecar_ros_probe_driver.py"]
    if hashlib.sha256((P2B / "inputs/new_building.pickle").read_bytes()).hexdigest() != MAP_SHA:
        raise RuntimeError("local map identity changed")
    mkdir = run(SSH + ["mkdir -p " + shlex.quote(REMOTE_SIDE)], 30)
    if mkdir.returncode:
        raise RuntimeError(mkdir.stderr)
    sync = run(["rsync", "-a", *map(str, files), "gpu5070ti:" + REMOTE_SIDE + "/"], 45)
    if sync.returncode:
        raise RuntimeError(sync.stderr)
    expected = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    remote_names = " ".join(shlex.quote(REMOTE_SIDE + "/" + path.name) for path in files)
    hashes = run(SSH + ["sha256sum " + remote_names + " " +
                        shlex.quote(REMOTE_MAP + "/inputs/new_building.pickle")], 30)
    (OUT / "remote_hashes.log").write_text(hashes.stdout + hashes.stderr)
    if hashes.returncode:
        raise RuntimeError("remote source hash read failed")
    observed = {Path(line.split()[1]).name: line.split()[0]
                for line in hashes.stdout.strip().splitlines()}
    if any(observed.get(name) != value for name, value in expected.items()) or \
       observed.get("new_building.pickle") != MAP_SHA:
        raise RuntimeError("remote sidecar or map identity mismatch")

    inner = "\n".join((
        "source /opt/ros/humble/setup.bash",
        "export PYTHONPATH=/sidecar:${PYTHONPATH:-}",
        "python3 /sidecar/pct_sim_clock_publisher.py --ros-args "
        "-p map_path:=/map/inputs/new_building.pickle -p use_sim_time:=true "
        ">/tmp/vla_pct_sidecar.log 2>&1 &",
        "sidecar_pid=$!",
        "trap 'kill $sidecar_pid 2>/dev/null || true' EXIT",
        "timeout -s INT 25 python3 /sidecar/pct_sidecar_ros_probe_driver.py",
        "driver_status=$?",
        "cat /tmp/vla_pct_sidecar.log",
        "exit $driver_status",
    ))
    podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
        "--name", "vla-pct-sidecar-ros-probe-20260923",
        "-e", "ROS_DOMAIN_ID=191", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1",
        "-v", REMOTE_SIDE + ":/sidecar:ro", "-v", REMOTE_MAP + ":/map:ro",
        IMAGE, "bash", "-lc", inner,
    ]
    command = SSH + [shlex.join(podman)]
    process = run(command, 50)
    output = process.stdout + process.stderr
    (OUT / "transport.log").write_text(output)
    driver = next((json.loads(line) for line in output.splitlines()
                   if line.startswith('{"passed":')), None)
    passed = process.returncode == 0 and driver is not None and driver.get("passed") is True
    record = {
        "passed": passed,
        "exit_code": process.returncode,
        "driver": driver,
        "remote_source_hashes": observed,
        "image_id": IMAGE,
        "command": command,
        "claim": "ROS sidecar transport with synthetic clock only; no SCAN subscriber, LiDAR, pedestrian, or robot motion",
    }
    (OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": passed, "exit_code": process.returncode, "driver": driver}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
