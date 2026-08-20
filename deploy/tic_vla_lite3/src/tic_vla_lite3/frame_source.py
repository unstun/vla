"""Replay samples and monotonic four-frame delayed context selection."""

from __future__ import annotations

import dataclasses
import math
from collections import deque
from pathlib import Path
from typing import Deque, Iterable, List, Sequence


@dataclasses.dataclass(frozen=True)
class FrameSample:
    sequence: int
    captured_monotonic_s: float
    width: int
    height: int
    rgb_jpeg: bytes

    @property
    def valid(self) -> bool:
        return (self.sequence >= 0 and math.isfinite(self.captured_monotonic_s) and
                self.captured_monotonic_s >= 0.0 and
                self.width > 0 and self.height > 0 and bool(self.rgb_jpeg))


class DelayedFrameBuffer:
    def __init__(self, max_history_s: float = 11.0) -> None:
        self._samples: Deque[FrameSample] = deque()
        self._max_history_s = max_history_s
        self._last_sequence = -1

    def append(self, sample: FrameSample) -> None:
        if not sample.valid:
            raise ValueError("invalid_frame")
        if sample.sequence <= self._last_sequence:
            raise ValueError("frame_sequence")
        if self._samples and sample.captured_monotonic_s <= self._samples[-1].captured_monotonic_s:
            raise ValueError("frame_time")
        self._samples.append(sample)
        self._last_sequence = sample.sequence
        cutoff = sample.captured_monotonic_s - self._max_history_s
        while self._samples and self._samples[0].captured_monotonic_s < cutoff:
            self._samples.popleft()

    def context(self, now_s: float, delays_s: Sequence[float] = (9.0, 6.0, 3.0, 0.0),
                tolerance_s: float = 1.0) -> List[FrameSample]:
        if not self._samples:
            raise ValueError("empty_history")
        if (not math.isfinite(now_s) or not math.isfinite(tolerance_s) or
                tolerance_s < 0.0 or not all(math.isfinite(delay) and delay >= 0.0
                                             for delay in delays_s)):
            raise ValueError("history_time")
        selected: List[FrameSample] = []
        samples = list(self._samples)
        for delay in delays_s:
            target = now_s - delay
            nearest = min(samples, key=lambda sample: abs(sample.captured_monotonic_s - target))
            if abs(nearest.captured_monotonic_s - target) > tolerance_s:
                raise ValueError("history_gap")
            selected.append(nearest)
        return selected


class ReplayFrameSource:
    def __init__(self, paths: Iterable[Path], start_monotonic_s: float = 0.0,
                 interval_s: float = 0.1, width: int = 640, height: int = 480) -> None:
        self._paths = list(paths)
        self._start = start_monotonic_s
        self._interval = interval_s
        self._width = width
        self._height = height

    def samples(self) -> Iterable[FrameSample]:
        for sequence, path in enumerate(self._paths):
            yield FrameSample(sequence, self._start + sequence * self._interval,
                              self._width, self._height, path.read_bytes())
