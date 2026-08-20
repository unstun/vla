"""Strict loader for the reviewed TIC-VLA runtime configuration."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Optional, Tuple

import yaml

from .protocol import MAX_DATAGRAM_BYTES, SCHEMA
from .trajectory_adapter import AdapterConfig


@dataclasses.dataclass(frozen=True)
class ShadowConfig:
    mode: str
    adapter: AdapterConfig
    delayed_context_s: Tuple[float, float, float, float]
    history_tolerance_s: float
    max_frame_age_s: float
    max_state_age_s: float


def _keys(value: object, expected: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(name + "_fields")
    return value


def _number(value: object, name: str, *, minimum: float,
            maximum: Optional[float] = None,
            minimum_inclusive: bool = False) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(float(value))):
        raise ValueError(name)
    result = float(value)
    minimum_ok = result >= minimum if minimum_inclusive else result > minimum
    if not minimum_ok or (maximum is not None and result > maximum):
        raise ValueError(name)
    return result


def load_config(path: Path) -> ShadowConfig:
    root = _keys(yaml.safe_load(path.read_text(encoding="utf-8")), {
        "mode", "protocol", "limits", "trajectory", "observation", "live_source"
    }, "root")
    if root["mode"] not in ("shadow", "active"):
        raise ValueError("mode")
    protocol = _keys(root["protocol"], {
        "schema", "max_datagram_bytes", "vla_timeout_ms"
    }, "protocol")
    if protocol != {"schema": SCHEMA, "max_datagram_bytes": MAX_DATAGRAM_BYTES,
                    "vla_timeout_ms": 500}:
        raise ValueError("protocol_contract")
    limits = _keys(root["limits"], {
        "vx_min_mps", "vx_max_mps", "vy_mps", "wz_abs_max_radps",
        "vx_slew_mps2", "wz_slew_radps2"
    }, "limits")
    vx_min = _number(limits["vx_min_mps"], "vx_min_mps", minimum=0.0,
                     maximum=0.0, minimum_inclusive=True)
    vy_fixed = _number(limits["vy_mps"], "vy_mps", minimum=0.0,
                       maximum=0.0, minimum_inclusive=True)
    if vx_min != 0.0 or vy_fixed != 0.0:
        raise ValueError("fixed_velocity_limits")
    trajectory = _keys(root["trajectory"], {
        "points", "lookahead_m", "min_path_m", "max_segment_m", "max_path_m",
        "max_age_s", "yaw_filter_alpha", "curvature_epsilon",
        "curvature_speed_gain", "yaw_feedforward_gain", "yaw_feedback_gain"
    }, "trajectory")
    if trajectory["points"] != 30:
        raise ValueError("trajectory_points")
    observation = _keys(root["observation"], {
        "delayed_context_s", "history_tolerance_s", "max_frame_age_s",
        "max_state_age_s"
    }, "observation")
    _keys(root["live_source"], {
        "host", "allowed_orin_source_as_seen_by_xavier", "rgb_topic", "state_topic",
        "width", "height", "orientation"
    }, "live_source")
    delays_raw = observation["delayed_context_s"]
    if not isinstance(delays_raw, list):
        raise ValueError("delayed_context")
    delays = tuple(_number(value, "delayed_context", minimum=0.0,
                           maximum=9.0, minimum_inclusive=True)
                   for value in delays_raw)
    if len(delays) != 4 or delays != (9.0, 6.0, 3.0, 0.0):
        raise ValueError("delayed_context")
    adapter = AdapterConfig(
        lookahead_m=_number(trajectory["lookahead_m"], "lookahead_m", minimum=0.0),
        min_path_m=_number(trajectory["min_path_m"], "min_path_m", minimum=0.0),
        max_segment_m=_number(trajectory["max_segment_m"], "max_segment_m", minimum=0.0),
        max_path_m=_number(trajectory["max_path_m"], "max_path_m", minimum=0.0),
        max_age_s=_number(trajectory["max_age_s"], "max_age_s", minimum=0.0),
        yaw_filter_alpha=_number(trajectory["yaw_filter_alpha"], "yaw_filter_alpha",
                                 minimum=0.0, maximum=1.0, minimum_inclusive=True),
        curvature_epsilon=_number(trajectory["curvature_epsilon"],
                                  "curvature_epsilon", minimum=0.0),
        curvature_speed_gain=_number(trajectory["curvature_speed_gain"],
                                     "curvature_speed_gain", minimum=0.0,
                                     minimum_inclusive=True),
        yaw_feedforward_gain=_number(trajectory["yaw_feedforward_gain"],
                                     "yaw_feedforward_gain", minimum=0.0,
                                     minimum_inclusive=True),
        yaw_feedback_gain=_number(trajectory["yaw_feedback_gain"],
                                  "yaw_feedback_gain", minimum=0.0,
                                  minimum_inclusive=True),
        vx_max_mps=_number(limits["vx_max_mps"], "vx_max_mps", minimum=0.0,
                           maximum=0.30),
        wz_abs_max_radps=_number(limits["wz_abs_max_radps"], "wz_abs_max_radps",
                                 minimum=0.0, maximum=0.20),
        vx_slew_mps2=_number(limits["vx_slew_mps2"], "vx_slew_mps2", minimum=0.0),
        wz_slew_radps2=_number(limits["wz_slew_radps2"], "wz_slew_radps2", minimum=0.0),
    )
    if not (adapter.min_path_m <= adapter.lookahead_m <= adapter.max_path_m):
        raise ValueError("trajectory_order")
    result = ShadowConfig(
        str(root["mode"]), adapter, delays,
        _number(observation["history_tolerance_s"], "history_tolerance_s", minimum=0.0),
        _number(observation["max_frame_age_s"], "max_frame_age_s", minimum=0.0),
        _number(observation["max_state_age_s"], "max_state_age_s", minimum=0.0),
    )
    return result


def load_shadow_config(path: Path) -> ShadowConfig:
    """Compatibility entry point retained for existing scripts."""
    return load_config(path)
