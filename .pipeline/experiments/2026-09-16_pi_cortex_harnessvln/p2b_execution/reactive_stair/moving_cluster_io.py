"""Validated ROS PointCloud2 payload decoding without a ROS import."""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Dict, List, Optional, Sequence, Tuple

from moving_cluster_core import TerrainSupport

Field = Tuple[int, int, int]  # offset, datatype, count
FLOAT32 = 7  # sensor_msgs/PointField.FLOAT32


def decode_float32_cloud(
    data: bytes, width: int, height: int, point_step: int, row_step: int,
    is_bigendian: bool, fields: Dict[str, Field], names: Sequence[str],
    max_points: int = 100_000,
) -> List[Tuple[float, ...]]:
    if is_bigendian or width < 0 or height <= 0 or width * height > max_points or \
       point_step <= 0 or row_step < width * point_step or len(data) < row_step * height:
        raise ValueError("invalid or unsupported PointCloud2 layout")
    offsets = []
    for name in names:
        if name not in fields:
            raise ValueError(f"missing PointCloud2 field: {name}")
        offset, datatype, count = fields[name]
        if datatype != FLOAT32 or count != 1 or offset < 0 or offset + 4 > point_step:
            raise ValueError(f"invalid PointCloud2 field: {name}")
        offsets.append(offset)
    output = []
    for row in range(height):
        row_base = row * row_step
        for column in range(width):
            base = row_base + column * point_step
            output.append(tuple(struct.unpack_from("<f", data, base + offset)[0]
                                for offset in offsets))
    return output


def terrain_from_pct_records(
    records: Sequence[Tuple[float, float, float, float]],
    data: bytes, frame: str, stamp_ns: int, resolution_m: float = 0.1,
    visual_z_offset_m: float = 0.03, cost_limit: Optional[float] = 20.0,
) -> TerrainSupport:
    if not frame or stamp_ns <= 0 or not math.isfinite(resolution_m) or resolution_m <= 0 or \
       not math.isfinite(visual_z_offset_m) or (cost_limit is not None and not math.isfinite(cost_limit)):
        raise ValueError("invalid PCT source metadata")
    selected = [(x, y, z - visual_z_offset_m) for x, y, z, cost in records
                if all(math.isfinite(v) for v in (x, y, z, cost)) and (cost_limit is None or cost <= cost_limit)]
    if not selected:
        raise ValueError("PCT selected ground is empty")
    origin_x = min(point[0] for point in selected) - resolution_m / 2
    origin_y = min(point[1] for point in selected) - resolution_m / 2
    heights = {}
    for x, y, z in selected:
        key = (math.floor((x - origin_x) / resolution_m),
               math.floor((y - origin_y) / resolution_m))
        heights.setdefault(key, []).append(z)
    return TerrainSupport(
        frame=frame, stamp_ns=stamp_ns,
        source_id=("pct_physical_ground" if cost_limit is None else "pct_tomogram") + "/sha256/" + hashlib.sha256(data).hexdigest(),
        resolution_m=resolution_m, origin_x_m=origin_x, origin_y_m=origin_y,
        heights={key: tuple(sorted(values)) for key, values in heights.items()},
    )
