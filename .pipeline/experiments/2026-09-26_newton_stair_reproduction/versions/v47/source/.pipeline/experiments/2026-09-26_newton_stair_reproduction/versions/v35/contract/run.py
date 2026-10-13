"""Bound the real native-FSM red/green contract in the cached networkless image."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import argparse
import json
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
VERSION = HERE.parent
BASE = VERSION.parents[1]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def hashes(root):
    expected = json.loads((root / "source_sha256.json").read_text())
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in expected}
    assert actual == expected
    return actual


def execute(label, native, legacy, attempt):
    suffix = f"{attempt:02d}"
    out = HERE / ("attempt_" + label + suffix)
    out.mkdir()
    before = hashes(native)
    name = "vla-v35-periodic-" + label + suffix
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
               "--cpus=3", "--memory=6g", "--name", name,
               "-e", "ROS_LOCALHOST_ONLY=1", "-e", "ROS_DOMAIN_ID=232",
               "-e", "V35_LEGACY_PARENT=" + ("ON" if legacy else "OFF"),
               "-v", str(native) + ":/workspace:ro", "-v", str(HERE) + ":/contract:ro",
               "-v", str(out) + ":/attempt:rw",
               "-v", str(VERSION / "building_planner.yaml") + ":/config/planner.yaml:ro",
               "-v", str(VERSION / "parent_source/building_planner.yaml") + ":/config/parent.yaml:ro",
               "--entrypoint", "/bin/bash", IMAGE, "/contract/inside.sh"]
    result = {"command": command, "started_utc": datetime.now(timezone.utc).isoformat(),
              "deadline_s": 900, "passed": False, "scope": "Compiled native FSM; no physics or actuation"}
    result["test_source_sha256"] = {}
    for path in (HERE / "CMakeLists.txt", HERE / "periodic_probe.cpp", HERE / "inside.sh"):
        raw = path.read_bytes()
        (out / ("executed_" + path.name)).write_bytes(raw)
        result["test_source_sha256"][path.name] = hashlib.sha256(raw).hexdigest()
    (out / "request.json").write_text(json.dumps(result, indent=2) + "\n")
    begin = time.monotonic()
    try:
        with (out / "execution.log").open("w") as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        result["exit_code"] = completed.returncode
        result["source_unchanged"] = hashes(native) == before
        result["checks_by_log"] = {
            p.name: sorted(set(re.findall(r"^V35_CHECK (\w+) PASS$", p.read_text(errors="replace"), re.M)))
            for p in out.glob("*.log") if p.name not in {"build.log", "execution.log"}}
        expected_logs = {"probe.log"} if legacy else {
            "probe.log", "omitted_frequency.log", "invalid_-1.log", "invalid_nan.log", "invalid_inf.log",
            "invalid_101.log", "invalid_1e-310.log"}
        result["passed"] = (completed.returncode == 0 and result["source_unchanged"] and
                            set(result["checks_by_log"]) == expected_logs and
                            all(result["checks_by_log"].values()))
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
    finally:
        cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=20)
        result["cleanup"] = {"exit_code": cleanup.returncode, "stderr": cleanup.stderr}
        result["wall_s"] = time.monotonic() - begin
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"label": label, **result}, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1, choices=range(1, 10))
    args = parser.parse_args()
    green = execute("green", BASE / "runtime/scan66_periodic_replan_v35", False, args.attempt)
    if not green["passed"]:
        raise SystemExit(1)
    red = execute("red", BASE / "runtime/scan65_evidence_floor_v34", True, args.attempt)
    result = {"passed": green["passed"] and red["passed"],
              "parent_reproduces_missing_trigger": "parent_reproduces_missing_early_trigger" in red["checks_by_log"].get("probe.log", []),
              "candidate_checks": green["checks_by_log"], "physics_run": False}
    (HERE / "contract_results.json").write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
