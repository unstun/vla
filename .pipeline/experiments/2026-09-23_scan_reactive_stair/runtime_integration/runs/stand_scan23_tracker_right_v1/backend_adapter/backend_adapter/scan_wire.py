"""SCAN route submission and acknowledgement boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol

from .contracts import CommandIdentity, ContractError, NativeRoute, ScanAdmission


class ScanPort(object):
    """Minimal synchronous port implemented by ROS/Foxy node code or tests."""

    def submit_route(self, identity: CommandIdentity, route: NativeRoute) -> ScanAdmission:
        raise NotImplementedError

    def request_stop(self, identity: CommandIdentity, reason: str) -> ScanAdmission:
        raise NotImplementedError


@dataclass(frozen=True)
class ScanTopics:
    route_topic: str = "/p2b/route"
    path_topic: str = "/initial_path"
    route_meta_topic: str = "/p2b/scan_route_meta"
    admission_topic: str = "/p2b/scan_admission"
    cancel_topic: str = "/p2b/scan_cancel"
    raw_cmd_topic: str = "/quad_0/raw_scan_cmd_vel"
    gated_cmd_topic: str = "/quad_0/cmd_vel"
    body_state_topic: str = "/p2b/body_state"
    heartbeat_topic: str = "/p2b/scan_heartbeat"

    def as_dict(self) -> Dict[str, str]:
        return self.__dict__.copy()


def route_metadata(identity: CommandIdentity, route: NativeRoute) -> Dict[str, Any]:
    if identity.goal_id != route.goal_id or identity.route_id != route.route_id:
        raise ContractError("route_identity_mismatch")
    if identity.map_epoch != route.map_epoch or identity.map_revision != route.map_revision:
        raise ContractError("route_map_mismatch")
    return {
        "schema": "p2b_scan_route_meta_v1",
        "identity": identity.to_dict(),
        "route": {
            "route_id": route.route_id,
            "goal_id": route.goal_id,
            "frame_id": route.frame_id,
            "map_epoch": route.map_epoch,
            "map_revision": route.map_revision,
            "waypoint_count": len(route.waypoints_m),
            "z_semantics": route.z_semantics,
        },
    }


def encode_route_metadata(identity: CommandIdentity, route: NativeRoute) -> str:
    return json.dumps(route_metadata(identity, route), sort_keys=True, separators=(",", ":"))


def decode_admission(payload: Mapping[str, Any], expected: CommandIdentity) -> ScanAdmission:
    admission = ScanAdmission.from_mapping(payload)
    if not admission.identity.matches(expected):
        raise ContractError("scan_admission_identity_mismatch")
    return admission


def validate_stop_admission(admission: ScanAdmission, expected: CommandIdentity) -> ScanAdmission:
    if not admission.identity.matches(expected):
        raise ContractError("scan_stop_identity_mismatch")
    if admission.status == "stopped" and not admission.hold_confirmed:
        raise ContractError("scan_stop_without_consumer_hold")
    return admission
