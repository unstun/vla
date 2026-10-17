#!/usr/bin/env python3
"""Bounded CPU-only cross-container tracker transport with synthetic points."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
HERE = Path(__file__).resolve().parent
OUT = HERE / "synthetic_track_ros_probe"
REMOTE_SIDE = "/home/sun/vla_exec/2026-09-23_scan_reactive_stair/pct_sidecar_probe"
REMOTE_MAP = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/qualification/pct_20260916T145741Z"
REMOTE_SCAN = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_09"
HUMBLE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
FOXY = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def run(command, timeout):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    OUT.mkdir(exist_ok=False)
    build = json.loads((P2B / "builds/scan_09/build_result.json").read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise RuntimeError("scan_09 Foxy build identity not accepted")
    sources = [P2B / "reactive_stair/pct_sim_clock_core.py",
               P2B / "reactive_stair/pct_sim_clock_publisher.py",
               HERE / "synthetic_track_ros_probe_driver.py"]
    expected = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    sync = run(["rsync", "-a", *map(str, sources), "gpu5070ti:" + REMOTE_SIDE + "/"], 45)
    if sync.returncode:
        raise RuntimeError(sync.stderr)
    names = " ".join(shlex.quote(REMOTE_SIDE + "/" + path.name) for path in sources)
    hashes = run(SSH + ["sha256sum " + names], 30)
    (OUT / "remote_hashes.log").write_text(hashes.stdout + hashes.stderr)
    observed = {Path(line.split()[1]).name: line.split()[0]
                for line in hashes.stdout.strip().splitlines()}
    if hashes.returncode or observed != expected:
        raise RuntimeError("cross-container probe source gate failed")

    sidecar_inner = (
        "source /opt/ros/humble/setup.bash && "
        "export PYTHONPATH=/sidecar:${PYTHONPATH:-} && "
        "timeout -s INT 40 python3 /sidecar/pct_sim_clock_publisher.py --ros-args "
        "-p map_path:=/map/inputs/new_building.pickle -p use_sim_time:=true"
    )
    sidecar_podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
        "--name", "vla-scan09-synthetic-pct-20260923",
        "-e", "ROS_DOMAIN_ID=192", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1",
        "-v", REMOTE_SIDE + ":/sidecar:ro", "-v", REMOTE_MAP + ":/map:ro",
        HUMBLE, "bash", "-lc", sidecar_inner,
    ]
    sidecar_command = SSH + [shlex.join(sidecar_podman)]
    foxy_inner = "\n".join((
        "source /opt/ros/foxy/setup.bash",
        "source /workspace/install/setup.bash",
        "ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args "
        "-p use_sim_time:=true >/tmp/vla_scan09_tracker.log 2>&1 &",
        "tracker_pid=$!",
        "trap 'kill $tracker_pid 2>/dev/null || true' EXIT",
        "timeout -s INT 28 python3 /probe/synthetic_track_ros_probe_driver.py",
        "driver_status=$?",
        "cat /tmp/vla_scan09_tracker.log",
        "exit $driver_status",
    ))
    foxy_podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
        "--name", "vla-scan09-synthetic-track-20260923",
        "-e", "ROS_DOMAIN_ID=192", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", REMOTE_SIDE + ":/probe:ro", "-v", REMOTE_SCAN + ":/workspace:ro",
        FOXY, "bash", "-lc", foxy_inner,
    ]
    foxy_command = SSH + [shlex.join(foxy_podman)]
    with (OUT / "sidecar.log").open("w") as sidecar_log:
        sidecar = subprocess.Popen(sidecar_command, stdout=sidecar_log,
                                   stderr=subprocess.STDOUT)
        try:
            foxy = run(foxy_command, 55)
        finally:
            # The remote sidecar has its own timeout, but stop it immediately
            # after the bounded driver so no execution copy is left running.
            stop = run(SSH + ["podman stop --time 2 vla-scan09-synthetic-pct-20260923"], 15)
            (OUT / "cleanup.log").write_text(stop.stdout + stop.stderr)
            try:
                sidecar.wait(timeout=10)
            except subprocess.TimeoutExpired:
                sidecar.terminate()
                sidecar.wait(timeout=5)
    output = foxy.stdout + foxy.stderr
    (OUT / "tracker_transport.log").write_text(output)
    driver = next((json.loads(line) for line in output.splitlines()
                   if line.startswith('{"passed":')), None)
    passed = foxy.returncode == 0 and driver is not None and driver.get("passed") is True
    record = {
        "passed": passed,
        "exit_code": foxy.returncode,
        "driver": driver,
        "sidecar_command": sidecar_command,
        "foxy_command": foxy_command,
        "remote_source_hashes": observed,
        "claim": "Cross-container ROS transport of synthetic moving cluster only; no human identity, SCAN collision query, Isaac episode, or robot motion",
    }
    (OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": passed, "exit_code": foxy.returncode, "driver": driver}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
