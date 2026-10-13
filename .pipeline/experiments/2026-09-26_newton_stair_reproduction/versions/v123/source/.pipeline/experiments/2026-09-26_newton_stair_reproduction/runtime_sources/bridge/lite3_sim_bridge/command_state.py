"""Thread-safe latest-command state and fail-closed watchdog behavior."""

from dataclasses import dataclass
import math
import threading
from typing import Optional, Sequence, Tuple

from .protocol import CommandV1, ProtocolError, SequenceTracker


@dataclass(frozen=True)
class CommandLimits:
    """Per-axis command limits with an optional horizontal-norm limit.

    `max_horizontal_norm` defaults to None, which reproduces the original
    per-axis-only behavior exactly. When set, two separately saturated axes can
    no longer combine into a horizontal speed above the declared limit: the XY
    pair is scaled down along its own direction so the commanded heading is
    preserved.
    """

    max_vx: float = 0.75
    max_vy: float = 0.35
    max_wz: float = 1.0
    max_horizontal_norm: Optional[float] = None

    def __post_init__(self) -> None:
        values = (self.max_vx, self.max_vy, self.max_wz)
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("command limits must be finite and positive")
        if self.max_horizontal_norm is not None and not (
            math.isfinite(self.max_horizontal_norm) and self.max_horizontal_norm > 0.0
        ):
            raise ValueError("max_horizontal_norm must be finite and positive")

    def clamp(self, command: CommandV1) -> CommandV1:
        values = (command.vx, command.vy, command.wz)
        if not all(math.isfinite(value) for value in values):
            raise ProtocolError("command contains a non-finite value")
        vx = max(-self.max_vx, min(self.max_vx, command.vx))
        vy = max(-self.max_vy, min(self.max_vy, command.vy))
        if self.max_horizontal_norm is not None:
            norm = math.hypot(vx, vy)
            if norm > self.max_horizontal_norm:
                scale = self.max_horizontal_norm / norm
                vx *= scale
                vy *= scale
        return CommandV1(
            vx=vx,
            vy=vy,
            wz=max(-self.max_wz, min(self.max_wz, command.wz)),
        )


@dataclass(frozen=True)
class CommandSnapshot:
    command: CommandV1
    sequence: Optional[int]
    source_timestamp_ns: Optional[int]
    received_monotonic_ns: Optional[int]
    stale: bool
    reason: str
    watchdog_events: int
    sequence_gaps: int
    # A latched case failure is terminal for this simulation trial. It is not
    # a watchdog event and no reconnect, fresh command or new trajectory clears
    # it: only a newly constructed state object starts another case.
    case_failed: bool = False
    case_failure_reason: Optional[str] = None


