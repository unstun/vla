"""Where do the final-check collision rejections of each run fall, and how did curves that passed cross the same cells?

Post-trial analysis for v32's RESULTS.md (not part of v32's change or its pre-registered judge). It reads only SCAN's
own scan.log lines:
- each final check (`final_spline_rejected status=N t=T ...` or `full_spline_sampled_clear`) is paired with the
  preceding `spline_curve_capture {"stage":"minimum_cruise_checked", ...}` line, which holds the checked cubic
  B-spline (controls and a uniform knot vector; its time runs from knot 3 to knot n);
- for a rejection, the curve is evaluated at the logged first-collision time T;
- for every final check, the curve is sampled every 5 ms and each sample is placed in PCT's 0.1 m navigation grid.
The grid geometry and the wrong-height cells come from the v30 stop audit
(audits/2026-09-28_v30_stop_classes/wrong_height_cells.json): cell (47, 41), centred at (-2.345, -4.187), carries only
the 1.4189 m landing layer where the corridor floor is 1.561 m, and v30's 109 reproduced rejections there had their
first colliding sample 0.120-0.135 m above 1.4189 + 0.30 m.
This does not rerun the native check: a rejection "at" a cell only means the logged first-collision time evaluates to a
sample inside it. v30_historical_full01 is included to compare with that audit's replay.
Usage: python3 corridor_entry_curves.py <run> [<run> ...]; writes corridor_entry_curves.json next to this script.
"""
import collections
import json
from pathlib import Path
import re
import sys

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
WRONG = json.loads((E / "audits/2026-09-28_v30_stop_classes/wrong_height_cells.json").read_text())
X0, Y0, RES = -7.095, -8.337, 0.1          # grid corner implied by the audit's cell centres (centre = corner + (i + 0.5) * RES)
LANDING_ONLY = {tuple(c["cell"]): c["layers"][0] for c in WRONG["landing_height_only_cells"]}
KEY = (47, 41)
KEY_X, KEY_Y_ROW = -2.345, (-4.237, -4.137)  # the key cell's centre x and its row's y range
REFERENCE = 1.4189 + 0.30                  # landing layer plus the 0.30 m body clearance, as in the audit
REJECTED = re.compile(r"final_spline_rejected status=(\d+) t=([0-9.]+) duration=([0-9.]+)")


def evaluate(controls, knots, times):
    """Uniform cubic B-spline positions at the given times (time runs from knots[3] to knots[len(controls)])."""
    p, k = np.asarray(controls, dtype=float), np.asarray(knots, dtype=float)
    dt = k[4] - k[3]
    span = np.clip(np.floor((np.asarray(times) - k[3]) / dt).astype(int), 0, len(p) - 4)
    u = (np.asarray(times) - k[3]) / dt - span
    basis = np.stack([(1 - u) ** 3, 3 * u ** 3 - 6 * u ** 2 + 4, -3 * u ** 3 + 3 * u ** 2 + 3 * u + 1, u ** 3], axis=1) / 6
    return np.einsum("nj,njd->nd", basis, np.stack([p[span + j] for j in range(4)], axis=1))


def cell(xy):
    return int(np.floor((xy[0] - X0) / RES)), int(np.floor((xy[1] - Y0) / RES))


