"""Build actual captured AStar against controlled occupancy fixtures in Foxy."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
CASES = ["blocked_first", "queue_order", "round_reuse", "no_path", "vertical_route", "improved_cost"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(fixed):
    root = Path("/test")
    expected = json.loads((root / "inputs.json").read_text())
    assert all(sha(root / p) == digest for p, digest in expected.items())
    command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-I/test/stubs", "-I/test/native/path_searching/include", "-I/test/native/plan_env/include",
               "-I/usr/include/eigen3", "/test/native/path_searching/src/dyn_a_star.cpp", "/test/test.cpp",
               "-o", "/test/native_tests"]
    if fixed:
        command.insert(1, "-DFIXED_QUEUE_TEST")
    compiled = subprocess.run(command, text=True, capture_output=True, timeout=45)
    (root / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"compile_command": command, "compile_exit": compiled.returncode,
              "inputs_match": True, "cases": {}, "source_sha256": expected,
              "claim": "Actual native search implementation; only collision and ROS logger are test doubles"}
    result["test_mutation"] = json.loads((root / "mutation.json").read_text()) if (root / "mutation.json").exists() else None
    if compiled.returncode == 0:
        for case in CASES:
            started = time.monotonic()
            run = subprocess.run([str(root / "native_tests"), case], text=True, capture_output=True, timeout=5)
            result["cases"][case] = {"exit_code": run.returncode, "stdout": run.stdout,
                                      "stderr": run.stderr, "wall_s": time.monotonic() - started}
    result["all_passed"] = compiled.returncode == 0 and all(r["exit_code"] == 0 for r in result["cases"].values())
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(name, fixed, attempt, mutation):
    if not name.replace("_", "").isalnum():
        raise ValueError("invalid build name")
    root = P2B.parents[3]
    source = P2B / "builds" / name / "src"
    run_id = "native_" + name + ("_v%d" % attempt if attempt > 1 else "")
    out = root / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/repairs/2026-09-26_sequential/step1_astar" / run_id
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    package = out / "package"
    package.mkdir()
    paths = ["path_searching/include/path_searching/dyn_a_star.h", "path_searching/src/dyn_a_star.cpp",
             "plan_env/include/plan_env/astar_grid_coordinates.h"]
    for rel in paths:
        target = package / "native" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)
    if mutation:
        if not fixed:
            raise ValueError("mutation control requires fixed queue")
        staged = package / "native/path_searching/src/dyn_a_star.cpp"
        text = staged.read_bytes()
        anchor = b"                    openSet_.emplace(neighborPtr);"
        if text.count(anchor) != 2:
            raise ValueError("mutation anchor changed")
        position = text.rfind(anchor)
        staged.write_bytes(text[:position] + b"                    // TEST MUTATION: omit improved-cost enqueue." + text[position + len(anchor):])
        (package / "mutation.json").write_text(json.dumps({"mutation": "omit only improved-cost enqueue", "production_source_unchanged": True}) + "\n")
    shutil.copytree(HERE / "astar_test_stubs", package / "stubs")
    shutil.copy2(HERE / "test_native_astar_bookkeeping.cpp", package / "test.cpp")
    shutil.copy2(Path(__file__), package / "worker.py")
    manifest = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + run_id
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
    commands = []

    def run(label, command, timeout=120):
        value = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        (out / (label + ".log")).write_text(value.stdout + value.stderr)
        commands.append({"label": label, "command": command, "returncode": value.returncode})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        print(label, value.returncode, flush=True)
        value.check_returncode()

    run("mkdir", ssh + [shlex.join(["mkdir", "-p", remote])])
    run("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
    cmd = ["timeout", "--kill-after=5", "80", "podman", "run", "--rm", "--pull=never", "--network=none",
           "--name", "vla-native-astar-" + name, "-v", remote + ":/test:rw", IMAGE,
           "python3", "/test/worker.py", "--worker"]
    if fixed:
        cmd.append("--fixed-queue")
    run("tests", ssh + [shlex.join(cmd)])
    run("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log", "--exclude=*",
                    "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["source_sha256"] == manifest and result["compile_exit"] == 0
    expected_failures = {"improved_cost"} if mutation else (set() if fixed else {"blocked_first", "queue_order", "round_reuse", "improved_cost"})
    failures = {k for k, v in result["cases"].items() if v["exit_code"] != 0}
    print(json.dumps({"build": name, "actual_failures": sorted(failures), "expected_failures": sorted(expected_failures)}))
    if failures != expected_failures:
        raise RuntimeError("Native regression outcome differs from its predeclared expectation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("build", nargs="?")
    parser.add_argument("--fixed-queue", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--mutation-no-requeue", action="store_true")
    args = parser.parse_args()
    worker(args.fixed_queue) if args.worker else host(args.build, args.fixed_queue, args.attempt, args.mutation_no_requeue)
