"""Pinned static geometry selects tracking candidates from current LiDAR only."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Tuple

import numpy as np
from scipy.spatial import cKDTree

from moving_cluster_core import CloudFrame, PoseObservation, TrackerParameters, rotate_by_quaternion

BUILDING_PCD_SHA256 = "8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae"
STATIC_MATCH_DISTANCE_M = 0.10
MINIMUM_BACKGROUND_MATCH_FRACTION = 0.80


@dataclass(frozen=True)
class ForegroundSelection:
    cloud: CloudFrame
    world_points: Tuple[Tuple[float, float, float], ...]
    matched_fraction: float
    input_points: int
    in_range_points: int
    background_source_id: str


class StaticBackgroundIndex:
    """An immutable known-map index. Runtime construction uses the pinned loader."""

    def __init__(self, points, source_id: str, frame: str = "world"):
        array = np.asarray(points, dtype=np.float64)
        if array.ndim != 2 or array.shape[1] != 3 or not len(array) or \
           not np.isfinite(array).all() or not source_id or frame != "world":
            raise ValueError("invalid static background geometry or provenance")
        self.frame = frame
        self.source_id = source_id
        self._tree = cKDTree(np.ascontiguousarray(array), copy_data=True)

    def select(self, cloud: CloudFrame, pose: PoseObservation,
               parameters: TrackerParameters) -> ForegroundSelection:
        if not cloud.complete or cloud.frame != pose.sensor_frame or pose.world_frame != self.frame or \
           cloud.stamp_ns != pose.stamp_ns or cloud.stamp_ns <= 0 or \
           len(cloud.points) == 0 or len(cloud.points) > parameters.max_points:
            raise ValueError("invalid current cloud/frame/pose pairing")
        points = np.asarray(cloud.points, dtype=np.float32)
        position = np.asarray(pose.position, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3 or position.shape != (3,) or \
           not np.isfinite(points).all() or not np.isfinite(position).all() or \
           not np.isfinite(parameters.max_range_m) or parameters.max_range_m <= 0:
            raise ValueError("invalid cloud geometry or measured position")
        in_range = points[np.linalg.norm(points, axis=1) <= parameters.max_range_m]
        if not len(in_range):
            raise ValueError("no measured coverage in the tracker range")
        rotation = np.array([rotate_by_quaternion(axis, pose.quaternion_xyzw)
                             for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]).T
        world = in_range @ rotation.T + position
        distance, _ = self._tree.query(world, k=1)
        foreground = distance > STATIC_MATCH_DISTANCE_M
        return ForegroundSelection(
            CloudFrame(cloud.stamp_ns, cloud.frame,
                       tuple(tuple(p) for p in in_range[foreground].tolist()), True),
            tuple(tuple(p) for p in world[foreground].tolist()),
            float(np.mean(~foreground)), len(points), len(in_range), self.source_id,
        )


def load_building_background(path: Path) -> StaticBackgroundIndex:
    """Load only the published raw-frame Building asset; never fit a transform."""
    raw = Path(path).read_bytes()
    if len(raw) != 48_000_221 or hashlib.sha256(raw).hexdigest() != BUILDING_PCD_SHA256:
        raise ValueError("static Building PCD hash/size mismatch")
    header, marker, body = raw.partition(b"DATA binary\n")
    if not marker or b"FIELDS x y z normal_x normal_y normal_z\n" not in header or \
       b"SIZE 4 4 4 4 4 4\n" not in header or b"TYPE F F F F F F\n" not in header or \
       len(body) != 2_000_000 * 24:
        raise ValueError("pinned static PCD binary layout mismatch")
    points = np.frombuffer(body, dtype="<f4").reshape(-1, 6)[:, :3]
    return StaticBackgroundIndex(points, "published_building_pcd/sha256/" + BUILDING_PCD_SHA256)
