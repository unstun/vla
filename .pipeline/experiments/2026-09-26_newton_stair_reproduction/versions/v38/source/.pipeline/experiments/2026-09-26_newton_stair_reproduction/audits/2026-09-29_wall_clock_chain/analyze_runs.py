"""Saved-log analysis of the wall-clock freshness chain in v28-v31 (and diagnostic runs).

Per run, from its own records only:
- control-step wall time (telemetry.jsonl `control_wall_s`, the physics step alone);
- body-pose callback gaps at the Linux backend (backend_body_callbacks.jsonl) over 0.2 s. For each one:
  - producer: the two stamps are consecutive publishes (<= 5.1 ms of sim apart), so the Mac published
    nothing in between;
  - the Mac control step that contains the gap, mapped through the clock filter's offset;
- clock sync (clock_samples.jsonl): rejected observations after convergence, and windows longer than
  the 200 ms TTL without an accepted sample;
- the clock thread's own cadence (gaps between sends over 60 ms);
- for each TTL window: whether a control step over 150 ms overlaps it;
- command transport counters (result.json).
Writes analysis.json beside this script.
"""
import bisect
import json
from pathlib import Path
import statistics
import sys

H = Path(__file__).resolve().parent
E = H.parents[1]
RUNS = sys.argv[1:] or ["v28_historical_full01", "v29_historical_full01", "v30_historical_full01",
                        "v31_historical_full01"]


