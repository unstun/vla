"""Measured locomotion ownership on the existing telemetry connection.

ID 9 is additive. All ID 1--8 payloads remain unchanged. Source time and
sequence identify actual physics updates, never bridge publication ticks.
"""
from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import Tuple

from .protocol import ProtocolError, _require_finite, _require_uint


class StanceMode(IntEnum):
    OFF = 0
    RL = 1
    STAND_SETTLING = 2
    STAND_TRANSITION = 3
    FIXED_STAND = 4
    REJOIN = 5


# Four identities, mode and three booleans, measured body twist, applied vx/vy/wz.
EXECUTION_STATE_STRUCT = struct.Struct("!QQQQBBBB9d")


@dataclass(frozen=True)
class ExecutionStateV1:
    simulation_time_ns: int
    state_sequence: int
    run_epoch_ns: int
    command_sequence: int
    stance_mode: StanceMode
    policy_owns_joints: bool
    navigation_ready: bool
    command_stale: bool
    linear_velocity_body: Tuple[float, float, float]
    angular_velocity_body: Tuple[float, float, float]
    applied_command: Tuple[float, float, float]


def _checked(state):
    for name in ("simulation_time_ns", "state_sequence", "run_epoch_ns", "command_sequence"):
        _require_uint(name, getattr(state, name), 64)
    if state.run_epoch_ns == 0:
        raise ProtocolError("execution state requires a nonzero run identity")
    try:
        StanceMode(state.stance_mode)
    except ValueError as error:
        raise ProtocolError("unknown stance mode") from error
    for name in ("policy_owns_joints", "navigation_ready", "command_stale"):
        if type(getattr(state, name)) is not bool:
            raise ProtocolError(name + " must be a boolean")
    for name in ("linear_velocity_body", "angular_velocity_body", "applied_command"):
        values = getattr(state, name)
        if len(values) != 3:
            raise ProtocolError(name + " must have three components")
        _require_finite(name, values)
    return state


def encode_execution_state_payload(state: ExecutionStateV1) -> bytes:
    state = _checked(state)
    return EXECUTION_STATE_STRUCT.pack(
        state.simulation_time_ns, state.state_sequence, state.run_epoch_ns,
        state.command_sequence, int(state.stance_mode), state.policy_owns_joints,
        state.navigation_ready, state.command_stale, *state.linear_velocity_body,
        *state.angular_velocity_body, *state.applied_command)


def decode_execution_state_payload(payload: bytes) -> ExecutionStateV1:
    if len(payload) != EXECUTION_STATE_STRUCT.size:
        raise ProtocolError("execution state payload length is invalid")
    values = EXECUTION_STATE_STRUCT.unpack(payload)
    if any(v not in (0, 1) for v in values[5:8]):
        raise ProtocolError("execution state contains a non-boolean flag")
    try:
        mode = StanceMode(values[4])
    except ValueError as error:
        raise ProtocolError("unknown stance mode") from error
    return _checked(ExecutionStateV1(
        *values[:4], mode, *map(bool, values[5:8]),
        tuple(values[8:11]), tuple(values[11:14]), tuple(values[14:17])))


def from_robot_sample(row, pose, *, simulation_time_ns, state_sequence,
                      run_epoch_ns, command_sequence, command_stale, navigation_ready):
    """Read one completed update; never infer PD ownership from a zero command."""
    return _checked(ExecutionStateV1(
        simulation_time_ns, state_sequence, run_epoch_ns, command_sequence or 0,
        StanceMode[row.get("stance_mode", "OFF")],
        bool(row.get("policy_owns_joints", True)), bool(navigation_ready),
        bool(command_stale), tuple(pose["linear_body"]), tuple(pose["angular_body"]),
        tuple(row["effective_command"])))
