"""Source-backed Livox MID-360 scan-pattern loading and scan slicing.

This module owns only the geometric ray directions and nominal point timing.
It deliberately does not model reflectivity, intensity, multiple returns,
weather, electronic noise, or intra-scan motion distortion.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Mapping, Optional

import numpy as np


OFFICIAL_MID360_PATTERN_COMMIT = "1cce1073633a062b92e30243a4c2920e45551bb5"
OFFICIAL_MID360_PATTERN_SHA256 = (
    "aa1fc08b6a4400608dbd6ee832b7ea3a9c3c37197e734f60f58fe5abf762269a"
)
OFFICIAL_MID360_PATTERN_SAMPLE_COUNT = 800_000
MID360_POINTS_PER_SECOND = 200_000
MID360_SCAN_HZ = 10
MID360_POINTS_PER_SCAN = MID360_POINTS_PER_SECOND // MID360_SCAN_HZ
MID360_MIN_RANGE_M = 0.1
MID360_MAX_RANGE_M = 40.0
MID360_AZIMUTH_FOV_DEG = (0.0, 360.0)
MID360_ELEVATION_FOV_DEG = (-7.0, 52.0)
MID360_PATTERN_HEADER = ("Time/s", "Azimuth/deg", "Zenith/deg")


class Mid360PatternError(ValueError):
    """Raised when a MID-360 pattern input violates its declared contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Mid360ScanWindow:
    """One nominal 0.1-second window of ordered MID-360 rays."""

    scan_index: int
    cycle_scan_index: int
    first_pattern_row: int
    last_pattern_row: int
    first_sample_ordinal: int
    last_sample_ordinal: int
    nominal_first_point_offset_ns: int
    nominal_last_point_offset_ns: int
    point_count: int

    def as_dict(self) -> Mapping[str, int]:
        return {
            "scan_index": self.scan_index,
            "cycle_scan_index": self.cycle_scan_index,
            "first_pattern_row": self.first_pattern_row,
            "last_pattern_row": self.last_pattern_row,
            "first_sample_ordinal": self.first_sample_ordinal,
            "last_sample_ordinal": self.last_sample_ordinal,
            "nominal_first_point_offset_ns": self.nominal_first_point_offset_ns,
            "nominal_last_point_offset_ns": self.nominal_last_point_offset_ns,
            "point_count": self.point_count,
        }


@dataclass(frozen=True)
class Mid360PatternTable:
    """Validated ordered MID-360 unit directions in the ROS sensor frame.

    Coordinates are ``x forward, y left, z up``. The pinned Livox plugin
    applies yaw from the CSV azimuth and pitch ``zenith - 90 deg`` to a
    positive-X ray; the equivalent elevation is ``90 deg - zenith``.
    """

    source_path: Path
    source_sha256: str
    directions_xyz: np.ndarray
    sample_count: int
    azimuth_range_deg: tuple[float, float]
    elevation_range_deg: tuple[float, float]
    points_per_second: int = MID360_POINTS_PER_SECOND
    scan_hz: int = MID360_SCAN_HZ

    @property
    def points_per_scan(self) -> int:
        return self.points_per_second // self.scan_hz

    @property
    def scans_per_pattern_cycle(self) -> int:
        if self.sample_count % self.points_per_scan != 0:
            raise Mid360PatternError(
                "pattern sample count is not divisible by the per-scan point count"
            )
        return self.sample_count // self.points_per_scan

    def scan_window(self, scan_index: int) -> tuple[np.ndarray, Mid360ScanWindow]:
        if isinstance(scan_index, bool) or not isinstance(scan_index, int) or scan_index < 0:
            raise Mid360PatternError("scan_index must be a non-negative integer")
        cycle_scan_index = scan_index % self.scans_per_pattern_cycle
        first = cycle_scan_index * self.points_per_scan
        last_exclusive = first + self.points_per_scan
        directions = self.directions_xyz[first:last_exclusive]
        if directions.shape != (self.points_per_scan, 3):
            raise Mid360PatternError("pattern window has an unexpected shape")
        metadata = Mid360ScanWindow(
            scan_index=scan_index,
            cycle_scan_index=cycle_scan_index,
            first_pattern_row=first + 2,
            last_pattern_row=last_exclusive + 1,
            first_sample_ordinal=first + 1,
            last_sample_ordinal=last_exclusive,
            nominal_first_point_offset_ns=0,
            nominal_last_point_offset_ns=(
                (self.points_per_scan - 1) * 1_000_000_000 // self.points_per_second
            ),
            point_count=self.points_per_scan,
        )
        return directions, metadata

    def identity(self) -> Mapping[str, object]:
        return {
            "model": "Livox MID-360 source-backed geometric snapshot",
            "upstream_repository": "https://github.com/Livox-SDK/livox_laser_simulation",
            "upstream_commit": OFFICIAL_MID360_PATTERN_COMMIT,
            "pattern_path": str(self.source_path),
            "pattern_sha256": self.source_sha256,
            "pattern_sample_count": self.sample_count,
            "pattern_cycle_seconds": self.sample_count / self.points_per_second,
            "scans_per_pattern_cycle": self.scans_per_pattern_cycle,
            "points_per_second": self.points_per_second,
            "scan_hz": self.scan_hz,
            "rays_per_scan": self.points_per_scan,
            "azimuth_range_degrees": list(self.azimuth_range_deg),
            "elevation_range_degrees": list(self.elevation_range_deg),
            "coordinate_frame": "sensor x-forward y-left z-up",
            "minimum_range_m": MID360_MIN_RANGE_M,
            "maximum_range_m": MID360_MAX_RANGE_M,
            "scan_reference_stamp": "same-step Isaac simulator time",
            "per_point_timing": "ordered nominal offsets retained in sensor metrics",
            "intra_scan_motion_distortion": "not modeled; all rays use one same-step pose",
            "unsupported_physics": [
                "material reflectivity and intensity",
                "multiple returns",
                "rain fog and dust",
                "electronic range noise",
            ],
        }


