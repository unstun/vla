#!/usr/bin/env python3
"""Bounded UDP relay for the routed Orin-to-RK3588 shadow-only path."""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path

MAX_PACKET_BYTES = 1024


def append_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-host", default="192.168.1.103")
    parser.add_argument("--bind-port", type=int, default=45460)
    parser.add_argument("--allowed-source", default="192.168.1.120")
    parser.add_argument("--target-host", default="192.168.1.120")
    parser.add_argument("--target-port", type=int, default=45461)
    parser.add_argument("--duration-s", type=float, required=True)
    parser.add_argument("--log", required=True, type=Path)
    args = parser.parse_args()
    if args.duration_s <= 0.0:
        raise ValueError("duration")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind((args.bind_host, args.bind_port))
    receiver.settimeout(0.2)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    started = time.monotonic()
    accepted = rejected = 0
    try:
        while time.monotonic() - started < args.duration_s:
            try:
                payload, address = receiver.recvfrom(MAX_PACKET_BYTES + 1)
            except socket.timeout:
                continue
            reason = "ok"
            if address[0] != args.allowed_source:
                reason = "source"
            elif not payload or len(payload) > MAX_PACKET_BYTES:
                reason = "size"
            if reason == "ok":
                sender.sendto(payload, (args.target_host, args.target_port))
                accepted += 1
            else:
                rejected += 1
            append_jsonl(args.log, {
                "received_monotonic_s": time.monotonic(),
                "source": address[0],
                "packet_bytes": len(payload),
                "forwarded": reason == "ok",
                "reason": reason,
                "accepted": accepted,
                "rejected": rejected,
                "motor_command_sent": False,
            })
    finally:
        receiver.close()
        sender.close()


if __name__ == "__main__":
    main()
