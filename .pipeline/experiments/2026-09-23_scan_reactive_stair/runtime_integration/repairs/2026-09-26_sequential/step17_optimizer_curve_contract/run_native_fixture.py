"""Exercise captured native optimizer terminal checks with an inert solver."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
CASES = ["clear", "tail", "endpoint", "thin_prefix", "zero_chord", "budget", "recorded_window"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(package):
    cpp = (package / "source_optimizer.cpp").read_text()
    header = (package / "source_optimizer.h").read_text()
    methods = cpp[cpp.index("  bool BsplineOptimizer::rebound_optimize()"):
                  cpp.index("  void BsplineOptimizer::combineCostRebound(")]
    controls = header[header.index("  class ControlPoints"):
                      header.index("  class BsplineOptimizer")]
    return {"native_optimizer_methods.inc": methods, "native_control_points.inc": controls}


def worker(package, compiler, eigen):
    manifest = json.loads((package / "inputs.json").read_text())
    assert all(sha(package / p) == value for p, value in manifest.items())
    assert all((package / p).read_text() == value for p, value in extract(package).items())
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-I" + str(package / "include"), "-I" + str(package), "-I" + str(eigen),
               str(package / "uniform_bspline.cpp"), str(package / "test.cpp"), "-o", str(package / "native_tests")]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=80)
    (package / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"inputs_sha256": manifest, "compile_command": command, "compile_exit": compiled.returncode,
              "cases": {}, "claim": "Two actual native optimizer methods and native spline math. Solver, map oracle and constraint generation are doubles; this verifies terminal/retry contract, not optimization or terrain integration."}
    if compiled.returncode == 0:
        for case in CASES:
            run = subprocess.run([str(package / "native_tests"), case, str(package / "recorded_curve.txt")],
                                 capture_output=True, text=True, timeout=10)
            result["cases"][case] = {"returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr}
    (package / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(args):
    if not args.build.replace("_", "").isalnum():
        raise ValueError("invalid build name")
    p2b = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
    source = p2b / "builds" / args.build / "src"
    out = HERE / f"native_{args.build}_{'local' if args.local else 'foxy'}_v{args.attempt}"
    package = out / "package"
    (package / "include/bspline_opt").mkdir(parents=True, exist_ok=False)
    (package / "include/rclcpp").mkdir()
    for name in ("uniform_bspline.h", "full_trajectory_collision.h", "rebound_constraint_utils.h"):
        shutil.copy2(source / "bspline_opt/include/bspline_opt" / name, package / "include/bspline_opt" / name)
    shutil.copy2(source / "bspline_opt/src/uniform_bspline.cpp", package / "uniform_bspline.cpp")
    shutil.copy2(source / "bspline_opt/src/bspline_optimizer.cpp", package / "source_optimizer.cpp")
    shutil.copy2(source / "bspline_opt/include/bspline_opt/bspline_optimizer.h", package / "source_optimizer.h")
    shutil.copy2(p2b / "reactive_stair/astar_test_stubs/rclcpp/rclcpp.hpp", package / "include/rclcpp/rclcpp.hpp")
    shutil.copy2(HERE / "test_native_optimizer_checks.cpp", package / "test.cpp")
    shutil.copy2(__file__, package / "worker.py")
    for name, value in extract(package).items():
        (package / name).write_text(value)
    geometry = HERE.parent / "step16_curve_rejection/GEOMETRY.json"
    curve = json.loads(geometry.read_text())["final"]
    controls, knots = curve["controls"], curve["knots"]
    h = knots[4] - knots[3]
    assert all(abs(b - a - h) < 1e-12 for a, b in zip(knots, knots[1:]))
    (package / "recorded_curve.txt").write_text(f"{len(controls)} {h:.17g}\n" + "".join(
        " ".join(f"{v:.17g}" for v in p) + "\n" for p in controls))
    (package / "provenance.json").write_text(json.dumps({"geometry_sha256": sha(geometry),
        "curve_label": "final", "note": "Actual recorded controls/time; synthetic narrow rejection region around recorded first failure."}, indent=2) + "\n")
    manifest = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.local:
        worker(package.resolve(), "clang++", Path(args.eigen_dir))
        for name in ("result.json", "compile.log"):
            shutil.copy2(package / name, out / name)
    else:
        remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/optimizer_checks_" + out.name
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
                   "--name", "vla-optimizer-checks-" + args.build, "-v", remote + ":/test:rw", IMAGE,
                   "python3", "/test/worker.py", "--worker"]
        call("tests", ssh + [shlex.join(command)])
        call("collect", ["rsync", "-a", "--include=/result.json", "--include=/compile.log", "--exclude=*",
                         "gpu5070ti:" + remote + "/", str(out) + "/"])
    result = json.loads((out / "result.json").read_text())
    assert result["compile_exit"] == 0 and result["inputs_sha256"] == manifest
    failures = {k for k, v in result["cases"].items() if v["returncode"] != 0}
    expected = set(CASES[1:]) if args.expected_red else set()
    print(json.dumps({"failures": sorted(failures), "expected": sorted(expected), "result": str(out / "result.json")}))
    if failures != expected:
        raise RuntimeError("native optimizer check outcome differs from declared expectation")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", default="scan_29")
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
