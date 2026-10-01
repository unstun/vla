"""Configuration helpers for the P2B Foxy ROS/HTTP backend."""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any, Dict, Mapping, Optional


DEFAULT_CONFIG = {
    "schema": "p2b_backend_ros_config_v1",
    "run_id": "p2b-two-goal-001",
    "run_epoch_ns": 0,
    "map": {
        "epoch": "flat_nominal",
        "revision": 1,
        "frame_id": "world",
        "nominal_body_height_m": 0.35,
        "pct_layer": 1,
    },
    "http": {
        "host": "127.0.0.1",
        "port": 8765,
    },
    "pct_worker": {
        "host": "127.0.0.1",
        "port": 47631,
        "connect_timeout_s": 0.20,
        "response_timeout_s": 5.0,
        "optimize": True,
    },
    "topics": {
        "route_topic": "/p2b/route",
        "admission_topic": "/p2b/scan_admission",
        "cancel_topic": "/p2b/scan_cancel",
        "raw_cmd_topic": "/quad_0/raw_scan_cmd_vel",
        "gated_cmd_topic": "/quad_0/cmd_vel",
        "body_pose_topic": "/quad_0/body_pose",
    },
    "gate": {
        "odom_stale_s": 0.25,
        "heartbeat_stale_s": 0.20,
        "still_speed_mps": 0.05,
        "still_window_s": 0.50,
        "initial_heartbeat_grace_s": 1.0,
    },
    "applied_evidence": {
        "current_command_path": "",
        "finish_request_path": "",
        "stop_command_norm": 0.01,
        "stop_speed_mps": 0.10,
        "stop_yaw_rate_radps": 0.15,
        "stop_dwell_sim_seconds": 1.0,
    },
    "arrival": {
        "xy_tolerance_m": 0.25,
        "z_tolerance_m": 0.20,
        "monitor_period_s": 0.05,
    },
    "service": {
        "max_evidence_age_s": 10.0,
        "command_timeout_s": 45.0,
        "body_ready_timeout_s": 5.0,
    },
}


def load_runtime_config(path: pathlib.Path, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config_must_be_object")
        schema = data.get("schema")
        if schema not in {"p2b_backend_ros_config_v1", "p2b_backend_adapter_config_v2"}:
            raise ValueError("invalid_config_schema")
        _deep_update(config, _normalize_adapter_config(data))
    if overrides:
        _deep_update(config, {k: v for k, v in overrides.items() if v is not None})
    _validate_localhost(config)
    return config


def render_wire_contract(config: Mapping[str, Any]) -> Dict[str, Any]:
    topics = dict(config.get("topics", {}))
    return {
        "schema": "p2b_backend_ros_wire_contract_v1",
        "http": {
            "host": config.get("http", {}).get("host"),
            "port": config.get("http", {}).get("port"),
            "endpoints": {
                "POST /goal": "asynchronous spatial goal admission; returns a job_id and later terminal record",
                "POST /cancel": "cancel active P2A owner and require controller hold plus causal stop evidence",
                "GET /state": "readiness, measured pose, owner, jobs and terminal result records",
            },
        },
        "topics": {
            "route": topics.get("route_topic"),
            "admission": topics.get("admission_topic"),
            "cancel": topics.get("cancel_topic"),
            "raw_scan_velocity": topics.get("raw_cmd_topic"),
            "gated_bridge_velocity": topics.get("gated_cmd_topic"),
            "measured_body_pose": topics.get("body_pose_topic"),
        },
        "goal_payload": {
            "schema": "p2b_http_goal_request_v1",
            "required": ["request_id", "goal_id", "target_ground_xyz", "map_epoch", "map_revision"],
            "target_ground_xyz": "[x_m, y_m, z_m] in world frame; PCT input target, not native body-reference output",
            "frame": "world by default",
        },
        "state_payload": {
            "readiness": "separate body_pose, active owner, gate and last error fields; owner=None is not success",
            "terminal_results": "per-request arrived/cancelled/failed/rejected/ignored records with route and cause",
        },
        "semantics": {
            "planning": "PCT runs in a bounded separate worker through backend_adapter.PctIpcClient",
            "start_z": "PCT start is measured body pose minus nominal_body_height_m",
            "route_z": "native route waypoints are Lite3 body-reference z with no display +0.5 m offset",
            "admission": "route accepted only from matching P2BAdmission consumer=fsm",
            "stop": "release requires matching consumer=controller hold plus post-cancel applied-zero/stillness dwell",
            "watchdog": "before first same-generation raw heartbeat the gate publishes zero and waits within grace; it does not pre-fault a new owner",
        },
    }


def _normalize_adapter_config(data: Mapping[str, Any]) -> Dict[str, Any]:
    if data.get("schema") == "p2b_backend_ros_config_v1":
        return dict(data)
    # Accept the sibling adapter example so lead can use one config file.
    pilot = data.get("pilot_contract", {})
    normalized = {
        "schema": "p2b_backend_ros_config_v1",
        "run_id": data.get("run_id"),
        "run_epoch_ns": data.get("run_epoch_ns"),
        "http": data.get("http", {}),
        "pct_worker": data.get("pct_worker", {}),
        "topics": data.get("topics", {}),
        "gate": data.get("gate", {}),
        "applied_evidence": data.get("applied_evidence", {}),
        "map": {
            "epoch": pilot.get("map_epoch"),
            "revision": pilot.get("map_revision"),
            "frame_id": pilot.get("frame_id"),
            "nominal_body_height_m": pilot.get("measured_body_height_reference_m"),
            "pct_layer": pilot.get("pct_layer"),
        },
    }
    normalized = _drop_none(normalized)
    # Explicit null selects native automatic layers; omission keeps the default.
    if "pct_layer" in pilot:
        normalized["map"]["pct_layer"] = pilot["pct_layer"]
    return normalized


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    return value


def _deep_update(base: Dict[str, Any], incoming: Mapping[str, Any], path: tuple = ()) -> None:
    for key, value in incoming.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _deep_update(base[key], value, path + (key,))
        elif value is not None or path + (key,) == ("map", "pct_layer"):
            base[key] = value


def _validate_localhost(config: Mapping[str, Any]) -> None:
    host = str(config.get("http", {}).get("host", "127.0.0.1"))
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("http_host_must_be_loopback")

