"""Version-owned timing and pose helpers; units are seconds, metres and radians."""
import math


def positive_finite(value, name):
    if isinstance(value, bool):
        raise ValueError(name + "_must_be_numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(name + "_must_be_finite_positive")
    return result


def normalize_yaw(value):
    if isinstance(value, bool):
        raise ValueError("target_yaw_rad_must_be_numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("target_yaw_rad_must_be_finite")
    return math.atan2(math.sin(value), math.cos(value))


def final_path_yaw(waypoints):
    if not waypoints:
        raise ValueError("goal_orientation_path_empty")
    end = waypoints[-1]
    for previous in reversed(waypoints[:-1]):
        dx, dy = end[0] - previous[0], end[1] - previous[1]
        if math.hypot(dx, dy) > 1e-6:
            return math.atan2(dy, dx)
    raise ValueError("goal_orientation_path_has_no_horizontal_segment")


class PeriodicDeadline:
    """Phase-preserving rate limit; one call can consume at most one slot."""
    def __init__(self, frequency):
        self.period = 1.0 / positive_finite(frequency, "frequency")
        if not math.isfinite(self.period) or self.period <= 0.0 or self.period > 1e9:
            raise ValueError("frequency_has_unrepresentable_period")
        self.next_s = None
        self.last_s = None
        self.skipped_slots = 0

    def due(self, now):
        now = float(now)
        if not math.isfinite(now):
            raise ValueError("nonfinite_schedule_clock")
        if self.last_s is not None and now < self.last_s:
            self.next_s = now + self.period
        self.last_s = now
        if self.next_s is None:
            self.next_s = now + self.period
        if now + 1e-9 < self.next_s:
            return False
        skipped = int(math.floor(max(0.0, now - self.next_s + 1e-9) / self.period))
        self.skipped_slots += skipped
        self.next_s += (skipped + 1) * self.period
        return True
