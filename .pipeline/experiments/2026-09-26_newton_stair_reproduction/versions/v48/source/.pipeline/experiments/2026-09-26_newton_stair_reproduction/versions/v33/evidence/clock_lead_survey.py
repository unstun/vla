"""How far simulated time ran ahead of the backend's newest pose in the recorded runs (review round 1: B2, N1, N5).

Inputs, for every run with runs/<run>/backend_body_callbacks.jsonl (at least 50 callbacks):
- backend_body_callbacks.jsonl: entered_ns (the backend's CLOCK_MONOTONIC at the callback) and stamp_ns;
- artifacts/reactive_observations.jsonl, where present: the in-container observer's events, each with the
  observer's /clock (clock_ns, may be null) and the same VM's CLOCK_MONOTONIC (wall_monotonic_ns). The observer
  subscribes to the bridge's /clock in its own process, so its clock_ns is a proxy for the backend's /clock.
Measures:
1 burst: for each wall gap over 0.25 s between consecutive backend callbacks, the simulated-time advance from the
  pose before the gap to the newest pose delivered within 50 ms after it (the burst that follows a gap). This
  is what a pose gap means in simulated time: while the backend's pose was frozen, physics moved this far.
2 observer lead: at every observer event with a clock, its clock_ns minus the stamp of the newest pose the
  backend had received by then (sample count, maximum, and the maximum outside the named run).
3 command gaps inside pose gaps: for each such pose gap, the longest interval between consecutive observed
  gated commands (the backend's output) and between consecutive raw commands (SCAN's), over the pose gap. A gated
  gap with raw commands still flowing means the backend itself was stalled; the backend's heartbeat check (0.20 s
  of wall time, unchanged by v33) then closes the gate when it resumes, as its timers run before subscriptions.
Added after review round 2, from applied_sent.jsonl where the run has it (the worker's per-step applied snapshot:
wall_monotonic_ns is the step's start mapped to the Linux clock, sim_time_s the physics time at its end):
4 physics advance (N4): for each pose gap, the physics time of the newest step started by the gap's end minus that
  of the newest step started by its start. It does not use the pose path. Resolution: one control step (0.02 s).
5 stopped-simulator margin (N1): for each step whose step-end pose (stamp equal to the snapshot's physics time)
  reached the backend, its receipt minus the step's snapshot stamp. If stepping stops after a step, that pose is
  the newest (nothing supersedes it), and the applied snapshot, whose 2.0 s age the backend checks before the gate,
  is older by this margin, so applied_evidence_stale fires before the pose backstop. Steps whose step-end pose was
  superseded in the bridge by the next step's are counted, not measured: pairing them with an earlier pose
  would understate the margin.
Writes clock_lead_survey.json next to this script.
"""
import bisect
import glob
import json
from pathlib import Path

H = Path(__file__).resolve().parent
E = H.parents[2]
GAP_NS, BURST_NS = 250_000_000, 50_000_000


def longest_gap_over(times, t0, t1):
    """Longest interval between consecutive times that overlaps (t0, t1); None without two events around it."""
    i = max(bisect.bisect_right(times, t0) - 1, 0)
    best = None
    while i + 1 < len(times) and times[i] < t1:
        if times[i + 1] > t0:
            gap = times[i + 1] - times[i]
            best = gap if best is None else max(best, gap)
        i += 1
    return best


def applied_series(run_dir):
    path = run_dir / "applied_sent.jsonl"
    if not path.exists():
        return None
    pairs = []
    for line in open(path):
        if line.strip():
            snapshot = json.loads(line)["snapshot"]
            pairs.append((snapshot["wall_monotonic_ns"], snapshot["sim_time_s"]))
    pairs.sort()
    return ([w for w, _ in pairs], [s for _, s in pairs]) if pairs else None


