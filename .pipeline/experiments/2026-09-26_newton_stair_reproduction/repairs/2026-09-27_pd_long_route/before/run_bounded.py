"""Run one immutable local experiment process with a recorded deadline."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--deadline", type=float, default=600)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.run_id) or not 0 < args.deadline <= 600:
        parser.error("invalid run identity or deadline")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required")
    out = BASE / "runs" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(NEWTON_CACHE_PATH=str(BASE / "runtime/assets"),
               WARP_CACHE_PATH=str(BASE / "runtime/warp-cache"),
               XDG_CACHE_HOME=str(BASE / "runtime/cache"),
               MPLCONFIGDIR=str(BASE / "runtime/matplotlib"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
               NEWTON_RUN_DIR=str(out))
    record = {"command": command, "deadline_s": args.deadline,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {k: env[k] for k in ("NEWTON_CACHE_PATH", "WARP_CACHE_PATH", "XDG_CACHE_HOME")},
              "claim": "Process evidence only; semantic acceptance requires the run artifacts."}
    (out / "request.json").write_text(json.dumps(record, indent=2) + "\n")
    begin = time.monotonic()
    timed_out = False
    with (out / "run.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env=env, cwd=BASE, start_new_session=True)
        record["pid"] = record["pgid"] = process.pid
        try:
            code = process.wait(timeout=args.deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait(timeout=5)
    record.update(exit_code=code, timed_out=timed_out,
                  wall_seconds=time.monotonic() - begin,
                  child_peak_rss_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                  finished_utc=datetime.now(timezone.utc).isoformat())
    (out / "process.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if timed_out or code != 0:
        raise SystemExit(code if code > 0 else 1)


if __name__ == "__main__":
    main()
