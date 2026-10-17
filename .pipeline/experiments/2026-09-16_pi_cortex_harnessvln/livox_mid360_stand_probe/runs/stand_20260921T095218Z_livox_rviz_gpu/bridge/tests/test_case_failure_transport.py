"""Case-failure ownership over the real loopback transport (B02, B05).

These cases bind a fresh loopback port and drive `CommandReceiverServer` with
`CommandClient`, so the reconnect contract under test is the shipped one rather
than a stand-in. No Isaac process, robot command sink or physical driver is
involved: the server here is an ordinary in-test socket.
"""

from __future__ import annotations

import socket
import time

import pytest

from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
from lite3_sim_bridge.protocol import CommandV1
from lite3_sim_bridge.transport import CommandClient, CommandReceiverServer


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def assert_no_foreign_listener(port: int) -> None:
    """Refuse to run against anything but a port this test just bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        with pytest.raises(OSError):
            probe.connect(("127.0.0.1", port))


def wait_for(predicate, timeout_s: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


@pytest.fixture()
def server():
    port = free_loopback_port()
    assert_no_foreign_listener(port)
    state = LatestCommandState(
        CommandLimits(0.30, 0.30, 0.8, max_horizontal_norm=0.30),
        timeout_ns=250_000_000,
    )
    receiver = CommandReceiverServer(state, "127.0.0.1", port)
    receiver.start()
    try:
        yield receiver, state, port
    finally:
        receiver.stop()


def test_b02_reconnect_after_a_case_failure_never_re_admits_motion(server):
    receiver, state, port = server
    client = CommandClient("127.0.0.1", port, limits=CommandLimits(0.30, 0.30, 0.8))
    client.connect()
    client.send_command(CommandV1(0.2, 0.0, 0.1), timestamp_ns=time.monotonic_ns())
    assert wait_for(lambda: receiver.snapshot().command != CommandV1(0.0, 0.0, 0.0))

    state.latch_case_failure("nonfoot_contact_above_threshold")
    assert receiver.snapshot().command == CommandV1(0.0, 0.0, 0.0)

    # Drop the connection the way a restarted bridge would, then reconnect and
    # send a valid nonzero command again.
    client.close()
    assert wait_for(lambda: receiver.stats().accepted_connections >= 1)
    # A reconnect continues the command sequence, which is the transport's own
    # existing contract: restarting at sequence 1 is a protocol error, not a
    # reconnect.
    reconnected = CommandClient(
        "127.0.0.1", port, limits=CommandLimits(0.30, 0.30, 0.8),
        initial_sequence=client.sequence,
    )
    reconnected.connect()
    try:
        assert wait_for(lambda: receiver.stats().reconnects >= 1)
        for _ in range(5):
            reconnected.send_command(
                CommandV1(0.25, 0.1, 0.4), timestamp_ns=time.monotonic_ns()
            )
            time.sleep(0.01)
        snapshot = receiver.snapshot()
        assert snapshot.command == CommandV1(0.0, 0.0, 0.0)
        assert snapshot.case_failed is True
        assert snapshot.reason == "case_failed"
        assert snapshot.case_failure_reason == "nonfoot_contact_above_threshold"
    finally:
        reconnected.close()


def test_b05_command_disconnect_alone_is_recoverable(server):
    """A plain disconnect is not a case failure: the contract is unchanged."""
    receiver, state, port = server
    client = CommandClient("127.0.0.1", port, limits=CommandLimits(0.30, 0.30, 0.8))
    client.connect()
    client.send_command(CommandV1(0.2, 0.0, 0.0), timestamp_ns=time.monotonic_ns())
    assert wait_for(lambda: receiver.snapshot().command != CommandV1(0.0, 0.0, 0.0))

    client.close()
    assert wait_for(lambda: receiver.snapshot().reason == "disconnected")
    assert receiver.snapshot().command == CommandV1(0.0, 0.0, 0.0)
    assert receiver.snapshot().case_failed is False

    again = CommandClient(
        "127.0.0.1", port, limits=CommandLimits(0.30, 0.30, 0.8),
        initial_sequence=client.sequence,
    )
    again.connect()
    try:
        assert wait_for(lambda: receiver.stats().reconnects >= 1)

        def resend_and_check() -> bool:
            again.send_command(
                CommandV1(0.15, 0.0, 0.0), timestamp_ns=time.monotonic_ns()
            )
            snapshot = receiver.snapshot()
            # CMD_VEL_V1 carries binary32, so the readback is compared with the
            # float32 value rather than the Python literal.
            return snapshot.reason == "active" and snapshot.command.vx == pytest.approx(
                0.15, abs=1e-7
            )

        assert wait_for(resend_and_check)
    finally:
        again.close()


def test_b05_command_loss_zeroes_motion_at_the_unchanged_watchdog(server):
    """The 0.25 s watchdog value is used as configured, with injected time."""
    receiver, state, port = server
    client = CommandClient("127.0.0.1", port, limits=CommandLimits(0.30, 0.30, 0.8))
    client.connect()
    try:
        client.send_command(CommandV1(0.2, 0.0, 0.0), timestamp_ns=time.monotonic_ns())
        assert wait_for(lambda: receiver.snapshot().command != CommandV1(0.0, 0.0, 0.0))
        received_ns = receiver.snapshot().received_monotonic_ns
        assert received_ns is not None
        # Deterministic deadline check, independent of scheduler latency.
        assert state.snapshot(received_ns + 250_000_000).command != CommandV1(0.0, 0.0, 0.0)
        stale = state.snapshot(received_ns + 250_000_001)
        assert stale.command == CommandV1(0.0, 0.0, 0.0)
        assert stale.reason == "watchdog_timeout"
        assert stale.watchdog_events == 1
    finally:
        client.close()
