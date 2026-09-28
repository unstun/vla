"""Request one native long PCT route and require arrival plus PD standing."""
import argparse
import importlib.util
from pathlib import Path
import time

source = Path(__file__).with_name("executed_geometry_driver.py")
spec = importlib.util.spec_from_file_location("verified_geometry_driver", source)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def fixed_stand(snapshot):
    control = snapshot.get("control", {})
    return (control.get("stance_mode") == "FIXED_STAND"
            and control.get("policy_owns_joints") is False and control.get("navigation_ready") is True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    args = parser.parse_args()
    root, run_id = args.run_root, args.run_id
    base = f"http://127.0.0.1:{args.http_port}"
    snapshots = root / "artifacts/external_episode/current_command.json"
    health = root / "artifacts/runtime_health.json"
    finish = root / "artifacts/external_episode/finish_request.json"
    scenario = driver.read_json(root / "inputs/stair_scenario.json")
    pilot = driver.read_json(root / "inputs/pilot.json")
    request_id = run_id + "-long-goal"
    journal, epoch = [], None
    try:
        snap = driver.wait_snapshot(snapshots, run_id, timeout_s=240.)
        epoch = snap["run_epoch_ns"]
        driver.wait_http_ready(base, journal, snapshots, run_id, epoch)
        deadline, stable_since = time.monotonic() + 90., None
        while time.monotonic() < deadline:
            snap = driver.wait_snapshot(snapshots, run_id, timeout_s=2.)
            stable = (fixed_stand(snap) and driver.snapshot_ready_to_walk(snap)
                      and driver.health_ready(health, run_id, epoch))
            stable_since = (snap["sim_time_s"] if stable_since is None else stable_since) if stable else None
            if stable_since is not None and snap["sim_time_s"] - stable_since >= 1.:
                break
            time.sleep(.05)
        else:
            raise RuntimeError("Initial measured PD hold was not reached")
        payload = {"request_id": request_id, "goal_id": "long-goal", "target_ground_xyz": scenario["goal_ground_xyz_m"],
                   "frame": "world", "map_epoch": "stair_reactive", "map_revision": 1}
        response = driver.post_json(base, "/goal", payload)
        journal.append({"event": "goal_request", "response": response, "payload": payload,
                        "sim_time_s": snap["sim_time_s"], "initial_snapshot": snap})
        if not response.get("ok"):
            raise RuntimeError("Native backend rejected the long goal")
        deadline = time.monotonic() + scenario["max_wall_seconds"]
        arrived, hold_since, unhealthy_since = None, None, None
        while time.monotonic() < deadline:
            snap = driver.wait_snapshot(snapshots, run_id, timeout_s=2.)
            state = driver.get_json(base, "/state")
            healthy = driver.health_ready(health, run_id, epoch)
            unhealthy_since = None if healthy else (unhealthy_since or time.monotonic())
            if unhealthy_since is not None and time.monotonic() - unhealthy_since > 1.:
                raise RuntimeError("Geometric sensing became unhealthy")
            failed = driver.state_terminal_for(state, request_id, "failed")
            if failed is not None:
                raise RuntimeError("Native navigation failed: " + str(failed))
            arrived = driver.state_terminal_for(state, request_id, "arrived") or arrived
            distance = driver.xy_distance(snap["measured"]["base_xyz"], scenario["goal_ground_xyz_m"])
            good = (arrived is not None and distance <= pilot["goal_xy_tolerance_m"]
                    and fixed_stand(snap) and driver.snapshot_stopped(snap, pilot))
            hold_since = (snap["sim_time_s"] if hold_since is None else hold_since) if good else None
            journal.append({"event": "observation", "sim_time_s": snap["sim_time_s"],
                            "distance_m": distance, "control": snap.get("control"), "arrived": arrived is not None})
            if hold_since is not None and snap["sim_time_s"] - hold_since >= 2.:
                driver.write_json(root / "artifacts/stair_driver_result.json", {
                    "execution_completed": True, "route_arrived": True, "final_snapshot": snap,
                    "arrival": arrived, "pd_dwell_start_s": hold_since, "journal": journal})
                driver.finish_request(finish, run_id, request_id, epoch, "FINISHED", "native arrival and measured PD hold")
                return
            time.sleep(.1)
        raise TimeoutError("Long route deadline before arrival and PD hold")
    except BaseException as exc:
        try:
            driver.post_json(base, "/cancel", {"request_id": run_id+"-failed-cancel", "target_request_id": request_id})
        except Exception:
            pass
        driver.write_json(root / "artifacts/stair_driver_result.json", {
            "execution_completed": False, "error": str(exc), "journal": journal})
        if epoch is not None:
            driver.finish_request(finish, run_id, request_id, epoch, "FAILED", str(exc))
        raise


if __name__ == "__main__":
    main()
