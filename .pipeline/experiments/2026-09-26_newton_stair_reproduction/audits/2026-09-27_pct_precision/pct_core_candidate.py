"""Pinned PCT ground points and a nonzero simulation-clock publication gate.

The point projection follows pct_planner.planner_node:publish_tomogram, pinned
locally by PCT_PUBLISHER_SHA. No ROS import occurs in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import pickle
from typing import Optional

import numpy as np

P2B = Path(__file__).resolve().parent.parent
DEFAULT_MAP = P2B / "inputs/new_building.pickle"
MAP_SHA = "ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da"
PCT_PUBLISHER_SHA = "8392343358f37e636f415e1dd8dd238b8dbb55b8bbb0386f7f2decb51642576b"
FIELDS = (("x", 0, 7, 1), ("y", 4, 7, 1), ("z", 8, 7, 1),
          ("intensity", 12, 7, 1))


def load_pinned_map(path: Path = DEFAULT_MAP) -> dict:
    if hashlib.sha256(path.read_bytes()).hexdigest() != MAP_SHA:
        raise ValueError("PCT Building map SHA-256 mismatch")
    with path.open("rb") as handle:
        data = pickle.load(handle)
    if not isinstance(data, dict) or not all(k in data for k in
                                              ("data", "resolution", "center", "slice_dh")):
        raise ValueError("PCT map contract mismatch")
    if float(data["resolution"]) != 0.1:
        raise ValueError("PCT map resolution mismatch")
    return data


ELEVATION_SOURCE_SHA = "9adbbaf3754fc1a488ada560775407d4c684d57e19a6caea7075fa907b5c0c2d"


def load_paired_elevations(path: Path, source: dict) -> np.ndarray:
    """Read original ground precision only after exact map-pair verification."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != ELEVATION_SOURCE_SHA:
        raise ValueError("PCT original-precision source SHA-256 mismatch")
    with np.load(path, allow_pickle=False) as original:
        data = np.asarray(original["data"])
        stored = np.asarray(source["data"])
        if data.dtype != np.float32 or data.shape != stored.shape or stored.dtype != np.float16 or \
           not np.array_equal(data.astype(np.float16), stored, equal_nan=True):
            raise ValueError("Original precision data does not round to the pinned map")
        for name in ("center", "resolution", "slice_h0", "slice_dh"):
            if not np.array_equal(np.asarray(original[name]), np.asarray(source[name])):
                raise ValueError("Original precision map metadata mismatch: " + name)
        return data[3].copy()


def selected_ground_points(
    source: dict, coord_mode: str = "identity",
    visual_z_offset_m: float = 0.03, cost_limit: Optional[float] = 20.0,
    paired_elevations: Optional[np.ndarray] = None,
) -> np.ndarray:
    if coord_mode not in ("identity", "sim_to_pct_180deg") or \
       not math.isfinite(visual_z_offset_m) or (cost_limit is not None and not math.isfinite(cost_limit)):
        raise ValueError("invalid PCT publisher parameters")
    tomogram = np.asarray(source["data"], dtype=np.float32)
    if tomogram.ndim != 4 or tomogram.shape[0] < 4:
        raise ValueError("invalid PCT tomogram shape")
    elevation_raw = tomogram[3]
    ground = np.where(np.isfinite(elevation_raw), elevation_raw, np.nan).copy()
    traversability = tomogram[0].copy()
    slice_dh = float(source["slice_dh"])
    for layer in range(ground.shape[0] - 1):
        height_difference = ground[layer + 1] - ground[layer]
        duplicate = np.isfinite(height_difference) & (height_difference < slice_dh)
        ground[layer, duplicate] = np.nan
        traversability[layer + 1, duplicate] = np.minimum(
            traversability[layer, duplicate], traversability[layer + 1, duplicate]
        )
    # None is a separate physical-ground input for perception. The default
    # selected navigation payload remains byte-identical to the pinned source.
    visible = np.isfinite(ground) & (np.isfinite(traversability) if cost_limit is None
                                    else traversability <= cost_limit)
    layers, grid_x, grid_y = np.nonzero(visible)
    if len(layers) == 0:
        raise ValueError("PCT map has no selected ground cells")
    center = np.asarray(source["center"], dtype=np.double)
    resolution = float(source["resolution"])
    offset = np.array([int(tomogram.shape[2] / 2), int(tomogram.shape[3] / 2)],
                      dtype=np.int32)
    x = (grid_x - offset[0]) * resolution + center[0]
    y = (grid_y - offset[1]) * resolution + center[1]
    # Selection, layer deduplication and cost remain the original float16 map.
    # Only the already-selected ground heights may retain generation precision.
    if paired_elevations is not None:
        paired_elevations = np.asarray(paired_elevations)
        if paired_elevations.shape != elevation_raw.shape or paired_elevations.dtype != np.float32 or \
           not np.array_equal(paired_elevations.astype(np.float16), elevation_raw.astype(np.float16), equal_nan=True):
            raise ValueError("Ground elevations do not match the stored map")
    height_source = ground if paired_elevations is None else paired_elevations
    z = height_source[layers, grid_x, grid_y] + visual_z_offset_m
    planner_points = np.column_stack((x, y, z)).astype(np.float32)
    world_points = planner_points.copy()
    if coord_mode == "sim_to_pct_180deg":
        world_points[..., :2] *= -1.0
    cost = traversability[layers, grid_x, grid_y].astype(np.float32)
    return np.column_stack((world_points, cost)).astype(np.float32)


@dataclass(frozen=True)
class CloudPayload:
    stamp_ns: int
    frame: str
    width: int
    height: int
    point_step: int
    row_step: int
    fields: tuple
    data: bytes


def cloud_payload(points: np.ndarray, stamp_ns: int, frame: str = "world") -> CloudPayload:
    if stamp_ns <= 0 or not frame:
        raise ValueError("a nonzero simulation stamp and frame are required")
    if points.ndim != 2 or points.shape[1] != 4 or len(points) == 0 or \
       not np.isfinite(points).all():
        raise ValueError("invalid selected ground points")
    little_endian = np.ascontiguousarray(points, dtype="<f4")
    return CloudPayload(
        stamp_ns=stamp_ns, frame=frame, width=len(little_endian), height=1,
        point_step=16, row_step=16 * len(little_endian), fields=FIELDS,
        data=little_endian.tobytes(),
    )


class SimClockGate:
    """Publish after two progressing positive /clock callbacks; rearm on reset."""

    def __init__(self) -> None:
        self._first_positive_ns: Optional[int] = None
        self._last_ns: Optional[int] = None
        self._published = False

    def observe(self, clock_ns: int) -> Optional[int]:
        if clock_ns <= 0:
            if self._last_ns is not None and clock_ns < self._last_ns:
                self._first_positive_ns = None
                self._published = False
            self._last_ns = clock_ns
            return None
        if self._last_ns is not None and clock_ns < self._last_ns:
            self._first_positive_ns = None
            self._published = False
        self._last_ns = clock_ns
        if self._first_positive_ns is None:
            self._first_positive_ns = clock_ns
            return None
        if self._published or clock_ns <= self._first_positive_ns:
            return None
        self._published = True
        return clock_ns
