"""MAVROS filter port and bounded local Mac/Linux clock-domain adapter.

Filter portions: Copyright 2014-2021 Vladimir Ermakov, M.H.Kabir.
BSD-3-Clause, see references/MAVROS_LICENSE_BSD.txt. Source and modifications
are recorded in references/mavros_clock_port.json. This is not a MAVLink wire
implementation. Original sensor/command wire formats remain unchanged.
"""
import ctypes
from dataclasses import dataclass
import json
import math
import socket
import struct
import threading
import time
import uuid

REQUEST = struct.Struct("!QQ")  # request sequence and local transmit time
RESPONSE = struct.Struct("!16sQQQ")  # responder identity, echoed fields, remote time
MAX_RTT_NS = 10_000_000
MAX_DEVIATION_NS = 10_000_000
SYNC_TTL_NS = 200_000_000


def f32(value):
    return ctypes.c_float(value).value


class ClockUnavailable(RuntimeError):
    pass


class MavrosFilter:
    """Pinned sys_time.cpp filter, without ROS publication or diagnostics."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.sequence = 0
        self.offset = self.skew = 0.0
        self.alpha = self.beta = f32(.05)
        self.high_rtt_count = self.high_deviation_count = 0

    def observe(self, offset, rtt):
        accepted = False
        deviation = abs(int(self.offset) - offset)
        if rtt < MAX_RTT_NS:
            if self.sequence >= 500 and deviation > MAX_DEVIATION_NS:
                self.high_deviation_count += 1
                if self.high_deviation_count > 10:
                    self.reset()
            else:
                if self.sequence < 500:
                    progress = f32(f32(self.sequence) / 500)
                    exponent = f32(.5 * f32(1.0 - f32(1.0 / f32(1.0 - progress))))
                    p = f32(1.0 - f32(math.exp(exponent)))
                    self.alpha = self.beta = f32(f32(p * f32(.003)) + f32(f32(1.0 - p) * f32(.05)))
                else:
                    self.alpha = self.beta = f32(.003)
                previous = self.offset
                if self.sequence == 0:
                    self.offset = float(offset)
                else:
                    self.offset = self.alpha * offset + (1.0 - self.alpha) * (self.offset + self.skew)
                    self.skew = self.beta * (self.offset - previous) + (1.0 - self.beta) * self.skew
                self.sequence += 1
                self.high_deviation_count = self.high_rtt_count = 0
                accepted = True
        else:
            self.high_rtt_count += 1
            if self.high_rtt_count > 10:
                self.high_rtt_count = 0
        return accepted


@dataclass(frozen=True)
class ClockEstimate:
    local_minus_remote_ns: int
    uncertainty_ns: int
    sampled_local_ns: int
    samples: int
    responder: str
    rtt_ns: int

    def remote_to_local_earliest(self, stamp):
        return int(stamp) + self.local_minus_remote_ns - self.uncertainty_ns

    def local_to_remote_earliest(self, stamp):
        return int(stamp) - self.local_minus_remote_ns - self.uncertainty_ns


def recv_exact(connection, count):
    result = bytearray()
    while len(result) < count:
        chunk = connection.recv(count - len(result))
        if not chunk:
            raise EOFError("clock channel closed")
        result.extend(chunk)
    return bytes(result)


def serve_clock(host, port):
    """Clock-only responder; exported by Docker only on host loopback."""
    identity = uuid.uuid4().bytes
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen(1)
        while True:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(2)
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                try:
                    while True:
                        seq, sent = REQUEST.unpack(recv_exact(connection, REQUEST.size))
                        remote = time.monotonic_ns()
                        connection.sendall(RESPONSE.pack(identity, seq, sent, remote))
                except (OSError, EOFError):
                    pass


class ClockClient:
    def __init__(self, host, port, log_path):
        self.host, self.port = host, port
        self.log_path = log_path
        self.filter = MavrosFilter()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.estimate_value = None
        self.responder = None
        self.error = "not_started"

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name="newton-clock-sync")
        self.thread.start()

    def _run(self):
        seq = 0
        with open(self.log_path, "w") as log:
            while not self.stop_event.is_set():
                try:
                    with socket.create_connection((self.host, self.port), timeout=.1) as connection:
                        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        while not self.stop_event.is_set():
                            seq += 1
                            sent = time.monotonic_ns()
                            connection.sendall(REQUEST.pack(seq, sent))
                            identity, echoed_seq, echoed_sent, remote = RESPONSE.unpack(recv_exact(connection, RESPONSE.size))
                            received = time.monotonic_ns()
                            if (echoed_seq, echoed_sent) != (seq, sent) or remote <= 0:
                                raise ClockUnavailable("mismatched_clock_reply")
                            identity = identity.hex()
                            if self.responder is None:
                                self.responder = identity
                            elif self.responder != identity:
                                raise ClockUnavailable("responder_restarted")
                            numerator = sent + received - 2 * remote
                            offset = numerator // 2 if numerator >= 0 else -((-numerator) // 2)
                            rtt = received - sent
                            with self.lock:
                                accepted = self.filter.observe(offset, rtt)
                                # MAVROS rejects a bad sample without renewing or
                                # discarding the last converged estimate. Its age
                                # still has to satisfy the original strict TTL.
                                if accepted:
                                    self.error = None
                                    margin = math.ceil(rtt / 2 + abs(offset - self.filter.offset) + MAX_DEVIATION_NS)
                                    self.estimate_value = ClockEstimate(round(self.filter.offset), margin, received,
                                                                       self.filter.sequence, identity, rtt)
                                elif self.filter.sequence == 0:
                                    self.estimate_value = None
                                    self.error = "clock_filter_reset"
                                row = {"seq": seq, "sent": sent, "remote": remote, "received": received,
                                       "rtt_ns": rtt, "observed_offset_ns": offset, "filtered_offset_ns": self.filter.offset,
                                       "samples": self.filter.sequence, "accepted": accepted,
                                       "responder": identity, "error": self.error,
                                       "observation_rejection": None if accepted else "rejected_clock_observation"}
                            log.write(json.dumps(row) + "\n")
                            log.flush()
                            self.stop_event.wait(max(0., .02 - (time.monotonic_ns() - sent) / 1e9))
                except (OSError, EOFError, ClockUnavailable) as error:
                    with self.lock:
                        self.error = str(error)
                    log.write(json.dumps({"error": str(error), "local_ns": time.monotonic_ns()}) + "\n")
                    log.flush()
                    self.stop_event.wait(.1)

    def estimate(self):
        with self.lock:
            estimate = self.estimate_value
            if self.error or estimate is None or estimate.samples < 500 or self.filter.sequence < 500:
                raise ClockUnavailable(self.error or "clock_not_converged")
            if not 0 <= time.monotonic_ns() - estimate.sampled_local_ns <= SYNC_TTL_NS:
                raise ClockUnavailable("clock_observation_stale")
            return estimate

    def wait_ready(self, timeout=25):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            try:
                return self.estimate()
            except ClockUnavailable:
                self.stop_event.wait(.02)
        raise ClockUnavailable("clock_convergence_deadline")

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=46202)
    args = parser.parse_args()
    serve_clock("0.0.0.0", args.port)
