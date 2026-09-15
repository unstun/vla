"""Run one upstream episode with a wall deadline and resource evidence."""

import datetime
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main():
    root = Path(os.environ["TICVLA_TASK_ROOT"])
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = root / "runs" / run_id
    run.mkdir(parents=True)
    command = ["bash", str(root / "work/DynaNav/run_benchmark.sh"),
               str(root / "configs/hospital_single.yaml"), "--run_id", run_id]
    metadata = {"run_id": run_id, "command": command, "cwd": str(root / "work"),
                "deadline_seconds": 1200, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (run / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (root / "runs/latest_run.txt").write_text(run_id + "\n")
    started = time.monotonic()
    timed_out = False
    with (run / "stdout.log").open("w") as stdout, (run / "stderr.log").open("w") as stderr, (run / "resources.jsonl").open("w") as resources:
        process = subprocess.Popen(command, cwd=root / "work", stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        metadata["pid"] = process.pid
        metadata["pgid"] = os.getpgid(process.pid)
        (run / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - started
                sample = {"wall_seconds": elapsed, "time_unix": time.time()}
                try:
                    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
                    sample["gpu_csv"] = gpu.stdout.strip()
                except (subprocess.SubprocessError, OSError) as error:
                    sample["gpu_error"] = str(error)
                sample["meminfo"] = {line.split(":")[0]: line.split(":", 1)[1].strip()
                                     for line in Path("/proc/meminfo").read_text().splitlines()
                                     if line.startswith(("MemAvailable:", "SwapFree:"))}
                resources.write(json.dumps(sample) + "\n")
                resources.flush()
                if elapsed > metadata["deadline_seconds"]:
                    timed_out = True
                    break
                time.sleep(2)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
            # The process group is owned exclusively by this trial, including its child episode.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        metadata.update({"exit_code": process.returncode, "timed_out": timed_out,
                         "wall_seconds": time.monotonic() - started,
                         "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        (run / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)
    return 124 if timed_out else process.returncode


if __name__ == "__main__":
    sys.exit(main())
