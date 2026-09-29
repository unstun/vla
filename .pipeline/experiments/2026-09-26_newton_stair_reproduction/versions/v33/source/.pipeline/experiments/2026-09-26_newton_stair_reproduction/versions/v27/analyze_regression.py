"""Independent curve algebra and a real blocked-shortcut manager control."""
import json
from pathlib import Path
import re

import numpy as np
from scipy.interpolate import BSpline

BASE = Path(__file__).resolve().parents[2]
RUN = BASE / "runs/v27_native_regression01"
OLD = BASE / "runs/v24_native_regression01"


def blocks(text):
    result = []
    for block in re.split(r"\[rebo replan\]:[^\n]*\n", text)[1:]:
        seeds = [json.loads(line.split("spline_seed_capture ", 1)[1])
                 for line in block.splitlines() if "spline_seed_capture " in line]
        if not seeds:
            continue
        node_count = int(re.search(r"upstream_arclength_seed nodes=(\d+)", block).group(1))
        curves = [json.loads(line.split("spline_curve_capture ", 1)[1])
                  for line in block.splitlines() if "spline_curve_capture " in line]
        result.append({"seed": seeds[0], "nodes": node_count, "curves": curves,
                       "shortcut": "verified_direct_seed_shortcut" in block,
                       "accepted": "full_spline_sampled_clear" in block})
    return result


negative = []
for name in ("v23", "v23_repeat"):
    outcome = json.loads((RUN / (name + ".json")).read_text())
    assert outcome["start_occupied"] == outcome["target_occupied"] == 0
    assert outcome["straight_clear"] is False
    current = blocks((RUN / (name + ".log")).read_text())
    previous = blocks((OLD / (name + ".log")).read_text())
    assert current and all(row["nodes"] > 2 and not row["shortcut"] for row in current)
    matches = []
    for row in current:
        equivalent = [i for i, old in enumerate(previous) if row["seed"] == old["seed"]]
        assert equivalent
        matches.append(equivalent)
    assert current[-1]["accepted"]
    negative.append({"case": name, "start_and_target_free": True,
        "direct_segment_blocked": True, "actual_manager_retained_original_seed": True,
        "node_counts": [row["nodes"] for row in current], "old_seed_matches": matches})

positive = []
curves = []
for name in ("v26", "v26_repeat"):
    attempts = blocks((RUN / (name + ".log")).read_text())
    assert any(row["shortcut"] and not row["accepted"] for row in attempts)
    accepted = [row for row in attempts if row["accepted"]]
    assert len(accepted) == 1 and accepted[0]["shortcut"]
    row = accepted[0]
    curve = row["curves"][-1]
    curves.append(curve)
    assert curve["stage"] == "minimum_cruise_checked"
    spline = BSpline(np.asarray(curve["knots"]), np.asarray(curve["controls"]), 3)
    start, end = np.asarray(row["seed"]["points"])[[0, -1]]
    derivatives = np.asarray(row["seed"]["derivatives"])
    begin, finish = spline.t[3], spline.t[-4]
    residuals = [np.max(np.abs(spline(begin) - start)), np.max(np.abs(spline(finish) - end))]
    for order, indices in ((1, (0, 1)), (2, (2, 3))):
        residuals.extend([np.max(np.abs(spline(begin, order) - derivatives[indices[0]])),
                          np.max(np.abs(spline(finish, order) - derivatives[indices[1]]))])
    assert max(residuals) < 1e-8
    times = np.linspace(begin, finish, int(np.ceil((finish - begin) / .01)) + 1)
    max_speed = float(np.max(np.linalg.norm(spline(times, 1), axis=1)))
    max_accel = float(np.max(np.linalg.norm(spline(times, 2), axis=1)))
    seed = row["seed"]
    assert max_speed <= seed["velocity_limit"] * (1 + seed["tolerance"]) + 1e-6
    assert max_accel <= seed["acceleration_limit"] * (1 + seed["tolerance"]) + 1e-6
    positive.append({"case": name, "duration_s": finish - begin,
        "accepted_endpoint_xy_distance_m": float(np.linalg.norm((end - start)[:2])),
        "independent_boundary_pva_max_error": float(max(residuals)),
        "sampled_max_speed_mps": max_speed, "sampled_max_acceleration_mps2": max_accel,
        "shortcut_success_did_not_bypass_failed_optimization": True})
assert curves[0] == curves[1]
result = {"passed": True, "blocked_direct_manager_controls": negative,
          "new_stopped_state": positive, "repeated_controls_and_knots_identical": True,
          "physical_route_validated": False}
(RUN / "independent_review.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
