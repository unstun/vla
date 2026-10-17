"""Actual Newton physics/sensing with commands from the archived native graph."""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

from bridge_adapter import DomainCommandState
from clock_sync import ClockClient, ClockUnavailable
from scene_assets import BASE, OfficialHuman, verify_inputs
from robot_scene import StairRobot
from geometric_lidar import GeometricLidar
from lite3_sim_bridge.command_state import CommandLimits
from lite3_sim_bridge.protocol import (BodyStateV2, DualCloudSensorFrameV1, MessageType,
    encode_frame, encode_body_state_v2_payload, encode_dual_cloud_sensor_payload)
from lite3_sim_bridge.transport import CommandReceiverServer, TelemetryPublisherServer


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value) + "\n")
    temporary.replace(path)


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    external = out / "artifacts/external_episode"
    request = json.loads((out / "episode_request.json").read_text())
    identity = verify_inputs()
    (out / "input_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    robot = StairRobot()
    human = OfficialHuman(out)
    lidar = GeometricLidar(robot, human, emitter_self_exclusion=True)
    (out / "clouds").mkdir()
    clock = ClockClient("127.0.0.1", 46202, out / "clock_samples.jsonl")
    state = DomainCommandState(clock, CommandLimits(1., .35, 1., 1.))
    commands = CommandReceiverServer(state, "127.0.0.1", 46201)
    telemetry = TelemetryPublisherServer("127.0.0.1", 46200, priority_send=True)
    clock.start()
    commands.start()
    telemetry.start()
    epoch = request["run_epoch_ns"]
    config_hash = hashlib.sha256((out / "episode_request.json").read_bytes()).digest()
    rows, clouds, video_states, results = [], [], [], {}
    wire_sequence = 0
    goal_sent = False
    last_backend = None
    last_http_error = None
    last_snapshot = None
    started = time.monotonic()
    failed_driver_at = None

    def publish(kind, stamp, payload):
        nonlocal wire_sequence
        wire_sequence += 1
        return telemetry.publish(encode_frame(kind, wire_sequence, stamp, payload))

    try:
        estimate = clock.wait_ready(30)
        (out / "initial_clock.json").write_text(json.dumps(asdict(estimate), indent=2) + "\n")
        with (out / "telemetry.jsonl").open("w") as log, (out / "sensor.jsonl").open("w") as sensor_log, (out / "backend_states.jsonl").open("w") as backend_log:
            steps = round(request["max_physics_s"] / .02)
            for step in range(steps):
                if (out / "native_failure.json").exists():
                    raise RuntimeError((out / "native_failure.json").read_text())
                if time.monotonic() - started > 430:
                    raise TimeoutError("Local episode wall deadline")
                snapshot, remote_source = state.current(time.monotonic_ns())
                command = (snapshot.command.vx, snapshot.command.vy, snapshot.command.wz)
                step_started = time.monotonic_ns()
                robot.step(command)
                row = robot.telemetry()
                pose = robot.body_and_sensor()
                sim_time = row["physics_time_s"]
                stamp = round(sim_time * 1e9)
                body = BodyStateV2(tuple(pose["position"]), tuple(pose["quaternion"][1:] + pose["quaternion"][:1]),
                     tuple(pose["linear_world"]), tuple(pose["angular_world"]),
                     tuple(pose["linear_body"]), tuple(pose["angular_body"]), stamp, step + 1, epoch)
                publish(MessageType.BODY_STATE_V2, stamp, encode_body_state_v2_payload(body))
                row.update(command=list(command), command_sequence=snapshot.sequence, command_stale=snapshot.stale,
                           command_reason=snapshot.reason, command_source_timestamp_linux_ns=remote_source,
                           wall_s=time.monotonic() - started, body_sensor=pose, state_sequence=step + 1)
                # Timestamp the evidence no later than the beginning of this
                # actual policy/physics update. Never stamp old state as new.
                try:
                    estimate = clock.estimate()
                    linux_stamp = estimate.local_to_remote_earliest(step_started)
                    cmd_dict = dict(zip(("vx", "vy", "wz"), command))
                    applied = {"schema_version": 1, "run_id": out.name, "run_epoch_ns": epoch,
                        "sim_step": robot.steps, "sim_time_s": sim_time, "wall_monotonic_ns": linux_stamp,
                        "command_source_timestamp_ns": remote_source, "command_sequence": snapshot.sequence or 0,
                        "command_stale": snapshot.stale, "command_reason": snapshot.reason,
                        "raw_command": cmd_dict, "admitted_command": cmd_dict, "applied_command": cmd_dict,
                        "freshness": {"max_reader_age_s": 2., "atomic_replace": True},
                        "state_epoch": {"state_sequence": step + 1, "telemetry_sequence": wire_sequence},
                        "measured": {"horizontal_speed_mps": float(np.linalg.norm(pose["linear_world"][:2])),
                          "yaw_rate_radps": pose["angular_body"][2], "base_xyz": pose["position"],
                          "base_quat_wxyz": pose["quaternion"], "command_obs_error": 0.},
                        "clock_mapping": asdict(estimate), "host_step_started_monotonic_ns": step_started}
                    atomic_json(external / "current_command.json", applied)
                except ClockUnavailable:
                    row["applied_snapshot_not_refreshed"] = "clock_unsynchronized"
                if (step + 1) % 5 == 0:
                    points, world, info, actor, audit = lidar.scan(len(clouds), sim_time)
                    raw = points.astype(">f4").tobytes()
                    sensor = DualCloudSensorFrameV1(tuple(pose["position"]), tuple(pose["quaternion"][1:] + pose["quaternion"][:1]),
                        tuple(pose["sensor_position"]), tuple(pose["sensor_quaternion"][1:] + pose["sensor_quaternion"][:1]),
                        config_hash, len(clouds) + 1, len(points), raw, len(points), raw, 0, 0)
                    publish(MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, stamp, encode_dual_cloud_sensor_payload(sensor))
                    cloud_path = out / "clouds" / f"{len(clouds):05d}.npz"
                    np.savez_compressed(cloud_path, sensor_points=points, world_points=world)
                    item = {"sim_time_s": sim_time, "stamp_ns": stamp, "body_sensor": pose, "sensor": info,
                            "actor_scoring_only": actor, "file": str(cloud_path.relative_to(out)),
                            "sha256": hashlib.sha256(cloud_path.read_bytes()).hexdigest()}
                    clouds.append(item)
                    sensor_log.write(json.dumps(item) + "\n")
                    sensor_log.flush()
                    try:
                        last_backend = json.loads((out / "backend_latest.json").read_text())
                        goal_sent = bool(last_backend.get("jobs"))
                        last_http_error = None
                        backend_log.write(json.dumps({"sim_time_s": sim_time, "data": last_backend}) + "\n")
                        backend_log.flush()
                    except Exception as error:
                        last_http_error = str(error)
                if (step + 1) % 4 == 0:
                    video_states.append({"physics_time_s": sim_time, "body_q": robot.state.body_q.numpy().tolist(),
                        "joint_q": row["joint_q"], "command": list(command), "command_reason": snapshot.reason,
                        "goal_sent": goal_sent, "last_backend_error": None if last_backend is None else last_backend["readiness"]["last_error"]})
                log.write(json.dumps(row) + "\n")
                log.flush()
                rows.append(row)
                last_snapshot = snapshot
                if row["base_up_z"] < .5:
                    state.latch_case_failure("fallen")
                    results["fallen"] = True
                    break
                if (step + 1) % 50 == 0:
                    print(json.dumps({"sim": sim_time, "command": command, "reason": snapshot.reason,
                         "base": pose["position"], "backend_error": last_http_error,
                         "goal_sent": goal_sent}), flush=True)
                finish_path = external / "finish_request.json"
                if not request["probe"] and finish_path.exists():
                    finish = json.loads(finish_path.read_text())
                    if finish.get("run_id") != out.name or finish.get("observed_run_epoch_ns") != epoch:
                        raise ValueError("Foreign finish request")
                    results["finish_request"] = finish
                    if finish.get("backend_terminal_status") == "FAILED":
                        state.latch_case_failure("original_driver_failed")
                        if failed_driver_at is None:
                            failed_driver_at = sim_time
                        if sim_time - failed_driver_at < 1.:
                            continue
                    break
        results.update(physics_duration_s=rows[-1]["physics_time_s"], policy_steps=len(rows), physics_steps=robot.steps,
            goal_sent=goal_sent, sensor_frames=len(clouds), wall_s=time.monotonic() - started,
            displacement_xyz_m=(np.array(rows[-1]["body_sensor"]["position"]) - np.array(rows[0]["body_sensor"]["position"])).tolist(),
            max_command_norm=max(float(np.linalg.norm(r["command"])) for r in rows),
            nonzero_command_steps=sum(np.linalg.norm(r["command"]) > .001 for r in rows),
            last_backend=last_backend, last_http_error=last_http_error,
            command_transport=asdict(commands.stats()), telemetry_transport=asdict(telemetry.stats()),
            final_command_reason=last_snapshot.reason, final_command_stale=last_snapshot.stale,
            claim="Actual Newton physics + geometric sensing + original native ROS graph; outcome requires artifact review")
        if request["probe"]:
            results["probe_passed"] = bool(last_backend and last_backend["readiness"]["body_pose_ready"]
                and last_backend["readiness"]["applied_snapshot"].get("ready") and commands.stats().frames_received > 10
                and telemetry.stats().frames_sent > 100)
        (out / "result.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps({k: v for k, v in results.items() if k != "last_backend"}, indent=2), flush=True)
        if request["probe"] and not results["probe_passed"]:
            raise RuntimeError("Native bridge probe did not meet its data/freshness gate")
    finally:
        (out / "video_states.json").write_text(json.dumps(video_states) + "\n")
        (out / "sensor_manifest.json").write_text(json.dumps(clouds, indent=2) + "\n")
        commands.stop()
        telemetry.stop()
        clock.stop()


if __name__ == "__main__":
    main()
