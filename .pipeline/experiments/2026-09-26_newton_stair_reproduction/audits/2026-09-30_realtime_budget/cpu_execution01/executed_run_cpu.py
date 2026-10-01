"""Own a single bounded profiler process group and retain every outcome."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
PYTHON=Path("/home/sun/vla_exec/envs/newton_worker/bin/python")


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert str(ROOT)=="/home/sun/vla_exec/vla"
    out=HERE/"cpu_execution01"
    out.mkdir()
    command=[str(PYTHON),str(HERE/"profile_cpu.py")]
    shutil.copyfile(__file__,out/"executed_run_cpu.py")
    shutil.copyfile(HERE/"profile_cpu.py",out/"submitted_profile_cpu.py")
    request={"command":command,"deadline_s":300,"profile_sha256":sha(HERE/"profile_cpu.py"),
        "local_source_of_truth":"/Users/sun/tongbu/study/phdproject/vla","physics_target_s":2.1,"navigation":False}
    (out/"request.json").write_text(json.dumps(request,indent=2)+"\n")
    started=time.monotonic();timed_out=False
    with (out/"execution.log").open("w") as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:exit_code=process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out=True
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
            exit_code=124
    result={"exit_code":exit_code,"timed_out":timed_out,"wall_s":time.monotonic()-started,"pid":process.pid,
        "process_completed":process.poll() is not None,"profile_result_exists":(HERE/"cpu_profile01/result.json").exists()}
    (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    records={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for directory in (out,HERE/"cpu_profile01")
        for p in directory.rglob("*") if p.is_file()}
    (out/"return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(exit_code)


if __name__=="__main__":main()
