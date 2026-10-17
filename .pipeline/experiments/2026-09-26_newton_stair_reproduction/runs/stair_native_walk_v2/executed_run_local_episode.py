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
import tarfile
import time

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
BUILD = BASE / "builds/scan33_humble_amd64_v1"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def return_linux_state(name, out):
    """Read the mounted tmpfs, using Docker's documented exec/tar method."""
    returned = out / "returned_external_episode"
    returned.mkdir(exist_ok=True)
    archive = out / "linux_external_episode.tar"
    receipt = {"method": "docker exec tar", "verified": False,
        "reference": "https://docs.docker.com/reference/cli/docker/container/cp/#corner-cases"}
    try:
        with archive.open("wb") as stream:
            copied = subprocess.run(["docker", "exec", name, "tar", "-C",
                str(out / "artifacts/external_episode"), "-cf", "-", "."],
                stdout=stream, stderr=subprocess.PIPE, timeout=15)
        receipt.update(exit_code=copied.returncode, stderr=copied.stderr.decode(errors="replace"))
        copied.check_returncode()
        with tarfile.open(archive) as bundle:
            for member in bundle:
                if member.isdir():
                    continue
                target = returned / member.name
                if (not member.isfile() or member.size > 8 * 1024**2
                        or not target.resolve().is_relative_to(returned.resolve())):
                    raise ValueError("Unexpected state archive member: " + member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source:
                    target.write_bytes(source.read())
        hashes = {str(p.relative_to(returned)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in returned.rglob("*") if p.is_file()}
        last_ack = None
        with (out / "applied_sent.jsonl").open() as sent:
            for line in sent:
                last_ack = json.loads(line)["ack"]
        receipt.update(files_sha256=hashes, last_ack=last_ack,
                       archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        if last_ack is None or hashes.get("current_command.json") != last_ack["sha256"]:
            raise ValueError("Returned Linux state does not match the last acknowledged bytes")
        receipt["verified"] = True
    except Exception as error:
        receipt["error"] = repr(error)
    (out / "state_copyback.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt["verified"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--backend-executor", choices=("multi", "single"), default="multi")
    parser.add_argument("--applied-transport", choices=("shared", "zmq"), default="shared")
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
    (out / "artifacts/external_episode").mkdir(parents=True)
    (out / "inputs").mkdir()
    for name in ("pilot.json", "stair_scenario.json"):
        shutil.copyfile(BASE / "inputs" / name, out / "inputs" / name)
    (out / "episode_request.json").write_text(json.dumps({"run_epoch_ns": epoch, "probe": args.probe,
        "backend_executor": args.backend_executor,
        "applied_transport": args.applied_transport,
        "max_physics_s": 3 if args.probe else 35, "max_worker_wall_s": 500,
        "source_condition": "original Building/right official human/sensor rig; unchanged PCT/SCAN/controller/tracker",
        "sensor_condition": "qualified geometric emitter-owner exclusion, not RTX",
        "control_timing_condition": "original watchdogs; MAVROS-derived clock mapping",
        "sensor_preprocessing": "unfiltered planner cloud, as archived unfiltered_planner_cloud=true"}, indent=2) + "\n")
    for path in (BASE / "scripts").glob("*.py"):
        shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(BASE.parent / "2026-09-26_newton_macos_policy/scripts/lite3_newton.py", out / "executed_lite3_newton.py")
    sources = BASE / "runtime_sources"
    pythonpath = str(BASE / "runtime/foreground_py310") + ":" + ":".join(
        str(sources / p) for p in ("backend_adapter", "backend_ros", "bridge", "pct_runtime/python"))
    script = "\n".join(["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
        "export PYTHONPATH=" + shlex.quote(pythonpath) + ':"${PYTHONPATH:-}"',
        "export LD_LIBRARY_PATH=" + shlex.quote(str(sources / "pct_runtime/lib")) + ':"${LD_LIBRARY_PATH:-}"',
        "exec python3 " + shlex.quote(str(BASE / "scripts/native_graph.py")) + " --output " + shlex.quote(str(out)), ""])
    (out / "native_inside.sh").write_text(script)
    name = "vla-newton-" + out.name.replace("_", "-")
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--name", name,
        "--memory=5g", "--cpus=4", "-e", "ROS_DOMAIN_ID=214", "-e", "ROS_LOCALHOST_ONLY=1",
        "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1",
        "-p", "127.0.0.1:46202:46202",
        "-v", str(PROJECT) + ":" + str(PROJECT) + ":ro", "-v", str(out) + ":" + str(out) + ":rw",
        "-v", str(BUILD) + ":/workspace:ro", "--entrypoint", "/bin/bash", IMAGE, str(out / "native_inside.sh")]
    if args.applied_transport == "zmq":
        image_index = command.index("--entrypoint")
        command[image_index:image_index] = ["-p", "127.0.0.1:46203:46203", "--tmpfs",
            str(out / "artifacts/external_episode") + ":rw,size=8m"]
    (out / "container_command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "native_graph.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            worker = subprocess.run([sys.executable, str(BASE / "scripts/newton_episode.py")], timeout=500)
            worker.check_returncode()
        finally:
            copyback_ok = True
            if args.applied_transport == "zmq":
                copyback_ok = return_linux_state(name, out)
            subprocess.run(["docker", "stop", "--time", "5", name], capture_output=True, text=True, timeout=10)
            cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=15)
            process.wait(timeout=10)
            (out / "container_cleanup.json").write_text(json.dumps({"exit_code": cleanup.returncode,
                  "stdout": cleanup.stdout, "stderr": cleanup.stderr}, indent=2) + "\n")
            if not copyback_ok:
                raise RuntimeError("Linux state copyback failed verification; see state_copyback.json")


if __name__ == "__main__":
    main()
