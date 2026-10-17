#!/usr/bin/env python3
"""Bounded CPU-only startup check of the locally recorded scan_07 install."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import subprocess


ROOT = Path(__file__).resolve().parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
OUT = Path(__file__).resolve().parent / "scan07_startup_probe"
REMOTE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_07"
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]


def main() -> int:
    build = json.loads((P2B / "builds/scan_07/build_result.json").read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise RuntimeError("scan_07 has no accepted Foxy build")
    identity_path = P2B / "builds/scan_07/install_identity.json"
    if not identity_path.exists():
        raise RuntimeError("scan_07 installed identity missing")
    OUT.mkdir(exist_ok=False)
    inner = (
        "source /opt/ros/foxy/setup.bash && "
        "source /workspace/install/setup.bash && "
        "timeout -s INT 10 ros2 run scan_planner scan_planner_node "
        "--ros-args --params-file /workspace/src/plan_manage/config/planner.yaml"
    )
    podman = [
        "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
        "--name", "vla-scan07-startup-probe-20260923",
        "-e", "ROS_DOMAIN_ID=189", "-e", "ROS_LOCALHOST_ONLY=1",
        "-v", REMOTE + ":/workspace:ro", IMAGE, "bash", "-lc", inner,
    ]
    command = SSH + [shlex.join(podman)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    output = result.stdout + result.stderr
    (OUT / "startup.log").write_text(output)
    passed = result.returncode == 124 and "Failed to initialize SCAN-Planner" not in output
    record = {
        "passed": passed,
        "exit_code": result.returncode,
        "command": command,
        "image_id": IMAGE,
        "local_install_identity_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "claim": "ROS process startup only; no PCT, LiDAR, tracks, planner route, or motion",
    }
    (OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": passed, "exit_code": result.returncode}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
