#!/usr/bin/env python3
"""Bounded, read-only PCT tomogram publisher probe on gpu5070ti (CPU only)."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
OUT = Path(__file__).resolve().parent / "pct_tomogram_probe"
REMOTE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/qualification/pct_20260916T145741Z"
IMAGE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
MAP_SHA = "ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=False)
    local_map = P2B / "inputs/new_building.pickle"
    local_sha = hashlib.sha256(local_map.read_bytes()).hexdigest()
    if local_sha != MAP_SHA:
        raise RuntimeError("local Building map hash mismatch")
    remote_hash = subprocess.run(
        SSH + ["sha256sum " + shlex.quote(REMOTE + "/inputs/new_building.pickle")],
        capture_output=True, text=True, timeout=30,
    )
    (OUT / "remote_map_hash.log").write_text(remote_hash.stdout + remote_hash.stderr)
    if remote_hash.returncode or remote_hash.stdout.split()[0] != MAP_SHA:
        raise RuntimeError("remote Building map hash mismatch")

    inner = "\n".join((
        "set -e",
        "source /opt/ros/humble/setup.bash",
        "export PYTHONPATH=/probe/pct_runtime/python:${PYTHONPATH:-}",
        "export LD_LIBRARY_PATH=/probe/pct_runtime/lib:${LD_LIBRARY_PATH:-}",
        "timeout -s INT 20 python3 -m pct_planner.planner_node --ros-args "
        "-p rsg_root:=/probe/inputs -p scene_name:=custom "
        "-p tomogram_path:=/probe/inputs/new_building.pickle "
        "-p enable_interactive_markers:=false -p plan_on_startup:=false",
    ))
    podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host",
        "--name", "vla-pct-tomogram-probe-20260923",
        "-e", "ROS_DOMAIN_ID=188", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1",
        "-v", REMOTE + ":/probe:ro", IMAGE, "bash", "-lc", inner,
    ]
    command = SSH + [shlex.join(podman)]
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(command, capture_output=True, text=True, timeout=45)
    log = proc.stdout + proc.stderr
    (OUT / "publisher.log").write_text(log)
    match = re.search(r"Published (\d+) selectable tomogram cells on /pct_tomogram", log)
    result = {
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "exit_code": proc.returncode,
        "map_sha256": local_sha,
        "image_id": IMAGE,
        "published_cells": int(match.group(1)) if match else None,
        "passed": match is not None and int(match.group(1)) > 0,
        "claim": "PCT ROS publisher startup only; no SCAN subscriber, tracker, motion or Isaac",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "published_cells": result["published_cells"],
                      "exit_code": proc.returncode}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
