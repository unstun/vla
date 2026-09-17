"""CLI helper for validating P2B adapter configuration."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict

from .applied_evidence import StopEvidenceConfig
from .contracts import GateConfig
from .pct_ipc import PctIpcClientConfig
from .scan_wire import ScanTopics


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("config_must_be_object")
    if data.get("schema") not in {"p2b_backend_adapter_config_v1", "p2b_backend_adapter_config_v2"}:
        raise ValueError("invalid_config_schema")
    return data


def render_contract(config: Dict[str, Any]) -> Dict[str, Any]:
    pct = config.get("pct_worker", {})
    gate = config.get("gate", {})
    topics = config.get("topics", {})
    applied = config.get("applied_evidence", {})
    pct_cfg = PctIpcClientConfig(
        host=pct.get("host", "127.0.0.1"),
        port=pct.get("port", 47631),
        connect_timeout_s=pct.get("connect_timeout_s", 0.20),
        response_timeout_s=pct.get("response_timeout_s", 5.0),
    )
    gate_cfg = GateConfig(
        odom_stale_s=gate.get("odom_stale_s", 0.25),
        heartbeat_stale_s=gate.get("heartbeat_stale_s", 0.20),
        still_speed_mps=gate.get("still_speed_mps", 0.05),
        still_window_s=gate.get("still_window_s", 0.50),
    )
    topic_cfg = ScanTopics(**topics)
    stop_cfg = StopEvidenceConfig(
        stop_command_norm=applied.get("stop_command_norm", 0.01),
        stop_speed_mps=applied.get("stop_speed_mps", 0.10),
        stop_yaw_rate_radps=applied.get("stop_yaw_rate_radps", 0.15),
        stop_dwell_sim_seconds=applied.get("stop_dwell_sim_seconds", 1.0),
    )
    return {
        "schema": "p2b_backend_adapter_contract_v1",
        "pct_worker": pct_cfg.__dict__,
        "gate": gate_cfg.__dict__,
        "topics": topic_cfg.as_dict(),
        "applied_evidence": stop_cfg.__dict__,
        "semantics": {
            "planner": "Native PCT runs in a separate bounded worker; unavailable worker fails explicitly.",
            "z_semantics": "PCT output z is Lite3 body reference; no display-only +0.5 m offset is added.",
            "submit_acceptance": "accepted only after SCAN consumer echoes matching command_id/route_id/generation.",
            "stop": "stopped requires controller consumer hold ack plus post-cancel runner applied-zero/stillness dwell; gate publication alone is not proof.",
            "gate": "raw SCAN cmd_vel is remapped through the generation/heartbeat/odom gate before bridge publication.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/render P2B adapter config")
    parser.add_argument("--config", required=True)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    contract = render_contract(load_config(pathlib.Path(args.config)))
    if args.print_contract:
        print(json.dumps(contract, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
