"""Versioned wire contract shared by the server and Lite3 client.

This module deliberately uses only the Python standard library and Python 3.8
syntax so the exact validation logic can run on both Lite3 and gpu40901.
"""

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid


SCHEMA_VERSION = 1
SOURCE_COMMIT = "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68"
CHECKPOINT_REVISION = "e36a84d4923c041149d441f93f3bdb7092bb5f07"
MODALITY = "language_only"
ACTUATION_ENABLED = False
METRIC_WAYPOINT_SPACING_M = 0.1
METRIC_SCALE_STATUS = "uncalibrated_for_lite3"
MAX_JPEG_BYTES = 5 * 1024 * 1024
MAX_INSTRUCTION_BYTES = 256
MAX_RESPONSE_BYTES = 1024 * 1024
REQUEST_IO_TIMEOUT_SECONDS = 30.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


class ProtocolError(ValueError):
    """A request or response violates the receive-only wire contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolError("value is not canonical JSON: %s" % exc)
    return (text + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_request_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError):
        raise ProtocolError("request_id must be a UUID")
    canonical = str(parsed)
    if value.lower() != canonical:
        raise ProtocolError("request_id must use canonical UUID form")
    return canonical


def validate_capture_utc(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtocolError("capture_utc must be an ISO-8601 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise ProtocolError("capture_utc must be an ISO-8601 UTC timestamp")
    return value


def validate_instruction(value: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError("instruction must be text")
    if not value.strip():
        raise ProtocolError("instruction must not be empty")
    if "\x00" in value:
        raise ProtocolError("instruction must not contain NUL")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ProtocolError("instruction must be valid UTF-8")
    if len(encoded) > MAX_INSTRUCTION_BYTES:
        raise ProtocolError("instruction exceeds %d UTF-8 bytes" % MAX_INSTRUCTION_BYTES)
    return value


def validate_sha256(value: str, label: str = "sha256") -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ProtocolError("%s must be 64 lowercase hexadecimal characters" % label)
    return value


def jpeg_dimensions(data: bytes) -> Tuple[int, int]:
    """Return JPEG width and height without a third-party decoder."""

    if not isinstance(data, bytes):
        raise ProtocolError("JPEG body must be bytes")
    if len(data) < 4 or data[:2] != b"\xff\xd8" or data[-2:] != b"\xff\xd9":
        raise ProtocolError("body is not a complete JPEG")
    if len(data) > MAX_JPEG_BYTES:
        raise ProtocolError("JPEG exceeds %d bytes" % MAX_JPEG_BYTES)

    position = 2
    size = len(data)
    while position + 1 < size:
        if data[position] != 0xFF:
            position += 1
            continue
        while position < size and data[position] == 0xFF:
            position += 1
        if position >= size:
            break
        marker = data[position]
        position += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if position + 2 > size:
            break
        segment_length = int.from_bytes(data[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > size:
            raise ProtocolError("JPEG contains an invalid segment length")
        if marker in _SOF_MARKERS:
            if segment_length < 7:
                raise ProtocolError("JPEG SOF segment is too short")
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            if width <= 0 or height <= 0:
                raise ProtocolError("JPEG dimensions must be positive")
            return width, height
        position += segment_length
    raise ProtocolError("JPEG has no supported start-of-frame marker")


def validate_jpeg(data: bytes, expected_sha256: Optional[str] = None) -> Tuple[int, int, str]:
    width, height = jpeg_dimensions(data)
    digest = sha256_bytes(data)
    if expected_sha256 is not None:
        validate_sha256(expected_sha256, "image_sha256")
        if digest != expected_sha256:
            raise ProtocolError("image_sha256 does not match the JPEG body")
    return width, height, digest


def _validate_trajectory(value: Any, label: str) -> List[List[float]]:
    if not isinstance(value, list) or len(value) != 8:
        raise ProtocolError("%s must contain exactly 8 waypoints" % label)
    normalized = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 4:
            raise ProtocolError("%s[%d] must contain exactly 4 values" % (label, row_index))
        values = []
        for column_index, item in enumerate(row):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ProtocolError(
                    "%s[%d][%d] must be numeric" % (label, row_index, column_index)
                )
            number = float(item)
            if not math.isfinite(number):
                raise ProtocolError(
                    "%s[%d][%d] must be finite" % (label, row_index, column_index)
                )
            values.append(number)
        normalized.append(values)
    return normalized


def metric_trajectory(trajectory_normalized: List[List[float]]) -> List[List[float]]:
    trajectory = _validate_trajectory(trajectory_normalized, "trajectory_normalized")
    return [
        [
            row[0] * METRIC_WAYPOINT_SPACING_M,
            row[1] * METRIC_WAYPOINT_SPACING_M,
            row[2],
            row[3],
        ]
        for row in trajectory
    ]


def make_success_response(
    request_id: str,
    trajectory_normalized: List[List[float]],
    inference_ms: float,
    source_commit: str = SOURCE_COMMIT,
    checkpoint_revision: str = CHECKPOINT_REVISION,
) -> Dict[str, Any]:
    request_id = validate_request_id(request_id)
    trajectory = _validate_trajectory(trajectory_normalized, "trajectory_normalized")
    inference_ms = float(inference_ms)
    if not math.isfinite(inference_ms) or inference_ms < 0:
        raise ProtocolError("inference_ms must be finite and non-negative")
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "source_commit": source_commit,
        "checkpoint_revision": checkpoint_revision,
        "modality": MODALITY,
        "trajectory_normalized": trajectory,
        "trajectory_metric_upstream_default": metric_trajectory(trajectory),
        "metric_waypoint_spacing_m": METRIC_WAYPOINT_SPACING_M,
        "metric_scale_status": METRIC_SCALE_STATUS,
        "inference_ms": inference_ms,
        "actuation_enabled": ACTUATION_ENABLED,
    }


def validate_success_response(
    value: Any,
    expected_request_id: str,
    expected_source_commit: str = SOURCE_COMMIT,
    expected_checkpoint_revision: str = CHECKPOINT_REVISION,
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError("response must be a JSON object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ProtocolError("response schema_version mismatch")
    if value.get("request_id") != validate_request_id(expected_request_id):
        raise ProtocolError("response request_id mismatch")
    if value.get("source_commit") != expected_source_commit:
        raise ProtocolError("response source_commit mismatch")
    if value.get("checkpoint_revision") != expected_checkpoint_revision:
        raise ProtocolError("response checkpoint_revision mismatch")
    if value.get("modality") != MODALITY:
        raise ProtocolError("response modality mismatch")
    if value.get("actuation_enabled") is not False:
        raise ProtocolError("response must have actuation_enabled=false")
    if value.get("metric_scale_status") != METRIC_SCALE_STATUS:
        raise ProtocolError("response metric_scale_status mismatch")
    if value.get("metric_waypoint_spacing_m") != METRIC_WAYPOINT_SPACING_M:
        raise ProtocolError("response metric_waypoint_spacing_m mismatch")

    trajectory = _validate_trajectory(
        value.get("trajectory_normalized"), "trajectory_normalized"
    )
    metric = _validate_trajectory(
        value.get("trajectory_metric_upstream_default"),
        "trajectory_metric_upstream_default",
    )
    expected_metric = metric_trajectory(trajectory)
    for row_index, (actual_row, expected_row) in enumerate(zip(metric, expected_metric)):
        for column_index, (actual, expected) in enumerate(zip(actual_row, expected_row)):
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9):
                raise ProtocolError(
                    "metric trajectory mismatch at [%d][%d]" % (row_index, column_index)
                )
    inference_ms = value.get("inference_ms")
    if isinstance(inference_ms, bool) or not isinstance(inference_ms, (int, float)):
        raise ProtocolError("inference_ms must be numeric")
    if not math.isfinite(float(inference_ms)) or float(inference_ms) < 0:
        raise ProtocolError("inference_ms must be finite and non-negative")

    normalized = dict(value)
    normalized["trajectory_normalized"] = trajectory
    normalized["trajectory_metric_upstream_default"] = metric
    normalized["inference_ms"] = float(inference_ms)
    return normalized
