"""Bounded actual cache, Nav2-contract and recorded-geometry checks."""
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
NATIVE = BASE / "runtime/scan70_feasible_window_v47"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--window-only",action="store_true")
    args = parser.parse_args()
    assert str(ROOT) == "/home/sun/vla_exec/vla"
    out = HERE / f"tests/attempt{args.attempt:02d}"
    out.mkdir(parents=True)
    expected = json.loads((NATIVE / "source_sha256.json").read_text())
    assert all(sha(NATIVE/name) == digest for name,digest in expected.items())
    assert json.loads((NATIVE / "build_result.json").read_text())["passed"]
    inputs = json.loads((BASE/"versions/v36/recorded_input_manifest.json").read_text())
    assert all(sha(ROOT/name)==item["sha256"] for name,item in inputs.items())
    sources = {str(p.relative_to(ROOT)):sha(p) for p in (HERE/"contract").iterdir() if p.is_file()}
    for p in (HERE/"contract").iterdir():
        if p.is_file(): shutil.copyfile(p,out/("executed_"+p.name))
    shutil.copyfile(__file__,out/"executed_remote_test.py")
    name = f"vla-v47-contract-{args.attempt}"
    command = ["docker","run","--rm","--pull=never","--platform=linux/amd64","--network=none",
        "--name",name,"--cpus=3","--memory=6g","-e","ROS_DOMAIN_ID=217","-e","ROS_LOCALHOST_ONLY=1",
        "-e","PYTHONDONTWRITEBYTECODE=1","-e","OPENBLAS_NUM_THREADS=1","-e","OMP_NUM_THREADS=1",
        "-v",str(NATIVE)+":/workspace:ro","-v",str(BASE)+":/archive:ro",
        "-v",str(BASE/"versions/v36")+":/config:ro","-v",str(HERE/"contract")+":/contract:ro",
        "-v",str(out)+":/attempt:rw","--entrypoint","/bin/bash",IMAGE,"/contract/inside.sh"]
    if args.window_only:
        command[command.index("--name"):command.index("--name")] = ["-e","V47_WINDOW_ONLY=1"]
    (out/"request.json").write_text(json.dumps({"command":command,"deadline_s":600,
        "source_sha256":sources,"native_source_sha256":expected,"recorded_inputs":inputs,
        "physics_run":False},indent=2)+"\n")
    started=time.monotonic()
    code,error,cleanup=127,None,False
    try:
        with (out/"execution.log").open("w") as log:
            code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600).returncode
    except (OSError,subprocess.TimeoutExpired) as e:
        error=repr(e)
    finally:
        subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=20)
        listed=subprocess.run(["docker","ps","--format","{{.Names}}"],capture_output=True,text=True,timeout=15)
        cleanup=listed.returncode==0 and name not in listed.stdout.splitlines()
    native=(out/"native_probe.log").read_text() if (out/"native_probe.log").exists() else ""
    cache=(out/"cache_probe.log").read_text() if (out/"cache_probe.log").exists() else ""
    inherited=None
    if args.window_only:
        prior=HERE/"tests/attempt06"
        assert json.loads((prior/"request.json").read_text())["native_source_sha256"] == expected
        inherited=json.loads((prior/"result.json").read_text())
        assert inherited["native_passed"] and inherited["cache_passed"] and inherited["source_unchanged"]
    plans=[]
    for state in ("v33_stand","v32_stand"):
        fixture_log=f"{state}_window.log" if args.window_only else f"{state}.log"
        text=(out/fixture_log).read_text() if (out/fixture_log).exists() else ""
        m=re.search(r"V36_NATIVE_PLAN_BUDGET success=(\d+) wall_s=([\d.]+) budget_s=([\d.]+) overrun=(\d+)",text)
        counts=re.search(r"V39_CACHE_COUNTS evaluated=(\d+) hits=(\d+)",text)
        path=out/(f"{state}_window_geometry.json" if args.window_only else f"{state}_geometry.json")
        parent=BASE/f"versions/v36/tests/attempt09/{state}/result.json"
        plans.append({"fixture":state,"measurement":None if not m else {
            "success":bool(int(m[1])),"wall_s":float(m[2]),"budget_s":float(m[3]),"overrun":bool(int(m[4]))},
            "cache_counts":None if not counts else {"evaluated":int(counts[1]),"hits":int(counts[2])},
            "geometry_exact_parent":path.exists() and parent.exists() and json.loads(path.read_text())==json.loads(parent.read_text())})
    result={"exit_code":code,"error":error,"cleanup_confirmed":cleanup,"wall_s":time.monotonic()-started,
        "native_passed":inherited["native_passed"] if inherited else "V36_NATIVE_PASSED" in native,"cache_passed":inherited["cache_passed"] if inherited else "V39_CACHE_PASSED" in cache,
        "native_checks":inherited["native_checks"] if inherited else len(re.findall(r"V36_CHECK .* PASS",native)),
        "cache_checks":inherited["cache_checks"] if inherited else len(re.findall(r"V39_CACHE_CHECK .* PASS",cache)),"plans":plans,
        "source_unchanged":all(sha(NATIVE/n)==h for n,h in expected.items()) and all(sha(ROOT/n)==h for n,h in sources.items()),
        "window_passed":all("V47_WINDOW_PASSED" in (out/f"{state}_window.log").read_text() for state in ("v33_stand","v32_stand") if (out/f"{state}_window.log").exists()) and all((out/f"{state}_window.log").exists() for state in ("v33_stand","v32_stand")),
        "full_scene_30hz_validated":False}
    if inherited:
        result["core_checks_from"]={"path":"tests/attempt06/result.json","sha256":sha(prior/"result.json"),"identical_native_source":True}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    records={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.rglob("*")
             if p.is_file() and not p.is_symlink() and "probe_build" not in p.parts}
    (out/"return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(0 if code==0 and cleanup and result["native_passed"] and result["cache_passed"] and result["window_passed"] and result["source_unchanged"] and all(p["geometry_exact_parent"] for p in plans) else 1)


if __name__ == "__main__":
    main()
