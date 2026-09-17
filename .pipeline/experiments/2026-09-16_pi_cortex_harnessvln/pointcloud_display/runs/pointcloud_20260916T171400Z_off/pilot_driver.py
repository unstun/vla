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
    raise RuntimeError("cancel displacement threshold not reached")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run_root = Path(args.run_root)
    pilot = read_json(run_root / "inputs/pilot.json")
    snapshot_path = run_root / "artifacts/external_episode/current_command.json"
    finish_path = run_root / "artifacts/external_episode/finish_request.json"
    journal = []
    base = "http://127.0.0.1:%d" % args.http_port
    thresholds = {"cmd": pilot["stop_command_norm"], "speed": pilot["stop_speed_mps"], "yaw": pilot["stop_yaw_rate_radps"]}
    final_status = "FAILED"
    observed_epoch = 0
    try:
        initial = wait_snapshot(snapshot_path, args.run_id, min_sim_s=0.0)
        observed_epoch = int(initial["run_epoch_ns"])
        start_xyz = current_body_xyz(initial)
        journal.append({"event": "initial_cancel_reference_snapshot", "snapshot": initial, "start_xyz": start_xyz, "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        ready = wait_http_ready(base, journal, snapshot_path, args.run_id, observed_epoch)
        journal.append({"event": "backend_ready", "state": ready})
        flush_journal(run_root, journal)

        goal_a = pilot["goals"][0]
        goal_b = pilot["goals"][1]
        request_a1 = args.run_id + "-goal-a-attempt-1"
        payload_a1 = {"request_id": request_a1, "goal_id": "goal-a", "target_ground_xyz": goal_a["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_a1)
        journal.append({"event": "post_goal", "payload": payload_a1, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-a attempt1 rejected: %r" % (resp,))
        moved = wait_displacement(snapshot_path, args.run_id, start_xyz, 0.4, journal)
        cancel_resp = post_json(base, "/cancel", {"request_id": args.run_id + "-cancel-goal-a-attempt-1", "target_request_id": request_a1})
        journal.append({"event": "post_cancel", "response": cancel_resp, "trigger_snapshot": moved, "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        wait_terminal(base, request_a1, "cancelled", journal, timeout_s=120.0)
        wait_post_stop(snapshot_path, args.run_id, pilot["stop_dwell_sim_seconds"], thresholds, journal, timeout_s=120.0)

        request_a2 = args.run_id + "-goal-a-attempt-2"
        payload_a2 = {"request_id": request_a2, "goal_id": "goal-a", "target_ground_xyz": goal_a["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_a2)
        journal.append({"event": "post_goal", "payload": payload_a2, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-a attempt2 rejected: %r" % (resp,))
        wait_terminal(base, request_a2, "arrived", journal, timeout_s=240.0)

        request_b = args.run_id + "-goal-b"
        payload_b = {"request_id": request_b, "goal_id": "goal-b", "target_ground_xyz": goal_b["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_b)
        journal.append({"event": "post_goal", "payload": payload_b, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-b rejected: %r" % (resp,))
        wait_terminal(base, request_b, "arrived", journal, timeout_s=240.0)
        final_status = "FINISHED"
        finish_request(finish_path, args.run_id, args.run_id + "-finish", observed_epoch, "FINISHED", "two arrivals and one explicit cancel confirmed by backend")
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": True, "events": journal})
        return 0
    except Exception as exc:
        journal.append({"event": "driver_error", "error": str(exc), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        try:
            post_json(base, "/cancel", {"request_id": args.run_id + "-failure-cancel"})
        except Exception as cancel_exc:
            journal.append({"event": "failure_cancel_error", "error": str(cancel_exc), "wall_monotonic_ns": time.monotonic_ns()})
        finish_request(finish_path, args.run_id, args.run_id + "-failed-finish", observed_epoch, "FAILED", str(exc))
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": False, "error": str(exc), "events": journal})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
