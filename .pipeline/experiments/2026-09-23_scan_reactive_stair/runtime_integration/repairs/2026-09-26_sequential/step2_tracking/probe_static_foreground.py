"""Offline fixed-prior foreground probe; actual clouds remain immutable."""
import collections
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
RI = HERE.parents[2]
ROOT = RI.parents[3]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
sys.path.insert(0, str(P2B / "builds/scan_21/src/scan_reactive_tracker"))
from pct_sim_clock_core import load_pinned_map, selected_ground_points
from scan_reactive_tracker.core import (CloudFrame, MovingClusterTracker, PoseObservation,
                                       rotate_by_quaternion)
from scan_reactive_tracker.io import terrain_from_pct_records

PCD = ROOT / "references/upstream/2026-09-26_pct_building_static_background/source/building2_9.pcd"
PCD_SHA = "8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae"
STATIC_DISTANCE_M = 0.10
MIN_STATIC_MATCH_FRACTION = 0.80


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def load_tree():
    raw = PCD.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PCD_SHA:
        raise ValueError("static PCD identity mismatch")
    marker = b"DATA binary\n"
    header, body = raw.split(marker, 1)
    if b"FIELDS x y z normal_x normal_y normal_z\n" not in header or len(body) != 2_000_000 * 24:
        raise ValueError("static PCD layout mismatch")
    points = np.frombuffer(body, dtype="<f4").reshape(-1, 6)[:, :3]
    if not np.isfinite(points).all():
        raise ValueError("non-finite static map")
    return cKDTree(np.ascontiguousarray(points, dtype=np.float64))


def audit(name, tree, ground):
    run = RI / "runs" / name
    artifact = run / "returned_artifacts"
    robot = artifact / "runner_output"
    events = list(records(artifact / "reactive_observations.jsonl"))
    observed = {r["data"]["stamp_ns"] for r in events if r["event"] == "cloud"}
    stamps = {r["scan_id"]: r["timestamp_ns"] for r in records(robot / "sensor_metrics.jsonl")}
    terrain_stamp = next(r["data"]["stamp_ns"] for r in events if r["event"] == "pct_tomogram")
    terrain = terrain_from_pct_records(ground.tolist(), ground.tobytes(), "world", terrain_stamp, cost_limit=1e6)
    tracker = MovingClusterTracker()
    truth = list(records(robot / "official_human_truth.jsonl"))
    report = []
    for cloud in records(robot / "clouds.jsonl"):
        stamp = stamps[cloud["scan_id"]]
        if stamp not in observed:
            continue
        started = time.perf_counter()
        w, x, y, z = cloud["sensor_quaternion_wxyz"]
        pose = PoseObservation(stamp, "world", "lidar", tuple(cloud["sensor_position"]), (x, y, z, w))
        points = np.asarray(cloud["planner_points_sensor_frame"], dtype=np.float32)
        points = points[np.linalg.norm(points, axis=1) <= tracker.p.max_range_m]
        rotation = np.array([rotate_by_quaternion(axis, pose.quaternion_xyzw)
                             for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]).T
        world = points @ rotation.T + np.array(pose.position)
        distances, _ = tree.query(world, k=1)
        foreground = distances > STATIC_DISTANCE_M
        static_fraction = float(np.mean(~foreground))
        unknown_ground = sum(terrain.ground_below(*p) is None for p in world[foreground])
        result = tracker.process(CloudFrame(stamp, "lidar", points[foreground].tolist()), pose, terrain, stamp)
        coverage_ok = static_fraction >= MIN_STATIC_MATCH_FRACTION and unknown_ground == 0
        # Truth is only scored after the candidate has consumed measured data.
        actor = min(truth, key=lambda r: abs(r["sim_time_s"] - cloud["sim_time_s"]))["actor_truth"]["ground_xyz_m"]
        near = [t for t in result.tracks if np.linalg.norm(np.array(t.center[:2]) - actor[:2]) < 0.65]
        report.append({"scan_id": cloud["scan_id"], "sim_time_s": cloud["sim_time_s"],
                       "foreground_points": int(foreground.sum()), "unknown_foreground_ground": unknown_ground,
                       "static_match_fraction": static_fraction, "distance_p95_m": float(np.quantile(distances, .95)),
                       "core_complete": result.complete, "coverage_ok": coverage_ok,
                       "guarded_complete": result.complete and coverage_ok,
                       "tracks": [t.__dict__ for t in result.tracks], "actor_near_track_count": len(near),
                       "reason": result.reason, "wall_s": time.perf_counter() - started})
    summary = {"run": name, "frames": len(report),
               "complete_actor_frames": sum(r["guarded_complete"] and r["actor_near_track_count"] > 0 for r in report),
               "core_complete_actor_frames": sum(r["core_complete"] and r["actor_near_track_count"] > 0 for r in report),
               "pre_motion_track_frames": sum(r["sim_time_s"] < 10 and bool(r["tracks"]) for r in report),
               "outside_actor_track_frames": sum(len(r["tracks"]) > r["actor_near_track_count"] for r in report),
               "unknown_ground_frames": sum(r["unknown_foreground_ground"] > 0 for r in report),
               "poor_background_match_frames": sum(r["static_match_fraction"] < MIN_STATIC_MATCH_FRACTION for r in report),
               "track_ids": sorted({t["id"] for r in report for t in r["tracks"]}),
               "first_complete_actor_time_s": next((r["sim_time_s"] for r in report if r["guarded_complete"] and r["actor_near_track_count"]), None),
               "max_frame_wall_s": max(r["wall_s"] for r in report),
               "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                                 (robot / "clouds.jsonl", robot / "official_human_truth.jsonl", artifact / "reactive_observations.jsonl")}}
    return {"summary": summary, "frames": report}


def main():
    output = HERE / "static_foreground_probe.json"
    if output.exists():
        raise FileExistsError(output)
    tree = load_tree()
    ground = selected_ground_points(load_pinned_map(), cost_limit=1e6)
    value = {"script_sha256": sha(Path(__file__)), "pcd_sha256": PCD_SHA,
             "static_distance_m": STATIC_DISTANCE_M, "minimum_static_match_fraction": MIN_STATIC_MATCH_FRACTION,
             "ground_points": len(ground), "cluster_algorithm": "unchanged captured XY connected cells",
             "claim": "Offline feasibility probe with thresholds frozen before this full-sequence run. Existing core is not changed; coverage guard is reported separately. No raw obstacle point or runtime input altered.",
             "runs": []}
    for name in ("walk_v4_ego", "walk_v5_actor_right_v2"):
        result = audit(name, tree, ground)
        value["runs"].append(result)
        print(json.dumps(result["summary"], indent=2), flush=True)
    output.write_text(json.dumps(value, indent=2) + "\n")


if __name__ == "__main__":
    main()
