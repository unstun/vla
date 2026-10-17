"""Bounded CPU-only native replay of a logging-only isolated planner copy."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
RI = HERE.parents[1]
BUILD = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/builds/scan19_audit_trace"
REMOTE = "/home/sun/vla_exec/2026-09-26_stair_cause_audit"
REMOTE_BUILD = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan19_audit_trace"
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
NAME = "vla-stair-cause-audit"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (HERE / "execution_result.json").exists() or (HERE / "replay_result").exists():
        raise FileExistsError("Audit already executed or partially returned")
    build = json.loads((BUILD / "build_result.json").read_text())
    if not build.get("passed") or not (BUILD / "install_identity.json").is_file():
        raise ValueError("Native build/install identity gate not complete")
    package = HERE / "remote_package"
    package.mkdir()
    shutil.copy2(RI / "replay_stair_inputs.py", package / "replay_stair_inputs.py")
    shutil.copytree(HERE / "search_inputs", package / "search_inputs")
    expected = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    logs = HERE / "host_logs"
    logs.mkdir()
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
    commands = []
    result = {"completed": False, "gpu_used": False, "build_result_sha256": sha(BUILD / "build_result.json"),
              "install_identity_sha256": sha(BUILD / "install_identity.json"), "package_sha256": expected}

    def call(label, command, stdin=None, timeout=120):
        start = time.monotonic()
        p = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=timeout)
        (logs / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append({"label": label, "command": command, "returncode": p.returncode,
                         "wall_s": time.monotonic() - start})
        print(label, p.returncode, flush=True)
        p.check_returncode()

    started = False
    try:
        call("mkdir", ssh + [shlex.join(["mkdir", "-p", REMOTE])])
        call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + REMOTE + "/"])
        gate = "import pathlib,hashlib,json\nroot=pathlib.Path(%r)\nexpected=%r\n" % (REMOTE, expected)
        gate += 'actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\nassert expected==actual\nprint("all audit inputs match")\n'
        call("input_gate", ssh + ["python3 -"], gate)
        inner = "set -e\nsource /opt/ros/foxy/setup.bash\nsource /workspace/install/setup.bash\npython3 /audit/replay_stair_inputs.py --inputs /audit/search_inputs --output /audit/replay_result"
        cmd = ["timeout", "--kill-after=5", "90", "podman", "run", "--rm", "--pull=never", "--network=none",
               "--name", NAME, "-e", "ROS_DOMAIN_ID=213", "-e", "ROS_LOCALHOST_ONLY=1",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", REMOTE_BUILD + ":/workspace:ro",
               "-v", REMOTE + ":/audit:rw", IMAGE, "bash", "-lc", inner]
        started = True
        call("replay", ssh + [shlex.join(cmd)], timeout=110)
    finally:
        if started:
            call("collect", ["rsync", "-a", "gpu5070ti:" + REMOTE + "/replay_result/", str(HERE / "replay_result") + "/"])
            native = json.loads((HERE / "replay_result/result.json").read_text())
            result["completed"] = native.get("completed") is True
            result["returned_log_hash_matches"] = native["scan_log_sha256"] == sha(HERE / "replay_result/scan.log")
            result["returned_source_hash_matches"] = native["replay_source_sha256"] == sha(HERE / "replay_result/replay_source.py")
        result["commands"] = commands
        (HERE / "execution_result.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["completed"] or not result["returned_log_hash_matches"] or not result["returned_source_hash_matches"]:
        raise RuntimeError("Native audit did not return complete verified evidence")
    print(HERE / "execution_result.json")


if __name__ == "__main__":
    main()
