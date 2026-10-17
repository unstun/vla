"""Own one local native-ROS container and one bounded Newton episode."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
BUILD = BASE / "builds/scan33_humble_amd64_v1"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    if shutil.disk_usage(BASE).free < 10 * 1024**3:
        raise RuntimeError("Less than10GiB free")
    for name in ("source_sha256.json", "install_sha256.json"):
        manifest = json.loads((BUILD / name).read_text())
        if any(hashlib.sha256((BUILD / p).read_bytes()).hexdigest() != sha for p, sha in manifest.items()):
            raise ValueError(f"Native identity mismatch: {name}")
    for record in json.loads((BASE / "setup/runtime_sources.json").read_text())["records"]:
        if hashlib.sha256((BASE / record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Archived runtime source changed")
    epoch = time.time_ns()
    (out / "episode_request.json").write_text(json.dumps({"run_epoch_ns": epoch, "probe": args.probe,
        "max_physics_s": 3 if args.probe else 35, "max_worker_wall_s": 500,
        "source_condition": "original Building/right official human/sensor rig; unchanged PCT/SCAN/controller/tracker",
        "sensor_condition": "qualified geometric emitter-owner exclusion, not RTX",
        "control_timing_condition": "original watchdogs; MAVROS-derived clock mapping",
        "sensor_preprocessing": "unfiltered planner cloud, as archived unfiltered_planner_cloud=true"}, indent=2) + "\n")
    for path in (BASE / "scripts").glob("*.py"):
        shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(BASE.parent / "2026-09-26_newton_macos_policy/scripts/lite3_newton.py", out / "executed_lite3_newton.py")
    sources = BASE / "runtime_sources"
    pythonpath = ":".join(str(sources / p) for p in ("backend_adapter", "backend_ros", "bridge", "pct_runtime/python"))
    script = "\n".join(["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
        "export PYTHONPATH=" + shlex.quote(pythonpath) + ':"${PYTHONPATH:-}"',
        "export LD_LIBRARY_PATH=" + shlex.quote(str(sources / "pct_runtime/lib")) + ':"${LD_LIBRARY_PATH:-}"',
        "exec python3 " + shlex.quote(str(BASE / "scripts/native_graph.py")) + " --output " + shlex.quote(str(out)), ""])
    (out / "native_inside.sh").write_text(script)
    name = "vla-newton-" + out.name.replace("_", "-")
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--name", name,
        "--memory=5g", "--cpus=4", "-e", "ROS_DOMAIN_ID=214", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1",
        "-p", "127.0.0.1:46202:46202", "-p", "127.0.0.1:8785:8785",
        "-v", str(PROJECT) + ":" + str(PROJECT) + ":ro", "-v", str(out) + ":" + str(out) + ":rw",
        "-v", str(BUILD) + ":/workspace:ro", "--entrypoint", "/bin/bash", IMAGE, str(out / "native_inside.sh")]
    (out / "container_command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "native_graph.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            worker = subprocess.run([sys.executable, str(BASE / "scripts/newton_episode.py")], timeout=500)
            worker.check_returncode()
        finally:
            cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=15)
            process.wait(timeout=10)
            (out / "container_cleanup.json").write_text(json.dumps({"exit_code": cleanup.returncode,
                  "stdout": cleanup.stdout, "stderr": cleanup.stderr}, indent=2) + "\n")


if __name__ == "__main__":
    main()
