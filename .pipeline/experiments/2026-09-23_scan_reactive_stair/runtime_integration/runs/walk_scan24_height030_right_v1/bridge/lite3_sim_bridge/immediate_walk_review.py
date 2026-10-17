"""Audit an auxiliary run-start pedestrian preview without promoting acceptance."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from .isaac_adapter_core import point_to_segment_distance_2d
from .trajectory_review import associate_bspline_sim_times


def _load_json(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Mapping[str, object]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows:
        raise ValueError(f"required JSONL is empty: {path}")
    return rows


def point_to_polyline_distance_2d(
    point: Sequence[float], polyline: Sequence[Sequence[float]]
) -> float:
    if len(polyline) < 2:
        raise ValueError("polyline needs at least two points")
    return min(
        point_to_segment_distance_2d(point[:2], left[:2], right[:2])
        for left, right in zip(polyline, polyline[1:])
    )


def directional_plan_deviation_2d(
    later: Sequence[Sequence[float]], earlier: Sequence[Sequence[float]]
) -> float:
    """Measure later-plan geometry outside the earlier path, ignoring truncation."""

    if len(later) < 2 or len(earlier) < 2:
        raise ValueError("plan deviation needs two nontrivial polylines")
    return max(point_to_polyline_distance_2d(point, earlier) for point in later)


def causal_plan_replacement(
    plans: Sequence[Mapping[str, object]],
    metrics: Sequence[Mapping[str, object]],
    *,
    maximum_active_path_distance_m: float,
    minimum_plan_deviation_m: float,
    maximum_response_seconds: float,
) -> Mapping[str, object]:
    """Find a later distinct SCAN plan after the pedestrian enters the active plan."""

    if len(plans) < 2:
        return {"passed": False, "reason": "fewer than two SCAN plans"}
    for earlier, later in zip(plans, plans[1:]):
        earlier_time = float(earlier["effective_sim_time_seconds"])
        later_time = float(later["effective_sim_time_seconds"])
        active_rows = [
            row
            for row in metrics
            if earlier_time <= float(row["sim_time_seconds"]) <= later_time
            and row.get("dynamic_obstacle_actual_pos_w") is not None
        ]
        conflict_rows = []
        for row in active_rows:
            distance = point_to_polyline_distance_2d(
                row["dynamic_obstacle_actual_pos_w"], earlier["sampled_points"]
            )
            if distance <= maximum_active_path_distance_m:
                conflict_rows.append((row, distance))
        if not conflict_rows:
            continue
        first_row, first_distance = min(
            conflict_rows, key=lambda item: float(item[0]["sim_time_seconds"])
        )
        conflict_time = float(first_row["sim_time_seconds"])
        response_latency = later_time - conflict_time
        deviation = directional_plan_deviation_2d(
            later["sampled_points"], earlier["sampled_points"]
        )
        passed = (
            int(later["trajectory_id"]) != int(earlier["trajectory_id"])
            and 0.0 <= response_latency <= maximum_response_seconds
            and deviation >= minimum_plan_deviation_m
        )
        evidence = {
            "passed": passed,
            "active_trajectory_id": int(earlier["trajectory_id"]),
            "replacement_trajectory_id": int(later["trajectory_id"]),
            "first_active_path_intrusion_sim_time_seconds": conflict_time,
            "active_path_distance_m": first_distance,
            "replacement_sim_time_seconds": later_time,
            "response_latency_seconds": response_latency,
            "directional_plan_deviation_m": deviation,
        }
        if passed:
            return evidence
    return {
        "passed": False,
        "reason": "no later geometrically distinct plan followed active-path intrusion",
    }


def audit_immediate_walk(
    metrics: Sequence[Mapping[str, object]],
    sensor_metrics: Sequence[Mapping[str, object]],
    events: Sequence[Mapping[str, object]],
    run_identity: Mapping[str, object],
    *,
    expected_speed_mps: float = 0.8,
    maximum_active_path_distance_m: float = 0.85,
    minimum_plan_deviation_m: float = 0.15,
    maximum_response_seconds: float = 2.5,
) -> Mapping[str, object]:
    dynamic_identity = run_identity.get("dynamic_obstacle") or {}
    static_precheck = dynamic_identity.get("static_route_precheck") or {}
    crossing = [row for row in metrics if row.get("dynamic_obstacle_phase") == "crossing"]
    speeds = [
        math.hypot(*[float(value) for value in row["dynamic_obstacle_scheduled_lin_vel_w"][:2]])
        for row in crossing
    ]
    contacts = [float(row.get("nonfoot_contact_max_n", 0.0)) for row in metrics]
    clearances = [
        float(row.get("root_to_dynamic_surface_clearance_m", -math.inf))
        for row in metrics
    ]
    lidar_detections = [
        row
        for row in sensor_metrics
        if int(row.get("dynamic_obstacle_surface_hit_count", 0)) > 0
    ]
    plans = associate_bspline_sim_times(events)
    causal = causal_plan_replacement(
        plans,
        metrics,
        maximum_active_path_distance_m=maximum_active_path_distance_m,
        minimum_plan_deviation_m=minimum_plan_deviation_m,
        maximum_response_seconds=maximum_response_seconds,
    )
    checks = {
        "run_start_trigger": dynamic_identity.get("schedule_trigger_mode") == "run_start",
        "static_route_precheck": static_precheck.get("passed") is True,
        "continuous_crossing": bool(crossing)
        and sum(row.get("dynamic_obstacle_phase") == "holding" for row in metrics) == 0
        and sum(row.get("dynamic_obstacle_phase") == "parked" for row in metrics) == 0,
        "constant_speed": bool(speeds)
        and max(abs(speed - expected_speed_mps) for speed in speeds) <= 1.0e-9,
        "lidar_detected_human": bool(lidar_detections),
        "causal_scan_plan_replacement": causal.get("passed") is True,
        "positive_robot_human_clearance": bool(clearances) and min(clearances) > 0.0,
        "zero_nonfoot_contact": bool(contacts) and max(contacts) <= 1.0e-6,
    }
    return {
        "schema_version": 1,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "claim_boundary": (
            "auxiliary run-start pedestrian visual and causal-local-plan audit; "
            "not frozen V8 R2 acceptance"
        ),
        "checks": checks,
        "static_route_precheck": static_precheck,
        "crossing_record_count": len(crossing),
        "speed_min_mps": min(speeds, default=None),
        "speed_max_mps": max(speeds, default=None),
        "lidar_detection_count": len(lidar_detections),
        "trajectory_ids": [int(plan["trajectory_id"]) for plan in plans],
        "causal_plan_replacement": causal,
        "minimum_robot_human_surface_clearance_m": min(clearances, default=None),
        "maximum_nonfoot_contact_n": max(contacts, default=None),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--sensor-metrics", type=Path, required=True)
    parser.add_argument("--ros-events", type=Path, required=True)
    parser.add_argument("--run-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit_immediate_walk(
        _load_jsonl(args.metrics),
        _load_jsonl(args.sensor_metrics),
        _load_jsonl(args.ros_events),
        _load_json(args.run_identity),
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
