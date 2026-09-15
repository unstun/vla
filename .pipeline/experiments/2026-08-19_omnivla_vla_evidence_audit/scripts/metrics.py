#!/usr/bin/env python3
"""Shared trajectory metrics used by analysis and review rendering."""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any, Dict, Iterable, List

from audit_contract import validate_trajectory


def _flatten(trajectory: List[List[float]]) -> List[float]:
    return [item for row in validate_trajectory(trajectory) for item in row]


def pairwise_difference(left: List[List[float]], right: List[List[float]]) -> Dict[str, float]:
    lhs = _flatten(left)
    rhs = _flatten(right)
    differences = [abs(a - b) for a, b in zip(lhs, rhs)]
    return {
        "mae": sum(differences) / len(differences),
        "rmse": math.sqrt(sum(value * value for value in differences) / len(differences)),
        "max_abs": max(differences),
    }


def repeat_dispersion(trajectories: Iterable[List[List[float]]]) -> Dict[str, Any]:
    values = list(trajectories)
    pairs = [pairwise_difference(left, right) for left, right in combinations(values, 2)]
    if not pairs:
        return {"pair_count": 0, "mean_pairwise_mae": None, "mean_pairwise_rmse": None, "max_pairwise_abs": None}
    return {
        "pair_count": len(pairs),
        "mean_pairwise_mae": sum(item["mae"] for item in pairs) / len(pairs),
        "mean_pairwise_rmse": sum(item["rmse"] for item in pairs) / len(pairs),
        "max_pairwise_abs": max(item["max_abs"] for item in pairs),
    }


def trajectory_metrics(trajectory: List[List[float]]) -> Dict[str, float]:
    points = validate_trajectory(trajectory)
    path_length = 0.0
    previous_x = 0.0
    previous_y = 0.0
    for row in points:
        path_length += math.hypot(row[0] - previous_x, row[1] - previous_y)
        previous_x, previous_y = row[0], row[1]
    endpoint = points[-1]
    return {
        "endpoint_x": endpoint[0],
        "endpoint_y": endpoint[1],
        "path_length": path_length,
        "signed_lateral_displacement": endpoint[1],
        "heading_radians": math.atan2(endpoint[3], endpoint[2]),
    }

