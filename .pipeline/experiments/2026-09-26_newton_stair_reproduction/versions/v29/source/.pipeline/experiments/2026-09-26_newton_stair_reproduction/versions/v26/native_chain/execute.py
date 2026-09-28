"""Bounded, receipt-producing execution; reruns require a fresh attempt path."""
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
NATIVE = BASE / "runtime/scan58_body_support_v24"
NAME = "vla-v26-config-native-chain"
assert not (HERE / "execution.json").exists()
command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64",
           "--network=none", "--memory=2g", "--cpus=1", "--name", NAME,
           "-v", str(BASE) + ":/base:ro", "-v", str(NATIVE) + ":/workspace:ro",
           "-v", str(HERE) + ":/audit:rw", "--entrypoint", "/bin/bash",
           "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb",
           "/audit/inside.sh"]
(HERE / "request.json").write_text(json.dumps({"command": command, "deadline_s": 120,
    "purpose": "Actual loader/TCP/native PCT chain regression, no physical movement"}, indent=2) + "\n")
started = time.monotonic()
try:
    with (HERE / "execution.log").open("w") as stream:
        completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    result = {"exit_code": completed.returncode, "wall_s": time.monotonic() - started}
except subprocess.TimeoutExpired:
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True, timeout=15)
    result = {"exit_code": 124, "wall_s": time.monotonic() - started, "timeout": True}
(HERE / "execution.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
raise SystemExit(result["exit_code"])
