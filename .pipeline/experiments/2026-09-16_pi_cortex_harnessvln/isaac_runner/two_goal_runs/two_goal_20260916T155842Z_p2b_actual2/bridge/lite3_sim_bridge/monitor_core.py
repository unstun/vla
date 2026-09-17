"""ROS-independent aggregation for closed-loop acceptance monitoring."""

from dataclasses import dataclass, field
import math
from typing import Dict, Optional, Sequence, Set, Tuple


def should_record_periodic_event(
    previous_receipt_ns: int, receipt_ns: int, period_ns: int
) -> bool:
    """Return whether a bounded-rate evidence event is due."""

    if receipt_ns <= 0 or period_ns <= 0 or previous_receipt_ns < 0:
        raise ValueError("periodic event timestamps and period must be positive")
    return previous_receipt_ns == 0 or receipt_ns - previous_receipt_ns >= period_ns


@dataclass
class TopicStats:
    count: int = 0
    first_receipt_ns: Optional[int] = None
    last_receipt_ns: Optional[int] = None
    last_stamp_ns: Optional[int] = None
    nonincreasing_stamp_count: int = 0

    def observe(self, receipt_ns: int, stamp_ns: Optional[int] = None) -> None:
        if receipt_ns < 0 or (stamp_ns is not None and stamp_ns < 0):
            raise ValueError("monitor timestamps must be non-negative")
        if self.first_receipt_ns is None:
            self.first_receipt_ns = receipt_ns
        self.last_receipt_ns = receipt_ns
        self.count += 1
        if stamp_ns is not None:
            if self.last_stamp_ns is not None and stamp_ns <= self.last_stamp_ns:
                self.nonincreasing_stamp_count += 1
            self.last_stamp_ns = stamp_ns

    def summary(self) -> Dict[str, object]:
        duration_seconds = 0.0
        rate_hz = 0.0
        if self.first_receipt_ns is not None and self.last_receipt_ns is not None:
            duration_seconds = max(
                0.0, (self.last_receipt_ns - self.first_receipt_ns) / 1.0e9
            )
            if self.count >= 2 and duration_seconds > 0.0:
                rate_hz = (self.count - 1) / duration_seconds
        return {
            "count": self.count,
            "duration_seconds": duration_seconds,
            "rate_hz": rate_hz,
            "nonincreasing_stamp_count": self.nonincreasing_stamp_count,
        }


@dataclass
class AcceptanceAccumulator:
    nonzero_command_threshold: float = 0.05
    topics: Dict[str, TopicStats] = field(
        default_factory=lambda: {
            name: TopicStats()
            for name in ("body_pose", "sensor_pose", "cloud", "cmd_vel", "bspline")
        }
    )
    path_length_m: float = 0.0
    last_body_position: Optional[Tuple[float, float, float]] = None
    max_abs_command: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    last_command: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    nonzero_command_count: int = 0
    cloud_point_sum: int = 0
    cloud_point_min: Optional[int] = None
    cloud_point_max: int = 0
    trajectory_ids: Set[int] = field(default_factory=set)
    body_stamps: Set[int] = field(default_factory=set)
    sensor_stamps: Set[int] = field(default_factory=set)
    cloud_stamps: Set[int] = field(default_factory=set)

    @staticmethod
    def _position(values: Sequence[float]) -> Tuple[float, float, float]:
        if len(values) != 3:
            raise ValueError("position must contain three values")
        result = tuple(float(value) for value in values)
        if not all(math.isfinite(value) for value in result):
            raise ValueError("position must be finite")
        return result

    def observe_body_pose(
        self, receipt_ns: int, stamp_ns: int, position: Sequence[float]
    ) -> None:
        checked = self._position(position)
        self.topics["body_pose"].observe(receipt_ns, stamp_ns)
        self.body_stamps.add(stamp_ns)
        if self.last_body_position is not None:
            self.path_length_m += math.dist(self.last_body_position, checked)
        self.last_body_position = checked

    def observe_sensor_pose(self, receipt_ns: int, stamp_ns: int) -> None:
        self.topics["sensor_pose"].observe(receipt_ns, stamp_ns)
        self.sensor_stamps.add(stamp_ns)

    def observe_cloud(self, receipt_ns: int, stamp_ns: int, point_count: int) -> None:
        if point_count < 0:
            raise ValueError("point count must be non-negative")
        self.topics["cloud"].observe(receipt_ns, stamp_ns)
        self.cloud_stamps.add(stamp_ns)
        self.cloud_point_sum += point_count
        self.cloud_point_min = (
            point_count if self.cloud_point_min is None else min(self.cloud_point_min, point_count)
        )
        self.cloud_point_max = max(self.cloud_point_max, point_count)

    def observe_command(self, receipt_ns: int, command: Sequence[float]) -> None:
        if len(command) != 3:
            raise ValueError("command must contain three values")
        checked = tuple(float(value) for value in command)
        if not all(math.isfinite(value) for value in checked):
            raise ValueError("command must be finite")
        self.topics["cmd_vel"].observe(receipt_ns)
        self.last_command = checked
        for index, value in enumerate(checked):
            self.max_abs_command[index] = max(self.max_abs_command[index], abs(value))
        if max(abs(value) for value in checked) > self.nonzero_command_threshold:
            self.nonzero_command_count += 1

    def observe_bspline(self, receipt_ns: int, trajectory_id: int) -> None:
        self.topics["bspline"].observe(receipt_ns)
        self.trajectory_ids.add(int(trajectory_id))

    def summary(self) -> Dict[str, object]:
        cloud_count = self.topics["cloud"].count
        synchronized = len(self.body_stamps & self.sensor_stamps & self.cloud_stamps)
        return {
            "schema_version": 1,
            "topics": {name: stats.summary() for name, stats in self.topics.items()},
            "path_length_m": self.path_length_m,
            "last_body_position": self.last_body_position,
            "max_abs_command": self.max_abs_command,
            "last_command": self.last_command,
            "nonzero_command_count": self.nonzero_command_count,
            "cloud_points": {
                "minimum": 0 if self.cloud_point_min is None else self.cloud_point_min,
                "maximum": self.cloud_point_max,
                "mean": 0.0 if cloud_count == 0 else self.cloud_point_sum / cloud_count,
            },
            "unique_trajectory_count": len(self.trajectory_ids),
            "trajectory_ids": sorted(self.trajectory_ids),
            "synchronized_sensor_triplet_count": synchronized,
            "synchronized_sensor_triplet_fraction": (
                0.0 if cloud_count == 0 else synchronized / cloud_count
            ),
        }
