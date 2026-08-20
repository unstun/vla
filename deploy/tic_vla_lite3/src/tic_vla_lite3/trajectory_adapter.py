"""Pure TIC-VLA waypoint validation and bounded Spot-reference following."""

from __future__ import annotations

import dataclasses
import math
from typing import Optional

import numpy as np


@dataclasses.dataclass(frozen=True)
class AdapterConfig:
    lookahead_m: float = 1.0
    min_path_m: float = 0.05
    max_segment_m: float = 1.0
    max_path_m: float = 15.0
    max_age_s: float = 0.50
    yaw_filter_alpha: float = 0.35
    curvature_epsilon: float = 1e-6
    curvature_speed_gain: float = 0.20
    yaw_feedforward_gain: float = 0.50
    yaw_feedback_gain: float = 0.80
    vx_max_mps: float = 0.30
    wz_abs_max_radps: float = 0.20
    vx_slew_mps2: float = 0.30
    wz_slew_radps2: float = 0.40


@dataclasses.dataclass(frozen=True)
class BodyVelocity:
    vx_mps: float
    vy_mps: float
    wz_radps: float
    valid: bool
    reason: str
    waypoint_index: int = -1


class TrajectoryAdapter:
    def __init__(self, config: AdapterConfig = AdapterConfig()) -> None:
        self.config = config
        self._last_sequence = -1
        self._yaw_filtered: Optional[float] = None
        self._last = BodyVelocity(0.0, 0.0, 0.0, False, "startup")
        self._last_time_s: Optional[float] = None

    @staticmethod
    def _zero(reason: str) -> BodyVelocity:
        return BodyVelocity(0.0, 0.0, 0.0, False, reason)

    @staticmethod
    def zero(reason: str) -> BodyVelocity:
        """Return a reason-coded non-actuating result for an upstream reject."""
        return TrajectoryAdapter._zero(reason)

    def reset(self) -> None:
        self._last_sequence = -1
        self._yaw_filtered = None
        self._last = self._zero("reset")
        self._last_time_s = None

    def adapt(self, waypoints: np.ndarray, sequence: int, produced_monotonic_s: float,
              now_monotonic_s: float) -> BodyVelocity:
        if not isinstance(waypoints, np.ndarray) or waypoints.shape != (30, 2):
            return self._zero("shape")
        if not np.isfinite(waypoints).all():
            return self._zero("nonfinite")
        if sequence <= self._last_sequence:
            return self._zero("sequence")
        age = now_monotonic_s - produced_monotonic_s
        if not math.isfinite(age) or age < 0.0 or age > self.config.max_age_s:
            return self._zero("stale")
        segment_lengths = np.linalg.norm(np.diff(waypoints, axis=0), axis=1)
        if not np.isfinite(segment_lengths).all() or np.any(segment_lengths > self.config.max_segment_m):
            return self._zero("discontinuity")
        cumulative = np.concatenate(([0.0], np.cumsum(segment_lengths)))
        path_length = float(cumulative[-1])
        if path_length < self.config.min_path_m:
            return self._zero("short_path")
        if path_length > self.config.max_path_m:
            return self._zero("long_path")

        index = int(np.searchsorted(cumulative, self.config.lookahead_m, side="left"))
        index = min(max(index, 2), len(waypoints) - 3)
        x, y = (float(v) for v in waypoints[index])
        distance2 = x * x + y * y
        if distance2 <= self.config.curvature_epsilon:
            return self._zero("degenerate_lookahead")
        heading = math.atan2(y, x)
        alpha = self.config.yaw_filter_alpha
        if self._yaw_filtered is None:
            yaw_filtered = heading
        else:
            wrapped_error = math.atan2(
                math.sin(heading - self._yaw_filtered),
                math.cos(heading - self._yaw_filtered))
            yaw_filtered = self._yaw_filtered + alpha * wrapped_error
        curvature = 2.0 * y / distance2
        curvature_speed = self.config.curvature_speed_gain / (
            abs(curvature) + self.config.curvature_epsilon)
        vx = min(self.config.vx_max_mps, max(0.0, curvature_speed))
        wz = (self.config.yaw_feedforward_gain * vx * curvature +
              self.config.yaw_feedback_gain * yaw_filtered)
        wz = max(-self.config.wz_abs_max_radps,
                 min(self.config.wz_abs_max_radps, wz))

        if self._last_time_s is not None:
            dt = now_monotonic_s - self._last_time_s
            if not math.isfinite(dt) or dt <= 0.0:
                return self._zero("time_order")
            vx = _slew(self._last.vx_mps, vx, self.config.vx_slew_mps2 * dt)
            wz = _slew(self._last.wz_radps, wz, self.config.wz_slew_radps2 * dt)
        result = BodyVelocity(vx, 0.0, wz, True, "ok", index)
        self._yaw_filtered = yaw_filtered
        self._last_sequence = sequence
        self._last_time_s = now_monotonic_s
        self._last = result
        return result


def _slew(previous: float, target: float, maximum_delta: float) -> float:
    return max(previous - maximum_delta, min(previous + maximum_delta, target))
