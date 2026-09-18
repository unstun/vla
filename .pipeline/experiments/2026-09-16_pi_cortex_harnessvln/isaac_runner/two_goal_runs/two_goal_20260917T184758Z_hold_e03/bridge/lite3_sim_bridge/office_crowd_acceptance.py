"""Dedicated Office L0 eight-person crowd acceptance evaluator with video quality and clock-consistent active-path causal audit."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .office_crowd_contract import (
    OfficePedestrianRoute,
    office_pedestrian_state,
    pairwise_clearance_precheck,
    routes_from_preflight,
)
from .trajectory_review import sample_uniform_bspline


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> List[Mapping[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"required JSONL is empty: {path}")
    return rows


def _rate(rows: Sequence[Mapping[str, Any]]) -> float:
    duration = float(rows[-1]["sim_time_seconds"]) - float(rows[0]["sim_time_seconds"])
    return 0.0 if len(rows) < 2 or duration <= 0.0 else (len(rows) - 1) / duration


def _runtime_gate_metrics(
    metrics_rows: Sequence[Mapping[str, Any]],
    sensor_rows: Sequence[Mapping[str, Any]],
    stop_window_seconds: float,
) -> Dict[str, Any]:
    """Project raw runtime rows onto frozen safety and terminal-stop gates."""
    final_time = float(metrics_rows[-1]["sim_time_seconds"])
    step_displacements = [
        math.dist(left["root_pos_w"], right["root_pos_w"])
        for left, right in zip(metrics_rows, metrics_rows[1:])
    ]
    command_max_abs = [
        max(abs(float(row["applied_command"][axis])) for row in metrics_rows)
        for axis in range(3)
    ]
    terminal_rows = [
        row
        for row in metrics_rows
        if float(row["sim_time_seconds"]) >= final_time - stop_window_seconds
    ]
    terminal_command_max_abs = max(
        abs(float(value))
        for row in terminal_rows
        for value in row["applied_command"]
    )
    terminal_planar_speed_max_mps = max(
        math.hypot(
            float(row["root_lin_vel_w"][0]),
            float(row["root_lin_vel_w"][1]),
        )
        for row in terminal_rows
    )
    cloud_nonempty_fraction = sum(
        int(row.get("point_count", 0)) > 0 for row in sensor_rows
    ) / len(sensor_rows)
    timestamps_advance = all(
        float(right["sim_time_seconds"]) > float(left["sim_time_seconds"])
        for left, right in zip(metrics_rows, metrics_rows[1:])
    )
    return {
        "simulation_duration_seconds": final_time,
        "maximum_step_displacement_m": max(step_displacements, default=0.0),
        "command_component_max_abs": command_max_abs,
        "terminal_command_max_abs": terminal_command_max_abs,
        "terminal_planar_speed_max_mps": terminal_planar_speed_max_mps,
        "cloud_nonempty_fraction": cloud_nonempty_fraction,
        "timestamps_advance": timestamps_advance,
        "termination_count": sum(
            bool(row.get("done", False)) for row in metrics_rows
        ),
    }


def _pedestrian_motion_fidelity(
    metrics_rows: Sequence[Mapping[str, Any]],
    moving_speed_threshold_mps: float = 0.05,
) -> Dict[str, Any]:
    """Measure whether visible walk clips agree with pedestrian root motion."""

    samples = []
    timeline_motion = []
    names = set()
    for row in metrics_rows:
        row_moving = False
        for pedestrian in row.get("office_pedestrians", []):
            names.add(str(pedestrian.get("name", "")))
            velocity = pedestrian.get("velocity_xy_mps", (0.0, 0.0))
            speed = math.hypot(float(velocity[0]), float(velocity[1]))
            moving = speed >= moving_speed_threshold_mps
            walk_clip = pedestrian.get("animation", {}).get("clip") == "walk"
            samples.append((moving, walk_clip))
            row_moving = row_moving or moving
        timeline_motion.append(row_moving)

    sample_count = len(samples)
    timeline_count = len(timeline_motion)
    moving_count = sum(moving for moving, _ in samples)
    walk_count = sum(walk for _, walk in samples)
    in_place_walk_count = sum(
        walk and not moving for moving, walk in samples
    )
    idle_while_moving_count = sum(
        moving and not walk for moving, walk in samples
    )

    def fraction(count: int, total: int) -> float:
        return 0.0 if total == 0 else count / total

    return {
        "sample_count": sample_count,
        "timeline_sample_count": timeline_count,
        "pedestrian_names": sorted(name for name in names if name),
        "root_moving_fraction": fraction(moving_count, sample_count),
        "walk_clip_fraction": fraction(walk_count, sample_count),
        "in_place_walk_fraction": fraction(in_place_walk_count, sample_count),
        "idle_while_moving_fraction": fraction(
            idle_while_moving_count, sample_count
        ),
        "timeline_any_root_motion_fraction": fraction(
            sum(timeline_motion), timeline_count
        ),
        "moving_speed_threshold_mps": moving_speed_threshold_mps,
    }


def probe_video_stream(video_path: Path) -> Dict[str, Any]:
    """Inspect video file metadata using ffprobe."""
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height,nb_frames,r_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(res.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise ValueError(f"no video streams found in {video_path}")
    v_stream = streams[0]
    format_info = payload.get("format", {})

    r_fps = v_stream.get("r_frame_rate", "0/1")
    num, den = map(int, r_fps.split("/")) if "/" in r_fps else (int(r_fps), 1)
    fps = num / den if den > 0 else 0.0

    nb_frames = int(v_stream.get("nb_frames", 0))
    duration = float(format_info.get("duration", 0.0))

    return {
        "codec": v_stream.get("codec_name"),
        "width": int(v_stream.get("width", 0)),
        "height": int(v_stream.get("height", 0)),
        "fps": fps,
        "nb_frames": nb_frames,
        "duration_seconds": duration,
        "size_bytes": int(format_info.get("size", 0)),
    }


def verify_video_quality(
    video_path: Path,
    num_samples: int = 10,
    min_luma_mean: float = 25.0,
    max_luma_mean: float = 230.0,
    min_luma_std: float = 12.0,
    min_temporal_diff: float = 1.0,
) -> Dict[str, Any]:
    """Verify that the recorded MP4 video is non-blank, decoded, and contains spatial/temporal contrast."""
    meta = probe_video_stream(video_path)
    total_frames = meta["nb_frames"]
    if total_frames < 2:
        return {
            "passed": False,
            "reason": f"insufficient frames ({total_frames})",
            "metadata": meta,
        }

    step = max(1, total_frames // (num_samples + 1))
    sample_indices = [min(total_frames - 1, step * i) for i in range(1, num_samples + 1)]
    sample_indices = sorted(set(sample_indices))

    import tempfile
    import numpy as np
    from PIL import Image

    frame_stats: List[Dict[str, Any]] = []
    luma_arrays: List[np.ndarray] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for idx in sample_indices:
            out_img = tmp_path / f"frame_{idx:05d}.png"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"select=eq(n\\,{idx})",
                "-vframes", "1",
                str(out_img),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            if not out_img.is_file():
                continue
            img = Image.open(out_img)
            arr = np.array(img, dtype=np.float32)
            if arr.ndim != 3 or arr.shape[2] < 3:
                continue
            luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            luma_arrays.append(luma)
            f_mean = float(luma.mean())
            f_std = float(luma.std())
            f_min = float(luma.min())
            f_max = float(luma.max())
            passed_contrast = (min_luma_mean <= f_mean <= max_luma_mean) and (f_std >= min_luma_std)
            frame_stats.append({
                "frame_index": idx,
                "luma_mean": f_mean,
                "luma_std": f_std,
                "luma_min": f_min,
                "luma_max": f_max,
                "passed_spatial_contrast": passed_contrast,
            })

    temporal_diffs: List[float] = []
    for i in range(len(luma_arrays) - 1):
        diff = float(np.mean(np.abs(luma_arrays[i+1] - luma_arrays[i])))
        temporal_diffs.append(diff)

    mean_temporal_diff = float(np.mean(temporal_diffs)) if temporal_diffs else 0.0
    nonblank_count = sum(1 for f in frame_stats if f["passed_spatial_contrast"])
    nonblank_fraction = nonblank_count / len(frame_stats) if frame_stats else 0.0

    passed = (
        nonblank_fraction >= 0.95
        and mean_temporal_diff >= min_temporal_diff
        and meta["width"] >= 640
        and meta["height"] >= 360
    )

    return {
        "passed": passed,
        "metadata": meta,
        "nonblank_fraction": nonblank_fraction,
        "mean_temporal_diff": mean_temporal_diff,
        "sample_count": len(frame_stats),
        "frame_stats": frame_stats,
    }


def _sample_bspline_curve(control_points: Sequence[Sequence[float]], num_samples: int = 50) -> List[Tuple[float, float, float]]:
    """Sample points along a continuous 3D B-spline or control polyline."""
    import numpy as np
    cps = np.array(control_points, dtype=np.float64)
    n = len(cps)
    if n == 0:
        return []
    if n == 1:
        return [(float(cps[0, 0]), float(cps[0, 1]), float(cps[0, 2]))]

    seg_lengths = np.linalg.norm(np.diff(cps, axis=0), axis=1)
    total_len = float(np.sum(seg_lengths))
    if total_len <= 1e-6:
        return [(float(cps[0, 0]), float(cps[0, 1]), float(cps[0, 2]))]

    cum_len = np.insert(np.cumsum(seg_lengths), 0, 0.0)
    sample_distances = np.linspace(0, total_len, num_samples)
    sampled = []
    for d in sample_distances:
        idx = int(np.searchsorted(cum_len, d, side="right") - 1)
        idx = max(0, min(idx, len(seg_lengths) - 1))
        seg_len = seg_lengths[idx]
        if seg_len <= 1e-6:
            p = cps[idx]
        else:
            fraction = (d - cum_len[idx]) / seg_len
            p = cps[idx] + fraction * (cps[idx + 1] - cps[idx])
        sampled.append((float(p[0]), float(p[1]), float(p[2])))
    return sampled


def _curve_point_distance(point_xy: Tuple[float, float], curve_samples: Sequence[Tuple[float, float, float]]) -> float:
    """Compute minimum 2D Euclidean distance from a point to a sampled curve."""
    if not curve_samples:
        return math.inf
    px, py = point_xy
    return min(math.hypot(px - cx, py - cy) for cx, cy, _ in curve_samples)


def _curves_geometric_difference(curve_a: Sequence[Tuple[float, float, float]], curve_b: Sequence[Tuple[float, float, float]]) -> float:
    """Measure mean bidirectional Hausdorff-like 2D spatial difference between two curves."""
    if not curve_a or not curve_b:
        return math.inf
    d_a_to_b = sum(_curve_point_distance((x, y), curve_b) for x, y, _ in curve_a) / len(curve_a)
    d_b_to_a = sum(_curve_point_distance((x, y), curve_a) for x, y, _ in curve_b) / len(curve_b)
    return max(d_a_to_b, d_b_to_a)


def _remaining_curve(
    curve: Sequence[Tuple[float, float, float]], robot_xy: Sequence[float]
) -> List[Tuple[float, float, float]]:
    """Trim an evaluated trajectory to the portion not yet passed by the robot."""

    if not curve:
        return []
    nearest = min(
        range(len(curve)),
        key=lambda index: math.hypot(
            float(curve[index][0]) - float(robot_xy[0]),
            float(curve[index][1]) - float(robot_xy[1]),
        ),
    )
    return list(curve[nearest:])


def _nearest_metric_xy(
    metrics_rows: Sequence[Mapping[str, Any]], sim_time_s: float
) -> Tuple[float, float]:
    row = min(
        metrics_rows,
        key=lambda value: abs(float(value["sim_time_seconds"]) - sim_time_s),
    )
    return float(row["root_pos_w"][0]), float(row["root_pos_w"][1])


def _mapped_event_time(
    event: Mapping[str, Any],
    pose_events: Sequence[Tuple[int, float]],
    pose_receipts: Sequence[int],
    maximum_alignment_error_s: float,
) -> Tuple[Optional[float], Optional[float]]:
    """Map a receipt-clock event onto simulator time with an explicit error bound."""

    if event.get("kind") == "occupancy_inflate" and int(event.get("stamp_ns", 0)) > 0:
        return float(event["stamp_ns"]) * 1.0e-9, 0.0
    receipt_ns = int(event.get("receipt_monotonic_ns", 0))
    if receipt_ns <= 0 or not pose_events:
        if event.get("kind") == "bspline" and int(
            event.get("simulator_stamp_ns", 0)
        ) > 0:
            age_s = float(
                event.get("simulator_stamp_receipt_age_s", math.inf)
            )
            if 0.0 <= age_s <= maximum_alignment_error_s:
                return float(event["simulator_stamp_ns"]) * 1.0e-9, age_s
            return None, age_s
        return None, None
    insertion = bisect.bisect_left(pose_receipts, receipt_ns)
    if 0 < insertion < len(pose_events):
        left_receipt, left_simulator_time = pose_events[insertion - 1]
        right_receipt, right_simulator_time = pose_events[insertion]
        receipt_span = right_receipt - left_receipt
        simulator_span = right_simulator_time - left_simulator_time
        if receipt_span > 0 and simulator_span >= 0.0:
            fraction = (receipt_ns - left_receipt) / receipt_span
            mapped_time = left_simulator_time + fraction * simulator_span
            # The bracketing simulator interval is a conservative uncertainty
            # bound. Wall-clock spacing is intentionally irrelevant because
            # Isaac can run slower than real time.
            alignment_error_s = simulator_span
            if alignment_error_s <= maximum_alignment_error_s:
                return mapped_time, alignment_error_s
            return None, alignment_error_s
    candidates = []
    if insertion < len(pose_events):
        candidates.append(pose_events[insertion])
    if insertion > 0:
        candidates.append(pose_events[insertion - 1])
    if not candidates:
        return None, None
    receipt, simulator_time = min(
        candidates, key=lambda value: abs(value[0] - receipt_ns)
    )
    alignment_error_s = abs(receipt - receipt_ns) * 1.0e-9
    if alignment_error_s > maximum_alignment_error_s:
        return None, alignment_error_s
    return simulator_time, alignment_error_s


def _per_person_detection_rows(
    sensor_rows: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    route_names: Sequence[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """Merge per-person LiDAR/depth evidence on the simulator-time axis."""

    merged: Dict[str, Dict[float, Dict[str, Any]]] = {
        name: {} for name in route_names
    }
    for row, field, count_name in (
        (
            sensor_rows,
            "office_pedestrian_surface_hit_counts",
            "lidar_hit_count",
        ),
        (
            depth_rows,
            "office_pedestrian_surface_pixel_counts",
            "depth_pixel_count",
        ),
    ):
        for value in row:
            timestamp = float(value["sim_time_seconds"])
            counts = value.get(field) or {}
            for name in route_names:
                record = merged[name].setdefault(
                    timestamp,
                    {
                        "sim_time_seconds": timestamp,
                        "lidar_hit_count": 0,
                        "depth_pixel_count": 0,
                    },
                )
                record[count_name] = int(counts.get(name, 0))
    return {
        name: sorted(records.values(), key=lambda value: value["sim_time_seconds"])
        for name, records in merged.items()
    }


def _occupancy_near_pedestrian(
    occupancy_events: Sequence[Mapping[str, Any]],
    route: OfficePedestrianRoute,
    detection_time_s: float,
    replan_time_s: float,
    maximum_distance_m: float,
) -> Optional[Dict[str, Any]]:
    """Find real SCAN inflated occupancy near the detected pedestrian."""

    best = None
    for event in occupancy_events:
        event_time = float(event["mapped_sim_time_s"])
        if event_time < detection_time_s - 0.15 or event_time > replan_time_s + 0.10:
            continue
        pedestrian = office_pedestrian_state(event_time, route)
        px, py = pedestrian["xy_m"]
        points = event.get("points_xyz") or []
        if not points:
            continue
        minimum = min(
            math.hypot(float(point[0]) - px, float(point[1]) - py)
            for point in points
        )
        if minimum <= maximum_distance_m and (
            best is None or minimum < best["minimum_distance_m"]
        ):
            best = {
                "sim_time_seconds": event_time,
                "minimum_distance_m": minimum,
                "source_point_count": int(event.get("point_count", len(points))),
                "sample_count": int(event.get("sample_count", len(points))),
            }
    return best


def audit_active_path_causal_replans(
    metrics_rows: Sequence[Mapping[str, Any]],
    sensor_rows: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    ros_events: Optional[Sequence[Mapping[str, Any]]] = None,
    routes: Optional[Sequence[OfficePedestrianRoute]] = None,
    sparse_waypoints: Optional[Sequence[Sequence[float]]] = None,
    spatial_envelope_radius_m: float = 1.20,
    min_replan_geometric_diff_m: float = 0.08,
    bspline_events: Optional[Sequence[Mapping[str, Any]]] = None,
    maximum_clock_alignment_error_s: float = 0.20,
    detection_lookback_s: float = 1.0,
    minimum_lidar_hits: int = 3,
    minimum_depth_pixels: int = 5,
    occupancy_match_distance_m: float = 0.85,
) -> Dict[str, Any]:
    """Require sensor detection, active-path intrusion, SCAN occupancy, and replacement."""
    routes = tuple(routes or ())
    sparse_waypoints = tuple(sparse_waypoints or ())
    if ros_events is not None:
        all_events = ros_events
        bspline_list = [e for e in ros_events if e.get("kind") == "bspline"]
    elif bspline_events is not None:
        all_events = bspline_events
        bspline_list = list(bspline_events)
    else:
        all_events = []
        bspline_list = []

    if not bspline_list or not metrics_rows:
        return {
            "passed": False,
            "reason": "missing bspline events or metrics",
            "trajectories": [],
            "reactive_replans": [],
        }

    # Time synchronization mapping via simulator-stamped body poses
    pose_events = sorted(
        (
            (int(event["receipt_monotonic_ns"]), float(event["stamp_ns"]) * 1e-9)
            for event in all_events
            if event.get("kind") == "body_pose" and "receipt_monotonic_ns" in event and "stamp_ns" in event
        ),
        key=lambda item: item[0],
    )
    pose_receipts = [item[0] for item in pose_events]
    # Build trajectory records with sampled curves and target waypoints
    trajectories: List[Dict[str, Any]] = []
    for event in bspline_list:
        traj_id = int(event.get("trajectory_id", 0))
        cps = event.get("control_points", [])
        receipt_ns = int(event.get("receipt_monotonic_ns", 0))
        receipt_s = receipt_ns * 1e-9 if receipt_ns > 0 else None
        sim_t, alignment_error_s = _mapped_event_time(
            event,
            pose_events,
            pose_receipts,
            maximum_clock_alignment_error_s,
        )
        if sim_t is None:
            return {
                "passed": False,
                "reason": "B-spline receipt cannot be aligned to simulator time",
                "trajectory_id": traj_id,
                "alignment_error_s": alignment_error_s,
                "reactive_replans": [],
            }
        try:
            curve = list(
                sample_uniform_bspline(
                    int(event["order"]),
                    event["knots"],
                    cps,
                    sample_count=100,
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            return {
                "passed": False,
                "reason": f"invalid B-spline event {traj_id}: {error}",
                "reactive_replans": [],
            }

        # Identify target waypoint
        end_pt = cps[-1][:2] if cps else (0.0, 0.0)
        target_wp_idx = min(
            range(len(sparse_waypoints)),
            key=lambda idx: math.hypot(end_pt[0] - sparse_waypoints[idx][0], end_pt[1] - sparse_waypoints[idx][1]),
        ) if sparse_waypoints else -1

        trajectories.append({
            "trajectory_id": traj_id,
            "receipt_monotonic_s": receipt_s,
            "mapped_sim_time_s": sim_t,
            "clock_alignment_error_s": alignment_error_s,
            "control_point_count": len(cps),
            "start_xy": cps[0][:2] if cps else None,
            "end_xy": end_pt,
            "target_waypoint_index": target_wp_idx,
            "curve_samples": curve,
            "classification": "unclassified",
        })

    # Classify each trajectory
    for i, traj in enumerate(trajectories):
        t = traj["mapped_sim_time_s"]
        if t <= 2.0 and i <= 2:
            traj["classification"] = "startup_refinement"
        elif i > 0 and traj["target_waypoint_index"] != trajectories[i-1]["target_waypoint_index"]:
            traj["classification"] = "waypoint_progression"
        else:
            traj["classification"] = "potential_replan"

    # Only declared crossing routes can satisfy AC54.
    crossing_routes = [r for r in routes if r.name.startswith("crossing")]
    if not crossing_routes:
        return {
            "passed": False,
            "reason": "no declared crossing pedestrian routes",
            "reactive_replans": [],
        }
    detections = _per_person_detection_rows(
        sensor_rows, depth_rows, [route.name for route in crossing_routes]
    )
    occupancy_events = []
    for event in all_events:
        if event.get("kind") != "occupancy_inflate":
            continue
        sim_t, alignment_error_s = _mapped_event_time(
            event,
            pose_events,
            pose_receipts,
            maximum_clock_alignment_error_s,
        )
        if sim_t is None:
            continue
        occupancy_events.append(
            {
                **event,
                "mapped_sim_time_s": sim_t,
                "clock_alignment_error_s": alignment_error_s,
            }
        )

    reactive_replans: List[Dict[str, Any]] = []
    candidate_diagnostics: List[Dict[str, Any]] = []

    for i in range(1, len(trajectories)):
        curr_traj = trajectories[i]
        prev_traj = trajectories[i-1]
        t_pub = curr_traj["mapped_sim_time_s"]

        # If it's a waypoint progression or startup, it's not a reactive obstacle replan
        if curr_traj["classification"] in ("startup_refinement", "waypoint_progression"):
            continue

        robot_xy = _nearest_metric_xy(metrics_rows, t_pub)
        previous_remaining = _remaining_curve(prev_traj["curve_samples"], robot_xy)
        current_remaining = _remaining_curve(curr_traj["curve_samples"], robot_xy)
        geom_diff = _curves_geometric_difference(
            current_remaining, previous_remaining
        )

        causal_pedestrian = None
        route_diagnostics = []
        for route in crossing_routes:
            qualifying = [
                value
                for value in detections[route.name]
                if t_pub - detection_lookback_s
                <= float(value["sim_time_seconds"])
                <= t_pub
                and (
                    int(value["lidar_hit_count"]) >= minimum_lidar_hits
                    or int(value["depth_pixel_count"]) >= minimum_depth_pixels
                )
            ]
            route_diagnostic = {
                "route_name": route.name,
                "qualifying_detection_count": len(qualifying),
            }
            for detection in reversed(qualifying):
                detection_time = float(detection["sim_time_seconds"])
                pedestrian = office_pedestrian_state(detection_time, route)
                route_diagnostic.update(
                    {
                        "latest_detection_sim_time_s": detection_time,
                        "latest_phase": pedestrian["phase"],
                        "latest_lidar_hit_count": int(
                            detection["lidar_hit_count"]
                        ),
                        "latest_depth_pixel_count": int(
                            detection["depth_pixel_count"]
                        ),
                    }
                )
                if pedestrian["phase"] != "walking":
                    continue
                distance = _curve_point_distance(
                    pedestrian["xy_m"], previous_remaining
                )
                route_diagnostic["latest_distance_to_active_path_m"] = distance
                if distance > spatial_envelope_radius_m:
                    continue
                occupancy = _occupancy_near_pedestrian(
                    occupancy_events,
                    route,
                    detection_time,
                    t_pub,
                    occupancy_match_distance_m,
                )
                if occupancy is None:
                    continue
                route_diagnostic["scan_occupancy_found"] = True
                causal_pedestrian = {
                    "route_name": route.name,
                    "pedestrian_xy": pedestrian["xy_m"],
                    "distance_to_active_path_m": distance,
                    "detection_sim_time_s": detection_time,
                    "lidar_hit_count": int(detection["lidar_hit_count"]),
                    "depth_pixel_count": int(detection["depth_pixel_count"]),
                    "scan_occupancy": occupancy,
                }
                break
            route_diagnostic.setdefault("scan_occupancy_found", False)
            route_diagnostics.append(route_diagnostic)
            if causal_pedestrian is not None:
                break

        candidate_diagnostics.append(
            {
                "trajectory_id": curr_traj["trajectory_id"],
                "replan_sim_time_s": t_pub,
                "geometric_difference_m": geom_diff,
                "target_waypoint_index": curr_traj["target_waypoint_index"],
                "route_evidence": route_diagnostics,
            }
        )

        if causal_pedestrian is not None and geom_diff >= min_replan_geometric_diff_m:
            curr_traj["classification"] = "reactive_obstacle_replan"
            reactive_replans.append({
                "trajectory_id": curr_traj["trajectory_id"],
                "replan_sim_time_s": t_pub,
                "trigger_pedestrian": causal_pedestrian["route_name"],
                "pedestrian_distance_to_path_m": causal_pedestrian["distance_to_active_path_m"],
                "detection_sim_time_s": causal_pedestrian["detection_sim_time_s"],
                "lidar_hit_count": causal_pedestrian["lidar_hit_count"],
                "depth_pixel_count": causal_pedestrian["depth_pixel_count"],
                "scan_occupancy": causal_pedestrian["scan_occupancy"],
                "geometric_difference_m": geom_diff,
                "target_waypoint_index": curr_traj["target_waypoint_index"],
            })
        else:
            curr_traj["classification"] = "untriggered_replan"

    passed = len(reactive_replans) >= 1
    return {
        "passed": passed,
        "total_trajectories": len(trajectories),
        "reactive_replan_count": len(reactive_replans),
        "reactive_replans": reactive_replans,
        "occupancy_event_count": len(occupancy_events),
        "candidate_diagnostics": candidate_diagnostics,
        "required_evidence": {
            "per_person_sensor_detection": True,
            "remaining_active_bspline_intrusion": True,
            "scan_inflated_occupancy_near_person": True,
            "later_true_bspline_geometry_change": True,
        },
        "trajectory_classifications": [
            {
                "trajectory_id": t["trajectory_id"],
                "classification": t["classification"],
                "mapped_sim_time_s": t["mapped_sim_time_s"],
                "target_waypoint_index": t["target_waypoint_index"],
            }
            for t in trajectories
        ],
    }


def evaluate_office_acceptance(
    thresholds: Mapping[str, Any],
    metrics_rows: Sequence[Mapping[str, Any]],
    sensor_rows: Sequence[Mapping[str, Any]],
    depth_rows: Sequence[Mapping[str, Any]],
    isaac_report: Mapping[str, Any],
    run_identity: Mapping[str, Any],
    ros_summary: Mapping[str, Any],
    ros_events: Sequence[Mapping[str, Any]],
    foxy_log_text: str,
    video_path: Path,
    overlay_video_path: Optional[Path],
    trajectory_review_metadata: Optional[Mapping[str, Any]],
    preflight_payload: Mapping[str, Any],
    effective_input_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprehensive Office L0 crowd acceptance check against frozen criteria."""
    limits = thresholds["thresholds"]
    checks: Dict[str, Any] = {}

    def add(name: str, passed: bool, value: Any, expected: Any) -> None:
        checks[name] = {"passed": bool(passed), "value": value, "expected": expected}

    # 1. Goal XY error
    final_pos = metrics_rows[-1]["root_pos_w"][:2]
    expected_goal = preflight_payload["goal_xy_m"]
    goal_error = math.dist(final_pos, expected_goal)
    max_goal_limit = float(limits.get("goal_xy_tolerance_m", limits.get("goal_xy_error_m", 0.25)))
    add("goal_xy_error", goal_error <= max_goal_limit, {"goal_xy_error_m": goal_error, "final_pos": final_pos}, {"max_allowed": max_goal_limit, "goal": expected_goal})

    # 2. Nonfoot contact force
    max_nonfoot = max(float(r.get("nonfoot_contact_max_n", 0.0)) for r in metrics_rows)
    max_nonfoot_limit = float(limits.get("maximum_nonfoot_contact_n", limits.get("max_nonfoot_contact_n", 75.0)))
    add("nonfoot_contact_force", max_nonfoot <= max_nonfoot_limit, {"max_nonfoot_contact_n": max_nonfoot}, {"max_allowed": max_nonfoot_limit})

    # 3. Watchdog zero
    total_watchdogs = max(int(r.get("watchdog_events", 0)) for r in metrics_rows)
    max_watchdogs = int(limits.get("maximum_watchdog_events", 0))
    add("watchdog_zero", total_watchdogs <= max_watchdogs, {"watchdog_events": total_watchdogs}, {"maximum_allowed": max_watchdogs})

    # 4. Root Z height range
    z_vals = [float(r["root_pos_w"][2]) for r in metrics_rows]
    z_min, z_max = min(z_vals), max(z_vals)
    z_range_expected = limits.get("root_height_range_m", limits.get("root_z_range_m", [0.25, 0.45]))
    add("root_z_range", z_min >= z_range_expected[0] and z_max <= z_range_expected[1], {"min_z": z_min, "max_z": z_max}, {"expected_range": z_range_expected})

    # 5. Pairwise pedestrian precheck
    office_identity = run_identity.get("office_crowd", {})
    pedestrian_motion_mode = str(
        office_identity.get("pedestrian_motion_mode", "single_pass")
    )
    pedestrian_turnaround_hold_s = float(
        office_identity.get("pedestrian_turnaround_hold_s", 0.0)
    )
    routes = routes_from_preflight(
        preflight_payload,
        motion_mode=pedestrian_motion_mode,
        turnaround_hold_s=pedestrian_turnaround_hold_s,
    )
    pair_check = pairwise_clearance_precheck(routes, duration_s=float(metrics_rows[-1]["sim_time_seconds"]))
    min_pair_clearance = float(pair_check["minimum_surface_clearance_m"])
    min_pair_limit = float(limits.get("minimum_pairwise_pedestrian_clearance_m", limits.get("pedestrian_pairwise_clearance_m", 0.05)))
    add("pedestrian_pairwise_clearance", min_pair_clearance >= min_pair_limit, {"min_surface_clearance_m": min_pair_clearance}, {"minimum_required": min_pair_limit})

    if pedestrian_motion_mode in ("background_ping_pong", "ping_pong"):
        motion_fidelity = _pedestrian_motion_fidelity(metrics_rows)
        motion_fidelity_passed = (
            len(motion_fidelity["pedestrian_names"]) == 8
            and motion_fidelity["root_moving_fraction"] >= 0.50
            and motion_fidelity["timeline_any_root_motion_fraction"] >= 0.95
            and motion_fidelity["in_place_walk_fraction"] <= 0.01
            and motion_fidelity["idle_while_moving_fraction"] <= 0.01
        )
        add(
            "pedestrian_motion_fidelity",
            motion_fidelity_passed,
            motion_fidelity,
            {
                "pedestrian_count": 8,
                "minimum_root_moving_fraction": 0.50,
                "minimum_timeline_any_root_motion_fraction": 0.95,
                "maximum_in_place_walk_fraction": 0.01,
                "maximum_idle_while_moving_fraction": 0.01,
            },
        )

    # 6. Conservative pedestrian clearance
    min_robot_person_clearance = math.inf
    closest_person = None
    closest_time = None
    robot_radius = float(limits.get("robot_collision_radius_m", 0.35))
    for r in metrics_rows:
        t = float(r["sim_time_seconds"])
        r_xy = r["root_pos_w"][:2]
        for route in routes:
            st = office_pedestrian_state(t, route)
            c = math.dist(r_xy, st["xy_m"]) - (robot_radius + route.radius_m)
            if c < min_robot_person_clearance:
                min_robot_person_clearance = c
                closest_person = route.name
                closest_time = t
    min_clearance_limit = float(limits.get("minimum_conservative_pedestrian_clearance_m", limits.get("minimum_pedestrian_clearance_m", 0.15)))
    add("conservative_pedestrian_clearance", min_robot_person_clearance >= min_clearance_limit, {"min_conservative_clearance_m": min_robot_person_clearance, "closest_pedestrian": closest_person, "time_s": closest_time}, {"minimum_clearance_m": min_clearance_limit})

    # 7. LiDAR pedestrian hits
    max_lidar_hits = max(int(r.get("office_pedestrian_surface_hit_count", 0)) for r in sensor_rows)
    min_lidar_hits = int(limits.get("minimum_lidar_pedestrian_hits", limits.get("min_lidar_pedestrian_hits", 10)))
    add("mid360_pedestrian_hits", max_lidar_hits >= min_lidar_hits, {"max_lidar_pedestrian_hits": max_lidar_hits}, {"minimum_required": min_lidar_hits})

    # 8. D435i pedestrian depth pixels
    max_depth_px = max(int(r.get("office_pedestrian_surface_pixel_count", 0)) for r in depth_rows)
    min_depth_px = int(limits.get("minimum_depth_pedestrian_pixels", limits.get("min_depth_pedestrian_pixels", 10)))
    add("d435i_pedestrian_pixels", max_depth_px >= min_depth_px, {"max_depth_pedestrian_pixels": max_depth_px}, {"minimum_required": min_depth_px})

    # 9. Retained static cloud points
    static_counts = [int(r.get("point_count", r.get("obstacle_surface_hit_count", r.get("valid_points", 0)))) for r in sensor_rows]
    min_static, max_static = min(static_counts), max(static_counts)
    min_static_limit = int(limits.get("minimum_static_cloud_points", limits.get("min_retained_static_cloud_points", 1000)))
    add("retained_static_cloud_points", min_static >= min_static_limit, {"min_static_points": min_static, "max_static_points": max_static}, {"minimum_required": min_static_limit})

    # 10. Trajectory count
    bspline_events = [e for e in ros_events if e.get("kind") == "bspline"]
    unique_traj_ids = len({int(e.get("trajectory_id", 0)) for e in bspline_events})
    min_trajs = int(limits.get("minimum_unique_trajectories", limits.get("min_unique_trajectories", 2)))
    add("multiple_trajectories", unique_traj_ids >= min_trajs, {"unique_trajectory_count": unique_traj_ids}, {"minimum_required": min_trajs})

    # 11. No SCAN emergency stop
    emergency_stops = ros_summary.get("emergency_stops", 0)
    max_e_stops = int(limits.get("maximum_emergency_stops", limits.get("max_scan_emergency_stops", 0)))
    add("no_scan_emergency_stop", emergency_stops <= max_e_stops, {"emergency_stop_count": emergency_stops}, {"maximum_allowed": max_e_stops})

    # 12. Finite policy & support
    supported_contacts = sum(1 for r in metrics_rows if int(r.get("contact_count", 0)) >= 1)
    support_fraction = supported_contacts / len(metrics_rows) if metrics_rows else 0.0
    min_support_limit = float(limits.get("minimum_supported_contact_fraction", 0.95))
    finite_policy = all(
        bool(r.get("finite", True))
        and all(math.isfinite(float(v)) for v in r.get("applied_command", []))
        and all(math.isfinite(float(v)) for v in r.get("root_pos_w", []))
        for r in metrics_rows
    )
    add("finite_policy_and_support", finite_policy and support_fraction >= min_support_limit, {"finite_policy": finite_policy, "support_fraction": support_fraction}, {"expected_finite": True, "minimum_support_fraction": min_support_limit})

    # 13. Transport clean
    proto_err = ros_summary.get("protocol_errors", 0)
    seq_gaps = ros_summary.get("sequence_gaps", 0)
    reconnects = ros_summary.get("reconnects", 0)
    add("transport_clean", proto_err == 0 and seq_gaps == 0 and reconnects == 0, {"protocol_errors": proto_err, "sequence_gaps": seq_gaps, "reconnects": reconnects}, {"protocol_errors": 0, "sequence_gaps": 0, "reconnects": 0})

    # 14. Rates nominal
    p_hz = _rate(metrics_rows)
    s_hz = _rate(sensor_rows)
    p_range = limits["policy_rate_hz_range"]
    s_range = limits["sensor_rate_hz_range"]
    add("rates_nominal", p_range[0] <= p_hz <= p_range[1] and s_range[0] <= s_hz <= s_range[1], {"policy_rate_hz": p_hz, "sensor_rate_hz": s_hz}, {"policy_rate_hz_range": p_range, "sensor_rate_hz_range": s_range})

    # 15. Frozen runtime duration, motion, command, stop, and cloud gates
    runtime = _runtime_gate_metrics(
        metrics_rows,
        sensor_rows,
        float(limits["stop_window_seconds"]),
    )
    minimum_duration = float(limits["minimum_sim_duration_seconds"])
    add(
        "simulation_duration",
        runtime["simulation_duration_seconds"] >= minimum_duration,
        runtime["simulation_duration_seconds"],
        {"minimum_seconds": minimum_duration},
    )
    command_limits = [
        float(value) for value in limits["command_component_max_abs"]
    ]
    command_epsilon = float(limits["command_bound_epsilon"])
    add(
        "command_bounds",
        all(
            actual <= expected + command_epsilon
            for actual, expected in zip(
                runtime["command_component_max_abs"], command_limits
            )
        ),
        runtime["command_component_max_abs"],
        {"maximum_abs": command_limits, "epsilon": command_epsilon},
    )
    maximum_step = float(limits["maximum_step_displacement_m"])
    add(
        "step_displacement_and_no_reset",
        runtime["maximum_step_displacement_m"] <= maximum_step
        and runtime["timestamps_advance"]
        and runtime["termination_count"] == 0,
        {
            "maximum_step_displacement_m": runtime[
                "maximum_step_displacement_m"
            ],
            "timestamps_advance": runtime["timestamps_advance"],
            "termination_count": runtime["termination_count"],
        },
        {
            "maximum_step_displacement_m": maximum_step,
            "timestamps_advance": True,
            "termination_count": 0,
        },
    )
    add(
        "terminal_stop",
        runtime["terminal_command_max_abs"]
        <= float(limits["stop_command_max_abs"])
        and runtime["terminal_planar_speed_max_mps"]
        <= float(limits["stop_planar_speed_max_mps"]),
        {
            "terminal_command_max_abs": runtime["terminal_command_max_abs"],
            "terminal_planar_speed_max_mps": runtime[
                "terminal_planar_speed_max_mps"
            ],
        },
        {
            "maximum_command_abs": limits["stop_command_max_abs"],
            "maximum_planar_speed_mps": limits["stop_planar_speed_max_mps"],
            "window_seconds": limits["stop_window_seconds"],
        },
    )
    minimum_nonempty = float(limits["minimum_cloud_nonempty_fraction"])
    add(
        "cloud_nonempty_fraction",
        runtime["cloud_nonempty_fraction"] >= minimum_nonempty,
        runtime["cloud_nonempty_fraction"],
        {"minimum_fraction": minimum_nonempty},
    )

    # 16. Real Video Quality Gate (ffprobe + nonblank luma + temporal contrast)
    video_qual = verify_video_quality(video_path)
    minimum_video_frames = int(limits["minimum_video_frames"])
    video_frame_count = int(video_qual.get("metadata", {}).get("nb_frames", 0))
    add("video_quality_and_visibility", video_qual["passed"] and video_frame_count >= minimum_video_frames, {
        "raw_video_path": str(video_path),
        "nonblank_fraction": video_qual.get("nonblank_fraction", 0.0),
        "mean_temporal_diff": video_qual.get("mean_temporal_diff", 0.0),
        "frame_count": video_frame_count,
        "metadata": video_qual.get("metadata", {}),
    }, {
        "min_nonblank_fraction": 0.95,
        "min_temporal_diff": 1.0,
        "min_width": 640,
        "min_height": 360,
        "minimum_frame_count": minimum_video_frames,
    })

    # 17. Clock-consistent active-path causal replan audit
    sparse_wps = preflight_payload.get("scan_sparse_waypoints_xyz_m", [])
    causal_audit = audit_active_path_causal_replans(
        metrics_rows=metrics_rows,
        sensor_rows=sensor_rows,
        depth_rows=depth_rows,
        ros_events=ros_events,
        routes=routes,
        sparse_waypoints=sparse_wps,
    )
    add("causal_active_path_replan_audit", causal_audit["passed"], causal_audit, {"required_reactive_replans": 1})

    all_passed = all(check["passed"] for check in checks.values())

    v_meta = video_qual.get("metadata", {})
    return {
        "schema_version": 2,
        "status": "PASS" if all_passed else "FAIL",
        "claim": "single-scenario Foxy-SCAN to V12-policy Lite3-Pro-sensor-rig reactive moving-occupancy Office L0 eight-person crowd simulation",
        "checks": checks,
        "summary": {
            "goal_xy_error_m": goal_error,
            "final_position_world_xy_m": [float(final_pos[0]), float(final_pos[1])],
            "max_nonfoot_contact_n": max_nonfoot,
            "watchdog_events": total_watchdogs,
            "min_root_z_m": z_min,
            "max_root_z_m": z_max,
            "min_conservative_pedestrian_clearance_m": min_robot_person_clearance,
            "max_lidar_pedestrian_hits": max_lidar_hits,
            "max_depth_pedestrian_pixels": max_depth_px,
            "unique_trajectory_count": unique_traj_ids,
            "reactive_replan_count": causal_audit.get("reactive_replan_count", 0),
            "policy_rate_hz": p_hz,
            "sensor_rate_hz": s_hz,
            "video_sha256": _sha256(video_path) if video_path.is_file() else None,
            "video_duration_seconds": v_meta.get("duration_seconds"),
            "video_frame_count": v_meta.get("nb_frames"),
            "overlay_sha256": _sha256(overlay_video_path) if overlay_video_path and overlay_video_path.is_file() else None,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Office crowd acceptance against frozen criteria.")
    parser.add_argument("--thresholds", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--sensor-metrics", type=Path, required=True)
    parser.add_argument("--depth-metrics", type=Path, required=True)
    parser.add_argument("--isaac-report", type=Path, required=True)
    parser.add_argument("--run-identity", type=Path, required=True)
    parser.add_argument("--ros-summary", type=Path, required=True)
    parser.add_argument("--ros-events", type=Path, required=True)
    parser.add_argument("--foxy-log", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--overlay-video", type=Path)
    parser.add_argument("--trajectory-review-metadata", type=Path)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--effective-input", type=Path)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))
    metrics_rows = _load_jsonl(args.metrics)
    sensor_rows = _load_jsonl(args.sensor_metrics)
    depth_rows = _load_jsonl(args.depth_metrics)
    isaac_report = json.loads(args.isaac_report.read_text(encoding="utf-8"))
    run_identity = json.loads(args.run_identity.read_text(encoding="utf-8"))
    ros_summary = json.loads(args.ros_summary.read_text(encoding="utf-8"))
    ros_events = [json.loads(line) for line in args.ros_events.read_text(encoding="utf-8").splitlines() if line.strip()]
    foxy_log = args.foxy_log.read_text(encoding="utf-8") if args.foxy_log.is_file() else ""
    traj_meta = json.loads(args.trajectory_review_metadata.read_text(encoding="utf-8")) if args.trajectory_review_metadata and args.trajectory_review_metadata.is_file() else None
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    effective_input = args.effective_input.read_text(encoding="utf-8") if args.effective_input and args.effective_input.is_file() else None

    report = evaluate_office_acceptance(
        thresholds=thresholds,
        metrics_rows=metrics_rows,
        sensor_rows=sensor_rows,
        depth_rows=depth_rows,
        isaac_report=isaac_report,
        run_identity=run_identity,
        ros_summary=ros_summary,
        ros_events=ros_events,
        foxy_log_text=foxy_log,
        video_path=args.video,
        overlay_video_path=args.overlay_video,
        trajectory_review_metadata=traj_meta,
        preflight_payload=preflight,
        effective_input_text=effective_input,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
