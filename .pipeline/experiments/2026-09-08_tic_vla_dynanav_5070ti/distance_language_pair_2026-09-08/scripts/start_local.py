"""Start reusable local UI and its loopback SSH forwarding; no simulator auto-run."""
import json
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def main():
    processes = {}
    for name, port, command in [
        ("tunnel", 18768, [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/tunnel.py")]),
        ("ui", 18765, [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/server.py")])]:
        if not listening(port):
            with (ROOT / f"logs/{name}.log").open("a") as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=log, start_new_session=True)
            processes[name] = child.pid
            for _ in range(40):
                if listening(port):
                    break
                if child.poll() is not None:
                    raise RuntimeError(f"{name} exited; see logs/{name}.log")
                time.sleep(.25)
            if not listening(port):
                raise RuntimeError(f"{name} did not open port {port}")
    with (ROOT / "logs/local_launches.jsonl").open("a") as out:
        out.write(json.dumps({"time_unix": time.time(), "processes": processes}) + "\n")
    print("http://127.0.0.1:18765", processes)


if __name__ == "__main__":
    main()
