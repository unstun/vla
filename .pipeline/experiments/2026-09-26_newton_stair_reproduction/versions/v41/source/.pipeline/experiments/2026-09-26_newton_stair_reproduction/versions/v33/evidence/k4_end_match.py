"""K4 of versions/v33/PLAN.md, the wall-base validation matched end by end (added after review round 4, N1).

For every run whose result.json ends on odom_stale (last_backend.stop_flow.reason), the stop flow's start comes from
backend_states.jsonl, and its pose gap from the pre-registered attribution rule (PHYSICAL_RUN_PLAN.md): the newest gap
over 0.25 s between body-pose receipts that contains the start or ended at most 0.1 s before it. The end counts as
reproduced when replay_gate.replay's wall base, the v32 rule, has a stale episode inside that gap. Also reported: the
stale window (the gap less 0.25 s), the delay from the earliest possible trip (the gap's start plus 0.25 s) to the stop
flow's start, and how long after the gap's end a flow started.
Prints JSON and writes nothing; the stored k4_end_match.json was saved from its output.
"""
import glob
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent))
import replay_gate  # noqa: E402

E = replay_gate.E


def odom_stale_end(path):
    result = json.load(open(path))
    return isinstance(result, dict) and ((result.get("last_backend") or {}).get("stop_flow") or {}).get("reason") == "odom_stale"


def main():
    g, c, root = replay_gate.load_green()
    ends = []
    for run in sorted(Path(p).parent.name for p in glob.glob(str(E / "runs/*/result.json")) if odom_stale_end(p)):
        rows = [json.loads(line) for line in open(E / "runs" / run / "backend_body_callbacks.jsonl") if line.strip()]
        wall = [r["entered_ns"] / 1e9 for r in rows]
        stamp = [r["stamp_ns"] / 1e9 for r in rows]
        gaps = [(a, b) for a, b in zip(wall, wall[1:]) if b - a > 0.25]
        flows = []
        for line in open(E / "runs" / run / "backend_states.jsonl"):
            flow = (json.loads(line).get("data") or {}).get("stop_flow") or {} if line.strip() else {}
            if flow.get("reason") == "odom_stale" and flow.get("started_monotonic_s") is not None:
                flows.append(flow["started_monotonic_s"])
        start = min(flows)
        qualifying = [(a, b) for a, b in gaps if a <= start <= b or b <= start <= b + 0.1]
        episodes = replay_gate.replay(g, c, wall, stamp, "wall", "M1")
        entry = {"run": run, "stop_flow_start_s": round(start, 4),
                 "gaps_over_0p25_s": [[round(a, 4), round(b - a, 4)] for a, b in gaps],
                 "wall_base_episodes": [[round(x, 3) for x in e] for e in episodes]}
        if qualifying:
            a, b = max(qualifying)
            inside = [e for e in episodes if e[0] >= a - 1e-9 and e[1] <= b + 1e-9]
            entry.update(trip_gap_start_s=round(a, 4), trip_gap_s=round(b - a, 4),
                         stale_window_ms=round((b - a - 0.25) * 1e3, 1),
                         delay_from_earliest_trip_ms=round((start - a - 0.25) * 1e3, 1),
                         lag_from_gap_start_s=round(start - a, 4),
                         flow_after_gap_end_ms=round((start - b) * 1e3, 1) if start > b else None,
                         episodes_in_trip_gap=inside, reproduced=bool(inside))
        else:
            entry.update(trip_gap_start_s=None, reproduced=False)
        ends.append(entry)
    delays = [e["delay_from_earliest_trip_ms"] for e in ends if e["trip_gap_start_s"] is not None]
    summary = {"odom_stale_ends": len(ends), "reproduced": sum(e["reproduced"] for e in ends),
               "missed": [e["run"] for e in ends if not e["reproduced"]],
               "without_qualifying_gap": [e["run"] for e in ends if e["trip_gap_start_s"] is None],
               "delay_from_earliest_trip_ms": [min(delays), max(delays)],
               "flows_after_gap_end_ms": {e["run"]: e["flow_after_gap_end_ms"] for e in ends if e.get("flow_after_gap_end_ms")}}
    print(json.dumps({"summary": summary, "ends": ends}, indent=2))
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
