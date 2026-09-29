"""Stand-in for scripts/run_bounded.py in the runner's dry tests (port review round 3, B7): the same process structure
(the episode in a new session, which run_bounded signals only on its deadline, no signal handler), with `sleep` as
the episode. Usage: standin_run_bounded.py <run directory> <seconds>."""
import json
import os
import subprocess
import sys

out = sys.argv[1]
os.makedirs(out, exist_ok=False)
process = subprocess.Popen(["sleep", sys.argv[2]], start_new_session=True)
code = process.wait()
with open(os.path.join(out, "process.json"), "w") as f:
    json.dump({"pid": process.pid, "exit_code": code}, f)
sys.exit(0 if code == 0 else 1)
