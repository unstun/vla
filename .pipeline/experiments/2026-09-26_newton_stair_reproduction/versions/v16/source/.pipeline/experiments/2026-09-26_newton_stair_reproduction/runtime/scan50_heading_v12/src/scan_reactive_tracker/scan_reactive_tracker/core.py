"""ROS-free, fail-closed current LiDAR cluster tracker candidate.

This detects moving person-shaped clusters, not human identity. Association
uses only last observed centers. No velocity or future occupancy is computed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Sequence, Tuple

NANOSECOND = 1_000_000_000
Cell = Tuple[int, int]
Point = Tuple[float, float, float]


@dataclass(frozen=True)
class TerrainSupport:
    frame: str
    stamp_ns: int
    source_id: str
    resolution_m: float
    origin_x_m: float
    origin_y_m: float
    heights: Dict[Cell, Tuple[float, ...]]

    def ground_below(self, x: float, y: float, z: float) -> Optional[float]:
        ix = math.floor((x - self.origin_x_m) / self.resolution_m)
        iy = math.floor((y - self.origin_y_m) / self.resolution_m)
        choices = [h for h in self.heights.get((ix, iy), ()) if h <= z + 0.05]
        return max(choices) if choices else None


@dataclass(frozen=True)
class PoseObservation:
    stamp_ns: int
    world_frame: str
    sensor_frame: str
    position: Point
    quaternion_xyzw: Tuple[float, float, float, float]


@dataclass(frozen=True)
class CloudFrame:
    stamp_ns: int
    frame: str
    points: Sequence[Point]
    complete: bool = True


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    z: float
    radius_m: float
    count: int


@dataclass(frozen=True)
class CurrentTrack:
    id: str
    stamp_ns: int
    center: Point
    radius_m: float


@dataclass(frozen=True)
class Snapshot:
    stamp_ns: int
    frame: str
    source_id: str
    complete: bool
    tracks: Tuple[CurrentTrack, ...]
    reason: str


@dataclass
class TrackState:
    id: str
    x: float
    y: float
    z: float
    radius_m: float
    stamp_ns: int
    anchor_x: float
    anchor_y: float
    observations: int = 1
    confirmed_moving: bool = False
    missing_frames: int = 0


@dataclass(frozen=True)
class TrackerParameters:
    max_cloud_age_ns: int = 250_000_000
    max_terrain_age_ns: int = 86_400 * NANOSECOND
    max_points: int = 100_000
    max_range_m: float = 5.0
    min_height_m: float = 0.35
    max_height_m: float = 2.0
    cluster_cell_m: float = 0.20
    min_cluster_points: int = 8
    min_vertical_span_m: float = 0.45
    min_horizontal_span_m: float = 0.10
    max_horizontal_span_m: float = 0.90
    association_radius_m: float = 0.65
    motion_confirmation_m: float = 0.08
    max_association_gap_ns: int = 500_000_000


def rotate_by_quaternion(point: Point, quaternion: Tuple[float, float, float, float]) -> Point:
    x, y, z, w = quaternion
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or norm < 0.95 or norm > 1.05:
        raise ValueError("invalid sensor quaternion norm")
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    px, py, pz = point
    # q * p * q^-1, using the equivalent rotation matrix.
    return (
        (1 - 2*(y*y + z*z))*px + 2*(x*y - z*w)*py + 2*(x*z + y*w)*pz,
        2*(x*y + z*w)*px + (1 - 2*(x*x + z*z))*py + 2*(y*z - x*w)*pz,
        2*(x*z - y*w)*px + 2*(y*z + x*w)*py + (1 - 2*(x*x + y*y))*pz,
    )


def world_point(point: Point, pose: PoseObservation) -> Point:
    rotated = rotate_by_quaternion(point, pose.quaternion_xyzw)
    return tuple(a + b for a, b in zip(rotated, pose.position))  # type: ignore[return-value]


def shape_candidates(
    cloud: CloudFrame, pose: PoseObservation, terrain: TerrainSupport,
    p: TrackerParameters,
) -> List[Detection]:
    buckets: Dict[Cell, List[Point]] = {}
    for point in cloud.points:
        if not all(math.isfinite(v) for v in point):
            continue
        if math.dist(point, (0.0, 0.0, 0.0)) > p.max_range_m:
            continue
        x, y, z = world_point(point, pose)
        ground = terrain.ground_below(x, y, z)
        if ground is None or not p.min_height_m <= z - ground <= p.max_height_m:
            continue
        key = (math.floor(x / p.cluster_cell_m), math.floor(y / p.cluster_cell_m))
        buckets.setdefault(key, []).append((x, y, z))

    detections: List[Detection] = []
    unvisited = set(buckets)
    while unvisited:
        start = unvisited.pop()
        queue = [start]
        component: List[Point] = []
        while queue:
            cx, cy = queue.pop()
            component.extend(buckets[(cx, cy)])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor = (cx + dx, cy + dy)
                    if neighbor in unvisited:
                        unvisited.remove(neighbor)
                        queue.append(neighbor)
        if len(component) < p.min_cluster_points:
            continue
        xs, ys, zs = zip(*component)
        width, depth = max(xs) - min(xs), max(ys) - min(ys)
        horizontal_span = math.hypot(width, depth)
        vertical_span = max(zs) - min(zs)
        if not (p.min_horizontal_span_m <= horizontal_span <= p.max_horizontal_span_m and
                vertical_span >= p.min_vertical_span_m):
            continue
        detections.append(Detection(
            x=sum(xs) / len(xs), y=sum(ys) / len(ys), z=sum(zs) / len(zs),
            radius_m=max(0.30, min(0.60, horizontal_span / 2 + 0.15)),
            count=len(component),
        ))
    return sorted(detections, key=lambda d: (d.x, d.y))


class MovingClusterTracker:
    SOURCE_ID = "sensor_lidar_moving_cluster_candidate_v2"

    def __init__(self, parameters: TrackerParameters = TrackerParameters()) -> None:
        self.p = parameters
        self._states: Dict[str, TrackState] = {}
        self._next_id = 1
        self._last_frame_ns: Optional[int] = None

    def _invalid(self, cloud: CloudFrame, terrain: Optional[TerrainSupport], reason: str) -> Snapshot:
        return Snapshot(cloud.stamp_ns, terrain.frame if terrain else "", self.SOURCE_ID,
                        False, (), reason)

    def process(
        self, cloud: CloudFrame, pose: Optional[PoseObservation],
        terrain: Optional[TerrainSupport], now_ns: int,
    ) -> Snapshot:
        if pose is None or terrain is None:
            return self._invalid(cloud, terrain, "missing_pose_or_terrain")
        if not cloud.complete or cloud.frame != pose.sensor_frame or \
           terrain.frame != pose.world_frame or not terrain.source_id or \
           cloud.stamp_ns != pose.stamp_ns or cloud.stamp_ns <= 0:
            return self._invalid(cloud, terrain, "incomplete_or_frame_mismatch")
        if now_ns < cloud.stamp_ns or now_ns - cloud.stamp_ns > self.p.max_cloud_age_ns or \
           now_ns < terrain.stamp_ns or now_ns - terrain.stamp_ns > self.p.max_terrain_age_ns:
            return self._invalid(cloud, terrain, "stale_or_future_input")
        if self._last_frame_ns is not None and cloud.stamp_ns <= self._last_frame_ns:
            return self._invalid(cloud, terrain, "non_monotonic_cloud")
        if len(cloud.points) > self.p.max_points or not terrain.heights or \
           not math.isfinite(terrain.resolution_m) or terrain.resolution_m <= 0 or \
           not all(math.isfinite(v) for v in pose.position):
            return self._invalid(cloud, terrain, "invalid_cloud_pose_or_terrain")
        try:
            rotate_by_quaternion((0.0, 0.0, 0.0), pose.quaternion_xyzw)
            detections = shape_candidates(cloud, pose, terrain, self.p)
        except (ValueError, OverflowError):
            return self._invalid(cloud, terrain, "invalid_sensor_transform")
        self._last_frame_ns = cloud.stamp_ns

        pairs = []
        for track_id, state in self._states.items():
            if cloud.stamp_ns - state.stamp_ns > self.p.max_association_gap_ns:
                continue
            for index, detection in enumerate(detections):
                distance = math.hypot(detection.x - state.x, detection.y - state.y)
                if distance <= self.p.association_radius_m:
                    pairs.append((distance, track_id, index))
        matched_states, matched_detections = set(), set()
        for distance, track_id, index in sorted(pairs):
            if track_id in matched_states or index in matched_detections:
                continue
            state, detection = self._states[track_id], detections[index]
            # Keep the first observed center as the motion anchor. At 10 Hz a
            # 0.3 m/s pedestrian moves only 0.03 m between adjacent frames.
            # Association still uses the last observed center; the anchor is
            # evidence of observed displacement, never a predicted position.
            observed_displacement = math.hypot(
                detection.x - state.anchor_x, detection.y - state.anchor_y)
            if observed_displacement >= self.p.motion_confirmation_m:
                state.confirmed_moving = True
            state.x, state.y, state.z = detection.x, detection.y, detection.z
            state.radius_m = detection.radius_m
            state.stamp_ns = cloud.stamp_ns
            state.observations += 1
            state.missing_frames = 0
            matched_states.add(track_id)
            matched_detections.add(index)

        for index, detection in enumerate(detections):
            if index in matched_detections:
                continue
            track_id = f"cluster-{self._next_id}"
            self._next_id += 1
            self._states[track_id] = TrackState(
                track_id, detection.x, detection.y, detection.z,
                detection.radius_m, cloud.stamp_ns,
                detection.x, detection.y,
            )
            matched_states.add(track_id)

        unresolved = False
        for track_id, state in list(self._states.items()):
            if track_id not in matched_states:
                state.missing_frames += 1
                if not state.confirmed_moving and state.missing_frames >= 2:
                    del self._states[track_id]
                    continue
                unresolved = True
            elif not state.confirmed_moving and state.observations < 3:
                unresolved = True
        current = tuple(
            CurrentTrack(state.id, cloud.stamp_ns, (state.x, state.y, state.z), state.radius_m)
            for state in sorted(self._states.values(), key=lambda item: item.id)
            if state.confirmed_moving and state.missing_frames == 0
        )
        return Snapshot(cloud.stamp_ns, terrain.frame, self.SOURCE_ID,
                        not unresolved, current,
                        "current_cluster_observation" if not unresolved else "unresolved_or_lost_cluster")
