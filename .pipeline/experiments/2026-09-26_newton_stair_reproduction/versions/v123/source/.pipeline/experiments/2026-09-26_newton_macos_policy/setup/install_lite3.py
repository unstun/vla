"""Add the existing Lite3 adapter's ONNX Runtime without upgrading Newton."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "setup/install_lite3_v1"
OUT.mkdir(exist_ok=False)
env = os.environ.copy()
env["UV_CACHE_DIR"] = str(BASE / "runtime/uv-cache")
records = []
for name, command, deadline in [
    ("resolve", ["/Users/sun/.local/bin/uv", "pip", "compile", "--python", str(BASE / "runtime/.venv/bin/python"),
                 "--generate-hashes", str(BASE / "setup/requirements_lite3.in"), "--output-file",
                 str(BASE / "setup/requirements_lite3.lock")], 300),
    ("install", ["/Users/sun/.local/bin/uv", "pip", "sync", "--python", str(BASE / "runtime/.venv/bin/python"),
                 "--require-hashes", "--only-binary", ":all:", str(BASE / "setup/requirements_lite3.lock")], 600),
]:
    if shutil.disk_usage(BASE).free < 10 * 1024**3:
        raise RuntimeError("Less than 10 GiB free")
    started = time.monotonic()
    with (OUT / (name + ".log")).open("w") as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=deadline)
    records.append({"command": command, "exit_code": result.returncode,
                    "deadline_s": deadline, "wall_s": time.monotonic() - started})
    (OUT / "result.json").write_text(json.dumps(records, indent=2) + "\n")
    result.check_returncode()
    print(name, "passed", flush=True)
