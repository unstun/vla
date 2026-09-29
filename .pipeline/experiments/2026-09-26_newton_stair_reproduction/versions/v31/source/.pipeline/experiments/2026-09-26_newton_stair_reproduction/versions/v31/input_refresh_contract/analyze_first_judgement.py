"""Judge the v31 input-refresh contract (versions/v31/PLAN.md step 2); writes summary.json.

This is the second contract (candidate scan64). The first, on scan63, is kept
in attempt01/input_refresh_contract with its first judgement and correction.
C1-C5 keep their corrected criteria; C6, C7 and the FSM odometry checks were
added after the first independent review (N4, N6), before this run.

FSM states: 2 GEN_NEW_TRAJ, 3 REPLAN_TRAJ, 4 EXEC_TRAJ, 5 EMERGENCY_STOP.
Only input_refresh lines between [CONTRACT-CALL-BEGIN] and [CONTRACT-CALL-END]
count: the replay itself passes the target_check site (p2bRouteCallback), which
v31 logs on every call. Expectations per case (red = v30, green = v31):
- C1 stale scan, nothing pending: both stop with the conflict at 0.000 s;
  green applies nothing.
- C2 stale scan, scans pending: red stops as in C1; green stays in its entry
  state, its re-check is clear, the processed scan is the newest pending, and
  the FSM's odom_pos_ and the map's body pose are the newest pending body pose.
- C3 stale pose, poses pending: red's re-check equals the stop diagnosis's
  stale-pose row at delta 0.15 s (audits/2026-09-28_v30_stop_classes/<state>/
  result.json: status, first_time_s, samples, raw_t), and red stops with
  remaining_spline_invalid status=2 exactly when that row is InvalidCurve,
  otherwise it keeps its entry state. Green stays clear in its entry state
  with a body pose under 0.1 s, and its odom_pos_ is the newest pending body
  pose. Green's re-check is also compared with the diagnosis's fresh-pose row
  (recorded, not required).
- C4 planning, scans pending: red fails in its entry state with the whole route
  blocked ("Target is occupied and no collision-free point"); green applies the
  pending inputs at the planning timer, and any failure carries no stale
  signature; its odom_pos_ is the newest pending body pose. Green's plan result
  is recorded beside the diagnosis's replan at delta 0 (not required: green
  plans 0.30 s later, from newer inputs and a later start point).
- C5spin: the executor processes the same pending inputs; the map digest must
  equal green's C2 digest, and red's C5spin digest must equal green's.
- C6 inputs arriving during a planning call: green logs input_refresh at
  target_check, replan_start, rebound_round and final_check during the call,
  applies at least one message at one of them, and after the call and an
  executor spin its map digest equals green's C5spin digest. Red logs no
  refresh, and its final digest equals red's C5spin digest.
- C7 split batches: green's C7refresh and C7spin and red's C7spin give the same
  per-batch records (processed-scan stamp, sensor position, body stamp) and
  the same final digest: the refresh applies exactly what the executor applies
  at the same batch boundaries, including a cloud whose pose arrives in a later
  batch. Whether that final map equals C5spin's is recorded.
"""
from pathlib import Path
import json, re

P = Path(__file__).resolve().parent
AUDIT = P.parents[2] / "audits/2026-09-28_v30_stop_classes"
STATES = {"stairs_replan": False, "stairs_hold": True, "corridor_entry_replan": False, "upper_corridor_hold": True}
ENTRY = {True: 2, False: 3}
STATUS = {0: "Clear", 1: "Collision", 2: "InvalidCurve"}
CASES = {"red_v30": ["C1", "C2", "C3", "C4", "C5spin", "C6", "C7spin"],
         "green_v31": ["C1", "C2", "C3", "C4", "C5spin", "C6", "C7spin", "C7refresh"]}
INNER = ["target_check", "replan_start", "rebound_round", "final_check"]
REFRESH = re.compile(r"input_refresh site=(\w+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+) fsm_odom=(-?\d+) "
                     r"cloud_age=([-0-9.]+)->([-0-9.]+) body_age=([-0-9.]+)->([-0-9.]+)")
pending = json.loads((P / "pending/pending_manifest.json").read_text())["states"]


def diagnosis(state, name):
    return json.loads((AUDIT / state / name).read_text())


def diagnosis_row(state, name):
    """The stop diagnosis's safety re-check at delta 0.15 s, in the contract's recheck form."""
    rows = [row for value in diagnosis(state, name).values() if isinstance(value, list)
            for row in value if isinstance(row, dict) and row.get("delta_s") == 0.15 and "safety" in row]
    assert len(rows) == 1, (state, name, len(rows))
    safety = rows[0]["safety"]
    return {"status": STATUS[safety["status"]], "first_time_s": safety["first_time_s"], "samples": safety["samples"],
            "raw_t": rows[0]["raw_t"]}