def lines(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def analyze(name):
    run = E / "runs" / name
    telemetry = [{k: row.get(k) for k in ("state_sequence", "physics_time_s", "control_wall_s", "wall_s",
                                          "command_reason", "stance_mode")} for row in lines(run / "telemetry.jsonl")]
    sent = {s["snapshot"]["state_epoch"]["state_sequence"]: s["snapshot"]["host_step_started_monotonic_ns"]
            for s in lines(run / "applied_sent.jsonl")}
    # Mac monotonic time of the worker's `started`: step start + physics time - wall_s (row written after physics).
    started = statistics.median(sent[r["state_sequence"]] / 1e9 + r["control_wall_s"] - r["wall_s"]
                                for r in telemetry if r["state_sequence"] in sent)
    for r in telemetry:
        r["end_mac_s"] = started + r["wall_s"]
        r["begin_mac_s"] = r["end_mac_s"] - r["control_wall_s"]
    walls = sorted(r["control_wall_s"] for r in telemetry)
    clock = [c for c in lines(run / "clock_samples.jsonl") if "seq" in c]
    accepted = [c for c in clock if c["accepted"]]
    accepted_t = [c["received"] for c in accepted]

    def offset_at(mac_ns):
        index = max(bisect.bisect_right(accepted_t, mac_ns) - 1, 0)
        return accepted[index]["filtered_offset_ns"]

    callbacks = list(lines(run / "backend_body_callbacks.jsonl"))
    gaps = []
    for a, b in zip(callbacks, callbacks[1:]):
        gap = (b["entered_ns"] - a["entered_ns"]) / 1e9
        if gap > .2:
            offset = offset_at(a["entered_ns"] + accepted[-1]["filtered_offset_ns"])
            begin_mac = (a["entered_ns"] + offset) / 1e9
            end_mac = (b["entered_ns"] + offset) / 1e9
            overlapping = [r for r in telemetry if r["begin_mac_s"] < end_mac and r["end_mac_s"] > begin_mac]
            longest = max(overlapping, key=lambda r: r["control_wall_s"]) if overlapping else None
            gaps.append({"linux_s": [a["entered_ns"] / 1e9, b["entered_ns"] / 1e9], "gap_s": gap,
                         "stamps_s": [a["stamp_ns"] / 1e9, b["stamp_ns"] / 1e9],
                         "producer_side": (b["stamp_ns"] - a["stamp_ns"]) <= 5_100_000,
                         "containing_step": None if longest is None else {
                             "state_sequence": longest["state_sequence"], "sim_end_s": longest["physics_time_s"],
                             "control_wall_s": longest["control_wall_s"], "command_reason": longest["command_reason"],
                             "stance_mode": longest["stance_mode"]}})
    converged = [c for c in clock if c["samples"] >= 500 or c["accepted"] is False and c["samples"] >= 500]
    rejected = [c for c in clock if not c["accepted"] and c["samples"] >= 500]
    windows = []
    for a, b in zip(accepted, accepted[1:]):
        if b["received"] - a["received"] > 200_000_000 and a["samples"] >= 500:
            begin, end = a["received"] / 1e9, b["received"] / 1e9
            slow = [r for r in telemetry if r["begin_mac_s"] < end and r["end_mac_s"] > begin and r["control_wall_s"] > .15]
            windows.append({"mac_s": [begin, end], "without_accepted_s": end - begin,
                            "overlapping_steps_over_150ms": [{"state_sequence": r["state_sequence"],
                                                              "control_wall_s": r["control_wall_s"]} for r in slow]})
    cadence = [(b["sent"] - a["sent"]) / 1e6 for a, b in zip(clock, clock[1:])]
    result = json.loads((run / "result.json").read_text()) if (run / "result.json").exists() else {}
    return {
        "run": name, "control_steps": len(telemetry),
        "control_wall_s": {"median": statistics.median(walls), "p90": walls[int(.9 * len(walls))],
                           "p99": walls[int(.99 * len(walls))], "max": walls[-1],
                           "over_0.15": sum(w > .15 for w in walls), "over_0.25": sum(w > .25 for w in walls)},
        "body_callback_gaps_over_0.2s": gaps,
        "clock": {"samples": len(clock), "converged_samples": len(converged), "rejected_after_convergence": len(rejected),
                  "rejected_rtt_ms_median": statistics.median(c["rtt_ns"] / 1e6 for c in rejected) if rejected else None,
                  "windows_over_ttl": windows,
                  "thread_cadence_ms": {"median": statistics.median(cadence), "over_60": sum(g > 60 for g in cadence),
                                        "max": max(cadence)}},
        "command_transport": result.get("command_transport"),
        "final_command_reason": result.get("final_command_reason"),
    }


def main():
    results = [analyze(name) for name in RUNS]
    path = H / ("analysis.json" if len(sys.argv) == 1 else "analysis_" + "_".join(RUNS) + ".json")
    path.write_text(json.dumps(results, indent=2) + "\n")
    for r in results:
        w = r["control_wall_s"]
        print(f"{r['run']}: steps {r['control_steps']} wall median {w['median']*1e3:.0f} ms p99 {w['p99']*1e3:.0f} "
              f"max {w['max']*1e3:.0f} >150ms {w['over_0.15']} >250ms {w['over_0.25']}")
        for g in r["body_callback_gaps_over_0.2s"]:
            s = g["containing_step"]
            print(f"   pose gap {g['gap_s']:.3f} s stamps {g['stamps_s'][0]:.4f}->{g['stamps_s'][1]:.4f} "
                  f"producer_side={g['producer_side']} step={s and (s['state_sequence'], round(s['control_wall_s'], 3), s['command_reason'], s['stance_mode'])}")
        c = r["clock"]
        print(f"   clock rejected {c['rejected_after_convergence']} (median rtt {c['rejected_rtt_ms_median']}), "
              f"TTL windows {len(c['windows_over_ttl'])}, cadence max {c['thread_cadence_ms']['max']:.0f} ms, "
              f"transport {r['command_transport'] and (r['command_transport']['reconnects'], r['command_transport']['protocol_errors'], r['command_transport']['last_protocol_error'])}")
        for wdw in c["windows_over_ttl"]:
            print(f"      TTL window {wdw['without_accepted_s']*1e3:.0f} ms; steps >150 ms overlapping: "
                  f"{[(s['state_sequence'], round(s['control_wall_s'], 3)) for s in wdw['overlapping_steps_over_150ms']]}")


if __name__ == "__main__":
    main()
