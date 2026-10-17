"""Native PVA/timing regression using the actual spline and recorded seed."""
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
COMMON = ["boundary_pva", "interior_invariance", "recorded_seed", "straight_control"]
EXTRA = ["invalid_input", "impossible_boundary", "final_pva_gate", "iteration_budget"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def worker(package, compiler, eigen):
    expected = json.loads((package / "inputs.json").read_text())
    assert all(sha(package / p) == value for p, value in expected.items())
    candidate = (package / "include/bspline_opt/timed_cubic_initialization.h").exists()
    command = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
               "-I" + str(package / "include"), "-I" + str(eigen)]
    if candidate:
        command.append("-DCANDIDATE_TIMED_CUBIC")
    command += [str(package / "uniform_bspline.cpp"), str(package / "test.cpp"), "-o", str(package / "native_tests")]
    compiled = subprocess.run(command, text=True, capture_output=True, timeout=80)
    (package / "compile.log").write_text(compiled.stdout + compiled.stderr)
    result = {"compile_command": command, "compile_exit": compiled.returncode,
              "inputs_sha256": expected, "cases": {}, "candidate": candidate,
              "claim": "Actual UniformBspline derivative evaluation and feasibility check; captured seed geometry and first-replan body velocity. No map or optimizer in this fixture."}
    if compiled.returncode == 0:
        for case in COMMON + (EXTRA if candidate else []):
            started = time.monotonic()
            run = subprocess.run([str(package / "native_tests"), case, str(package / "seed.csv")],
                                 text=True, capture_output=True, timeout=15)
            result["cases"][case] = {"returncode": run.returncode, "stdout": run.stdout,
                                     "stderr": run.stderr, "wall_s": time.monotonic() - started}
    (package / "result.json").write_text(json.dumps(result, indent=2) + "\n")


def host(args):
    if not args.build.replace("_", "").isalnum():
        raise ValueError("invalid build identity")
    p2b = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
    build = p2b / "builds" / args.build / "src"
    out = HERE / f"native_{args.build}_{'local' if args.local else 'foxy'}_v{args.attempt}"
    package = out / "package"
    (package / "include/bspline_opt").mkdir(parents=True, exist_ok=False)
    (package / "include/plan_manage").mkdir()
    for name in ("uniform_bspline.h", "full_trajectory_collision.h", "timed_cubic_initialization.h"):
        source = build / "bspline_opt/include/bspline_opt" / name
        if source.exists():
            shutil.copy2(source, package / "include/bspline_opt" / name)
    shutil.copy2(build / "plan_manage/include/plan_manage/seed_polyline_sampling.h", package / "include/plan_manage/seed_polyline_sampling.h")
    shutil.copy2(build / "bspline_opt/src/uniform_bspline.cpp", package / "uniform_bspline.cpp")
    shutil.copy2(p2b / "reactive_stair/test_timed_cubic.cpp", package / "test.cpp")
    trace = HERE.parent / "step8_spline_seed/GEOMETRY_TRACE.json"
    points = json.loads(trace.read_text())["points"]["seed"]
    (package / "seed.csv").write_text("".join(",".join(format(v,".17g") for v in p) + "\n" for p in points))
    events = HERE.parent / "step6_body_reference/body_reference_030_inputs/events.json"
    body = [e for e in json.loads(events.read_text()) if e["kind"] == "body" and abs(e["stamp"]/1e9 - 5.01) < 1e-6]
    assert len(body) == 1 and sum((a-b)**2 for a,b in zip(body[0]["data"]["position"],points[0])) < 1e-18
    (package / "seed.csv.pva").write_text(" ".join(format(v,".17g") for v in body[0]["data"]["linear"]) + "\n")
    (package / "provenance.json").write_text(json.dumps({"geometry_trace_sha256":sha(trace), "events_sha256":sha(events),
        "body_event":body[0], "terminal_velocity":[0,0,0], "accelerations":[[0,0,0],[0,0,0]],
        "terminal_source":"first-replan goal log and getLocalTarget braking branch"},indent=2)+"\n")
    shutil.copy2(__file__,package / "worker.py")
    manifest={p.relative_to(package).as_posix():sha(p) for p in package.rglob("*") if p.is_file()}
    (package / "inputs.json").write_text(json.dumps(manifest,indent=2)+"\n")
    if args.local:
        eigen=Path(args.eigen_dir)
        (out / "eigen_identity.json").write_text(json.dumps({p.relative_to(eigen).as_posix():sha(p)
            for p in (eigen / "Eigen").rglob("*") if p.is_file()},indent=2)+"\n")
        worker(package.resolve(),"clang++",eigen)
        for name in ("result.json","compile.log"):
            shutil.copy2(package/name,out/name)
    else:
        remote="/home/sun/vla_exec/2026-09-26_stair_repairs/"+out.name
        ssh=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=15","gpu5070ti"]
        commands=[]
        def call(label,command):
            run=subprocess.run(command,capture_output=True,text=True,timeout=180)
            (out/(label+".log")).write_text(run.stdout+run.stderr)
            commands.append({"label":label,"command":command,"returncode":run.returncode})
            (out/"commands.json").write_text(json.dumps(commands,indent=2)+"\n")
            print(label,run.returncode,flush=True)
            run.check_returncode()
        call("mkdir",ssh+[shlex.join(["mkdir",remote])])
        call("sync",["rsync","-a",str(package)+"/","gpu5070ti:"+remote+"/"])
        command=["timeout","--kill-after=5","150","podman","run","--rm","--pull=never","--network=none",
                 "--name","vla-timed-cubic-"+args.build,"-v",remote+":/test:rw",IMAGE,"python3","/test/worker.py","--worker"]
        call("tests",ssh+[shlex.join(command)])
        call("collect",["rsync","-a","--include=/result.json","--include=/compile.log","--exclude=*",
                        "gpu5070ti:"+remote+"/",str(out)+"/"])
    result=json.loads((out/"result.json").read_text())
    assert result["compile_exit"]==0 and result["inputs_sha256"]==manifest
    failures={name for name,r in result["cases"].items() if r["returncode"]!=0}
    expected=set(COMMON[:3]) if args.expected_red else set()
    print(json.dumps({"failures":sorted(failures),"expected":sorted(expected),"cases":result["cases"]},indent=2))
    if failures!=expected:
        raise RuntimeError("native timing fixture differs from declared expectation")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--worker",action="store_true")
    p.add_argument("--build",default="scan_27")
    p.add_argument("--attempt",type=int,default=1)
    p.add_argument("--local",action="store_true")
    p.add_argument("--eigen-dir")
    p.add_argument("--expected-red",action="store_true")
    a=p.parse_args()
    if a.worker:
        worker(Path("/test"),"g++",Path("/usr/include/eigen3"))
    else:
        if a.local and not a.eigen_dir:
            p.error("explicit read-only Eigen path required")
        host(a)
