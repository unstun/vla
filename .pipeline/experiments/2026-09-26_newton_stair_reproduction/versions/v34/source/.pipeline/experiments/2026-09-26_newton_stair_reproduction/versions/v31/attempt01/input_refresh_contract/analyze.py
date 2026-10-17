"""Judge the v31 input-refresh contract (versions/v31/PLAN.md step 2); writes summary.json.

FSM states: 2 GEN_NEW_TRAJ, 3 REPLAN_TRAJ, 4 EXEC_TRAJ, 5 EMERGENCY_STOP.
Expectations per case (red = v30, green = v31):
- C1 stale scan, nothing pending: both stop with the conflict at 0.000 s;
  green applies nothing.
- C2 stale scan, scans pending: red stops as in C1; green stays in its entry
  state, its re-check is clear, and the processed scan is the newest pending.
- C3 stale pose, poses pending: red's re-check equals the stop diagnosis's
  stale-pose row at delta 0.15 s (audits/2026-09-28_v30_stop_classes/<state>/
  result.json: status, first_time_s, samples, raw_t), and red stops with
  remaining_spline_invalid status=2 exactly when that row is InvalidCurve,
  otherwise it keeps its entry state. Green stays clear in its entry state
  with a body pose under 0.1 s.
  Corrected after the first judgement (kept in summary_first_judgement.json
  and analyze_first_judgement.py). That version required red to stay clear on
  both moving curves, but the diagnosis (RESULT.md section 2, committed in
  b3a172e5 before this contract ran) records that a curve ending at rest fails
  in its last ~0.1 s with a stale pose, and its stairs_replan row is
  InvalidCurve at 3.9526 s. The first judgement failed only on that
  expectation. Green's re-check is also compared with the diagnosis's
  fresh-pose row (result_fresh_pose.json); that comparison is recorded, not
  required, since green applies the run's own newer body poses rather than a
  re-stamped frozen pose.
- C4 planning, scans pending: red fails in its entry state with the whole route
  blocked ("Target is occupied and no collision-free point"); green applies the
  pending inputs at the planning timer, and any failure carries no stale
  signature. The first version described red's stale signature ("the whole
  route blocked or a silent route exit") but tested only the entry state; the
  same correction (see C3) added the test. A silent route exit leaves no log
  line, so it would fail this test.
- C5spin: the executor processes the same pending inputs; the map digest must
  equal green's C2 digest, and red's C5spin digest must equal green's.
"""
from pathlib import Path
import json

P = Path(__file__).resolve().parent
AUDIT = P.parents[2] / "audits/2026-09-28_v30_stop_classes"
STATES = {"stairs_replan": False, "stairs_hold": True, "corridor_entry_replan": False, "upper_corridor_hold": True}
ENTRY = {True: 2, False: 3}
STATUS = {0: "Clear", 1: "Collision", 2: "InvalidCurve"}
pending = json.loads((P / "pending/pending_manifest.json").read_text())["states"]


def diagnosis_row(state, name):
    """The stop diagnosis's safety re-check at delta 0.15 s, in the contract's recheck form."""
    rows = [row for value in json.loads((AUDIT / state / name).read_text()).values() if isinstance(value, list)
            for row in value if isinstance(row, dict) and row.get("delta_s") == 0.15 and "safety" in row]
    assert len(rows) == 1, (state, name, len(rows))
    safety = rows[0]["safety"]
    return {"status": STATUS[safety["status"]], "first_time_s": safety["first_time_s"], "samples": safety["samples"],
            "raw_t": rows[0]["raw_t"]}


def same_recheck(a, b):
    return a["status"] == b["status"] and a["samples"] == b["samples"] and \
        abs(a["first_time_s"] - b["first_time_s"]) < 1e-9 and abs(a["raw_t"] - b["raw_t"]) < 1e-9


