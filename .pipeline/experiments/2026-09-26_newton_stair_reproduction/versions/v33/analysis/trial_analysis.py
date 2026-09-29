"""v33's trial analysis for one run, as pre-registered in versions/v33/PHYSICAL_RUN_PLAN.md ("What is recorded").

Usage: trial_analysis.py <run directory> <output JSON>. It reads only the run's own records and writes only the
output file. Written before v33's trial and tested on port5070_v33_flat02 (the port's P6 run).

Clocks: backend_body_callbacks.jsonl's entered_ns, the status samples' data.gate.last_measurement.monotonic_s and
data.stop_flow.started_monotonic_s, and the observer's wall_monotonic_ns (artifacts/reactive_observations.jsonl)
are the container's CLOCK_MONOTONIC. applied_sent.jsonl's snapshot.wall_monotonic_ns is the worker's step start,
mapped to that clock by the clock filter. On gpu5070ti the container shares the host's clock.

- Pose wall gaps: intervals over 0.25 s between consecutive body-pose callbacks.
  - Measure 1 (the pose path): the simulated-time advance from the pose before the gap to the newest pose delivered
    within 50 ms after it (evidence/clock_lead_survey.py's method).
  - Measure 2 (independent of the pose path): the physics time of the newest step started by the gap's end, minus
    that of the newest step started by its start (applied_sent.jsonl); resolution one control step (0.02 s).
  - A terminal gap: from the last callback to the stop flow's start or the last step's start, whichever is first,
    when that is over 0.25 s; it has measure 2 only.
  - The flag: either measure over 0.25 s. For each flagged gap, the commands physics received: applied_sent's
    applied command and reason for the steps started inside the gap, telemetry's command and command_reason for
    the same steps, and the observer's gated commands inside the gap.
- Exposure, for each gap:
  1. admitted and open: the newest status sample whose data.gate.last_measurement.monotonic_s is at or before the
     gap's start, if at most 0.5 s older than it, shows data.gate.owner set and data.gate.closed_reason "open";
     with no such sample, "unknown";
  2. no sample shows data.stop_flow.started_monotonic_s at or before the gap's start;
  3. the observer's raw_command and gated_command streams both have no interval over 0.20 s overlapping the gap
     (a stream with no event on either side of the gap cannot show this, and fails).
  A gap failing 2 or 3 is not exposed; one meeting 2 and 3 with 1 unknown is unknown; one meeting all three is
  exposed.
- The gate: the stop flow and terminal results; for an odom_stale end, the trip lag (the stop flow's start minus the
  start of the newest pose gap over 0.25 s that contains it or ended at most 0.1 s before it), its classification
  (at least 2.0 s: the backstop; shorter: the simulation age), and the observer cross-check (the observer's newest
  clock_ns at the stop flow's start minus the stamp of the pose before the gap); with no such gap, "unattributed".
- The status fields odom_time_base, sim_clock_s, last_body_pose_sim_age_s (negative values clamped at 0, as the gate
  does; the raw minimum reported) and last_body_pose_age_s, and their distributions.
- The wall and simulated gaps between body-pose callbacks.
- Watched reasons: heartbeat_stale, initial_heartbeat_missing and applied_evidence_stale in any stop flow or
  terminal result.
"""
import bisect
import collections
import json
from pathlib import Path
import sys

GAP_NS, BURST_NS = 250_000_000, 50_000_000
FLAG_S, ADMIT_WINDOW_S, STREAM_GAP_S, ATTRIBUTION_S, BACKSTOP_S = 0.25, 0.5, 0.20, 0.1, 2.0
WATCHED = ("heartbeat_stale", "initial_heartbeat_missing", "applied_evidence_stale")


def lines(path):
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def longest_gap_over(times, t0, t1):
    """Longest interval between consecutive times that overlaps (t0, t1); None without an event on each side."""
    i = max(bisect.bisect_right(times, t0) - 1, 0)
    best = None
    while i + 1 < len(times) and times[i] < t1:
        if times[i + 1] > t0:
            gap = times[i + 1] - times[i]
            best = gap if best is None else max(best, gap)
        i += 1
    if not times or times[0] > t0 or times[-1] < t1:
        return None
    return best


