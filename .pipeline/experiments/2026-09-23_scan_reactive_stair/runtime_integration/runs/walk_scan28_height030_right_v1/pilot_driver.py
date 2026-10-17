#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.request


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def post_json(base, endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(base, endpoint):
    with urllib.request.urlopen(base + endpoint, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def snapshot_ok(snapshot, run_id, max_age_s=2.0):
    if snapshot.get("run_id") != run_id:
        return False
    if not isinstance(snapshot.get("applied_command"), dict):
        return False
    measured = snapshot.get("measured")
    if not isinstance(measured, dict):
        return False
    if not isinstance(measured.get("base_xyz"), list) or len(measured.get("base_xyz")) != 3:
        return False
    if not isinstance(measured.get("base_quat_wxyz"), list) or len(measured.get("base_quat_wxyz")) != 4:
        return False
    for key in ["horizontal_speed_mps", "yaw_rate_radps", "command_obs_error"]:
        if key not in measured:
            return False
    if snapshot.get("wall_monotonic_ns") is None:
        return False
    age = (time.monotonic_ns() - int(snapshot["wall_monotonic_ns"])) / 1e9
    return 0.0 <= age <= max_age_s


def wait_snapshot(path, run_id, min_sim_s=0.0, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = read_json(path)
        except Exception:
            time.sleep(0.05)
            continue
        last = snap
        if snapshot_ok(snap, run_id) and float(snap.get("sim_time_s", 0.0)) >= min_sim_s:
            return snap
        time.sleep(0.05)
    raise RuntimeError("fresh runner snapshot unavailable; last=%r" % (last,))


def xy_distance(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def current_body_xyz(snapshot):
    measured = snapshot.get("measured") or {}
    xyz = measured.get("base_xyz")
    if not isinstance(xyz, list) or len(xyz) != 3:
        raise RuntimeError("snapshot missing measured.base_xyz")
    return [float(x) for x in xyz]


def state_terminal_for(state, request_id, status):
    for item in state.get("terminal_results", []):
        if item.get("request_id") == request_id and item.get("status") == status:
            return item
    jobs = state.get("jobs") or {}
    item = jobs.get(request_id)
    if isinstance(item, dict) and item.get("status") == status:
        return item
    return None


def owner_none_is_not_success(state):
    service = state.get("service") or {}
    return service.get("current_owner") is None


def wait_terminal(base, request_id, status, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        state = get_json(base, "/state")
        last = state
        journal.append({"event": "state_poll", "request_id": request_id, "want": status, "state": state, "wall_monotonic_ns": time.monotonic_ns()})
        terminal = state_terminal_for(state, request_id, status)
        if terminal is not None:
            return terminal
        # owner None alone is explicitly recorded but never accepted as success.
        if owner_none_is_not_success(state):
            pass
        time.sleep(0.1)
    raise RuntimeError("timed out waiting for %s status %s; last=%r" % (request_id, status, last))


def wait_http_ready(base, journal, snapshot_path, run_id, observed_epoch, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
            state = get_json(base, "/state")
        except Exception as exc:
            last = str(exc)
            time.sleep(0.1)
            continue
        journal.append({"event": "http_ready_poll", "state": state, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        readiness = state.get("readiness") or {}
        applied_ready = readiness.get("applied_snapshot") or {}
        body_pose = state.get("measurement_body_pose")
        if (
            state.get("run_id") == run_id
            and int(state.get("run_epoch_ns", 0)) == int(observed_epoch)
            and readiness.get("body_pose_ready") is True
            and isinstance(body_pose, dict)
            and applied_ready.get("configured") is True
            and applied_ready.get("ready") is True
            and snapshot_ok(snap, run_id)
        ):
            return state
        last = state
        time.sleep(0.1)
    raise RuntimeError("HTTP backend not ready with body pose and applied snapshot; last=%r" % (last,))


def wait_displacement(snapshot_path, run_id, start_xyz, min_distance_m, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
        body = current_body_xyz(snap)
        distance = xy_distance(body, start_xyz)
        journal.append({"event": "cancel_distance_poll", "distance_xy_m": distance, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        if distance >= min_distance_m:
            return snap
        time.sleep(0.05)
    raise RuntimeError("cancel displacement threshold %.3f m not reached" % min_distance_m)


def wait_post_stop(snapshot_path, run_id, dwell_sim_s, thresholds, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    start_sim = None
    last_good = None
    while time.monotonic() < deadline:
        snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
        measured = snap.get("measured") or {}
        applied = snap.get("applied_command") or {}
        vx = float(applied.get("vx", 0.0))
        vy = float(applied.get("vy", 0.0))
        wz = float(applied.get("wz", 0.0))
        cmd_ok = math.hypot(vx, vy) <= thresholds["cmd"] and abs(wz) <= thresholds["cmd"]
        speed_ok = abs(float(measured.get("horizontal_speed_mps", 999.0))) <= thresholds["speed"]
        yaw_ok = abs(float(measured.get("yaw_rate_radps", 999.0))) <= thresholds["yaw"]
        if cmd_ok and speed_ok and yaw_ok:
            if start_sim is None:
                start_sim = float(snap.get("sim_time_s", 0.0))
            last_good = snap
            if float(snap.get("sim_time_s", 0.0)) - start_sim >= dwell_sim_s:
                journal.append({"event": "post_stop_proof", "snapshot": snap, "dwell_start_sim_s": start_sim, "wall_monotonic_ns": time.monotonic_ns()})
                return snap
        else:
            start_sim = None
        journal.append({"event": "post_stop_poll", "cmd_ok": cmd_ok, "speed_ok": speed_ok, "yaw_ok": yaw_ok, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        time.sleep(0.05)
    raise RuntimeError("post-stop proof dwell not reached; last_good=%r" % (last_good,))


def flush_journal(run_root, journal):
    write_json(Path(run_root) / "artifacts/pilot_journal_live.json", {"events": journal})


def finish_request(path, run_id, request_id, observed_epoch, status, note):
    path = Path(path)
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "request_id": request_id,
        "observed_run_epoch_ns": int(observed_epoch),
        "requested_at_monotonic_ns": time.monotonic_ns(),
        "backend_terminal_status": status,
        "note": note,
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


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
