"""Run one host-contention condition of the physics replay benchmark.

Conditions:
  alone            no container may run; the Mac physics process runs by itself.
  container_load4  the pinned planner image (linux/amd64, as in the trials) runs four busy loops under
                   --cpus=4, the trials' container CPU limit. This is a worst-case stand-in for the planner
                   container's load, not a reproduction of it.
Every condition also runs the external lateness probe and samples host load once per second.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

H = Path(__file__).resolve().parent
E = H.parents[1]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
PYTHON = E.parent / "2026-09-26_newton_macos_policy/runtime/.venv/bin/python"
LOAD_NAME = "vla-v32-diag-load"


def running_containers():
    names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, check=True)
    return [name for name in names.stdout.split() if name]


def sample_host(path, stop):
    with open(path, "w") as f:
        while not stop.is_set():
            top = subprocess.run(["ps", "-Ao", "pcpu,comm", "-r"], capture_output=True, text=True).stdout.splitlines()[1:9]
            f.write(json.dumps({"monotonic_ns": time.monotonic_ns(), "loadavg": os.getloadavg(),
                                "top": [line.strip() for line in top]}) + "\n")
            f.flush()
            stop.wait(1.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=("alone", "container_load4"))
    parser.add_argument("--trial", default=str(E / "runs/v31_historical_full01"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--steps", type=int, default=0)
    args = parser.parse_args()
    out = H / "bench" / args.name
    out.parent.mkdir(exist_ok=True)
    before = running_containers()
    if before:
        raise SystemExit(f"Other containers are running: {before}")
    record = {"condition": args.condition, "trial": args.trial, "containers_before": before,
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if args.condition == "container_load4":
        subprocess.run(["docker", "run", "-d", "--rm", "--pull=never", "--platform=linux/amd64", "--cpus=4",
                        "--name", LOAD_NAME, "--entrypoint", "/bin/bash", IMAGE, "-c",
                        "for i in 1 2 3 4; do (while :; do :; done) & done; wait"], check=True, capture_output=True)
        time.sleep(3)
        record["load_container"] = {"name": LOAD_NAME, "image": IMAGE, "cpus": 4, "busy_loops": 4}
    stop = threading.Event()
    sampler = threading.Thread(target=sample_host, args=(H / "bench" / f"{args.name}_host.jsonl", stop), daemon=True)
    sampler.start()
    probe = subprocess.Popen([sys.executable, str(H / "probe_latency.py"), str(H / "bench" / f"{args.name}_probe_out.npy")])
    env = dict(os.environ, BENCH_OUT=str(out), BENCH_TRIAL=args.trial, BENCH_STEPS=str(args.steps),
               WARP_CACHE_PATH=str(E / "runtime/warp-cache"), NEWTON_CACHE_PATH=str(E / "runtime/assets"),
               XDG_CACHE_HOME=str(E / "runtime/cache"))
    started = time.monotonic()
    try:
        result = subprocess.run([str(PYTHON), str(H / "bench_physics.py")], env=env, capture_output=True, text=True,
                                timeout=1200)
        record["exit_code"] = result.returncode
        (H / "bench" / f"{args.name}_stdout.log").write_text(result.stdout + "\n--- stderr ---\n" + result.stderr)
    finally:
        record["wall_s"] = time.monotonic() - started
        probe.terminate()
        probe.wait(timeout=10)
        stop.set()
        sampler.join(timeout=5)
        if args.condition == "container_load4":
            subprocess.run(["docker", "stop", "-t", "1", LOAD_NAME], capture_output=True)
        record["containers_after"] = running_containers()
        record["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (H / "bench" / f"{args.name}_run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
