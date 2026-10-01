"""Build and run bounded diagnostic scopes; keep production v36 untouched."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = HERE / "native_profile"
PARENT = BASE / "runtime/scan67_nav2_contract_v36"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert str(ROOT) == "/home/sun/vla_exec/vla"
    identity = json.loads((HERE / "source_identity.json").read_text())
    assert all(sha(PARENT/name)==digest for name,digest in identity["parent_native_source"].items())
    assert all(sha(NATIVE/name)==digest for name,digest in identity["profile_native_source"].items())
    recorded = json.loads((BASE / "versions/v36/recorded_input_manifest.json").read_text())
    assert all(sha(ROOT/name)==row["sha256"] for name,row in recorded.items())
    if not (NATIVE / "build_result.json").exists():
        cache = PARENT / "build_attempt_02"
        for name in ("build", "install"):
            shutil.copytree(cache/name, NATIVE/name, symlinks=True)
        spec = importlib.util.spec_from_file_location("bounded_native_build", BASE / "setup/build_scan_local.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.WORKSPACE, builder.NAME = NATIVE, "vla-local-profile-build"
        builder.main()
    assert json.loads((NATIVE / "build_result.json").read_text())["passed"]
    out = HERE / "tests/attempt01"
    out.mkdir(parents=True)
    shutil.copyfile(__file__, out / "executed_remote_profile.py")
    for path in (HERE/"contract").iterdir():
        if path.is_file():
            shutil.copyfile(path, out/("executed_"+path.name))
    script = "\n".join([
        "set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
        "cmake -S /contract -B /attempt/probe_build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1",
        "cmake --build /attempt/probe_build -j2 >> /attempt/build.log 2>&1",
        "env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 VLA_GEOMETRY_INPUT=/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs VLA_GEOMETRY_OUTPUT=/attempt/geometry_result.json stdbuf -oL /attempt/probe_build/performance_probe --ros-args --params-file /archive/audits/2026-09-29_corridor_entry/v33_stand/inputs/planner.yaml > /attempt/probe.log 2>&1", ""])
    (out/"inside.sh").write_text(script)
    command = ["docker","run","--rm","--pull=never","--platform=linux/amd64","--network=none",
        "--name","vla-local-profile-test01","--cpus=3","--memory=6g","-e","ROS_DOMAIN_ID=216",
        "-e","ROS_LOCALHOST_ONLY=1","-e","OPENBLAS_NUM_THREADS=1","-e","OMP_NUM_THREADS=1",
        "-v",str(NATIVE)+":/workspace:ro","-v",str(BASE)+":/archive:ro",
        "-v",str(HERE/"contract")+":/contract:ro","-v",str(out)+":/attempt:rw",
        "--entrypoint","/bin/bash",IMAGE,"/attempt/inside.sh"]
    (out/"request.json").write_text(json.dumps({"command":command,"deadline_s":600,
        "native_source":identity["profile_native_source"],"recorded_inputs":recorded,
        "driver_sha256":sha(Path(__file__)),"contract_sha256":{p.name:sha(p) for p in (HERE/"contract").iterdir() if p.is_file()},
        "diagnostic_only":True,"physics_run":False},indent=2)+"\n")
    started=time.monotonic();code=127;error=None
    try:
        with (out/"execution.log").open("w") as log:
            code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
    except (OSError,subprocess.TimeoutExpired) as exception:
        error=repr(exception)
    finally:
        removed=subprocess.run(["docker","rm","-f","vla-local-profile-test01"],capture_output=True,text=True,timeout=20)
        names=subprocess.run(["docker","ps","--format","{{.Names}}"],capture_output=True,text=True,timeout=15)
        text=(out/"probe.log").read_text() if (out/"probe.log").exists() else ""
        timings=[{"name":m[0],"calls":int(m[1]),"inclusive_wall_s":float(m[2])} for m in
                 re.findall(r"LOCAL_PROFILE name=(\w+) calls=(\d+) inclusive_wall_s=([\d.e+-]+)",text)]
        original=json.loads((BASE/"versions/v36/tests/attempt09/v33_stand/result.json").read_text())
        actual=json.loads((out/"geometry_result.json").read_text()) if (out/"geometry_result.json").exists() else None
        result={"exit_code":code,"error":error,"wall_s":time.monotonic()-started,
            "timings":timings,"geometry_result_matches_parent":actual==original,
            "source_unchanged":all(sha(NATIVE/name)==digest for name,digest in identity["profile_native_source"].items()),
            "cleanup":{"remove_exit_code":removed.returncode,"confirmed_not_running":names.returncode==0 and "vla-local-profile-test01" not in names.stdout.splitlines()},
            "diagnostic_only":True,"physics_run":False,"profile_overhead_included":True}
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
        files={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.rglob("*")
               if p.is_file() and "probe_build" not in p.parts}
        for name in ("build_result.json","build_request.json","build.log","source_sha256.json","install_sha256.json"):
            files[str((NATIVE/name).relative_to(ROOT))]={"sha256":sha(NATIVE/name),"bytes":(NATIVE/name).stat().st_size}
        (out/"return_manifest.json").write_text(json.dumps(files,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(code)


if __name__=="__main__":main()
