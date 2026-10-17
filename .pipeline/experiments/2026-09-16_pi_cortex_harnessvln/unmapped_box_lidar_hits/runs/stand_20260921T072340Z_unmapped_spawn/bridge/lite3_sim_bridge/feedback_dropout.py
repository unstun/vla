"""Opt-in bounded simulation probe: withhold genuine state, never fabricate it."""
import math


class FeedbackDropout:
    def __init__(self, start_sim_s=-1.0, duration_wall_s=0.0):
        if not math.isfinite(start_sim_s) or not math.isfinite(duration_wall_s):
            raise ValueError('dropout settings must be finite')
        self.enabled = start_sim_s >= 0
        if self.enabled and not 0.25 < duration_wall_s <= 2.0:
            raise ValueError('enabled dropout must exceed the 0.25 s deadline and be <= 2 s')
        if not self.enabled and duration_wall_s != 0:
            raise ValueError('disabled dropout must have zero duration')
        self.start_sim_s = start_sim_s
        self.duration_ns = int(duration_wall_s * 1e9)
        self.started_ns = None
        self.restored_ns = None
        self.withheld_sequences = []

    def suppress(self, sim_s, monotonic_ns, sequence):
        if not self.enabled or sim_s < self.start_sim_s or self.restored_ns is not None:
            return False
        if self.started_ns is None:
            self.started_ns = monotonic_ns
        if monotonic_ns - self.started_ns >= self.duration_ns:
            self.restored_ns = monotonic_ns
            return False
        self.withheld_sequences.append(sequence)
        return True

    def record(self):
        return {'enabled': self.enabled, 'scheduled_sim_s': self.start_sim_s,
                'duration_wall_s': self.duration_ns / 1e9,
                'started_monotonic_ns': self.started_ns,
                'restored_monotonic_ns': self.restored_ns,
                'withheld_sequences': list(self.withheld_sequences)}
