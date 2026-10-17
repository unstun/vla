"""Local-only TCP roles built on the shared v1 frame decoder."""

import collections
from dataclasses import dataclass
import select
import socket
import threading
import time
from typing import Callable, Deque, Dict, List, Optional, Tuple

from .command_state import CommandLimits, CommandSnapshot, LatestCommandState
from .protocol import (
    CommandV1,
    Frame,
    MessageType,
    ProtocolError,
    decode_command_payload,
    decode_frame,
    encode_command_payload,
    encode_frame,
    recv_frame,
    send_frame,
)


DEFAULT_TELEMETRY_PORT = 46000
DEFAULT_COMMAND_PORT = 46001

# Telemetry classes for the optional priority sender. Control state and status
# are small and latency-critical; sensor frames are large and may wait.
PRIORITY_HIGH = "high"
PRIORITY_LOW = "low"
_HIGH_PRIORITY_MESSAGE_TYPES = frozenset(
    {
        MessageType.BODY_STATE_V1,
        MessageType.BODY_STATE_V2,
        MessageType.STATUS_V1,
        MessageType.HEARTBEAT_V1,
    }
)


@dataclass(frozen=True)
class TransportStats:
    accepted_connections: int
    reconnects: int
    frames_received: int
    frames_sent: int
    protocol_errors: int
    io_errors: int
    last_protocol_error: Optional[str]
    coalesced_frames: int


class _StatsState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.accepted_connections = 0
        self.reconnects = 0
        self.frames_received = 0
        self.frames_sent = 0
        self.protocol_errors = 0
        self.io_errors = 0
        self.last_protocol_error = None  # type: Optional[str]
        self.coalesced_frames = 0

    def increment(self, field: str, count: int = 1) -> None:
        with self.lock:
            setattr(self, field, getattr(self, field) + count)

    def record_protocol_error(self, error: object) -> None:
        with self.lock:
            self.protocol_errors += 1
            self.last_protocol_error = str(error)

    def snapshot(self) -> TransportStats:
        with self.lock:
            return TransportStats(
                accepted_connections=self.accepted_connections,
                reconnects=self.reconnects,
                frames_received=self.frames_received,
                frames_sent=self.frames_sent,
                protocol_errors=self.protocol_errors,
                io_errors=self.io_errors,
                last_protocol_error=self.last_protocol_error,
                coalesced_frames=self.coalesced_frames,
            )


def _configure_connection(connection: socket.socket, timeout_seconds: float) -> None:
    connection.settimeout(timeout_seconds)
    connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


