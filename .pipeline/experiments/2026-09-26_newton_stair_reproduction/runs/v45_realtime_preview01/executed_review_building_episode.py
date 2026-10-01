"""Read actual Building outcome without promoting the empty-floor acceptance."""
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
    common = json.loads((BASE / "validation" / (args.run_id + "_review.json")).read_text())
    rows = [json.loads(line) for line in (run / "telemetry.jsonl").read_text().splitlines()]
    scenario = json.loads((run / "inputs/stair_scenario.json").read_text())
    request = json.loads((run / "episode_request.json").read_text())
    historical_full = request.get("building_route_profile") == "historical_full"
    profile_file = "historical_full_building.json" if historical_full else "stair_scenario.json"
    original = json.loads((BASE / "inputs" / profile_file).read_text())
    driver = json.loads((run / "artifacts/stair_driver_result.json").read_text())
    source = json.loads((run / "execution_sources.json").read_text())
    handoff = json.loads((run / "factory_handoff.json").read_text())
    factory = np.load(run / "factory_full_rate.npz")["records"]
    expected, continuous = np.float32(0.), True
    for row in factory:
        continuous &= float(expected) == row[0]
        expected = np.float32(expected + np.float32(.001))
    for row in rows:
        for _ in range(20):
            expected = np.float32(expected + np.float32(.001))
        continuous &= float(expected) == row["physics_time_s"]
    held = []
    for row in reversed(rows):
        if row.get("stance_mode") != "FIXED_STAND" or row.get("policy_owns_joints") is not False:
            break
        held.append(row)
    dwell = held[0]["physics_time_s"]-held[-1]["physics_time_s"] if held else 0.
    goal = np.asarray(scenario["goal_ground_xyz_m"])
    positions = np.asarray([r["joint_q"][:3] for r in rows])
    checks = {
        "common_interface": common["interface_checks_passed"],
        "executed_sources": all(hashlib.sha256((run/p).read_bytes()).hexdigest()==h for p,h in source.items()),
        "original_goal_and_spawn": all(scenario[k] == original[k] for k in ("goal_ground_xyz_m", "spawn_ground_xyz_m", "spawn_yaw_rad")),
        "native_arrival": any(t["status"]=="arrived" for t in common["navigation_terminal_results"]),
        "driver_arrival_and_pd": driver.get("route_arrived") is True,
        "native_moving_curve": len(common["moving_curves"]) >= 1,
        "actual_motion": np.linalg.norm(positions[-1,:2]-positions[0,:2]) >= 4.,
        "goal_xy": np.linalg.norm(positions[-1,:2]-goal[:2]) <= .25,
        "goal_floor_clearance": .20 <= positions[-1,2]-goal[2] <= .55,
        "final_pd_two_seconds": dwell >= 2.,
        "original_pd_gains": bool(held) and all(np.all(np.asarray(r["motor_kp"])==60.) and np.all(np.asarray(r["motor_kd"])==1.) for r in held),
        "no_fall": min(r["base_up_z"] for r in rows) >= .5,
        "continuous_physics": continuous,
        "factory_pd_force_match": np.max(np.abs(np.asarray(handoff["new_force_nm"])-handoff["factory_force_nm"])) < 1e-10,
        "motor_map": rows[-1]["applied_torque_max_abs"] <= 1e-4,
    }
    route_profile_checks = {}
    if historical_full:
        outcome = json.loads((run / "result.json").read_text())
        pct = outcome["last_backend"]["pct"]
        history = pct.get("plan_history", [])
        planned = np.asarray(history[-1].get("waypoints_m", []) if history else [])
        route_profile_checks = {
            "automatic_native_layers": "configured_pct_layer" in pct and pct["configured_pct_layer"] is None,
            "historical_route_length": len(planned) > 1 and np.linalg.norm(np.diff(planned[:,:2],axis=0),axis=1).sum() >= 70.,
            "correct_goal_level": len(planned) > 1 and abs(planned[-1,2]-goal[2]-.30) <= .02,
        }
        checks.update(route_profile_checks)
    checks = {k:bool(v) for k,v in checks.items()}
    result = {"building_route_profile": request.get("building_route_profile", "short_stair"),
              "actual_xy_path_m":float(np.linalg.norm(np.diff(positions[:,:2],axis=0),axis=1).sum()),
              "checks":checks,"passed":all(checks.values()),"actual_navigation_path_m":float(np.linalg.norm(np.diff(positions,axis=0),axis=1).sum()),
              "goal_xy_error_m":float(np.linalg.norm(positions[-1,:2]-goal[:2])),"final_pd_hold_s":dwell,
              "physics_s":rows[-1]["physics_time_s"],"moving_curves":len(common["moving_curves"]),
              "architectural_surface_contact_acceptance":"not assessed; no collision-free claim",
              "scope":("Historical complete-floor route" if historical_full else "Short stair route in complete Building geometry") + "; no added actor or physical-robot claim"}
    (BASE / "validation" / (args.run_id + "_building.json")).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
