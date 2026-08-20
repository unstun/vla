"""Strict, bounded JSON protocol for high-level Lite3 body commands."""

from __future__ import annotations

import dataclasses
import json
import math
from typing import Any, Dict, Optional

SCHEMA = "tic-vla-lite3.body-command.v1"
MAX_DATAGRAM_BYTES = 1024
_FIELDS = frozenset(
    {
        "schema",
        "session_id",
        "plan_seq",
        "source_frame_seq",
        "reasoning_generation",
        "mode",
        "valid",
        "vx_mps",
        "vy_mps",
        "wz_radps",
    }
)


class ProtocolError(ValueError):
    """A datagram violates the body-command wire contract."""


@dataclasses.dataclass(frozen=True)
class BodyCommand:
    session_id: str
    plan_seq: int
    source_frame_seq: int
    reasoning_generation: int
    mode: str
    valid: bool
    vx_mps: float
    vy_mps: float
    wz_radps: float
    schema: str = SCHEMA


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_obj(value: Any, expected_session: Optional[str] = None) -> BodyCommand:
    if not isinstance(value, dict) or frozenset(value) != _FIELDS:
        raise ProtocolError("field_set")
    if value["schema"] != SCHEMA:
        raise ProtocolError("schema")
    session = value["session_id"]
    if not isinstance(session, str) or not session or len(session) > 128:
        raise ProtocolError("session_type")
    if expected_session is not None and session != expected_session:
        raise ProtocolError("session")
    for key in ("plan_seq", "source_frame_seq", "reasoning_generation"):
        if not _is_int(value[key]) or value[key] > (2**64 - 1):
            raise ProtocolError(key)
    if value["mode"] not in ("shadow", "active"):
        raise ProtocolError("mode")
    if type(value["valid"]) is not bool:
        raise ProtocolError("valid")
    numeric: Dict[str, float] = {}
    for key in ("vx_mps", "vy_mps", "wz_radps"):
        raw = value[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ProtocolError(key)
        numeric[key] = float(raw)
        if not math.isfinite(numeric[key]):
            raise ProtocolError(key)
    if not 0.0 <= numeric["vx_mps"] <= 0.30:
        raise ProtocolError("vx_range")
    if numeric["vy_mps"] != 0.0:
        raise ProtocolError("vy_range")
    if abs(numeric["wz_radps"]) > 0.20:
        raise ProtocolError("wz_range")
    return BodyCommand(
        session_id=session,
        plan_seq=value["plan_seq"],
        source_frame_seq=value["source_frame_seq"],
        reasoning_generation=value["reasoning_generation"],
        mode=value["mode"],
        valid=value["valid"],
        vx_mps=numeric["vx_mps"],
        vy_mps=numeric["vy_mps"],
        wz_radps=numeric["wz_radps"],
    )


def encode_command(command: BodyCommand) -> bytes:
    payload = dataclasses.asdict(command)
    validated = _validate_obj(payload)
    data = json.dumps(dataclasses.asdict(validated), separators=(",", ":"),
                      sort_keys=True, allow_nan=False).encode("utf-8")
    if len(data) > MAX_DATAGRAM_BYTES:
        raise ProtocolError("oversized")
    return data


def decode_command(data: bytes, expected_session: Optional[str] = None) -> BodyCommand:
    if not isinstance(data, bytes) or not data or len(data) > MAX_DATAGRAM_BYTES:
        raise ProtocolError("size")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("json") from exc
    return _validate_obj(value, expected_session)
