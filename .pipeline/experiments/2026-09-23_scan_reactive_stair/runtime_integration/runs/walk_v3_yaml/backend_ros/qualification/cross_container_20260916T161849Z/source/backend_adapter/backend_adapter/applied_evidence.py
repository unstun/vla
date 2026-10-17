"""Atomic applied-command evidence reader and dwell verifier."""

from __future__ import annotations

import json
import math
import pathlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple

from .contracts import ContractError, require_finite, require_identifier, require_int, require_nonnegative, require_xyz

FRESH_STOP_REASONS = {"active", "held", "stopped", "zero_hold", "cancelled"}


@dataclass(frozen=True)
class StopEvidenceConfig:
    stop_command_norm: float = 0.01
    stop_speed_mps: float = 0.10
    stop_yaw_rate_radps: float = 0.15
    stop_dwell_sim_seconds: float = 1.0

    def __post_init__(self) -> None:
        require_nonnegative("stop_command_norm", self.stop_command_norm)
        require_nonnegative("stop_speed_mps", self.stop_speed_mps)
        require_nonnegative("stop_yaw_rate_radps", self.stop_yaw_rate_radps)
        require_nonnegative("stop_dwell_sim_seconds", self.stop_dwell_sim_seconds)


@dataclass(frozen=True)
class AppliedCommandSnapshot:
    run_id: str
    run_epoch_ns: int
    sim_step: int
    sim_time_s: float
    wall_monotonic_ns: int
    command_source_timestamp_ns: int
    max_reader_age_s: float
    applied_command: Tuple[float, float, float]
    admitted_command: Tuple[float, float, float]
    raw_command: Tuple[float, float, float]
    command_sequence: int
    command_stale: bool
    command_reason: str
    horizontal_speed_mps: float
    yaw_rate_radps: float
    base_xyz: Tuple[float, float, float]
    base_quat_wxyz: Tuple[float, float, float, float]
    command_obs_error: float
    state_sequence: int
    telemetry_sequence: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AppliedCommandSnapshot":
        if data.get("schema_version") != 1:
            raise ContractError("invalid_applied_snapshot_schema")
        freshness = _mapping("freshness", data.get("freshness"))
        measured = _mapping("measured", data.get("measured"))
        state_epoch = _mapping("state_epoch", data.get("state_epoch"))
        return cls(
            run_id=require_identifier("run_id", data.get("run_id")),
            run_epoch_ns=require_int("run_epoch_ns", data.get("run_epoch_ns"), 1),
            sim_step=require_int("sim_step", data.get("sim_step"), 0),
            sim_time_s=require_nonnegative("sim_time_s", data.get("sim_time_s")),
            wall_monotonic_ns=require_int("wall_monotonic_ns", data.get("wall_monotonic_ns"), 0),
            command_source_timestamp_ns=require_int("command_source_timestamp_ns", data.get("command_source_timestamp_ns"), 0),
            max_reader_age_s=require_nonnegative("max_reader_age_s", freshness.get("max_reader_age_s")),
            applied_command=_cmd_tuple("applied_command", data.get("applied_command")),
            admitted_command=_cmd_tuple("admitted_command", data.get("admitted_command")),
            raw_command=_cmd_tuple("raw_command", data.get("raw_command")),
            command_sequence=require_int("command_sequence", data.get("command_sequence"), 0),
            command_stale=_bool("command_stale", data.get("command_stale")),
            command_reason=require_identifier("command_reason", data.get("command_reason")),
            horizontal_speed_mps=require_nonnegative("horizontal_speed_mps", measured.get("horizontal_speed_mps")),
            yaw_rate_radps=require_finite("yaw_rate_radps", measured.get("yaw_rate_radps")),
            base_xyz=require_xyz("base_xyz", measured.get("base_xyz")),
            base_quat_wxyz=_quat("base_quat_wxyz", measured.get("base_quat_wxyz")),
            command_obs_error=require_nonnegative("command_obs_error", measured.get("command_obs_error")),
            state_sequence=require_int("state_sequence", state_epoch.get("state_sequence"), 0),
            telemetry_sequence=require_int("telemetry_sequence", state_epoch.get("telemetry_sequence"), 0),
        )

    def applied_xy_norm(self) -> float:
        return math.hypot(self.applied_command[0], self.applied_command[1])


class AppliedEvidenceReader:
    def __init__(self, path: pathlib.Path, monotonic_ns: Callable[[], int] = time.monotonic_ns) -> None:
        self.path = pathlib.Path(path)
        self.monotonic_ns = monotonic_ns

    def read(self) -> AppliedCommandSnapshot:
        try:
            text = self.path.read_text(encoding="utf-8")
            data = json.loads(text)
        except FileNotFoundError as exc:
            raise ContractError("applied_snapshot_missing") from exc
        except Exception as exc:
            raise ContractError("applied_snapshot_invalid_json") from exc
        if not isinstance(data, dict):
            raise ContractError("applied_snapshot_not_object")
        snapshot = AppliedCommandSnapshot.from_mapping(data)
        age_s = (self.monotonic_ns() - snapshot.wall_monotonic_ns) / 1.0e9
        if age_s < 0.0 or age_s > snapshot.max_reader_age_s:
            raise ContractError("applied_snapshot_stale")
        return snapshot


