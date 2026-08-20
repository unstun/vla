"""Strict Orin client for the task-owned Xavier observation bridge."""

from __future__ import annotations

import dataclasses
import json
import math
import socket
import struct
import time
from typing import BinaryIO, Optional, Tuple

from .frame_source import FrameSample
from .state_source import RobotStateSample

MAX_METADATA_BYTES = 4096
MAX_JPEG_BYTES = 2 * 1024 * 1024
_FIELDS = {
    "schema", "frame_sequence", "frame_callback_monotonic_s", "frame_source_age_s",
    "state_sequence", "state_callback_monotonic_s", "state_source_age_s",
    "width", "height", "encoding", "frame_id",
    "child_frame_id", "x_m", "y_m", "z_m", "qx", "qy", "qz", "qw",
    "vx_mps", "vy_mps", "wz_radps",
}


@dataclasses.dataclass(frozen=True)
class ObservationSample:
    frame: FrameSample
    state: RobotStateSample
    received_monotonic_s: float
    frame_source_age_s: float
    state_source_age_s: float


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError("observation_bridge_closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def decode_record(stream: BinaryIO,
                  received_monotonic_s: Optional[float] = None) -> ObservationSample:
    metadata_size = struct.unpack("!I", _read_exact(stream, 4))[0]
    if metadata_size == 0 or metadata_size > MAX_METADATA_BYTES:
        raise ValueError("metadata_size")
    metadata = json.loads(_read_exact(stream, metadata_size).decode("utf-8"))
    jpeg_size = struct.unpack("!I", _read_exact(stream, 4))[0]
    if jpeg_size == 0 or jpeg_size > MAX_JPEG_BYTES:
        raise ValueError("jpeg_size")
    jpeg = _read_exact(stream, jpeg_size)
    if received_monotonic_s is None:
        # Stamp after the complete record has arrived.  Stamping before the
        # blocking read would make a slow transfer appear newer than it is.
        received_monotonic_s = time.monotonic()
    if not isinstance(metadata, dict) or set(metadata) != _FIELDS:
        raise ValueError("metadata_fields")
    if metadata["schema"] != "tic-vla-lite3.observation.v1" or metadata["encoding"] != "jpeg-bgr8":
        raise ValueError("metadata_schema")
    for key in ("frame_sequence", "state_sequence", "width", "height"):
        if not isinstance(metadata[key], int) or isinstance(metadata[key], bool) or metadata[key] < 0:
            raise ValueError(key)
    numeric = ("frame_callback_monotonic_s", "frame_source_age_s",
               "state_callback_monotonic_s", "state_source_age_s",
               "x_m", "y_m", "z_m", "qx", "qy", "qz", "qw",
               "vx_mps", "vy_mps", "wz_radps")
    if not all(isinstance(metadata[key], (int, float)) and not isinstance(metadata[key], bool)
               and math.isfinite(float(metadata[key])) for key in numeric):
        raise ValueError("metadata_nonfinite")
    # Cross-host source monotonic values are diagnostic only. Safety timestamps
    # are the Orin-local receipt time supplied by the caller.
    frame = FrameSample(metadata["frame_sequence"], received_monotonic_s,
                        metadata["width"], metadata["height"], jpeg)
    state = RobotStateSample(metadata["state_sequence"], received_monotonic_s,
                             float(metadata["vx_mps"]), float(metadata["vy_mps"]),
                             float(metadata["wz_radps"]), float(metadata["x_m"]),
                             float(metadata["y_m"]))
    if metadata["frame_source_age_s"] < 0.0 or metadata["state_source_age_s"] < 0.0:
        raise ValueError("negative_source_age")
    return ObservationSample(frame, state, received_monotonic_s,
                             float(metadata["frame_source_age_s"]),
                             float(metadata["state_source_age_s"]))


class LiveBridgeClient:
    def __init__(self, host: str = "192.168.1.103", port: int = 45451,
                 timeout_s: float = 2.0) -> None:
        self._socket = socket.create_connection((host, port), timeout=timeout_s)
        self._socket.settimeout(timeout_s)
        self._stream = self._socket.makefile("rb")

    def receive(self) -> ObservationSample:
        self._socket.sendall(b"\x01")
        return decode_record(self._stream)

    def close(self) -> None:
        self._stream.close()
        self._socket.close()

    def __enter__(self) -> "LiveBridgeClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
