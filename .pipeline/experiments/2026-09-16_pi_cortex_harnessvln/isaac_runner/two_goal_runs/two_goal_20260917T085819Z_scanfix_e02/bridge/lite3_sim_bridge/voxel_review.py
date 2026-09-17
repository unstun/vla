"""Decode native SCAN voxel messages and render traceable review video."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Mapping, Sequence

import numpy as np


RAW_VOXEL_COLOR_BGR = (210, 225, 235)
INFLATED_VOXEL_COLOR_BGR = (50, 80, 245)
LIVE_CLOUD_COLOR_BGR = (255, 190, 40)
PLAN_COLOR_BGR = (80, 220, 80)
ACTUAL_COLOR_BGR = (255, 220, 40)
GOAL_COLOR_BGR = (210, 80, 230)
BOUND_COLOR_BGR = (230, 180, 60)
RAW_DISPLAY_POINT_LIMIT = 50_000
INFLATED_DISPLAY_POINT_LIMIT = 30_000
LIVE_DISPLAY_POINT_LIMIT = 18_000


def _stamp_ns(message) -> int:
    return int(message.header.stamp.sec) * 1_000_000_000 + int(
        message.header.stamp.nanosec
    )


def pointcloud2_xyz(message) -> np.ndarray:
    """Decode finite XYZ values using the PointCloud2 field/stride contract."""

    width = int(message.width)
    height = int(message.height)
    point_step = int(message.point_step)
    row_step = int(message.row_step)
    if width < 0 or height < 0 or point_step <= 0 or row_step < width * point_step:
        raise ValueError("PointCloud2 dimensions or strides are invalid")
    if width == 0 or height == 0:
        return np.empty((0, 3), dtype=np.float32)
    payload = memoryview(message.data)
    required_size = row_step * height
    if len(payload) < required_size:
        raise ValueError("PointCloud2 payload is shorter than its declared shape")

    field_by_name = {str(field.name): field for field in message.fields}
    missing = sorted({"x", "y", "z"} - set(field_by_name))
    if missing:
        raise ValueError(f"PointCloud2 lacks XYZ fields: {', '.join(missing)}")
    endian = ">" if bool(message.is_bigendian) else "<"
    formats = []
    offsets = []
    for name in ("x", "y", "z"):
        field = field_by_name[name]
        if int(field.count) != 1 or int(field.datatype) not in (7, 8):
            raise ValueError("PointCloud2 XYZ fields must be scalar float32/float64")
        formats.append(endian + ("f4" if int(field.datatype) == 7 else "f8"))
        offset = int(field.offset)
        width_bytes = 4 if int(field.datatype) == 7 else 8
        if offset < 0 or offset + width_bytes > point_step:
            raise ValueError("PointCloud2 XYZ field offset exceeds point_step")
        offsets.append(offset)
    dtype = np.dtype(
        {
            "names": ("x", "y", "z"),
            "formats": tuple(formats),
            "offsets": tuple(offsets),
            "itemsize": point_step,
        }
    )
    rows = []
    for row_index in range(height):
        start = row_index * row_step
        row = np.frombuffer(payload[start : start + width * point_step], dtype=dtype)
        rows.append(np.column_stack((row["x"], row["y"], row["z"])))
    points = np.concatenate(rows, axis=0).astype(np.float32, copy=False)
    return points[np.isfinite(points).all(axis=1)]


def transform_sensor_points(
    points: np.ndarray, position: np.ndarray, quaternion_xyzw: np.ndarray
) -> np.ndarray:
    """Transform an XYZ sensor-frame cloud into the shared world frame."""

    points = np.asarray(points, dtype=np.float32)
    position = np.asarray(position, dtype=np.float64)
    quaternion = np.asarray(quaternion_xyzw, dtype=np.float64)
    if points.ndim != 2 or points.shape[1:] != (3,):
        raise ValueError("sensor points must be finite Nx3 values")
    if position.shape != (3,) or quaternion.shape != (4,):
        raise ValueError("sensor pose must contain XYZ and XYZW values")
    if not np.isfinite(points).all() or not np.isfinite(position).all() or not np.isfinite(quaternion).all():
        raise ValueError("sensor cloud transform inputs must be finite")
    norm = float(np.linalg.norm(quaternion))
    if norm <= 1.0e-9:
        raise ValueError("sensor quaternion norm must be positive")
    x, y, z, w = quaternion / norm
    rotation = np.asarray(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
    return (points.astype(np.float64) @ rotation.T + position).astype(np.float32)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Mapping[str, object]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows:
        raise ValueError(f"voxel metadata is empty: {path}")
    return rows


def _plan_bounds(
    bbox_points: np.ndarray, raw_points: np.ndarray, body_position: np.ndarray
) -> tuple[float, float, float, float, float, float]:
    source = bbox_points if len(bbox_points) >= 2 else raw_points
    if len(source) == 0:
        raise ValueError("voxel frame has no points from which to derive bounds")
    minimum = np.min(source, axis=0).astype(float)
    maximum = np.max(source, axis=0).astype(float)
    if maximum[0] - minimum[0] < 1.0 or maximum[1] - minimum[1] < 1.0:
        minimum[:2] = body_position[:2] - 1.0
        maximum[:2] = body_position[:2] + 1.0
    if maximum[2] - minimum[2] < 0.5:
        minimum[2] -= 0.25
        maximum[2] += 0.25
    return (*minimum, *maximum)


def _top_pixels(
    points: np.ndarray,
    bounds: Sequence[float],
    rect: tuple[int, int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    left, top, width, height = rect
    min_x, min_y, _, max_x, max_y, _ = bounds
    x = (points[:, 0] - min_x) / max(max_x - min_x, 1.0e-9)
    y = (points[:, 1] - min_y) / max(max_y - min_y, 1.0e-9)
    return (
        left + np.rint(x * (width - 1)).astype(np.int32),
        top + height - 1 - np.rint(y * (height - 1)).astype(np.int32),
    )


def _oblique_coordinates(points: np.ndarray) -> np.ndarray:
    return np.column_stack(
        (
            points[:, 0] - 0.62 * points[:, 1],
            0.32 * points[:, 0] + 0.32 * points[:, 1] + 1.35 * points[:, 2],
        )
    )


def _oblique_pixels(
    points: np.ndarray,
    bounds: Sequence[float],
    rect: tuple[int, int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    corners = np.asarray(
        [
            (x, y, z)
            for x in (min_x, max_x)
            for y in (min_y, max_y)
            for z in (min_z, max_z)
        ],
        dtype=np.float32,
    )
    projected = _oblique_coordinates(points)
    projected_bounds = _oblique_coordinates(corners)
    minimum = np.min(projected_bounds, axis=0)
    maximum = np.max(projected_bounds, axis=0)
    fraction = (projected - minimum) / np.maximum(maximum - minimum, 1.0e-9)
    left, top, width, height = rect
    return (
        left + np.rint(fraction[:, 0] * (width - 1)).astype(np.int32),
        top + height - 1 - np.rint(fraction[:, 1] * (height - 1)).astype(np.int32),
    )


def _point_mask(frame, pixels, rect, radius: int):
    import cv2

    left, top, width, height = rect
    x, y = pixels
    valid = (x >= left) & (x < left + width) & (y >= top) & (y < top + height)
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    mask[y[valid], x[valid]] = 255
    if radius > 0:
        kernel_size = 2 * radius + 1
        mask = cv2.dilate(mask, np.ones((kernel_size, kernel_size), dtype=np.uint8))
    return mask


def _paint_points(frame, pixels, rect, color, radius: int, alpha: float = 1.0) -> None:
    mask = _point_mask(frame, pixels, rect, radius)
    selected = mask > 0
    if alpha >= 1.0:
        frame[selected] = color
        return
    if alpha <= 0.0:
        return
    source = frame[selected].astype(np.float32)
    target = np.asarray(color, dtype=np.float32)
    frame[selected] = np.rint((1.0 - alpha) * source + alpha * target).astype(
        np.uint8
    )


def _paint_outline(frame, pixels, rect, color, radius: int, thickness: int) -> None:
    import cv2

    mask = _point_mask(frame, pixels, rect, radius)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(frame, contours, -1, color, thickness, cv2.LINE_AA)


def _draw_polyline(frame, points: np.ndarray, mapper, color, thickness=2) -> None:
    import cv2

    if len(points) < 2:
        return
    x, y = mapper(points)
    pixels = np.column_stack((x, y)).astype(np.int32)
    cv2.polylines(frame, [pixels], False, color, thickness, cv2.LINE_AA)


def _rgb(color_bgr: Sequence[int]) -> tuple[float, float, float]:
    return tuple(float(value) / 255.0 for value in reversed(color_bgr))


def _display_sample(points: np.ndarray, limit: int) -> np.ndarray:
    """Deterministically cap display load without changing captured evidence."""

    if limit <= 0:
        raise ValueError("display point limit must be positive")
    if len(points) <= limit:
        return points
    indices = np.linspace(0, len(points) - 1, limit, dtype=np.int64)
    return points[indices]


def _draw_bbox_3d(axis, bounds: Sequence[float]) -> None:
    min_x, min_y, min_z, max_x, max_y, max_z = bounds
    corners = {
        (x_index, y_index, z_index): (
            (min_x, max_x)[x_index],
            (min_y, max_y)[y_index],
            (min_z, max_z)[z_index],
        )
        for x_index in (0, 1)
        for y_index in (0, 1)
        for z_index in (0, 1)
    }
    for start_index, start in corners.items():
        for dimension in range(3):
            end_index = list(start_index)
            end_index[dimension] = 1 - end_index[dimension]
            end_index = tuple(end_index)
            if start_index[dimension] != 0:
                continue
            end = corners[end_index]
            axis.plot(
                (start[0], end[0]),
                (start[1], end[1]),
                (start[2], end[2]),
                color=(0.38, 0.43, 0.48),
                linewidth=0.6,
                alpha=0.65,
            )


def render_voxel_review(
    snapshot_dir: Path,
    metadata_path: Path,
    summary_path: Path,
    run_identity_path: Path,
    output_path: Path,
    sidecar_path: Path,
    *,
    fps: float = 10.0,
    frame_size: tuple[int, int] = (1280, 720),
) -> Mapping[str, object]:
    """Render native SCAN XYZ voxels in a true three-axis perspective view."""

    import cv2

    if not math.isfinite(fps) or fps <= 0.0:
        raise ValueError("voxel video fps must be positive and finite")
    records = _load_jsonl(metadata_path)
    summary = _load_json(summary_path)
    if summary.get("status") != "PASS":
        raise ValueError("voxel capture summary did not pass")
    identity = _load_json(run_identity_path)
    navigation = (identity.get("forest_scene") or {}).get("navigation") or {}
    goal = navigation.get("goal_world_m")
    goal_point = (
        np.asarray(goal[:3], dtype=np.float32)
        if isinstance(goal, list) and len(goal) >= 3
        else None
    )

    width, height = frame_size
    if width < 640 or height < 360:
        raise ValueError("voxel video frame size is too small")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or sidecar_path.exists():
        raise FileExistsError("voxel review output already exists")
    source_stamps = [int(record["body_stamp_ns"]) for record in records]
    if any(left >= right for left, right in zip(source_stamps, source_stamps[1:])):
        raise ValueError("voxel snapshot simulator stamps must increase strictly")
    source_duration_seconds = (source_stamps[-1] - source_stamps[0]) / 1.0e9
    output_frame_count = max(1, int(math.floor(source_duration_seconds * fps)) + 1)
    target_stamps = [
        source_stamps[0] + int(round(index * 1.0e9 / fps))
        for index in range(output_frame_count)
    ]
    source_indices = [
        max(0, bisect.bisect_right(source_stamps, stamp) - 1)
        for stamp in target_stamps
    ]
    snapshot_digest = hashlib.sha256()
    for record in records:
        snapshot_path = snapshot_dir / str(record["snapshot_file"])
        if not snapshot_path.is_file():
            raise FileNotFoundError(f"voxel snapshot is missing: {snapshot_path}")
        snapshot_digest.update(snapshot_path.name.encode("utf-8"))
        snapshot_digest.update(bytes.fromhex(_sha256(snapshot_path)))

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required for native SCAN voxel review encoding")
    encoder = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner", "-loglevel", "error", "-n",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{width}x{height}", "-pix_fmt", "bgr24",
            "-r", str(float(fps)), "-i", "-", "-an",
            "-c:v", "libx264", "-profile:v", "high",
            "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
            "-color_range", "tv", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-colorspace", "bt709",
            "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
            "-movflags", "+faststart", str(output_path),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    background_rgb = (24 / 255.0, 29 / 255.0, 34 / 255.0)
    figure = Figure(
        figsize=(width / 100.0, height / 100.0),
        dpi=100,
        facecolor=background_rgb,
    )
    canvas = FigureCanvasAgg(figure)
    axis = figure.add_axes((0.035, 0.14, 0.69, 0.72), projection="3d")
    inset = figure.add_axes((0.75, 0.53, 0.23, 0.31), facecolor=background_rgb)
    header = figure.text(
        0.025,
        0.965,
        "Native SCAN XYZ voxel map",
        color=(0.94, 0.96, 0.98),
        fontsize=15,
        fontweight="bold",
        va="top",
    )
    figure.text(
        0.025,
        0.915,
        "Live LiDAR + complete SCAN local fused occupancy (not global SLAM) + inflated collision voxels | XYZ scale 1:1",
        color=(0.75, 0.80, 0.84),
        fontsize=8.5,
        va="top",
    )
    status_text = figure.text(
        0.025,
        0.095,
        "",
        color=(0.92, 0.94, 0.96),
        fontsize=8.5,
        va="top",
    )
    legend_handles = (
        Line2D(
            [0],
            [0],
            marker=".",
            linestyle="",
            color=_rgb(LIVE_CLOUD_COLOR_BGR),
            label="live LiDAR scan",
            markersize=5,
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="",
            color=_rgb(RAW_VOXEL_COLOR_BGR),
            label="complete local fused occupancy",
            markersize=6,
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="",
            color=_rgb(INFLATED_VOXEL_COLOR_BGR),
            label="inflated collision voxels",
            markersize=6,
            alpha=0.65,
        ),
        Line2D([0], [0], color=_rgb(PLAN_COLOR_BGR), label="SCAN B-spline", lw=2.5),
        Line2D([0], [0], color=_rgb(ACTUAL_COLOR_BGR), label="Lite3 actual", lw=2.5),
        Line2D(
            [0],
            [0],
            marker="x",
            linestyle="",
            color=_rgb(GOAL_COLOR_BGR),
            label="goal",
            markersize=7,
        ),
    )
    figure.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.012),
        ncol=6,
        frameon=False,
        labelcolor=(0.88, 0.90, 0.92),
        fontsize=7.5,
    )
    body_trace = np.asarray(
        [record["body_position"] for record in records], dtype=np.float32
    )
    first_stamp_ns = int(records[0]["body_stamp_ns"])
    trajectory_ids = set()
    cached_source_index = None
    cached_snapshot = None
    try:
        for frame_index, source_index in enumerate(source_indices):
            record = records[source_index]
            snapshot_path = snapshot_dir / str(record["snapshot_file"])
            if source_index != cached_source_index:
                with np.load(snapshot_path, allow_pickle=False) as snapshot:
                    cached_snapshot = {
                        "live": np.asarray(
                            snapshot["live_points"]
                            if "live_points" in snapshot
                            else np.empty((0, 3), dtype=np.float32),
                            dtype=np.float32,
                        ),
                        "raw": np.asarray(snapshot["raw_points"], dtype=np.float32),
                        "inflated": np.asarray(
                            snapshot["inflated_points"], dtype=np.float32
                        ),
                        "body": np.asarray(snapshot["body_position"], dtype=np.float32),
                        "bbox": np.asarray(snapshot["bbox_points"], dtype=np.float32),
                        "plan": np.asarray(snapshot["plan_points"], dtype=np.float32),
                        "yaw": float(snapshot["body_yaw_rad"]),
                        "trajectory_id": int(snapshot["trajectory_id"]),
                    }
                cached_source_index = source_index
            live = cached_snapshot["live"]
            raw = cached_snapshot["raw"]
            inflated = cached_snapshot["inflated"]
            body = cached_snapshot["body"]
            bbox = cached_snapshot["bbox"]
            plan = cached_snapshot["plan"]
            yaw = cached_snapshot["yaw"]
            trajectory_id = cached_snapshot["trajectory_id"]
            if raw.ndim != 2 or raw.shape[1:] != (3,) or len(raw) == 0:
                raise ValueError("raw voxel snapshot is empty or malformed")
            if live.ndim != 2 or live.shape[1:] != (3,):
                raise ValueError("live sensor cloud snapshot is malformed")
            if inflated.ndim != 2 or inflated.shape[1:] != (3,) or len(inflated) == 0:
                raise ValueError("inflated voxel snapshot is empty or malformed")
            if plan.ndim != 2 or plan.shape[1:] != (3,):
                raise ValueError("B-spline snapshot is malformed")
            if int(record["raw_point_count"]) != len(raw) or int(
                record["inflated_point_count"]
            ) != len(inflated):
                raise ValueError("voxel metadata point counts do not match snapshot")
            if "live_point_count" in record and int(record["live_point_count"]) != len(live):
                raise ValueError("live cloud metadata point count does not match snapshot")
            if len(live) > LIVE_DISPLAY_POINT_LIMIT:
                raise ValueError("live cloud exceeds the complete-display point limit")
            if len(raw) > RAW_DISPLAY_POINT_LIMIT:
                raise ValueError("local fused occupancy exceeds the complete-display point limit")
            if trajectory_id >= 0:
                trajectory_ids.add(trajectory_id)
            bounds = _plan_bounds(bbox, raw, body)
            elapsed = (target_stamps[frame_index] - first_stamp_ns) / 1.0e9
            min_x, min_y, min_z, max_x, max_y, max_z = bounds
            live_display = _display_sample(live, LIVE_DISPLAY_POINT_LIMIT)
            raw_display = _display_sample(raw, RAW_DISPLAY_POINT_LIMIT)
            inflated_display = _display_sample(
                inflated, INFLATED_DISPLAY_POINT_LIMIT
            )
            trace = body_trace[: source_index + 1]

            axis.clear()
            axis.computed_zorder = False
            axis.set_facecolor(background_rgb)
            axis.set_proj_type("persp", focal_length=0.9)
            axis.view_init(elev=30.0, azim=-62.0)
            axis.scatter(
                inflated_display[:, 0],
                inflated_display[:, 1],
                inflated_display[:, 2],
                marker="s",
                s=0.7,
                c=[_rgb(INFLATED_VOXEL_COLOR_BGR)],
                alpha=0.08,
                linewidths=0.0,
                depthshade=False,
                zorder=1,
            )
            if len(live_display):
                axis.scatter(
                    live_display[:, 0],
                    live_display[:, 1],
                    live_display[:, 2],
                    marker=".",
                    s=2.2,
                    c=[_rgb(LIVE_CLOUD_COLOR_BGR)],
                    alpha=0.75,
                    linewidths=0.0,
                    depthshade=True,
                    zorder=3,
                )
            axis.scatter(
                raw_display[:, 0],
                raw_display[:, 1],
                raw_display[:, 2],
                marker="s",
                s=2.5,
                c=[_rgb(RAW_VOXEL_COLOR_BGR)],
                alpha=0.94,
                linewidths=0.0,
                depthshade=True,
                zorder=4,
            )
            if len(plan) >= 2:
                axis.plot(
                    plan[:, 0],
                    plan[:, 1],
                    plan[:, 2],
                    color=_rgb(PLAN_COLOR_BGR),
                    linewidth=3.0,
                    zorder=6,
                )
            if len(trace) >= 2:
                axis.plot(
                    trace[:, 0],
                    trace[:, 1],
                    trace[:, 2],
                    color=_rgb(ACTUAL_COLOR_BGR),
                    linewidth=2.3,
                    zorder=7,
                )
            axis.scatter(
                [body[0]],
                [body[1]],
                [body[2]],
                s=48,
                c=[_rgb(ACTUAL_COLOR_BGR)],
                edgecolors="white",
                linewidths=0.6,
                depthshade=False,
                zorder=8,
            )
            axis.quiver(
                body[0],
                body[1],
                body[2],
                math.cos(yaw),
                math.sin(yaw),
                0.0,
                length=0.55,
                normalize=True,
                color=_rgb(ACTUAL_COLOR_BGR),
                linewidth=1.8,
                arrow_length_ratio=0.3,
                zorder=8,
            )
            if goal_point is not None:
                axis.scatter(
                    [goal_point[0]],
                    [goal_point[1]],
                    [goal_point[2]],
                    marker="x",
                    s=85,
                    c=[_rgb(GOAL_COLOR_BGR)],
                    linewidths=2.5,
                    depthshade=False,
                    zorder=8,
                )
            _draw_bbox_3d(axis, bounds)
            axis.set_xlim(min_x, max_x)
            axis.set_ylim(min_y, max_y)
            axis.set_zlim(min_z, max_z)
            axis.set_box_aspect(
                (
                    max(max_x - min_x, 1.0e-3),
                    max(max_y - min_y, 1.0e-3),
                    max(max_z - min_z, 1.0e-3),
                )
            )
            axis.set_xlabel("X world (m)", color=(0.82, 0.85, 0.88), fontsize=8)
            axis.set_ylabel("Y world (m)", color=(0.82, 0.85, 0.88), fontsize=8)
            axis.set_zlabel("Z world (m)", color=(0.82, 0.85, 0.88), fontsize=8)
            axis.tick_params(colors=(0.72, 0.76, 0.80), labelsize=6, pad=0)
            axis.grid(True, color=(0.35, 0.39, 0.43), alpha=0.45)
            axis.set_title(
                "RViz-style fixed 3D frame — live scan / fused map / collision inflation",
                color=(0.88, 0.91, 0.94),
                fontsize=10,
                pad=4,
            )

            inset.clear()
            inset.set_facecolor(background_rgb)
            inset.scatter(
                inflated_display[:, 0],
                inflated_display[:, 1],
                marker="s",
                s=0.35,
                c=[_rgb(INFLATED_VOXEL_COLOR_BGR)],
                alpha=0.18,
                linewidths=0.0,
            )
            if len(live_display):
                inset.scatter(
                    live_display[:, 0],
                    live_display[:, 1],
                    marker=".",
                    s=0.5,
                    c=[_rgb(LIVE_CLOUD_COLOR_BGR)],
                    alpha=0.65,
                    linewidths=0.0,
                )
            inset.scatter(
                raw_display[:, 0],
                raw_display[:, 1],
                marker="s",
                s=1.0,
                c=[_rgb(RAW_VOXEL_COLOR_BGR)],
                alpha=0.9,
                linewidths=0.0,
            )
            if len(plan) >= 2:
                inset.plot(
                    plan[:, 0],
                    plan[:, 1],
                    color=_rgb(PLAN_COLOR_BGR),
                    linewidth=1.8,
                )
            if len(trace) >= 2:
                inset.plot(
                    trace[:, 0],
                    trace[:, 1],
                    color=_rgb(ACTUAL_COLOR_BGR),
                    linewidth=1.5,
                )
            inset.scatter(
                [body[0]], [body[1]], s=18, c=[_rgb(ACTUAL_COLOR_BGR)], zorder=5
            )
            if goal_point is not None:
                inset.scatter(
                    [goal_point[0]],
                    [goal_point[1]],
                    marker="x",
                    s=28,
                    c=[_rgb(GOAL_COLOR_BGR)],
                    linewidths=1.5,
                )
            inset.set_xlim(min_x, max_x)
            inset.set_ylim(min_y, max_y)
            inset.set_aspect("equal", adjustable="box")
            inset.set_xticks([])
            inset.set_yticks([])
            inset.set_title(
                "XY planning inset",
                color=(0.86, 0.89, 0.92),
                fontsize=8,
                pad=3,
            )
            for spine in inset.spines.values():
                spine.set_edgecolor((0.35, 0.40, 0.45))

            header.set_text("Native SCAN 3D navigation view")
            status_text.set_text(
                f"t={elapsed:5.2f}s | live scan(all)={len(live)} | local fused(all)={len(raw)} | "
                f"inflated={len(inflated)} | "
                f"SCAN trajectory={trajectory_id if trajectory_id >= 0 else 'pending'}"
            )
            canvas.draw()
            rgba = np.asarray(canvas.buffer_rgba())
            frame = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
            if frame.shape[:2] != (height, width):
                raise RuntimeError("matplotlib rendered an unexpected voxel frame size")
            if encoder.stdin is None:
                raise RuntimeError("native SCAN voxel encoder stdin is unavailable")
            encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
    finally:
        if encoder.stdin is not None and not encoder.stdin.closed:
            encoder.stdin.close()
        stderr = (
            encoder.stderr.read().decode("utf-8", "replace")
            if encoder.stderr is not None
            else ""
        )
        return_code = encoder.wait()
    if return_code != 0:
        raise RuntimeError(
            f"native SCAN voxel encoder exited {return_code}: {stderr.strip()}"
        )
    metadata = {
        "schema_version": 3,
        "claim_boundary": (
            "true XYZ visualization of live LiDAR and native SCAN occupancy topics; "
            "deterministic display subsampling only; no scene-truth voxels"
        ),
        "render_geometry": {
            "spatial_dimensions": ["x", "y", "z"],
            "dimension_count": 3,
            "projection": "matplotlib_mplot3d_perspective",
            "camera": "sliding-map-following fixed RViz-style isometric view",
            "vertical_scale": 1.0,
            "raw_display_point_limit": RAW_DISPLAY_POINT_LIMIT,
            "inflated_display_point_limit": INFLATED_DISPLAY_POINT_LIMIT,
            "live_display_point_limit": LIVE_DISPLAY_POINT_LIMIT,
            "display_sampling": "live and raw local layers complete; deterministic inflation subsampling only",
            "xy_inset_role": "auxiliary planning correlation only",
        },
        "sources": {
            "topics": [
                "/grid_map/occupancy",
                "/grid_map/occupancy_inflate",
                "/quad_0/cloud_raw",
                "/quad_0/lidar_pose",
                "/grid_map/sliding_map_bbox",
                "/quad_0/body_pose",
                "/planning/bspline",
            ],
            "capture_metadata_sha256": _sha256(metadata_path),
            "capture_summary_sha256": _sha256(summary_path),
            "run_identity_sha256": _sha256(run_identity_path),
            "snapshot_aggregate_sha256": snapshot_digest.hexdigest(),
        },
        "output": {
            "path": str(output_path),
            "sha256": _sha256(output_path),
            "codec": "h264_high_crf16_bt709_direct",
            "frame_count": output_frame_count,
            "source_snapshot_count": len(records),
            "fps": fps,
            "duration_seconds": output_frame_count / fps,
            "source_simulator_duration_seconds": source_duration_seconds,
            "width": width,
            "height": height,
        },
        "trajectory_ids": sorted(trajectory_ids),
        "raw_point_count": {
            "minimum": min(int(row["raw_point_count"]) for row in records),
            "maximum": max(int(row["raw_point_count"]) for row in records),
        },
        "inflated_point_count": {
            "minimum": min(int(row["inflated_point_count"]) for row in records),
            "maximum": max(int(row["inflated_point_count"]) for row in records),
        },
        "live_point_count": {
            "minimum": min(int(row.get("live_point_count", 0)) for row in records),
            "maximum": max(int(row.get("live_point_count", 0)) for row in records),
        },
    }
    sidecar_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--run-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)
    metadata = render_voxel_review(
        args.snapshot_dir,
        args.metadata,
        args.summary,
        args.run_identity,
        args.output,
        args.sidecar,
        fps=args.fps,
        frame_size=(args.width, args.height),
    )
    print(json.dumps({"status": "PASS", "output": metadata["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
