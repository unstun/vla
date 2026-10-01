"""Own one bounded device worker; preserve output and cleanup even on failure."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PYTHON = Path("/home/sun/vla_exec/envs/newton_worker/bin/python")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("parent_cpu", "v37_cpu", "v37_cuda", "v38_cuda_solver_graph", "v37_cuda_target_replay", "v38_cuda_solver_graph_target_replay"), required=True)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    assert str(ROOT) == "/home/sun/vla_exec/vla"
    out = HERE / "runs" / f"{args.case}_attempt{args.attempt:02d}"
    out.mkdir(parents=True)
    gpu = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
                         capture_output=True, text=True, timeout=15)
    gpu_state = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=15)
    preflight = {"compute_exit_code": gpu.returncode, "compute_processes": gpu.stdout, "gpu": gpu_state.stdout}
    (out / "host_preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    if args.case not in ("parent_cpu", "v37_cpu") and (gpu.returncode != 0 or gpu.stdout.strip()):
        raise RuntimeError("GPU not verified idle; no worker launched")
    command = [str(PYTHON), str(HERE / "profile_device.py"), "--case", args.case, "--output", str(out)]
    shutil.copyfile(__file__, out / "executed_run_case.py")
    shutil.copyfile(HERE / "profile_device.py", out / "executed_profile_device.py")
    request = {"command": command, "deadline_s": 600, "profile_sha256": sha(HERE / "profile_device.py"),
               "case": args.case, "integration_version": "v38" if args.case.startswith("v38_") else "v37", "navigation": False,
               "simulation_target_s": 4.1, "local_source_of_truth": "/Users/sun/tongbu/study/phdproject/vla"}
    (out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    started = time.monotonic()
    process = None
    timed_out, execution_error, exit_code = False, None, 127
    try:
        with (out / "execution.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                exit_code = process.wait(timeout=600)
            except subprocess.TimeoutExpired:
                timed_out, exit_code = True, 124
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
    except OSError as error:
        execution_error = repr(error)
    finally:
        result = {"exit_code": exit_code, "timed_out": timed_out, "error": execution_error,
                  "wall_s": time.monotonic() - started, "pid": None if process is None else process.pid,
                  "process_completed": process is None or process.poll() is not None,
                  "profile_result_exists": (out / "result.json").exists()}
        (out / "execution_result.json").write_text(json.dumps(result, indent=2) + "\n")
        records = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
                   for p in out.rglob("*") if p.is_file()}
        (out / "return_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
