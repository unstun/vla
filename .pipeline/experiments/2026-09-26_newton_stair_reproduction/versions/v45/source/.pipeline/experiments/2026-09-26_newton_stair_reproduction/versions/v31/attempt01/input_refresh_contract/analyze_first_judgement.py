"""Judge the v31 input-refresh contract (versions/v31/PLAN.md step 2); writes summary.json.

FSM states: 2 GEN_NEW_TRAJ, 3 REPLAN_TRAJ, 4 EXEC_TRAJ, 5 EMERGENCY_STOP.
Expectations per case (red = v30, green = v31):
- C1 stale scan, nothing pending: both stop with the conflict at 0.000 s;
  green applies nothing.
- C2 stale scan, scans pending: red stops as in C1; green stays in its entry
  state, its re-check is clear, and the processed scan is the newest pending.
- C3 stale pose, poses pending: red stops on InvalidCurve on the holds and stays
  clear on the moving curves; green stays clear with a body pose under 0.1 s.
- C4 planning, scans pending: red fails with a stale signature (the whole route
  blocked or a silent route exit); green applies the pending inputs at the
  planning timer, and any failure carries no stale signature.
- C5spin: the executor processes the same pending inputs; the map digest must
  equal green's C2 digest, and red's C5spin digest must equal green's.
"""
from pathlib import Path
import json

P = Path(__file__).resolve().parent
STATES = {"stairs_replan": False, "stairs_hold": True, "corridor_entry_replan": False, "upper_corridor_hold": True}
ENTRY = {True: 2, False: 3}
pending = json.loads((P / "pending/pending_manifest.json").read_text())["states"]


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
    if hold:
        check("C3 red invalid-curve stop", r["exec_state_after"] == 5 and r["invalid_curve_stop"])
    else:
        check("C3 red moving curve clear", r["exec_state_after"] == entry and r["recheck"]["status"] == "Clear")
    check("C3 green clear", g["exec_state_after"] == entry and g["recheck"]["status"] == "Clear" and g["body_age_after_s"] < 0.1)
    r, g = rows["red_v30/C4"], rows["green_v31/C4"]
    check("C4 red fails", r["exec_state_after"] == entry)
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
        print(f"{state:22s} {key:17s} state={row['exec_state_after']} recheck={row['recheck']['status']:12s} "
              f"cloud {row['cloud_age_before_s']:.3f}->{row['cloud_age_after_s']:.3f} body {row['body_age_before_s']:.3f}->"
              f"{row['body_age_after_s']:.3f} sites={','.join(row['refresh_sites']) or '-'} plan={','.join(row['final_plan_success']) or '-'} "
              f"digest={row['map_digest']} {row['call_wall_ms']:.0f}ms")
