"""Exercise captured optimizer blocks with controlled map/search boundaries."""
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
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
CASES = ["empty_route", "no_intersection", "stale_intersection", "zero_direction",
         "rebound_stale_intersection", "rebound_zero_direction", "valid_then_zero",
         "valid_constraints", "no_collision", "short_segment"]
CASES += ["initial_mode", "retry_mode", "callback_mode", "merge_mode", "failure_modes", "reuse_modes"]
CASES += ["recorded_projection", "blocked_projection_heading", "mismatched_projection_route"]
OLD_FAILURES = {"recorded_projection"}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def worker(package, compiler, eigen):
    expected = json.loads((package / "inputs.json").read_text())
    assert all(sha(package / p) == value for p, value in expected.items())
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-DEIGEN_INITIALIZE_MATRICES_BY_NAN", "-I" + str(package), "-I" + str(eigen),
               str(package / "test.cpp"), "-o", str(package / "native_tests")]
    projection = "nearestPointOnMatchingRoute" in (package / "rebound_constraint_utils.h").read_text()
    if projection:
        command.insert(1, "-DROUTE_PROJECTION_FALLBACK")
    compile_result = subprocess.run(command, text=True, capture_output=True, timeout=60)
    (package / "compile.log").write_text(compile_result.stdout + compile_result.stderr)
    result = {"compile_command": command, "compile_exit": compile_result.returncode,
              "inputs_sha256": expected, "platform": platform.platform(), "cases": {},
              "claim": "Actual full native initControlPoints and check_collision_and_rebound methods plus assignment block and ControlPoints. Map/search/logger are doubles. Search spy verifies exact-endpoint mode and unchanged control-column endpoints; actual route and curve acceptance require runtime replay."}
    if compile_result.returncode == 0:
        for case in CASES + (["projection_math"] if projection else []):
            started = time.monotonic()
            run = subprocess.run([str(package / "native_tests"), case, str(package / "recorded_projection.txt")], text=True, capture_output=True, timeout=5)
            result["cases"][case] = {"returncode": run.returncode, "stdout": run.stdout,
                                     "stderr": run.stderr, "wall_s": time.monotonic() - started}
    result["all_passed"] = compile_result.returncode == 0 and len(result["cases"]) == len(CASES) + int(projection) and all(
        case["returncode"] == 0 for case in result["cases"].values())
    (package / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(args):
    if not args.build.replace("_", "").isalnum():
        raise ValueError("invalid build name")
    root = HERE.parents[6]
    p2b = root / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
    native = p2b / "builds" / args.build / "src/bspline_opt"
    run_id = f"constraints_{args.build}_{'local' if args.local else 'foxy'}_v{args.attempt}"
    out = HERE / run_id
    package = out / "package"
    (package / "rclcpp").mkdir(parents=True, exist_ok=False)
    shutil.copy2(native / "src/bspline_optimizer.cpp", package / "source_optimizer.cpp")
    shutil.copy2(native / "include/bspline_opt/bspline_optimizer.h", package / "source_optimizer.h")
    source = (package / "source_optimizer.cpp").read_text()
    header = (package / "source_optimizer.h").read_text()
    init_begin = source.index("  std::vector<std::vector<Eigen::Vector3d>> BsplineOptimizer::initControlPoints(")
    init_end = source.index("  int BsplineOptimizer::earlyExit(", init_begin)
    (package / "native_init.inc").write_text(source[init_begin:init_end])
    first = source.index("    /*** Assign data to each segment ***/")
    last = source.index("    return a_star_paths;", first)
    assignment = source[first:last]
    first_rebound = source.index("  bool BsplineOptimizer::check_collision_and_rebound(void)")
    last_rebound = source.index("  bool BsplineOptimizer::BsplineOptimizeTrajRebound", first_rebound)
    rebound = source[first_rebound:last_rebound]
    (package / "native_blocks.inc").write_text(
        "vector<vector<Vector3d>> BsplineOptimizer::assignTest() {\n"
        "  auto& segment_ids = segments_; auto& final_segment_ids = final_segments_;\n"
        "  auto& a_star_paths = paths_; bool occ = false;\n" + assignment +
        "  return a_star_paths;\n}\n" + rebound)
    (package / "native_control_points.inc").write_text(
        header[header.index("  class ControlPoints"):header.index("  class BsplineOptimizer")])
    (package / "extraction.json").write_text(json.dumps({
        "assignment_start_line": source[:first].count("\n") + 1,
        "assignment_end_line_exclusive": source[:last].count("\n") + 1,
        "rebound_start_line": source[:first_rebound].count("\n") + 1,
        "rebound_end_line_exclusive": source[:last_rebound].count("\n") + 1,
        "source_sha256": sha(package / "source_optimizer.cpp"),
        "boundary": "Native blocks verbatim after line-ending normalization; fixtures provide inputs and outer declarations."}, indent=2) + "\n")
    helper = native / "include/bspline_opt/rebound_constraint_utils.h"
    if helper.exists():
        shutil.copy2(helper, package / helper.name)
    shutil.copy2(p2b / "reactive_stair/test_native_rebound_constraints.cpp", package / "test.cpp")
    shutil.copy2(p2b / "reactive_stair/astar_test_stubs/rclcpp/rclcpp.hpp", package / "rclcpp/rclcpp.hpp")
    geometry = HERE.parent / "step20_rebound_returned_curve/GEOMETRY.json"
    data = json.loads(geometry.read_text())
    points = data["final"]["controls"]
    begin, end = data["stop_state"]["segments"][0]
    path = data["stop_state"]["paths"][0]
    (package / "recorded_projection.txt").write_text(f"{len(points)} {begin} {end} {len(path)}\n" + "".join(
        " ".join(format(v,".17g") for v in p) + "\n" for p in points + path))
    (package / "recorded_provenance.json").write_text(json.dumps({"geometry_sha256":sha(geometry),
        "claim":"Actual returned controls and failed segment/path; collision oracle is synthetic for isolating constraint generation and heading guards."},indent=2)+"\n")
    shutil.copy2(__file__, package / "worker.py")
    manifest = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.local:
        eigen = Path(args.eigen_dir)
        (out / "eigen_identity.json").write_text(json.dumps({p.relative_to(eigen).as_posix(): sha(p)
            for p in (eigen / "Eigen").rglob("*") if p.is_file()}, indent=2) + "\n")
        worker(package.resolve(), "clang++", eigen)
        for name in ["result.json", "compile.log"]:
            shutil.copy2(package / name, out / name)
    else:
        remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/" + run_id
        ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
        commands = []
        def call(label, command):
            run = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (out / (label + ".log")).write_text(run.stdout + run.stderr)
            commands.append({"label": label, "command": command, "returncode": run.returncode})
            (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            print(label, run.returncode, flush=True)
            run.check_returncode()
        call("mkdir", ssh + [shlex.join(["mkdir", remote])])
        call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
        command = ["timeout", "--kill-after=5", "100", "podman", "run", "--rm", "--pull=never", "--network=none",
                   "--name", "vla-constraints-" + args.build, "-v", remote + ":/test:rw", IMAGE,
                   "python3", "/test/worker.py", "--worker"]
        call("tests", ssh + [shlex.join(command)])
        call("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log", "--exclude=*",
                         "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["compile_exit"] == 0 and result["inputs_sha256"] == manifest
    failures = {name for name, r in result["cases"].items() if r["returncode"] != 0}
    expected = OLD_FAILURES if args.expected_red else set()
    print(json.dumps({"build": args.build, "failures": sorted(failures), "expected": sorted(expected), "result": str(out / "result.json")}))
    if failures != expected:
        raise RuntimeError("native constraint regression differed from predeclared expectation")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--worker", action="store_true")
    p.add_argument("--build", default="scan_31")
    p.add_argument("--expected-red", action="store_true")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--local", action="store_true")
    p.add_argument("--eigen-dir")
    a = p.parse_args()
    if a.worker:
        worker(Path("/test"), "g++", Path("/usr/include/eigen3"))
    else:
        if a.local and not a.eigen_dir:
            p.error("local test requires explicit read-only Eigen path")
        host(a)
