"""Offline audit of captured inputs; never sends truth or commands to runtime."""
from __future__ import annotations

import collections
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
RI = HERE.parents[1]
ROOT = RI.parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
CORE_ROOT = P2B / "builds/scan_13/src/scan_reactive_tracker"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(P2B / "reactive_stair"))

from scan_reactive_tracker.core import (CloudFrame, MovingClusterTracker,
                                       PoseObservation, rotate_by_quaternion)
from scan_reactive_tracker.io import terrain_from_pct_records
from pct_sim_clock_core import load_pinned_map, selected_ground_points


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def stamp(header):
    value = header["stamp"]
    return value["sec"] * 1_000_000_000 + value["nanosec"]


def audit(name, ground):
    run = RI / "runs" / name
    artifacts = run / "returned_artifacts"
    robot = artifacts / "runner_output"
    events = list(rows(artifacts / "reactive_observations.jsonl"))
    accepted_stamps = {r["data"]["stamp_ns"] for r in events if r["event"] == "cloud"}
    sensor_stamps = {r["scan_id"]: r["timestamp_ns"] for r in rows(robot / "sensor_metrics.jsonl")}
    truth = list(rows(robot / "official_human_truth.jsonl"))
    origin = read(robot / "run_clock.json")["simulation_origin_s"]
    terrain_stamp = next(r["data"]["stamp_ns"] for r in events if r["event"] == "pct_tomogram")
    terrain = terrain_from_pct_records(ground.tolist(), ground.tobytes(), "world", terrain_stamp)
    tracker = MovingClusterTracker()
    frame_results = []
    counters = collections.Counter()
    for cloud in rows(robot / "clouds.jsonl"):
        ns = sensor_stamps[cloud["scan_id"]]
        if ns not in accepted_stamps:
            continue
        w, x, y, z = cloud["sensor_quaternion_wxyz"]
        pose = PoseObservation(ns, "world", "lidar", tuple(cloud["sensor_position"]), (x, y, z, w))
        # The archive rounds points to 4 decimal places. Float32 conversion
        # matches the published type, but cannot restore discarded decimals.
        points = np.asarray(cloud["planner_points_sensor_frame"], dtype=np.float32)
        snapshot = tracker.process(CloudFrame(ns, "lidar", points.tolist()), pose, terrain, ns)
        rotation = np.array([rotate_by_quaternion(axis, pose.quaternion_xyzw)
                             for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]).T
        world = points @ rotation.T + np.array(pose.position)
        actor_record = min(truth, key=lambda r: abs(r["sim_time_s"] - cloud["sim_time_s"]))
        actor = actor_record["actor_truth"]["ground_xyz_m"]
        # Truth is used ONLY for offline attribution to a spatial region.
        # This is not an object-ID measurement or a tracker input.
        region = ((np.linalg.norm(world[:, :2] - actor[:2], axis=1) < 0.32)
                  & (world[:, 2] > actor[2] + 0.45)
                  & (world[:, 2] < actor[2] + 1.70))
        stages = collections.Counter()
        for local, (wx, wy, wz) in zip(points[region], world[region]):
            stages["actor_region_returns"] += 1
            floor = terrain.ground_below(float(wx), float(wy), float(wz))
            if np.linalg.norm(local) > tracker.p.max_range_m:
                stages["range_rejected"] += 1
            elif floor is None:
                stages["no_selected_ground"] += 1
            elif not tracker.p.min_height_m <= wz - floor <= tracker.p.max_height_m:
                stages["height_rejected"] += 1
            else:
                stages["passes_point_filter"] += 1
        counters.update(stages)
        frame_results.append({"scan_id": cloud["scan_id"], "stamp_ns": ns,
                              "sim_time_s": cloud["sim_time_s"],
                              "complete": snapshot.complete, "reason": snapshot.reason,
                              "tracks": [t.__dict__ for t in snapshot.tracks],
                              "candidate_states": len(tracker._states),
                              "actor_region_filter": dict(stages)})
    live = [r for r in events if r["event"] == "tracks"]
    live_nonempty = [r for r in live if r["data"]["complete"] and r["data"]["tracks"]]
    replay_nonempty = [r for r in frame_results if r["complete"] and r["tracks"]]
    live_positive = {stamp(r["data"]["header"]) for r in live_nonempty}
    replay_positive = {r["stamp_ns"] for r in replay_nonempty}
    metrics = list(rows(robot / "metrics.jsonl"))
    journal = read(artifacts / "stair_driver_result.json")["journal"]
    goal = next(r for r in journal if r["event"] == "goal_request")
    state = min(metrics, key=lambda r: abs(r["sim_time_s"] - goal["sim_time_s"]))
    splines = []
    for event in events:
        if event["event"] != "bspline":
            continue
        pts = event["data"]["pos_pts"]
        spread = max(math.dist(tuple(pts[0].values()), tuple(p.values())) for p in pts)
        splines.append({"sim_time_s": event["clock_ns"] / 1e9 - origin,
                        "control_point_count": len(pts), "max_control_point_spread_m": spread})
    source_paths = [robot / p for p in ("clouds.jsonl", "sensor_metrics.jsonl", "official_human_truth.jsonl", "metrics.jsonl")]
    source_paths += [artifacts / "reactive_observations.jsonl", artifacts / "stair_driver_result.json"]
    return {"run": name, "recorded_cloud_frames": len(accepted_stamps),
            "replayed_frames": len(frame_results), "live_nonempty_frames": len(live_nonempty),
            "replay_nonempty_frames": len(replay_nonempty),
            "live_vs_replay_positive_stamp_symmetric_difference": sorted(live_positive ^ replay_positive),
            "all_frame_actor_region_filter_totals": dict(counters),
            "goal_request_sim_s": goal["sim_time_s"],
            "state_at_goal": {k: state[k] for k in ("sim_time_s", "stance_mode", "horizontal_speed_mps", "yaw_rate_radps")},
            "nonzero_admitted_commands": sum(any(v != 0 for v in r["admitted_command"]) for r in metrics),
            "bsplines": splines, "frames": frame_results,
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in source_paths}}


def main():
    output = HERE / "tracker_and_timing.json"
    if output.exists():
        raise FileExistsError(output)
    manifest = read(P2B / "builds/scan_13/source_sha256.json")
    sources = [CORE_ROOT / "scan_reactive_tracker" / name for name in ("core.py", "io.py", "node.py")]
    for path in sources:
        key = str(path.relative_to(P2B / "builds/scan_13"))
        if sha(path) != manifest[key]:
            raise ValueError("Captured tracker source changed: " + str(path))
    ground = selected_ground_points(load_pinned_map())
    result = {"script_sha256": sha(Path(__file__)), "tracker_source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
              "ground_sha256": hashlib.sha256(ground.tobytes()).hexdigest(),
              "claim": "Offline same-core replay with archived rounded points; no navigation inputs, policies or safety gates changed. Actor truth only identifies a posthoc spatial ROI.",
              "runs": []}
    for name in ("walk_v4_ego", "walk_v5_actor_right_v2"):
        value = audit(name, ground)
        result["runs"].append(value)
        print(json.dumps({k: v for k, v in value.items() if k not in ("frames", "source_sha256")}), flush=True)
    output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
