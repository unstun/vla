"""Explain onset start_occupied: diagnosis baseline 0, probe-only oracle 1, v30 0.

python3 onset_start_support.py  ->  onset_start_support.json

The probe computes start_occupied = getInflateOccupancy(start, yaw), with
yaw = collisionSegmentYaw(start, target): the heading toward the target it
chose. The baseline chose a different target from the oracle and v30, so it
checked a different yaw. The script reads the logged yaws. It then locates
the front and rear footprint circle centres (start +/- 0.18 m along the yaw)
and reads their support labels: v29 labels for the baseline, v29 labels with
the oracle's relabelling (walkway layers 1.35-1.65 m inside x[-5.3,-3.5]
y[-4.5,-2.3] only) for the oracle, and v30 labels for v30.
"""
import json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "support_contract"))
import oracle  # noqa: E402

AUDIT = E / "audits/2026-09-28_v29_landing_stall"
NAMES = {0: "Unknown", 1: "Flat", 2: "Stair", 3: "Unsupported"}
nav = oracle.decode_f32(E / "audits/2026-09-27_pct_precision/ground_precise.f32")
evidence = oracle.decode_f32(E / "audits/2026-09-27_dense_static_sampling/raw_ground.f32")
v29, v30 = oracle.score(nav), oracle.score(nav, evidence)
RUNS = {"baseline": (AUDIT / "onset/baseline.json", AUDIT / "onset/baseline.log", v29, False),
        "oracle": (AUDIT / "onset_oracle/result.json", AUDIT / "onset_oracle/probe.log", v29, True),
        "v30": (E / "runs/v30_saved_states01/onset/result.json", E / "runs/v30_saved_states01/onset/probe.log", v30, False)}


def in_oracle_box(cell, elevation):
    x0, y0 = nav.origin[0] + cell[0] * 0.1, nav.origin[1] + cell[1] * 0.1
    return -5.3 <= x0 <= -3.5 and -4.5 <= y0 <= -2.3 and 1.35 <= elevation <= 1.65


def support(labels, relabel, cell, target, limit):
    layers = nav.cells.get(cell)
    if layers is None:
        return {"cell": list(cell), "state": "no navigation ground"}
    order = sorted(range(len(layers)), key=lambda i: abs(layers[i] - target))
    k = order[0]
    if (len(order) > 1 and abs(abs(layers[order[1]] - target) - abs(layers[k] - target)) <= 1e-9) or abs(layers[k] - target) > limit:
        return {"cell": list(cell), "state": "no unambiguous layer in reach"}
    label = labels[cell][k][0]
    boxed = in_oracle_box(cell, layers[k])
    if relabel and boxed and label == 0:
        label = 1  # the oracle's probe-only relabelling of the landing ring
    return {"cell": list(cell), "elevation_m": round(layers[k], 4), "label": NAMES[label], "inside_oracle_box": boxed,
            "selected": label in (1, 2)}


report = {}
for name, (result_path, log_path, labels, relabel) in RUNS.items():
    result = json.loads(result_path.read_text())
    x, y, z = result["start"]
    tx, ty, _ = result["target"]
    logged = re.search(r"initial_spline_collision pos=\(\S+\) yaw=(\S+)", log_path.read_text(errors="replace"))
    yaw = float(logged.group(1)) if logged else math.atan2(ty - y, tx - x)
    body = support(labels, relabel, (math.floor((x - nav.origin[0]) / 0.1), math.floor((y - nav.origin[1]) / 0.1)), z - 0.3, 0.12)
    circles = {tag: support(labels, relabel, (math.floor((x + s * 0.18 * math.cos(yaw) - nav.origin[0]) / 0.1),
                                              math.floor((y + s * 0.18 * math.sin(yaw) - nav.origin[1]) / 0.1)),
                            body["elevation_m"], oracle.CRIT)
               for tag, s in (("front", 1), ("rear", -1))}
    passes = bool(body.get("selected")) and all(c.get("selected") for c in circles.values())
    report[name] = {"start": [x, y, z], "target": result["target"], "yaw": yaw, "yaw_source": "log" if logged else "atan2",
                    "atan2_yaw_to_target": math.atan2(ty - y, tx - x), "body": body, "circles": circles,
                    "support_check_passes": passes, "recorded_start_occupied": result["start_occupied"],
                    "support_check_predicts_recorded_value": result["start_occupied"] == (0 if passes else 1)}
summary = {n: {k: r[k] for k in ("yaw", "recorded_start_occupied", "support_check_passes", "support_check_predicts_recorded_value")}
           | {"front": r["circles"]["front"]} for n, r in report.items()}
(HERE / "onset_start_support.json").write_text(json.dumps({"summary": summary, "runs": report}, indent=1) + "\n")
print(json.dumps(summary, indent=1))
