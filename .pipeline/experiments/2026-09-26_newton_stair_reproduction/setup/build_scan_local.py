"""Bound the unchanged SCAN33 build inside the cached local ROS image."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE / "builds/scan33_humble_amd64_v1"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
NAME = "vla-newton-scan33-build-v1"


def main():
    if (WORKSPACE / "build_result.json").exists():
        raise FileExistsError("Build attempt already completed")
    if shutil.disk_usage(BASE).free < 10 * 1024**3:
        raise RuntimeError("Less than10GiB free")
    expected = json.loads((WORKSPACE / "source_sha256.json").read_text())
    actual = {name: hashlib.sha256((WORKSPACE / name).read_bytes()).hexdigest() for name in expected}
    if actual != expected:
        raise ValueError("Source identity mismatch")
    script = "\n".join([
        "set -e", "source /opt/ros/humble/setup.bash", "cd /workspace", "python3 --version", "g++ --version",
        "dpkg-query -W > package_versions.txt",
        "colcon build --base-paths src --executor sequential --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF", ""])
    (WORKSPACE / "build_inside.sh").write_text(script)
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
               "--name", NAME, "--memory=6g", "--cpus=3", "-e", "CMAKE_BUILD_PARALLEL_LEVEL=3",
               "-e", "MAKEFLAGS=-j3", "-v", str(WORKSPACE) + ":/workspace:rw",
               "--entrypoint", "/bin/bash", IMAGE, "/workspace/build_inside.sh"]
    result = {"command": command, "started_utc": datetime.now(timezone.utc).isoformat(),
              "deadline_s": 1200, "image": IMAGE, "passed": False}
    (WORKSPACE / "build_request.json").write_text(json.dumps(result, indent=2) + "\n")
    begin = time.monotonic()
    try:
        with (WORKSPACE / "build.log").open("w") as f:
            process = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=1200)
        result["exit_code"] = process.returncode
        after = {name: hashlib.sha256((WORKSPACE / name).read_bytes()).hexdigest() for name in expected}
        result["source_unchanged"] = after == expected
        result["passed"] = process.returncode == 0 and after == expected
        if result["passed"]:
            installed = {str(p.relative_to(WORKSPACE)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (WORKSPACE / "install").rglob("*") if p.is_file()}
            (WORKSPACE / "install_sha256.json").write_text(json.dumps(installed, indent=2) + "\n")
        process.check_returncode()
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
        raise
    finally:
        cleanup = subprocess.run(["docker", "rm", "-f", NAME], capture_output=True, text=True, timeout=20)
        result["cleanup"] = {"exit_code": cleanup.returncode, "stdout": cleanup.stdout, "stderr": cleanup.stderr}
        result["wall_s"] = time.monotonic() - begin
        (WORKSPACE / "build_result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
