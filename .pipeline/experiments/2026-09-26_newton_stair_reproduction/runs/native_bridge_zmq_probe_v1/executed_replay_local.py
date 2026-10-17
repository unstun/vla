"""Execute unchanged recorded-input replay with the local native SCAN build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
BUILD = BASE / "builds/scan33_humble_amd64_v1"
REPAIRS = PROJECT / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/repairs/2026-09-26_sequential"
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=("old_positive", "fresh_live"))
    args = parser.parse_args()
    source = REPAIRS / ({"old_positive": "step13_replay_twist/body_reference_030_twist_fixed_inputs",
                         "fresh_live": "step14_live_input_gap/scan28_live_inputs"}[args.condition])
    out = BASE / "replays" / (args.condition + "_v1")
    out.mkdir(parents=True, exist_ok=False)
    if not json.loads((BUILD / "build_result.json").read_text())["passed"]:
        raise RuntimeError("Native build not qualified")
    for filename in ("source_sha256.json", "install_sha256.json"):
        expected = json.loads((BUILD / filename).read_text())
        if any(sha(BUILD / name) != value for name, value in expected.items()):
            raise ValueError(f"Native identity changed: {filename}")
    shutil.copytree(source, out / "inputs")
    shutil.copyfile(BASE / "references/replay_stair_inputs.py", out / "replay_stair_inputs.py")
    name = "vla-newton-scan33-replay-" + args.condition.replace("_", "-")
    script = "\n".join(["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
                           "python3 /attempt/replay_stair_inputs.py --inputs /attempt/inputs --output /attempt/result", ""])
    (out / "inside.sh").write_text(script)
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
               "--memory=3g", "--cpus=2", "--name", name, "-e", "ROS_DOMAIN_ID=213",
               "-e", "ROS_LOCALHOST_ONLY=1", "-e", "PYTHONDONTWRITEBYTECODE=1",
               "-v", str(BUILD) + ":/workspace:ro", "-v", str(out) + ":/attempt:rw",
               "--entrypoint", "/bin/bash", IMAGE, "/attempt/inside.sh"]
    started = time.monotonic()
    record = {"command": command, "deadline_s": 120, "condition": args.condition,
              "input_manifest_sha256": sha(out / "inputs/input_manifest.json"),
              "build_result_sha256": sha(BUILD / "build_result.json")}
    (out / "request.json").write_text(json.dumps(record, indent=2) + "\n")
    try:
        with (out / "transport.log").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        record["exit_code"] = result.returncode
        result.check_returncode()
        native = json.loads((out / "result/result.json").read_text())
        curves = [r["data"] for r in native["received"] if r["kind"] == "bspline"]
        moving = [c for c in curves if c["pos_pts"] and any(
            sum((p[k] - c["pos_pts"][0][k]) ** 2 for k in ("x", "y", "z")) > .0004 for p in c["pos_pts"])]
        log = (out / "result/scan.log").read_text()
        record.update(completed=native["completed"], moving_curves=len(moving), total_curves=len(curves),
                      checked_seeds=log.count("reactive_stair_seed_checked"),
                      successful_plans=log.count("final_plan_success=1"),
                      output_log_sha256=sha(out / "result/scan.log"))
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=20)
        record["wall_s"] = time.monotonic() - started
        (out / "review.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
