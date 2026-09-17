"""Typed wire contracts for the P2B PCT/SCAN adapter.

The production ROS messages are intentionally simple: the adapter owns the JSON
metadata schema and the native ROS nodes only receive or echo these validated
fields.  This file is the single place that decodes untrusted JSON/IPC payloads.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_ROUTE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class ContractError(ValueError):
    """Invalid adapter boundary value."""


def require_identifier(name: str, value: Any, route: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("invalid_%s" % name)
    pattern = _ROUTE_RE if route else _ID_RE
    if not pattern.match(value):
        raise ContractError("invalid_%s" % name)
    return value


def require_finite(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError("invalid_%s" % name)
    value_f = float(value)
    if not math.isfinite(value_f):
        raise ContractError("invalid_%s" % name)
    return value_f


def require_nonnegative(name: str, value: Any) -> float:
    value_f = require_finite(name, value)
    if value_f < 0.0:
        raise ContractError("invalid_%s" % name)
    return value_f


def require_int(name: str, value: Any, minimum: Optional[int] = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError("invalid_%s" % name)
    if minimum is not None and value < minimum:
        raise ContractError("invalid_%s" % name)
    return value


def require_xyz(name: str, values: Sequence[Any]) -> Tuple[float, float, float]:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ContractError("invalid_%s" % name)
    return (
        require_finite("%s_x" % name, values[0]),
        require_finite("%s_y" % name, values[1]),
        require_finite("%s_z" % name, values[2]),
    )


@dataclass(frozen=True)
class CommandIdentity:
    run_id: str
    epoch: int
    request_id: str
    goal_id: str
    route_id: str
    command_id: str
    generation: int
    map_epoch: str
    map_revision: int

    def __post_init__(self) -> None:
        require_identifier("run_id", self.run_id)
        require_int("epoch", self.epoch, 1)
        require_identifier("request_id", self.request_id)
        require_identifier("goal_id", self.goal_id)
        require_identifier("route_id", self.route_id, route=True)
        require_identifier("command_id", self.command_id)
        require_int("generation", self.generation, 1)
        require_identifier("map_epoch", self.map_epoch)
        require_int("map_revision", self.map_revision, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "epoch": self.epoch,
            "request_id": self.request_id,
            "goal_id": self.goal_id,
            "route_id": self.route_id,
            "command_id": self.command_id,
            "generation": self.generation,
            "map_epoch": self.map_epoch,
            "map_revision": self.map_revision,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CommandIdentity":
        return cls(
            run_id=require_identifier("run_id", data.get("run_id")),
            epoch=require_int("epoch", data.get("epoch"), 1),
            request_id=require_identifier("request_id", data.get("request_id")),
            goal_id=require_identifier("goal_id", data.get("goal_id")),
            route_id=require_identifier("route_id", data.get("route_id"), route=True),
            command_id=require_identifier("command_id", data.get("command_id")),
            generation=require_int("generation", data.get("generation"), 1),
            map_epoch=require_identifier("map_epoch", data.get("map_epoch")),
            map_revision=require_int("map_revision", data.get("map_revision"), 0),
        )

    def matches(self, other: "CommandIdentity") -> bool:
        return self.to_dict() == other.to_dict()


@dataclass(frozen=True)
class PlannerRequest:
    request_id: str
    goal_id: str
    start_xyz_m: Tuple[float, float, float]
    target_xyz_m: Tuple[float, float, float]
    frame_id: str
    map_epoch: str
    map_revision: int
    start_layer: Optional[int] = None
    target_layer: Optional[int] = None
    optimize: bool = False

    def __post_init__(self) -> None:
        require_identifier("request_id", self.request_id)
        require_identifier("goal_id", self.goal_id)
        require_xyz("start_xyz_m", self.start_xyz_m)
        require_xyz("target_xyz_m", self.target_xyz_m)
        require_identifier("frame_id", self.frame_id)
        require_identifier("map_epoch", self.map_epoch)
        require_int("map_revision", self.map_revision, 0)
        if self.start_layer is not None:
            require_int("start_layer", self.start_layer, 0)
        if self.target_layer is not None:
            require_int("target_layer", self.target_layer, 0)
        if not isinstance(self.optimize, bool):
            raise ContractError("invalid_optimize")

    def to_wire(self) -> Dict[str, Any]:
        return {
            "schema": "p2b_pct_plan_request_v1",
            "request_id": self.request_id,
            "goal_id": self.goal_id,
            "start_xyz_m": list(self.start_xyz_m),
            "target_xyz_m": list(self.target_xyz_m),
            "frame_id": self.frame_id,
            "map_epoch": self.map_epoch,
            "map_revision": self.map_revision,
            "start_layer": self.start_layer,
            "target_layer": self.target_layer,
            "optimize": self.optimize,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PlannerRequest":
        if data.get("schema") != "p2b_pct_plan_request_v1":
            raise ContractError("invalid_planner_request_schema")
        return cls(
            request_id=require_identifier("request_id", data.get("request_id")),
            goal_id=require_identifier("goal_id", data.get("goal_id")),
            start_xyz_m=require_xyz("start_xyz_m", data.get("start_xyz_m")),
            target_xyz_m=require_xyz("target_xyz_m", data.get("target_xyz_m")),
            frame_id=require_identifier("frame_id", data.get("frame_id")),
            map_epoch=require_identifier("map_epoch", data.get("map_epoch")),
            map_revision=require_int("map_revision", data.get("map_revision"), 0),
            start_layer=None if data.get("start_layer") is None else require_int("start_layer", data.get("start_layer"), 0),
            target_layer=None if data.get("target_layer") is None else require_int("target_layer", data.get("target_layer"), 0),
            optimize=bool(data.get("optimize", False)),
        )


@dataclass(frozen=True)
class NativeRoute:
    route_id: str
    goal_id: str
    frame_id: str
    map_epoch: str
    map_revision: int
    waypoints_m: Tuple[Tuple[float, float, float], ...]
    planner: str = "native_pct"
    z_semantics: str = "lite3_body_reference_no_display_offset"

    def __post_init__(self) -> None:
        require_identifier("route_id", self.route_id, route=True)
        require_identifier("goal_id", self.goal_id)
        require_identifier("frame_id", self.frame_id)
        require_identifier("map_epoch", self.map_epoch)
        require_int("map_revision", self.map_revision, 0)
        if not isinstance(self.waypoints_m, tuple) or len(self.waypoints_m) < 2:
            raise ContractError("invalid_waypoints")
        for point in self.waypoints_m:
            require_xyz("waypoint", point)
        if self.planner != "native_pct":
            raise ContractError("invalid_planner")
        if self.z_semantics != "lite3_body_reference_no_display_offset":
            raise ContractError("invalid_z_semantics")

    def to_wire(self) -> Dict[str, Any]:
        return {
            "schema": "p2b_native_route_v1",
            "route_id": self.route_id,
            "goal_id": self.goal_id,
            "frame_id": self.frame_id,
            "map_epoch": self.map_epoch,
            "map_revision": self.map_revision,
            "waypoints_m": [list(p) for p in self.waypoints_m],
            "planner": self.planner,
            "z_semantics": self.z_semantics,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "NativeRoute":
        if data.get("schema") != "p2b_native_route_v1":
            raise ContractError("invalid_route_schema")
        points_raw = data.get("waypoints_m")
        if not isinstance(points_raw, list):
            raise ContractError("invalid_waypoints")
        points = tuple(require_xyz("waypoint", p) for p in points_raw)
        return cls(
            route_id=require_identifier("route_id", data.get("route_id"), route=True),
            goal_id=require_identifier("goal_id", data.get("goal_id")),
            frame_id=require_identifier("frame_id", data.get("frame_id")),
            map_epoch=require_identifier("map_epoch", data.get("map_epoch")),
            map_revision=require_int("map_revision", data.get("map_revision"), 0),
            waypoints_m=points,
            planner=data.get("planner", "native_pct"),
            z_semantics=data.get("z_semantics", "lite3_body_reference_no_display_offset"),
        )


@dataclass(frozen=True)
class ScanAdmission:
    status: str
    identity: CommandIdentity
    message: str = ""
    consumer: str = "controller"
    hold_confirmed: bool = False
    measured_stillness_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "rejected", "pending", "uncertain", "stopped"}:
            raise ContractError("invalid_scan_status")
        if not isinstance(self.identity, CommandIdentity):
            raise ContractError("invalid_scan_identity")
        if not isinstance(self.message, str):
            raise ContractError("invalid_scan_message")
        require_identifier("consumer", self.consumer)
        if not isinstance(self.hold_confirmed, bool):
            raise ContractError("invalid_hold_confirmed")
        if not isinstance(self.measured_stillness_confirmed, bool):
            raise ContractError("invalid_measured_stillness_confirmed")

    def to_wire(self) -> Dict[str, Any]:
        return {
            "schema": "p2b_scan_admission_v1",
            "status": self.status,
            "identity": self.identity.to_dict(),
            "message": self.message,
            "consumer": self.consumer,
            "hold_confirmed": self.hold_confirmed,
            "measured_stillness_confirmed": self.measured_stillness_confirmed,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ScanAdmission":
        if data.get("schema") != "p2b_scan_admission_v1":
            raise ContractError("invalid_scan_admission_schema")
        identity = CommandIdentity.from_mapping(_require_mapping("identity", data.get("identity")))
        return cls(
            status=str(data.get("status")),
            identity=identity,
            message=str(data.get("message", "")),
            consumer=require_identifier("consumer", data.get("consumer", "controller")),
            hold_confirmed=bool(data.get("hold_confirmed", False)),
            measured_stillness_confirmed=bool(data.get("measured_stillness_confirmed", False)),
        )


@dataclass(frozen=True)
class MeasuredState:
    state_sequence: int
    monotonic_s: float
    position_world_m: Tuple[float, float, float]
    velocity_world_mps: Tuple[float, float, float]
    map_epoch: str
    map_revision: int
    source: str = "diagnostic_sim_truth"

    def __post_init__(self) -> None:
        require_int("state_sequence", self.state_sequence, 1)
        require_finite("monotonic_s", self.monotonic_s)
        require_xyz("position_world_m", self.position_world_m)
        require_xyz("velocity_world_mps", self.velocity_world_mps)
        require_identifier("map_epoch", self.map_epoch)
        require_int("map_revision", self.map_revision, 0)
        require_identifier("source", self.source)

    @property
    def horizontal_speed_mps(self) -> float:
        return math.hypot(self.velocity_world_mps[0], self.velocity_world_mps[1])


@dataclass(frozen=True)
class GateConfig:
    odom_stale_s: float = 0.25
    heartbeat_stale_s: float = 0.20
    still_speed_mps: float = 0.05
    still_window_s: float = 0.50

    def __post_init__(self) -> None:
        require_nonnegative("odom_stale_s", self.odom_stale_s)
        require_nonnegative("heartbeat_stale_s", self.heartbeat_stale_s)
        require_nonnegative("still_speed_mps", self.still_speed_mps)
        require_nonnegative("still_window_s", self.still_window_s)


def _require_mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError("invalid_%s" % name)
    return value


def encode_json_line(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def decode_json_line(raw: bytes) -> Dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except Exception as exc:
        raise ContractError("invalid_json_payload") from exc
    if not isinstance(data, dict):
        raise ContractError("invalid_json_object")
    return data
