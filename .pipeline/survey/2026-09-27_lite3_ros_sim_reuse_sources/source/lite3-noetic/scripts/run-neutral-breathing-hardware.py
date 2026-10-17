#!/usr/bin/env python3
"""Run the commissioned neutral breathing loop through the Retroid Pose path."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import queue
import select
import signal
import subprocess
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCE = ROOT / "hardware-ws/src/emotion_bot_lite3_hw/src"
sys.path.insert(0, str(PACKAGE_SOURCE))

from emotion_bot_lite3_hw.direct_pose import (  # noqa: E402
    DirectPoseLimits,
    HEARTBEAT_CODE,
    HEIGHT_CODE,
    MOVE_MODE_CODE,
    POSE_MODE_CODE,
    RateLimitedHeight,
    YAW_CODE,
    gate_failure,
)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-ssh", default=os.environ.get("ROBOT_MOTION_SSH", "ysc@192.168.2.1"))
    parser.add_argument("--perception-ssh", default=os.environ.get("ROBOT_PERCEPTION_SSH", "ysc@192.168.1.103"))
    parser.add_argument("--local-address", default=os.environ.get("HARDWARE_WIFI_IP", ""))
    parser.add_argument("--minimum-battery", type=float, default=float(os.environ.get("HARDWARE_MINIMUM_BATTERY", "25")))
    parser.add_argument("--duration", type=float, default=None, help="stop after this many active seconds (verification only)")
    parser.add_argument("--fixed-height", type=float, default=None, help="fixed normalized test target; requires --duration")
    return parser.parse_args()


class NeutralPoseBridge:
    def __init__(self, options):
        self.options = options
        self.limits = DirectPoseLimits()
        self.wave = RateLimitedHeight(self.limits)
        self.stop_requested = False
        self.ssh = None
        self.udp = None
        self.snapshots = queue.Queue(maxsize=200)
        self.latest = None
        self.latest_at = 0.0
        self.last_pause_reason = None
        self.active_samples = 0
        self.minimum_height = None
        self.maximum_height = None
        self.lock_file = None
        self.last_neutral_acknowledged = False
        self.joint_minimum = None
        self.joint_maximum = None
        self.imu_minimum = None
        self.imu_maximum = None

    def gate_reader(self):
        for line in self.ssh.stdout:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            try:
                self.snapshots.put(value, timeout=0.1)
            except queue.Full:
                try:
                    self.snapshots.get_nowait()
                except queue.Empty:
                    pass
                self.snapshots.put_nowait(value)

    def request_stop(self, _signum=None, _frame=None):
        self.stop_requested = True

    def start(self):
        self.lock_file = open("/tmp/emotion-bot-neutral-breathing.lock", "w")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another neutral breathing bridge already owns the hardware path") from exc
        self.lock_file.write("%d\n" % os.getpid())
        self.lock_file.flush()
        jump = self.options.motion_ssh
        target = self.options.perception_ssh
        remote = (
            "source /opt/ros/noetic/setup.bash; "
            "source ~/lite_cog/transfer/devel/setup.bash; "
            "source ~/emotion_bot_lite3_hw_ws/devel/setup.bash; "
            "exec rosrun emotion_bot_lite3_hw direct_gate_stream.py"
        )
        self.ssh = subprocess.Popen(
            [
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                "-o", "ConnectionAttempts=1", "-J", jump, target, remote,
            ],
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        threading.Thread(target=self.gate_reader, daemon=True).start()

        relay = subprocess.check_output(
            ["wslpath", "-w", str(ROOT / "scripts/windows/retroid-udp-relay.ps1")],
            text=True,
        ).strip()
        command = [
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", relay,
        ]
        if self.options.local_address:
            command.extend(["-LocalAddress", self.options.local_address])
        self.udp = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        ready = self.udp.stdout.readline().strip()
        expected = None if not self.options.local_address else "READY %s:43897" % self.options.local_address
        if not ready.startswith("READY 192.168.2.") or (expected is not None and ready != expected):
            raise RuntimeError("Windows UDP relay failed to bind: %s" % ready)
        print("Neutral breathing relay %s; waiting for neutral hardware gates." % ready, flush=True)

    def receive(self, timeout):
        if self.ssh.poll() is not None:
            raise BridgeFailure("hardware gate stream exited")
        if self.udp is not None and self.udp.poll() is not None:
            raise BridgeFailure("Windows UDP relay exited")
        try:
            value = self.snapshots.get(timeout=max(0.0, timeout))
            self.latest = value
            self.latest_at = time.monotonic()
            while True:
                self.latest = self.snapshots.get_nowait()
                self.latest_at = time.monotonic()
        except queue.Empty:
            pass
        if self.latest is None:
            return
        joints = self.latest.get("joints") or []
        imu = self.latest.get("imu") or []
        if len(joints) == 12:
            if self.joint_minimum is None:
                self.joint_minimum = list(joints)
                self.joint_maximum = list(joints)
            else:
                self.joint_minimum = [min(a, b) for a, b in zip(self.joint_minimum, joints)]
                self.joint_maximum = [max(a, b) for a, b in zip(self.joint_maximum, joints)]
        if len(imu) == 2:
            if self.imu_minimum is None:
                self.imu_minimum = list(imu)
                self.imu_maximum = list(imu)
            else:
                self.imu_minimum = [min(a, b) for a, b in zip(self.imu_minimum, imu)]
                self.imu_maximum = [max(a, b) for a, b in zip(self.imu_maximum, imu)]

    def failure(self):
        if self.latest is None or time.monotonic() - self.latest_at > 0.35:
            return "hardware gate stream is stale"
        return gate_failure(self.latest, self.options.minimum_battery)

    def wait_safe(self, duration):
        deadline = time.monotonic() + duration
        while not self.stop_requested and time.monotonic() < deadline:
            self.receive(min(0.05, max(0.0, deadline - time.monotonic())))
            reason = self.failure()
            if reason is not None:
                raise GateUnsafe(reason)

    def send(self, code, value=0):
        if self.udp.poll() is not None:
            raise BridgeFailure("Windows UDP relay exited")
        self.udp.stdin.write("ONE %d %d\n" % (int(code), int(value)))
        self.udp.stdin.flush()

    def send_pair(self, yaw, height):
        if self.udp.poll() is not None:
            raise BridgeFailure("Windows UDP relay exited")
        self.udp.stdin.write("PAIR %d %d\n" % (int(yaw), int(height)))
        self.udp.stdin.flush()

    def neutralize(self):
        self.last_neutral_acknowledged = False
        if self.udp is not None and self.udp.poll() is None:
            try:
                self.udp.stdin.write("ZERO\n")
                self.udp.stdin.flush()
                readable, _writable, _errors = select.select([self.udp.stdout], [], [], 0.75)
                if readable and self.udp.stdout.readline().strip() == "ACK ZERO":
                    self.last_neutral_acknowledged = True
                    self.udp.stdin.write("WATCHDOG OFF\n")
                    self.udp.stdin.flush()
                else:
                    print("Neutral breathing warning: zero acknowledgement was not received.", file=sys.stderr, flush=True)
            except (BrokenPipeError, OSError):
                pass
        self.wave.reset()

    def establish_pose(self):
        for _attempt in range(4):
            self.send(HEARTBEAT_CODE)
            self.wait_safe(0.5)
        self.send(MOVE_MODE_CODE)
        self.wait_safe(2.0)
        self.send(POSE_MODE_CODE)
        self.wait_safe(1.5)
        self.udp.stdin.write("WATCHDOG ON\n")
        self.udp.stdin.flush()

    def active_cycle(self):
        self.establish_pose()
        print("Neutral gates ready; 50% bounded height-only breathing active.", flush=True)
        self.joint_minimum = None
        self.joint_maximum = None
        self.imu_minimum = None
        self.imu_maximum = None
        started = time.monotonic()
        previous = started
        next_tick = started
        next_heartbeat = started
        while not self.stop_requested:
            now = time.monotonic()
            if self.options.duration is not None and now - started >= self.options.duration:
                self.stop_requested = True
                break
            self.receive(0.0)
            reason = self.failure()
            if reason is not None:
                raise RuntimeError(reason)
            if self.options.fixed_height is None:
                value = self.wave.update(now - started, now - previous)
            else:
                value = self.wave.update_target(self.options.fixed_height, now - previous)
            previous = now
            self.send_pair(32768, value)
            self.active_samples += 1
            self.minimum_height = value if self.minimum_height is None else min(self.minimum_height, value)
            self.maximum_height = value if self.maximum_height is None else max(self.maximum_height, value)
            if now >= next_heartbeat:
                self.send(HEARTBEAT_CODE)
                next_heartbeat = now + 0.5
            next_tick += 1.0 / self.limits.publish_rate
            self.receive(max(0.0, next_tick - time.monotonic()))

    def run(self):
        try:
            self.start()
            safe_since = None
            while not self.stop_requested:
                self.receive(0.1)
                reason = self.failure()
                if reason is not None:
                    safe_since = None
                    if reason != self.last_pause_reason:
                        print("Neutral breathing paused: %s." % reason, flush=True)
                        self.last_pause_reason = reason
                    continue
                if safe_since is None:
                    safe_since = time.monotonic()
                    continue
                if time.monotonic() - safe_since < 2.0:
                    continue
                self.last_pause_reason = None
                try:
                    self.active_cycle()
                except GateUnsafe as exc:
                    self.neutralize()
                    safe_since = None
                    if not self.stop_requested:
                        print("Neutral breathing paused: %s." % exc, flush=True)
                        self.last_pause_reason = str(exc)
        finally:
            self.neutralize()
            self.close()
        joint_spans = [] if self.joint_minimum is None else [
            high - low for low, high in zip(self.joint_minimum, self.joint_maximum)
        ]
        imu_spans = [] if self.imu_minimum is None else [
            high - low for low, high in zip(self.imu_minimum, self.imu_maximum)
        ]
        print(json.dumps({
            "active_samples": self.active_samples,
            "height_min": self.minimum_height,
            "height_max": self.maximum_height,
            "minimum_battery": self.options.minimum_battery,
            "final_zero_repetitions": 5 if self.last_neutral_acknowledged else 0,
            "joint_max_span_rad": max(joint_spans) if joint_spans else None,
            "imu_max_orientation_component_span": max(imu_spans) if imu_spans else None,
        }, sort_keys=True), flush=True)

    def close(self):
        if self.udp is not None:
            if self.udp.stdin:
                self.udp.stdin.close()
            try:
                self.udp.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.udp.kill()
                self.udp.wait(timeout=2.0)
        if self.ssh is not None:
            self.ssh.terminate()
            try:
                self.ssh.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.ssh.kill()
                self.ssh.wait(timeout=2.0)
        if self.lock_file is not None:
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()


class BridgeFailure(RuntimeError):
    pass


class GateUnsafe(RuntimeError):
    pass


def main():
    options = arguments()
    if options.minimum_battery < 25.0:
        raise SystemExit("minimum battery may not be set below the commissioned 25% floor")
    if options.fixed_height is not None:
        if options.duration is None:
            raise SystemExit("--fixed-height requires --duration")
        if not -1.0 <= options.fixed_height <= 1.0:
            raise SystemExit("--fixed-height must be within [-1, 1]")
    bridge = NeutralPoseBridge(options)
    signal.signal(signal.SIGINT, bridge.request_stop)
    signal.signal(signal.SIGTERM, bridge.request_stop)
    bridge.run()


if __name__ == "__main__":
    main()
