"""Classify replayed candidate rejections into candidates_summary.json.

A live candidate counts as reproduced when the replay returns Collision with
the same duration (1e-6 s) and a first collision time within 0.02 s of the
logged one. For each reproduced candidate the blocking cause is the first
failing footprint circle at the first colliding sample:
  support_*  : the support query failed (body or footprint layer), no obstacle;
  verdict_6  : the queried voxel itself was never observed (UnknownObstacle);
  verdict_7  : a measured non-terrain return inside the inflation volume
               (StaticObstacle), with every such return put in a height band.
Height bands are measured from the body's support layer: ground_level within
0.05 m, leg_zone up to the URDF torso bottom, trunk to the torso top, and
above_trunk. The torso interior is TORSO z -0.05..+0.07 m about the body
reference, ignoring pitch.
"""
import json
import sys
from collections import Counter
from pathlib import Path

audit = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
STATES = ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]


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


def cause(candidate):
    circles = candidate.get("circles", [])
    blocking = [c for c in circles if c["circle"]["native"] == 1]
    if not blocking:
        return "no_blocking_circle", Counter(), None
    b = blocking[0]["circle"]
    bands = Counter()
    if b["stage"] == "verdict_7":
        ground = b["body_ground"]
        body_z = candidate["sample"][2]
        for xyz in b["unclassified_xyz"]:
            bands[band(xyz[2] - ground, body_z - 0.05 - ground, body_z + 0.07 - ground)] += 1
    return b["stage"], bands, blocking[0]["side"]


summary = {}
for kind, result_name, list_name in (("replan_delta0", "candidates_result.json", "candidates.json"),
                                     ("live_status1", "live_candidates_result.json", "live_candidates.json")):
    totals, causes, band_totals, cells = Counter(), Counter(), Counter(), Counter()
    per_state = {}
    for state in STATES:
        rp, lp = audit / state / result_name, audit / state / list_name
        if not rp.exists() or not lp.exists():
            continue
        replay = json.loads(rp.read_text())["candidates"]
        logged = {c["id"]: c for c in json.loads(lp.read_text())}
        rows = []
        for c in replay:
            log = logged[c["id"]]
            check = c["check"]
            if log.get("logged_t") is None:
                ok = check["status"] == 0 and abs(check["duration_s"] - log["logged_duration"]) < 1e-6
                rows.append({"id": c["id"], "reproduced": ok, "cause": "clear"})
                totals["reproduced" if ok else "not_reproduced"] += 1
                continue
            ok = (check["status"] == 1 and abs(check["duration_s"] - log["logged_duration"]) < 1e-6
                  and abs(check["first_time_s"] - log["logged_t"]) < 0.02)
            totals["reproduced" if ok else "not_reproduced"] += 1
            row = {"id": c["id"], "reproduced": ok, "replay_status": check["status"],
                   "replay_t": check["first_time_s"], "logged_t": log["logged_t"]}
            if ok:
                stage, bands, side = cause(c)
                causes[stage] += 1
                band_totals.update(bands)
                cells[tuple(round(v, 1) for v in c["sample"][:2])] += 1
                row.update({"cause": stage, "side": side, "bands": dict(bands), "sample": c["sample"]})
            rows.append(row)
        per_state[state] = rows
    summary[kind] = {"totals": dict(totals), "causes_of_reproduced": dict(causes),
                     "static_obstacle_return_bands": dict(band_totals),
                     "first_colliding_sample_xy_most_common": [[list(k), v] for k, v in cells.most_common(10)],
                     "per_state": per_state}
(audit / "candidates_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for kind, s in summary.items():
    print(kind, s["totals"], s["causes_of_reproduced"], s["static_obstacle_return_bands"])
    print("   most common first colliding XY:", s["first_colliding_sample_xy_most_common"][:6])