class TelemetryPublisherServer:
    """Isaac-side single-client server for sensor and status frames."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_TELEMETRY_PORT,
        io_timeout_seconds: float = 0.2,
        priority_send: bool = False,
        high_queue_depth: int = 256,
        low_queue_depth: int = 8,
    ) -> None:
        self._host = host
        self._port = port
        self._io_timeout_seconds = io_timeout_seconds
        self._listener = None  # type: Optional[socket.socket]
        self._connection = None  # type: Optional[socket.socket]
        self._connection_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._accept_thread = None  # type: Optional[threading.Thread]
        self._stats = _StatsState()
        # Optional asynchronous priority sender. Off by default, so every
        # existing caller keeps the original synchronous sendall path and the
        # exact same return semantics.
        if high_queue_depth <= 0 or low_queue_depth <= 0:
            raise ValueError("queue depths must be positive")
        self._priority_send = bool(priority_send)
        self._high_queue_depth = int(high_queue_depth)
        self._low_queue_depth = int(low_queue_depth)
        self._queue_lock = threading.Lock()
        self._queue_ready = threading.Condition(self._queue_lock)
        self._high_queue = collections.deque()  # type: Deque[Tuple[int, bytes]]
        self._low_queue = collections.deque()  # type: Deque[Tuple[int, bytes]]
        self._sender_thread = None  # type: Optional[threading.Thread]
        self._in_flight = 0
        # Priority scheduling may overtake already-numbered producer frames.
        # The single sender owns wire order; payload sample IDs remain intact.
        self._wire_sequence = 0
        self._queue_metrics = {
            "high_enqueued": 0,
            "high_sent": 0,
            "high_overflow": 0,
            "low_enqueued": 0,
            "low_sent": 0,
            "low_dropped_oldest": 0,
            "send_failures": 0,
            "max_high_queue_depth": 0,
            "max_low_queue_depth": 0,
            "max_high_latency_ns": 0,
            "max_low_latency_ns": 0,
            "total_high_latency_ns": 0,
            "total_low_latency_ns": 0,
            "low_frames_overtaken_by_high": 0,
        }

    @property
    def endpoint(self) -> Tuple[str, int]:
        if self._listener is None:
            raise RuntimeError("telemetry server is not started")
        host, port = self._listener.getsockname()[:2]
        return str(host), int(port)

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError("telemetry server is already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._host, self._port))
        listener.listen(1)
        listener.settimeout(self._io_timeout_seconds)
        self._listener = listener
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="lite3-telemetry-accept", daemon=True
        )
        self._accept_thread.start()
        if self._priority_send:
            self._sender_thread = threading.Thread(
                target=self._sender_loop, name="lite3-telemetry-sender", daemon=True
            )
            self._sender_thread.start()

    def _accept_loop(self) -> None:
        assert self._listener is not None
        while not self._stop_event.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if not self._stop_event.is_set():
                    self._stats.increment("io_errors")
                break
            _configure_connection(connection, self._io_timeout_seconds)
            with self._connection_lock:
                previous = self._connection
                self._connection = connection
            if previous is not None:
                previous.close()
                self._stats.increment("reconnects")
            self._stats.increment("accepted_connections")

    def publish(self, frame_bytes: bytes) -> bool:
        frame = decode_frame(frame_bytes)
        if frame.header.message_type not in (
            MessageType.SENSOR_FRAME_V1,
            MessageType.SENSOR_FRAME_DUAL_CLOUD_V1,
            MessageType.STATUS_V1,
            MessageType.HEARTBEAT_V1,
            MessageType.JOINT_STATE_V1,
            MessageType.BODY_STATE_V1,
            MessageType.BODY_STATE_V2,
        ):
            raise ProtocolError("telemetry stream received a command frame")
        if self._priority_send:
            return self._enqueue(frame.header.message_type, frame_bytes)
        with self._connection_lock:
            connection = self._connection
        if connection is None:
            return False
        return self._send_now(connection, frame_bytes)

    def _send_now(self, connection: socket.socket, frame_bytes: bytes) -> bool:
        try:
            send_frame(connection, frame_bytes)
        except (OSError, EOFError):
            self._stats.increment("io_errors")
            with self._connection_lock:
                if self._connection is connection:
                    self._connection = None
            connection.close()
            return False
        self._stats.increment("frames_sent")
        return True

    def _enqueue(self, message_type: MessageType, frame_bytes: bytes) -> bool:
        """Queue one frame by class. Returns False only when it is not queued.

        A high-priority frame is never dropped to make room: overflow there
        means the sender has genuinely stopped, which is a reportable fault, not
        something to hide. A low-priority frame drops the oldest entry, because
        an obsolete point cloud is worth less than a current one.
        """
        high = message_type in _HIGH_PRIORITY_MESSAGE_TYPES
        stamped = (time.monotonic_ns(), frame_bytes)
        with self._queue_ready:
            if high:
                if len(self._high_queue) >= self._high_queue_depth:
                    self._queue_metrics["high_overflow"] += 1
                    return False
                self._high_queue.append(stamped)
                self._queue_metrics["high_enqueued"] += 1
                self._queue_metrics["max_high_queue_depth"] = max(
                    self._queue_metrics["max_high_queue_depth"], len(self._high_queue)
                )
                # Every low frame still waiting is now behind this state frame.
                self._queue_metrics["low_frames_overtaken_by_high"] += len(self._low_queue)
            else:
                while len(self._low_queue) >= self._low_queue_depth:
                    self._low_queue.popleft()
                    self._queue_metrics["low_dropped_oldest"] += 1
                self._low_queue.append(stamped)
                self._queue_metrics["low_enqueued"] += 1
                self._queue_metrics["max_low_queue_depth"] = max(
                    self._queue_metrics["max_low_queue_depth"], len(self._low_queue)
                )
            self._queue_ready.notify()
        return True

    def _sender_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._queue_ready:
                while (
                    not self._high_queue
                    and not self._low_queue
                    and not self._stop_event.is_set()
                ):
                    self._queue_ready.wait(0.05)
                if self._stop_event.is_set() and not self._high_queue and not self._low_queue:
                    return
                # The high queue is drained completely before a single low frame
                # is written, so a queued point cloud can never delay a control
                # state frame by more than the one frame already in flight.
                if self._high_queue:
                    enqueued_ns, frame_bytes = self._high_queue.popleft()
                    priority = PRIORITY_HIGH
                elif self._low_queue:
                    enqueued_ns, frame_bytes = self._low_queue.popleft()
                    priority = PRIORITY_LOW
                else:
                    continue
                self._in_flight += 1
            with self._connection_lock:
                connection = self._connection
            sent = False
            if connection is not None:
                frame = decode_frame(frame_bytes)
                self._wire_sequence += 1
                frame_bytes = encode_frame(
                    frame.header.message_type,
                    self._wire_sequence,
                    frame.header.timestamp_ns,
                    frame.payload,
                    flags=frame.header.flags,
                )
                sent = self._send_now(connection, frame_bytes)
            latency_ns = max(0, time.monotonic_ns() - enqueued_ns)
            with self._queue_ready:
                self._in_flight -= 1
                if sent:
                    self._queue_metrics[priority + "_sent"] += 1
                else:
                    self._queue_metrics["send_failures"] += 1
                key = "max_" + priority + "_latency_ns"
                self._queue_metrics[key] = max(self._queue_metrics[key], latency_ns)
                self._queue_metrics["total_" + priority + "_latency_ns"] += latency_ns

    def drain(self, timeout_seconds: float = 5.0) -> bool:
        """Block until both queues are empty, or the timeout expires."""
        if not self._priority_send:
            return True
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() < deadline:
            with self._queue_ready:
                if not self._high_queue and not self._low_queue and self._in_flight == 0:
                    return True
            time.sleep(0.005)
        with self._queue_ready:
            return (
                not self._high_queue and not self._low_queue and self._in_flight == 0
            )

    def queue_metrics(self) -> Dict[str, int]:
        """Measured behaviour of the priority sender, for the run record."""
        with self._queue_ready:
            metrics = dict(self._queue_metrics)
        metrics["priority_send_enabled"] = int(self._priority_send)
        metrics["wire_sequence_owned_by_sender"] = int(self._priority_send)
        metrics["last_assigned_wire_sequence"] = self._wire_sequence
        metrics["high_queue_depth_limit"] = self._high_queue_depth
        metrics["low_queue_depth_limit"] = self._low_queue_depth
        for priority in (PRIORITY_HIGH, PRIORITY_LOW):
            sent = metrics[priority + "_sent"]
            total = metrics["total_" + priority + "_latency_ns"]
            metrics["mean_" + priority + "_latency_ns"] = int(total / sent) if sent else 0
        return metrics

    def stats(self) -> TransportStats:
        return self._stats.snapshot()

    def stop(self) -> None:
        self._stop_event.set()
        if self._sender_thread is not None:
            with self._queue_ready:
                self._queue_ready.notify_all()
            self._sender_thread.join(timeout=2.0)
            self._sender_thread = None
        with self._connection_lock:
            connection = self._connection
            self._connection = None
        if connection is not None:
            connection.close()
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=1.0)
            self._accept_thread = None


class CommandReceiverServer:
    """Isaac-side command receiver with one shared fail-closed state owner."""

    def __init__(
        self,
        command_state: LatestCommandState,
        host: str = "127.0.0.1",
        port: int = DEFAULT_COMMAND_PORT,
        io_timeout_seconds: float = 0.2,
        on_update: Optional[Callable[[CommandSnapshot], None]] = None,
    ) -> None:
        self._command_state = command_state
        self._host = host
        self._port = port
        self._io_timeout_seconds = io_timeout_seconds
        self._on_update = on_update
        self._listener = None  # type: Optional[socket.socket]
        self._connection = None  # type: Optional[socket.socket]
        self._connection_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None  # type: Optional[threading.Thread]
        self._stats = _StatsState()

    @property
    def endpoint(self) -> Tuple[str, int]:
        if self._listener is None:
            raise RuntimeError("command server is not started")
        host, port = self._listener.getsockname()[:2]
        return str(host), int(port)

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError("command server is already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._host, self._port))
        listener.listen(1)
        listener.settimeout(self._io_timeout_seconds)
        self._listener = listener
        self._thread = threading.Thread(
            target=self._run, name="lite3-command-receiver", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        assert self._listener is not None
        has_accepted = False
        while not self._stop_event.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if not self._stop_event.is_set():
                    self._stats.increment("io_errors")
                break
            _configure_connection(connection, self._io_timeout_seconds)
            with self._connection_lock:
                self._connection = connection
            self._stats.increment("accepted_connections")
            if has_accepted:
                self._stats.increment("reconnects")
            has_accepted = True
            self._receive_connection(connection)
            with self._connection_lock:
                if self._connection is connection:
                    self._connection = None
            connection.close()
            if not self._stop_event.is_set():
                self._command_state.mark_disconnected()

    def _receive_connection(self, connection: socket.socket) -> None:
        while not self._stop_event.is_set():
            try:
                frames = [recv_frame(connection)]
                while len(frames) < 256:
                    readable, _, _ = select.select([connection], [], [], 0.0)
                    if not readable:
                        break
                    frames.append(recv_frame(connection))
            except socket.timeout:
                continue
            except ProtocolError as error:
                self._stats.record_protocol_error(error)
                return
            except (EOFError, OSError, ValueError):
                # stop() closes the active socket from the owner thread.  A
                # concurrent select() can then observe fileno() == -1 and
                # raises ValueError instead of OSError; treat that close race
                # exactly like EOF so shutdown cannot strand the outer run.
                return
            updates = []
            try:
                received_monotonic_ns = time.monotonic_ns()
                for frame in frames:
                    if frame.header.message_type == MessageType.HEARTBEAT_V1:
                        if frame.payload:
                            raise ProtocolError(
                                "heartbeat frame must have an empty payload"
                            )
                        continue
                    if frame.header.message_type != MessageType.CMD_VEL_V1:
                        raise ProtocolError(
                            "command stream received a non-command frame"
                        )
                    updates.append(
                        (
                            decode_command_payload(frame.payload),
                            frame.header.sequence,
                            frame.header.timestamp_ns,
                            received_monotonic_ns,
                        )
                    )
                snapshot = (
                    None
                    if not updates
                    else self._command_state.update_batch(updates)
                )
            except ProtocolError as error:
                self._stats.record_protocol_error(error)
                return
            self._stats.increment("frames_received", len(frames))
            self._stats.increment("coalesced_frames", max(0, len(updates) - 1))
            if snapshot is not None and self._on_update is not None:
                self._on_update(snapshot)

    def snapshot(self, now_monotonic_ns: Optional[int] = None) -> CommandSnapshot:
        now = time.monotonic_ns() if now_monotonic_ns is None else now_monotonic_ns
        return self._command_state.snapshot(now)

    def stats(self) -> TransportStats:
        return self._stats.snapshot()

    def stop(self) -> None:
        self._stop_event.set()
        with self._connection_lock:
            connection = self._connection
            self._connection = None
        if connection is not None:
            connection.close()
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None


class FrameStreamClient:
    """Foxy-side reconnectable client for one framed stream."""

    def __init__(self, host: str, port: int, timeout_seconds: float = 5.0) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._socket = None  # type: Optional[socket.socket]

    def connect(self) -> None:
        self.close()
        connection = socket.create_connection(
            (self._host, self._port), timeout=self._timeout_seconds
        )
        _configure_connection(connection, self._timeout_seconds)
        self._socket = connection

    def receive(self) -> Frame:
        if self._socket is None:
            raise ConnectionError("stream client is not connected")
        try:
            return recv_frame(self._socket)
        except (EOFError, OSError, ProtocolError):
            self.close()
            raise

    def send(self, frame_bytes: bytes) -> None:
        if self._socket is None:
            raise ConnectionError("stream client is not connected")
        try:
            send_frame(self._socket, frame_bytes)
        except (OSError, ProtocolError):
            self.close()
            raise

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None


class CommandClient:
    """Foxy-side sequence and saturation owner for CMD_VEL_V1 frames."""

    def __init__(
        self,
        host: str,
        port: int,
        limits: CommandLimits,
        timeout_seconds: float = 1.0,
        initial_sequence: int = 0,
    ) -> None:
        if initial_sequence < 0:
            raise ValueError("initial_sequence must be non-negative")
        self._stream = FrameStreamClient(host, port, timeout_seconds)
        self._limits = limits
        self._sequence = initial_sequence

    @property
    def sequence(self) -> int:
        return self._sequence

    def connect(self) -> None:
        self._stream.connect()

    def send_command(
        self, command: CommandV1, timestamp_ns: Optional[int] = None
    ) -> CommandV1:
        checked = self._limits.clamp(command)
        self._sequence += 1
        timestamp = time.monotonic_ns() if timestamp_ns is None else timestamp_ns
        frame_bytes = encode_frame(
            MessageType.CMD_VEL_V1,
            sequence=self._sequence,
            timestamp_ns=timestamp,
            payload=encode_command_payload(checked),
        )
        self._stream.send(frame_bytes)
        return checked

    def close(self) -> None:
        self._stream.close()
