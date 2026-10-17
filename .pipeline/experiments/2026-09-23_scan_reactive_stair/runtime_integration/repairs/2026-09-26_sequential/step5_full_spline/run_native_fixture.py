"""Compile actual UniformBspline and the complete-interval gate in pinned Foxy."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker():
    root = Path("/test")
    expected = json.loads((root / "inputs.json").read_text())
    assert all(sha(root / p) == digest for p, digest in expected.items())
    command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic", "-I/test/include", "-I/usr/include/eigen3",
               "/test/uniform_bspline.cpp", "/test/test.cpp", "-o", "/test/native_tests"]
    compiled = subprocess.run(command, text=True, capture_output=True, timeout=50)
    (root / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"compile_command": command, "compile_exit": compiled.returncode, "inputs_sha256": expected, "passed": False}
    if compiled.returncode == 0:
        started = time.monotonic()
        run = subprocess.run(["/test/native_tests"], text=True, capture_output=True, timeout=10)
        result.update(test_exit=run.returncode, stdout=run.stdout, stderr=run.stderr,
                      fixture_wall_s=time.monotonic() - started, passed=run.returncode == 0)
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(attempt):
    root = HERE.parents[6]
    p2b = root / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
    build = p2b / "builds/scan_24/src"
    out = HERE / ("native_scan24_v%d" % attempt)
    out.mkdir(exist_ok=False)
    package = out / "package"
    for name in ("bspline_opt", "plan_env"):
        (package / "include" / name).mkdir(parents=True)
    for name in ("uniform_bspline.h", "full_trajectory_collision.h"):
        shutil.copy2(build / "bspline_opt/include/bspline_opt" / name, package / "include/bspline_opt" / name)
    for name in ("motion_heading.h", "reactive_collision.h"):
        shutil.copy2(build / "plan_env/include/plan_env" / name, package / "include/plan_env" / name)
    shutil.copy2(build / "bspline_opt/src/uniform_bspline.cpp", package / "uniform_bspline.cpp")
    shutil.copy2(p2b / "reactive_stair/test_full_trajectory_collision.cpp", package / "test.cpp")
    shutil.copy2(__file__, package / "worker.py")
    manifest = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + out.name
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
    commands = []
    def call(label, command):
        p = subprocess.run(command, capture_output=True, text=True, timeout=110)
        (out / (label + ".log")).write_text(p.stdout + p.stderr)
        commands.append({"label": label, "command": command, "returncode": p.returncode})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        print(label, p.returncode, flush=True)
        p.check_returncode()
    call("mkdir", ssh + [shlex.join(["mkdir", remote])])
    call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
    command = ["timeout", "--kill-after=5", "80", "podman", "run", "--rm", "--pull=never", "--network=none",
               "--name", "vla-spline-gate-" + out.name, "-v", remote + ":/test:rw", IMAGE, "python3", "/test/worker.py", "--worker"]
    call("tests", ssh + [shlex.join(command)])
    call("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log", "--exclude=*",
                     "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["inputs_sha256"] == manifest
    print(json.dumps({k: v for k, v in result.items() if k != "inputs_sha256"}, indent=2))
    if not result["passed"]:
        raise RuntimeError("native complete-interval fixture failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    worker() if args.worker else host(args.attempt)
