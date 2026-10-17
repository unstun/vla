"""Clock mapping around the unchanged archived command-state implementation."""
from dataclasses import replace
from pathlib import Path
import sys
import threading

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "runtime_sources/bridge"))
from lite3_sim_bridge.command_state import LatestCommandState
from lite3_sim_bridge.protocol import ProtocolError
from clock_sync import ClockUnavailable


class DomainCommandState(LatestCommandState):
    def __init__(self, clock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock
        self.domain_lock = threading.Lock()
        self.remote_source = 0
        self.remote_command = self.ZERO

    def update_batch(self, updates):
        try:
            estimate = self.clock.estimate()
        except ClockUnavailable as error:
            raise ProtocolError(str(error)) from error
        converted = []
        for command, sequence, source, received in updates:
            # Check the latest plausible time too: mapping to the earliest time
            # for conservative age must not conceal a future-dated command.
            latest = source + estimate.local_minus_remote_ns + estimate.uncertainty_ns
            if latest - received > self._max_future_skew_ns:
                raise ProtocolError("remote command can exceed original future-skew limit")
            converted.append((command, sequence, estimate.remote_to_local_earliest(source), received))
        with self.domain_lock:
            snapshot = super().update_batch(converted)
            self.remote_source = updates[-1][2]
            self.remote_command = updates[-1][0]
            return snapshot

    def snapshot(self, now_monotonic_ns):
        snapshot = super().snapshot(now_monotonic_ns)
        try:
            self.clock.estimate()
        except ClockUnavailable:
            return replace(snapshot, command=self.ZERO, stale=True, reason="clock_unsynchronized")
        return snapshot

    def current(self, now_monotonic_ns):
        with self.domain_lock:
            return self.snapshot(now_monotonic_ns), self.remote_source, self.remote_command
