"""Summarize the landing-stall replays: reproduction, cross-checks and the
reason each footprint circle beyond the frontier is blocked."""
from collections import Counter
from pathlib import Path
import csv, json, math

here = Path(__file__).resolve().parent
VERDICTS = {0: "Free", 1: "InvalidQuery", 2: "OutOfMap", 3: "MissingInput", 4: "StaleInput", 5: "Person",
            6: "UnknownObstacle", 7: "StaticObstacle", 8: "UnknownSupport", 9: "UnsupportedTerrain", 10: "WrongHeight"}
OCC = {0: "Unknown", 1: "Free", 2: "Occupied"}


def label(row):
    stage = row["stage"]
    if stage.startswith("verdict_"):
        return VERDICTS[int(stage.split("_")[1])]
    return stage


summary = {}
for state in ("landing", "onset"):
    d = here / state
    if not (d / "result.json").exists():
        continue
    result = json.loads((d / "result.json").read_text())
    baseline = json.loads((d / "baseline.json").read_text()) if (d / "baseline.json").exists() else None
    probe_log = (d / "probe.log").read_text(errors="replace")
    check = next((l for l in probe_log.splitlines() if "[LANDING-BREAKDOWN]" in l), "")
    rows = list(csv.DictReader((d / "result_breakdown.csv").open()))
    walk = list(csv.DictReader((d / "result_walk.csv").open()))
    frontier = result["frontier_time_s"]
    beyond = [r for r in rows if float(r["t"]) > frontier + 1e-9]
    by_sample = {}
    for r in beyond:
        by_sample.setdefault(int(r["i"]), {})[r["circle"]] = r
    first_block_reasons = Counter()
    circle_reasons = Counter()
    table = []
    for i in sorted(by_sample, key=lambda k: float(by_sample[k]["front"]["t"])):
        front, rear = by_sample[i]["front"], by_sample[i]["rear"]
        # Native getInflateOccupancy stops at a blocked front circle.
        deciding = front if front["native_circle"] == "1" else rear
        first_block_reasons[label(deciding) if deciding["native_circle"] == "1" else "free"] += 1
        for c in (front, rear):
            circle_reasons[(c["circle"], label(c))] += 1
        if len(table) < 40:
            def brief(c):
                text = label(c)
                if text == "UnknownObstacle":
                    text += " local=(%.2f,%.2f,%.3f) elev=%.1f trunk=%s" % (float(c["local_x"]), float(c["local_y"]), float(c["local_z"]), float(c["sensor_elev_deg"]), c["trunk_inside"])
                elif text == "StaticObstacle":
                    text += " contrib=%s/%s first=(%.2f,%.2f,%.3f) flags=%s on_ground=%s" % (c["unclassified"], c["contributors"], float(c["first_unclassified_x"]), float(c["first_unclassified_y"]), float(c["first_unclassified_z"]), c["first_flags"], c["first_on_ground"])
                elif text.startswith("support"):
                    text += " body_ground=%s foot_ground=%s body_verdict=%s" % (c["body_ground"], c["footprint_ground"], c["body_verdict"])
                return text
            table.append({"t": round(float(front["t"]), 3), "xyz": [round(float(front[k]), 3) for k in "xyz"],
                          "native": int(front["native"]), "front": brief(front), "rear": brief(rear)})
    walk_beyond = [w for w in walk if float(w["t"]) > frontier + 1e-9]
    summary[state] = {
        "result": result, "baseline": baseline,
        "baseline_equals_probe": baseline == result if baseline else None,
        "breakdown_check": check,
        "walk_samples_beyond_frontier": len(walk_beyond),
        "walk_free_beyond_frontier": sum(1 for w in walk_beyond if w["native"] == "0"),
        "window_samples_beyond_frontier": len(by_sample),
        "deciding_reason_counts": dict(first_block_reasons),
        "circle_reason_counts": {f"{k[0]}:{k[1]}": v for k, v in sorted(circle_reasons.items())},
        "first_samples": table,
    }
(here / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for state, s in summary.items():
    print("==", state)
    print(" frontier", s["result"]["frontier_time_s"], "continued", s["result"]["continued"], "baseline==probe", s["baseline_equals_probe"])
    print(" ", s["breakdown_check"][:400])
    print(" walk beyond frontier:", s["walk_samples_beyond_frontier"], "free:", s["walk_free_beyond_frontier"])
    print(" deciding reasons:", s["deciding_reason_counts"])
    print(" circle reasons:", s["circle_reason_counts"])
    for row in s["first_samples"][:24]:
        print("  t=%.3f %s native=%d | F: %s | R: %s" % (row["t"], row["xyz"], row["native"], row["front"], row["rear"]))
