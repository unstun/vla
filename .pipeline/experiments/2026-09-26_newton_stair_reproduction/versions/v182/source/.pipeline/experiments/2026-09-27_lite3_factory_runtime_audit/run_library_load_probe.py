"""Run the passive load probe in a bounded, device-free, network-free container."""

import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "library_load_check"
OUTPUT.mkdir(exist_ok=True)
IMAGE = "sha256:1c102582b40d5305e310788c79e963e4b6cde13aea2bc5db3b7c1800e821935d"
name = "vla-factory-library-load-" + str(os.getpid())
command = [
    "docker", "create", "--pull", "never", "--name", name,
    "--network", "none", "--read-only", "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges", "--memory", "512m",
    "--cpus", "1", "--pids-limit", "64",
    "--user", f"{os.getuid()}:{os.getgid()}",
    "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m", "--workdir", "/tmp",
    "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
    "--env", "MKL_NUM_THREADS=1",
    "--env", "LD_LIBRARY_PATH=/snapshot/deps:/snapshot/lib/ras_lib",
    "--mount", f"type=bind,src={ROOT / 'private_snapshot'},dst=/snapshot,readonly",
    "--mount", f"type=bind,src={ROOT / 'library_load_probe.py'},dst=/probe.py,readonly",
    "--entrypoint", "/usr/bin/python3", IMAGE, "/probe.py",
]
result = {"create_command": command, "image": IMAGE,
          "scope": "dynamic load and symbol resolution only; no algorithm call"}
created = False
started = time.monotonic()
try:
    creation = subprocess.run(command, check=True, text=True, capture_output=True, timeout=15)
    created = True
    result["container_id"] = creation.stdout.strip()
    try:
        run = subprocess.run(["docker", "start", "-a", name], capture_output=True,
                             text=True, timeout=30)
        result["timed_out"] = False
        result["exit_code"] = run.returncode
        (OUTPUT / "stdout.log").write_text(run.stdout)
        (OUTPUT / "stderr.log").write_text(run.stderr)
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
        subprocess.run(["docker", "kill", name], check=False, capture_output=True, timeout=10)
    inspected = subprocess.run(["docker", "inspect", name], check=True,
                               text=True, capture_output=True, timeout=10)
    detail = json.loads(inspected.stdout)[0]
    result["state"] = detail["State"]
    result["network_mode"] = detail["HostConfig"]["NetworkMode"]
    result["devices"] = detail["HostConfig"]["Devices"]
    result["read_only_rootfs"] = detail["HostConfig"]["ReadonlyRootfs"]
finally:
    if created:
        cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                                 text=True, timeout=10)
        result["cleanup_exit_code"] = cleanup.returncode
    result["wall_seconds"] = time.monotonic() - started
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "create_command"}, indent=2))
