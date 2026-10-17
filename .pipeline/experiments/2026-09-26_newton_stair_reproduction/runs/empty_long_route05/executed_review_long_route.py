"""Read-only, prospective 12 m route and PD stop acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run = BASE / "runs" / args.run_id
    if run.parent != BASE / "runs":
        raise ValueError("Invalid run name")
    rows = [json.loads(s) for s in (run / "telemetry.jsonl").read_text().splitlines()]
    obs = [json.loads(s) for s in (run / "artifacts/reactive_observations.jsonl").read_text().splitlines()]
    common = json.loads((BASE / "validation" / (args.run_id+"_review.json")).read_text())
    driver = json.loads((run / "artifacts/stair_driver_result.json").read_text())
    stance = json.loads((run / "stance_status.json").read_text())
    handoff = json.loads((run / "factory_handoff.json").read_text())
    factory = np.load(run / "factory_full_rate.npz")["records"]
    request = json.loads((run / "episode_request.json").read_text())
    clock_type = float if request.get("physics_backend") == "native" else np.float32
    expected = clock_type(0.)
    factory_continuous = True
    for row in factory:
        factory_continuous &= float(expected) == row[0]
        expected = clock_type(expected+clock_type(.001))
    for row in rows:
        for _ in range(20):
            expected = clock_type(expected+clock_type(.001))
        factory_continuous &= float(expected) == row["physics_time_s"]
    routes = [r for r in obs if r["event"] == "pct_route"]
    points = np.array([[p["pose"]["position"][k] for k in ("x","y","z")]
                       for p in routes[0]["data"]["path"]["poses"]]) if routes else np.empty((0,3))
    route_length = float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()) if len(points) else 0.
    held = []
    for row in reversed(rows):
        if row.get("stance_mode") != "FIXED_STAND" or row.get("policy_owns_joints") is not False:
            break
        held.append(row)
    hold_duration = held[0]["physics_time_s"]-held[-1]["physics_time_s"] if held else 0.
    source = json.loads((run / "execution_sources.json").read_text())
    checks = {
        "common_interface": common["interface_checks_passed"],
        "source_snapshots": all(hashlib.sha256((run/p).read_bytes()).hexdigest()==v for p,v in source.items()),
        "native_arrival": any(t["status"]=="arrived" for t in common["navigation_terminal_results"]),
        "driver_arrival_and_pd_hold": driver.get("route_arrived") is True,
        "global_route_over_11_5m": route_length >= 11.5,
        "original_goal": len(points)>0 and np.linalg.norm(points[-1,:2]-[12.,0.]) <= .11,
        "multiple_local_curves": len(common["moving_curves"]) >= 3,
        "measured_goal_error": common["final_goal_xy_distance_m"] <= .25,
        "final_pd_two_seconds": hold_duration >= 2.,
        "pd_gains": bool(held) and all(np.all(np.asarray(r["motor_kp"])==60.) and np.all(np.asarray(r["motor_kd"])==1.) for r in held),
        "pd_to_rl": stance["hold"]["counters"]["rejoin_complete"] >= 1,
        "rl_to_pd": stance["hold"]["counters"]["entries"] >= 1,
        "no_fall": min(r["base_up_z"] for r in rows)>=.5,
        "body_height": min(r["joint_q"][2] for r in rows)>=.20,
        "continuous_factory_navigation_clock": bool(factory_continuous),
        "factory_pd_force_match": np.max(np.abs(np.array(handoff["new_force_nm"])-handoff["factory_force_nm"])) < 1e-10,
        "full_rate_motor_map": rows[-1]["applied_torque_max_abs"] <= 1e-4,
    }
    report = {"checks": checks, "passed": all(checks.values()), "route_length_m": route_length,
              "actual_path_m": float(np.linalg.norm(np.diff(np.array([r["joint_q"][:2] for r in rows]),axis=0),axis=1).sum()),
              "final_goal_error_m": common["final_goal_xy_distance_m"], "final_pd_hold_s": hold_duration,
              "native_moving_curves": len(common["moving_curves"]), "physics_duration_s": rows[-1]["physics_time_s"],
              "factory_calibration_validated": False, "scope": "One obstacle-free Newton route; no obstacle or hardware validation"}
    target=BASE/"validation"/(args.run_id+"_long_route.json")
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