def diagnosis_replan_ok_at_delta0(state):
    rows = [row for row in diagnosis(state, "result.json")["replans"] if row.get("delta_s") == 0]
    assert len(rows) == 1, state
    return rows[0]["ok"]


def same_recheck(a, b):
    return a["status"] == b["status"] and a["samples"] == b["samples"] and \
        abs(a["first_time_s"] - b["first_time_s"]) < 1e-9 and abs(a["raw_t"] - b["raw_t"]) < 1e-9


def same_xyz(a, b):
    return a is not None and b is not None and all(abs(x - y) < 1e-9 for x, y in zip(a, b))


def run(build, state, case):
    d = P / build / state
    result = json.loads((d / f"{case}.json").read_text())
    log = (d / f"{case}.log").read_text(errors="replace")
    result["exit_code"] = int((d / f"{case}_exit_code.txt").read_text())
    call = log.split("[CONTRACT-CALL-BEGIN]", 1)[1].split("[CONTRACT-CALL-END]", 1)[0]
    result["conflict_stop_0s"] = "Obstacle discovered; emergency stop in 0.000s" in call
    result["invalid_curve_stop"] = "remaining_spline_invalid status=2" in call
    result["whole_route_blocked"] = "Target is occupied and no collision-free point" in call
    lines = [m.groups() for m in REFRESH.finditer(call)]
    result["refresh_sites"] = sorted({g[0] for g in lines})
    result["refresh_lines"] = len(lines)
    result["applied_by_site"] = {}
    for g in lines:
        entry = result["applied_by_site"].setdefault(g[0], {"lines": 0, "sensor_poses": 0, "clouds": 0, "body_poses": 0})
        entry["lines"] += 1
        for key, value in zip(("sensor_poses", "clouds", "body_poses"), g[1:4]):
            entry[key] += int(value)
    result["final_plan_success"] = [line.split("=")[1].strip() for line in call.splitlines()
                                    if line.startswith("final_plan_success=")]
    return result


KEYS = ("exit_code", "exec_state_after", "recheck", "cloud_age_before_s", "cloud_age_after_s", "body_age_before_s",
        "body_age_after_s", "conflict_stop_0s", "invalid_curve_stop", "whole_route_blocked", "refresh_sites",
        "refresh_lines", "applied_by_site", "final_plan_success", "map_digest", "call_wall_ms", "call_batches",
        "call_batches_before_call_end", "batches", "fsm_odom_xyz", "map_body_xyz", "newest_pending_body_xyz")
