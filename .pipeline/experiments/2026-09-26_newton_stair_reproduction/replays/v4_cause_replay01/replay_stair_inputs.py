"""Replay recorded stair inputs to native SCAN without simulator or controller.

Only actual recorded clouds, body poses, track snapshots and the PCT route are
published. Actor truth is not an input. Scheduling is deliberately slower than
the simulation clock; this diagnoses geometry, not end-to-end timing.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def recorded_body_twist(item):
    """Recorded metrics store world twist; Odometry child=base requires body twist."""
    if "linear_body" in item or "angular_body" in item:
        if "linear_body" not in item or "angular_body" not in item:
            raise ValueError("incomplete recorded body twist")
        values = tuple(np.asarray(item[name], dtype=float) for name in ("linear_body", "angular_body"))
        if any(value.shape != (3,) or not np.isfinite(value).all() for value in values):
            raise ValueError("invalid recorded body twist")
        return values
    q = np.asarray(item["quaternion"], dtype=float)
    linear = np.asarray(item["linear"], dtype=float)
    angular = np.asarray(item["angular"], dtype=float)
    if q.shape != (4,) or linear.shape != (3,) or angular.shape != (3,) or not all(
            np.isfinite(value).all() for value in (q, linear, angular)):
        raise ValueError("invalid recorded pose or world twist")
    norm = float(np.linalg.norm(q))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError("recorded orientation must be a unit quaternion")
    q = q / norm
    # Rotate with the conjugate unit quaternion. Preserve recorded pose bytes;
    # normalization here only avoids scaling a velocity by float pose roundoff.
    w, xyz = q[0], -q[1:]
    def rotate(value):
        cross = 2.0 * np.cross(xyz, value)
        return value + w * cross + np.cross(xyz, cross)
    return rotate(linear), rotate(angular)


def assign_recorded_twist(message, item):
    linear, angular = recorded_body_twist(item)
    message.twist.twist.linear.x, message.twist.twist.linear.y, message.twist.twist.linear.z = map(float, linear)
    message.twist.twist.angular.x, message.twist.twist.angular.y, message.twist.twist.angular.z = map(float, angular)


def prepare(run, output, seconds, route_at=None):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    source = run / "returned_artifacts"
    origin = json.loads((source / "runner_output/run_clock.json").read_text())["simulation_origin_s"]
    events, arrays, provenance = [], {}, {}
    for filename, kind in (("clouds.jsonl", "cloud"), ("metrics.jsonl", "body")):
        path = source / "runner_output" / filename
        provenance[str(path)] = sha(path)
        for line in path.open():
            item = json.loads(line)
            if item["sim_time_s"] > seconds:
                break
            stamp = int(round((item["sim_time_s"] + origin) * 1e9))
            if kind == "cloud":
                key = "cloud_%d" % item["scan_id"]
                arrays[key] = np.asarray(item["planner_points_sensor_frame"], dtype="<f4")
                data = {"array": key, "position": item["sensor_position"], "quaternion": item["sensor_quaternion_wxyz"]}
            else:
                data = {"position": item["base_xyz"], "quaternion": item["base_quat_wxyz"],
                        "linear": item["base_linear_velocity_world"], "angular": item["base_angular_velocity_world"],
                        "linear_body": item["base_linear_velocity_body"], "angular_body": item["base_angular_velocity_body"],
                        "twist_schema": "world_and_body_v1"}
            events.append({"stamp": stamp, "kind": kind, "data": data})
    path = source / "reactive_observations.jsonl"
    provenance[str(path)] = sha(path)
    for line in path.open():
        item = json.loads(line)
        if item["event"] not in ("tracks", "pct_route") or item["clock_ns"] > int((seconds + origin) * 1e9):
            continue
        dispatch_stamp = item["clock_ns"]
        if item["event"] == "pct_route" and route_at is not None:
            if not 0.0 < route_at < seconds:
                raise ValueError("route dispatch must be inside the recorded replay interval")
            dispatch_stamp = int((route_at + origin) * 1e9)
        events.append({"stamp": dispatch_stamp, "kind": item["event"], "data": item["data"]})
    corepath = HERE.parents[1] / "2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/pct_sim_clock_core.py"
    spec = importlib.util.spec_from_file_location("replay_pct_core", corepath)
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    arrays["ground"] = core.selected_ground_points(core.load_pinned_map(run / "inputs/new_building.pickle"))
    np.savez_compressed(output / "points.npz", **arrays)
    write(output / "events.json", sorted(events, key=lambda e: (e["stamp"], {"body": 0, "cloud": 1, "tracks": 2, "pct_route": 3}[e["kind"]])))
    (output / "planner.yaml").write_bytes((run / "config/planner.yaml").read_bytes())
    write(output / "input_manifest.json", {"source": provenance, "recorded_run": run.name,
          "route_dispatch_override_relative_s": route_at, "recorded_twist_frame": "world",
          "files": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
          "claim": "Actual sensor replay only; cannot validate live avoidance or timing"})
    print(output)


def ros_run(inputs, output):
    import rclpy
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import PointCloud2, PointField
    from nav_msgs.msg import Odometry
    from scan_planner_msgs.msg import P2BRoute, TrackedPersonSnapshot, Bspline, P2BAdmission
    from rosidl_runtime_py.set_message import set_message_fields
    from rosidl_runtime_py.convert import message_to_ordereddict

    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    manifest = json.loads((inputs / "input_manifest.json").read_text())
    shutil.copy2(__file__, output / "replay_source.py")
    if any(sha(inputs / p) != digest for p, digest in manifest["files"].items()):
        raise ValueError("replay inputs changed")
    data = np.load(inputs / "points.npz")
    events = json.loads((inputs / "events.json").read_text())
    rclpy.init()
    node = rclpy.create_node("stair_recorded_input_replay")
    pubs = {"clock": node.create_publisher(Clock, "/clock", 100),
            "body": node.create_publisher(Odometry, "/quad_0/body_pose", 100),
            "pose": node.create_publisher(Odometry, "/quad_0/lidar_pose", 100),
            "cloud": node.create_publisher(PointCloud2, "/quad_0/cloud", 30),
            "tracks": node.create_publisher(TrackedPersonSnapshot, "/tracked_person_snapshot", 30),
            "pct_route": node.create_publisher(P2BRoute, "/p2b/route", 10),
            "ground": node.create_publisher(PointCloud2, "/pct_tomogram", QoSProfile(
                depth=1, reliability=QoSReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))}
    received = []
    node.create_subscription(Bspline, "/planning/bspline", lambda m: received.append({"kind": "bspline", "data": message_to_ordereddict(m)}), 100)
    node.create_subscription(P2BAdmission, "/p2b/scan_admission", lambda m: received.append({"kind": "admission", "data": message_to_ordereddict(m)}), 100)

    def stamp(msg, value):
        msg.sec, msg.nanosec = divmod(int(value), 1_000_000_000)

    def cloud(array, value, frame):
        msg = PointCloud2()
        stamp(msg.header.stamp, value)
        msg.header.frame_id = frame
        msg.width, msg.height = len(array), 1
        names = ["x", "y", "z", "intensity"][:array.shape[1]]
        msg.fields = [PointField(name=name, offset=i * 4, datatype=7, count=1) for i, name in enumerate(names)]
        msg.point_step, msg.row_step = array.shape[1] * 4, array.nbytes
        msg.is_dense = False
        msg.data = np.ascontiguousarray(array, dtype="<f4").tobytes()
        return msg

    def odom(item, value):
        msg = Odometry()
        stamp(msg.header.stamp, value)
        msg.header.frame_id, msg.child_frame_id = "world", "base"
        msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z = map(float, item["position"])
        q = msg.pose.pose.orientation
        q.w, q.x, q.y, q.z = map(float, item["quaternion"])
        if "linear" in item:
            assign_recorded_twist(msg, item)
        return msg

    command = ["ros2", "run", "scan_planner", "scan_planner_node", "--ros-args", "--params-file", str(inputs / "planner.yaml"),
               "-r", "body_pose:=/quad_0/body_pose", "-r", "sensor_pose:=/quad_0/lidar_pose", "-r", "cloud:=/quad_0/cloud"]
    log = (output / "scan.log").open("w")
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    result = {"completed": False, "input_manifest_sha256": sha(inputs / "input_manifest.json"),
              "replay_source_sha256": sha(Path(__file__)), "command": command,
              "recorded_twist_frame": "world", "published_odometry_twist_frame": "base",
              "body_twist_contract_version": 1,
              "twist_sources": {"direct_body_events": sum(e["kind"] == "body" and "linear_body" in e["data"] for e in events),
                                "legacy_world_rotation_events": sum(e["kind"] == "body" and "linear_body" not in e["data"] for e in events)}}
    try:
        time.sleep(1.5)
        last = 0
        for event in events:
            if process.poll() is not None:
                raise RuntimeError("SCAN replay process exited")
            value = event["stamp"]
            # 2x wall duration gives native wall timers time to consume each sweep.
            time.sleep(min(0.2, max(0.0, (value - last) / 1e9 * 2)))
            c = Clock()
            stamp(c.clock, value)
            pubs["clock"].publish(c)
            if last == 0:
                pubs["ground"].publish(cloud(data["ground"], value, "world"))
            kind, item = event["kind"], event["data"]
            if kind == "body":
                pubs[kind].publish(odom(item, value))
            elif kind == "cloud":
                pubs["pose"].publish(odom(item, value))
                time.sleep(0.005)
                pubs[kind].publish(cloud(data[item["array"]], value, "lidar"))
                # Geometry replay waits for the 50 ms native occupancy timer.
                # Otherwise a same-stamp route races the just-delivered cloud,
                # unlike the original route which used the previous ready scan.
                time.sleep(0.08)
            else:
                msg = P2BRoute() if kind == "pct_route" else TrackedPersonSnapshot()
                set_message_fields(msg, item)
                pubs[kind].publish(msg)
            rclpy.spin_once(node, timeout_sec=0.001)
            last = value
        for _ in range(30):
            rclpy.spin_once(node, timeout_sec=0.01)
        result["completed"] = True
    finally:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        log.close()
        result["exit_after_stop"] = process.returncode
        result["received"] = received
        result["scan_log_sha256"] = sha(output / "scan.log")
        write(output / "result.json", result)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare", type=Path)
    p.add_argument("--inputs", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seconds", type=float, default=3.5)
    p.add_argument("--route-at", type=float)
    a = p.parse_args()
    prepare(a.prepare, a.output, a.seconds, a.route_at) if a.prepare else ros_run(a.inputs, a.output)
