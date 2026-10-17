#!/usr/bin/env python3
"""Check the existing one-shot PCT publisher stamp with simulation time enabled."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess


OUT = Path(__file__).resolve().parent / "pct_zero_clock_probe"
REMOTE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/qualification/pct_20260916T145741Z"
IMAGE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    inner = "\n".join((
        "set -e",
        "source /opt/ros/humble/setup.bash",
        "export PYTHONPATH=/probe/pct_runtime/python:${PYTHONPATH:-}",
        "export LD_LIBRARY_PATH=/probe/pct_runtime/lib:${LD_LIBRARY_PATH:-}",
        "python3 -m pct_planner.planner_node --ros-args "
        "-p rsg_root:=/probe/inputs -p scene_name:=custom "
        "-p tomogram_path:=/probe/inputs/new_building.pickle "
        "-p enable_interactive_markers:=false -p plan_on_startup:=false "
        "-p use_sim_time:=true >/tmp/vla_pct_zero_clock_node.log 2>&1 &",
        "pct_pid=$!",
        "trap 'kill $pct_pid 2>/dev/null || true' EXIT",
        "set +e",
        "timeout 20 ros2 topic echo /pct_tomogram sensor_msgs/msg/PointCloud2 "
        "--once --field header --qos-durability transient_local",
        "echo topic_echo_exit=$?",
        "cat /tmp/vla_pct_zero_clock_node.log",
    ))
    podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
        "--name", "vla-pct-zero-clock-probe-20260923",
        "-e", "ROS_DOMAIN_ID=190", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1",
        "-v", REMOTE + ":/probe:ro", IMAGE, "bash", "-lc", inner,
    ]
    command = SSH + [shlex.join(podman)]
    process = subprocess.run(command, capture_output=True, text=True, timeout=55)
    output = process.stdout + process.stderr
    (OUT / "output.log").write_text(output)
    passed = process.returncode == 0 and "sec: 0" in output and \
        "Published 86775 selectable tomogram cells" in output
    record = {"passed": passed, "exit_code": process.returncode,
              "command": command, "observed_zero_sec": "sec: 0" in output,
              "claim": "One-shot PCT map has zero stamp when use_sim_time is true before the clock spins; no SCAN or motion"}
    (OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": passed, "exit_code": process.returncode,
                      "observed_zero_sec": record["observed_zero_sec"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
