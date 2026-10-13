"""Command gate between raw SCAN velocity and the Lite3 bridge command topic."""

from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .contracts import CommandIdentity, ContractError, GateConfig, MeasuredState, require_xyz


@dataclass(frozen=True)
class GateOutput:
    allowed: bool
    command_xyz_yaw: Tuple[float, float, float]
    reason: str
    identity: Optional[CommandIdentity]


class CommandGate:
    """Stateful safety gate for SCAN command ownership.

    This gate is intentionally independent of model calls and PCT planning.  A
    caller should tick it from a ROS timer and route raw SCAN commands through
    :meth:`gate_raw_command` before publishing to the bridge topic.
    """

    def __init__(
        self,
        config: Optional[GateConfig] = None,
        clock: Callable[[], float] = time.monotonic,
        sim_clock: Optional[Callable[[], Optional[float]]] = None,
    ) -> None:
        self.config = config or GateConfig()
        self.clock = clock
        self.owner = None  # type: Optional[CommandIdentity]
        self.closed_reason = "no_owner"
        self.cancel_pending = False
        self.hold_ack = False
        self.transport_ok = True
        self.last_heartbeat_s = None  # type: Optional[float]
        self.last_measurement = None  # type: Optional[MeasuredState]
        self.still_since_s = None  # type: Optional[float]
        self.events = []  # type: List[Dict[str, Any]]
        self.sim_clock = sim_clock  # v33: newest /clock in seconds, or None before the first

    def admit(self, identity: CommandIdentity) -> None:
        self.owner = identity
        self.closed_reason = "open"
        self.cancel_pending = False
        self.hold_ack = False
        self.transport_ok = True
        self.still_since_s = None
        self._event("admit", {"identity": identity.to_dict()})

    def close(self, reason: str) -> None:
        self.closed_reason = reason
        self._event("close", {"reason": reason, "owner": self.owner.to_dict() if self.owner else None})

    def clear_owner_if_quiescent(self) -> bool:
        if self.owner is not None and self.stop_confirmed():
            self._event("release", {"identity": self.owner.to_dict()})
            self.owner = None
            self.closed_reason = "no_owner"
            self.cancel_pending = False
            self.hold_ack = False
            self.still_since_s = None
            return True
        return False

    def request_cancel(self, identity: CommandIdentity, reason: str) -> None:
        if self.owner is None or not self.owner.matches(identity):
            self.close("cancel_identity_mismatch")
            return
        self.cancel_pending = True
        self.close(reason)

    def confirm_consumer_hold(self, identity: CommandIdentity) -> None:
        if self.owner is None or not self.owner.matches(identity):
            raise ContractError("hold_identity_mismatch")
        self.hold_ack = True
        self.close("consumer_hold_confirmed")

    def observe_heartbeat(self, now_s: Optional[float] = None) -> None:
        self.last_heartbeat_s = self.clock() if now_s is None else float(now_s)

    def observe_transport_loss(self, reason: str = "transport_loss") -> None:
        self.transport_ok = False
        self.close(reason)

    def observe_map_invalidated(self, reason: str = "map_invalidated") -> None:
        self.close(reason)

    def observe_measurement(self, state: MeasuredState) -> None:
        if self.last_measurement is not None and state.state_sequence <= self.last_measurement.state_sequence:
            raise ContractError("stale_measured_state_sequence")
        self.last_measurement = state
        if state.horizontal_speed_mps <= self.config.still_speed_mps:
            if self.still_since_s is None:
                self.still_since_s = state.monotonic_s
        else:
            self.still_since_s = None

    def stop_confirmed(self) -> bool:
        if not self.hold_ack:
            return False
        if self.last_measurement is None or self.still_since_s is None:
            return False
        return (self.last_measurement.monotonic_s - self.still_since_s) >= self.config.still_window_s

    def gate_raw_command(
        self,
        identity: Optional[CommandIdentity],
        command_xyz_yaw: Tuple[float, float, float],
        now_s: Optional[float] = None,
    ) -> GateOutput:
        now = self.clock() if now_s is None else float(now_s)
        command = require_xyz("command_xyz_yaw", command_xyz_yaw)
        reason = self._blocking_reason(identity, now)
        if reason is not None:
            self._event("blocked_command", {"reason": reason, "identity": identity.to_dict() if identity else None})
            return GateOutput(False, (0.0, 0.0, 0.0), reason, self.owner)
        return GateOutput(True, command, "ok", self.owner)

    def tick(self, now_s: Optional[float] = None) -> GateOutput:
        return self.gate_raw_command(self.owner, (0.0, 0.0, 0.0), now_s=now_s)

    def _blocking_reason(self, identity: Optional[CommandIdentity], now: float) -> Optional[str]:
        if self.owner is None:
            return "no_owner"
        if identity is None or not self.owner.matches(identity):
            return "identity_mismatch"
        if self.closed_reason != "open":
            return self.closed_reason
        if self.cancel_pending:
            return "cancel_pending"
        if not self.transport_ok:
            return "transport_loss"
        if self.last_heartbeat_s is None or now - self.last_heartbeat_s > self.config.heartbeat_stale_s:
            self.closed_reason = "heartbeat_stale"
            return "heartbeat_stale"
        if self.measurement_stale(self.last_measurement, now):
            self.closed_reason = "odom_stale"
            return "odom_stale"
        if self.last_measurement.map_epoch != self.owner.map_epoch or self.last_measurement.map_revision != self.owner.map_revision:
            self.closed_reason = "measured_map_mismatch"
            return "measured_map_mismatch"
        return None

    def measurement_stale(self, measurement: Optional[MeasuredState], now: float) -> bool:
        """Whether a body pose is too old to steer by.

        Wall base: its wall-time age exceeds odom_stale_s. Simulation base (v33): its simulation-time age
        against the newest /clock exceeds odom_stale_s, or its wall-time age exceeds odom_wall_backstop_s
        (/clock stops with a stopped simulator and with a stalled pose path, as it travels with the poses);
        a missing stamp or clock counts as stale.
        """
        if measurement is None:
            return True
        if self.config.odom_time_base == "wall":
            return now - measurement.monotonic_s > self.config.odom_stale_s
        sim_now = self.sim_clock() if self.sim_clock is not None else None
        if measurement.stamp_s is None or sim_now is None:
            return True
        return (max(0.0, sim_now - measurement.stamp_s) > self.config.odom_stale_s
                or now - measurement.monotonic_s > self.config.odom_wall_backstop_s)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "owner": self.owner.to_dict() if self.owner else None,
            "closed_reason": self.closed_reason,
            "cancel_pending": self.cancel_pending,
            "hold_ack": self.hold_ack,
            "transport_ok": self.transport_ok,
            "last_heartbeat_s": self.last_heartbeat_s,
            "last_measurement": None if self.last_measurement is None else {
                "state_sequence": self.last_measurement.state_sequence,
                "monotonic_s": self.last_measurement.monotonic_s,
                "position_world_m": self.last_measurement.position_world_m,
                "velocity_world_mps": self.last_measurement.velocity_world_mps,
                "map_epoch": self.last_measurement.map_epoch,
                "map_revision": self.last_measurement.map_revision,
                "source": self.last_measurement.source,
            },
            "still_since_s": self.still_since_s,
        }

    def _event(self, kind: str, data: Dict[str, Any]) -> None:
        self.events.append({
            "seq": len(self.events) + 1,
            "monotonic_s": self.clock(),
            "kind": kind,
            "data": copy.deepcopy(data),
        })
