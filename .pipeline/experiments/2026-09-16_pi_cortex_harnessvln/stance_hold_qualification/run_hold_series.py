#!/usr/bin/env python3
"""Run the stance-hold two-goal Isaac episodes on the 5070 Ti host (task 09-17-isaac-runner-stance-hold, AC4).

Same shape as the SCAN fix series driver, with the hold switched on: for each episode check the host is idle,
prepare a run package, execute it, run review_two_goal.py, and append one ledger line. Any launcher error or
failed review pauses the series (exit 2) for the lead; this script never retries and never skips a check.

It reuses the reviewed helpers of `scan_fix_qualification/run_isaac_series.py` (host probe, ledger, review
summary, run roots) and only changes the episode plan, the run-id prefix and the launcher flags:
`--stance-hold auto --stance-entry-kd <variant>`. The SCAN build (`scan_04`) and `--remote-only-bulk` are the
ones Dr Sun approved for the two-goal pilot.

    run_hold_series.py --lead-authorized-execute [--entry-kd xfade1s] [--from-episode N]
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / "scan_fix_qualification"))
import run_isaac_series as base  # noqa: E402  (path set above)

# AC4: 8 episodes, 6 cancels at 0.40 m, one at 0.45 m, one at 0.50 m.
PLAN = [(1, 0.40), (2, 0.40), (3, 0.40), (4, 0.40), (5, 0.40), (6, 0.40), (7, 0.45), (8, 0.50)]


def run_episode(index, cancel_m, ledger, entry_kd):
    record = {"episode": index, "cancel_displacement_m": cancel_m, "stance_hold": "auto",
              "stance_entry_kd": entry_kd, "started_utc": base.utc()}
    record["host_before"] = base.host_state()
    if not record["host_before"]["ok"]:
        record["outcome"] = "host_not_idle"
        return base.finish(ledger, record, False)
    run_id = datetime.now(timezone.utc).strftime(f"two_goal_%Y%m%dT%H%M%SZ_hold_e{index:02d}")
    record["run_id"] = run_id
    common = [
        sys.executable, str(base.LAUNCHER), "--run-id", run_id,
        "--accepted-scan-build-dir", str(base.BUILD), "--remote-scan-workspace", base.REMOTE_BUILD,
        "--cancel-displacement-m", f"{cancel_m:.2f}", "--remote-only-bulk",
        "--stance-hold", "auto", "--stance-entry-kd", entry_kd,
    ]
    steps = [("prepare", common), ("execute", common + ["--execute", "--lead-authorized-execute"])]
    for label, command in steps:
        start = time.monotonic()
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=base.STEP_TIMEOUT_S)
        except subprocess.TimeoutExpired as error:
            record[label] = {"returncode": None, "timed_out": True, "timeout_s": base.STEP_TIMEOUT_S,
                             "wall_s": round(time.monotonic() - start, 1), "tail": base.tail(error.stdout, error.stderr)}
            record["outcome"] = label + "_timeout"
            return base.finish(ledger, record, False)
        except OSError as error:
            record[label] = {"returncode": None, "wall_s": round(time.monotonic() - start, 1), "error": repr(error)}
            record["outcome"] = label + "_failed"
            return base.finish(ledger, record, False)
        record[label] = {"returncode": proc.returncode, "wall_s": round(time.monotonic() - start, 1),
                         "tail": base.tail(proc.stdout, proc.stderr)}
        if proc.returncode:
            record["outcome"] = label + "_failed"
            return base.finish(ledger, record, False)
    try:
        ok = base.summarize(run_id, record)
    except Exception as error:  # any review problem still leaves a ledger line for the lead
        ok = False
        record["outcome"] = "review_error"
        record["review_error"] = repr(error)
    return base.finish(ledger, record, ok)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", type=Path, default=HERE / "hold_series/series_ledger.jsonl")
    parser.add_argument("--entry-kd", default="xfade1s")
    parser.add_argument("--from-episode", type=int, default=1)
    parser.add_argument("--lead-authorized-execute", action="store_true")
    args = parser.parse_args()
    if not args.lead_authorized_execute:
        print("refusing to run: --lead-authorized-execute is required")
        return 2
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    for index, cancel_m in PLAN:
        if index < args.from_episode:
            continue
        print("== episode %d (cancel %.2f m, entry %s) %s" % (index, cancel_m, args.entry_kd, base.utc()), flush=True)
        if not run_episode(index, cancel_m, args.ledger, args.entry_kd):
            print("== episode %d did not pass; series paused for the lead (ledger %s)" % (index, args.ledger), flush=True)
            return 2
        print("== episode %d passed %s" % (index, base.utc()), flush=True)
    print("== series complete: %d episodes passed" % len([p for p in PLAN if p[0] >= args.from_episode]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
