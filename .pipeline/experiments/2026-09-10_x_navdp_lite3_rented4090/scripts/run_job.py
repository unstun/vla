"""Run one task-owned command under a process-group deadline with raw logs.

Adapted from .pipeline/experiments/2026-09-08_dualvln_rented4090/scripts/run_job.py.
Layout: <root>/runs/<name>/{stdout.log,stderr.log,process.json,meta.json}.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def utc(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.replace("_", "").replace("-", "").isalnum():
        parser.error("invalid job name")
    root = Path(__file__).resolve().parents[1]
    out = root / "runs" / args.name
    out.mkdir(parents=True, exist_ok=False)
    cmd = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not cmd:
        parser.error("missing command")
    cwd = args.cwd or str(root)
    start = time.time()
    timed_out = False
    with (out / "stdout.log").open("w") as so, (out / "stderr.log").open("w") as se:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=so, stderr=se, start_new_session=True)
        (out / "process.json").write_text(json.dumps({
            "pid": proc.pid, "pgid": os.getpgid(proc.pid), "supervisor_pid": os.getpid(),
            "command": cmd, "cwd": cwd, "started_unix": start, "started_utc": utc(start),
            "deadline_seconds": args.seconds, "hostname": os.uname().nodename,
        }, indent=2) + "\n")
        try:
            code = proc.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                code = proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                code = proc.wait()
    end = time.time()
    meta = {"exit_code": code, "timed_out": timed_out, "wall_seconds": end - start,
            "started_utc": utc(start), "ended_utc": utc(end), "command": cmd, "cwd": cwd}
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta), flush=True)
    sys.exit(code if code >= 0 else 128 - code)


if __name__ == "__main__":
    main()
