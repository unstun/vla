"""Install the chosen release into the experiment-owned virtual environment."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
SETUP = BASE / "setup"
PYTHON = BASE / "runtime/.venv/bin/python"


def main():
    out = SETUP / "install_v1"
    out.mkdir(exist_ok=False)
    environment = os.environ.copy()
    environment.update(UV_CACHE_DIR=str(BASE / "runtime/uv-cache"),
                       XDG_CACHE_HOME=str(BASE / "runtime/cache"),
                       PYTHONDONTWRITEBYTECODE="1")
    commands = [
        ("resolve", ["uv", "pip", "compile", "--python", str(PYTHON), "--generate-hashes",
                     str(SETUP / "requirements.in"), "--output-file", str(SETUP / "requirements.lock")], 300),
        ("install", ["uv", "pip", "sync", "--python", str(PYTHON), "--require-hashes",
                     "--only-binary", ":all:", str(SETUP / "requirements.lock")], 600),
    ]
    records = []
    for name, command, deadline in commands:
        if shutil.disk_usage(BASE).free < 10 * 1024**3:
            raise RuntimeError("experiment disk preflight fell below 10 GiB")
        begin = time.monotonic()
        with (out / (name + ".log")).open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    env=environment, timeout=deadline)
        records.append({"name": name, "command": command, "exit_code": result.returncode,
                        "wall_seconds": time.monotonic() - begin, "deadline_s": deadline})
        (out / "result.json").write_text(json.dumps(records, indent=2) + "\n")
        print(name, result.returncode, flush=True)
        result.check_returncode()


if __name__ == "__main__":
    main()
