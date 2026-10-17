"""Adapt measured sensor fixtures to the existing unmodified SCAN replay tool."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from materialize import BASE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="static_human_detour")
    parser.add_argument("--goal-y", type=float)
    parser.add_argument("--planner-config", type=Path, default=Path(__file__).with_name("geometry_planner.yaml"))
    args = parser.parse_args()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    source = BASE / "runs/generic_temporal_sensor_v1" / args.case
    target = out / "inputs"
    target.mkdir()
    route_sample = next(row["data"] for row in json.loads(
        (BASE / "replays/old_positive_v1/inputs/events.json").read_text()) if row["kind"] == "pct_route")
    route = copy.deepcopy(route_sample)
    for name in ("run_id", "request_id", "goal_id", "route_id", "command_id"):
        route[name] = args.case + "-" + name
    route["map_epoch"] = "flat_sensor_fixture"
    start_goal = np.loadtxt(source / "start_goal.txt")
    start, goal = start_goal[:3], start_goal[3:]
    if args.goal_y is not None:
        goal[1] = args.goal_y
    pose_template = route["path"]["poses"][0]
    route["path"]["poses"] = []
    # The requested reference is a straight start-to-goal route, intentionally
    # crossing observed obstacles. No obstacle position helps construct it.
    for u in np.linspace(0., 1., 31):
        pose = copy.deepcopy(pose_template)
        pose["pose"]["position"] = dict(zip(("x", "y", "z"), (start + u * (goal - start)).tolist()))
        pose["header"]["stamp"] = {"sec": 3, "nanosec": 10_000_000}
        route["path"]["poses"].append(pose)
    route["path"]["header"]["stamp"] = {"sec": 3, "nanosec": 10_000_000}
    body_pose = np.loadtxt(source / "body_pose.txt")
    sensor_pose = np.loadtxt(source / "sensor_pose.txt")
    arrays = {"ground": np.fromfile(source / "ground.f32", dtype="<f4").reshape(-1, 4)}
    events = []
    files = (source / "clouds.txt").read_text().splitlines()
    for step in range(1, 201):
        stamp = 1_000_000_000 + step * 20_000_000
        body = {"position": body_pose[:3].tolist(), "quaternion": body_pose[[6, 3, 4, 5]].tolist(),
                "linear": [0., 0., 0.], "angular": [0., 0., 0.],
                "linear_body": [0., 0., 0.], "angular_body": [0., 0., 0.]}
        events.append({"stamp": stamp, "kind": "body", "data": body})
        if step % 5 == 0:
            index = step // 5 - 1
            key = f"cloud_{index}"
            arrays[key] = np.fromfile(source / files[index % len(files)], dtype="<f4").reshape(-1, 3)
            events.append({"stamp": stamp, "kind": "cloud", "data": {
                "array": key, "position": sensor_pose[:3].tolist(), "quaternion": sensor_pose[[6, 3, 4, 5]].tolist()}})
    events.append({"stamp": 3_010_000_000, "kind": "pct_route", "data": route})
    events.sort(key=lambda row: (row["stamp"], {"body": 0, "cloud": 1, "pct_route": 2}[row["kind"]]))
    np.savez_compressed(target / "points.npz", **arrays)
    (target / "events.json").write_text(json.dumps(events, indent=2) + "\n")
    shutil.copyfile(args.planner_config, target / "planner.yaml")
    (target / "input_manifest.json").write_text(json.dumps({
        "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in target.iterdir()},
        "measured_source": str(source), "semantic_track_events": 0,
        "claim": "Measured clouds replayed through the existing native planner. Requested reference is a straight line, not a truth-derived detour. Frozen body pose; not physical execution."
    }, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
