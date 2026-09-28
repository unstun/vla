"""Classify every emergency stop and curve rejection in v30_historical_full01.

Read-only over runs/v30_historical_full01. Writes timeline.json.

Usage: python3 timeline.py <experiment root> <output json>

Clock mapping. ROS log lines carry container wall time (epoch). Applied-command
snapshots carry run_epoch_ns + wall_monotonic_ns together with sim time. The
constant offset between the two wall bases is fitted on the scan.log lines that
print both a wall stamp and `now=<sim>`; the residual is reported.

Scan availability. Each scan is published 0.020 s after its stamp
(`published_at_physics_s` in sensor_manifest.json). The newest scan SCAN could
have processed at a moment is the newest one published by then. `now=` is printed
to 1 ms, so a scan published within 0.5 ms of a printed `now` is undecidable.
"""
import bisect
import collections
import json
import re
import statistics
import sys
from pathlib import Path

base, output = Path(sys.argv[1]), Path(sys.argv[2])
run = base / "runs/v30_historical_full01"
scan_lines = (run / "scan.log").read_text(errors="replace").splitlines()
TS = re.compile(r"^\[[A-Z]+\] \[([0-9]+\.[0-9]+)\]")
TRANSITION = re.compile(r"^\[([A-Z_0-9]+)\]: from (\w+) to (\w+)")

# --- clock mapping -----------------------------------------------------------
snap = [json.loads(l)["snapshot"] for l in (run / "applied_sent.jsonl").open()]
snap_wall = [(s["run_epoch_ns"] + s["wall_monotonic_ns"]) / 1e9 for s in snap]
snap_sim = [s["sim_time_s"] for s in snap]


def sim_from_base(wall):
    i = min(max(bisect.bisect_left(snap_wall, wall), 1), len(snap_wall) - 1)
    a, b = snap_wall[i - 1], snap_wall[i]
    return snap_sim[i - 1] + (snap_sim[i] - snap_sim[i - 1]) * (wall - a) / (b - a) if b > a else snap_sim[i]


pairs = [(float(w), float(s)) for w, s in re.findall(
    r"^\[[A-Z]+\] \[([0-9.]+)\].*now=([0-9.]+)", "\n".join(scan_lines), re.M)]
offset = min((sum(abs(s - sim_from_base(w - o)) for w, s in pairs), o)
             for o in [x / 1000 for x in range(0, 1000)])[1]
residual = [abs(s - sim_from_base(w - offset)) for w, s in pairs]


def sim_at(wall):
    return sim_from_base(wall - offset)


# --- inputs published to SCAN --------------------------------------------------
manifest = json.loads((run / "sensor_manifest.json").read_text())
cloud_stamps = sorted(r["stamp_ns"] / 1e9 for r in manifest)
cloud_gaps = [b - a for a, b in zip(cloud_stamps, cloud_stamps[1:])]
cloud_published = sorted((r["published_at_physics_s"], r["stamp_ns"] / 1e9) for r in manifest)


def newest_published(sim):
    return max(s for p, s in cloud_published if p <= sim)