def main():
    runs, all_gaps = [], []
    margins_all = []
    lead_samples, lead_max, lead_max_run = 0, None, None
    per_run_lead = {}
    for path in sorted(glob.glob(str(E / "runs/*/backend_body_callbacks.jsonl"))):
        rows = [json.loads(line) for line in open(path) if line.strip()]
        if len(rows) < 50:
            continue
        run = Path(path).parent.name
        t = [r["entered_ns"] for r in rows]
        s = [r["stamp_ns"] for r in rows]
        gaps = []
        for i in range(len(rows) - 1):
            if t[i + 1] - t[i] > GAP_NS:
                j, newest = i + 1, s[i + 1]
                while j + 1 < len(rows) and t[j + 1] - t[i + 1] <= BURST_NS:
                    j += 1
                    newest = max(newest, s[j])
                gaps.append({"t0": t[i], "t1": t[i + 1], "wall_s": (t[i + 1] - t[i]) / 1e9,
                             "sim_consecutive_s": (s[i + 1] - s[i]) / 1e9, "sim_with_burst_s": (newest - s[i]) / 1e9})
        applied = applied_series(Path(path).parent)
        if applied is not None:
            aw, at = applied
            for g in gaps:
                k0, k1 = bisect.bisect_right(aw, g["t0"]) - 1, bisect.bisect_right(aw, g["t1"]) - 1
                g["physics_advance_s"] = None if k0 < 0 else round(at[k1] - at[k0], 4)
            index = {stamp_ns: k for k, stamp_ns in enumerate(s)}
            margins, superseded = [], 0
            for w, end in zip(aw, at):
                k = index.get(round(end * 1e9))
                if k is None:
                    superseded += 1
                else:
                    margins.append((t[k] - w) / 1e6)
            margins.sort()
            margins_all += margins
        obs_path = Path(path).parent / "artifacts/reactive_observations.jsonl"
        entry = {"run": run, "callbacks": len(rows), "pose_gaps_over_0p25_s": len(gaps),
                 "max_sim_advance_with_burst_s": round(max((g["sim_with_burst_s"] for g in gaps), default=0.0), 4)}
        if applied is not None:
            entry["max_physics_advance_in_pose_gaps_s"] = max(
                (g["physics_advance_s"] for g in gaps if g.get("physics_advance_s") is not None), default=None)
            entry["stopped_simulator_margin_ms"] = None if not margins else {
                "steps": len(margins), "steps_superseded": superseded, "min": round(margins[0], 1),
                "p1": round(margins[len(margins) // 100], 1), "median": round(margins[len(margins) // 2], 1)}
        if obs_path.exists():
            gated, raw, n, worst = [], [], 0, None
            for line in open(obs_path):
                if not line.strip():
                    continue
                event = json.loads(line)
                wall = event.get("wall_monotonic_ns")
                if event.get("event") == "gated_command":
                    gated.append(wall)
                elif event.get("event") == "raw_command":
                    raw.append(wall)
                if event.get("clock_ns") is None or wall is None:
                    continue
                k = bisect.bisect_right(t, wall) - 1
                if k < 0:
                    continue
                lead = (event["clock_ns"] - s[k]) / 1e9
                n += 1
                worst = lead if worst is None else max(worst, lead)
            gated.sort()
            raw.sort()
            lead_samples += n
            per_run_lead[run] = worst
            if worst is not None and (lead_max is None or worst > lead_max):
                lead_max, lead_max_run = worst, run
            entry["observer_clock_samples"] = n
            entry["observer_max_clock_lead_s"] = None if worst is None else round(worst, 4)
            for g in gaps:
                gg = longest_gap_over(gated, g["t0"], g["t1"])
                rg = longest_gap_over(raw, g["t0"], g["t1"])
                g["gated_command_gap_s"] = None if gg is None else round(gg / 1e9, 4)
                g["raw_command_gap_s"] = None if rg is None else round(rg / 1e9, 4)
            entry["max_gated_command_gap_in_pose_gaps_s"] = max(
                (g["gated_command_gap_s"] for g in gaps if g.get("gated_command_gap_s") is not None), default=None)
            entry["max_raw_command_gap_in_pose_gaps_s"] = max(
                (g["raw_command_gap_s"] for g in gaps if g.get("raw_command_gap_s") is not None), default=None)
            entry["backend_stalls_ge_0p2_s"] = [
                {"pose_gap_s": round(g["wall_s"], 4), "gated_command_gap_s": g["gated_command_gap_s"],
                 "raw_command_gap_s": g["raw_command_gap_s"]}
                for g in gaps if (g.get("gated_command_gap_s") or 0) >= 0.2]
        runs.append(entry)
        all_gaps += [dict(g, run=run) for g in gaps]
    lead_outside = max((v for r, v in per_run_lead.items() if r != lead_max_run and v is not None), default=None)
    summary = {
        "runs": len(runs),
        "pose_gaps_over_0p25_s": len(all_gaps),
        "runs_with_pose_gaps": len({g["run"] for g in all_gaps}),
        "max_sim_advance_consecutive_s": round(max(g["sim_consecutive_s"] for g in all_gaps), 4),
        "max_sim_advance_with_burst_s": round(max(g["sim_with_burst_s"] for g in all_gaps), 4),
        "max_sim_advance_with_burst_run": max(all_gaps, key=lambda g: g["sim_with_burst_s"])["run"],
        "observer_clock_samples": lead_samples,
        "observer_max_clock_lead_s": None if lead_max is None else round(lead_max, 4),
        "observer_max_clock_lead_run": lead_max_run,
        "observer_max_clock_lead_outside_that_run_s": None if lead_outside is None else round(lead_outside, 4),
        "runs_with_backend_stall_ge_0p2_s_in_a_pose_gap": sorted(r["run"] for r in runs if r.get("backend_stalls_ge_0p2_s")),
        "pose_gaps_with_physics_advance": sum(1 for g in all_gaps if g.get("physics_advance_s") is not None),
        "max_physics_advance_in_pose_gaps_s": max((g["physics_advance_s"] for g in all_gaps
                                                   if g.get("physics_advance_s") is not None), default=None),
        "max_physics_advance_run": max((g for g in all_gaps if g.get("physics_advance_s") is not None),
                                       key=lambda g: g["physics_advance_s"], default={}).get("run"),
        "stopped_simulator_margin_ms": None if not margins_all else {
            "steps": len(margins_all), "min": round(min(margins_all), 1),
            "median": round(sorted(margins_all)[len(margins_all) // 2], 1),
            "runs": sum(1 for r in runs if r.get("stopped_simulator_margin_ms"))},
    }
    (H / "clock_lead_survey.json").write_text(json.dumps({"summary": summary, "runs": runs}, indent=2) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
