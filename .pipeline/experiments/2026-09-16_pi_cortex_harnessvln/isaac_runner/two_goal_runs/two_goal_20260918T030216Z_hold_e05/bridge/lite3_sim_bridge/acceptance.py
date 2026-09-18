"""Evaluate a frozen SCAN-to-Lite3 physical-simulation acceptance run."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Dict, Iterable, List, Mapping, Sequence

from .isaac_adapter_core import point_to_segment_distance_2d


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> List[Mapping[str, object]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows:
        raise ValueError(f"required JSONL is empty: {path}")
    return rows


def _percentile(values: Iterable[float], quantile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered or not 0.0 <= quantile <= 1.0:
        raise ValueError("percentile needs values and a quantile within [0, 1]")
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _rate(rows: Sequence[Mapping[str, object]]) -> float:
    duration = float(rows[-1]["sim_time_seconds"]) - float(rows[0]["sim_time_seconds"])
    return 0.0 if len(rows) < 2 or duration <= 0.0 else (len(rows) - 1) / duration


def _key_value_lines(text: str) -> Mapping[str, str]:
    values = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _yaml_numeric_value(text: str, key: str) -> float:
    pattern = re.compile(
        rf"^\s*{re.escape(key)}:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*(?:#.*)?$"
    )
    matches = [pattern.match(line) for line in text.splitlines()]
    values = [float(match.group(1)) for match in matches if match is not None]
    if len(values) != 1 or not math.isfinite(values[0]):
        raise ValueError(f"expected one finite YAML value for {key}, got {values}")
    return values[0]


def evaluate_acceptance(
    thresholds: Mapping[str, object],
    metrics: Sequence[Mapping[str, object]],
    sensor_metrics: Sequence[Mapping[str, object]],
    isaac_report: Mapping[str, object],
    run_identity: Mapping[str, object],
    ros_summary: Mapping[str, object],
    video_path: Path,
    rosbag_dir: Path,
    foxy_log_text: str,
    threshold_sha256: str,
    depth_metrics: Sequence[Mapping[str, object]] = None,
    runtime_composition: Mapping[str, object] = None,
    depth_artifact_root: Path = None,
    overlay_video_path: Path = None,
    trajectory_events: Sequence[Mapping[str, object]] = None,
    trajectory_review_metadata: Mapping[str, object] = None,
    trajectory_review_input_sha256: Mapping[str, str] = None,
    effective_input_text: str = None,
    planner_config_text: str = None,
    controller_config_text: str = None,
) -> Dict[str, object]:
    limits = thresholds["thresholds"]
    goal = thresholds["goal_world_m"]
    v7 = thresholds.get("v7_dynamic_obstacle")
    v8 = thresholds.get("v8_human_obstacle")
    v8_official = thresholds.get("v8_official_human_obstacle")
    checks = {}

    def add(name: str, passed: bool, value, expected) -> None:
        checks[name] = {"passed": bool(passed), "value": value, "expected": expected}

    duration = float(metrics[-1]["sim_time_seconds"]) - float(
        metrics[0]["sim_time_seconds"]
    )
    final_position = [float(value) for value in metrics[-1]["root_pos_w"]]
    goal_xy_error = math.dist(final_position[:2], [float(goal[0]), float(goal[1])])
    goal_z_error = abs(final_position[2] - float(goal[2]))
    goal_stop_event = None
    if v7 is not None:
        goal_xy_tolerance = float(limits["goal_xy_tolerance_m"])
        stop_window_seconds = float(limits["stop_window_seconds"])
        stop_command_limit = float(limits["stop_command_max_abs"])
        stop_speed_limit = float(limits["stop_planar_speed_max_mps"])
        for start_index, start_row in enumerate(metrics):
            start_time = float(start_row["sim_time_seconds"])
            end_index = start_index
            while (
                end_index < len(metrics)
                and float(metrics[end_index]["sim_time_seconds"]) - start_time
                < stop_window_seconds
            ):
                end_index += 1
            if end_index >= len(metrics):
                break
            window_rows = metrics[start_index : end_index + 1]
            window_goal_errors = [
                math.dist(
                    [float(value) for value in row["root_pos_w"][:2]],
                    [float(goal[0]), float(goal[1])],
                )
                for row in window_rows
            ]
            window_command = max(
                max(abs(float(value)) for value in row["applied_command"])
                for row in window_rows
            )
            window_speed = max(
                math.hypot(
                    float(row["root_lin_vel_w"][0]),
                    float(row["root_lin_vel_w"][1]),
                )
                for row in window_rows
            )
            if (
                max(window_goal_errors) <= goal_xy_tolerance
                and window_command <= stop_command_limit
                and window_speed <= stop_speed_limit
            ):
                anchor_position = [
                    float(value) for value in metrics[end_index]["root_pos_w"][:2]
                ]
                goal_stop_event = {
                    "start_index": start_index,
                    "end_index": end_index,
                    "start_sim_time_seconds": start_time,
                    "end_sim_time_seconds": float(
                        metrics[end_index]["sim_time_seconds"]
                    ),
                    "maximum_goal_error_m": max(window_goal_errors),
                    "maximum_command_abs": window_command,
                    "maximum_planar_speed_mps": window_speed,
                    "anchor_position_w_xy_m": anchor_position,
                }
                break
    stop_start = float(metrics[-1]["sim_time_seconds"]) - float(
        limits["stop_window_seconds"]
    )
    stop_rows = [row for row in metrics if float(row["sim_time_seconds"]) >= stop_start]
    stop_command = max(
        max(abs(float(value)) for value in row["applied_command"]) for row in stop_rows
    )
    stop_speed = max(
        math.hypot(float(row["root_lin_vel_w"][0]), float(row["root_lin_vel_w"][1]))
        for row in stop_rows
    )
    command_max = [
        max(abs(float(row["applied_command"][index])) for row in metrics)
        for index in range(3)
    ]
    command_bounds = [float(value) for value in limits["command_component_max_abs"]]
    bound_epsilon = float(limits["command_bound_epsilon"])
    step_displacements = [
        math.dist(left["root_pos_w"], right["root_pos_w"])
        for left, right in zip(metrics, metrics[1:])
    ]
    support_fraction = sum(int(row["contact_count"]) >= 1 for row in metrics) / len(metrics)
    obstacle_window = thresholds["obstacle"]["detour_x_window_m"]
    near_obstacle = [
        row
        for row in metrics
        if float(obstacle_window[0])
        <= float(row["root_pos_w"][0])
        <= float(obstacle_window[1])
    ]
    detour_abs_y = (
        min(abs(float(row["root_pos_w"][1])) for row in near_obstacle)
        if near_obstacle
        else 0.0
    )
    policy_rate = _rate(metrics)
    sensor_rate = _rate(sensor_metrics)
    cloud_nonempty = sum(int(row["point_count"]) > 0 for row in sensor_metrics) / len(
        sensor_metrics
    )
    sensor_displacement = math.dist(
        sensor_metrics[0]["sensor_position_w"], sensor_metrics[-1]["sensor_position_w"]
    )
    command_age_p95 = _percentile(
        (float(row["command_age_ms"]) for row in metrics), 0.95
    )

    add("isaac_runtime_pass", isaac_report.get("status") == "PASS", isaac_report.get("status"), "PASS")
    add("isaac_runtime_error", isaac_report.get("runtime_error") is None, isaac_report.get("runtime_error"), None)
    add("record_count", len(metrics) >= int(limits["minimum_record_count"]), len(metrics), limits["minimum_record_count"])
    add("sim_duration", duration >= float(limits["minimum_sim_duration_seconds"]), duration, limits["minimum_sim_duration_seconds"])
    if v7 is None:
        add("goal_xy", goal_xy_error <= float(limits["goal_xy_tolerance_m"]), goal_xy_error, limits["goal_xy_tolerance_m"])
    else:
        add(
            "goal_xy",
            goal_stop_event is not None,
            {
                "final_goal_error_m": goal_xy_error,
                "stable_goal_stop_event": goal_stop_event,
            },
            {
                "goal_xy_tolerance_m": limits["goal_xy_tolerance_m"],
                "continuous_stop_window_seconds": limits["stop_window_seconds"],
            },
        )
    add("goal_z", goal_z_error <= float(limits["goal_z_tolerance_m"]), goal_z_error, limits["goal_z_tolerance_m"])
    add("stopped_command", stop_command <= float(limits["stop_command_max_abs"]), stop_command, limits["stop_command_max_abs"])
    add("stopped_motion", stop_speed <= float(limits["stop_planar_speed_max_mps"]), stop_speed, limits["stop_planar_speed_max_mps"])
    nonzero_count = sum(
        max(abs(float(value)) for value in row["applied_command"]) > 0.05
        for row in metrics
    )
    add("nonzero_commands", nonzero_count >= int(limits["minimum_nonzero_command_records"]), nonzero_count, limits["minimum_nonzero_command_records"])
    add("command_bounds", all(value <= bound + bound_epsilon for value, bound in zip(command_max, command_bounds)), command_max, command_bounds)
    add("finite_policy", all(bool(row["finite"]) for row in metrics), all(bool(row["finite"]) for row in metrics), True)
    add("no_termination", not any(bool(row["done"]) for row in metrics), any(bool(row["done"]) for row in metrics), False)
    heights = [float(row["root_pos_w"][2]) for row in metrics]
    height_range = [min(heights), max(heights)]
    expected_heights = [float(value) for value in limits["root_height_range_m"]]
    add("root_height", height_range[0] >= expected_heights[0] and height_range[1] <= expected_heights[1], height_range, expected_heights)
    max_step = max(step_displacements) if step_displacements else 0.0
    add("no_base_teleport", max_step <= float(limits["maximum_step_displacement_m"]), max_step, limits["maximum_step_displacement_m"])
    add("contact_support", support_fraction >= float(limits["minimum_supported_contact_fraction"]), support_fraction, limits["minimum_supported_contact_fraction"])
    max_nonfoot = max(float(row["nonfoot_contact_max_n"]) for row in metrics)
    add("no_collision", max_nonfoot <= float(limits["maximum_nonfoot_contact_n"]), max_nonfoot, limits["maximum_nonfoot_contact_n"])
    add("obstacle_detour", detour_abs_y >= float(limits["minimum_detour_abs_y_m"]), detour_abs_y, limits["minimum_detour_abs_y_m"])
    rate_range = [float(value) for value in limits["policy_rate_hz_range"]]
    add("policy_rate", rate_range[0] <= policy_rate <= rate_range[1], policy_rate, rate_range)
    sensor_rate_range = [float(value) for value in limits["sensor_rate_hz_range"]]
    add("sensor_rate", sensor_rate_range[0] <= sensor_rate <= sensor_rate_range[1], sensor_rate, sensor_rate_range)
    add("cloud_nonempty", cloud_nonempty >= float(limits["minimum_cloud_nonempty_fraction"]), cloud_nonempty, limits["minimum_cloud_nonempty_fraction"])
    min_points = min(int(row["point_count"]) for row in sensor_metrics)
    add("cloud_points", min_points >= int(limits["minimum_cloud_points"]), min_points, limits["minimum_cloud_points"])
    max_obstacle_hits = max(int(row["obstacle_surface_hit_count"]) for row in sensor_metrics)
    add("obstacle_returns", max_obstacle_hits >= int(limits["minimum_obstacle_surface_hits"]), max_obstacle_hits, limits["minimum_obstacle_surface_hits"])
    max_unexpected = max(int(row["unexpected_above_floor_hit_count"]) for row in sensor_metrics)
    add("unexpected_returns", max_unexpected <= int(limits["maximum_unexpected_above_floor_hits"]), max_unexpected, limits["maximum_unexpected_above_floor_hits"])
    add("pose_dependent_sensor", sensor_displacement >= float(limits["minimum_sensor_pose_displacement_m"]), sensor_displacement, limits["minimum_sensor_pose_displacement_m"])
    max_gaps = max(int(row["sequence_gaps"]) for row in metrics)
    add("sequence_gaps", max_gaps <= int(limits["maximum_sequence_gaps"]), max_gaps, limits["maximum_sequence_gaps"])
    max_watchdogs = max(int(row["watchdog_events"]) for row in metrics)
    add("watchdog_events", max_watchdogs <= int(limits["maximum_watchdog_events"]), max_watchdogs, limits["maximum_watchdog_events"])
    add("command_age_p95", command_age_p95 <= float(limits["maximum_command_age_p95_ms"]), command_age_p95, limits["maximum_command_age_p95_ms"])

    monitor_topics = ros_summary["topics"]
    ros_topic_rate_range = [
        float(value)
        for value in limits.get("ros_topic_rate_hz_range", sensor_rate_range)
    ]
    for topic in ("body_pose", "sensor_pose", "cloud"):
        topic_rate = float(monitor_topics[topic]["rate_hz"])
        add(
            f"ros_{topic}_rate",
            ros_topic_rate_range[0] <= topic_rate <= ros_topic_rate_range[1],
            topic_rate,
            ros_topic_rate_range,
        )
        add(f"ros_{topic}_timestamps", int(monitor_topics[topic]["nonincreasing_stamp_count"]) == 0, monitor_topics[topic]["nonincreasing_stamp_count"], 0)
    add("ros_trajectories", int(ros_summary["unique_trajectory_count"]) >= int(limits["minimum_unique_trajectories"]), ros_summary["unique_trajectory_count"], limits["minimum_unique_trajectories"])
    add("ros_sensor_sync", float(ros_summary["synchronized_sensor_triplet_fraction"]) >= float(limits["minimum_synchronized_sensor_fraction"]), ros_summary["synchronized_sensor_triplet_fraction"], limits["minimum_synchronized_sensor_fraction"])
    add("ros_cloud_points", int(ros_summary["cloud_points"]["minimum"]) >= int(limits["minimum_cloud_points"]), ros_summary["cloud_points"]["minimum"], limits["minimum_cloud_points"])

    command_transport = isaac_report["command_transport"]
    telemetry_transport = isaac_report["telemetry_transport"]
    protocol_errors = int(command_transport["protocol_errors"]) + int(telemetry_transport["protocol_errors"])
    add("transport_protocol_errors", protocol_errors <= int(limits["maximum_transport_protocol_errors"]), protocol_errors, limits["maximum_transport_protocol_errors"])
    if "maximum_coalesced_command_frames" in limits:
        coalesced_commands = int(command_transport.get("coalesced_frames", 0))
        add(
            "coalesced_command_frames",
            coalesced_commands
            <= int(limits["maximum_coalesced_command_frames"]),
            coalesced_commands,
            limits["maximum_coalesced_command_frames"],
        )
    add("telemetry_reconnects", int(telemetry_transport["reconnects"]) <= int(limits["maximum_telemetry_reconnects"]), telemetry_transport["reconnects"], limits["maximum_telemetry_reconnects"])

    video = isaac_report.get("video", {})
    add("video_regular_file", video_path.is_file(), video_path.is_file(), True)
    add("video_frames", int(video.get("frame_count", 0)) >= int(limits["minimum_video_frames"]), video.get("frame_count", 0), limits["minimum_video_frames"])
    add("video_duration", float(video.get("encoded_duration_seconds", 0.0)) >= float(limits["minimum_video_duration_seconds"]), video.get("encoded_duration_seconds", 0.0), limits["minimum_video_duration_seconds"])
    video_bytes = video_path.stat().st_size if video_path.is_file() else 0
    add("video_bytes", video_bytes >= int(limits["minimum_video_bytes"]), video_bytes, limits["minimum_video_bytes"])
    video_hash = _sha256(video_path) if video_path.is_file() else None
    add("video_hash", video_hash == video.get("sha256"), video_hash, video.get("sha256"))

    bag_metadata = rosbag_dir / "metadata.yaml"
    bag_files = list(rosbag_dir.glob("*.db3"))
    bag_bytes = sum(path.stat().st_size for path in bag_files)
    add("rosbag_metadata", bag_metadata.is_file(), bag_metadata.is_file(), True)
    add("rosbag_bytes", bag_bytes >= int(limits["minimum_rosbag_bytes"]), bag_bytes, limits["minimum_rosbag_bytes"])

    planner_successes = foxy_log_text.count("final_plan_success=1")
    planner_failures = foxy_log_text.count("final_plan_success=0")
    origin_errors = foxy_log_text.count("inside an obstacle")
    add("planner_successes", planner_successes >= int(limits["minimum_planner_successes"]), planner_successes, limits["minimum_planner_successes"])
    add("planner_failures", planner_failures <= int(limits["maximum_planner_failures"]), planner_failures, limits["maximum_planner_failures"])
    add("origin_occupancy_errors", origin_errors <= int(limits["maximum_origin_occupancy_errors"]), origin_errors, limits["maximum_origin_occupancy_errors"])
    add("planner_wait_target", "from EXEC_TRAJ to WAIT_TARGET" in foxy_log_text, "from EXEC_TRAJ to WAIT_TARGET" in foxy_log_text, True)
    add("clean_process_exit", "process has died" not in foxy_log_text and "KeyboardInterrupt" not in foxy_log_text, {"process_has_died": "process has died" in foxy_log_text, "keyboard_interrupt": "KeyboardInterrupt" in foxy_log_text}, False)
    add("threshold_identity", run_identity.get("acceptance_config_sha256") == threshold_sha256, run_identity.get("acceptance_config_sha256"), threshold_sha256)

    v3 = thresholds.get("v3_sensor_rig")
    if v3 is not None:
        depth_rows = list(depth_metrics or [])
        composition = runtime_composition or {}
        robot_asset = run_identity.get("robot_asset", {})
        add(
            "v3_canonical_urdf_hash",
            robot_asset.get("canonical_asset_sha256")
            == v3["canonical_urdf_sha256"],
            robot_asset.get("canonical_asset_sha256"),
            v3["canonical_urdf_sha256"],
        )
        add(
            "v3_isaac_urdf_hash",
            robot_asset.get("asset_sha256") == v3["isaac_urdf_sha256"],
            robot_asset.get("asset_sha256"),
            v3["isaac_urdf_sha256"],
        )
        add(
            "v3_lidar_frame",
            run_identity.get("sensor", {}).get("parent_frame")
            == v3["lidar_frame"],
            run_identity.get("sensor", {}).get("parent_frame"),
            v3["lidar_frame"],
        )
        add(
            "v3_depth_frame",
            run_identity.get("depth_camera", {}).get("parent_frame")
            == v3["depth_frame"],
            run_identity.get("depth_camera", {}).get("parent_frame"),
            v3["depth_frame"],
        )
        runtime_body_names = composition.get("runtime_body_names", [])
        runtime_joints = composition.get("imported_joint_prim_paths", [])
        runtime_fixed_joints = composition.get(
            "imported_fixed_joint_prim_paths", []
        )
        runtime_movable_joints = composition.get(
            "imported_movable_joint_prim_paths", []
        )
        runtime_collisions = composition.get("imported_collision_prim_paths", [])
        add(
            "v3_runtime_body_count",
            len(runtime_body_names) == int(v3["expected_body_count"]),
            len(runtime_body_names),
            v3["expected_body_count"],
        )
        add(
            "v3_runtime_joint_count",
            len(runtime_joints) == int(v3["expected_joint_count"]),
            len(runtime_joints),
            v3["expected_joint_count"],
        )
        add(
            "v3_runtime_fixed_joint_count",
            len(runtime_fixed_joints) == int(v3["expected_fixed_joint_count"]),
            len(runtime_fixed_joints),
            v3["expected_fixed_joint_count"],
        )
        add(
            "v3_runtime_movable_joint_count",
            len(runtime_movable_joints)
            == int(v3["expected_movable_joint_count"]),
            len(runtime_movable_joints),
            v3["expected_movable_joint_count"],
        )
        add(
            "v3_runtime_collision_count",
            len(runtime_collisions) == int(v3["expected_collision_count"]),
            len(runtime_collisions),
            v3["expected_collision_count"],
        )
        runtime_mass = composition.get("runtime_total_mass_kg")
        mass_range = [float(value) for value in v3["runtime_mass_range_kg"]]
        add(
            "v3_runtime_mass",
            runtime_mass is not None
            and mass_range[0] <= float(runtime_mass) <= mass_range[1],
            runtime_mass,
            mass_range,
        )
        add(
            "v3_no_silent_default_mass",
            composition.get("silent_default_mass_check", {}).get("status")
            == "pass",
            composition.get("silent_default_mass_check"),
            "pass",
        )
        add(
            "v3_depth_records",
            len(depth_rows) >= int(v3["minimum_depth_frames"]),
            len(depth_rows),
            v3["minimum_depth_frames"],
        )
        if depth_rows:
            depth_rate = _rate(depth_rows)
            depth_rate_range = [float(value) for value in v3["depth_rate_hz_range"]]
            depth_nonempty_fraction = sum(
                int(row["valid_depth_pixel_count"]) > 0 for row in depth_rows
            ) / len(depth_rows)
            depth_displacement = math.dist(
                depth_rows[0]["sensor_position_w"],
                depth_rows[-1]["sensor_position_w"],
            )
            add(
                "v3_depth_rate",
                depth_rate_range[0] <= depth_rate <= depth_rate_range[1],
                depth_rate,
                depth_rate_range,
            )
            add(
                "v3_depth_finite",
                all(int(row["nonfinite_depth_count"]) == 0 for row in depth_rows),
                max(int(row["nonfinite_depth_count"]) for row in depth_rows),
                0,
            )
            add(
                "v3_depth_nonempty",
                depth_nonempty_fraction
                >= float(v3["minimum_depth_nonempty_fraction"]),
                depth_nonempty_fraction,
                v3["minimum_depth_nonempty_fraction"],
            )
            depth_obstacle_pixels = max(
                int(row["obstacle_surface_pixel_count"]) for row in depth_rows
            )
            add(
                "v3_depth_obstacle",
                depth_obstacle_pixels
                >= int(v3["minimum_depth_obstacle_pixels"]),
                depth_obstacle_pixels,
                v3["minimum_depth_obstacle_pixels"],
            )
            add(
                "v3_depth_pose_dependent",
                depth_displacement
                >= float(v3["minimum_depth_pose_displacement_m"]),
                depth_displacement,
                v3["minimum_depth_pose_displacement_m"],
            )
            dimensions = [
                int(depth_rows[0]["width"]),
                int(depth_rows[0]["height"]),
            ]
            add(
                "v3_depth_dimensions",
                dimensions == list(v3["depth_dimensions"]),
                dimensions,
                v3["depth_dimensions"],
            )
        else:
            for name in (
                "v3_depth_rate",
                "v3_depth_finite",
                "v3_depth_nonempty",
                "v3_depth_obstacle",
                "v3_depth_pose_dependent",
                "v3_depth_dimensions",
            ):
                add(name, False, None, "depth metrics required")
        self_occluded = max(
            (int(row.get("self_occluded_hit_count", 0)) for row in sensor_metrics),
            default=0,
        )
        add(
            "v3_lidar_self_occlusion",
            self_occluded >= int(v3["minimum_self_occluded_lidar_hits"]),
            self_occluded,
            v3["minimum_self_occluded_lidar_hits"],
        )
        depth_artifact = isaac_report.get("depth_artifact") or {}
        artifact_records = depth_artifact.get("artifacts", {})
        artifact_checks = {}
        for record in artifact_records.values():
            artifact_path = (
                None
                if depth_artifact_root is None
                else depth_artifact_root / record["path"]
            )
            artifact_checks[record["path"]] = (
                artifact_path is not None
                and artifact_path.is_file()
                and _sha256(artifact_path) == record["sha256"]
            )
        add(
            "v3_depth_artifacts",
            len(artifact_checks) >= int(v3["minimum_depth_artifact_count"])
            and all(artifact_checks.values()),
            artifact_checks,
            v3["minimum_depth_artifact_count"],
        )

    forest = thresholds.get("forest_navigation")
    if forest is not None:
        navigation = run_identity.get("forest_scene", {}).get("navigation") or {}
        primary = navigation.get("primary_blocker") or {}
        start = [float(value) for value in navigation.get("start_world_m", [])]
        nav_goal = [float(value) for value in navigation.get("goal_world_m", [])]
        center = [float(value) for value in primary.get("center_m", [])]
        identity_valid = len(start) == 3 and len(nav_goal) == 3 and len(center) == 3
        expected_goal = [float(value) for value in forest["goal_world_m"]]
        add(
            "forest_goal_identity",
            identity_valid and nav_goal == expected_goal,
            nav_goal,
            expected_goal,
        )
        direct_distance = (
            point_to_segment_distance_2d(center[:2], start[:2], nav_goal[:2])
            if identity_valid
            else math.inf
        )
        required_clearance = float(
            navigation.get("required_center_clearance_m", math.inf)
        )
        add(
            "forest_direct_path_blocked",
            identity_valid
            and bool(navigation.get("direct_path_intersects_inflated_blocker"))
            and direct_distance < required_clearance,
            {
                "center_to_segment_m": direct_distance,
                "required_center_clearance_m": required_clearance,
            },
            "center_to_segment < required_center_clearance",
        )
        sensor_filter = run_identity.get("sensor", {}).get(
            "forest_geometry_filter", {}
        )
        forbidden_inputs = set(sensor_filter.get("forbidden_inputs", []))
        add(
            "forest_geometry_only_planner_input",
            sensor_filter.get("enabled") is True
            and forbidden_inputs
            == {
                "terrain_height_function",
                "scene_prim_id",
                "proxy_bounds",
                "obstacle_label",
            },
            sensor_filter,
            "rendered XYZ geometry filter with all scene-truth inputs forbidden",
        )

        filter_enabled_fraction = sum(
            bool(row.get("planner_geometry_filter_enabled"))
            for row in sensor_metrics
        ) / len(sensor_metrics)
        minimum_filtered_ground = min(
            int(row.get("planner_geometry_filter_ground_hit_count", 0))
            for row in sensor_metrics
        )
        minimum_filtered_obstacles = min(
            int(row.get("planner_geometry_filter_obstacle_hit_count", 0))
            for row in sensor_metrics
        )
        maximum_sparse_fraction = max(
            int(row.get("planner_geometry_filter_sparse_retained_hit_count", 0))
            / max(
                1,
                int(row.get("planner_geometry_filter_obstacle_hit_count", 0)),
            )
            for row in sensor_metrics
        )
        add(
            "forest_filter_enabled",
            filter_enabled_fraction
            >= float(forest["minimum_filter_enabled_fraction"]),
            filter_enabled_fraction,
            forest["minimum_filter_enabled_fraction"],
        )
        add(
            "forest_filter_removes_terrain",
            minimum_filtered_ground
            >= int(forest["minimum_filtered_ground_hits_per_frame"]),
            minimum_filtered_ground,
            forest["minimum_filtered_ground_hits_per_frame"],
        )
        add(
            "forest_filter_keeps_obstacles",
            minimum_filtered_obstacles
            >= int(forest["minimum_filtered_obstacle_hits_per_frame"]),
            minimum_filtered_obstacles,
            forest["minimum_filtered_obstacle_hits_per_frame"],
        )
        add(
            "forest_filter_sparse_fraction",
            maximum_sparse_fraction
            <= float(forest["maximum_sparse_retained_fraction"]),
            maximum_sparse_fraction,
            forest["maximum_sparse_retained_fraction"],
        )

        moving_rows = [
            row
            for row in metrics
            if math.hypot(
                float(row["applied_command"][0]),
                float(row["applied_command"][1]),
            )
            >= 0.10
        ]
        max_forward_command = max(
            (float(row["applied_command"][0]) for row in metrics), default=0.0
        )
        moving_speeds = [
            math.hypot(
                float(row["root_lin_vel_w"][0]),
                float(row["root_lin_vel_w"][1]),
            )
            for row in moving_rows
        ]
        speed_p75 = _percentile(moving_speeds, 0.75) if moving_speeds else 0.0
        add(
            "forest_forward_command_speed",
            max_forward_command >= float(forest["minimum_forward_command_mps"]),
            max_forward_command,
            forest["minimum_forward_command_mps"],
        )
        add(
            "forest_measured_speed_p75",
            speed_p75 >= float(forest["minimum_measured_speed_p75_mps"]),
            speed_p75,
            forest["minimum_measured_speed_p75_mps"],
        )

        if identity_valid:
            primary_clearance = min(
                math.dist(
                    [float(value) for value in row["root_pos_w"][:2]],
                    center[:2],
                )
                for row in metrics
            )
            obstacle_window = [
                float(value) for value in forest["obstacle_x_window_m"]
            ]
            obstacle_rows = [
                row
                for row in metrics
                if obstacle_window[0]
                <= float(row["root_pos_w"][0])
                <= obstacle_window[1]
            ]
            maximum_line_deviation = max(
                (
                    point_to_segment_distance_2d(
                        [float(value) for value in row["root_pos_w"][:2]],
                        start[:2],
                        nav_goal[:2],
                    )
                    for row in obstacle_rows
                ),
                default=0.0,
            )
            path_length = sum(
                math.dist(
                    [float(value) for value in left["root_pos_w"][:2]],
                    [float(value) for value in right["root_pos_w"][:2]],
                )
                for left, right in zip(metrics, metrics[1:])
            )
            direct_length = math.dist(start[:2], nav_goal[:2])
            path_excess = path_length - direct_length
        else:
            primary_clearance = 0.0
            maximum_line_deviation = 0.0
            path_excess = 0.0
        add(
            "forest_primary_blocker_clearance",
            primary_clearance
            >= float(forest["minimum_primary_center_clearance_m"]),
            primary_clearance,
            forest["minimum_primary_center_clearance_m"],
        )
        add(
            "forest_planner_detour",
            maximum_line_deviation
            >= float(forest["minimum_line_deviation_m"]),
            maximum_line_deviation,
            forest["minimum_line_deviation_m"],
        )
        add(
            "forest_path_length_excess",
            path_excess >= float(forest["minimum_path_length_excess_m"]),
            path_excess,
            forest["minimum_path_length_excess_m"],
        )
        base_clearances = [
            float(row["base_clearance_m"])
            for row in metrics
            if row.get("base_clearance_m") is not None
        ]
        terrain_heights = [
            float(row["terrain_height_under_root_m"])
            for row in metrics
            if row.get("terrain_height_under_root_m") is not None
        ]
        minimum_base_clearance = min(base_clearances) if base_clearances else 0.0
        terrain_height_range = (
            max(terrain_heights) - min(terrain_heights)
            if terrain_heights
            else 0.0
        )
        add(
            "forest_base_clearance",
            minimum_base_clearance
            >= float(forest["minimum_base_clearance_m"]),
            minimum_base_clearance,
            forest["minimum_base_clearance_m"],
        )
        add(
            "forest_nonflat_terrain",
            terrain_height_range
            >= float(forest["minimum_terrain_height_range_m"]),
            terrain_height_range,
            forest["minimum_terrain_height_range_m"],
        )

    v6 = thresholds.get("v6_review")
    if v6 is not None:
        expected_limit = float(v6["expected_forward_limit_mps"])
        effective_values = _key_value_lines(effective_input_text or "")

        def numeric_or_none(text, key):
            if text is None:
                return None
            try:
                return _yaml_numeric_value(text, key)
            except ValueError:
                return None

        planner_manager_limit = numeric_or_none(
            planner_config_text, "manager.max_vel"
        )
        planner_optimizer_limit = numeric_or_none(
            planner_config_text, "optimization.max_vel"
        )
        planner_acceleration_limit = numeric_or_none(
            planner_config_text, "manager.max_acc"
        )
        controller_limit = numeric_or_none(controller_config_text, "max_vx")
        try:
            transport_limit = float(effective_values.get("max_vx", "nan"))
        except ValueError:
            transport_limit = math.nan
        isaac_limits = [
            float(value) for value in run_identity.get("command_limits", [])
        ]
        isaac_limit = isaac_limits[0] if len(isaac_limits) == 3 else None
        speed_contract = {
            "scan_manager_max_vel_mps": planner_manager_limit,
            "scan_optimizer_max_vel_mps": planner_optimizer_limit,
            "controller_max_vx_mps": controller_limit,
            "foxy_bridge_effective_max_vx_mps": transport_limit,
            "isaac_receiver_max_vx_mps": isaac_limit,
            "scan_manager_max_acc_mps2": planner_acceleration_limit,
        }
        speed_limits = (
            planner_manager_limit,
            planner_optimizer_limit,
            controller_limit,
            transport_limit,
            isaac_limit,
        )
        add(
            "v6_course_identity",
            run_identity.get("course", {}).get("name") == v6["expected_course"],
            run_identity.get("course", {}).get("name"),
            v6["expected_course"],
        )
        add(
            "v6_synchronized_forward_limits",
            all(
                value is not None
                and math.isfinite(float(value))
                and abs(float(value) - expected_limit) <= 1.0e-9
                for value in speed_limits
            ),
            speed_contract,
            expected_limit,
        )
        add(
            "v6_acceleration_limit",
            planner_acceleration_limit is not None
            and abs(
                planner_acceleration_limit
                - float(v6["planner_acceleration_limit_mps2"])
            )
            <= 1.0e-9,
            planner_acceleration_limit,
            v6["planner_acceleration_limit_mps2"],
        )

        high_command_rows = [
            row
            for row in metrics
            if float(row["applied_command"][0])
            >= float(v6["high_command_minimum_vx_mps"])
            and abs(float(row["applied_command"][2]))
            <= float(v6["high_command_maximum_abs_yaw_rps"])
        ]
        high_command_speeds = [
            math.hypot(
                float(row["root_lin_vel_w"][0]),
                float(row["root_lin_vel_w"][1]),
            )
            for row in high_command_rows
        ]
        high_speed_p75 = (
            _percentile(high_command_speeds, 0.75) if high_command_speeds else 0.0
        )
        add(
            "v6_high_command_samples",
            len(high_command_rows)
            >= int(v6["minimum_high_command_sample_count"]),
            len(high_command_rows),
            v6["minimum_high_command_sample_count"],
        )
        add(
            "v6_high_command_measured_speed_p75",
            high_speed_p75
            >= float(v6["minimum_high_command_measured_speed_p75_mps"]),
            high_speed_p75,
            v6["minimum_high_command_measured_speed_p75_mps"],
        )

        composition = runtime_composition or {}
        geometry = composition.get("forest_scene", {}).get(
            "static_geometry_checks"
        ) or {}
        proxy_records = list(geometry.get("proxy_records", []))
        rock_records = [row for row in proxy_records if row.get("kind") == "Rock"]
        minimum_rock_clearance = min(
            (
                float(row["source_visual_terrain_clearance_m"])
                for row in rock_records
                if row.get("source_visual_terrain_clearance_m") is not None
            ),
            default=-math.inf,
        )
        maximum_proxy_bounds_error = max(
            (
                float(row.get("proxy_bounds_max_error_m", math.inf))
                for row in proxy_records
            ),
            default=math.inf,
        )
        expected_proxy_visibility = bool(v6["expected_proxy_render_visible"])
        proxy_render_modes_match = bool(proxy_records) and all(
            bool(row.get("expected_render_visible")) == expected_proxy_visibility
            and bool(row.get("visible_geometry_prim_paths"))
            == expected_proxy_visibility
            and bool(row.get("render_visibility_matches"))
            for row in proxy_records
        )
        add(
            "v6_static_geometry_gate",
            bool(geometry.get("passed")),
            geometry.get("passed"),
            True,
        )
        add(
            "v6_rock_terrain_clearance",
            bool(rock_records)
            and minimum_rock_clearance
            >= float(v6["minimum_rock_terrain_clearance_m"]),
            minimum_rock_clearance,
            v6["minimum_rock_terrain_clearance_m"],
        )
        add(
            "v6_proxy_bounds",
            bool(proxy_records)
            and maximum_proxy_bounds_error
            <= float(v6["maximum_proxy_bounds_error_m"]),
            maximum_proxy_bounds_error,
            v6["maximum_proxy_bounds_error_m"],
        )
        add(
            "v6_proxy_review_visibility",
            proxy_render_modes_match,
            {
                row.get("name"): {
                    "expected": row.get("expected_render_visible"),
                    "visible_geometry_count": len(
                        row.get("visible_geometry_prim_paths", [])
                    ),
                }
                for row in proxy_records
            },
            expected_proxy_visibility,
        )

        complete_bspline_events = []
        for event in trajectory_events or []:
            if event.get("kind") != "bspline":
                continue
            try:
                order = int(event["order"])
                knots = [float(value) for value in event["knots"]]
                points = [
                    [float(value) for value in point]
                    for point in event["control_points"]
                ]
                complete = (
                    order >= 1
                    and len(points) >= order + 1
                    and len(knots) == len(points) + order + 1
                    and all(len(point) == 3 for point in points)
                    and all(
                        math.isfinite(value)
                        for value in knots
                        + [coordinate for point in points for coordinate in point]
                    )
                    and int(event["start_time_ns"]) >= 0
                )
            except (KeyError, TypeError, ValueError):
                complete = False
            if complete:
                complete_bspline_events.append(event)
        add(
            "v6_complete_bspline_records",
            len(complete_bspline_events)
            >= int(v6["minimum_complete_bspline_records"]),
            len(complete_bspline_events),
            v6["minimum_complete_bspline_records"],
        )

        review_metadata = trajectory_review_metadata or {}
        review_output = review_metadata.get("output", {})
        review_mapping = review_metadata.get("mapping", {})
        overlay_regular = overlay_video_path is not None and overlay_video_path.is_file()
        overlay_bytes = overlay_video_path.stat().st_size if overlay_regular else 0
        overlay_hash = _sha256(overlay_video_path) if overlay_regular else None
        add(
            "v6_overlay_video",
            overlay_regular
            and overlay_bytes >= int(v6["minimum_overlay_video_bytes"])
            and int(review_output.get("frame_count", 0))
            >= int(v6["minimum_overlay_video_frames"]),
            {
                "regular_file": overlay_regular,
                "bytes": overlay_bytes,
                "frame_count": review_output.get("frame_count"),
            },
            {
                "minimum_bytes": v6["minimum_overlay_video_bytes"],
                "minimum_frames": v6["minimum_overlay_video_frames"],
            },
        )
        add(
            "v6_overlay_hash",
            overlay_hash is not None and overlay_hash == review_output.get("sha256"),
            overlay_hash,
            review_output.get("sha256"),
        )
        add(
            "v6_overlay_input_hashes",
            bool(trajectory_review_input_sha256)
            and review_metadata.get("input_sha256")
            == dict(trajectory_review_input_sha256),
            review_metadata.get("input_sha256"),
            trajectory_review_input_sha256,
        )
        alignment_error = float(
            review_mapping.get("maximum_plan_pose_alignment_error_ms", math.inf)
        )
        add(
            "v6_overlay_time_alignment",
            alignment_error
            <= float(v6["maximum_plan_pose_alignment_error_ms"]),
            alignment_error,
            v6["maximum_plan_pose_alignment_error_ms"],
        )

    if v7 is not None:
        add(
            "v7_stable_goal_stop_event",
            goal_stop_event is not None,
            goal_stop_event,
            {
                "goal_xy_tolerance_m": limits["goal_xy_tolerance_m"],
                "stop_window_seconds": limits["stop_window_seconds"],
                "stop_command_max_abs": limits["stop_command_max_abs"],
                "stop_planar_speed_max_mps": limits[
                    "stop_planar_speed_max_mps"
                ],
            },
        )
        post_stop_drift = math.inf
        if goal_stop_event is not None:
            anchor = goal_stop_event["anchor_position_w_xy_m"]
            post_stop_drift = max(
                math.dist(
                    [float(value) for value in row["root_pos_w"][:2]], anchor
                )
                for row in metrics[int(goal_stop_event["end_index"]) :]
            )
        add(
            "v7_post_stop_drift",
            post_stop_drift <= float(v7["maximum_post_stop_drift_m"]),
            {
                "maximum_drift_m": post_stop_drift,
                "final_goal_error_m": goal_xy_error,
            },
            v7["maximum_post_stop_drift_m"],
        )
        try:
            occupied_decay_updates = _yaml_numeric_value(
                planner_config_text or "", "grid_map.occupied_decay_updates"
            )
        except ValueError:
            occupied_decay_updates = None
        add(
            "v7_occupied_freshness_window",
            occupied_decay_updates is not None
            and abs(
                occupied_decay_updates
                - float(v7["expected_occupied_decay_updates"])
            )
            <= 1.0e-9,
            occupied_decay_updates,
            v7["expected_occupied_decay_updates"],
        )
        try:
            controller_tracking_error = _yaml_numeric_value(
                controller_config_text or "", "max_tracking_error"
            )
        except ValueError:
            controller_tracking_error = None
        add(
            "v7_controller_tracking_window",
            controller_tracking_error is not None
            and abs(
                controller_tracking_error
                - float(v7["expected_controller_strict_tracking_error_m"])
            )
            <= 1.0e-9,
            controller_tracking_error,
            v7["expected_controller_strict_tracking_error_m"],
        )
        try:
            controller_catchup_error = _yaml_numeric_value(
                controller_config_text or "", "replan_catchup_max_error"
            )
        except ValueError:
            controller_catchup_error = None
        add(
            "v7_controller_catchup_limit",
            controller_catchup_error is not None
            and abs(
                controller_catchup_error
                - float(v7["expected_controller_catchup_max_error_m"])
            )
            <= 1.0e-9,
            controller_catchup_error,
            v7["expected_controller_catchup_max_error_m"],
        )
        try:
            controller_catchup_min_speed = _yaml_numeric_value(
                controller_config_text or "", "replan_catchup_min_speed"
            )
        except ValueError:
            controller_catchup_min_speed = None
        add(
            "v7_controller_catchup_minimum_speed",
            controller_catchup_min_speed is not None
            and abs(
                controller_catchup_min_speed
                - float(v7["expected_controller_catchup_minimum_speed_mps"])
            )
            <= 1.0e-9,
            controller_catchup_min_speed,
            v7["expected_controller_catchup_minimum_speed_mps"],
        )
        try:
            controller_finish_distance = _yaml_numeric_value(
                controller_config_text or "", "finish_dist"
            )
        except ValueError:
            controller_finish_distance = None
        add(
            "v7_controller_finish_distance",
            controller_finish_distance is not None
            and abs(
                controller_finish_distance
                - float(v7["expected_controller_finish_distance_m"])
            )
            <= 1.0e-9,
            controller_finish_distance,
            v7["expected_controller_finish_distance_m"],
        )
        dynamic_identity = run_identity.get("dynamic_obstacle") or {}
        composition = runtime_composition or {}
        dynamic_geometry = composition.get("dynamic_obstacle", {}).get(
            "geometry_checks"
        ) or {}
        add(
            "v7_course_identity",
            run_identity.get("course", {}).get("name") == v7["expected_course"],
            run_identity.get("course", {}).get("name"),
            v7["expected_course"],
        )
        expected_identity = {
            "shape": v7["expected_shape"],
            "radius_m": float(v7["expected_radius_m"]),
            "height_m": float(v7["expected_height_m"]),
            "speed_mps": float(v7["expected_speed_mps"]),
            "wait_seconds": float(v7["expected_wait_seconds"]),
            "hold_fraction": float(v7["expected_hold_fraction"]),
            "hold_seconds": float(v7["expected_hold_seconds"]),
            "schedule_trigger": v7["expected_schedule_trigger"],
        }
        observed_identity = {
            "shape": dynamic_identity.get("shape"),
            "radius_m": dynamic_identity.get("radius_m"),
            "height_m": dynamic_identity.get("height_m"),
            "speed_mps": dynamic_identity.get("speed_mps"),
            "wait_seconds": dynamic_identity.get("wait_seconds"),
            "hold_fraction": dynamic_identity.get("hold_fraction"),
            "hold_seconds": dynamic_identity.get("hold_seconds"),
            "schedule_trigger": dynamic_identity.get("schedule_trigger"),
        }
        add(
            "v7_dynamic_identity",
            observed_identity == expected_identity,
            observed_identity,
            expected_identity,
        )
        required_geometry_checks = (
            "runtime_root_exists",
            "rigid_object_initialized",
            "kinematic_enabled",
            "collision_enabled",
            "lidar_transform_tracking",
            "depth_transform_tracking",
        )
        geometry_visibility = dynamic_geometry.get("checks", {}).get(
            "physical_geometry_visibility",
            dynamic_geometry.get("checks", {}).get("visible_geometry"),
        )
        add(
            "v7_dynamic_physics_sensor_geometry",
            bool(dynamic_geometry.get("passed"))
            and all(
                dynamic_geometry.get("checks", {}).get(name) is True
                for name in required_geometry_checks
            )
            and geometry_visibility is True,
            dynamic_geometry,
            {
                **{name: True for name in required_geometry_checks},
                "physical_geometry_visibility_or_legacy_visible_geometry": True,
            },
        )
        add(
            "v7_ground_truth_evidence_only",
            dynamic_identity.get("planner_input") == "rendered sensor hits only"
            and "forbidden" in str(dynamic_identity.get("ground_truth_use", "")),
            {
                "planner_input": dynamic_identity.get("planner_input"),
                "ground_truth_use": dynamic_identity.get("ground_truth_use"),
            },
            "rendered sensor hits only; ground truth forbidden from planner/steering",
        )

        dynamic_rows = [
            row
            for row in metrics
            if row.get("dynamic_obstacle_actual_pos_w") is not None
        ]
        phases = {str(row.get("dynamic_obstacle_phase")) for row in dynamic_rows}
        required_phases = {"waiting", "crossing", "parked"}
        if float(v7["expected_hold_seconds"]) > 0.0:
            required_phases.add("holding")
        trigger_indices = [
            index
            for index, row in enumerate(dynamic_rows)
            if row.get("dynamic_obstacle_schedule_triggered") is True
        ]
        trigger_evidence = None
        if trigger_indices:
            trigger_index = trigger_indices[0]
            trigger_row = dynamic_rows[trigger_index]
            pre_trigger_rows = dynamic_rows[:trigger_index]
            trigger_evidence = {
                "trigger_index": trigger_index,
                "trigger_sim_time_seconds": trigger_row.get(
                    "dynamic_obstacle_trigger_sim_time_seconds"
                ),
                "trigger_command_max_abs": max(
                    abs(float(value)) for value in trigger_row["applied_command"]
                ),
                "pre_trigger_record_count": len(pre_trigger_rows),
                "pre_trigger_maximum_elapsed_seconds": max(
                    (
                        float(row.get("dynamic_obstacle_elapsed_seconds", math.inf))
                        for row in pre_trigger_rows
                    ),
                    default=0.0,
                ),
                "pre_trigger_maximum_command_abs": max(
                    (
                        max(abs(float(value)) for value in row["applied_command"])
                        for row in pre_trigger_rows
                    ),
                    default=0.0,
                ),
            }
        add(
            "v7_command_relative_schedule_trigger",
            trigger_evidence is not None
            and trigger_evidence["trigger_command_max_abs"] > 0.05
            and trigger_evidence["pre_trigger_maximum_elapsed_seconds"] <= 1.0e-9
            and trigger_evidence["pre_trigger_maximum_command_abs"] <= 0.05,
            trigger_evidence,
            "elapsed stays zero until first accepted command exceeds 0.05",
        )
        actual_travel = (
            math.dist(
                dynamic_rows[0]["dynamic_obstacle_actual_pos_w"],
                dynamic_rows[-1]["dynamic_obstacle_actual_pos_w"],
            )
            if len(dynamic_rows) >= 2
            else 0.0
        )
        maximum_pose_error = max(
            (
                float(row.get("dynamic_obstacle_pose_error_m", math.inf))
                for row in dynamic_rows
            ),
            default=math.inf,
        )
        minimum_terrain_clearance = min(
            (
                float(row.get("dynamic_obstacle_bottom_clearance_m", -math.inf))
                for row in dynamic_rows
            ),
            default=-math.inf,
        )
        add(
            "v7_dynamic_motion",
            required_phases.issubset(phases)
            and actual_travel >= float(v7["minimum_actual_travel_m"])
            and maximum_pose_error <= float(v7["maximum_pose_error_m"]),
            {
                "phases": sorted(phases),
                "actual_travel_m": actual_travel,
                "maximum_pose_error_m": maximum_pose_error,
            },
            {
                "phases": sorted(required_phases),
                "minimum_actual_travel_m": v7["minimum_actual_travel_m"],
                "maximum_pose_error_m": v7["maximum_pose_error_m"],
            },
        )
        add(
            "v7_dynamic_terrain_clearance",
            minimum_terrain_clearance
            >= float(v7["minimum_terrain_clearance_m"]),
            minimum_terrain_clearance,
            v7["minimum_terrain_clearance_m"],
        )

        lidar_dynamic_rows = [
            row
            for row in sensor_metrics
            if int(row.get("dynamic_obstacle_surface_hit_count", 0))
            >= int(v7["minimum_lidar_hits_per_detection"])
            and row.get("dynamic_obstacle_actual_pos_w") is not None
        ]
        depth_dynamic_rows = [
            row
            for row in (depth_metrics or [])
            if int(row.get("dynamic_obstacle_surface_pixel_count", 0))
            >= int(v7["minimum_depth_pixels_per_detection"])
            and row.get("dynamic_obstacle_actual_pos_w") is not None
        ]

        def observation_span(rows):
            if len(rows) < 2:
                return 0.0
            positions = [row["dynamic_obstacle_actual_pos_w"] for row in rows]
            return max(
                math.dist(left[:2], right[:2])
                for left in positions
                for right in positions
            )

        lidar_span = observation_span(lidar_dynamic_rows)
        depth_span = observation_span(depth_dynamic_rows)
        add(
            "v7_lidar_dynamic_observations",
            len(lidar_dynamic_rows) >= int(v7["minimum_lidar_detection_frames"])
            and lidar_span >= float(v7["minimum_observed_position_span_m"]),
            {"frame_count": len(lidar_dynamic_rows), "position_span_m": lidar_span},
            {
                "minimum_frames": v7["minimum_lidar_detection_frames"],
                "minimum_position_span_m": v7["minimum_observed_position_span_m"],
            },
        )
        add(
            "v7_depth_dynamic_observations",
            len(depth_dynamic_rows) >= int(v7["minimum_depth_detection_frames"])
            and depth_span >= float(v7["minimum_observed_position_span_m"]),
            {"frame_count": len(depth_dynamic_rows), "position_span_m": depth_span},
            {
                "minimum_frames": v7["minimum_depth_detection_frames"],
                "minimum_position_span_m": v7["minimum_observed_position_span_m"],
            },
        )

        navigation = run_identity.get("forest_scene", {}).get("navigation") or {}
        start = navigation.get("start_world_m", [])
        nav_goal = navigation.get("goal_world_m", [])
        dynamic_start = dynamic_identity.get("start_xy_m", [])
        dynamic_end = dynamic_identity.get("end_xy_m", [])
        if (
            len(start) >= 2
            and len(nav_goal) >= 2
            and len(dynamic_start) == 2
            and len(dynamic_end) == 2
        ):
            dynamic_corridor_distance = min(
                point_to_segment_distance_2d(
                    (
                        float(dynamic_start[0])
                        + (float(dynamic_end[0]) - float(dynamic_start[0]))
                        * index
                        / 100.0,
                        float(dynamic_start[1])
                        + (float(dynamic_end[1]) - float(dynamic_start[1]))
                        * index
                        / 100.0,
                    ),
                    start[:2],
                    nav_goal[:2],
                )
                for index in range(101)
            )
        else:
            dynamic_corridor_distance = math.inf
        required_conflict_distance = float(v7["maximum_nominal_route_distance_m"])
        add(
            "v7_nominal_route_conflict",
            dynamic_corridor_distance <= required_conflict_distance,
            dynamic_corridor_distance,
            required_conflict_distance,
        )

        first_detection_time = min(
            (float(row["sim_time_seconds"]) for row in lidar_dynamic_rows),
            default=math.inf,
        )
        plan_records = list((trajectory_review_metadata or {}).get("plans", []))
        post_detection_plans = [
            row
            for row in plan_records
            if float(row.get("effective_sim_time_seconds", -math.inf))
            >= first_detection_time
        ]
        response_latency = (
            min(
                float(row["effective_sim_time_seconds"])
                for row in post_detection_plans
            )
            - first_detection_time
            if post_detection_plans and math.isfinite(first_detection_time)
            else math.inf
        )
        add(
            "v7_post_detection_scan_response",
            len(post_detection_plans)
            >= int(v7["minimum_post_detection_bspline_records"])
            and 0.0 <= response_latency
            <= float(v7["maximum_replan_response_seconds"]),
            {
                "first_lidar_detection_sim_time_seconds": first_detection_time,
                "post_detection_plan_ids": [
                    row.get("trajectory_id") for row in post_detection_plans
                ],
                "response_latency_seconds": response_latency,
            },
            {
                "minimum_records": v7["minimum_post_detection_bspline_records"],
                "maximum_response_seconds": v7["maximum_replan_response_seconds"],
            },
        )
        synchronized_clearance = min(
            (
                float(row.get("root_to_dynamic_surface_clearance_m", -math.inf))
                for row in dynamic_rows
                if row.get("dynamic_obstacle_phase") == "crossing"
            ),
            default=-math.inf,
        )
        add(
            "v7_physical_dynamic_clearance",
            synchronized_clearance
            >= float(v7["minimum_synchronized_surface_clearance_m"]),
            synchronized_clearance,
            v7["minimum_synchronized_surface_clearance_m"],
        )
        review_dynamic = (trajectory_review_metadata or {}).get(
            "dynamic_obstacle", {}
        )
        add(
            "v7_overlay_dynamic_trace",
            review_dynamic.get("rendered") is True
            and int(review_dynamic.get("record_count", 0))
            >= int(v7["minimum_overlay_dynamic_records"]),
            review_dynamic,
            {
                "rendered": True,
                "minimum_records": v7["minimum_overlay_dynamic_records"],
            },
        )

        if v8 is not None:
            expected_parts = sorted(str(value) for value in v8["expected_part_names"])
            human_asset = dynamic_identity.get("human_asset") or {}
            human_asset_path = (
                None
                if depth_artifact_root is None
                else depth_artifact_root / str(v8["expected_asset_filename"])
            )
            observed_asset_sha = (
                None
                if human_asset_path is None or not human_asset_path.is_file()
                else _sha256(human_asset_path)
            )
            add(
                "v8_generated_human_asset",
                human_asset.get("source")
                == "locally generated procedural USDA; no external character asset"
                and human_asset.get("sha256") == observed_asset_sha
                and observed_asset_sha == v8["expected_asset_sha256"],
                {
                    "identity": human_asset,
                    "copied_asset_sha256": observed_asset_sha,
                },
                {
                    "source": "locally generated procedural USDA; no external character asset",
                    "sha256": v8["expected_asset_sha256"],
                },
            )
            observed_human_identity = {
                "shape": dynamic_identity.get("shape"),
                "collision_shape": dynamic_identity.get("collision_shape"),
                "colour_rgb": dynamic_identity.get("colour_rgb"),
                "visible_part_names": sorted(
                    str(value)
                    for value in dynamic_identity.get("visible_part_names", [])
                ),
                "sensor_target_count": len(
                    dynamic_identity.get("sensor_target_exprs", [])
                ),
            }
            expected_human_identity = {
                "shape": "procedural_humanoid",
                "collision_shape": "hidden_capsule",
                "colour_rgb": list(v8["expected_colour_rgb"]),
                "visible_part_names": expected_parts,
                "sensor_target_count": len(expected_parts),
            }
            add(
                "v8_human_identity",
                observed_human_identity == expected_human_identity,
                observed_human_identity,
                expected_human_identity,
            )
            add(
                "v8_human_stage_geometry",
                dynamic_geometry.get("checks", {}).get("human_parts_complete") is True
                and dynamic_geometry.get("checks", {}).get("human_collision_hidden")
                is True
                and dynamic_geometry.get("checks", {}).get(
                    "lidar_transform_tracking"
                )
                is True
                and dynamic_geometry.get("checks", {}).get(
                    "depth_transform_tracking"
                )
                is True
                and sorted(dynamic_geometry.get("visible_human_part_names", []))
                == expected_parts
                and len(dynamic_geometry.get("collision_prim_paths", [])) == 1
                and not dynamic_geometry.get("visible_collision_prim_paths"),
                dynamic_geometry,
                {
                    "visible_part_names": expected_parts,
                    "one_hidden_collision_prim": True,
                    "dual_sensor_transform_tracking": True,
                },
            )

            gait_rows = [
                row
                for row in dynamic_rows
                if isinstance(row.get("dynamic_human_gait_angles"), dict)
            ]
            crossing_gait = [
                row["dynamic_human_gait_angles"]
                for row in gait_rows
                if row.get("dynamic_obstacle_phase") == "crossing"
            ]
            neutral_gait = [
                row["dynamic_human_gait_angles"]
                for row in gait_rows
                if row.get("dynamic_obstacle_phase")
                in ("waiting", "holding", "parked")
            ]
            maximum_swing = max(
                (
                    max(abs(float(value)) for value in row.values())
                    for row in crossing_gait
                ),
                default=0.0,
            )
            opposition_error = max(
                (
                    max(
                        abs(
                            float(row["left_arm_radians"])
                            + float(row["right_arm_radians"])
                        ),
                        abs(
                            float(row["left_leg_radians"])
                            + float(row["right_leg_radians"])
                        ),
                        abs(
                            float(row["left_arm_radians"])
                            - float(row["right_leg_radians"])
                        ),
                    )
                    for row in crossing_gait
                ),
                default=math.inf,
            )
            neutral_maximum = max(
                (
                    max(abs(float(value)) for value in row.values())
                    for row in neutral_gait
                ),
                default=math.inf,
            )
            add(
                "v8_human_gait",
                len(crossing_gait) >= int(v8["minimum_crossing_gait_records"])
                and maximum_swing >= float(v8["minimum_observed_swing_radians"])
                and maximum_swing
                <= float(v8["expected_maximum_swing_radians"]) + 1.0e-6
                and opposition_error <= float(v8["maximum_opposition_error_radians"])
                and neutral_gait
                and neutral_maximum <= float(v8["maximum_neutral_swing_radians"]),
                {
                    "crossing_record_count": len(crossing_gait),
                    "maximum_swing_radians": maximum_swing,
                    "maximum_opposition_error_radians": opposition_error,
                    "maximum_neutral_swing_radians": neutral_maximum,
                },
                {
                    "minimum_crossing_records": v8["minimum_crossing_gait_records"],
                    "minimum_swing_radians": v8["minimum_observed_swing_radians"],
                    "crossing_only_and_opposed": True,
                },
            )

            def animated_detection_count(rows, count_key):
                return sum(
                    int(row.get(count_key, 0)) > 0
                    and isinstance(row.get("dynamic_human_gait_angles"), dict)
                    and max(
                        abs(float(value))
                        for value in row["dynamic_human_gait_angles"].values()
                    )
                    >= float(v8["minimum_sensor_visible_swing_radians"])
                    for row in rows
                )

            lidar_animated = animated_detection_count(
                sensor_metrics, "dynamic_obstacle_surface_hit_count"
            )
            depth_animated = animated_detection_count(
                depth_metrics or [], "dynamic_obstacle_surface_pixel_count"
            )
            expected_overlay_colour = list(v8["expected_overlay_colour_bgr"])
            observed_overlay_colour = (
                (trajectory_review_metadata or {})
                .get("colours_bgr", {})
                .get("dynamic_obstacle_actual")
            )
            add(
                "v8_sensor_visible_gait_and_overlay",
                lidar_animated >= int(v8["minimum_lidar_animated_detections"])
                and depth_animated >= int(v8["minimum_depth_animated_detections"])
                and observed_overlay_colour == expected_overlay_colour,
                {
                    "lidar_animated_detection_count": lidar_animated,
                    "depth_animated_detection_count": depth_animated,
                    "overlay_colour_bgr": observed_overlay_colour,
                },
                {
                    "minimum_lidar_animated_detections": v8[
                        "minimum_lidar_animated_detections"
                    ],
                    "minimum_depth_animated_detections": v8[
                        "minimum_depth_animated_detections"
                    ],
                    "overlay_colour_bgr": expected_overlay_colour,
                },
            )

        if v8_official is not None:
            human_asset = dynamic_identity.get("human_asset") or {}
            official_visual = human_asset.get("official_visual") or {}
            official_proxy = human_asset.get("physical_and_sensor_proxy") or {}
            gait_identity = dynamic_identity.get("gait") or {}
            cache_identity = gait_identity.get("retarget_cache") or {}
            visual_path = (
                None
                if depth_artifact_root is None
                else depth_artifact_root
                / str(v8_official["expected_visual_asset_filename"])
            )
            proxy_path = (
                None
                if depth_artifact_root is None
                else depth_artifact_root
                / str(v8_official["expected_proxy_asset_filename"])
            )
            visual_sha = (
                _sha256(visual_path)
                if visual_path is not None and visual_path.is_file()
                else None
            )
            proxy_sha = (
                _sha256(proxy_path)
                if proxy_path is not None and proxy_path.is_file()
                else None
            )
            expected_visual_sha = v8_official.get("expected_visual_asset_sha256")
            expected_proxy_sha = v8_official.get("expected_proxy_asset_sha256")
            add(
                "v8_official_asset_files",
                visual_sha is not None
                and proxy_sha is not None
                and official_visual.get("sha256") == visual_sha
                and official_proxy.get("sha256") == proxy_sha
                and (
                    expected_visual_sha is None or visual_sha == expected_visual_sha
                )
                and (expected_proxy_sha is None or proxy_sha == expected_proxy_sha),
                {
                    "visual_identity_sha256": official_visual.get("sha256"),
                    "visual_copied_sha256": visual_sha,
                    "proxy_identity_sha256": official_proxy.get("sha256"),
                    "proxy_copied_sha256": proxy_sha,
                },
                {
                    "visual_sha256": expected_visual_sha or "identity/file parity",
                    "proxy_sha256": expected_proxy_sha or "identity/file parity",
                },
            )

            observed_official_identity = {
                "shape": dynamic_identity.get("shape"),
                "collision_shape": dynamic_identity.get("collision_shape"),
                "visible_part_names": dynamic_identity.get("visible_part_names"),
                "sensor_target_count": len(
                    dynamic_identity.get("sensor_target_exprs", [])
                ),
                "character_url": official_visual.get("official_character_url"),
                "biped_url": gait_identity.get("biped_url"),
                "gait_status": gait_identity.get("status"),
                "local_procedural_gait": gait_identity.get(
                    "local_procedural_gait"
                ),
                "direct_gpu_animation_graph_used": gait_identity.get(
                    "direct_gpu_animation_graph_used"
                ),
                "cache_content_sha256": cache_identity.get("content_sha256"),
                "cache_joint_count": cache_identity.get("joint_count"),
                "cache_fps": cache_identity.get("fps"),
                "cache_idle_frame_count": cache_identity.get("idle_frame_count"),
                "cache_walk_frame_count": cache_identity.get("walk_frame_count"),
            }
            expected_official_identity = {
                "shape": "official_skinned_human_plus_capsule",
                "collision_shape": "hidden_capsule",
                "visible_part_names": [
                    v8_official["expected_visual_runtime_prim"]
                ],
                "sensor_target_count": 1,
                "character_url": v8_official["expected_character_url"],
                "biped_url": v8_official["expected_biped_url"],
                "gait_status": "official_biped_retarget_cache_replay",
                "local_procedural_gait": False,
                "direct_gpu_animation_graph_used": False,
                "cache_content_sha256": v8_official[
                    "expected_cache_content_sha256"
                ],
                "cache_joint_count": int(v8_official["expected_joint_count"]),
                "cache_fps": int(v8_official["expected_animation_fps"]),
                "cache_idle_frame_count": int(
                    v8_official["expected_idle_frame_count"]
                ),
                "cache_walk_frame_count": int(
                    v8_official["expected_walk_frame_count"]
                ),
            }
            add(
                "v8_official_identity",
                observed_official_identity == expected_official_identity,
                observed_official_identity,
                expected_official_identity,
            )

            official_checks = dynamic_geometry.get("checks", {})
            required_official_checks = (
                "runtime_root_exists",
                "rigid_object_initialized",
                "kinematic_enabled",
                "collision_enabled",
                "physical_geometry_visibility",
                "lidar_transform_tracking",
                "depth_transform_tracking",
                "human_parts_complete",
                "human_collision_hidden",
                "official_visual_root_exists",
                "official_visual_geometry_visible",
                "official_visual_has_no_collision",
                "official_visual_has_no_rigid_body",
                "official_sensor_proxy_is_capsule",
            )
            add(
                "v8_official_stage_geometry",
                bool(dynamic_geometry.get("passed"))
                and all(
                    official_checks.get(name) is True
                    for name in required_official_checks
                )
                and len(dynamic_geometry.get("collision_prim_paths", [])) == 1
                and not dynamic_geometry.get("visible_collision_prim_paths")
                and not dynamic_geometry.get("visible_geometry_prim_paths")
                and bool(
                    dynamic_geometry.get("official_visual_geometry_prim_paths")
                )
                and not dynamic_geometry.get(
                    "official_visual_collision_prim_paths"
                )
                and dynamic_geometry.get("official_visual_runtime_prim")
                == v8_official["expected_visual_runtime_prim"],
                dynamic_geometry,
                {
                    **{name: True for name in required_official_checks},
                    "one_hidden_proxy_collision": True,
                    "visible_collision_free_official_character": True,
                },
            )

            registration_rows = [
                row.get("official_human_visual_pose")
                for row in dynamic_rows
                if isinstance(row.get("official_human_visual_pose"), dict)
            ]
            maximum_root_pose_error = max(
                (
                    abs(float(row.get("root_pose_error_m", math.inf)))
                    for row in registration_rows
                ),
                default=math.inf,
            )
            maximum_foot_datum_error = max(
                (
                    abs(
                        float(
                            row.get("foot_to_capsule_bottom_error_m", math.inf)
                        )
                    )
                    for row in registration_rows
                ),
                default=math.inf,
            )
            add(
                "v8_official_registration",
                len(registration_rows) == len(dynamic_rows)
                and maximum_root_pose_error
                <= float(v8_official["maximum_visual_root_pose_error_m"])
                and maximum_foot_datum_error
                <= float(v8_official["maximum_foot_datum_error_m"]),
                {
                    "record_count": len(registration_rows),
                    "dynamic_record_count": len(dynamic_rows),
                    "maximum_visual_root_pose_error_m": maximum_root_pose_error,
                    "maximum_foot_datum_error_m": maximum_foot_datum_error,
                },
                {
                    "all_dynamic_records_registered": True,
                    "maximum_visual_root_pose_error_m": v8_official[
                        "maximum_visual_root_pose_error_m"
                    ],
                    "maximum_foot_datum_error_m": v8_official[
                        "maximum_foot_datum_error_m"
                    ],
                },
            )

            official_gait_rows = [
                row
                for row in dynamic_rows
                if isinstance(row.get("dynamic_human_gait_angles"), dict)
            ]
            crossing_walk = [
                row["dynamic_human_gait_angles"]
                for row in official_gait_rows
                if row.get("dynamic_obstacle_phase") == "crossing"
                and row["dynamic_human_gait_angles"].get("clip") == "walk"
            ]
            idle_animation = [
                row["dynamic_human_gait_angles"]
                for row in official_gait_rows
                if row.get("dynamic_obstacle_phase")
                in ("waiting", "holding", "parked")
                and row["dynamic_human_gait_angles"].get("clip") == "idle"
            ]

            def official_gait_metadata_valid(gait):
                expected_frames = (
                    int(v8_official["expected_walk_frame_count"])
                    if gait.get("clip") == "walk"
                    else int(v8_official["expected_idle_frame_count"])
                )
                return (
                    gait.get("source")
                    == "NVIDIA Isaac Sim 5.1 Biped AnimationGraph retarget cache"
                    and gait.get("cache_content_sha256")
                    == v8_official["expected_cache_content_sha256"]
                    and int(gait.get("target_joint_count", -1))
                    == int(v8_official["expected_joint_count"])
                    and int(gait.get("fps", -1))
                    == int(v8_official["expected_animation_fps"])
                    and int(gait.get("frame_count", -1)) == expected_frames
                    and gait.get("local_procedural_gait") is False
                    and gait.get("direct_gpu_animation_graph_used") is False
                )

            walk_frame_span = len(
                {int(gait.get("frame_index", -1)) for gait in crossing_walk}
            )
            add(
                "v8_official_animation",
                len(crossing_walk)
                >= int(v8_official["minimum_crossing_animation_records"])
                and walk_frame_span
                >= int(v8_official["minimum_distinct_walk_frames"])
                and len(idle_animation)
                >= int(v8_official["minimum_idle_animation_records"])
                and len(official_gait_rows) == len(dynamic_rows)
                and all(
                    official_gait_metadata_valid(row["dynamic_human_gait_angles"])
                    for row in official_gait_rows
                ),
                {
                    "crossing_walk_record_count": len(crossing_walk),
                    "distinct_walk_frame_count": walk_frame_span,
                    "idle_record_count": len(idle_animation),
                    "all_dynamic_records_have_official_animation": len(
                        official_gait_rows
                    )
                    == len(dynamic_rows),
                },
                {
                    "minimum_crossing_records": v8_official[
                        "minimum_crossing_animation_records"
                    ],
                    "minimum_distinct_walk_frames": v8_official[
                        "minimum_distinct_walk_frames"
                    ],
                    "minimum_idle_records": v8_official[
                        "minimum_idle_animation_records"
                    ],
                    "official_cache_metadata_on_every_record": True,
                },
            )

            def official_walk_detection_count(rows, count_key, minimum_count):
                return sum(
                    int(row.get(count_key, 0)) >= int(minimum_count)
                    and isinstance(row.get("dynamic_human_gait_angles"), dict)
                    and row["dynamic_human_gait_angles"].get("clip") == "walk"
                    and official_gait_metadata_valid(
                        row["dynamic_human_gait_angles"]
                    )
                    for row in rows
                )

            lidar_walk_detections = official_walk_detection_count(
                sensor_metrics,
                "dynamic_obstacle_surface_hit_count",
                v7["minimum_lidar_hits_per_detection"],
            )
            depth_walk_detections = official_walk_detection_count(
                depth_metrics or [],
                "dynamic_obstacle_surface_pixel_count",
                v7["minimum_depth_pixels_per_detection"],
            )
            expected_overlay_colour = list(
                v8_official["expected_overlay_colour_bgr"]
            )
            review_metadata = trajectory_review_metadata or {}
            observed_overlay_colour = review_metadata.get("colours_bgr", {}).get(
                "dynamic_obstacle_actual"
            )
            observed_overlay_label = review_metadata.get(
                "dynamic_obstacle", {}
            ).get("label")
            add(
                "v8_official_sensor_visible_walk_and_overlay",
                lidar_walk_detections
                >= int(v8_official["minimum_lidar_walk_detections"])
                and depth_walk_detections
                >= int(v8_official["minimum_depth_walk_detections"])
                and observed_overlay_colour == expected_overlay_colour
                and observed_overlay_label == "Official human actual",
                {
                    "lidar_walk_detection_count": lidar_walk_detections,
                    "depth_walk_detection_count": depth_walk_detections,
                    "overlay_colour_bgr": observed_overlay_colour,
                    "overlay_label": observed_overlay_label,
                },
                {
                    "minimum_lidar_walk_detections": v8_official[
                        "minimum_lidar_walk_detections"
                    ],
                    "minimum_depth_walk_detections": v8_official[
                        "minimum_depth_walk_detections"
                    ],
                    "overlay_colour_bgr": expected_overlay_colour,
                    "overlay_label": "Official human actual",
                },
            )

    passed = all(value["passed"] for value in checks.values())
    return {
        "schema_version": 1,
        "status": "PASS" if passed else "FAIL",
        "claim": thresholds["claim"],
        "checks": checks,
        "summary": {
            "final_position_world_m": final_position,
            "goal_xy_error_m": goal_xy_error,
            "detour_min_abs_y_m": detour_abs_y,
            "max_nonfoot_contact_n": max_nonfoot,
            "policy_rate_hz": policy_rate,
            "sensor_rate_hz": sensor_rate,
            "command_age_p95_ms": command_age_p95,
            "video_sha256": video_hash,
            "rosbag_bytes": bag_bytes,
            "forest_navigation_enabled": forest is not None,
            "dynamic_obstacle_enabled": v7 is not None,
            "human_obstacle_enabled": v8 is not None or v8_official is not None,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--sensor-metrics", type=Path, required=True)
    parser.add_argument("--isaac-report", type=Path, required=True)
    parser.add_argument("--run-identity", type=Path, required=True)
    parser.add_argument("--ros-summary", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--rosbag", type=Path, required=True)
    parser.add_argument("--foxy-log", type=Path, required=True)
    parser.add_argument("--depth-metrics", type=Path)
    parser.add_argument("--runtime-composition", type=Path)
    parser.add_argument("--depth-artifact-root", type=Path)
    parser.add_argument("--overlay-video", type=Path)
    parser.add_argument("--trajectory-events", type=Path)
    parser.add_argument("--trajectory-review-metadata", type=Path)
    parser.add_argument("--effective-input", type=Path)
    parser.add_argument("--planner-config", type=Path)
    parser.add_argument("--controller-config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))
    trajectory_input_hashes = None
    if args.trajectory_review_metadata is not None:
        required_review_inputs = (
            args.trajectory_events,
            args.metrics,
            args.run_identity,
            args.video,
        )
        if any(path is None or not path.is_file() for path in required_review_inputs):
            raise SystemExit("trajectory review metadata requires all raw input files")
        trajectory_input_hashes = {
            "raw_video": _sha256(args.video),
            "ros_events": _sha256(args.trajectory_events),
            "metrics": _sha256(args.metrics),
            "run_identity": _sha256(args.run_identity),
        }
    report = evaluate_acceptance(
        thresholds,
        _load_jsonl(args.metrics),
        _load_jsonl(args.sensor_metrics),
        json.loads(args.isaac_report.read_text(encoding="utf-8")),
        json.loads(args.run_identity.read_text(encoding="utf-8")),
        json.loads(args.ros_summary.read_text(encoding="utf-8")),
        args.video,
        args.rosbag,
        args.foxy_log.read_text(encoding="utf-8"),
        _sha256(args.thresholds),
        None if args.depth_metrics is None else _load_jsonl(args.depth_metrics),
        (
            None
            if args.runtime_composition is None
            else json.loads(args.runtime_composition.read_text(encoding="utf-8"))
        ),
        args.depth_artifact_root,
        args.overlay_video,
        (
            None
            if args.trajectory_events is None
            else _load_jsonl(args.trajectory_events)
        ),
        (
            None
            if args.trajectory_review_metadata is None
            else json.loads(
                args.trajectory_review_metadata.read_text(encoding="utf-8")
            )
        ),
        trajectory_input_hashes,
        (
            None
            if args.effective_input is None
            else args.effective_input.read_text(encoding="utf-8")
        ),
        (
            None
            if args.planner_config is None
            else args.planner_config.read_text(encoding="utf-8")
        ),
        (
            None
            if args.controller_config is None
            else args.controller_config.read_text(encoding="utf-8")
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
