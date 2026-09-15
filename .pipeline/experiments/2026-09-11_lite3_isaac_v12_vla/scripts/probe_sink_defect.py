#!/usr/bin/env python3
"""Reproduce the qualification telemetry-sink defect. Stdlib only: no Isaac, no GPU, under a second.

`run_isaac_lite3.py:171-176` treats a read timeout as recoverable (`except TimeoutError: continue`), but
`FrameStreamClient.receive()` has already CLOSED the socket by then, because `socket.timeout` IS a
`TimeoutError` and `TimeoutError` is a subclass of `OSError`. The next `receive()` therefore raises
`ConnectionError`, which the sink reports as "telemetry stream ended unexpectedly".

A peer that is merely SLOW - a simulator still starting up - is enough to kill the sink for good.
"""
import pathlib
import socket
import sys
import threading
import time

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'references/upstream/2026-09-11_lite3_sim_bridge/source'))
from lite3_sim_bridge.transport import FrameStreamClient  # noqa: E402

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 0))
server.listen(1)
port = server.getsockname()[1]
held = []


def accept_and_stay_silent():
    connection, _ = server.accept()
    held.append(connection)      # connected and healthy, just not sending yet
    time.sleep(5.0)


threading.Thread(target=accept_and_stay_silent, daemon=True).start()

client = FrameStreamClient('127.0.0.1', port, timeout_seconds=1.0)
client.connect()
print('connected; the peer is alive and silent')

try:
    client.receive()
except TimeoutError as error:
    print(f'1st receive -> {type(error).__name__}; the sink loop CONTINUES past this')
    print(f'   isinstance(error, OSError): {isinstance(error, OSError)}')
print(f'   client socket after the timeout: {client._socket!r}')

try:
    client.receive()
except Exception as error:
    reported = isinstance(error, OSError)
    print(f'2nd receive -> {type(error).__name__}: {error}')
    print(f'   reported by the sink as "telemetry stream ended unexpectedly": {reported}')
    print('DEFECT REPRODUCED' if reported and not isinstance(error, TimeoutError) else 'not reproduced')
