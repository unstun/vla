"""Owned, bounded Docker clock responder for the actual cross-OS probe."""
import json
import os
from pathlib import Path
import subprocess
import sys

base = Path(__file__).resolve().parents[1]
out = Path(os.environ["NEWTON_RUN_DIR"])
name = "vla-newton-" + out.name.replace("_", "-")
command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64",
           "--name", name, "--memory=256m", "--cpus=1",
           "-p", "127.0.0.1:46202:46202", "-v", str(base / "scripts") + ":/scripts:ro",
           "--entrypoint", "/usr/bin/python3",
           "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb",
           "/scripts/clock_sync.py"]
(out / "responder_command.json").write_text(json.dumps(command, indent=2) + "\n")
with (out / "responder.log").open("w") as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    try:
        subprocess.run([sys.executable, str(base / "scripts/probe_clock.py"), "--port", "46202"],
                       check=True, timeout=50)
    finally:
        cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=10)
        process.wait(timeout=10)
        (out / "cleanup.json").write_text(json.dumps({"exit_code": cleanup.returncode,
              "stdout": cleanup.stdout, "stderr": cleanup.stderr}, indent=2) + "\n")
