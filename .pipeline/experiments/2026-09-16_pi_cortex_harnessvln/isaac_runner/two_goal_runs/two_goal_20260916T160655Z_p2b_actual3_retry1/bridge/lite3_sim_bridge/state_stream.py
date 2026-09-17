"""Consume-once holder for the complete body-state stream.

The failure this module exists to prevent is a *plausible* state: an odometry
message whose pose and twist were sampled at different times, or a sample that
keeps being republished after the producer stopped stepping. Both look healthy
to every downstream consumer and both stop the robot for reasons that have
nothing to do with the robot.

Rules enforced here, all of them independent of any ROS clock:

* One sample is handed out at most once, keyed on its state sequence. A stalled
  producer therefore produces silence, not a fresh-looking repeat.
* State sequence must strictly increase and simulation time must not go
  backwards. A reordered or duplicated packet is refused, not merged.
* Run identity is latched on the first accepted sample. A packet from an
  earlier run is refused even if its sequence and time look newer.
* A sample the freshness monitor already refused is never stored.

This module holds no ROS types so it can be exercised without a ROS graph, and
so the same rules are testable directly.
"""

from __future__ import annotations

import threading
from typing import Optional, Tuple

DUPLICATE_SEQUENCE = "duplicate_or_reordered_state_sequence"
BACKWARD_SIMULATION_TIME = "backward_simulation_time"
FOREIGN_RUN_IDENTITY = "foreign_run_identity"
REFUSED_BY_FRESHNESS_MONITOR = "refused_by_freshness_monitor"


class CompleteStateStream:
    """Latest accepted complete body state, deliverable exactly once."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending = None  # type: Optional[Tuple[object, int]]
        self._last_sequence = None  # type: Optional[int]
        self._last_simulation_time_ns = None  # type: Optional[int]
        self._run_epoch_ns = None  # type: Optional[int]
        self._last_rejection = None  # type: Optional[str]
        self._accepted = 0
        self._delivered = 0
        self._superseded_before_delivery = 0
        self._rejected_duplicate_sequence = 0
        self._rejected_backward_time = 0
        self._rejected_foreign_run = 0
        self._rejected_by_monitor = 0

    @property
    def last_rejection(self) -> Optional[str]:
        with self._lock:
            return self._last_rejection

    @property
    def run_epoch_ns(self) -> Optional[int]:
        with self._lock:
            return self._run_epoch_ns

    def offer(self, state, receive_monotonic_ns: int, monitor_accepted: bool = True) -> bool:
        """Offer one decoded ``BodyStateV2``. True when it became the pending sample."""
        with self._lock:
            if not monitor_accepted:
                self._rejected_by_monitor += 1
                self._last_rejection = REFUSED_BY_FRESHNESS_MONITOR
                return False
            if self._run_epoch_ns is None:
                self._run_epoch_ns = state.run_epoch_ns
            elif state.run_epoch_ns != self._run_epoch_ns:
                self._rejected_foreign_run += 1
                self._last_rejection = FOREIGN_RUN_IDENTITY
                return False
            if self._last_sequence is not None and state.state_sequence <= self._last_sequence:
                self._rejected_duplicate_sequence += 1
                self._last_rejection = DUPLICATE_SEQUENCE
                return False
            if (
                self._last_simulation_time_ns is not None
                and state.simulation_time_ns < self._last_simulation_time_ns
            ):
                self._rejected_backward_time += 1
                self._last_rejection = BACKWARD_SIMULATION_TIME
                return False
            if self._pending is not None:
                # The previous sample never reached ROS. That is a publication
                # backlog, recorded rather than hidden.
                self._superseded_before_delivery += 1
            self._pending = (state, int(receive_monotonic_ns))
            self._last_sequence = state.state_sequence
            self._last_simulation_time_ns = state.simulation_time_ns
            self._accepted += 1
            self._last_rejection = None
            return True

    def take(self):
        """Return ``(state, receive_monotonic_ns)`` once, then None until a new sample."""
        with self._lock:
            pending = self._pending
            self._pending = None
            if pending is not None:
                self._delivered += 1
            return pending

    def counters(self) -> dict:
        with self._lock:
            return {
                "complete_state_accepted": self._accepted,
                "complete_state_delivered": self._delivered,
                "complete_state_superseded_before_delivery": self._superseded_before_delivery,
                "complete_state_rejected_duplicate_sequence": self._rejected_duplicate_sequence,
                "complete_state_rejected_backward_time": self._rejected_backward_time,
                "complete_state_rejected_foreign_run": self._rejected_foreign_run,
                "complete_state_rejected_by_monitor": self._rejected_by_monitor,
                "complete_state_run_epoch_ns": self._run_epoch_ns,
                "complete_state_last_sequence": self._last_sequence,
            }
