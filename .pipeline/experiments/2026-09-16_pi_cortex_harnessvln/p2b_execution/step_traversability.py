"""ROS-free step-vs-wall rule for SCAN occupancy queries.

ETH StepFilter is the surveyed source of the height-jump test
(https://github.com/leggedrobotics/traversability_estimation). This module
does not import that repository. Thresholds are V12 capability, not ETH
defaults. The thin-wall test (minimum high-patch plan extent) is ours.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Sequence, Tuple

Cell = Tuple[int, int]
Sample = Tuple[int, int, float]


@dataclass(frozen=True)
class StepTraversabilityParams:
    critical_height_m: float = 0.26
    window_radius_m: float = 0.30
    height_band_m: float = 0.05
    min_tread_depth_m: float = 0.15
    min_step_height_m: float = 0.04
    resolution_m: float = 0.05


DEFAULT_PARAMS = StepTraversabilityParams()


def samples_in_window(
    height_by_cell: Dict[Cell, float],
    query_x: float,
    query_y: float,
    params: StepTraversabilityParams,
) -> List[Sample]:
    qix = math.floor(query_x / params.resolution_m)
    qiy = math.floor(query_y / params.resolution_m)
    r_cells = int(math.ceil(params.window_radius_m / params.resolution_m))
    radius_sq = params.window_radius_m * params.window_radius_m
    samples: List[Sample] = []
    for dx in range(-r_cells, r_cells + 1):
        for dy in range(-r_cells, r_cells + 1):
            ix = qix + dx
            iy = qiy + dy
            cx = (ix + 0.5) * params.resolution_m
            cy = (iy + 0.5) * params.resolution_m
            if (cx - query_x) ** 2 + (cy - query_y) ** 2 > radius_sq:
                continue
            if (ix, iy) not in height_by_cell:
                continue
            samples.append((ix, iy, float(height_by_cell[(ix, iy)])))
    return samples


def classify_step_samples(
    samples: Sequence[Sample],
    params: StepTraversabilityParams,
) -> bool:
    if len(samples) < 2:
        return False
    zs = [sample[2] for sample in samples]
    h_min = min(zs)
    h_max = max(zs)
    delta = h_max - h_min
    if delta < params.min_step_height_m:
        return False
    if delta >= params.critical_height_m:
        return False
    high = [
        sample
        for sample in samples
        if abs(sample[2] - h_max) <= params.height_band_m
    ]
    if not high:
        return False
    ixs = [sample[0] for sample in high]
    iys = [sample[1] for sample in high]
    span_x = (max(ixs) - min(ixs) + 1) * params.resolution_m
    span_y = (max(iys) - min(iys) + 1) * params.resolution_m
    return min(span_x, span_y) >= params.min_tread_depth_m


def occupancy_hit_is_traversable_step(
    height_by_cell: Dict[Cell, float],
    query_x: float,
    query_y: float,
    params: StepTraversabilityParams,
) -> bool:
    return classify_step_samples(
        samples_in_window(height_by_cell, query_x, query_y, params),
        params,
    )
