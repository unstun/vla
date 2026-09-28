"""Summarize the four stop replays into summary.json.

For every state: the fresh-input result (delta 0), the first delta at which
each check changes, the input ages there, the replans, and a height-band
breakdown of every unclassified contributor inside the two footprint circles
at the robot's current point.

Height bands are measured from the support layer under the body reference
(body_ground). The trunk band is the pinned URDF TORSO collision interior,
z in [-0.05, +0.07] m about the measured TORSO origin (known_lite3_trunk.h),
ignoring body pitch.
"""
import json
import sys
from collections import Counter
from pathlib import Path

audit = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
STATES = ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]
STATUS = {0: "Clear", 1: "Collision", 2: "InvalidCurve", 3: "InvalidTime", 4: "InvalidResolution", 5: "SampleBudgetExceeded"}
VERDICT = {0: "Free", 1: "InvalidQuery", 2: "OutOfMap", 3: "MissingInput", 4: "StaleInput", 5: "Person",
           6: "UnknownObstacle", 7: "StaticObstacle", 8: "UnknownSupport", 9: "UnsupportedTerrain", 10: "WrongHeight"}


def band(z_rel, trunk_bottom, trunk_top):
    if z_rel < -0.05:
        return "below_ground"
    if z_rel < 0.05:
        return "ground_level"
    if z_rel < trunk_bottom:
        return "leg_zone"
    if z_rel <= trunk_top:
        return "trunk"
    return "above_trunk"


def first_change(sweep, key):
    base = key(sweep[0])
    for row in sweep[1:]:
        if key(row) != base:
            return {"delta_s": row["delta_s"], "from": base, "to": key(row),
                    "body_age_s": round(row["body_age_s"], 4), "cloud_age_s": round(row["cloud_age_s"], 4)}
    return None


def summarize(path):
    r = json.loads(path.read_text())
    sweep = r["sweep"]
    fresh = sweep[0]
    body_z = r["body"][2]
    circles = []
    for c in r["circles"]:
        b = c["circle"]
        ground = b["body_ground"] if b["body_ground"] != -999.0 else None
        bands = Counter()
        if ground is not None:
            trunk_bottom, trunk_top = body_z - 0.05 - ground, body_z + 0.07 - ground
            for xyz in b["unclassified_xyz"]:
                bands[band(xyz[2] - ground, trunk_bottom, trunk_top)] += 1
        circles.append({"delta_s": c["delta_s"], "side": c["side"], "stage": b["stage"],
                        "verdict": VERDICT.get(b["verdict"], b["verdict"]), "native": b["native"], "replicated": b["replicated"],
                        "raw_class": b["raw_class"], "final_class": b["final_class"], "trunk_inside": b["trunk_inside"],
                        "contributors": b["contributors"], "terrain_contributors": b["terrain_contributors"],
                        "unclassified": b["unclassified"], "unclassified_bands": dict(bands),
                        "body_ground": ground, "torso_origin_above_ground": None if ground is None else round(body_z - ground, 4)})
    return {
        "refresh_pose": r.get("refresh_pose", False),
        "executing_traj_id": r["executing_traj_id"], "executing_is_hold": r["executing_is_hold"],
        "body": r["body"], "clouds": r["clouds"], "cloud_max_age": r["inflation"]["cloud_max_age"],
        "circle_mismatches": r["circle_mismatches"], "support_mismatches": r["support_mismatches"],
        "fresh": {
            "body_age_s": round(fresh["body_age_s"], 4), "cloud_age_s": round(fresh["cloud_age_s"], 4),
            "safety": STATUS[fresh["safety"]["status"]], "safety_first_time_s": fresh["safety"]["first_time_s"],
            "raw_t": fresh["raw_t"], "hold": STATUS[fresh["hold"]["status"]],
            "whole_executing": STATUS[fresh["whole_executing"]["status"]],
            "whole_executing_first_time_s": fresh["whole_executing"]["first_time_s"],
            "current_occupied": fresh["current_occupied_safety_yaw"], "frontier_ok": fresh["frontier_ok"],
            "frontier_s": fresh["frontier_s"], "route": fresh["route"],
        },
        "first_changes": {
            "safety": first_change(sweep, lambda x: STATUS[x["safety"]["status"]]),
            "hold": first_change(sweep, lambda x: STATUS[x["hold"]["status"]]),
            "whole_executing": first_change(sweep, lambda x: STATUS[x["whole_executing"]["status"]]),
            "current_occupied": first_change(sweep, lambda x: x["current_occupied_safety_yaw"]),
            "frontier_ok": first_change(sweep, lambda x: x["frontier_ok"]),
            "route_free_zero": first_change(sweep, lambda x: x["route"]["free"] == 0),
        },
        "sweep": [{"delta_s": x["delta_s"], "body_age_s": round(x["body_age_s"], 4), "cloud_age_s": round(x["cloud_age_s"], 4),
                   "safety": STATUS[x["safety"]["status"]], "hold": STATUS[x["hold"]["status"]],
                   "whole_executing": STATUS[x["whole_executing"]["status"]],
                   "current_occupied": x["current_occupied_safety_yaw"], "frontier_ok": x["frontier_ok"],
                   "route_free": x["route"]["free"], "route_within_3m_free": x["route"]["within_3m_free"],
                   "route_nan_yaw": x["route"]["nan_yaw"]} for x in sweep],
        "circles": circles,
        "replans": r["replans"],
    }


summary = {}
for state in STATES:
    summary[state] = {}
    for mode, name in (("aged_pose_and_scan", "result.json"), ("fresh_pose_aged_scan", "result_fresh_pose.json")):
        path = audit / state / name
        code = audit / state / ("probe_exit_code.txt" if name == "result.json" else "probe_fresh_pose_exit_code.txt")
        summary[state][mode] = summarize(path) if path.exists() else {
            "missing": True, "exit_code": code.read_text().strip() if code.exists() else None}
(audit / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
