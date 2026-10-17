"""Exercise actual target/FSM methods with an explicit planning verdict double."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
CASES = ["global_preserved", "adjusted_commit", "failed_progress", "prefix_success", "shared_budget",
         "no_frontier", "near_goal", "frontier_refresh", "unchanged_positive", "legacy_goal_adjustment", "new_route_reset",
         "invalid_input", "blocked_prefix", "rejected_prefix_budget"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def brace_end(text, begin):
    depth = 0
    tokens = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)
    for match in tokens.finditer(text, begin):
        if match[0] == "{":
            depth += 1
        elif match[0] == "}":
            depth -= 1
            if depth == 0:
                return match.end()
    raise ValueError("unclosed native method")


def extract(text):
    methods = []
    for name in ("adjustGlobalTargetIfOccupied", "getLocalTarget", "callReboundReplan", "planFromCurrentTraj"):
        match = re.search(r"  (?:bool|void) SCANReplanFSM::" + name + r"\(", text)
        assert match
        end = brace_end(text, text.index("{", match.end()))
        methods.append(text[match.start():end] + "\n")
    marker = text.index("      if (t_cur > info->duration_ - 1e-2)")
    begin = text.index("{", marker)
    end = brace_end(text, begin)
    methods.append("void SCANReplanFSM::expireLocal() {\n" + text[begin+1:end-1] + "\n}\n")
    return "\n".join(methods)


def worker(package, compiler, eigen):
    manifest = json.loads((package / "inputs.json").read_text())
    assert all(sha(package / p) == value for p, value in manifest.items())
    source = (package / "source_fsm.cpp").read_text()
    assert (package / "native_target_methods.inc").read_text() == extract(source)
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-I" + str(package), "-I" + str(eigen), str(package / "test.cpp"), "-o", str(package / "native_tests")]
    if "reference_frontier_time_" in source:
        command.insert(1, "-DCANDIDATE_REFERENCE_PREFIX")
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (package / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"inputs_sha256": manifest, "compile_command": command, "compile_exit": compiled.returncode,
              "cases": {}, "claim": "Actual target selection, replan wrappers and existing expiry block. Route, manager complete-planning verdict and ROS are doubles; no optimizer/map or physical-stop claim."}
    if compiled.returncode == 0:
        for case in CASES:
            run = subprocess.run([str(package / "native_tests"), case], capture_output=True, text=True, timeout=10)
            result["cases"][case] = {"returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr}
    (package / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(args):
    if not args.build.replace("_", "").isalnum():
        raise ValueError("invalid build name")
    p2b = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
    source = p2b / "builds" / args.build / "src/plan_manage"
    out = HERE / f"native_{args.build}_{'local' if args.local else 'foxy'}_v{args.attempt}"
    package = out / "package"
    package.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source / "src/scan_replan_fsm.cpp", package / "source_fsm.cpp")
    shutil.copy2(source / "include/plan_manage/scan_replan_fsm.h", package / "source_fsm.h")
    shutil.copy2(HERE / "test_native_targets.cpp", package / "test.cpp")
    shutil.copy2(__file__, package / "worker.py")
    (package / "native_target_methods.inc").write_text(extract((package / "source_fsm.cpp").read_text()))
    manifest = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.local:
        worker(package.resolve(), "clang++", Path(args.eigen_dir))
        for name in ("result.json", "compile.log"):
            shutil.copy2(package / name, out / name)
    else:
        remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/reference_targets_" + out.name
        ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
        commands = []
        def call(label, command):
            run = subprocess.run(command, capture_output=True, text=True, timeout=180)
            (out / (label + ".log")).write_text(run.stdout + run.stderr)
            commands.append({"label": label, "command": command, "returncode": run.returncode})
            (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            print(label, run.returncode, flush=True)
            run.check_returncode()
        call("mkdir", ssh + [shlex.join(["mkdir", remote])])
        call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
        command = ["timeout", "--kill-after=5", "150", "podman", "run", "--rm", "--pull=never", "--network=none",
                   "--name", "vla-reference-targets-" + args.build, "-v", remote + ":/test:rw", IMAGE,
                   "python3", "/test/worker.py", "--worker"]
        call("tests", ssh + [shlex.join(command)])
        call("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log", "--exclude=*",
                         "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["compile_exit"] == 0 and result["inputs_sha256"] == manifest
    failures = {k for k, v in result["cases"].items() if v["returncode"] != 0}
    expected = set(CASES[:8] + CASES[11:]) if args.expected_red else set()
    print(json.dumps({"failures": sorted(failures), "expected": sorted(expected), "result": str(out / "result.json")}))
    if failures != expected:
        raise RuntimeError("native target outcome differs from declared expectation")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", default="scan_32")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--local", action="store_true")
    p.add_argument("--eigen-dir")
    p.add_argument("--expected-red", action="store_true")
    p.add_argument("--worker", action="store_true")
    args = p.parse_args()
    if args.worker:
        worker(Path("/test"), "g++", Path("/usr/include/eigen3"))
    else:
        if args.local and not args.eigen_dir:
            p.error("explicit Eigen include path required")
        host(args)