class LatestCommandState:
    """Own the command sequence, timestamp validation, clamp and watchdog."""

    ZERO = CommandV1(0.0, 0.0, 0.0)

    def __init__(
        self,
        limits: CommandLimits,
        timeout_ns: int = 250_000_000,
        max_source_age_ns: int = 250_000_000,
        max_future_skew_ns: int = 25_000_000,
    ) -> None:
        for name, value in (
            ("timeout_ns", timeout_ns),
            ("max_source_age_ns", max_source_age_ns),
            ("max_future_skew_ns", max_future_skew_ns),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError("{} must be a non-negative integer".format(name))
        if timeout_ns == 0:
            raise ValueError("timeout_ns must be positive")
        self._limits = limits
        self._timeout_ns = timeout_ns
        self._max_source_age_ns = max_source_age_ns
        self._max_future_skew_ns = max_future_skew_ns
        self._lock = threading.Lock()
        self._command = self.ZERO
        self._sequence_tracker = SequenceTracker()
        self._source_timestamp_ns = None  # type: Optional[int]
        self._received_monotonic_ns = None  # type: Optional[int]
        self._stale = True
        self._reason = "no_command"
        self._watchdog_events = 0
        self._case_failed = False
        self._case_failure_reason = None  # type: Optional[str]

    @property
    def case_failed(self) -> bool:
        return self._case_failed

    def latch_case_failure(self, reason: str) -> CommandSnapshot:
        """Terminally disable command admission for this simulation case.

        The first reason wins so the original cause survives any later event.
        Admission stays disabled through reconnects and fresh commands; the
        transport contract itself is untouched, so a client may still connect
        and send, but nothing it sends is ever admitted again.
        """
        if not isinstance(reason, str) or not reason:
            raise ValueError("case failure reason must be a non-empty string")
        with self._lock:
            if not self._case_failed:
                self._case_failed = True
                self._case_failure_reason = reason
            self._command = self.ZERO
            self._stale = True
            self._reason = "case_failed"
            return self._snapshot_locked()

    def update(
        self,
        command: CommandV1,
        sequence: int,
        source_timestamp_ns: int,
        received_monotonic_ns: int,
    ) -> CommandSnapshot:
        return self.update_batch(
            ((command, sequence, source_timestamp_ns, received_monotonic_ns),)
        )

    def update_batch(
        self,
        updates: Sequence[Tuple[CommandV1, int, int, int]],
    ) -> CommandSnapshot:
        """Atomically coalesce a received backlog to its fresh latest command.

        Every sequence is observed so an intentional latest-wins coalesce is
        not reported as packet loss. Intermediate source-stale commands are
        never applied. The newest command must still satisfy the unchanged
        freshness and future-skew limits, otherwise the whole batch fails.
        """

        if not updates:
            raise ValueError("command update batch must not be empty")
        checked_updates = []
        for command, sequence, source_timestamp_ns, received_monotonic_ns in updates:
            for name, value in (
                ("sequence", sequence),
                ("source_timestamp_ns", source_timestamp_ns),
                ("received_monotonic_ns", received_monotonic_ns),
            ):
                if not isinstance(value, int) or value < 0:
                    raise ProtocolError(
                        "{} must be a non-negative integer".format(name)
                    )
            age_ns = received_monotonic_ns - source_timestamp_ns
            if age_ns < -self._max_future_skew_ns:
                raise ProtocolError("command timestamp is too far in the future")
            checked_updates.append(
                (
                    self._limits.clamp(command),
                    sequence,
                    source_timestamp_ns,
                    received_monotonic_ns,
                    age_ns,
                )
            )
        if checked_updates[-1][4] > self._max_source_age_ns:
            raise ProtocolError("command timestamp is stale")

        with self._lock:
            previous_sequence = self._sequence_tracker.last_sequence
            for _, sequence, _, _, _ in checked_updates:
                if previous_sequence is not None and sequence <= previous_sequence:
                    raise ProtocolError("sequence is not increasing")
                previous_sequence = sequence
            for _, sequence, _, _, _ in checked_updates:
                self._sequence_tracker.observe(sequence)
            latest = checked_updates[-1]
            self._source_timestamp_ns = latest[2]
            self._received_monotonic_ns = latest[3]
            if self._case_failed:
                # Sequence and receipt bookkeeping continue so the transport
                # contract and its evidence stay intact, but a failed case can
                # never re-admit motion.
                self._command = self.ZERO
                self._stale = True
                self._reason = "case_failed"
                return self._snapshot_locked()
            self._command = latest[0]
            self._stale = False
            self._reason = "active"
            return self._snapshot_locked()

    def snapshot(self, now_monotonic_ns: int) -> CommandSnapshot:
        if not isinstance(now_monotonic_ns, int) or now_monotonic_ns < 0:
            raise ValueError("now_monotonic_ns must be a non-negative integer")
        with self._lock:
            if self._case_failed:
                self._command = self.ZERO
                self._stale = True
                self._reason = "case_failed"
                return self._snapshot_locked()
            if (
                not self._stale
                and self._received_monotonic_ns is not None
                and now_monotonic_ns - self._received_monotonic_ns > self._timeout_ns
            ):
                self._command = self.ZERO
                self._stale = True
                self._reason = "watchdog_timeout"
                self._watchdog_events += 1
            return self._snapshot_locked()

    def mark_disconnected(self) -> CommandSnapshot:
        with self._lock:
            was_active = not self._stale
            self._command = self.ZERO
            self._stale = True
            # A reconnect may clear "disconnected"; it can never clear a case
            # failure, so the terminal reason is preserved here.
            self._reason = "case_failed" if self._case_failed else "disconnected"
            if was_active:
                self._watchdog_events += 1
            return self._snapshot_locked()

    def _snapshot_locked(self) -> CommandSnapshot:
        return CommandSnapshot(
            command=self._command,
            sequence=self._sequence_tracker.last_sequence,
            source_timestamp_ns=self._source_timestamp_ns,
            received_monotonic_ns=self._received_monotonic_ns,
            stale=self._stale,
            reason=self._reason,
            watchdog_events=self._watchdog_events,
            sequence_gaps=self._sequence_tracker.gap_count,
            case_failed=self._case_failed,
            case_failure_reason=self._case_failure_reason,
        )
