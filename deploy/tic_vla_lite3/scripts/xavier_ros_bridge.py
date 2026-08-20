#!/usr/bin/env python3
"""Read-only Xavier ROS2 RGB/odometry bridge for the task-owned Orin client."""

from __future__ import annotations

import argparse
import json
import math
import socket
import struct
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

MAX_METADATA_BYTES = 4096
MAX_JPEG_BYTES = 2 * 1024 * 1024


class LatestSamples:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.frame = None
        self.state = None
        self.frame_sequence = 0
        self.state_sequence = 0


def finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def send_record(connection: socket.socket, metadata: dict, jpeg: bytes) -> None:
    metadata_bytes = json.dumps(metadata, separators=(",", ":"),
                                allow_nan=False).encode("utf-8")
    if len(metadata_bytes) > MAX_METADATA_BYTES or len(jpeg) > MAX_JPEG_BYTES:
        raise ValueError("bridge_record_oversized")
    connection.sendall(struct.pack("!I", len(metadata_bytes)))
    connection.sendall(metadata_bytes)
    connection.sendall(struct.pack("!I", len(jpeg)))
    connection.sendall(jpeg)


def serve(samples: LatestSamples, bind_host: str, port: int,
          allowed_client: str, rate_hz: float, stop: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((bind_host, port))
    server.listen(1)
    server.settimeout(0.5)
    period = 1.0 / rate_hz
    try:
        while not stop.is_set():
            try:
                connection, address = server.accept()
            except socket.timeout:
                continue
            print(json.dumps({"client_source": address[0],
                              "client_allowed": address[0] == allowed_client},
                             sort_keys=True), flush=True)
            if address[0] != allowed_client:
                connection.close()
                continue
            # The official first reasoning generation is about 19 seconds on
            # this Orin. Keep the request connection idle across that bounded
            # pause without permitting an unbounded blocked socket.
            connection.settimeout(30.0)
            last_frame_sequence = -1
            try:
                while not stop.is_set():
                    # Request/response avoids queuing old camera records while
                    # the Orin is busy in a slow reasoning generation.
                    if connection.recv(1) != b"\x01":
                        break
                    deadline = time.monotonic() + 2.0
                    while not stop.is_set():
                        with samples.lock:
                            frame = samples.frame
                            state = samples.state
                        if (frame is not None and state is not None and
                                frame[0] != last_frame_sequence):
                            break
                        if time.monotonic() >= deadline:
                            raise TimeoutError("live_sample_timeout")
                        stop.wait(min(period, max(0.0, deadline - time.monotonic())))
                    if frame is not None and state is not None:
                        frame_sequence, frame_time, width, height, jpeg = frame
                        state_sequence, state_time, state_values = state
                        metadata = {
                            "schema": "tic-vla-lite3.observation.v1",
                            "frame_sequence": frame_sequence,
                            "frame_callback_monotonic_s": frame_time,
                            "frame_source_age_s": max(0.0, time.monotonic() - frame_time),
                            "state_sequence": state_sequence,
                            "state_callback_monotonic_s": state_time,
                            "state_source_age_s": max(0.0, time.monotonic() - state_time),
                            "width": width,
                            "height": height,
                            "encoding": "jpeg-bgr8",
                            **state_values,
                        }
                        send_record(connection, metadata, jpeg)
                        last_frame_sequence = frame_sequence
            except (BrokenPipeError, ConnectionError, OSError, TimeoutError, ValueError):
                connection.close()
    finally:
        server.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-host", default="192.168.1.103")
    parser.add_argument("--port", type=int, default=45451)
    parser.add_argument("--allowed-client", default="192.168.1.120")
    parser.add_argument("--rate-hz", type=float, default=4.0)
    parser.add_argument("--camera-topic", default="/camera/color/image_raw")
    parser.add_argument("--state-topic", default="/aft_mapped_to_init")
    parser.add_argument("--jpeg-quality", type=int, default=85)
    args = parser.parse_args()
    if not 1.0 <= args.rate_hz <= 10.0 or not 50 <= args.jpeg_quality <= 95:
        raise ValueError("invalid_bridge_configuration")

    import rclpy
    from cv_bridge import CvBridge
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image

    samples = LatestSamples()
    stop = threading.Event()
    cv_bridge = CvBridge()

    class BridgeNode(Node):
        def __init__(self) -> None:
            super().__init__("tic_vla_lite3_read_only_bridge")
            camera_qos = QoSProfile(depth=1)
            camera_qos.reliability = ReliabilityPolicy.RELIABLE
            camera_qos.durability = DurabilityPolicy.VOLATILE
            state_qos = QoSProfile(depth=1)
            # The selected Fast-LIVO2 publisher is RELIABLE; match it exactly
            # to avoid vendor-RMW compatibility differences on Foxy.
            state_qos.reliability = ReliabilityPolicy.RELIABLE
            state_qos.durability = DurabilityPolicy.VOLATILE
            self.create_subscription(Image, args.camera_topic, self.on_image, camera_qos)
            self.create_subscription(Odometry, args.state_topic, self.on_state, state_qos)
            self.create_timer(5.0, self.report_counts)

        def report_counts(self) -> None:
            with samples.lock:
                payload = {"frame_count": samples.frame_sequence,
                           "state_count": samples.state_sequence,
                           "motor_command_sent": False}
            print(json.dumps(payload, sort_keys=True), flush=True)

        def on_image(self, message) -> None:
            image = cv_bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
            ok, encoded = cv2.imencode(
                ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), args.jpeg_quality]
            )
            if not ok:
                return
            with samples.lock:
                samples.frame_sequence += 1
                samples.frame = (samples.frame_sequence, time.monotonic(),
                                 int(message.width), int(message.height),
                                 encoded.tobytes())

        def on_state(self, message) -> None:
            position = message.pose.pose.position
            orientation = message.pose.pose.orientation
            linear = message.twist.twist.linear
            angular = message.twist.twist.angular
            values = [position.x, position.y, position.z, orientation.x,
                      orientation.y, orientation.z, orientation.w,
                      linear.x, linear.y, angular.z]
            if not finite(values):
                return
            state_values = {
                "frame_id": str(message.header.frame_id),
                "child_frame_id": str(message.child_frame_id),
                "x_m": float(position.x),
                "y_m": float(position.y),
                "z_m": float(position.z),
                "qx": float(orientation.x),
                "qy": float(orientation.y),
                "qz": float(orientation.z),
                "qw": float(orientation.w),
                "vx_mps": float(linear.x),
                "vy_mps": float(linear.y),
                "wz_radps": float(angular.z),
            }
            with samples.lock:
                samples.state_sequence += 1
                samples.state = (samples.state_sequence, time.monotonic(), state_values)

    thread = threading.Thread(target=serve, args=(samples, args.bind_host, args.port,
                              args.allowed_client, args.rate_hz, stop), daemon=False)
    rclpy.init()
    node = BridgeNode()
    thread.start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        node.destroy_node()
        rclpy.shutdown()
        thread.join(timeout=3.0)
        if thread.is_alive():
            raise RuntimeError("bridge_server_thread_did_not_stop")


if __name__ == "__main__":
    main()
