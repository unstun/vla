"""Replay immutable measured clouds through the unchanged ROS-free tracker."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import scipy

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "runs/stair_native_walk_v2"
BUILD = BASE / "builds/scan33_humble_amd64_v1"
sys.path.insert(0, str(BUILD / "src/scan_reactive_tracker"))
sys.path.insert(0, str(BASE / "runtime_sources/bridge/lite3_sim_bridge"))
from scan_reactive_tracker.core import CloudFrame, PoseObservation
from scan_reactive_tracker.io import terrain_from_pct_records
from scan_reactive_tracker.physical_ground_contract import PHYSICAL_GROUND_SHA256
from scan_reactive_tracker.static_background import load_building_background
from scan_reactive_tracker.static_foreground_tracker import StaticForegroundTracker
from pct_sim_clock_core import load_pinned_map, selected_ground_points


def stamp(header):
    return header["stamp"]["sec"] * 1_000_000_000 + header["stamp"]["nanosec"]


def inputs():
    manifest = json.loads((BUILD / "source_sha256.json").read_text())
    for path, expected in manifest.items():
        if hashlib.sha256((BUILD / path).read_bytes()).hexdigest() != expected:
            raise ValueError("Native baseline changed: " + path)
    observations = [json.loads(line) for line in (SOURCE / "artifacts/reactive_observations.jsonl").open()]
    poses, live, clouds = {}, {}, {}
    ground = next(r for r in observations if r["event"] == "tracker_ground")
    for row in observations:
        data = row["data"]
        if row["event"] == "lidar_pose":
            pose = data["pose"]["pose"]
            poses[stamp(data["header"])] = PoseObservation(stamp(data["header"]), data["header"]["frame_id"],
                data["child_frame_id"], tuple(pose["position"][k] for k in ("x", "y", "z")),
                tuple(pose["orientation"][k] for k in ("x", "y", "z", "w")))
        elif row["event"] == "tracks":
            live[stamp(data["header"])] = data
        elif row["event"] == "cloud":
            clouds[data["stamp_ns"]] = row
    points = selected_ground_points(load_pinned_map(BASE / "inputs/new_building.pickle"), cost_limit=None)
    raw = points.astype("<f4").tobytes()
    if hashlib.sha256(raw).hexdigest() != PHYSICAL_GROUND_SHA256:
        raise ValueError("Regenerated physical-ground payload differs from the run")
    terrain = terrain_from_pct_records(points.tolist(), raw, "world", ground["data"]["stamp_ns"], cost_limit=None)
    sensors = [json.loads(line) for line in (SOURCE / "sensor.jsonl").open()]
    return sensors, poses, live, clouds, ground, terrain


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    sensors, poses, live, clouds, ground, terrain = inputs()
    background = load_building_background(BASE / "inputs/static_background/building2_9.pcd")
    tracker = StaticForegroundTracker(background)
    rows = []
    for sensor in sensors:
        path = SOURCE / sensor["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != sensor["sha256"]:
            raise ValueError("Saved cloud bytes changed")
        points = np.load(path)["sensor_points"]
        ns = sensor["stamp_ns"]
        cloud = CloudFrame(ns, "lidar", points.tolist())
        # Reuse received ROS pose values and the original ground publication
        # boundary. No truth actor labels are consumed by the tracker.
        available_terrain = terrain if clouds[ns]["wall_monotonic_ns"] >= ground["wall_monotonic_ns"] else None
        snapshot = tracker.process(cloud, poses[ns], available_terrain, max(ns, clouds[ns]["clock_ns"]))
        observed = live.get(ns)
        match = observed is not None and observed["complete"] == snapshot.complete and len(observed["tracks"]) == len(snapshot.tracks)
        center_errors = []
        if match:
            for actual, expected in zip(snapshot.tracks, observed["tracks"]):
                center_errors.append(float(np.max(np.abs(np.asarray(actual.center) - [expected["center"][k] for k in ("x", "y", "z")]))))
                match = match and actual.id == expected["id"] and center_errors[-1] < 1e-6
        rows.append({"scan_index": sensor["sensor"]["scan_window"]["scan_index"], "sim_time_s": ns / 1e9,
            "snapshot": asdict(snapshot), "background_metrics": tracker.last_background_metrics,
            "matches_last_live_same_stamp": bool(match), "center_errors_m": center_errors,
            "states": {k: asdict(v) for k, v in tracker._states.items()}})
    (out / "tracker_replay.json").write_text(json.dumps(rows, indent=2) + "\n")
    failures = [r for r in rows if 12.5 < r["sim_time_s"] < 13.5 and not r["snapshot"]["complete"]]
    report = {"source_run": SOURCE.name, "frames": len(rows), "live_matches": sum(r["matches_last_live_same_stamp"] for r in rows),
        "mismatched_times_s": [r["sim_time_s"] for r in rows if not r["matches_last_live_same_stamp"]],
        "failure_times_s": [r["sim_time_s"] for r in failures], "failure_reasons": [r["snapshot"]["reason"] for r in failures],
        "numpy": np.__version__, "scipy": scipy.__version__, "tracker_parameters": asdict(tracker.p),
        "source_manifest_sha256": hashlib.sha256((BUILD / "source_sha256.json").read_bytes()).hexdigest(),
        "claim": "Original measured-cloud tracker core replay; no new simulation or tracking fix"}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if len(failures) != 2 or any(r["snapshot"]["reason"] != "unresolved_or_lost_cluster" for r in failures):
        raise AssertionError("The captured tracking interruption was not reproduced")


if __name__ == "__main__":
    main()
