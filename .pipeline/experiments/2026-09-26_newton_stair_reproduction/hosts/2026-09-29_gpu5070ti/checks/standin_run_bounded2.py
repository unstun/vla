"""Stand-in for scripts/run_bounded.py in the runner's round-4 dry tests (port review round 4, N27 and N28).

As in round 3 (standin_run_bounded.py): the episode runs in a new session, nothing but the runner signals it, and
there is no signal handler. Added for round 4: like run_bounded, it prints its record, about 2 KB of JSON, to the
stdout it inherits when the episode ends (N27). Environment variables select the other round-4 cases (N28):
  DRY_SLEEP        the episode's length in seconds (default 3)
  DRY_SPAWN_DELAY  seconds before the episode starts (default 0)
  DRY_IGNORE_TERM  1: the episode ignores SIGTERM, so only SIGKILL ends it
  DRY_HANG         1: after the episode ends and the record is printed, hang instead of exiting
Usage: standin_run_bounded2.py <run directory>."""
import json
import os
import subprocess
import sys
import time

out = sys.argv[1]
os.makedirs(out, exist_ok=False)
time.sleep(float(os.environ.get("DRY_SPAWN_DELAY", "0")))
seconds = os.environ.get("DRY_SLEEP", "3")
command = ["sleep", seconds]
if os.environ.get("DRY_IGNORE_TERM") == "1":
    command = ["bash", "-c", 'trap "" TERM; exec sleep "$1"', "episode", seconds]
process = subprocess.Popen(command, start_new_session=True)
code = process.wait()
record = {"pid": process.pid, "exit_code": code, "padding": "x" * 2000}
with open(os.path.join(out, "process.json"), "w") as f:
    json.dump(record, f)
print(json.dumps(record, indent=2), flush=True)
if os.environ.get("DRY_HANG") == "1":
    time.sleep(3600)
sys.exit(0 if code == 0 else 1)
