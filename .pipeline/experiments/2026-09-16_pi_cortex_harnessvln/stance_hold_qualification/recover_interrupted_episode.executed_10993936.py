#!/usr/bin/env python3
"""Collect and review a hold-series episode whose remote worker finished after the local driver died (AC4).

The series driver (`run_hold_series.py`) runs the launcher's execute step, which waits on the remote worker over
SSH and then collects. If the local driver is killed after the remote worker has written its final result, the
episode ran but was never collected, reviewed or entered in the ledger. Re-running it instead would drop a finished
outcome, so this script finishes the episode as the launcher would have:

1. check the prepared package hashes (launcher `load_prepared_run`);
2. require the remote `result.json` to be the final write (`last_result_write_phase == "final"`);
3. run the launcher's own remote-only collect sequence (`collect_remote_only`, same commands and log names) and
   write `return_verdict.json` with a `recovered_collect` record;
4. run the same review summary as the driver (`run_isaac_series.summarize`) and append one ledger line marked
   `recovered_after_driver_interrupt`.

It never re-runs physics. The remote worker's stdout (`02_remote_worker.log`) went to the killed SSH session and is
recorded as not captured; the remote `artifacts/logs/` are collected as usual.

    recover_interrupted_episode.py --run-id RUN_ID --episode N --cancel-displacement-m X [--entry-kd xfade1s]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / "scan_fix_qualification"))
sys.path.insert(0, str(EXP / "isaac_runner"))
import run_isaac_series as base  # noqa: E402  (paths set above)
import run_two_goal_pilot as launcher  # noqa: E402


def remote_result(commands):
    remote_run = commands["remote_run"]
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", base.HOST,
                          "cat %s/artifacts/result.json" % remote_run], capture_output=True, text=True, timeout=120)
    if out.returncode:
        raise RuntimeError("cannot read remote result.json: " + out.stderr[-500:])
    return json.loads(out.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--episode", type=int, required=True)
    parser.add_argument("--cancel-displacement-m", type=float, required=True)
    parser.add_argument("--entry-kd", default="xfade1s")
    parser.add_argument("--ledger", type=Path, default=HERE / "hold_series/series_ledger.jsonl")
    args = parser.parse_args()

    local_run, commands = launcher.load_prepared_run(SimpleNamespace(run_id=args.run_id, local_runs_root=base.RUNS))
    request = json.loads((local_run / "run_request.json").read_text())
    expected = {"cancel_displacement_m": args.cancel_displacement_m, "stance_hold": "auto", "stance_entry_kd": args.entry_kd}
    mismatch = {k: request.get(k) for k, v in expected.items() if request.get(k) != v}
    if mismatch or not commands.get("remote_only_bulk"):
        raise SystemExit("prepared package differs from the requested episode: %s remote_only_bulk=%s"
                         % (mismatch, commands.get("remote_only_bulk")))
    if (local_run / "returned_artifacts").exists() or (local_run / "return_verdict.json").exists():
        raise SystemExit("run already has returned artifacts or a verdict; nothing to recover: " + str(local_run))

    result = remote_result(commands)
    if result.get("last_result_write_phase") != "final":
        raise SystemExit("remote result is not final (phase %r); do not recover" % result.get("last_result_write_phase"))

    logs = local_run / "host_logs"
    logs.mkdir(exist_ok=True)
    verdict = {"remote_worker_started": True, "host_wall_seconds": {}, "recovered_collect": {
        "reason": "local series driver killed after the remote worker finished; collected by recover_interrupted_episode.py",
        "remote_result_passed": result.get("passed"),
        "remote_finished_utc": result.get("finished_utc"),
        "remote_worker_stdout_log": "not captured (02_remote_worker.log went to the killed SSH session)",
        "collected_utc": base.utc(),
    }}

    def timed(label, log_name, timeout=1800):
        started = time.monotonic()
        try:
            launcher.run_command(label, commands[label], logs / log_name, timeout=timeout)
        finally:
            verdict["host_wall_seconds"][label] = time.monotonic() - started

    collect_error = launcher.collect_remote_only(commands, timed, verdict, local_run)
    launcher.write_json(local_run / "return_verdict.json", verdict)

    record = {"episode": args.episode, "cancel_displacement_m": args.cancel_displacement_m, "stance_hold": "auto",
              "stance_entry_kd": args.entry_kd, "run_id": args.run_id, "started_utc": None,
              "host_before": None, "recovered_after_driver_interrupt": verdict["recovered_collect"]}
    if collect_error is not None:
        record["outcome"] = "collect_failed"
        record["collect_error"] = str(collect_error)
        ok = False
    elif not verdict.get("returned_hashes_match"):
        record["outcome"] = "collect_failed"
        ok = False
    else:
        try:
            ok = base.summarize(args.run_id, record)
        except Exception as error:  # still leave a ledger line for the lead
            ok = False
            record["outcome"] = "review_error"
            record["review_error"] = repr(error)
    base.finish(args.ledger, record, ok)
    print(json.dumps({k: record.get(k) for k in ("episode", "run_id", "outcome", "checks_passed", "checks_total",
                                                  "failed_checks", "returned_hashes_match", "walk_review_ok")}))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
