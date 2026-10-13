"""Run the authorized bounded v47 Building experiment and return original evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
PYTHON = "/home/sun/vla_exec/envs/newton_worker/bin/python"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert str(ROOT) == "/home/sun/vla_exec/vla"
    parser=argparse.ArgumentParser()
    parser.add_argument("--attempt",type=int,default=1)
    args=parser.parse_args()
    run=f"v47_realtime_trial{args.attempt:02d}"
    output = HERE / f"trials/attempt{args.attempt:02d}"
    output.mkdir(parents=True)
    os.environ["PATH"] = "/home/sun/vla_exec/bin:" + os.environ["PATH"]
    containers = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=20)
    ports = subprocess.run(["ss", "-ltnH", "( sport >= :46200 and sport <= :46203 )"], capture_output=True, text=True, timeout=15)
    gpu = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"], capture_output=True, text=True, timeout=15)
    preflight = {"containers":containers.stdout,"containers_exit_code":containers.returncode,
                 "ports":ports.stdout,"ports_exit_code":ports.returncode,
                 "gpu_processes":gpu.stdout,"gpu_exit_code":gpu.returncode}
    (output / "preflight.json").write_text(json.dumps(preflight,indent=2)+"\n")
    assert containers.returncode==0 and not containers.stdout.strip()
    assert ports.returncode==0 and not ports.stdout.strip()
    assert gpu.returncode==0 and not gpu.stdout.strip()
    command = [PYTHON,str(BASE/"scripts/run_bounded.py"),"--run-id",run,"--deadline","360","--",
        PYTHON,str(BASE/"versions/v47/run_local_episode.py"),"--backend-executor","single",
        "--applied-transport","zmq","--geometry-obstacles","--scene","building_full",
        "--building-route","historical_full","--goal-wall-budget","180",
        "--startup-mode","factory_pd","--stance-hold","--integration-version","v47",
        "--real-time-factor","1","--recording-sim-seconds","90"]
    (output/"request.json").write_text(json.dumps({"command":command,"local_source_of_truth":"/Users/sun/tongbu/study/phdproject/vla",
        "deadline_s":360,"source_sha256":sha(Path(__file__)),"integration_manifest_sha256":sha(BASE/"versions/v47/manifest.json"),
        "goal":"Measure actual local planning frequency and physical progress with Candidate 1; same v45 Building profile and control settings; bounded run does not imply route acceptance"},indent=2)+"\n")
    started=time.monotonic()
    code,error=127,None
    try:
        with (output/"execution.log").open("w") as log:
            code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=380).returncode
    except (OSError,subprocess.TimeoutExpired) as exception:
        error=repr(exception)
    name="vla-newton-"+run.replace("_","-")
    # Exact owned name; the original runner has already preserved its tmpfs state.
    subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=20)
    listed=subprocess.run(["docker","ps","--format","{{.Names}}"],capture_output=True,text=True,timeout=20)
    evidence={"exit_code":code,"error":error,"wall_s":time.monotonic()-started,
        "owned_container_not_running":listed.returncode==0 and name not in listed.stdout.splitlines()}
    (output/"result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    paths=[p for directory in (output,BASE/"runs"/run) for p in directory.rglob("*") if p.is_file()]
    records={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in paths}
    (output/"return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(evidence,indent=2),flush=True)
    raise SystemExit(code)


if __name__ == "__main__": main()
