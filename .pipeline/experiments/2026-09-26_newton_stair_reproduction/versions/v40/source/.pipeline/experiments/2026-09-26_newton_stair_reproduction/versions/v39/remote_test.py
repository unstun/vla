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
NATIVE = BASE / "runtime/scan68_raw_contributor_cache_v39"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
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
    name = f"vla-v39-contract-{args.attempt}"
    command = ["docker","run","--rm","--pull=never","--platform=linux/amd64","--network=none",
        "--name",name,"--cpus=3","--memory=6g","-e","ROS_DOMAIN_ID=217","-e","ROS_LOCALHOST_ONLY=1",
        "-e","PYTHONDONTWRITEBYTECODE=1","-e","OPENBLAS_NUM_THREADS=1","-e","OMP_NUM_THREADS=1",
        "-v",str(NATIVE)+":/workspace:ro","-v",str(BASE)+":/archive:ro",
        "-v",str(BASE/"versions/v36")+":/config:ro","-v",str(HERE/"contract")+":/contract:ro",
        "-v",str(out)+":/attempt:rw","--entrypoint","/bin/bash",IMAGE,"/contract/inside.sh"]
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
    plans=[]
    for state in ("v33_stand","v32_stand"):
        text=(out/f"{state}.log").read_text() if (out/f"{state}.log").exists() else ""
        m=re.search(r"V36_NATIVE_PLAN_BUDGET success=(\d+) wall_s=([\d.]+) budget_s=([\d.]+) overrun=(\d+)",text)
        counts=re.search(r"V39_CACHE_COUNTS evaluated=(\d+) hits=(\d+)",text)
        path=out/f"{state}_geometry.json"
        parent=BASE/f"versions/v36/tests/attempt09/{state}/geometry.json"
        plans.append({"fixture":state,"measurement":None if not m else {
            "success":bool(int(m[1])),"wall_s":float(m[2]),"budget_s":float(m[3]),"overrun":bool(int(m[4]))},
            "cache_counts":None if not counts else {"evaluated":int(counts[1]),"hits":int(counts[2])},
            "geometry_exact_parent":path.exists() and parent.exists() and json.loads(path.read_text())==json.loads(parent.read_text())})
    result={"exit_code":code,"error":error,"cleanup_confirmed":cleanup,"wall_s":time.monotonic()-started,
        "native_passed":"V36_NATIVE_PASSED" in native,"cache_passed":"V39_CACHE_PASSED" in cache,
        "native_checks":len(re.findall(r"V36_CHECK .* PASS",native)),
        "cache_checks":len(re.findall(r"V39_CACHE_CHECK .* PASS",cache)),"plans":plans,
        "source_unchanged":all(sha(NATIVE/n)==h for n,h in expected.items()) and all(sha(ROOT/n)==h for n,h in sources.items()),
        "full_scene_30hz_validated":False}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    records={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.rglob("*")
             if p.is_file() and not p.is_symlink() and "probe_build" not in p.parts}
    (out/"return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(code if code else 0 if cleanup else 1)


if __name__ == "__main__":
    main()
