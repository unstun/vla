"""Detached remote batch worker: inference, video packaging, completion metadata."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    identity = sys.argv[1]
    view = sys.argv[2] if len(sys.argv) > 2 else "third_person"
    if view not in ("third_person", "top_down"):
        raise ValueError("Invalid recording view")
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity):
        raise ValueError("Invalid run ID")
    status = {"run_id": identity, "started_unix": time.time(), "done": False}
    target = ROOT / "runs" / f"{identity}.delivery.json"
    target.write_text(json.dumps(status) + "\n")
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts/run_demo.py"), "--offline", "--run-id", identity, "--view", view], check=True)
        meta = json.loads((ROOT / "runs" / identity / "meta.json").read_text())
        if meta["timed_out"] or meta["exit_code"] != 0:
            raise RuntimeError(f"Simulator run failed: {meta}")
        subprocess.run([sys.executable, str(ROOT / "scripts/collect_demo.py"), identity], check=True, timeout=180)
        status.update(done=True, success=True)
    except Exception as error:
        status.update(done=True, success=False, error=str(error))
    finally:
        status["finished_unix"] = time.time()
        target.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status), flush=True)


if __name__ == "__main__":
    main()
