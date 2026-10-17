"""Trace the original shape-candidate gate on the captured failure frames."""
from dataclasses import asdict
import inspect
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

from diagnose_tracker_replay import BASE, SOURCE, inputs
from scan_reactive_tracker.core import CloudFrame, TrackerParameters, shape_candidates
from scan_reactive_tracker.static_background import load_building_background


def trace_candidates(cloud, pose, terrain, parameters):
    source, first_line = inspect.getsourcelines(shape_candidates)
    checkpoint = first_line + next(i for i, line in enumerate(source) if "if len(component) < p.min_cluster_points:" in line)
    components, bucket_counts = [], []

    def observe(frame, event, arg):
        if frame.f_code is not shape_candidates.__code__:
            return None
        if event == "line" and frame.f_lineno == checkpoint:
            points = np.asarray(frame.f_locals["component"])
            span = np.ptp(points, axis=0)
            horizontal = math.hypot(*span[:2])
            reasons = []
            if len(points) < parameters.min_cluster_points:
                reasons.append("point_count")
            if not parameters.min_horizontal_span_m <= horizontal <= parameters.max_horizontal_span_m:
                reasons.append("horizontal_span")
            if span[2] < parameters.min_vertical_span_m:
                reasons.append("vertical_span")
            components.append({"count": len(points), "min_xyz": points.min(axis=0).tolist(),
                "max_xyz": points.max(axis=0).tolist(), "center_xyz": points.mean(axis=0).tolist(),
                "horizontal_span_m": horizontal, "vertical_span_m": float(span[2]),
                "failed_gates": reasons, "points_world": points.tolist()})
        elif event == "return":
            bucket_counts.append(sum(len(points) for points in frame.f_locals["buckets"].values()))
        return observe

    previous = sys.gettrace()
    sys.settrace(observe)
    try:
        detections = shape_candidates(cloud, pose, terrain, parameters)
    finally:
        sys.settrace(previous)
    if len(detections) != sum(not c["failed_gates"] for c in components):
        raise AssertionError("Instrumented gates do not match original returned detections")
    return detections, components, bucket_counts[-1]


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    sensors, poses, _, _, _, terrain = inputs()
    background = load_building_background(BASE / "inputs/static_background/building2_9.pcd")
    parameters = TrackerParameters()
    baseline = json.loads((BASE / "runs/tracking_replay_diagnosis_v1/tracker_replay.json").read_text())
    rows = []
    for i in range(124, 134):
        sensor = sensors[i]
        points = np.load(SOURCE / sensor["file"])["sensor_points"]
        pose = poses[sensor["stamp_ns"]]
        cloud = CloudFrame(pose.stamp_ns, "lidar", points.tolist())
        selected = background.select(cloud, pose, parameters)
        detections, components, height_kept = trace_candidates(selected.cloud, pose, terrain, parameters)
        unfiltered, raw_components, _ = trace_candidates(cloud, pose, terrain, parameters)
        previous = baseline[i - 1]["states"].get("cluster-1")
        rows.append({"scan_index": i, "sim_time_s": pose.stamp_ns / 1e9,
            "input_points": len(points), "foreground_points": len(selected.cloud.points), "height_kept": height_kept,
            "human_hit_count_scoring_only": sensor["sensor"]["human_hit_count_scoring_only"],
            "components": components, "detections": [asdict(d) for d in detections],
            "previous_observation_center": None if previous is None else [previous[k] for k in ("x", "y", "z")],
            "association_distances_m": [] if previous is None else [math.hypot(d.x-previous["x"], d.y-previous["y"]) for d in detections],
            "background_removed_counterfactual": {"detections": [asdict(d) for d in unfiltered], "components": raw_components},
            "counterfactual_scope": "Diagnostic only; dropping background classification is not a proposed accepted input"})
    (out / "gate_trace.json").write_text(json.dumps(rows, indent=2) + "\n")
    brief = [{k: r[k] for k in ("scan_index", "sim_time_s", "input_points", "foreground_points", "height_kept",
        "human_hit_count_scoring_only", "detections", "association_distances_m")} |
        {"components": [{k:v for k,v in c.items() if k != "points_world"} for c in r["components"]]} for r in rows]
    (out / "result.json").write_text(json.dumps({"parameters": asdict(parameters), "frames": brief,
        "original_candidate_function_traced": True, "production_code_changed": False}, indent=2) + "\n")
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
