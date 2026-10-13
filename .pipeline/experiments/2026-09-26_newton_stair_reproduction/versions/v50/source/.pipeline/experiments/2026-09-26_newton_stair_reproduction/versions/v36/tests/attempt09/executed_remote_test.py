"""Build/run bounded components and recorded native geometry; no physical run."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = BASE / "runtime/scan67_nav2_contract_v36"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--reuse-probe-build-from", type=int)
    args = parser.parse_args()
    out = HERE / f"tests/attempt{args.attempt:02d}"
    out.mkdir(parents=True)
    expected = json.loads((NATIVE / "source_sha256.json").read_text())
    assert all(sha(NATIVE / name) == digest for name, digest in expected.items())
    assert json.loads((NATIVE / "build_result.json").read_text())["passed"]
    fixture_manifest=json.loads((HERE/"recorded_input_manifest.json").read_text())
    assert all(sha(ROOT/name)==entry["sha256"] for name,entry in fixture_manifest.items()), "Recorded input sync mismatch"
    legacy = BASE / "runtime/scan66_periodic_replan_v35"
    legacy_install = json.loads((legacy / "install_sha256.json").read_text())
    assert all(sha(legacy/name)==digest for name,digest in legacy_install.items()), "Parent generated types changed"
    if args.reuse_probe_build_from is not None:
        previous=HERE/f"tests/attempt{args.reuse_probe_build_from:02d}"
        previous_request=json.loads((previous/"request.json").read_text())
        assert previous_request["native_source_sha256"]==expected, "Cannot reuse a build from different native sources"
        shutil.copytree(previous/"probe_build",out/"probe_build",symlinks=True)
    for path in (HERE / "contract").iterdir():
        if path.is_file():
            shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(HERE / "test_backend_contract.py", out / "executed_test_backend_contract.py")
    shutil.copyfile(Path(__file__).resolve(), out / "executed_remote_test.py")
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
        "--name", f"vla-v36-contract-{args.attempt}", "--cpus=3", "--memory=6g",
        "-e", "ROS_DOMAIN_ID=215", "-e", "ROS_LOCALHOST_ONLY=1", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=1",
        "-v", str(NATIVE) + ":/workspace:ro", "-v", str(BASE) + ":/archive:ro",
        "-v", str(BASE/"runtime/scan66_periodic_replan_v35") + ":/legacy:ro",
        "-v", str(HERE) + ":/config:ro", "-v", str(HERE / "contract") + ":/contract:ro",
        "-v", str(out) + ":/attempt:rw", "--entrypoint", "/bin/bash", IMAGE, "/contract/inside.sh"]
    sources = {str(p.relative_to(ROOT)): sha(p) for directory in (HERE / "contract", HERE / "backend_ros")
               for p in directory.rglob("*") if p.is_file()}
    (out / "request.json").write_text(json.dumps({"command":command,"deadline_s":600,"source_sha256":sources,
        "native_source_sha256":expected,"legacy_install_sha256":legacy_install,"recorded_inputs":fixture_manifest,"physics":False,"config":{name:sha(HERE/name) for name in
        ("building_planner.yaml","controller.yaml","navigation_contract.json","test_backend_contract.py")}},indent=2)+"\n")
    started = time.monotonic()
    timed_out, execution_error, cleanup = False, None, {}
    exit_code = 127
    try:
        with (out / "execution.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
            exit_code = result.returncode
    except subprocess.TimeoutExpired as error:
        timed_out, execution_error, exit_code = True, str(error), 124
    except OSError as error:
        execution_error = repr(error)
    finally:
        try:
            removed = subprocess.run(["docker","rm","-f",f"vla-v36-contract-{args.attempt}"],capture_output=True,text=True,timeout=20)
            names = subprocess.run(["docker","ps","--format","{{.Names}}"],capture_output=True,text=True,timeout=15)
            cleanup = {"remove_exit_code":removed.returncode,"remove_stdout":removed.stdout,"remove_stderr":removed.stderr,
                "list_exit_code":names.returncode,"confirmed_not_running":names.returncode==0 and
                f"vla-v36-contract-{args.attempt}" not in names.stdout.splitlines()}
        except (OSError, subprocess.TimeoutExpired) as error:
            cleanup = {"confirmed_not_running":False,"error":repr(error)}
    text = (out / "probe.log").read_text() if (out / "probe.log").exists() else ""
    measured = re.search(r"V36_CONTROLLER_MEASURE samples=(\d+) hz=([\d.]+) max_wall_gap_s=([\d.]+)", text)
    plans = []
    for path in out.glob("*_stand/probe.log"):
        match = re.search(r"V36_NATIVE_PLAN_BUDGET success=(\d+) wall_s=([\d.]+) budget_s=([\d.]+) overrun=(\d+)", path.read_text())
        if match:
            plans.append({"fixture":path.parent.name,"success":bool(int(match[1])),"wall_s":float(match[2]),
                          "budget_s":float(match[3]),"overrun":bool(int(match[4]))})
    backend_text = (out / "backend_tests.log").read_text() if (out / "backend_tests.log").exists() else ""
    evidence = {"exit_code":exit_code,"timed_out":timed_out,"execution_error":execution_error,"cleanup":cleanup,
        "wall_s":time.monotonic()-started,"physics_run":False,"backend_tests_passed":"\nOK\n" in backend_text,
        "native_checks":len(re.findall(r"V36_CHECK .* PASS", text)),"native_passed":"V36_NATIVE_PASSED" in text,
        "controller_measurement":None if measured is None else {"samples":int(measured[1]),"hz":float(measured[2]),"max_wall_gap_s":float(measured[3])},
        "recorded_native_plan_measurements":plans,"local_30hz_full_scene_validated":False,
        "source_unchanged":all(sha(NATIVE/name)==digest for name,digest in expected.items()) and all(sha(ROOT/name)==digest for name,digest in sources.items())}
    (out / "result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    records = {str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.rglob("*")
               if p.is_file() and not p.is_symlink() and "probe_build" not in p.parts}
    (out / "return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(evidence,indent=2),flush=True)
    raise SystemExit(exit_code if exit_code else (0 if cleanup.get("confirmed_not_running") else 1))


if __name__ == "__main__":
    main()
