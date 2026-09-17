"""Render a traceable SCAN-planned versus Isaac-actual review overlay."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Iterable, Mapping, Sequence


PLAN_COLOR_BGR = (80, 220, 80)
ACTUAL_COLOR_BGR = (255, 220, 40)
PRIMARY_OBSTACLE_COLOR_BGR = (40, 70, 245)
OBSTACLE_COLOR_BGR = (145, 145, 145)
DYNAMIC_OBSTACLE_COLOR_BGR = (0, 120, 255)
DYNAMIC_HUMAN_COLOR_BGR = (0, 215, 255)
DYNAMIC_OFFICIAL_HUMAN_COLOR_BGR = (40, 40, 235)
SCAN_OCCUPANCY_COLOR_BGR = (40, 90, 245)


def dynamic_obstacle_color_bgr(identity: Mapping[str, object]) -> tuple[int, int, int]:
    dynamic_identity = identity.get("dynamic_obstacle") or {}
    shape = dynamic_identity.get("shape")
    if shape == "official_skinned_human_plus_capsule":
        return DYNAMIC_OFFICIAL_HUMAN_COLOR_BGR
    if shape == "procedural_humanoid":
        return DYNAMIC_HUMAN_COLOR_BGR
    return DYNAMIC_OBSTACLE_COLOR_BGR


def dynamic_obstacle_label(identity: Mapping[str, object]) -> str:
    dynamic_identity = identity.get("dynamic_obstacle") or {}
    shape = dynamic_identity.get("shape")
    if shape == "official_skinned_human_plus_capsule":
        return "Official human actual"
    if shape == "procedural_humanoid":
        return "Procedural human actual"
    return "Dynamic obstacle actual"


def _finite_point(point: Sequence[float]) -> tuple[float, float, float]:
    if len(point) != 3:
        raise ValueError("B-spline points must contain three coordinates")
    checked = tuple(float(value) for value in point)
    if not all(math.isfinite(value) for value in checked):
        raise ValueError("B-spline points must be finite")
    return checked


def sample_uniform_bspline(
    order: int,
    knots: Sequence[float],
    control_points: Sequence[Sequence[float]],
    sample_count: int = 160,
) -> tuple[tuple[float, float, float], ...]:
    """Sample the exact B-spline payload using the de Boor algorithm."""

    degree = int(order)
    points = tuple(_finite_point(point) for point in control_points)
    checked_knots = tuple(float(value) for value in knots)
    if degree < 1 or len(points) < degree + 1:
        raise ValueError("B-spline order and control-point count are invalid")
    if len(checked_knots) != len(points) + degree + 1:
        raise ValueError("B-spline knot count is inconsistent with its shape")
    if sample_count < 2:
        raise ValueError("B-spline sampling needs at least two points")
    if not all(math.isfinite(value) for value in checked_knots):
        raise ValueError("B-spline knots must be finite")
    if any(left > right for left, right in zip(checked_knots, checked_knots[1:])):
        raise ValueError("B-spline knots must be non-decreasing")

    start = checked_knots[degree]
    end = checked_knots[len(points)]
    if end <= start:
        raise ValueError("B-spline parameter interval must be positive")

    def evaluate(parameter: float) -> tuple[float, float, float]:
        if parameter >= end:
            span = len(points) - 1
        else:
            span = bisect.bisect_right(checked_knots, parameter) - 1
            span = max(degree, min(span, len(points) - 1))
        work = [
            list(points[span - degree + index])
            for index in range(degree + 1)
        ]
        for recursion in range(1, degree + 1):
            for index in range(degree, recursion - 1, -1):
                knot_index = span - degree + index
                denominator = (
                    checked_knots[knot_index + degree - recursion + 1]
                    - checked_knots[knot_index]
                )
                alpha = (
                    0.0
                    if denominator == 0.0
                    else (parameter - checked_knots[knot_index]) / denominator
                )
                work[index] = [
                    (1.0 - alpha) * work[index - 1][axis]
                    + alpha * work[index][axis]
                    for axis in range(3)
                ]
        return tuple(work[degree])

    return tuple(
        evaluate(start + (end - start) * index / (sample_count - 1))
        for index in range(sample_count)
    )


def associate_bspline_sim_times(
    events: Sequence[Mapping[str, object]], sample_count: int = 160
) -> tuple[Mapping[str, object], ...]:
    """Interpolate each plan receipt on the simulator-stamped body-pose clock."""

    pose_events = sorted(
        (
            (int(event["receipt_monotonic_ns"]), int(event["stamp_ns"]))
            for event in events
            if event.get("kind") == "body_pose"
        ),
        key=lambda item: item[0],
    )
    if not pose_events:
        raise ValueError("trajectory review needs simulator-stamped body poses")
    pose_receipts = [item[0] for item in pose_events]
    plans = []
    for event in events:
        if event.get("kind") != "bspline":
            continue
        receipt = int(event["receipt_monotonic_ns"])
        insertion = bisect.bisect_left(pose_receipts, receipt)
        mapping_method = "nearest_pose_edge_fallback"
        if 0 < insertion < len(pose_events):
            left_receipt, left_stamp = pose_events[insertion - 1]
            right_receipt, right_stamp = pose_events[insertion]
            receipt_span = right_receipt - left_receipt
            if receipt_span > 0 and right_stamp >= left_stamp:
                fraction = (receipt - left_receipt) / receipt_span
                simulator_stamp = left_stamp + fraction * (
                    right_stamp - left_stamp
                )
                alignment_error_ms = (right_stamp - left_stamp) / 1.0e6
                nearest_receipt = min(
                    (left_receipt, right_receipt),
                    key=lambda value: abs(value - receipt),
                )
                mapping_method = "bracketed_simulator_time_interpolation"
            else:
                insertion = 0
        if mapping_method == "nearest_pose_edge_fallback":
            candidates = []
            if insertion < len(pose_events):
                candidates.append(pose_events[insertion])
            if insertion > 0:
                candidates.append(pose_events[insertion - 1])
            nearest_receipt, simulator_stamp = min(
                candidates, key=lambda item: abs(item[0] - receipt)
            )
            alignment_error_ms = abs(nearest_receipt - receipt) / 1.0e6
        sampled = sample_uniform_bspline(
            int(event["order"]),
            event["knots"],
            event["control_points"],
            sample_count=sample_count,
        )
        plans.append(
            {
                "trajectory_id": int(event["trajectory_id"]),
                "receipt_monotonic_ns": receipt,
                "nearest_pose_receipt_monotonic_ns": nearest_receipt,
                "receipt_alignment_error_ms": alignment_error_ms,
                "mapping_method": mapping_method,
                "effective_sim_time_seconds": simulator_stamp / 1.0e9,
                "start_time_ns": int(event["start_time_ns"]),
                "sampled_points": sampled,
            }
        )
    if not plans:
        raise ValueError("trajectory review needs at least one complete B-spline")
    return tuple(sorted(plans, key=lambda item: item["effective_sim_time_seconds"]))


def frame_metric_rows(
    metrics: Sequence[Mapping[str, object]], frame_stride: int, frame_count: int
) -> tuple[Mapping[str, object], ...]:
    """Return the exact Isaac step records at which raw frames were captured."""

    if frame_stride <= 0 or frame_count <= 0:
        raise ValueError("frame stride and video frame count must be positive")
    selected = [
        row for row in metrics if int(row["step"]) % int(frame_stride) == 0
    ]
    if len(selected) < frame_count:
        raise ValueError(
            f"metrics cover {len(selected)} video frames but {frame_count} are encoded"
        )
    return tuple(selected[:frame_count])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[Mapping[str, object]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows:
        raise ValueError(f"required JSONL is empty: {path}")
    return rows


def _plot_bounds(
    plans: Sequence[Mapping[str, object]],
    metrics: Sequence[Mapping[str, object]],
    navigation: Mapping[str, object],
) -> tuple[float, float, float, float]:
    points = []
    for key in ("start_world_m", "goal_world_m"):
        value = navigation.get(key)
        if value and len(value) >= 2:
            points.append((float(value[0]), float(value[1])))
    points.extend(
        (float(row["root_pos_w"][0]), float(row["root_pos_w"][1]))
        for row in metrics
    )
    points.extend(
        (
            float(row["dynamic_obstacle_actual_pos_w"][0]),
            float(row["dynamic_obstacle_actual_pos_w"][1]),
        )
        for row in metrics
        if row.get("dynamic_obstacle_actual_pos_w") is not None
    )
    for plan in plans:
        points.extend((float(point[0]), float(point[1])) for point in plan["sampled_points"])
    if not points:
        raise ValueError("trajectory overlay has no world points")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_span = max(1.0, max(xs) - min(xs))
    y_span = max(1.0, max(ys) - min(ys))
    padding = 0.12 * max(x_span, y_span) + 0.25
    return min(xs) - padding, max(xs) + padding, min(ys) - padding, max(ys) + padding


def _world_to_inset(
    point: Sequence[float],
    bounds: Sequence[float],
    inset_origin: tuple[int, int],
    inset_size: tuple[int, int],
) -> tuple[int, int]:
    x_min, x_max, y_min, y_max = bounds
    x_fraction = (float(point[0]) - x_min) / (x_max - x_min)
    y_fraction = (float(point[1]) - y_min) / (y_max - y_min)
    left, top = inset_origin
    width, height = inset_size
    return (
        left + int(round(x_fraction * (width - 1))),
        top + height - 1 - int(round(y_fraction * (height - 1))),
    )


def _polyline(points: Iterable[Sequence[float]], mapper) -> list[tuple[int, int]]:
    return [mapper(point) for point in points]


def render_trajectory_review(
    raw_video: Path,
    ros_events_path: Path,
    metrics_path: Path,
    run_identity_path: Path,
    output_video: Path,
    metadata_path: Path,
) -> Mapping[str, object]:
    """Render and hash the review overlay while preserving the raw MP4."""

    import cv2
    import numpy as np

    for path in (raw_video, ros_events_path, metrics_path, run_identity_path):
        if not path.is_file():
            raise ValueError(f"required trajectory-review input is missing: {path}")
    events = _load_jsonl(ros_events_path)
    metrics = _load_jsonl(metrics_path)
    identity = json.loads(run_identity_path.read_text(encoding="utf-8"))
    dynamic_color_bgr = dynamic_obstacle_color_bgr(identity)
    dynamic_label = dynamic_obstacle_label(identity)
    video_identity = identity.get("video", {})
    frame_stride = int(video_identity.get("frame_stride", 0))
    capture = cv2.VideoCapture(str(raw_video))
    if not capture.isOpened():
        raise ValueError(f"cannot decode raw video: {raw_video}")
    frame_count = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
    height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if frame_count <= 0 or fps <= 0.0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError("raw video metadata is invalid")
    frame_rows = frame_metric_rows(metrics, frame_stride, frame_count)
    plans = associate_bspline_sim_times(events)
    occupancy_events = sorted(
        (
            {
                "effective_sim_time_seconds": float(event["stamp_ns"]) / 1.0e9,
                "points_xyz": event.get("points_xyz") or [],
                "point_count": int(event.get("point_count", 0)),
            }
            for event in events
            if event.get("kind") == "occupancy_inflate"
            and int(event.get("stamp_ns", 0)) > 0
        ),
        key=lambda value: value["effective_sim_time_seconds"],
    )
    forest = identity.get("forest_scene", {})
    navigation = forest.get("navigation") or {}
    course = identity.get("course") or {}
    if not navigation and isinstance(course, dict) and "office_start_xy_m" in course:
        navigation = {
            "start_world_m": course.get("office_start_xy_m"),
            "goal_world_m": course.get("office_goal_xy_m"),
        }

    office_routes = []
    if isinstance(course, dict) and course.get("name") == "office_l0_crowd":
        route_path_str = course.get("office_route_path")
        if route_path_str:
            route_path = Path(route_path_str)
            if not route_path.is_file():
                # Fallback to local repo path if on mac
                route_path = Path(__file__).resolve().parents[3] / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/office_l0_route_preflight07.json"
            if route_path.is_file():
                try:
                    from .office_crowd_contract import routes_from_preflight
                    pre_payload = json.loads(route_path.read_text(encoding="utf-8"))
                    office_routes = list(routes_from_preflight(pre_payload))
                except Exception:
                    pass

    bounds = _plot_bounds(plans, metrics, navigation)

    inset_width = min(430, max(300, width // 3))
    inset_height = min(330, max(230, height // 2))
    inset_left = width - inset_width - 24
    inset_top = 24
    mapper = lambda point: _world_to_inset(
        point, bounds, (inset_left, inset_top), (inset_width, inset_height)
    )

    output_video.parent.mkdir(parents=True, exist_ok=True)
    staging = output_video.with_name(output_video.stem + ".mp4v-staging.mp4")
    writer = cv2.VideoWriter(
        str(staging), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise ValueError(f"cannot create overlay staging video: {staging}")

    actual_path = []
    dynamic_path = []
    active_plan_index = -1
    active_occupancy_index = -1
    replan_banner_until_s = -1.0
    rendered = 0
    try:
        while rendered < frame_count:
            ok, frame = capture.read()
            if not ok:
                raise ValueError(
                    f"raw video ended at frame {rendered}, expected {frame_count}"
                )
            row = frame_rows[rendered]
            sim_time = float(row["sim_time_seconds"])
            previous_plan_index = active_plan_index
            while (
                active_plan_index + 1 < len(plans)
                and float(plans[active_plan_index + 1]["effective_sim_time_seconds"])
                <= sim_time
            ):
                active_plan_index += 1
            if active_plan_index != previous_plan_index and active_plan_index >= 0:
                replan_banner_until_s = sim_time + 0.8
            while (
                active_occupancy_index + 1 < len(occupancy_events)
                and float(
                    occupancy_events[active_occupancy_index + 1][
                        "effective_sim_time_seconds"
                    ]
                )
                <= sim_time
            ):
                active_occupancy_index += 1
            actual_path.append(tuple(float(value) for value in row["root_pos_w"][:2]))
            dynamic_position = row.get("dynamic_obstacle_actual_pos_w")
            if dynamic_position is not None:
                dynamic_path.append(
                    (float(dynamic_position[0]), float(dynamic_position[1]))
                )

            shaded = frame.copy()
            cv2.rectangle(
                shaded,
                (inset_left, inset_top),
                (inset_left + inset_width, inset_top + inset_height),
                (18, 22, 24),
                thickness=-1,
            )
            cv2.addWeighted(shaded, 0.78, frame, 0.22, 0.0, frame)
            cv2.rectangle(
                frame,
                (inset_left, inset_top),
                (inset_left + inset_width, inset_top + inset_height),
                (225, 225, 225),
                thickness=1,
            )

            primary_name = (navigation.get("primary_blocker") or {}).get("name")
            for proxy in forest.get("proxies", []):
                center = proxy.get("center_m", ())
                size = proxy.get("size_m", ())
                if len(center) < 2 or len(size) < 2:
                    continue
                color = (
                    PRIMARY_OBSTACLE_COLOR_BGR
                    if proxy.get("name") == primary_name
                    else OBSTACLE_COLOR_BGR
                )
                if proxy.get("shape") == "cylinder":
                    centre_px = mapper(center)
                    edge_px = mapper((float(center[0]) + 0.5 * float(size[0]), center[1]))
                    radius_px = max(2, abs(edge_px[0] - centre_px[0]))
                    cv2.circle(frame, centre_px, radius_px, color, thickness=2)
                else:
                    lower = mapper(
                        (float(center[0]) - 0.5 * float(size[0]), float(center[1]) - 0.5 * float(size[1]))
                    )
                    upper = mapper(
                        (float(center[0]) + 0.5 * float(size[0]), float(center[1]) + 0.5 * float(size[1]))
                    )
                    cv2.rectangle(frame, lower, upper, color, thickness=2)

            if active_plan_index >= 0:
                plan_pixels = _polyline(plans[active_plan_index]["sampled_points"], mapper)
                if len(plan_pixels) >= 2:
                    cv2.polylines(
                        frame,
                        [np.asarray(plan_pixels, dtype=np.int32)],
                        False,
                        PLAN_COLOR_BGR,
                        thickness=3,
                        lineType=cv2.LINE_AA,
                    )
            if active_occupancy_index >= 0:
                # These are sampled directly from SCAN's published inflated
                # occupancy, never from scene or pedestrian schedule truth.
                for point in occupancy_events[active_occupancy_index]["points_xyz"]:
                    if len(point) < 2:
                        continue
                    pixel = mapper(point)
                    if (
                        inset_left <= pixel[0] < inset_left + inset_width
                        and inset_top <= pixel[1] < inset_top + inset_height
                    ):
                        cv2.circle(
                            frame,
                            pixel,
                            1,
                            SCAN_OCCUPANCY_COLOR_BGR,
                            thickness=-1,
                        )
            actual_pixels = _polyline(actual_path, mapper)
            if len(actual_pixels) >= 2:
                cv2.polylines(
                    frame,
                    [np.asarray(actual_pixels, dtype=np.int32)],
                    False,
                    ACTUAL_COLOR_BGR,
                    thickness=3,
                    lineType=cv2.LINE_AA,
                )
            cv2.circle(frame, mapper(actual_path[-1]), 5, ACTUAL_COLOR_BGR, thickness=-1)
            if dynamic_path:
                dynamic_pixels = _polyline(dynamic_path, mapper)
                if len(dynamic_pixels) >= 2:
                    cv2.polylines(
                        frame,
                        [np.asarray(dynamic_pixels, dtype=np.int32)],
                        False,
                        dynamic_color_bgr,
                        thickness=2,
                        lineType=cv2.LINE_AA,
                    )
                dynamic_centre_px = mapper(dynamic_path[-1])
                dynamic_radius = float(
                    (identity.get("dynamic_obstacle") or {}).get("radius_m", 0.30)
                )
                dynamic_edge_px = mapper(
                    (dynamic_path[-1][0] + dynamic_radius, dynamic_path[-1][1])
                )
                dynamic_radius_px = max(
                    3, abs(dynamic_edge_px[0] - dynamic_centre_px[0])
                )
                cv2.circle(
                    frame,
                    dynamic_centre_px,
                    dynamic_radius_px,
                    dynamic_color_bgr,
                    thickness=3,
                )
                cv2.circle(
                    frame,
                    dynamic_centre_px,
                    4,
                    dynamic_color_bgr,
                    thickness=-1,
                )
            if office_routes:
                from .office_crowd_contract import office_pedestrian_state
                for r in office_routes:
                    p_state = office_pedestrian_state(sim_time, r)
                    p_xy = p_state["xy_m"]
                    p_px = mapper(p_xy)
                    is_crossing = r.name.startswith("crossing")
                    p_color = (0, 140, 255) if is_crossing else (230, 180, 50)
                    r_edge_px = mapper((p_xy[0] + r.radius_m, p_xy[1]))
                    r_px = max(3, abs(r_edge_px[0] - p_px[0]))
                    cv2.circle(frame, p_px, r_px, p_color, thickness=2)
                    cv2.circle(frame, p_px, 3, p_color, thickness=-1)

            goal = navigation.get("goal_world_m")
            if goal and len(goal) >= 2:
                cv2.drawMarker(
                    frame,
                    mapper(goal),
                    (220, 80, 230),
                    markerType=cv2.MARKER_STAR,
                    markerSize=18,
                    thickness=2,
                )

            legend_y = inset_top + 22
            cv2.putText(frame, "Top view (world XY)", (inset_left + 12, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1, cv2.LINE_AA)
            cv2.line(frame, (inset_left + 12, legend_y + 18), (inset_left + 40, legend_y + 18), PLAN_COLOR_BGR, 3, cv2.LINE_AA)
            cv2.putText(frame, "SCAN planned", (inset_left + 48, legend_y + 23), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (245, 245, 245), 1, cv2.LINE_AA)
            cv2.line(frame, (inset_left + 175, legend_y + 18), (inset_left + 203, legend_y + 18), ACTUAL_COLOR_BGR, 3, cv2.LINE_AA)
            cv2.putText(frame, "Isaac actual", (inset_left + 211, legend_y + 23), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (245, 245, 245), 1, cv2.LINE_AA)
            cv2.circle(
                frame,
                (inset_left + 18, legend_y + 43),
                3,
                SCAN_OCCUPANCY_COLOR_BGR,
                thickness=-1,
            )
            cv2.putText(
                frame,
                "SCAN inflated occupancy",
                (inset_left + 29, legend_y + 48),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (245, 245, 245),
                1,
                cv2.LINE_AA,
            )
            if office_routes:
                cv2.circle(
                    frame,
                    (inset_left + 18, legend_y + 67),
                    4,
                    (0, 140, 255),
                    thickness=2,
                )
                cv2.circle(
                    frame,
                    (inset_left + 32, legend_y + 67),
                    4,
                    (230, 180, 50),
                    thickness=2,
                )
                cv2.putText(
                    frame,
                    "GT pedestrian routes (evaluation only)",
                    (inset_left + 45, legend_y + 72),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.36,
                    (245, 245, 245),
                    1,
                    cv2.LINE_AA,
                )
            if dynamic_path:
                cv2.line(
                    frame,
                    (inset_left + 12, legend_y + 42),
                    (inset_left + 40, legend_y + 42),
                    dynamic_color_bgr,
                    3,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame,
                    dynamic_label,
                    (inset_left + 48, legend_y + 47),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.46,
                    (245, 245, 245),
                    1,
                    cv2.LINE_AA,
                )
            speed = math.hypot(float(row["root_lin_vel_w"][0]), float(row["root_lin_vel_w"][1]))
            command_vx = float(row["applied_command"][0])
            trajectory_id = "none" if active_plan_index < 0 else str(plans[active_plan_index]["trajectory_id"])
            cv2.putText(
                frame,
                f"t={sim_time:5.2f}s  cmd vx={command_vx:4.2f} m/s  speed={speed:4.2f} m/s  traj={trajectory_id}",
                (24, height - 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            if sim_time <= replan_banner_until_s and active_plan_index >= 0:
                cv2.putText(
                    frame,
                    f"NEW SCAN B-SPLINE  traj={trajectory_id}",
                    (24, 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    SCAN_OCCUPANCY_COLOR_BGR,
                    2,
                    cv2.LINE_AA,
                )
            if dynamic_path:
                phase = str(row.get("dynamic_obstacle_phase", "unknown"))
                clearance = float(
                    row.get("root_to_dynamic_surface_clearance_m", math.nan)
                )
                cv2.putText(
                    frame,
                    f"dynamic={phase}  synchronized clearance={clearance:4.2f} m",
                    (24, height - 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.60,
                    dynamic_color_bgr,
                    2,
                    cv2.LINE_AA,
                )
            writer.write(frame)
            rendered += 1
    finally:
        capture.release()
        writer.release()

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        staging.replace(output_video)
        encoder = "OpenCV mp4v fallback because ffmpeg is unavailable"
    else:
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(staging),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_video),
            ],
            check=True,
        )
        staging.unlink()
        encoder = "ffmpeg libx264 yuv420p"

    metadata = {
        "schema_version": 2 if identity.get("dynamic_obstacle") else 1,
        "mapping": {
            "plan_to_sim_time": "bracketed interpolation on simulator-stamped body_pose receipts",
            "frame_to_sim_time": "metrics rows where step modulo video frame_stride equals zero",
            "frame_stride": frame_stride,
            "maximum_plan_pose_alignment_error_ms": max(
                float(plan["receipt_alignment_error_ms"]) for plan in plans
            ),
        },
        "input_sha256": {
            "raw_video": _sha256(raw_video),
            "ros_events": _sha256(ros_events_path),
            "metrics": _sha256(metrics_path),
            "run_identity": _sha256(run_identity_path),
        },
        "output": {
            "path": output_video.name,
            "sha256": _sha256(output_video),
            "bytes": output_video.stat().st_size,
            "frame_count": rendered,
            "fps": fps,
            "resolution": [width, height],
            "encoder": encoder,
        },
        "trajectory_ids": [int(plan["trajectory_id"]) for plan in plans],
        "trajectory_count": len(plans),
        "plans": [
            {
                "trajectory_id": int(plan["trajectory_id"]),
                "effective_sim_time_seconds": float(
                    plan["effective_sim_time_seconds"]
                ),
                "receipt_alignment_error_ms": float(
                    plan["receipt_alignment_error_ms"]
                ),
            }
            for plan in plans
        ],
        "sample_count_per_trajectory": len(plans[0]["sampled_points"]),
        "plot_bounds_world_xy_m": list(bounds),
        "dynamic_obstacle": {
            "rendered": bool(dynamic_path),
            "label": dynamic_label,
            "record_count": sum(
                row.get("dynamic_obstacle_actual_pos_w") is not None
                for row in metrics
            ),
            "identity": identity.get("dynamic_obstacle"),
            "path_source": "dynamic_obstacle_actual_pos_w PhysX readback",
        },
        "colours_bgr": {
            "scan_planned": list(PLAN_COLOR_BGR),
            "isaac_actual": list(ACTUAL_COLOR_BGR),
            "primary_obstacle": list(PRIMARY_OBSTACLE_COLOR_BGR),
            "dynamic_obstacle_actual": list(dynamic_color_bgr),
        },
        "claim_boundary": (
            "Derived human-review overlay from the hashed raw SCAN Bspline, "
            "Isaac PhysX metrics, run identity, and untouched raw simulator MP4."
        ),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-video", type=Path, required=True)
    parser.add_argument("--ros-events", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--run-identity", type=Path, required=True)
    parser.add_argument("--output-video", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    metadata = render_trajectory_review(
        args.raw_video,
        args.ros_events,
        args.metrics,
        args.run_identity,
        args.output_video,
        args.metadata,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(args.output_video),
                "sha256": metadata["output"]["sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
