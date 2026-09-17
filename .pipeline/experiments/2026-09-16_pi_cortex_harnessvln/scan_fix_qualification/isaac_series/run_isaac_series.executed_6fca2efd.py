#!/usr/bin/env python3
"""Run the scan_04 Isaac episodes one at a time on the 5070 Ti host (task 09-16-scan-terminal-accel-fix-qualification).

For each episode: check the host is idle, prepare a new run package, execute it with the approved flags, run
review_two_goal.py, and append one line to the series ledger. Any launcher error or failed review pauses the series
(exit 2) for the lead to apply PRD D11 by hand; this script never retries and never skips a check.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
LAUNCHER = EXP / "isaac_runner/run_two_goal_pilot.py"
REVIEW = EXP / "p2b_execution/review_two_goal.py"
RUNS = EXP / "isaac_runner/two_goal_runs"
BUILD = EXP / "p2b_execution/builds/scan_04"
REMOTE_BUILD = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04"
HOST = "gpu5070ti"
PORTS = (46240, 46241, 8765, 47631)
# PRD D12: episodes 2-6 at 0.40 m, 7 at 0.45 m, 8 at 0.50 m (episode 1 ran on its own).
PLAN = [(2, 0.40), (3, 0.40), (4, 0.40), (5, 0.40), (6, 0.40), (7, 0.45), (8, 0.50)]
HOST_PROBE = (
    "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits; echo ---; "
    "nvidia-smi --query-compute-apps=pid,name --format=csv,noheader; echo ---; "
    "podman ps --format '{{.Names}}'; echo ---; ss -ltnH"
)


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def host_state():
    out = subprocess.run(["ssh", "-o", "ConnectTimeout=15", HOST, HOST_PROBE], capture_output=True, text=True, timeout=60)
    parts = out.stdout.split("---\n")
    if out.returncode or len(parts) != 4:
        return {"ok": False, "error": (out.stderr or out.stdout)[-500:]}
    gpu, apps, containers, listen = parts
    used = [f":{p}" for p in PORTS if any(line.split()[3].endswith(f":{p}") for line in listen.splitlines() if len(line.split()) > 3)]
    state = {
        "gpu_memory_used_mib": gpu.strip(),
        "compute_apps": [line for line in apps.splitlines() if line.strip()],
        "containers": [line for line in containers.splitlines() if line.strip()],
        "ports_in_use": used,
    }
    state["ok"] = not (state["compute_apps"] or state["containers"] or used)
    return state


def append(ledger, record):
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def summarize(run_id, record):
    """Review a returned run and add its verdict fields to record; True only if every gate passed."""
    run = RUNS / run_id
    proc = subprocess.run([sys.executable, str(REVIEW), str(run), "--output", str(run / "review.json")], capture_output=True, text=True, cwd=REVIEW.parent)
    review = json.loads((run / "review.json").read_text())
    verdict = json.loads((run / "return_verdict.json").read_text())
    stop = review["terminals"][0]
    record.update({
        "review_exit": proc.returncode,
        "checks_passed": sum(review["checks"].values()),
        "checks_total": len(review["checks"]),
        "failed_checks": [k for k, v in review["checks"].items() if not v],
        "cancel_stop_xyz": stop.get("base_xyz"),
        "measured_cancel_displacement_m": stop.get("cancel_displacement_m"),
        "resume_plan_start_xyz": next((p["request"]["start_xyz_m"] for p in review["plan_history"] if p.get("request_id", "").endswith("goal-a-attempt-2")), None),
        "arrival_xy_error_m": [t.get("target_xy_error_m") for t in review["terminals"][1:]],
        "sim_seconds": review["sim_seconds"],
        "episode_wall_seconds": review["wall_seconds"],
        "returned_hashes_match": verdict.get("returned_hashes_match"),
        "walk_review_ok": verdict.get("walk_review", {}).get("ok"),
    })
    for name in ("scan_workspace_gate.json", "scan_workspace_gate_after.json"):
        record[name.replace(".json", "_passed")] = json.loads((run / "returned_artifacts" / name).read_text()).get("passed")
    result = json.loads((run / "returned_artifacts/result.json").read_text())
    record["gpu_peak_mib"] = result.get("gpu_memory", {}).get("peak_memory_used_mib")
    ok = (proc.returncode == 0 and review["passed"] and record["returned_hashes_match"] and record["walk_review_ok"]
          and record["scan_workspace_gate_passed"] and record["scan_workspace_gate_after_passed"])
    record["outcome"] = "passed" if ok else "review_failed"
    return ok


def run_episode(index, cancel_m, ledger):
    record = {"episode": index, "cancel_displacement_m": cancel_m, "started_utc": utc()}
    record["host_before"] = host_state()
    if not record["host_before"]["ok"]:
        record["outcome"] = "host_not_idle"
        append(ledger, record)
        return False
    run_id = datetime.now(timezone.utc).strftime(f"two_goal_%Y%m%dT%H%M%SZ_scanfix_e{index:02d}")
    record["run_id"] = run_id
    common = [
        sys.executable, str(LAUNCHER), "--run-id", run_id,
        "--accepted-scan-build-dir", str(BUILD), "--remote-scan-workspace", REMOTE_BUILD,
        "--cancel-displacement-m", f"{cancel_m:.2f}", "--remote-only-bulk",
    ]
    steps = [("prepare", common), ("execute", common + ["--execute", "--lead-authorized-execute"])]
    for label, command in steps:
        start = time.monotonic()
        proc = subprocess.run(command, capture_output=True, text=True, timeout=2400)
        record[label] = {"returncode": proc.returncode, "wall_s": round(time.monotonic() - start, 1), "tail": (proc.stdout + proc.stderr)[-1500:]}
        if proc.returncode:
            record["outcome"] = label + "_failed"
            append(ledger, record)
            return False
    try:
        ok = summarize(run_id, record)
    except (OSError, KeyError, ValueError) as error:
        ok = False
        record["outcome"] = "review_error"
        record["review_error"] = repr(error)
    record["finished_utc"] = utc()
    append(ledger, record)
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=HERE / "isaac_series/series_ledger.jsonl")
    parser.add_argument("--from-episode", type=int, default=2)
    parser.add_argument("--lead-authorized-execute", action="store_true")
    parser.add_argument("--record-existing", nargs=3, metavar=("RUN_ID", "EPISODE", "CANCEL_M"),
                        help="review an already returned run and append its ledger line; runs nothing on the host")
    args = parser.parse_args()
    if args.record_existing:
        run_id, index, cancel_m = args.record_existing
        record = {"episode": int(index), "cancel_displacement_m": float(cancel_m), "run_id": run_id,
                  "host_before": {"note": "checked by the lead before a separately launched run"}}
        ok = summarize(run_id, record)
        record["recorded_utc"] = utc()
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        append(args.ledger, record)
        print(json.dumps(record, indent=1, sort_keys=True))
        return 0 if ok else 2
    if not args.lead_authorized_execute:
        print(json.dumps({"plan": PLAN, "note": "dry run; pass --lead-authorized-execute to run"}))
        return 0
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    for index, cancel_m in PLAN:
        if index < args.from_episode:
            continue
        print(f"{utc()} episode {index} cancel {cancel_m:.2f} m", flush=True)
        if not run_episode(index, cancel_m, args.ledger):
            print(f"{utc()} episode {index} did not pass; paused for lead review", flush=True)
            return 2
        print(f"{utc()} episode {index} passed", flush=True)
    append(args.ledger, {"series_end_utc": utc(), "host_after": host_state()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