body_stamps = []
with (run / "artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        record = json.loads(line)
        if record["event"] == "body_pose_observer" and record["clock_ns"] is not None:
            body_stamps.append(record["clock_ns"] / 1e9)
body_positions = {}
with (run / "artifacts/reactive_observations.jsonl").open() as f:
    for line in f:
        record = json.loads(line)
        if record["event"] == "body_pose_observer" and record["clock_ns"] is not None:
            p = record["data"]["pose"]["pose"]["position"]
            body_positions[record["clock_ns"] / 1e9] = (p["x"], p["y"], p["z"])
body_stamps.sort()
body_gaps = [b - a for a, b in zip(body_stamps, body_stamps[1:])]


def body_at(sim):
    return body_positions[body_stamps[max(0, bisect.bisect_right(body_stamps, sim) - 1)]]


def location(xyz):
    # Upper floor walkway: torso origin above 1.80 m (corridor floor 1.558-1.561 m + ~0.3 m).
    if xyz[2] < 1.80:
        return "stairs_and_landings"
    return "corridor_entry" if xyz[0] <= -4.5 else "upper_corridor"

# --- controller receipts: moving curves versus 3.000 s holds --------------------
receipts = [(float(w), int(n), float(d)) for w, n, d in re.findall(
    r"\[([0-9.]+)\] \[closed_loop_controller\]: Received trajectory (\d+), duration ([0-9.]+)s",
    (run / "controller.log").read_text())]
receipt_walls = [r[0] for r in receipts]


def executing_at(wall):
    i = bisect.bisect_right(receipt_walls, wall) - 1
    if i < 0:
        return None
    return {"trajectory": receipts[i][1], "duration_s": receipts[i][2],
            "hold": abs(receipts[i][2] - 3.0) < 1e-6}


# --- scan.log segments (each ends with the transition printed by its callback) --
segments, current, last_wall = [], [], None
for index, line in enumerate(scan_lines, 1):
    m = TS.match(line)
    if m:
        last_wall = float(m.group(1))
    t = TRANSITION.match(line)
    if t:
        segments.append({"line": index, "source": t.group(1), "from": t.group(2), "to": t.group(3),
                         "wall": last_wall, "lines": current})
        current = []
    else:
        current.append((index, last_wall, line))


def window(sim):
    if sim < 36.4:
        return "start_and_stairs"
    if sim < 50.6:
        return "corridor_entry"
    return "upper_corridor"


stops, remaining, final_checks = [], [], []
for seg in segments:
    text = [x[2] for x in seg["lines"]]
    if seg["source"] == "SAFETY" and seg["to"] == "EMERGENCY_STOP":
        lead = [float(x) for x in re.findall(r"emergency stop in ([0-9.]+)s", "\n".join(text))]
        walls = [x[1] for x in seg["lines"] if x[1] is not None]
        sim = sim_at(walls[-1])
        newest = newest_published(sim)
        stops.append({
            "line": seg["line"], "from_state": seg["from"], "wall": walls[-1], "sim_s": round(sim, 4),
            "window": window(sim), "location": location(body_at(sim)), "body": [round(v, 3) for v in body_at(sim)],
            "time_to_collision_s": lead[-1] if lead else None,
            "whole_route_blocked_messages": sum("Target is occupied and no collision-free point" in x for x in text),
            "frontier_found": any("reference_frontier time=" in x for x in text),
            "goal_search_errors": sum("Unable to handle the initial or end point" in x for x in text),
            "min_possible_cloud_age_s": round(sim - newest, 4),
            "executing": executing_at(walls[-1]),
        })
    for index, wall, line in seg["lines"]:
        m = re.search(r"remaining_spline_invalid status=(\d+) raw_t=([-0-9.]+) samples=(\d+)", line)
        if m:
            sim = sim_at(wall)
            remaining.append({"line": index, "wall": wall, "sim_s": round(sim, 4), "window": window(sim),
                              "status": int(m.group(1)), "raw_t": float(m.group(2)),
                              "samples": int(m.group(3)), "executing": executing_at(wall),
                              "closing_transition": f"{seg['source']}:{seg['from']}->{seg['to']}"})
        m = re.search(r"final_spline_rejected status=(\d+) t=([0-9.]+) duration=([0-9.]+) samples=(\d+)", line)
        if m:
            t, d = float(m.group(2)), float(m.group(3))
            final_checks.append({"line": index, "sim_s": round(sim_at(wall), 4), "status": int(m.group(1)),
                                 "t": t, "duration": d, "before_end_s": round(d - t, 4),
                                 "samples": int(m.group(4))})
        m = re.search(r"full_spline_sampled_clear duration=([0-9.]+) samples=(\d+)", line)
        if m:
            final_checks.append({"line": index, "sim_s": round(sim_at(wall), 4), "status": 0,
                                 "duration": float(m.group(1)), "samples": int(m.group(2))})

# Direct age readings printed by the native node.
body_age_readings = [round(float(n) - float(b), 4) for b, n in re.findall(
    r"initial_spline_collision .* body_stamp=([0-9.]+) now=([0-9.]+)", "\n".join(scan_lines))]
cloud_age_readings = [(int(v), round(float(n) - float(c), 4)) for v, n, c in re.findall(
    r"reactive_collision_blocked verdict=(\d+) .* now=([0-9.]+) cloud_stamp=([0-9.]+)", "\n".join(scan_lines))]

# Planning callback length (lower bound): first to last timestamped line of each
# segment closed by a transition out of GEN_NEW_TRAJ or REPLAN_TRAJ.
callbacks = []
for seg in segments:
    walls = [x[1] for x in seg["lines"] if x[1] is not None and TS.match(x[2])]
    if seg["from"] in ("GEN_NEW_TRAJ", "REPLAN_TRAJ") and len(walls) >= 2 and walls[-1] > walls[0]:
        callbacks.append((walls[-1] - walls[0], sim_at(walls[-1]) - sim_at(walls[0]), seg["source"]))


def quantiles(values):
    v = sorted(values)
    q = lambda p: round(v[min(len(v) - 1, int(p * len(v)))], 4)
    return {"median": q(0.5), "p75": q(0.75), "p90": q(0.9), "max": round(v[-1], 4)}


processed_scan_lines = []
for w, n, c in re.findall(r"^\[[A-Z]+\] \[([0-9.]+)\].*reactive_collision_blocked .* now=([0-9.]+) cloud_stamp=([0-9.]+)",
                          "\n".join(scan_lines), re.M):
    now_s, stamp = float(n), float(c)
    newest, maybe = newest_published(now_s - 0.0005), newest_published(now_s + 0.0005 - 1e-9)
    processed_scan_lines.append({"now_s": now_s, "processed_age_s": round(now_s - stamp, 4),
                                 "newest_published_age_s": round(now_s - newest, 4),
                                 "scans_behind": round((newest - stamp) / 0.1) if newest == maybe else None,
                                 "undecidable_at_print_resolution": newest != maybe})
inside_obstacle = {"lines": 0, "followed_by_terminal_in_obstacle": 0, "in_fixed_height_recovery": 0,
                   "segments_with_frontier_found": 0, "segments_with_whole_route_blocked": 0, "segments": 0}
for seg in segments:
    text = [x[2] for x in seg["lines"]]
    idx = [k for k, x in enumerate(text) if "robot is inside an obstacle" in x]
    if not idx:
        continue
    inside_obstacle["segments"] += 1
    inside_obstacle["segments_with_frontier_found"] += any("reference_frontier time=" in x for x in text)
    inside_obstacle["segments_with_whole_route_blocked"] += any("Target is occupied and no collision-free point" in x for x in text)
    for k in idx:
        inside_obstacle["lines"] += 1
        inside_obstacle["followed_by_terminal_in_obstacle"] += any("terminal point is in an obstacle" in x for x in text[k:k + 3])
        j = k
        while j > 0 and "[rebo replan]" not in text[j]:
            j -= 1
        inside_obstacle["in_fixed_height_recovery"] += any("fixed_height_recovery_attempt" in x for x in text[max(0, j - 6):j])

transitions = collections.Counter(f"{s['source']}:{s['from']}->{s['to']}" for s in segments)
status2 = [c for c in final_checks if c["status"] == 2]
status1 = [c for c in final_checks if c["status"] == 1]
summary = {
    "clock_mapping": {"offset_s": offset, "pairs": len(pairs),
                      "residual_median_s": round(statistics.median(residual), 4),
                      "residual_max_s": round(max(residual), 4)},
    "inputs": {
        "cloud_count": len(cloud_stamps),
        "cloud_gap_s": {"median": round(statistics.median(cloud_gaps), 4), "max": round(max(cloud_gaps), 4)},
        "body_pose_count": len(body_stamps),
        "body_gap_s": {"median": round(statistics.median(body_gaps), 4), "max": round(max(body_gaps), 4)},
    },
    "transitions": dict(transitions.most_common()),
    "emergency_stops": {
        "count": len(stops),
        "time_to_collision_values": dict(collections.Counter(s["time_to_collision_s"] for s in stops)),
        "by_from_state": dict(collections.Counter(s["from_state"] for s in stops)),
        "by_window": dict(collections.Counter(s["window"] for s in stops)),
        "by_location": dict(collections.Counter(s["location"] for s in stops)),
        "whole_route_blocked_message_counts": dict(collections.Counter(s["whole_route_blocked_messages"] for s in stops)),
        "with_frontier_found": sum(s["frontier_found"] for s in stops),
        "min_possible_cloud_age_s": {"median": round(statistics.median(s["min_possible_cloud_age_s"] for s in stops), 4),
                                     "max": round(max(s["min_possible_cloud_age_s"] for s in stops), 4)},
        "executing_hold_at_stop": sum(bool(s["executing"] and s["executing"]["hold"]) for s in stops),
    },
    "remaining_curve_invalid": {
        "count": len(remaining),
        "status_values": dict(collections.Counter(r["status"] for r in remaining)),
        "samples_values": dict(collections.Counter(r["samples"] for r in remaining)),
        "executing_hold": sum(bool(r["executing"] and r["executing"]["hold"]) for r in remaining),
        "by_window": dict(collections.Counter(r["window"] for r in remaining)),
    },
    "final_curve_checks": {
        "clear": sum(c["status"] == 0 for c in final_checks),
        "status1": len(status1),
        "status2": len(status2),
        "status2_before_end_s": {"min": min(c["before_end_s"] for c in status2),
                                 "median": statistics.median(c["before_end_s"] for c in status2),
                                 "max": max(c["before_end_s"] for c in status2)},
        "status2_samples_min": min(c["samples"] for c in status2),
        "status1_fraction_of_duration_median": round(statistics.median(c["t"] / c["duration"] for c in status1), 3),
    },
    "planning_callbacks": {
        "count": len(callbacks), "wall_s": quantiles([c[0] for c in callbacks]),
        "sim_s": quantiles([c[1] for c in callbacks]),
        "over_0p1_sim": sum(c[1] > 0.1 for c in callbacks), "over_0p25_sim": sum(c[1] > 0.25 for c in callbacks),
        "planning_timer_only": {
            "count": sum(c[2] == "FSM" for c in callbacks),
            "wall_s": quantiles([c[0] for c in callbacks if c[2] == "FSM"]),
            "sim_s": quantiles([c[1] for c in callbacks if c[2] == "FSM"]),
            "over_0p1_sim": sum(c[1] > 0.1 for c in callbacks if c[2] == "FSM")},
        "safety_timer_only": {
            "count": sum(c[2] != "FSM" for c in callbacks),
            "wall_s": quantiles([c[0] for c in callbacks if c[2] != "FSM"])},
        "astar_time_limit_hits": sum("0.2 second time limit exceeded" in l for l in scan_lines),
    },
    "processed_scan_lag_counts": dict(collections.Counter(
        "undecidable" if l["undecidable_at_print_resolution"] else str(l["scans_behind"]) for l in processed_scan_lines)),
    "processed_scan_age_lines": processed_scan_lines,
    "robot_inside_obstacle": inside_obstacle,
    "emergency_stop_transitions": dict(collections.Counter(
        f"{s['source']}:{s['from']}" for s in segments if s["to"] == "EMERGENCY_STOP")),
    "hold_trajectories_received": sum(r[2] == 3.0 for r in receipts),
    "direct_age_readings": {"body_age_s": body_age_readings,
                            "cloud_age_by_verdict": cloud_age_readings},
}
output.write_text(json.dumps({"summary": summary, "stops": stops, "remaining_curve_invalid": remaining,
                              "final_curve_checks": final_checks}, indent=2) + "\n")
print(json.dumps(summary, indent=2))