class StopEvidenceWindow:
    def __init__(self, config: Optional[StopEvidenceConfig] = None) -> None:
        self.config = config or StopEvidenceConfig()
        self.reset(0)

    def reset(self, min_command_source_timestamp_ns: int) -> None:
        self.min_command_source_timestamp_ns = int(min_command_source_timestamp_ns)
        self.first_ok_sim_time_s = None  # type: Optional[float]
        self.last_ok_sim_time_s = None  # type: Optional[float]
        self.last_state_sequence = None  # type: Optional[int]
        self.last_command_sequence = None  # type: Optional[int]

    def observe(self, snapshot: AppliedCommandSnapshot, expected_run_id: str, expected_run_epoch_ns: int) -> bool:
        if snapshot.run_id != expected_run_id:
            raise ContractError("applied_snapshot_run_mismatch")
        if snapshot.run_epoch_ns != expected_run_epoch_ns:
            raise ContractError("applied_snapshot_epoch_mismatch")
        if snapshot.command_source_timestamp_ns < self.min_command_source_timestamp_ns:
            self._reset_continuity()
            return False
        if self.last_state_sequence is not None and snapshot.state_sequence <= self.last_state_sequence:
            return False
        if self.last_command_sequence is not None and snapshot.command_sequence < self.last_command_sequence:
            self._reset_continuity()
            return False
        self.last_state_sequence = snapshot.state_sequence
        self.last_command_sequence = snapshot.command_sequence
        if not _instant_stop_ok(snapshot, self.config):
            self._reset_continuity()
            return False
        if self.first_ok_sim_time_s is None:
            self.first_ok_sim_time_s = snapshot.sim_time_s
        self.last_ok_sim_time_s = snapshot.sim_time_s
        return (self.last_ok_sim_time_s - self.first_ok_sim_time_s) >= self.config.stop_dwell_sim_seconds

    def _reset_continuity(self) -> None:
        self.first_ok_sim_time_s = None
        self.last_ok_sim_time_s = None


def stop_evidence_confirmed(snapshot: AppliedCommandSnapshot, expected_run_id: str, expected_run_epoch_ns: int, config: Optional[StopEvidenceConfig] = None) -> bool:
    # Compatibility helper for unit checks: validates one fresh sample but does not satisfy dwell by itself.
    if snapshot.run_id != expected_run_id:
        raise ContractError("applied_snapshot_run_mismatch")
    if snapshot.run_epoch_ns != expected_run_epoch_ns:
        raise ContractError("applied_snapshot_epoch_mismatch")
    return _instant_stop_ok(snapshot, config or StopEvidenceConfig())


def finish_request_payload(run_id: str, request_id: str, observed_run_epoch_ns: int, status: str, monotonic_ns: Optional[int] = None) -> dict:
    if status not in {"FINISHED", "FAILED"}:
        raise ContractError("invalid_backend_terminal_status")
    return {
        "schema_version": 1,
        "run_id": require_identifier("run_id", run_id),
        "request_id": require_identifier("request_id", request_id),
        "observed_run_epoch_ns": require_int("observed_run_epoch_ns", observed_run_epoch_ns, 1),
        "requested_at_monotonic_ns": time.monotonic_ns() if monotonic_ns is None else require_int("requested_at_monotonic_ns", monotonic_ns, 0),
        "backend_terminal_status": status,
    }


def _instant_stop_ok(snapshot: AppliedCommandSnapshot, cfg: StopEvidenceConfig) -> bool:
    if snapshot.command_stale:
        return False
    if snapshot.command_reason not in FRESH_STOP_REASONS:
        return False
    if snapshot.applied_xy_norm() > cfg.stop_command_norm:
        return False
    if abs(snapshot.applied_command[2]) > cfg.stop_command_norm:
        return False
    if snapshot.horizontal_speed_mps > cfg.stop_speed_mps:
        return False
    if abs(snapshot.yaw_rate_radps) > cfg.stop_yaw_rate_radps:
        return False
    return True


def _mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError("invalid_%s" % name)
    return value


def _cmd_tuple(name: str, value: Any) -> Tuple[float, float, float]:
    data = _mapping(name, value)
    return (require_finite("%s_vx" % name, data.get("vx")), require_finite("%s_vy" % name, data.get("vy")), require_finite("%s_wz" % name, data.get("wz")))


def _quat(name: str, value: Any) -> Tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ContractError("invalid_%s" % name)
    return tuple(require_finite("%s_%d" % (name, i), value[i]) for i in range(4))  # type: ignore[return-value]


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ContractError("invalid_%s" % name)
    return value
