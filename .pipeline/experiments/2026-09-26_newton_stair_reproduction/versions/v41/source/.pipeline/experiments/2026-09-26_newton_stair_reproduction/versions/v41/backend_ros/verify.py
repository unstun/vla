"""Local CPU verification for backend_ros."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time


ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
ADAPTER = ROOT.parent / "backend_adapter"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(label, command, env=None):
    started = time.monotonic()
    proc = subprocess.run(command, cwd=str(REPO), capture_output=True, text=True, env=env)
    return {
        "label": label,
        "command": command,
        "returncode": proc.returncode,
        "elapsed_s": time.monotonic() - started,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    py = sys.executable
    env = dict(**__import__("os").environ)
    env["PYTHONPATH"] = str(ROOT) + ":" + str(ADAPTER) + ":" + env.get("PYTHONPATH", "")
    commands = [
        ("compile", [py, "-m", "compileall", "-q", str(ROOT / "p2b_backend_ros"), str(ROOT / "tests")]),
        ("tests", [py, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"]),
        ("contract", [py, "-m", "p2b_backend_ros.node", "--config", str(ROOT / "config/p2b_backend_ros.example.json"), "--print-contract"]),
    ]
    results = [run(label, command, env=env) for label, command in commands]
    owned = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and "checks" not in path.parts
    }
    output = {
        "schema": "p2b_backend_ros_verify_v1",
        "ok": all(item["returncode"] == 0 for item in results),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commands": results,
        "owned_files": len(owned),
        "owned_sha256": owned,
        "claim": "CPU source/schema tests only; no ROS graph, PCT worker, Isaac or robot execution.",
    }
    checks = ROOT / "checks"
    checks.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = checks / ("verify_%s.json" % stamp)
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (checks / "latest_verify.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
