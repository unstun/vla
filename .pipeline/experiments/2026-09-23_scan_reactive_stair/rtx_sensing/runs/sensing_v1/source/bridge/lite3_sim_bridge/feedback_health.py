"""Freshness, ordering and clock-progress gating for simulator feedback.

The audit's F4 finding is that command arrival was the only freshness signal on
the ROS side: a stopped simulation clock or a lost telemetry stream still left
recently published commands looking healthy, and 47 nonzero commands were
published across a 0.46 s interval in which simulation time never advanced.

This module answers one question for the command producer: *has the simulator
actually reported new, ordered state recently?* It deliberately does not look at
Twist arrival, planned-trajectory progress or any ROS timer, because each of
those can keep running while the simulator is stopped.

Clock domains, kept separate on purpose:

  * `simulation_time_ns` is Isaac simulation time. It is the value whose
    *progress* is being checked and is never used to measure elapsed real time.
  * `monotonic_ns` is the local monotonic wall clock. It is the value used to
    measure how long simulation time has failed to progress, so a stalled or
    paused simulation clock cannot hide its own stall.

An unhealthy verdict means the producer must command zero. Reporting a plausible
measured zero as a healthy sample is exactly the failure being corrected, so a
rejected sample never becomes valid feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Optional

NO_FEEDBACK = "no_feedback"
ACTIVE = "active"
STALLED = "simulation_clock_stalled"
DISCONNECTED = "telemetry_disconnected"
BACKWARD_TIME = "backward_simulation_time"
SEQUENCE_REGRESSION = "state_sequence_regression"
FOREIGN_RUN = "foreign_run_identity"


@dataclass(frozen=True)
class FeedbackVerdict:
    """Whether motion may be admitted, and the exact reason if it may not."""

    healthy: bool
    reason: str
    simulation_time_ns: Optional[int]
    state_sequence: Optional[int]
    stall_monotonic_ns: Optional[int]
    accepted: bool = True
    run_epoch_ns: Optional[int] = None

    def as_record(self) -> dict:
        return {
            "healthy": self.healthy,
            "reason": self.reason,
            "simulation_time_ns": self.simulation_time_ns,
            "state_sequence": self.state_sequence,
            "stall_monotonic_ns": self.stall_monotonic_ns,
            "accepted": self.accepted,
            "run_epoch_ns": self.run_epoch_ns,
        }


class SimulationFeedbackMonitor:
    """Track ordered, progressing simulator feedback on the monotonic clock."""

    def __init__(self, max_stall_ns: int) -> None:
        if not isinstance(max_stall_ns, int) or max_stall_ns <= 0:
            raise ValueError("max_stall_ns must be a positive integer")
        self._max_stall_ns = max_stall_ns
        self._lock = threading.Lock()
        self._simulation_time_ns = None  # type: Optional[int]
        self._state_sequence = None  # type: Optional[int]
        # Monotonic time of the last sample whose simulation time actually
        # advanced. A repeated timestamp does not refresh it.
        self._last_progress_monotonic_ns = None  # type: Optional[int]
        self._connected = True
        self._invalid = False
        self._invalid_reason = None  # type: Optional[str]
        self._backward_time_events = 0
        self._repeated_time_events = 0
        self._sequence_regression_events = 0
        self._stall_events = 0
        self._rejected_samples = 0
        self._in_stall = False
        # Run identity. The first epoch observed becomes this monitor's run;
        # a frame from any other run is rejected instead of being promoted to
        # fresh state, so a replayed packet cannot release a stop.
        self._run_epoch_ns = None  # type: Optional[int]
        self._foreign_run_events = 0

    @property
    def max_stall_ns(self) -> int:
        return self._max_stall_ns

    def observe(
        self,
        simulation_time_ns: int,
        state_sequence: int,
        monotonic_ns: int,
        run_epoch_ns: Optional[int] = None,
    ) -> FeedbackVerdict:
        """Record one body-state sample and re-evaluate feedback health."""
        for name, value in (
            ("simulation_time_ns", simulation_time_ns),
            ("state_sequence", state_sequence),
            ("monotonic_ns", monotonic_ns),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError("{} must be a non-negative integer".format(name))
        if run_epoch_ns is not None and (
            not isinstance(run_epoch_ns, int) or run_epoch_ns <= 0
        ):
            raise ValueError("run_epoch_ns must be a positive integer")
        with self._lock:
            if run_epoch_ns is not None:
                if self._run_epoch_ns is None:
                    self._run_epoch_ns = run_epoch_ns
                elif run_epoch_ns != self._run_epoch_ns:
                    # A frame from another run is not this run's state. It is
                    # refused outright and never advances time or sequence.
                    self._foreign_run_events += 1
                    self._rejected_samples += 1
                    return self._verdict_locked(
                        monotonic_ns, accepted=False, reject_reason=FOREIGN_RUN
                    )
            self._connected = True
            previous_time = self._simulation_time_ns
            previous_sequence = self._state_sequence
            if previous_time is not None and simulation_time_ns < previous_time:
                # Backward simulation time invalidates the stream until a
                # strictly newer sample arrives; it never becomes a valid zero.
                self._backward_time_events += 1
                self._rejected_samples += 1
                self._invalid = True
                self._invalid_reason = BACKWARD_TIME
                return self._verdict_locked(monotonic_ns, accepted=False)
            if previous_sequence is not None and state_sequence <= previous_sequence:
                self._sequence_regression_events += 1
                self._rejected_samples += 1
                self._invalid = True
                self._invalid_reason = SEQUENCE_REGRESSION
                return self._verdict_locked(monotonic_ns, accepted=False)
            if previous_time is not None and simulation_time_ns == previous_time:
                # A repeated stamp is a legitimate observation of a stopped
                # clock. It is accepted as a sample but must not refresh
                # progress, otherwise the stall could never be detected.
                self._repeated_time_events += 1
                self._state_sequence = state_sequence
                return self._verdict_locked(monotonic_ns)
            self._simulation_time_ns = simulation_time_ns
            self._state_sequence = state_sequence
            self._last_progress_monotonic_ns = monotonic_ns
            self._invalid = False
            self._invalid_reason = None
            self._in_stall = False
            return self._verdict_locked(monotonic_ns)

    def evaluate(self, monotonic_ns: int) -> FeedbackVerdict:
        """Re-evaluate health without a new sample, at the caller's rate."""
        if not isinstance(monotonic_ns, int) or monotonic_ns < 0:
            raise ValueError("monotonic_ns must be a non-negative integer")
        with self._lock:
            return self._verdict_locked(monotonic_ns)

    def mark_disconnected(self) -> None:
        """Telemetry transport loss: feedback is immediately not healthy."""
        with self._lock:
            self._connected = False
            self._last_progress_monotonic_ns = None

    def counters(self) -> dict:
        with self._lock:
            return {
                "backward_simulation_time_events": self._backward_time_events,
                "repeated_simulation_time_events": self._repeated_time_events,
                "state_sequence_regression_events": self._sequence_regression_events,
                "simulation_clock_stall_events": self._stall_events,
                "rejected_feedback_samples": self._rejected_samples,
                "foreign_run_identity_events": self._foreign_run_events,
                "run_epoch_ns": self._run_epoch_ns,
                "max_stall_ns": self._max_stall_ns,
            }

    def _verdict_locked(
        self,
        monotonic_ns: int,
        accepted: bool = True,
        reject_reason: Optional[str] = None,
    ) -> FeedbackVerdict:
        base = self._healthy_verdict_locked(monotonic_ns, accepted)
        if reject_reason is None:
            return base
        # A frame from another run is refused on its own terms. It does not
        # invalidate the stream this monitor is genuinely tracking, so the
        # health verdict is reported unchanged and only `accepted` says no.
        return FeedbackVerdict(
            base.healthy, reject_reason, base.simulation_time_ns,
            base.state_sequence, base.stall_monotonic_ns, False, self._run_epoch_ns,
        )

    def _healthy_verdict_locked(self, monotonic_ns: int, accepted: bool) -> FeedbackVerdict:
        if not self._connected:
            return FeedbackVerdict(
                False, DISCONNECTED, self._simulation_time_ns, self._state_sequence,
                None, accepted, self._run_epoch_ns,
            )
        if self._invalid:
            return FeedbackVerdict(
                False, self._invalid_reason or NO_FEEDBACK, self._simulation_time_ns,
                self._state_sequence, None, accepted, self._run_epoch_ns,
            )
        if self._last_progress_monotonic_ns is None:
            return FeedbackVerdict(
                False, NO_FEEDBACK, self._simulation_time_ns, self._state_sequence,
                None, accepted, self._run_epoch_ns,
            )
        stall_ns = monotonic_ns - self._last_progress_monotonic_ns
        if stall_ns > self._max_stall_ns:
            if not self._in_stall:
                self._stall_events += 1
                self._in_stall = True
            return FeedbackVerdict(
                False, STALLED, self._simulation_time_ns, self._state_sequence,
                stall_ns, accepted, self._run_epoch_ns,
            )
        return FeedbackVerdict(
            True, ACTIVE, self._simulation_time_ns, self._state_sequence, stall_ns,
            accepted, self._run_epoch_ns,
        )
