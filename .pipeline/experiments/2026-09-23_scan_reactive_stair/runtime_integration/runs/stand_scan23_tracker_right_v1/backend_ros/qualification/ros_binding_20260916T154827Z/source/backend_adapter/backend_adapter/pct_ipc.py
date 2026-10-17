"""Bounded JSON-line IPC for the native PCT worker.

The Foxy adapter does not import PCT's Humble-built Python extension modules.
It talks to a small worker running in the existing PCT image.  A missing worker,
malformed response or timeout is an explicit planning failure; no route is
fabricated locally.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

from .contracts import ContractError, NativeRoute, PlannerRequest, decode_json_line, encode_json_line, require_nonnegative


class PlannerUnavailable(RuntimeError):
    pass


class PlannerRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class PctIpcClientConfig:
    host: str = "127.0.0.1"
    port: int = 47631
    connect_timeout_s: float = 0.20
    response_timeout_s: float = 5.0

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host:
            raise ContractError("invalid_pct_host")
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not (1 <= self.port <= 65535):
            raise ContractError("invalid_pct_port")
        require_nonnegative("connect_timeout_s", self.connect_timeout_s)
        require_nonnegative("response_timeout_s", self.response_timeout_s)


class PctIpcClient:
    def __init__(self, config: PctIpcClientConfig) -> None:
        self.config = config

    def plan(self, request: PlannerRequest) -> NativeRoute:
        payload = request.to_wire()
        try:
            with socket.create_connection((self.config.host, self.config.port), timeout=self.config.connect_timeout_s) as sock:
                sock.settimeout(self.config.response_timeout_s)
                sock.sendall(encode_json_line(payload))
                raw = _read_line(sock, max_bytes=4 * 1024 * 1024)
        except (OSError, socket.timeout) as exc:
            raise PlannerUnavailable("pct_worker_unavailable_or_timeout") from exc
        data = decode_json_line(raw)
        if data.get("schema") != "p2b_pct_plan_response_v1":
            raise PlannerUnavailable("invalid_pct_response_schema")
        status = data.get("status")
        if status == "rejected":
            raise PlannerRejected(str(data.get("message", "pct_plan_rejected")))
        if status != "ok":
            raise PlannerUnavailable("invalid_pct_response_status")
        route = NativeRoute.from_mapping(_require_mapping("route", data.get("route")))
        if route.goal_id != request.goal_id or route.frame_id != request.frame_id:
            raise PlannerUnavailable("pct_route_identity_mismatch")
        if route.map_epoch != request.map_epoch or route.map_revision != request.map_revision:
            raise PlannerUnavailable("pct_route_map_mismatch")
        return route


def make_route_id(request: PlannerRequest, waypoints: Tuple[Tuple[float, float, float], ...]) -> str:
    payload = {
        "goal_id": request.goal_id,
        "start_xyz_m": request.start_xyz_m,
        "target_xyz_m": request.target_xyz_m,
        "frame_id": request.frame_id,
        "map_epoch": request.map_epoch,
        "map_revision": request.map_revision,
        "waypoints_m": waypoints,
        "planner": "native_pct",
        "z_semantics": "lite3_body_reference_no_display_offset",
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]
    return "pct:%s:%s" % (request.goal_id, digest)


def ok_response(route: NativeRoute) -> Dict[str, Any]:
    return {"schema": "p2b_pct_plan_response_v1", "status": "ok", "route": route.to_wire()}


def rejected_response(message: str) -> Dict[str, Any]:
    return {"schema": "p2b_pct_plan_response_v1", "status": "rejected", "message": message}


def error_response(message: str) -> Dict[str, Any]:
    return {"schema": "p2b_pct_plan_response_v1", "status": "error", "message": message}


def _read_line(sock: socket.socket, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise PlannerUnavailable("pct_response_too_large")
        if b"\n" in chunk:
            joined = b"".join(chunks)
            return joined.split(b"\n", 1)[0] + b"\n"
    raise PlannerUnavailable("pct_response_missing_newline")


def _require_mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError("invalid_%s" % name)
    return value
