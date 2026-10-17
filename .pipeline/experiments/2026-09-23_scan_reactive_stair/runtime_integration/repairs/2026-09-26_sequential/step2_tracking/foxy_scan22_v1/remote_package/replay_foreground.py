"""Measured-input tracking replay; simulator actor truth is never staged here."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def records(path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def prepare(output):
    here = Path(__file__).resolve().parent
    ri = here.parents[2]
    root = ri.parents[3]
    reactive = root / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair"
    sys.path.insert(0, str(reactive))
    from pct_sim_clock_core import load_pinned_map, selected_ground_points
    output.mkdir(parents=True, exist_ok=False)
    arrays = {"ground": selected_ground_points(load_pinned_map(), cost_limit=None),
              "old_selected_ground": selected_ground_points(load_pinned_map())}
    runs, provenance = [], {}
    for name in ("walk_v4_ego", "walk_v5_actor_right_v2"):
        artifact = ri / "runs" / name / "returned_artifacts"
        robot = artifact / "runner_output"
        events = list(records(artifact / "reactive_observations.jsonl"))
        observed = {r["data"]["stamp_ns"] for r in events if r["event"] == "cloud"}
        stamps = {r["scan_id"]: r["timestamp_ns"] for r in records(robot / "sensor_metrics.jsonl")}
        terrain_stamp = next(r["data"]["stamp_ns"] for r in events if r["event"] == "pct_tomogram")
        frames = []
        for cloud in records(robot / "clouds.jsonl"):
            value = stamps[cloud["scan_id"]]
            if value not in observed:
                continue
            key = name + "_%d" % cloud["scan_id"]
            arrays[key] = np.asarray(cloud["planner_points_sensor_frame"], dtype="<f4")
            frames.append({"array": key, "scan_id": cloud["scan_id"], "stamp_ns": value,
                           "sim_time_s": cloud["sim_time_s"], "position": cloud["sensor_position"],
                           "quaternion_wxyz": cloud["sensor_quaternion_wxyz"]})
        assert len(frames) == len(observed)
        runs.append({"name": name, "terrain_stamp_ns": terrain_stamp, "frames": frames})
        for p in (robot / "clouds.jsonl", robot / "sensor_metrics.jsonl", artifact / "reactive_observations.jsonl"):
            provenance[str(p.relative_to(root))] = sha(p)
    np.savez_compressed(output / "points.npz", **arrays)
    write(output / "events.json", runs)
    write(output / "input_manifest.json", {
        "files": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
        "sources_sha256": provenance, "producer_sha256": sha(Path(__file__)),
        "claim": "Captured published LiDAR, exact measured sensor pose/stamp, and pinned ground only. No actor truth, old tracks, or predicted positions."})
    print(json.dumps({r["name"]: len(r["frames"]) for r in runs}), flush=True)


def inputs_at(inputs):
    manifest = json.loads((inputs / "input_manifest.json").read_text())
    if any(sha(inputs / p) != digest for p, digest in manifest["files"].items()):
        raise ValueError("replay input identity changed")
    return np.load(inputs / "points.npz", allow_pickle=False), json.loads((inputs / "events.json").read_text())


def numeric(inputs, output, background_path):
    import scipy
    from scan_reactive_tracker import core, io, static_background, static_foreground_tracker, physical_ground_contract
    output.mkdir(parents=True, exist_ok=False)
    data, runs = inputs_at(inputs)
    ground = data["ground"]
    fields = {name: (i * 4, 7, 1) for i, name in enumerate(("x", "y", "z", "intensity"))}
    contract = dict(data=ground.tobytes(), frame="world", width=len(ground), height=1,
                    point_step=16, row_step=ground.nbytes, is_bigendian=False, fields=fields)
    physical_ground_contract.verify_physical_ground(**contract)
    rejected = []
    for name, change in (("z_offset_zero", {"fields": dict(fields, z=(0, 7, 1))}),
                         ("wrong_stride", {"row_step": ground.nbytes + 16}),
                         ("big_endian", {"is_bigendian": True}),
                         ("old_selected_payload", {"data": data["old_selected_ground"].tobytes()})):
        try:
            physical_ground_contract.verify_physical_ground(**dict(contract, **change))
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError("bad physical ground accepted: " + name)
    index = static_background.load_building_background(background_path)
    report = {"completed": False, "python": platform.python_version(), "numpy": np.__version__,
              "scipy": scipy.__version__, "scipy_path": scipy.__file__, "runs": [],
              "ground_negative_cases_rejected": rejected,
              "source_sha256": {Path(m.__file__).name: sha(Path(m.__file__)) for m in
                                (core, io, static_background, static_foreground_tracker, physical_ground_contract)},
              "input_manifest_sha256": sha(inputs / "input_manifest.json"),
              "replay_sha256": sha(Path(__file__)), "background_sha256": sha(background_path),
              "claim": "Actual wrapper on full captured sequences; no ROS timing or live physics claim."}
    for run in runs:
        tracker = static_foreground_tracker.StaticForegroundTracker(index)
        terrain = io.terrain_from_pct_records(ground.tolist(), ground.tobytes(), "world",
                                               run["terrain_stamp_ns"], cost_limit=None)
        frames = []
        for event in run["frames"]:
            w, x, y, z = event["quaternion_wxyz"]
            pose = core.PoseObservation(event["stamp_ns"], "world", "lidar", tuple(event["position"]), (x, y, z, w))
            points = data[event["array"]]
            cloud = core.CloudFrame(event["stamp_ns"], "lidar", points.tolist())
            before = hashlib.sha256(points.tobytes()).hexdigest()
            started = time.perf_counter()
            result = tracker.process(cloud, pose, terrain, event["stamp_ns"])
            elapsed = time.perf_counter() - started
            assert before == hashlib.sha256(points.tobytes()).hexdigest()
            frames.append({"scan_id": event["scan_id"], "sim_time_s": event["sim_time_s"],
                           "snapshot": asdict(result), "background": tracker.last_background_metrics, "wall_s": elapsed})
        report["runs"].append({"name": run["name"], "frames": frames,
                               "max_frame_wall_s": max(f["wall_s"] for f in frames)})
        print(run["name"], len(frames), "frames, max_seconds", report["runs"][-1]["max_frame_wall_s"], flush=True)
    report["completed"] = True
    write(output / "result.json", report)


def ros(inputs, output, background_path):
    import rclpy
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, qos_profile_sensor_data
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import PointCloud2, PointField
    from nav_msgs.msg import Odometry
    from scan_planner_msgs.msg import TrackedPersonSnapshot
    from rosidl_runtime_py.convert import message_to_ordereddict

    output.mkdir(parents=True, exist_ok=False)
    data, runs = inputs_at(inputs)
    report = {"completed": False, "input_manifest_sha256": sha(inputs / "input_manifest.json"),
              "replay_sha256": sha(Path(__file__)), "runs": [],
              "claim": "Real installed ROS tracker on immutable recorded inputs at 10 Hz wall cadence. No physics, actuation, navigation or actor-truth input."}
    rclpy.init()
    node = rclpy.create_node("static_foreground_recorded_replay")
    pubs = {"clock": node.create_publisher(Clock, "/clock", 100),
            "pose": node.create_publisher(Odometry, "/quad_0/lidar_pose", qos_profile_sensor_data),
            "cloud": node.create_publisher(PointCloud2, "/quad_0/cloud", qos_profile_sensor_data),
            "ground": node.create_publisher(PointCloud2, "/tracker_ground", QoSProfile(
                depth=1, reliability=QoSReliabilityPolicy.RELIABLE, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL))}
    received, sent = [], []
    node.create_subscription(TrackedPersonSnapshot, "/tracked_person_snapshot",
                             lambda m: received.append({"arrival_wall": time.monotonic(), "data": message_to_ordereddict(m)}),
                             qos_profile_sensor_data)

    def spin(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(.01, max(0., deadline - time.monotonic())))

    def stamp(msg, value):
        msg.sec, msg.nanosec = divmod(int(value), 1_000_000_000)

    def clock(value):
        msg = Clock()
        stamp(msg.clock, value)
        pubs["clock"].publish(msg)

    def cloud(array, value, frame):
        msg = PointCloud2()
        stamp(msg.header.stamp, value)
        msg.header.frame_id = frame
        msg.width, msg.height = len(array), 1
        msg.fields = [PointField(name=name, offset=i * 4, datatype=7, count=1)
                      for i, name in enumerate(("x", "y", "z", "intensity")[:array.shape[1]])]
        msg.point_step, msg.row_step = array.shape[1] * 4, array.nbytes
        msg.is_dense = True
        msg.data = array.astype("<f4", copy=False).tobytes()
        return msg

    try:
        for run in runs:
            received.clear()
            sent.clear()
            command = ["ros2", "run", "scan_reactive_tracker", "moving_cluster_tracker", "--ros-args",
                       "-p", "use_sim_time:=true", "-p", "static_background_pcd:=" + str(background_path)]
            logpath = output / (run["name"] + ".log")
            log = logpath.open("w")
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result = {"name": run["name"], "command": command, "completed": False}
            try:
                deadline = time.monotonic() + 15
                while pubs["cloud"].get_subscription_count() == 0:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("tracker failed to become ready")
                    spin(.05)
                clock(run["terrain_stamp_ns"])
                spin(.1)
                # The previous selected support is intentionally rejected first.
                pubs["ground"].publish(cloud(data["old_selected_ground"], run["terrain_stamp_ns"], "world"))
                spin(.25)
                pubs["ground"].publish(cloud(data["ground"], run["terrain_stamp_ns"], "world"))
                spin(.7)
                for event in run["frames"]:
                    if process.poll() is not None:
                        raise RuntimeError("tracker exited during ROS replay")
                    begin = time.monotonic()
                    clock(event["stamp_ns"])
                    spin(.005)
                    pose = Odometry()
                    stamp(pose.header.stamp, event["stamp_ns"])
                    pose.header.frame_id, pose.child_frame_id = "world", "lidar"
                    pose.pose.pose.position.x, pose.pose.pose.position.y, pose.pose.pose.position.z = map(float, event["position"])
                    q = pose.pose.pose.orientation
                    q.w, q.x, q.y, q.z = map(float, event["quaternion_wxyz"])
                    pubs["pose"].publish(pose)
                    spin(.005)
                    pubs["cloud"].publish(cloud(data[event["array"]], event["stamp_ns"], "lidar"))
                    sent.append({"stamp_ns": event["stamp_ns"], "scan_id": event["scan_id"],
                                 "sim_time_s": event["sim_time_s"], "publish_wall": time.monotonic()})
                    spin(max(0., .1 - (time.monotonic() - begin)))
                spin(.3)
                # Schema drift invalidates support even if all data bytes match.
                bad_stamp = run["frames"][-1]["stamp_ns"] + 100_000_000
                clock(bad_stamp)
                spin(.01)
                bad = cloud(data["ground"], bad_stamp, "world")
                bad.fields[2].offset = 0
                start_bad = len(received)
                pubs["ground"].publish(bad)
                spin(.2)
                result["wrong_schema_incomplete_seen"] = any(not v["data"]["complete"] for v in received[start_bad:])
                clock(bad_stamp + 500_000_000)
                spin(.15)
                result["completed"] = True
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                log.close()
                result.update(received=list(received), sent=list(sent), log_sha256=sha(logpath), exit_after_stop=process.returncode)
                report["runs"].append(result)
                write(output / "result.json", report)
            print(run["name"], len(sent), "published frames", len(received), "received snapshots", flush=True)
            # Let graph discovery release the stopped subscriber before next run.
            spin(.5)
        report["completed"] = True
        write(output / "result.json", report)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "numeric", "ros"))
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--background", type=Path)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    if args.package:
        sys.path.insert(0, str(args.package))
    if args.mode == "prepare":
        prepare(args.output)
    else:
        {"numeric": numeric, "ros": ros}[args.mode](args.inputs, args.output, args.background)
