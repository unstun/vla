"""Compile the captured native AStar locally or in the pinned Foxy runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
CASES = ["changed_heading", "unknown_midpoint", "blocked_endpoint", "reuse_modes", "lattice_and_short_goal"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def worker(package, strict, eigen, compiler):
    expected = json.loads((package / "inputs.json").read_text())
    assert all(sha(package / p) == digest for p, digest in expected.items())
    eigen_files = {p.relative_to(eigen).as_posix(): sha(p)
                   for p in (eigen / "Eigen").rglob("*") if p.is_file()}
    assert "Eigen/Core" in eigen_files
    (package / "eigen_identity.json").write_text(json.dumps(eigen_files, indent=2) + "\n")
    version = subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True).stdout
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-I" + str(package / "stubs"), "-I" + str(package / "native/path_searching/include"),
               "-I" + str(package / "native/plan_env/include"), "-I" + str(eigen),
               str(package / "native/path_searching/src/dyn_a_star.cpp"), str(package / "test.cpp"),
               "-o", str(package / "native_tests")]
    if strict:
        command.insert(1, "-DSTRICT_ENDPOINT_TEST")
    compiled = subprocess.run(command, text=True, capture_output=True, timeout=60)
    (package / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"compile_command": command, "compile_exit": compiled.returncode,
              "compiler_version": version, "platform": platform.platform(),
              "source_sha256": expected, "eigen_identity_sha256": sha(package / "eigen_identity.json"),
              "cases": {}, "strict": strict,
              "claim": "Actual captured AStar source; collision/ROS logger test doubles. No ROS/simulator claim."}
    if compiled.returncode == 0:
        for case in CASES + (["invalid_input", "connector_budget", "connector_radius"] if strict else []):
            started = time.monotonic()
            run = subprocess.run([str(package / "native_tests"), case], text=True, capture_output=True, timeout=5)
            result["cases"][case] = {"exit_code": run.returncode, "stdout": run.stdout,
                                     "stderr": run.stderr, "wall_s": time.monotonic() - started}
    result["all_passed"] = compiled.returncode == 0 and bool(result["cases"]) and all(
        r["exit_code"] == 0 for r in result["cases"].values())
    (package / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(args):
    root = P2B.parents[3]
    output_root = root / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/repairs/2026-09-26_sequential/step7_exact_endpoint"
    if not args.build.replace("_", "").isalnum():
        raise ValueError("invalid build name")
    source = P2B / "builds" / args.build / "src"
    run_id = f"endpoints_{args.build}_{'local' if args.local else 'foxy'}_v{args.attempt}"
    out = output_root / run_id
    package = out / "package"
    package.mkdir(parents=True, exist_ok=False)
    for rel in ["path_searching/include/path_searching/dyn_a_star.h", "path_searching/src/dyn_a_star.cpp",
                "plan_env/include/plan_env/astar_grid_coordinates.h", "plan_env/include/plan_env/collision_segment.h"]:
        target = package / "native" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    shutil.copytree(HERE / "astar_test_stubs", package / "stubs")
    shutil.copy2(HERE / "test_native_astar_endpoints.cpp", package / "test.cpp")
    shutil.copy2(Path(__file__), package / "worker.py")
    manifest = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.local:
        worker(package.resolve(), args.strict, Path(args.eigen_dir).resolve(), "clang++")
        for name in ["result.json", "compile.log", "eigen_identity.json"]:
            shutil.copy2(package / name, out / name)
    else:
        remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + run_id
        ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
        commands = []

        def run(label, command):
            value = subprocess.run(command, text=True, capture_output=True, timeout=120)
            (out / (label + ".log")).write_text(value.stdout + value.stderr)
            commands.append({"label": label, "command": command, "returncode": value.returncode})
            (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            print(label, value.returncode, flush=True)
            value.check_returncode()

        run("mkdir", ssh + [shlex.join(["mkdir", "-p", remote])])
        run("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
        cmd = ["timeout", "--kill-after=5", "100", "podman", "run", "--rm", "--pull=never", "--network=none",
               "--name", "vla-endpoints-" + args.build, "-v", remote + ":/test:rw", IMAGE,
               "python3", "/test/worker.py", "--worker"]
        if args.strict:
            cmd.append("--strict")
        run("tests", ssh + [shlex.join(cmd)])
        run("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log",
                        "--include=/eigen_identity.json", "--exclude=*", "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["source_sha256"] == manifest and result["compile_exit"] == 0
    failures = {k for k, v in result["cases"].items() if v["exit_code"] != 0}
    expected_failures = set() if args.strict else set(CASES)
    print(json.dumps({"build": args.build, "actual_failures": sorted(failures),
                      "expected_failures": sorted(expected_failures), "result": str(out / "result.json")}))
    if failures != expected_failures:
        raise RuntimeError("Native endpoint outcome differs from its predeclared expectation")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("build", nargs="?")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--local", action="store_true")
    p.add_argument("--eigen-dir")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--worker", action="store_true")
    a = p.parse_args()
    if a.worker:
        worker(Path("/test"), a.strict, Path("/usr/include/eigen3"), "g++")
    else:
        if a.local and not a.eigen_dir:
            p.error("local compilation requires an explicit read-only Eigen include directory")
        host(a)
