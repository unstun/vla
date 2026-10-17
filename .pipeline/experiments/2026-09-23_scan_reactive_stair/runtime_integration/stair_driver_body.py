"""Task-specific main, assembled after the pinned two-goal driver's helpers."""


def health_ready(path, run_id, epoch, source_id="sensor_lidar_moving_cluster_candidate_v2"):
    try:
        value = read_json(path)
        stamps = value["stamps_ns"]
        now = stamps["clock"]
        keys = ("cloud", "lidar_pose", "pct_tomogram", "tracked_person_snapshot")
        if source_id == "sensor_lidar_static_background_cluster_v3":
            keys += ("tracker_ground",)
        elif source_id != "sensor_lidar_moving_cluster_candidate_v2":
            return False
        if value["run_id"] != run_id or value["run_epoch_ns"] != epoch:
            return False
        if time.monotonic_ns() - value["wall_monotonic_ns"] > 1_000_000_000:
            return False
        if not all(stamps.get(k, 0) > 0 for k in keys) or now <= 0:
            return False
        return (stamps["cloud"] == stamps["lidar_pose"] and value["tracks_complete"]
                and value["track_source_id"] == source_id
                and 0 <= now - stamps["cloud"] <= 500_000_000
                and 0 <= now - stamps["tracked_person_snapshot"] <= 500_000_000)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def snapshot_stopped(snapshot, pilot):
    command, measured = snapshot["applied_command"], snapshot["measured"]
    return (math.hypot(command["vx"], command["vy"]) <= pilot["stop_command_norm"]
            and abs(command["wz"]) <= pilot["stop_command_norm"]
            and measured["horizontal_speed_mps"] <= pilot["stop_speed_mps"]
            and abs(measured["yaw_rate_radps"]) <= pilot["stop_yaw_rate_radps"])


def snapshot_ready_to_walk(snapshot):
    command, measured = snapshot["applied_command"], snapshot["measured"]
    return (snapshot["sim_time_s"] >= 5.0
            and math.hypot(command["vx"], command["vy"]) <= 0.005
            and abs(command["wz"]) <= 0.005
            and measured["horizontal_speed_mps"] <= 0.01
            and abs(measured["yaw_rate_radps"]) <= 0.03)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--cancel-displacement-m", type=float)
    args = parser.parse_args()
    root = args.run_root
    pilot = read_json(root / "inputs/pilot.json")
    scenario = read_json(root / "inputs/stair_scenario.json")
    track_source = scenario.get("track_source_id", "sensor_lidar_moving_cluster_candidate_v2")
    base = "http://127.0.0.1:%d" % args.http_port
    snapshots = root / "artifacts/external_episode/current_command.json"
    health = root / "artifacts/runtime_health.json"
    finish_path = root / "artifacts/external_episode/finish_request.json"
    journal = []
    request_id = args.run_id + "-stair-goal"
    epoch = None
    try:
        snap = wait_snapshot(snapshots, args.run_id, timeout_s=120)
        epoch = int(snap["run_epoch_ns"])
        wait_http_ready(base, journal, snapshots, args.run_id, epoch, timeout_s=120)
        deadline = time.monotonic() + 60
        while not health_ready(health, args.run_id, epoch, track_source):
            if time.monotonic() > deadline:
                raise RuntimeError("paired cloud/PCT/current-track readiness timed out")
            time.sleep(0.05)
        if scenario["mode"] == "walk":
            stable_since = None
            settle_deadline = time.monotonic() + 60.0
            while time.monotonic() < settle_deadline:
                snap = wait_snapshot(snapshots, args.run_id, timeout_s=2)
                stable = snapshot_ready_to_walk(snap) and health_ready(health, args.run_id, epoch, track_source)
                stable_since = (snap["sim_time_s"] if stable_since is None else stable_since) if stable else None
                if stable_since is not None and snap["sim_time_s"] - stable_since >= 0.5:
                    journal.append({"event": "measured_ready_to_walk", "sim_time_s": snap["sim_time_s"],
                                    "stable_since_s": stable_since, "measured": snap["measured"],
                                    "claim": "actual stable state; no velocity zeroing or pose injection"})
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("measured stable start was not reached")
            payload = {"request_id": request_id, "goal_id": "stair-goal",
                       "target_ground_xyz": scenario["goal_ground_xyz_m"], "frame": "world",
                       "map_epoch": "stair_reactive", "map_revision": 1}
            response = post_json(base, "/goal", payload)
            journal.append({"event": "goal_request", "response": response, "payload": payload,
                            "sim_time_s": snap["sim_time_s"]})
            if not response.get("ok"):
                raise RuntimeError("stair goal rejected by backend")
        stop_at = 18.0 if scenario["mode"] == "stand" else 27.0
        unhealthy_since = None
        wall_deadline = time.monotonic() + scenario["max_wall_seconds"]
        while time.monotonic() < wall_deadline:
            snap = wait_snapshot(snapshots, args.run_id, timeout_s=2)
            state = get_json(base, "/state")
            good = health_ready(health, args.run_id, epoch, track_source)
            unhealthy_since = None if good else (unhealthy_since or time.monotonic())
            if unhealthy_since is not None and time.monotonic() - unhealthy_since > 1.0:
                raise RuntimeError("required sensor/terrain/track feed became unhealthy")
            journal.append({"event": "observation", "sim_time_s": snap["sim_time_s"],
                            "body_xyz": snap["measured"]["base_xyz"], "command": snap["applied_command"],
                            "health_ready": good, "terminal_results": state.get("terminal_results", [])})
            if snap["sim_time_s"] >= stop_at:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("episode wall deadline exceeded")
        if scenario["mode"] == "walk":
            response = post_json(base, "/cancel", {"request_id": args.run_id + "-end-observation",
                                                    "target_request_id": request_id})
            journal.append({"event": "end_observation_cancel", "response": response,
                            "sim_time_s": snap["sim_time_s"], "claim": "deadline cancellation is not avoidance"})
        dwell = None
        stop_deadline = time.monotonic() + 30.0
        while time.monotonic() < stop_deadline:
            snap = wait_snapshot(snapshots, args.run_id, timeout_s=2)
            if snapshot_stopped(snap, pilot):
                dwell = snap["sim_time_s"] if dwell is None else dwell
                if snap["sim_time_s"] - dwell >= 1.0:
                    break
            else:
                dwell = None
            time.sleep(0.05)
        else:
            raise RuntimeError("no measured post-observation stop")
        finish_request(finish_path, args.run_id, args.run_id + "-finish", epoch, "FINISHED", "bounded observation complete; avoidance scored offline")
        write_json(root / "artifacts/stair_driver_result.json", {
            "execution_completed": True, "mode": scenario["mode"], "journal": journal,
            "claim": "Execution/recording only; route, contact, fall and yield require full-rate offline review"})
    except BaseException as exc:
        try:
            post_json(base, "/cancel", {"request_id": args.run_id + "-driver-failure", "target_request_id": request_id})
        except Exception:
            pass
        if epoch is not None:
            finish_request(finish_path, args.run_id, args.run_id + "-failure", epoch, "FAILED", str(exc))
        write_json(root / "artifacts/stair_driver_result.json", {
            "execution_completed": False, "error": str(exc), "journal": journal})
        raise


if __name__ == "__main__":
    main()