def run(build, state, case):
    d = P / build / state
    result = json.loads((d / f"{case}.json").read_text())
    log = (d / f"{case}.log").read_text(errors="replace")
    result["exit_code"] = int((d / f"{case}_exit_code.txt").read_text())
    result["conflict_stop_0s"] = "Obstacle discovered; emergency stop in 0.000s" in log
    result["invalid_curve_stop"] = "remaining_spline_invalid status=2" in log
    result["whole_route_blocked"] = "Target is occupied and no collision-free point" in log
    result["refresh_sites"] = sorted({line.split("site=")[1].split()[0] for line in log.splitlines() if "input_refresh site=" in line})
    result["final_plan_success"] = [line.split("=")[1].strip() for line in log.splitlines() if line.startswith("final_plan_success=")]
    return result


summary, failures = {}, []
for state, hold in STATES.items():
    entry = ENTRY[hold]
    newest_scan_s = max(pending[state]["scans_0p30"]["scan_stamps_ns"]) / 1e9
    rows = {f"{b}/{c}": run(b, state, c) for b in ("red_v30", "green_v31") for c in ("C1", "C2", "C3", "C4", "C5spin")}
    summary[state] = {k: {key: v[key] for key in ("exit_code", "exec_state_after", "recheck", "cloud_age_before_s",
                                                  "cloud_age_after_s", "body_age_before_s", "body_age_after_s",
                                                  "conflict_stop_0s", "invalid_curve_stop", "whole_route_blocked",
                                                  "refresh_sites", "final_plan_success", "map_digest", "call_wall_ms")}
                      for k, v in rows.items()}
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
    r, g = rows["red_v30/C3"], rows["green_v31/C3"]
    stale, fresh = diagnosis_row(state, "result.json"), diagnosis_row(state, "result_fresh_pose.json")
    check("C3 red equals the diagnosis's stale-pose row", same_recheck(r["recheck"], stale))
    if stale["status"] == "InvalidCurve":
        check("C3 red invalid-curve stop", r["exec_state_after"] == 5 and r["invalid_curve_stop"])
    else:
        check("C3 red keeps its entry state", r["exec_state_after"] == entry and not r["invalid_curve_stop"])
    check("C3 green clear", g["exec_state_after"] == entry and g["recheck"]["status"] == "Clear" and g["body_age_after_s"] < 0.1)
    summary[state]["C3_diagnosis_rows"] = {"stale_pose": stale, "fresh_pose": fresh,
                                           "green_equals_fresh_pose_row": same_recheck(g["recheck"], fresh)}
    r, g = rows["red_v30/C4"], rows["green_v31/C4"]
    check("C4 red fails with the whole route blocked", r["exec_state_after"] == entry and r["whole_route_blocked"])
    check("C4 green refresh at exec", "exec" in g["refresh_sites"])
    check("C4 green no stale signature", not g["whole_route_blocked"] and not g["conflict_stop_0s"])
    check("C5 executor map equals refresh map", rows["green_v31/C5spin"]["map_digest"] == rows["green_v31/C2"]["map_digest"])
    check("C5 executor map equal across builds", rows["red_v30/C5spin"]["map_digest"] == rows["green_v31/C5spin"]["map_digest"])
    check("C5 green applies nothing after spin", not rows["green_v31/C5spin"]["refresh_sites"])
out = {"passed": not failures, "failures": failures, "states": summary}
(P / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"passed": out["passed"], "failures": failures}, indent=2))
for state, rows in summary.items():
    for key, row in rows.items():
        if key == "C3_diagnosis_rows":
            continue
        print(f"{state:22s} {key:17s} state={row['exec_state_after']} recheck={row['recheck']['status']:12s} "
              f"cloud {row['cloud_age_before_s']:.3f}->{row['cloud_age_after_s']:.3f} body {row['body_age_before_s']:.3f}->"
              f"{row['body_age_after_s']:.3f} sites={','.join(row['refresh_sites']) or '-'} plan={','.join(row['final_plan_success']) or '-'} "
              f"digest={row['map_digest']} {row['call_wall_ms']:.0f}ms")