def quantiles(values):
    if not values:
        return None
    v = sorted(values)
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]
    return {"n": len(v), "min": round(v[0], 4), "p50": round(pick(0.5), 4), "p90": round(pick(0.9), 4),
            "p99": round(pick(0.99), 4), "max": round(v[-1], 4)}


def main():
    run, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    callbacks = list(lines(run / "backend_body_callbacks.jsonl"))
    t = [r["entered_ns"] for r in callbacks]
    s = [r["stamp_ns"] for r in callbacks]
    assert all(a <= b for a, b in zip(t, t[1:])), "callbacks are not in receipt order"

    applied = sorted(((row["snapshot"]["wall_monotonic_ns"], row["snapshot"]["sim_time_s"], row["snapshot"])
                      for row in lines(run / "applied_sent.jsonl")), key=lambda a: a[0])
    aw = [a[0] for a in applied]
    at = [a[1] for a in applied]
    telemetry = {row["state_sequence"]: row for row in lines(run / "telemetry.jsonl")}

    raw, gated, clocked = [], [], []
    for event in lines(run / "artifacts/reactive_observations.jsonl"):
        wall = event.get("wall_monotonic_ns")
        if wall is None:
            continue
        if event.get("event") == "raw_command":
            raw.append(wall)
        elif event.get("event") == "gated_command":
            gated.append((wall, event.get("data")))
        if event.get("clock_ns") is not None:
            clocked.append((wall, event["clock_ns"]))
    raw.sort()
    gated.sort(key=lambda g: g[0])
    gated_t = [g[0] for g in gated]
    clocked.sort()

    samples = []
    for index, row in enumerate(lines(run / "backend_states.jsonl")):
        data = row.get("data") or {}
        gate = data.get("gate") or {}
        measurement = gate.get("last_measurement") or {}
        samples.append({"index": index, "m": measurement.get("monotonic_s"), "owner": gate.get("owner") is not None,
                        "closed_reason": gate.get("closed_reason"), "stop_flow": data.get("stop_flow"),
                        "terminal_results": data.get("terminal_results") or [], "scan_port": data.get("scan_port") or {}})
    timed = sorted((x for x in samples if x["m"] is not None), key=lambda x: (x["m"], x["index"]))
    timed_m = [x["m"] for x in timed]
    stops = [x["stop_flow"] for x in samples if isinstance(x["stop_flow"], dict)]
    stop_start_s = min((f["started_monotonic_s"] for f in stops if f.get("started_monotonic_s") is not None),
                       default=None)
    first_stop = min(stops, key=lambda f: f.get("started_monotonic_s") or float("inf")) if stops else None
    terminal = samples[-1]["terminal_results"] if samples else []

    def physics_at(wall_ns):
        k = bisect.bisect_right(aw, wall_ns) - 1
        return None if k < 0 else at[k]

    def steps_inside(t0, t1):
        return [a[2] for a in applied[bisect.bisect_right(aw, t0):bisect.bisect_right(aw, t1)]]

    def exposure(t0_ns, t1_ns):
        t0 = t0_ns / 1e9
        k = bisect.bisect_right(timed_m, t0 + 1e-6) - 1
        if k >= 0 and t0 - timed[k]["m"] <= ADMIT_WINDOW_S:
            c1 = timed[k]["owner"] and timed[k]["closed_reason"] == "open"
            c1_detail = {"sample_age_s": round(t0 - timed[k]["m"], 4), "owner": timed[k]["owner"],
                         "closed_reason": timed[k]["closed_reason"]}
        else:
            c1, c1_detail = "unknown", None
        c2 = stop_start_s is None or t0 < stop_start_s
        rg, gg = longest_gap_over(raw, t0_ns, t1_ns), longest_gap_over(gated_t, t0_ns, t1_ns)
        c3 = rg is not None and gg is not None and rg <= STREAM_GAP_S * 1e9 and gg <= STREAM_GAP_S * 1e9
        if not c2 or not c3 or c1 is False:
            verdict = "not exposed"
        elif c1 == "unknown":
            verdict = "unknown"
        else:
            verdict = "exposed"
        return {"verdict": verdict, "c1_admitted_open": c1, "c1_sample": c1_detail, "c2_no_stop_flow_before": c2,
                "c3_streams_fresh": c3, "raw_command_gap_s": None if rg is None else round(rg / 1e9, 4),
                "gated_command_gap_s": None if gg is None else round(gg / 1e9, 4)}

    def received(t0_ns, t1_ns):
        steps = steps_inside(t0_ns, t1_ns)
        applied_counts = collections.Counter(
            (json.dumps(x.get("applied_command"), sort_keys=True), x.get("command_reason")) for x in steps)
        telemetry_counts = collections.Counter()
        for x in steps:
            row = telemetry.get(x.get("state_epoch", {}).get("state_sequence"))
            if row is not None:
                telemetry_counts[(json.dumps(row.get("command")), row.get("command_reason"))] += 1
        observed = [g[1] for g in gated[bisect.bisect_right(gated_t, t0_ns):bisect.bisect_right(gated_t, t1_ns)]]
        observed_counts = collections.Counter(json.dumps(g, sort_keys=True) for g in observed)
        return {"steps_started_inside": len(steps),
                "applied": [{"applied_command": json.loads(c), "command_reason": r, "steps": n}
                            for (c, r), n in applied_counts.most_common()],
                "telemetry": [{"command": json.loads(c), "command_reason": r, "steps": n}
                              for (c, r), n in telemetry_counts.most_common()],
                "observer_gated_commands": [{"command": json.loads(c), "events": n}
                                            for c, n in observed_counts.most_common()]}

    gaps = []
    for i in range(len(t) - 1):
        if t[i + 1] - t[i] <= GAP_NS:
            continue
        j, newest = i + 1, s[i + 1]
        while j + 1 < len(t) and t[j + 1] - t[i + 1] <= BURST_NS:
            j += 1
            newest = max(newest, s[j])
        p0, p1 = physics_at(t[i]), physics_at(t[i + 1])
        gaps.append({"t0_s": t[i] / 1e9, "t1_s": t[i + 1] / 1e9, "wall_s": round((t[i + 1] - t[i]) / 1e9, 4),
                     "pose_stamp_before_s": s[i] / 1e9, "terminal": False,
                     "measure1_sim_advance_s": round((newest - s[i]) / 1e9, 4),
                     "measure2_physics_advance_s": None if p0 is None else round(p1 - p0, 4)})
    if t and aw:
        end_ns = aw[-1] if stop_start_s is None else min(aw[-1], round(stop_start_s * 1e9))
        if end_ns - t[-1] > GAP_NS:
            p0, p1 = physics_at(t[-1]), physics_at(end_ns)
            gaps.append({"t0_s": t[-1] / 1e9, "t1_s": end_ns / 1e9, "wall_s": round((end_ns - t[-1]) / 1e9, 4),
                         "pose_stamp_before_s": s[-1] / 1e9, "terminal": True, "measure1_sim_advance_s": None,
                         "measure2_physics_advance_s": None if p0 is None else round(p1 - p0, 4)})
    for g in gaps:
        m1, m2 = g["measure1_sim_advance_s"], g["measure2_physics_advance_s"]
        g["flagged"] = (m1 is not None and m1 > FLAG_S) or (m2 is not None and m2 > FLAG_S)
        g["exposure"] = exposure(round(g["t0_s"] * 1e9), round(g["t1_s"] * 1e9))
        if g["flagged"]:
            g["received"] = received(round(g["t0_s"] * 1e9), round(g["t1_s"] * 1e9))

    cause = None
    if first_stop is not None and first_stop.get("reason") == "odom_stale" and stop_start_s is not None:
        qualifying = [g for g in gaps if g["t0_s"] <= stop_start_s and
                      (g["terminal"] or stop_start_s - g["t1_s"] <= ATTRIBUTION_S)]
        k = bisect.bisect_right(clocked, (round(stop_start_s * 1e9), float("inf"))) - 1
        observer_clock_s = None if k < 0 else clocked[k][1] / 1e9
        if qualifying:
            gap = max(qualifying, key=lambda g: g["t0_s"])
            lag = stop_start_s - gap["t0_s"]
            cause = {"gap_t0_s": gap["t0_s"], "gap_wall_s": gap["wall_s"], "gap_terminal": gap["terminal"],
                     "trip_lag_s": round(lag, 4), "classification": "backstop" if lag >= BACKSTOP_S else "simulation age",
                     "observer_cross_check_s": None if observer_clock_s is None else
                     round(observer_clock_s - gap["pose_stamp_before_s"], 4)}
        else:
            k2 = bisect.bisect_right(t, round(stop_start_s * 1e9)) - 1
            cause = {"classification": "unattributed", "observer_cross_check_s": None if observer_clock_s is None or
                     k2 < 0 else round(observer_clock_s - s[k2] / 1e9, 4)}

    ports = [x["scan_port"] for x in samples if x["scan_port"]]
    sim_ages = [p["last_body_pose_sim_age_s"] for p in ports if p.get("last_body_pose_sim_age_s") is not None]
    wall_ages = [p["last_body_pose_age_s"] for p in ports if p.get("last_body_pose_age_s") is not None]
    sim_clock = [p["sim_clock_s"] for p in ports if p.get("sim_clock_s") is not None]
    reasons = collections.Counter(f.get("reason") for f in stops)
    terminal_causes = collections.Counter(r.get("cause") for r in terminal)
    wall_gaps = [(b - a) / 1e9 for a, b in zip(t, t[1:])]
    sim_gaps = [(b - a) / 1e9 for a, b in zip(s, s[1:])]
    result = {
        "run": run.name,
        "records": {"callbacks": len(t), "status_samples": len(samples), "applied_steps": len(applied),
                    "observer_raw_commands": len(raw), "observer_gated_commands": len(gated),
                    "observer_clock_samples": len(clocked)},
        "stop_flow": None if first_stop is None else {k: first_stop.get(k) for k in ("reason", "intent", "started_monotonic_s")},
        "stop_flow_reasons_seen": dict(reasons),
        "terminal_results": [{k: r.get(k) for k in ("cause", "status", "monotonic_s")} for r in terminal],
        "watched_reasons_seen": {w: reasons.get(w, 0) + terminal_causes.get(w, 0) for w in WATCHED},
        "odom_stale_cause": cause,
        "pose_gaps": {"count": len(gaps), "terminal": sum(g["terminal"] for g in gaps),
                      "flagged": sum(g["flagged"] for g in gaps),
                      "exposure": dict(collections.Counter(g["exposure"]["verdict"] for g in gaps)),
                      "measure1_sim_advance_s": quantiles([g["measure1_sim_advance_s"] for g in gaps
                                                           if g["measure1_sim_advance_s"] is not None]),
                      "measure2_physics_advance_s": quantiles([g["measure2_physics_advance_s"] for g in gaps
                                                               if g["measure2_physics_advance_s"] is not None]),
                      "gaps": gaps},
        "status_fields": {
            "odom_time_base": dict(collections.Counter(p.get("odom_time_base") for p in ports)),
            "sim_clock_s": None if not sim_clock else {"first": sim_clock[0], "last": sim_clock[-1],
                                                       "backward_events_max": max(p.get("sim_clock_backward_events") or 0 for p in ports)},
            "last_body_pose_sim_age_s": None if not sim_ages else dict(quantiles([max(a, 0.0) for a in sim_ages]),
                                                                       raw_min=round(min(sim_ages), 6),
                                                                       negative=sum(a < 0 for a in sim_ages)),
            "last_body_pose_age_s": quantiles(wall_ages)},
        "callback_gaps": {"wall_s": quantiles(wall_gaps), "sim_s": quantiles(sim_gaps),
                          "wall_over_0p25_s": sum(g > 0.25 for g in wall_gaps)},
    }
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    summary = {k: result[k] for k in ("records", "stop_flow", "watched_reasons_seen", "odom_stale_cause")}
    summary["pose_gaps"] = {k: v for k, v in result["pose_gaps"].items() if k != "gaps"}
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
