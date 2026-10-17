"""Capture actual RTX sweeps at the existing mounted sensor pose.

The original Warp sensor supplies only its measured attachment transform.
Its hit points are never used as a published navigation cloud in this adapter.
"""
from __future__ import annotations

import time
import numpy as np
from scipy.spatial import cKDTree


def capture_sweep(sim, pose_sensor, rtx_sensor, scan_index, torch):
    from .isaac_adapter_core import mounted_sensor_pose, rotation_matrix_from_wxyz

    started = time.monotonic()
    pose_sensor.update(dt=0.0, force_recompute=True)
    position, quaternion = mounted_sensor_pose(
        pose_sensor.data.pos_w[0].detach().cpu().tolist(),
        pose_sensor.data.quat_w[0].detach().cpu().tolist(),
        pose_sensor.cfg.offset.pos, pose_sensor.cfg.offset.rot)
    rtx_sensor.sensor.set_world_pose(position=np.asarray(position), orientation=np.asarray(quaternion))
    directions = rtx_sensor.set_window(scan_index)
    tree = cKDTree(directions)
    points = np.empty((0, 3), dtype=np.float32)
    error = None
    for attempt in range(3):
        # Rendering does not advance physics. A retry may finish an asynchronous
        # render, but it must still match this scan's rays at this same pose.
        sim.render()
        points, metadata = rtx_sensor.points()
        if len(points):
            unit = points / np.linalg.norm(points, axis=1)[:, None]
            error = float(tree.query(unit)[0].max())
            if error <= 0.0001:
                break
    if len(points) and (error is None or error > 0.0001):
        raise RuntimeError("RTX returned an old or incompatible scan window")
    if not len(points) and sim.current_time > 1.0:
        raise RuntimeError("RTX has no current Building returns after startup")
    measured_position, measured_quaternion = rtx_sensor.sensor.get_world_pose()
    pose_error = float(np.max(np.abs(np.asarray(measured_position) - position)))
    quaternion_error = min(float(np.max(np.abs(np.asarray(measured_quaternion) - quaternion))),
                           float(np.max(np.abs(np.asarray(measured_quaternion) + quaternion))))
    if pose_error > 0.0001 or quaternion_error > 0.0001:
        raise RuntimeError("RTX mounted world pose differs from the paired sensor pose")
    world = points @ np.asarray(rotation_matrix_from_wxyz(quaternion)).T + np.asarray(position)
    hits = np.full((rtx_sensor.pattern.points_per_scan, 3), np.inf, dtype=np.float32)
    if len(world) > len(hits):
        raise RuntimeError("RTX returned more than one declared sweep")
    hits[:len(world)] = world
    info = {"backend": "RTX_pinned_livox_csv_geometric_snapshot", "ready": bool(len(points)),
            "scan_window": rtx_sensor.window.as_dict(), "point_count": len(points),
            "max_direction_vector_error": error, "mount_position_error_m": pose_error,
            "mount_quaternion_error": quaternion_error, "render_attempts": attempt + 1,
            "wall_seconds": time.monotonic() - started,
            "self_return_filter": "none; all actual in-range returns retained"}
    return torch.as_tensor(hits, device=pose_sensor.device), list(position), list(quaternion), info