def load_mid360_pattern(
    path: Path,
    *,
    expected_sha256: Optional[str] = OFFICIAL_MID360_PATTERN_SHA256,
    expected_sample_count: Optional[int] = OFFICIAL_MID360_PATTERN_SAMPLE_COUNT,
    points_per_second: int = MID360_POINTS_PER_SECOND,
    scan_hz: int = MID360_SCAN_HZ,
) -> Mid360PatternTable:
    """Load and validate an ordered Livox angle-time CSV.

    The first CSV column is treated as an ordered sample ordinal because the
    pinned Livox plugin uses row order, not the misleading ``Time/s`` label, to
    advance the scan pattern.
    """

    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise Mid360PatternError(
            f"MID-360 pattern must be a regular file: {source_path}"
        )
    source_sha256 = sha256_file(source_path)
    if expected_sha256 is not None and source_sha256 != expected_sha256:
        raise Mid360PatternError(
            "MID-360 pattern SHA-256 mismatch: "
            f"expected {expected_sha256}, got {source_sha256}"
        )
    if (
        isinstance(points_per_second, bool)
        or not isinstance(points_per_second, int)
        or points_per_second <= 0
        or isinstance(scan_hz, bool)
        or not isinstance(scan_hz, int)
        or scan_hz <= 0
        or points_per_second % scan_hz != 0
    ):
        raise Mid360PatternError(
            "points_per_second and scan_hz must be positive integers with an exact ratio"
        )

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = tuple(part.strip() for part in handle.readline().strip().split(","))
    if header != MID360_PATTERN_HEADER:
        raise Mid360PatternError(
            f"unexpected MID-360 pattern header: {header!r}"
        )
    try:
        values = np.loadtxt(
            source_path,
            delimiter=",",
            skiprows=1,
            dtype=np.float64,
            ndmin=2,
        )
    except (OSError, ValueError) as error:
        raise Mid360PatternError(f"cannot parse MID-360 pattern: {error}") from error
    if values.ndim != 2 or values.shape[1] != 3 or values.shape[0] == 0:
        raise Mid360PatternError("MID-360 pattern must contain three finite columns")
    if not np.isfinite(values).all():
        raise Mid360PatternError("MID-360 pattern contains non-finite values")
    sample_count = int(values.shape[0])
    if expected_sample_count is not None and sample_count != expected_sample_count:
        raise Mid360PatternError(
            "MID-360 pattern sample-count mismatch: "
            f"expected {expected_sample_count}, got {sample_count}"
        )
    sample_ordinals = values[:, 0]
    if (
        sample_ordinals[0] != 1.0
        or sample_ordinals[-1] != float(sample_count)
        or not np.equal(np.diff(sample_ordinals), 1.0).all()
    ):
        raise Mid360PatternError(
            "MID-360 first column must be the consecutive ordinals 1..N"
        )
    points_per_scan = points_per_second // scan_hz
    if sample_count % points_per_scan != 0:
        raise Mid360PatternError(
            "MID-360 pattern cycle must contain a whole number of scans"
        )

    azimuth_deg = values[:, 1]
    elevation_deg = 90.0 - values[:, 2]
    if azimuth_deg.min() < 0.0 or azimuth_deg.max() > 360.0:
        raise Mid360PatternError("MID-360 azimuth must stay within [0, 360] deg")
    if elevation_deg.min() < -8.0 or elevation_deg.max() > 53.0:
        raise Mid360PatternError(
            "MID-360 elevation exceeds the source-backed vertical envelope"
        )

    azimuth_rad = np.deg2rad(azimuth_deg)
    elevation_rad = np.deg2rad(elevation_deg)
    cos_elevation = np.cos(elevation_rad)
    directions = np.column_stack(
        (
            cos_elevation * np.cos(azimuth_rad),
            cos_elevation * np.sin(azimuth_rad),
            np.sin(elevation_rad),
        )
    ).astype(np.float32, copy=False)
    norms = np.linalg.norm(directions, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=2.0e-6):
        raise Mid360PatternError("MID-360 ray directions are not unit length")
    directions.setflags(write=False)
    return Mid360PatternTable(
        source_path=source_path,
        source_sha256=source_sha256,
        directions_xyz=directions,
        sample_count=sample_count,
        azimuth_range_deg=(float(azimuth_deg.min()), float(azimuth_deg.max())),
        elevation_range_deg=(
            float(elevation_deg.min()),
            float(elevation_deg.max()),
        ),
        points_per_second=points_per_second,
        scan_hz=scan_hz,
    )
