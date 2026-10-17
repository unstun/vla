"""Stage a bounded CPU tracking replay in the frozen Foxy execution copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id.replace("_", "").isalnum():
        raise ValueError("invalid run id")
    build = P2B / "builds/scan_22"
    if not json.loads((build / "build_result.json").read_text())["passed"] or not (build / "install_identity.json").exists():
        raise ValueError("build identity incomplete")
    out = HERE / args.run_id
    out.mkdir(exist_ok=False)
    package = out / "remote_package"
    package.mkdir()
    shutil.copytree(HERE / "captured_inputs", package / "inputs")
    shutil.copy2(HERE / "replay_foreground.py", package / "replay_foreground.py")
    shutil.copy2(HERE / "unpack_foreground_dependency.py", package / "unpack_foreground_dependency.py")
    deps = HERE / "dependencies/scipy_1_8_1_cp38"
    dep_manifest = json.loads((deps / "manifest.json").read_text())
    shutil.copy2(deps / "manifest.json", package / "dependency_manifest.json")
    shutil.copy2(deps / dep_manifest["filename"], package / "scipy.whl")
    shutil.copy2(ROOT / "references/upstream/2026-09-26_pct_building_static_background/source/building2_9.pcd", package / "building2_9.pcd")
    tests = package / "unit_source"
    tests.mkdir()
    for name in ("moving_cluster_core.py", "moving_cluster_io.py", "static_background.py", "static_foreground_tracker.py",
                 "test_static_foreground_tracker.py", "test_moving_cluster_core.py", "test_moving_cluster_io.py"):
        shutil.copy2(P2B / "reactive_stair" / name, tests / name)
    expected = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    write(out / "package_manifest.json", {"files": expected, "generator_sha256": sha(Path(__file__)),
          "install_identity_sha256": sha(build / "install_identity.json"), "source_manifest_sha256": sha(build / "source_sha256.json")})
    (out / ".gitignore").write_text("# Local staging duplicates; package_manifest.json pins every file.\n"
                                    "/remote_package/scipy.whl\n/remote_package/building2_9.pcd\n/remote_package/inputs/points.npz\n")
    remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + args.run_id
    remote_build = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_22"
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
    logs = out / "host_logs"
    logs.mkdir()
    result = {"completed": False, "gpu_used": False, "image": IMAGE, "remote": remote, "commands": []}

    def call(label, command, stdin=None, timeout=120, required=True):
        start = time.monotonic()
        proc = subprocess.run(command, input=stdin, text=True, capture_output=True, timeout=timeout)
        (logs / (label + ".log")).write_text(proc.stdout + proc.stderr)
        result["commands"].append({"label": label, "command": command, "returncode": proc.returncode, "wall_s": time.monotonic() - start})
        print(label, proc.returncode, flush=True)
        if required:
            proc.check_returncode()
        return proc

    started = False
    try:
        # Fresh execution directory; never mix evidence from attempts.
        call("mkdir", ssh + [shlex.join(["mkdir", remote])])
        call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"], timeout=180)
        gate = "import pathlib,hashlib\nroot=pathlib.Path(%r)\nexpected=%r\n" % (remote, expected)
        gate += "assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in expected.items())\nprint('input identity matches')\n"
        call("input_gate", ssh + ["python3 -"], gate)
        inner = """set -e
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
mkdir /audit/results
python3 -c 'import numpy; assert numpy.__version__ == "1.17.4"; print(numpy.__version__)' > /audit/results/numpy_before.log
python3 /audit/unpack_foreground_dependency.py --wheel /audit/scipy.whl --manifest /audit/dependency_manifest.json --destination /tmp/foreground_dependencies --receipt /audit/results/dependency_receipt.json
export PYTHONPATH=/tmp/foreground_dependencies:$PYTHONPATH
python3 -m unittest discover -s /audit/unit_source -p 'test_*.py' > /audit/results/unit_tests.log 2>&1
python3 /audit/replay_foreground.py numeric --inputs /audit/inputs --background /audit/building2_9.pcd --output /audit/results/numeric
python3 /audit/replay_foreground.py ros --inputs /audit/inputs --background /audit/building2_9.pcd --output /audit/results/ros
"""
        command = ["timeout", "--kill-after=5", "200", "podman", "run", "--rm", "--pull=never", "--network=none",
                   "--name", "vla-foreground-" + args.run_id, "-e", "ROS_DOMAIN_ID=215", "-e", "ROS_LOCALHOST_ONLY=1",
                   "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1",
                   "-v", remote_build + ":/workspace:ro", "-v", remote + ":/audit:rw", IMAGE, "bash", "-lc", inner]
        started = True
        call("replay", ssh + [shlex.join(command)], timeout=220)
        result["completed"] = True
    finally:
        if started:
            call("collect", ["rsync", "-a", "gpu5070ti:" + remote + "/results/", str(out / "results") + "/"], required=False)
            listing = "import pathlib,hashlib,json\np=pathlib.Path(%r)\nprint(json.dumps({str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in p.rglob('*') if x.is_file()}))\n" % (remote + "/results")
            native = call("returned_hashes", ssh + ["python3 -"], listing)
            remote_hashes = json.loads(native.stdout)
            result["returned_sha256"] = remote_hashes
            result["returned_hashes_match"] = all((out / "results" / p).is_file() and sha(out / "results" / p) == h for p, h in remote_hashes.items())
            call("input_gate_after", ssh + ["python3 -"], gate)
        write(out / "execution_result.json", result)
    if not result["completed"] or not result["returned_hashes_match"]:
        raise RuntimeError("replay incomplete or output identity failed")
    print(out / "execution_result.json")


if __name__ == "__main__":
    main()