def summarize(run):
    lines = (E / "runs" / run / "scan.log").read_text(errors="replace").splitlines()
    capture, rejected, clear, statuses = None, [], [], collections.Counter()
    for line in lines:
        if '"stage":"minimum_cruise_checked"' in line:
            capture = json.loads(line.split("spline_curve_capture ", 1)[1])
            continue
        m = REJECTED.search(line)
        if m:
            statuses[m.group(1)] += 1
        if capture is None or not (m or "full_spline_sampled_clear" in line):
            continue
        duration = float(m.group(3)) if m else None
        knots = capture["knots"]
        end = knots[len(capture["controls"])] - knots[3]
        times = np.arange(0.0, end, 0.005)
        samples = evaluate(capture["controls"], knots, times)
        in_key = [z for (x, y, z) in samples if cell((x, y)) == KEY]
        crossing = np.nonzero(np.diff(np.sign(samples[:, 0] - KEY_X)))[0]
        entry = {"start": [round(v, 3) for v in samples[0]], "duration": round(end, 4),
                 "crosses_key_cell": bool(in_key),
                 "key_cell_max_offset_m": round(max(in_key) - REFERENCE, 4) if in_key else None,
                 "y_at_key_x": round(float(samples[crossing[0], 1]), 3) if len(crossing) else None}
        if m:
            if duration is not None and abs(duration - end) > 1e-3:
                entry["duration_mismatch"] = [duration, end]
            at = evaluate(capture["controls"], knots, [float(m.group(2))])[0]
            c = cell(at[:2])
            entry.update({"status": int(m.group(1)), "t": float(m.group(2)), "first_collision": [round(v, 3) for v in at],
                          "cell": list(c), "landing_only_cell": c in LANDING_ONLY,
                          "offset_above_reference_m": round(at[2] - REFERENCE, 4) if c in LANDING_ONLY else None})
            rejected.append(entry)
        else:
            clear.append(entry)
        capture = None
    collisions = [r for r in rejected if r["status"] == 1]
    at_key = [r for r in collisions if tuple(r["cell"]) == KEY]
    cells = collections.Counter(tuple(r["cell"]) for r in collisions)
    passing = [c for c in clear if c["crosses_key_cell"]]

    def crossing_y(entries):
        ys = [e["y_at_key_x"] for e in entries if e["y_at_key_x"] is not None]
        return {"curves": len(ys), "min": min(ys), "median": float(np.median(ys)), "max": max(ys),
                "in_key_row": sum(KEY_Y_ROW[0] <= y < KEY_Y_ROW[1] for y in ys)} if ys else {"curves": 0}

    near_boundary = [r["first_collision"][0] for r in collisions if tuple(r["cell"]) == (46, 41)]
    # Curves checked from where the robot finally stood (within 0.15 m of the last rejected curve's start), and those
    # whose first colliding sample lies within 0.01 m of the key cell's western edge (x = -2.395) inside its row.
    final = collisions[-1]["start"] if collisions else None
    from_final = [r for r in collisions if np.hypot(r["start"][0] - final[0], r["start"][1] - final[1]) < 0.15] if final else []
    at_edge = [r for r in from_final if abs(r["first_collision"][0] - (KEY_X - RES / 2)) < 0.01
               and KEY_Y_ROW[0] <= r["first_collision"][1] < KEY_Y_ROW[1]]
    return {
        "run": run,
        "final_rejections_by_status": dict(statuses),
        "final_checks_paired": {"rejected": len(rejected), "clear": len(clear)},
        "duration_mismatches": sum("duration_mismatch" in r for r in rejected),
        "collision_rejections": len(collisions),
        "collision_first_sample_cells_top": [{"cell": list(k), "count": n, "landing_only": k in LANDING_ONLY}
                                             for k, n in cells.most_common(6)],
        "collision_first_sample_at_key_cell": len(at_key),
        "key_cell_first_sample_offset_m": ({"min": min(r["offset_above_reference_m"] for r in at_key),
                                            "max": max(r["offset_above_reference_m"] for r in at_key)} if at_key else None),
        "collision_curve_starts_bbox": ({"x": [min(r["start"][0] for r in collisions), max(r["start"][0] for r in collisions)],
                                         "y": [min(r["start"][1] for r in collisions), max(r["start"][1] for r in collisions)]}
                                        if collisions else None),
        "first_sample_x_in_cell_46_41": ({"min": min(near_boundary), "max": max(near_boundary)} if near_boundary else None),
        "final_position": final,
        "collision_rejections_from_final_position": len(from_final),
        "of_which_first_sample_at_key_cell_west_edge": len(at_edge),
        "other_collision_rejections": [{"start": r["start"], "first_collision": r["first_collision"]}
                                       for r in collisions if r not in at_edge],
        "clear_curves": len(clear),
        "y_where_clear_curves_cross_key_x": crossing_y(clear),
        "y_where_rejected_curves_cross_key_x": crossing_y(rejected),
        "clear_curves_crossing_key_x": [{"start": c["start"], "duration": c["duration"], "y_at_key_x": c["y_at_key_x"]}
                                        for c in clear if c["y_at_key_x"] is not None],
        "clear_curves_crossing_key_cell": [{"start": c["start"], "duration": c["duration"],
                                            "key_cell_max_offset_m": c["key_cell_max_offset_m"]} for c in passing],
        "rejected_curves_crossing_key_cell_max_offset_m": (
            {"min": min(r["key_cell_max_offset_m"] for r in rejected if r["crosses_key_cell"]),
             "max": max(r["key_cell_max_offset_m"] for r in rejected if r["crosses_key_cell"])}
            if any(r["crosses_key_cell"] for r in rejected) else None),
    }


def main():
    runs = sys.argv[1:] or ["v30_historical_full01", "diag_v31_clock03", "diag_v31_clock04", "diag_v32_clock01",
                            "v32_historical_full01"]
    report = {"reference_m": REFERENCE, "key_cell": list(KEY), "runs": [summarize(r) for r in runs]}
    (H / "corridor_entry_curves.json").write_text(json.dumps(report, indent=2) + "\n")
    for r in report["runs"]:
        print(json.dumps({k: v for k, v in r.items() if k != "clear_curves_crossing_key_cell"}))
        print("  clear curves crossing", r["run"], r["clear_curves_crossing_key_cell"])


if __name__ == "__main__":
    main()
