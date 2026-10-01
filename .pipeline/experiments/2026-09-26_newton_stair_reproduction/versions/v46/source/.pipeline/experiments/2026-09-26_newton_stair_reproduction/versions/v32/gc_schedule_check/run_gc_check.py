"""Run K3 (versions/v32/PLAN.md) and judge it: three GC schedules on v31_historical_full01's commands.

Pass conditions, pre-registered in PLAN.md before this ran: with v32's collect_freeze schedule,
(a) no collection after the loop starts, automatic or explicit, lasts longer than 20 ms;
(b) the frozen garbage (collected only after the final unfreeze, once pending garbage has been collected)
    is at most 10% of the freeze-only schedule's (run 02; run 01 counted pending garbage too);
(c) the replayed joint states equal the trial's exactly.
"""
import json
import os
from pathlib import Path
import subprocess
import time

H = Path(__file__).resolve().parent
E = H.parents[2]
PYTHON = E.parent / "2026-09-26_newton_macos_policy/runtime/.venv/bin/python"
TRIAL = E / "runs/v31_historical_full01"


def main():
    containers = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, check=True)
    if containers.stdout.split():
        raise SystemExit("Other containers are running; K3 needs a quiet host")
    record = {"trial": str(TRIAL), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "modes": {}}
    for mode in ("none", "freeze", "collect_freeze"):
        env = dict(os.environ, BENCH_GC_MODE=mode, BENCH_OUT=str(H / mode), BENCH_TRIAL=str(TRIAL),
                   WARP_CACHE_PATH=str(E / "runtime/warp-cache"), NEWTON_CACHE_PATH=str(E / "runtime/assets"),
                   XDG_CACHE_HOME=str(E / "runtime/cache"))
        result = subprocess.run([str(PYTHON), str(H / "bench_gc.py")], env=env, capture_output=True, text=True,
                                timeout=1200)
        (H / f"{mode}_stdout.log").write_text(result.stdout + "\n--- stderr ---\n" + result.stderr)
        if result.returncode != 0:
            raise SystemExit(f"{mode} failed with exit code {result.returncode}")
        record["modes"][mode] = json.loads((H / mode / "summary.json").read_text())
    v32, candidate1 = record["modes"]["collect_freeze"], record["modes"]["freeze"]
    checks = {
        "a_no_collection_over_20ms": v32["longest_collection_in_loop_ms"] <= 20.0,
        "b_frozen_garbage_at_most_10pct_of_freeze_only":
            v32["frozen_garbage"] <= .1 * max(candidate1["frozen_garbage"], 1),
        "c_states_identical": v32["joint_q_worst_error"] == 0.0,
    }
    record.update(checks=checks, passed=all(checks.values()),
                  finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (H / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"checks": checks, "passed": record["passed"],
                      "longest_ms": {m: s["longest_collection_in_loop_ms"] for m, s in record["modes"].items()},
                      "frozen_garbage": {m: s["frozen_garbage"] for m, s in record["modes"].items()},
                      "pending_at_end": {m: s["unfrozen_garbage_pending_at_end"] for m, s in record["modes"].items()},
                      "startup_explicit_ms": {m: s["startup_explicit_collection_ms"] for m, s in record["modes"].items()},
                      "peak_rss_gb": {m: round(s["peak_rss_bytes"] / 1e9, 3) for m, s in record["modes"].items()}}, indent=1))


if __name__ == "__main__":
    main()
