"""Extract every live candidate rejected with status 1 (collision) in v30_historical_full01.

For each `final_spline_rejected status=1` line, the preceding
`spline_curve_capture {"stage":"minimum_cruise_checked"...}` line holds the
checked curve's controls and knots. Each candidate is assigned to the frozen
state nearest in sim time. Support labels come from the static PCT grounds, so
a support verdict does not depend on which state is used. Occupancy does, so
only candidates whose replayed first collision time matches the logged one are
counted as reproduced.

Usage: python3 extract_live_candidates.py <experiment root> <audit dir>
"""
import bisect, json, re, sys
from pathlib import Path

base, audit = Path(sys.argv[1]), Path(sys.argv[2])
run = base / "runs/v30_historical_full01"
timeline = json.loads((audit / "timeline.json").read_text())
offset = timeline["summary"]["clock_mapping"]["offset_s"]
snap = [json.loads(l)["snapshot"] for l in (run / "applied_sent.jsonl").open()]
W = [(s["run_epoch_ns"] + s["wall_monotonic_ns"]) / 1e9 for s in snap]
S = [s["sim_time_s"] for s in snap]


def sim_at(wall):
    wall -= offset
    i = min(max(bisect.bisect_left(W, wall), 1), len(W) - 1)
    return S[i - 1] + (S[i] - S[i - 1]) * (wall - W[i - 1]) / (W[i] - W[i - 1])


states = {name: json.loads((audit / name / "inputs/input_manifest.json").read_text())["now_ns"] / 1e9
          for name in ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]}
lines = (run / "scan.log").read_text(errors="replace").splitlines()
capture, groups = None, {name: [] for name in states}
for index, line in enumerate(lines, 1):
    if '"stage":"minimum_cruise_checked"' in line:
        capture = json.loads(line.split("spline_curve_capture ", 1)[1])
    m = re.search(r"^\[[A-Z]+\] \[([0-9.]+)\].*final_spline_rejected status=1 t=([0-9.]+) duration=([0-9.]+) samples=(\d+)", line)
    if m and capture is not None:
        sim = sim_at(float(m.group(1)))
        state = min(states, key=lambda s: abs(states[s] - sim))
        groups[state].append({"id": len(groups[state]) + 1, "line": index, "sim_s": round(sim, 4),
                              "state_gap_s": round(sim - states[state], 4), "logged_t": float(m.group(2)),
                              "logged_duration": float(m.group(3)), "logged_samples": int(m.group(4)),
                              "controls": capture["controls"], "knots": capture["knots"]})
        capture = None
for state, items in groups.items():
    (audit / state / "live_candidates.json").write_text(json.dumps(items, indent=2) + "\n")
    with (audit / state / "live_candidates.txt").open("w") as f:
        for c in items:
            flat = [c["id"], len(c["controls"])] + [x for p in c["controls"] for x in p] + [len(c["knots"])] + c["knots"]
            f.write(" ".join(format(float(x), ".17g") for x in flat) + "\n")
    print(state, len(items), "candidates; sim-time gap to state", (min(c["state_gap_s"] for c in items), max(c["state_gap_s"] for c in items)) if items else None)
print("total", sum(len(v) for v in groups.values()))
