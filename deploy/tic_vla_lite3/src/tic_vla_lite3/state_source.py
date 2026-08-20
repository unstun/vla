"""Robot-state sample contract and reasoning-relative displacement."""

from __future__ import annotations

import dataclasses
import math
from collections import deque
from typing import Deque, Optional
from typing import Tuple


@dataclasses.dataclass(frozen=True)
class RobotStateSample:
    sequence: int
    received_monotonic_s: float
    vx_mps: float
    vy_mps: float
    wz_radps: float
    x_m: float
    y_m: float

    def validate(self, now_s: float, max_age_s: float) -> None:
        values = (self.received_monotonic_s, self.vx_mps, self.vy_mps,
                  self.wz_radps, self.x_m, self.y_m, now_s, max_age_s)
        if self.sequence < 0 or not all(math.isfinite(value) for value in values):
            raise ValueError("invalid_state")
        if max_age_s <= 0.0:
            raise ValueError("invalid_state_age_limit")
        age = now_s - self.received_monotonic_s
        if age < 0.0 or age > max_age_s:
            raise ValueError("stale_state")


def model_state(current: RobotStateSample, generation_start: RobotStateSample,
                reasoning_delay_s: float) -> Tuple[float, float, float, float, float, float]:
    if not math.isfinite(reasoning_delay_s) or reasoning_delay_s < 0.0:
        raise ValueError("reasoning_delay")
    return (current.vx_mps, current.vy_mps, current.wz_radps,
            current.x_m - generation_start.x_m,
            current.y_m - generation_start.y_m, reasoning_delay_s)


class ReasoningReferenceBuffer:
    """Track the two generation starts used by the upstream async behavior.

    TIC-VLA's reference behaviors calculate displacement and delay from the
    older of the two most recently reported VLM generation starts.  Keeping an
    unbounded episode-start reference would make these inputs grow for the
    entire shadow run and diverge from that contract.
    """

    def __init__(self) -> None:
        self._starts: Deque[RobotStateSample] = deque(maxlen=2)

    def reference(self, current: RobotStateSample) -> RobotStateSample:
        return self._starts[0] if self._starts else current

    def observe(self, generation_step: Optional[int], generation_pose: Optional[dict],
                received_monotonic_s: float) -> None:
        if generation_step is None:
            return
        if (not isinstance(generation_step, int) or isinstance(generation_step, bool) or
                generation_step < 0 or not isinstance(generation_pose, dict)):
            raise ValueError("generation_reference")
        position = generation_pose.get("position")
        if (not isinstance(position, (list, tuple)) or len(position) < 2 or
                not all(isinstance(value, (int, float)) and
                        not isinstance(value, bool) and math.isfinite(float(value))
                        for value in position[:2])):
            raise ValueError("generation_pose")
        if self._starts and generation_step <= self._starts[-1].sequence:
            raise ValueError("generation_sequence")
        self._starts.append(RobotStateSample(
            generation_step, received_monotonic_s, 0.0, 0.0, 0.0,
            float(position[0]), float(position[1])))

    def reset(self) -> None:
        self._starts.clear()