summary, failures = {}, []
for state, hold in STATES.items():
    entry = ENTRY[hold]
    newest_scan_s = max(pending[state]["scans_0p30"]["scan_stamps_ns"]) / 1e9
    rows = {f"{b}/{c}": run(b, state, c) for b, cases in CASES.items() for c in cases}
    summary[state] = {k: {key: v.get(key) for key in KEYS} for k, v in rows.items()}
    check = lambda name, ok: failures.append(f"{state}: {name}") if not ok else None
    for key, row in rows.items():
        check(f"{key} exit 0", row["exit_code"] == 0)
    r, g = rows["red_v30/C1"], rows["green_v31/C1"]
    for row in (r, g):
        check("C1 conflict stop", row["exec_state_after"] == 5 and row["conflict_stop_0s"] and row["recheck"]["status"] == "Collision")
    check("C1 green applies nothing", not g["refresh_sites"] and abs(g["cloud_age_after_s"] - g["cloud_age_before_s"] -
                                                                 (g["now_after_s"] - g["now_before_s"])) < 1e-9)
    r, g = rows["red_v30/C2"], rows["green_v31/C2"]
    check("C2 red conflict stop", r["exec_state_after"] == 5 and r["conflict_stop_0s"])
    check("C2 green clear", g["exec_state_after"] == entry and g["recheck"]["status"] == "Clear" and not g["conflict_stop_0s"])
    check("C2 green newest scan", abs(g["cloud_stamp_after_s"] - newest_scan_s) < 1e-6 and g["cloud_age_after_s"] < 0.12)
    check("C2 green refresh at safety", g["refresh_sites"] == ["safety"])
    check("C2 green FSM odometry is the newest pending body pose",
          same_xyz(g["fsm_odom_xyz"], g["newest_pending_body_xyz"]) and same_xyz(g["map_body_xyz"], g["newest_pending_body_xyz"]))
    r, g = rows["red_v30/C3"], rows["green_v31/C3"]
    stale, fresh = diagnosis_row(state, "result.json"), diagnosis_row(state, "result_fresh_pose.json")
    check("C3 red equals the diagnosis's stale-pose row", same_recheck(r["recheck"], stale))
    if stale["status"] == "InvalidCurve":
        check("C3 red invalid-curve stop", r["exec_state_after"] == 5 and r["invalid_curve_stop"])
    else:
        check("C3 red keeps its entry state", r["exec_state_after"] == entry and not r["invalid_curve_stop"])
    check("C3 green clear", g["exec_state_after"] == entry and g["recheck"]["status"] == "Clear" and g["body_age_after_s"] < 0.1)
    check("C3 green FSM odometry is the newest pending body pose",
          same_xyz(g["fsm_odom_xyz"], g["newest_pending_body_xyz"]) and same_xyz(g["map_body_xyz"], g["newest_pending_body_xyz"]))
    summary[state]["C3_diagnosis_rows"] = {"stale_pose": stale, "fresh_pose": fresh,
                                           "green_equals_fresh_pose_row": same_recheck(g["recheck"], fresh)}
    r, g = rows["red_v30/C4"], rows["green_v31/C4"]
    check("C4 red fails with the whole route blocked", r["exec_state_after"] == entry and r["whole_route_blocked"])
    check("C4 green refresh at exec", "exec" in g["refresh_sites"])
    check("C4 green no stale signature", not g["whole_route_blocked"] and not g["conflict_stop_0s"])
    check("C4 green FSM odometry is the newest pending body pose", same_xyz(g["fsm_odom_xyz"], g["newest_pending_body_xyz"]))
    summary[state]["C4_beside_diagnosis_delta0"] = {"diagnosis_replan_ok_at_delta0": diagnosis_replan_ok_at_delta0(state),
                                                    "green_final_plan_success": g["final_plan_success"],
                                                    "green_exec_state_after": g["exec_state_after"]}
    check("C5 executor map equals refresh map", rows["green_v31/C5spin"]["map_digest"] == rows["green_v31/C2"]["map_digest"])
    check("C5 executor map equal across builds", rows["red_v30/C5spin"]["map_digest"] == rows["green_v31/C5spin"]["map_digest"])
    check("C5 green applies nothing after spin", not rows["green_v31/C5spin"]["refresh_sites"])
    r, g = rows["red_v30/C6"], rows["green_v31/C6"]
    inner_applied = sum(g["applied_by_site"].get(site, {}).get(k, 0) for site in INNER
                        for k in ("sensor_poses", "clouds", "body_poses"))
    check("C6 green logs every inner site", all(site in g["refresh_sites"] for site in INNER))
    check("C6 green applies inputs mid-call", inner_applied > 0)
    check("C6 green final map equals the executor's", g["map_digest"] == rows["green_v31/C5spin"]["map_digest"])
    check("C6 red no refresh", not r["refresh_sites"])
    check("C6 red final map equals the executor's", r["map_digest"] == rows["red_v30/C5spin"]["map_digest"])
    summary[state]["C6_inner_applied"] = inner_applied
    a, b, c = rows["green_v31/C7refresh"], rows["green_v31/C7spin"], rows["red_v30/C7spin"]
    check("C7 refresh batches equal executor batches", a["batches"] == b["batches"] == c["batches"])
    check("C7 refresh map equals executor map", a["map_digest"] == b["map_digest"] == c["map_digest"])
    summary[state]["C7_equals_C5spin"] = a["map_digest"] == rows["green_v31/C5spin"]["map_digest"]
    batches = a["batches"] or []
    if len(batches) == 5:
        summary[state]["C7_late_pose_cloud"] = {
            "batch4_cloud_stamp_s": batches[3]["cloud_stamp_s"], "batch4_ray_pos": batches[3]["ray_pos"],
            "batch4_ray_pos_is_previous_pose": batches[3]["ray_pos"] == batches[1]["ray_pos"],
            "batch5_ray_pos": batches[4]["ray_pos"]}
out = {"passed": not failures, "failures": failures, "states": summary}
(P / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"passed": out["passed"], "failures": failures}, indent=2))
for state, rows in summary.items():
    for key, row in rows.items():
        if not key.startswith(("red_", "green_")):
            continue
        print(f"{state:22s} {key:19s} state={row['exec_state_after']} recheck={row['recheck']['status']:12s} "
              f"cloud {row['cloud_age_before_s']:.3f}->{row['cloud_age_after_s']:.3f} body {row['body_age_before_s']:.3f}->"
              f"{row['body_age_after_s']:.3f} sites={','.join(row['refresh_sites']) or '-'} "
              f"plan={','.join(row['final_plan_success']) or '-'} digest={row['map_digest']} {row['call_wall_ms']:.0f}ms")
    print(state, {k: v for k, v in rows.items() if not k.startswith(("red_", "green_"))})
