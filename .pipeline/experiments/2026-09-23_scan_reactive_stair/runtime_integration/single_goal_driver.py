#!/usr/bin/env python3
"""Bounded one-goal backend driver; requires a separately reviewed live worker.

This process reads robot/backend observations and runtime health only. Human
actor truth stays outside this process and may be used for outcome scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import time
import urllib.request


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def post(base: str, endpoint: str, value: dict) -> dict:
    request = urllib.request.Request(
        base + endpoint, data=json.dumps(value).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode())


def get(base: str, endpoint: str) -> dict:
    with urllib.request.urlopen(base + endpoint, timeout=5) as response:
        return json.loads(response.read().decode())


def fresh_snapshot(path: Path, run_id: str, epoch: int | None = None) -> dict:
    snapshot = read(path)
    if snapshot.get("run_id") != run_id:
        raise RuntimeError("runner snapshot has wrong run ID")
    if epoch is not None and snapshot.get("run_epoch_ns") != epoch:
        raise RuntimeError("runner epoch changed")
    age_s = (time.monotonic_ns() - int(snapshot["wall_monotonic_ns"])) / 1e9
    if not 0 <= age_s <= 2.0:
        raise RuntimeError("runner snapshot stale or from another clock")
    measured = snapshot.get("measured") or {}
    if len(measured.get("base_xyz") or []) != 3 or not isinstance(snapshot.get("applied_command"), dict):
        raise RuntimeError("runner snapshot lacks measured pose or applied command")
    return snapshot


def runtime_health(path: Path, run_id: str, epoch: int) -> dict:
    health = read(path)
    if health.get("run_id") != run_id or health.get("run_epoch_ns") != epoch:
        raise RuntimeError("runtime health identity mismatch")
    age_s = (time.monotonic_ns() - int(health["wall_monotonic_ns"])) / 1e9
    if not 0 <= age_s <= 2.0:
        raise RuntimeError("runtime health stale or from another clock")
    required = {
        "clock_advancing": True,
        "sidecar_alive": True,
        "tracker_alive": True,
        "scan_alive": True,
        "pct_socket_worker_alive": True,
        "pct_tomogram_publisher_count": 1,
        "track_source": "sensor_lidar_current_only",
        "track_snapshot_complete": True,
        "ros_domain_id": 192,
    }
    if any(health.get(key) != value for key, value in required.items()):
        raise RuntimeError("runtime health lacks live sensor/clock/process proof")
    stamps = health.get("stamps_ns") or {}
    if not all(isinstance(stamps.get(key), int) and stamps[key] > 0
               for key in ("clock", "pct_tomogram", "cloud", "lidar_pose", "tracked_person_snapshot")):
        raise RuntimeError("runtime health lacks topic stamps")
    if stamps["cloud"] != stamps["lidar_pose"]:
        raise RuntimeError("LiDAR cloud and pose stamps differ")
    if stamps["tracked_person_snapshot"] > stamps["clock"]:
        raise RuntimeError("track snapshot lies in the future")
    if stamps["clock"] - stamps["tracked_person_snapshot"] > 500_000_000:
        raise RuntimeError("current track snapshot is stale")
    if stamps["clock"] - stamps["cloud"] > 500_000_000:
        raise RuntimeError("LiDAR cloud is stale")
    # A complete empty snapshot is a valid current observation after a person
    # leaves the sensor view. Whether a person was ever observed is scored
    # separately from process health and cannot turn a deadline stop into yield.
    if (not isinstance(health.get("tracked_person_count"), int)
            or isinstance(health["tracked_person_count"], bool)
            or health["tracked_person_count"] < 0):
        raise RuntimeError("invalid current sensor-derived track count")
    return health


def stopped(snapshot: dict, goal: dict) -> bool:
    measured = snapshot["measured"]
    command = snapshot["applied_command"]
    values = [command.get(key) for key in ("vx", "vy", "wz")]
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
        return False
    vx, vy, wz = values
    return (math.hypot(vx, vy) <= goal["stop_command_norm"]
            and abs(wz) <= goal["stop_command_norm"]
            and abs(measured.get("horizontal_speed_mps", math.inf)) <= goal["stop_speed_mps"]
            and abs(measured.get("yaw_rate_radps", math.inf)) <= goal["stop_yaw_rate_radps"])


def terminal(state: dict, request_id: str) -> str | None:
    for result in state.get("terminal_results") or []:
        if result.get("request_id") == request_id:
            return result.get("status")
    job = (state.get("jobs") or {}).get(request_id)
    return job.get("status") if isinstance(job, dict) else None


def finish(path: Path, run_id: str, epoch: int, status: str, note: str) -> None:
    payload = {
        "schema_version": 1, "run_id": run_id, "request_id": run_id + "-finish",
        "observed_run_epoch_ns": epoch, "requested_at_monotonic_ns": time.monotonic_ns(),
        "backend_terminal_status": status, "note": note,
    }
    temporary = path.with_name(path.name + ".tmp")
    write(temporary, payload)
    temporary.replace(path)


def verify_package(run_root: Path, run_id: str) -> dict:
    gate = read(run_root / "execution_gate.json")
    package = read(run_root / "package_status.json")
    if gate.get("passed") is not True or package.get("execution_allowed") is not True:
        raise RuntimeError("package execution gates are not approved")
    manifest = read(run_root / "source_manifest.json")
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise RuntimeError("package source manifest is empty")
    for relative, expected in manifest.get("files", {}).items():
        path = (run_root / relative).resolve()
        if run_root.resolve() not in path.parents or not path.is_file():
            raise RuntimeError("package source missing or outside run root: " + relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("package source SHA-256 mismatch: " + relative)
    if read(run_root / "evidence/first_hit_result.json").get("passed") is not True:
        raise RuntimeError("official human LiDAR first-hit has not passed")
    build = read(run_root / "evidence/scan_build_result.json")
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise RuntimeError("SCAN build/source gate has not passed")
    goal = read(run_root / "inputs/single_goal.json")
    xyz = goal.get("goal_ground_xyz_m")
    if goal.get("status") != "reviewed_stair_goal" or not isinstance(xyz, list) or len(xyz) != 3:
        raise RuntimeError("single stair goal has not been reviewed")
    if goal.get("frame_id") != "world" or not all(isinstance(x, (float, int)) and math.isfinite(x) for x in xyz):
        raise RuntimeError("goal world coordinates invalid")
    spawn = goal.get("spawn_ground_xyz_m")
    route = read(run_root / "inputs/actor_route.proposed.json")
    actor_source = (run_root / "runner/official_building_human.py").read_text(encoding="utf-8")
    match = re.search(r"^APPROVED_ROUTE_SHA256\s*=\s*[\"']([0-9a-f]{64})[\"']$",
                      actor_source, re.MULTILINE)
    if match is None or hashlib.sha256((run_root / "inputs/actor_route.proposed.json").read_bytes()).hexdigest() != match.group(1):
        raise RuntimeError("actor route lacks matching source-pinned approval")
    if route.get("geometry_reviewed") is not True:
        raise RuntimeError("actor route geometry has not been reviewed")
    actor_points = (route.get("official_human") or {}).get("waypoints_ground_xyz_m") or route.get("waypoints_ground_xyz_m")
    if (not isinstance(spawn, list) or len(spawn) != 3
            or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in spawn)
            or not isinstance(actor_points, list) or not actor_points):
        raise RuntimeError("reviewed robot spawn and actor route are required")
    actor_start = actor_points[0]
    distance = math.hypot(spawn[0] - actor_start[0], spawn[1] - actor_start[1])
    # 0.18 m double-cylinder forward offset + 0.25 m robot radius +
    # 0.30 m person occupancy radius + 0.10 m review margin.
    if distance <= 0.83:
        raise RuntimeError("initial robot/person separation %.3f m <= 0.83 m" % distance)
    if package.get("run_id") != run_id:
        raise RuntimeError("package run ID mismatch")
    return goal


def drive(run_root: Path, run_id: str, http_port: int) -> dict:
    goal = verify_package(run_root, run_id)
    if not 1 <= http_port <= 65535:
        raise ValueError("HTTP port outside valid range")
    base = f"http://127.0.0.1:{http_port}"
    snapshot_path = run_root / "artifacts/external_episode/current_command.json"
    finish_path = run_root / "artifacts/external_episode/finish_request.json"
    health_path = run_root / "artifacts/runtime_health.json"
    journal_path = run_root / "artifacts/single_goal_journal.json"
    start = time.monotonic()
    observations = []
    request_id = run_id + "-stair-goal"
    epoch = None
    outcome = "FAILED"
    try:
        snapshot = fresh_snapshot(snapshot_path, run_id)
        epoch = int(snapshot["run_epoch_ns"])
        runtime_health(health_path, run_id, epoch)
        state = get(base, "/state")
        ready = state.get("readiness") or {}
        if (state.get("run_id") != run_id or state.get("run_epoch_ns") != epoch
                or ready.get("body_pose_ready") is not True
                or (ready.get("applied_snapshot") or {}).get("ready") is not True):
            raise RuntimeError("backend has no fresh body/applied readiness")
        payload = {
            "request_id": request_id, "goal_id": goal["goal_id"],
            "target_ground_xyz": goal["goal_ground_xyz_m"], "frame": goal["frame_id"],
            "map_epoch": goal["map_epoch"], "map_revision": goal["map_revision"],
        }
        response = post(base, "/goal", payload)
        observations.append({"event": "goal_request", "payload": payload, "response": response,
                             "sim_time_s": snapshot["sim_time_s"]})
        if response.get("ok") is not True:
            raise RuntimeError("backend rejected reviewed stair goal")
        deadline = start + min(float(goal["max_wall_seconds"]), 1200.0)
        while time.monotonic() < deadline:
            snapshot = fresh_snapshot(snapshot_path, run_id, epoch)
            health = runtime_health(health_path, run_id, epoch)
            state = get(base, "/state")
            status = terminal(state, request_id)
            observations.append({"event": "observation", "sim_time_s": snapshot["sim_time_s"],
                                 "body_xyz": snapshot["measured"]["base_xyz"],
                                 "applied_command": snapshot["applied_command"],
                                 "track_stamp_ns": health["stamps_ns"]["tracked_person_snapshot"],
                                 "tracked_person_count": health["tracked_person_count"],
                                 "terminal_status": status})
            if status == "arrived":
                outcome = "ARRIVED"
                break
            if status in ("failed", "cancelled", "rejected", "stopped", "ignored"):
                raise RuntimeError("backend goal terminated: " + status)
            if float(snapshot["sim_time_s"]) >= float(goal["max_sim_seconds"]):
                break
            time.sleep(0.1)
        if outcome != "ARRIVED":
            cancel_response = post(base, "/cancel", {"request_id": run_id + "-deadline-cancel",
                                                    "target_request_id": request_id})
            observations.append({"event": "deadline_cancel", "response": cancel_response})
            dwell_start = None
            stop_deadline = min(start + 1200.0, time.monotonic() + 15.0)
            while time.monotonic() < stop_deadline:
                snapshot = fresh_snapshot(snapshot_path, run_id, epoch)
                state = get(base, "/state")
                if terminal(state, request_id) == "cancelled" and stopped(snapshot, goal):
                    if dwell_start is None:
                        dwell_start = float(snapshot["sim_time_s"])
                    if float(snapshot["sim_time_s"]) - dwell_start >= goal["stop_dwell_sim_seconds"]:
                        outcome = "DEADLINE_STOPPED"
                        break
                else:
                    dwell_start = None
                time.sleep(0.05)
            if outcome != "DEADLINE_STOPPED":
                raise RuntimeError("deadline reached without measured safe stop")
        finish(finish_path, run_id, epoch, "FINISHED" if outcome == "ARRIVED" else "FAILED", outcome)
        result = {"outcome": outcome, "observations": observations,
                  "avoidance_assessment": "unassessed: no obstacle-linked SCAN correction evidence",
                  "claim": "One bounded simulator request only; deadline stop is not pedestrian avoidance; actor contact remains unverified"}
        write(journal_path, result)
        return result
    except BaseException as error:
        observations.append({"event": "driver_error", "error": str(error)})
        try:
            post(base, "/cancel", {"request_id": run_id + "-failure-cancel",
                                   "target_request_id": request_id})
        except Exception as cancel_error:
            observations.append({"event": "cancel_error", "error": str(cancel_error)})
        if epoch is not None:
            finish(finish_path, run_id, epoch, "FAILED", str(error))
        write(journal_path, {"outcome": "FAILED", "error": str(error),
                             "observations": observations})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(drive(args.run_root, args.run_id, args.http_port), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
