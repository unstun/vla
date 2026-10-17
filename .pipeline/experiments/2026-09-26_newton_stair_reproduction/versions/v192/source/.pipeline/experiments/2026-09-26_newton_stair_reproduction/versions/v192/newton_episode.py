"""Actual Newton physics/sensing with commands from the archived native graph."""
from dataclasses import asdict
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import gc
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

import sys
sys.path[:0] = [str(Path(__file__).resolve().parent),
                str(Path(__file__).resolve().parents[1] / "v40/physics"),
                str(Path(__file__).resolve().parents[2] / "scripts")]

from bridge_adapter import DomainCommandState
from clock_sync import ClockClient, ClockUnavailable
from scene_assets import BASE, OfficialHuman, verify_inputs
from robot_scene_v40 import StairRobot
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
    if request.get("scene") in ("flat_static", "flat_box", "flat_empty_long"):
        from flat_scene import FlatSceneRobot, FlatStaticHuman
        human = FlatStaticHuman(out) if request["scene"] == "flat_static" else None
        robot = FlatSceneRobot(human, obstacle_kind={"flat_box": "box", "flat_static": "human", "flat_empty_long": "none"}[request["scene"]],
                               startup_mode=request.get("startup_mode", "policy"), stance_hold=request.get("stance_hold", False),
                               native_cpu=request.get("physics_backend") == "native",
                               scenario=json.loads((out / "inputs/stair_scenario.json").read_text()))
    elif request.get("scene") == "building_full":
        robot = StairRobot(startup_mode=request["startup_mode"], stance_hold=True, model_device="cpu", use_solver_graph=True,
                           automatic_contact_capacity=True,
                           scenario=json.loads((out / "inputs/stair_scenario.json").read_text()))
        human = None
    else:
        robot = StairRobot()
        human = OfficialHuman(out)
    from realtime_pacer import NativeClockPacer
    pacer = None
    original_motor_substep = robot._motor_substep
    def paced_motor_substep(*args, **kwargs):
        value = original_motor_substep(*args, **kwargs)
        if robot.solver._step != robot.steps:
            raise RuntimeError("Captured solver counter differs from actual physical integrations")
        pacer.wait(robot.physics_time())
        return value
    robot._motor_substep = paced_motor_substep
    lidar = GeometricLidar(robot, human, emitter_self_exclusion=True,
                           visible_human_only=request.get("geometry_obstacles", False))
    # Compile sensor kernels before the timed episode. Do not publish this
    # captured-state probe, advance physics, or consume a sensor sequence.
    if request.get("async_sensor_evidence", False):
        before = robot.state.body_q.numpy().copy()
        before_time, before_steps = robot.physics_time(), robot.steps
        captured = robot.model.state()
        captured.body_q.assign(robot.state.body_q)
        pose = robot.body_and_sensor()
        cold = lidar.scan(0, 0.0, override_pose=pose, captured_state=captured)
        warm = lidar.scan(0, 0.0, override_pose=pose, captured_state=captured)
        assert np.array_equal(cold[0], warm[0]) and np.array_equal(cold[1], warm[1])
        assert np.array_equal(before, robot.state.body_q.numpy())
        assert (before_time, before_steps) == (robot.physics_time(), robot.steps)
        atomic_json(out / "sensor_warmup.json", {
            "cold_wall_s": cold[2]["wall_s"], "warm_wall_s": warm[2]["wall_s"],
            "points": len(warm[0]), "payload_equal": True, "physics_unchanged": True,
            "published": False, "sensor_sequence_consumed": False})
    (out / "clouds").mkdir()
    clock = ClockClient("127.0.0.1", 24602, out / "clock_samples.jsonl")
    state = DomainCommandState(clock, CommandLimits(1., .35, 1., 1.))
    commands = CommandReceiverServer(state, "127.0.0.1", 24601)
    telemetry = TelemetryPublisherServer("127.0.0.1", 24600, priority_send=True)
    clock.start()
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
    asynchronous = request.get("async_sensor_evidence", False)
    if asynchronous and (human is not None or request.get("scene") not in ("flat_empty_long", "building_full")):
        raise ValueError("Captured-state sensing requires a static scene without an animated actor")

    def publish(kind, stamp, payload):
        nonlocal wire_sequence
        wire_sequence += 1
        return telemetry.publish(encode_frame(kind, wire_sequence, stamp, payload))

    def publish_body(pose, stamp, sequence):
        body = BodyStateV2(tuple(pose["position"]), tuple(pose["quaternion"][1:] + pose["quaternion"][:1]),
            tuple(pose["linear_world"]), tuple(pose["angular_world"]),
            tuple(pose["linear_body"]), tuple(pose["angular_body"]), stamp, sequence, epoch)
        publish(MessageType.BODY_STATE_V2, stamp, encode_body_state_v2_payload(body))

    def physical_body_observer(current_robot):
        # Publish freshly integrated poses within each 20 ms control interval.
        # A slower-than-real-time CPU step must not withhold all localization
        # until the complete policy interval. Never repeat/restamp an old pose.
        if current_robot.steps % request.get("body_publish_substeps", 20) == 0:
            publish_body(current_robot.body_and_sensor(), round(current_robot.physics_time()*1e9), current_robot.steps)

    try:
        pacer = NativeClockPacer(robot.physics_time())
        if robot.startup_mode == "factory_pd":
            from initial_frame_v142 import initialize
            video_states.extend(initialize(robot, out))
        estimate = clock.wait_ready(30)
        commands.start()
        telemetry.start()
        if request.get("body_publish_substeps", 20) < 20:
            robot.physics_observer = physical_body_observer
        (out / "initial_clock.json").write_text(json.dumps(asdict(estimate), indent=2) + "\n")
        atomic_json(out / "startup_pacing.json", pacer.snapshot(robot.physics_time()))
        # The 1:1 navigation video starts from the measured initialized state.
        # Factory execution remains separately timed; native ROS time is continuous.
        pacer = NativeClockPacer(robot.physics_time())
        atomic_json(out / "navigation_clock_anchor.json", pacer.snapshot(robot.physics_time()))
        with (out / "telemetry.jsonl").open("w") as log, (out / "sensor.jsonl").open("w") as sensor_log, (out / "backend_states.jsonl").open("w") as backend_log, ThreadPoolExecutor(max_workers=1) as writer, ThreadPoolExecutor(max_workers=1) as scanner:
            io_jobs, pending_scan = deque(), None
            scan_index = 0

            def save_line(stream, value):
                stream.write(json.dumps(value)+"\n")
                stream.flush()

            def record(function, *arguments):
                if asynchronous:
                    io_jobs.append(writer.submit(function, *arguments))
                else:
                    function(*arguments)

            def save_cloud(points, world, item):
                path = out / item["file"]
                np.savez_compressed(path, sensor_points=points, world_points=world)
                item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                save_line(sensor_log, item)

            def publish_scan(data, index, captured_pose, captured_time):
                points, world, info, actor, _ = data
                capture_stamp = round(captured_time*1e9)
                raw = points.astype(">f4").tobytes()
                sensor = DualCloudSensorFrameV1(tuple(captured_pose["position"]),
                    tuple(captured_pose["quaternion"][1:]+captured_pose["quaternion"][:1]),
                    tuple(captured_pose["sensor_position"]),
                    tuple(captured_pose["sensor_quaternion"][1:]+captured_pose["sensor_quaternion"][:1]),
                    config_hash, index+1, len(points), raw, len(points), raw, 0, 0)
                publish(MessageType.SENSOR_FRAME_DUAL_CLOUD_V1, capture_stamp, encode_dual_cloud_sensor_payload(sensor))
                item = {"sim_time_s": captured_time, "stamp_ns": capture_stamp, "body_sensor": captured_pose,
                        "sensor": info, "actor_scoring_only": actor, "file": f"clouds/{index:05d}.npz",
                        "published_at_physics_s": robot.physics_time()}
                clouds.append(item)
                record(save_cloud, points, world, item)

            steps = round((request["max_physics_s"] - robot.physics_time()) / .02)
            # v32: collect, then move the surviving start-up heap out of the cyclic collector's reach.
            # Logged full collections in this worker took 99-176 ms, holding the GIL throughout
            # (audits/2026-09-29_wall_clock_chain). No computation changes.
            gc.collect()
            gc.freeze()
            for step in range(steps):
                control_loop_started = time.monotonic()
                while io_jobs and io_jobs[0].done():
                    io_jobs.popleft().result()
                if len(io_jobs) > 256:
                    raise RuntimeError("Evidence writer backlog exceeds its declared bound")
                finish = None
                if (out / "native_failure.json").exists():
                    raise RuntimeError((out / "native_failure.json").read_text())
                if time.monotonic() - started > request["max_worker_wall_s"] - 30:
                    raise TimeoutError("Local episode wall deadline")
                snapshot, remote_source, wire_command = state.current(time.monotonic_ns())
                command = (snapshot.command.vx, snapshot.command.vy, snapshot.command.wz)
                step_started = time.monotonic_ns()
                robot.step(command)
                physics_finished = time.monotonic_ns()
                row = robot.telemetry()
                row["realtime_pacing"] = pacer.snapshot(robot.physics_time())
                requested_command = command
                command = tuple(row["effective_command"])
                if hasattr(robot, "actor_contact_count"):
                    row["actor_contacts_scoring_only"] = robot.actor_contact_count()
                    row["obstacle_contact_scoring_only"] = dict(robot.contact_scoring)
                pose = robot.body_and_sensor()
                sim_time = row["physics_time_s"]
                stamp = round(sim_time * 1e9)
                if robot.physics_observer is None:
                    publish_body(pose, stamp, step+1)
                row.update(command=list(command), requested_command=list(requested_command),
                           command_sequence=snapshot.sequence, command_stale=snapshot.stale,
                           command_reason=snapshot.reason, command_source_timestamp_linux_ns=remote_source,
                           wall_s=time.monotonic() - started, body_sensor=pose, state_sequence=step + 1)
                row["control_wall_s"] = (physics_finished-step_started)/1e9
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
                        "raw_command": asdict(wire_command),
                        "admitted_command": dict(zip(("vx", "vy", "wz"), requested_command)), "applied_command": cmd_dict,
                        "control": {"startup_mode": robot.startup_mode, "phase": row["controller_phase"],
                            "stance_mode": row.get("stance_mode", "OFF"),
                            "policy_owns_joints": row.get("policy_owns_joints", True),
                            "navigation_ready": robot.navigation_ready, "policy_observation_valid": robot.policy_calls > 0},
                        "freshness": {"max_reader_age_s": 2., "atomic_replace": True},
                        "state_epoch": {"state_sequence": step + 1, "telemetry_sequence": wire_sequence},
                        "measured": {"horizontal_speed_mps": float(np.linalg.norm(pose["linear_world"][:2])),
                          "yaw_rate_radps": pose["angular_body"][2], "base_xyz": pose["position"],
                          "base_quat_wxyz": pose["quaternion"],
                          "command_obs_error": float(np.max(np.abs(np.asarray(row["observation"])[6:9] - command)))},
                        "clock_mapping": asdict(estimate), "host_step_started_monotonic_ns": step_started}
                    # The v1 applied-state schema requires a real policy-observation
                    # error. During PD-only startup no such observation exists;
                    # keep readiness missing rather than publish a fabricated zero.
                    if robot.policy_calls > 0:
                        # The existing ordered writer keeps VirtioFS writes out
                        # of the 20 ms physics/control interval.
                        record(atomic_json, external / "current_command.json", applied)
                except ClockUnavailable:
                    row["applied_snapshot_not_refreshed"] = "clock_unsynchronized"
                if pending_scan is not None and pending_scan[0].done():
                    future, index, captured_pose, captured_time = pending_scan
                    publish_scan(future.result(), index, captured_pose, captured_time)
                    pending_scan = None
                if (step + 1) % 5 == 0:
                    actor_time = 0.0 if request.get("static_human", False) else sim_time
                    if asynchronous:
                        if pending_scan is not None:
                            raise RuntimeError("Captured scan did not finish before the next sensor period")
                        captured_state = robot.model.state()
                        captured_state.body_q.assign(robot.state.body_q)
                        future = scanner.submit(lidar.scan, scan_index, actor_time, override_pose=pose, captured_state=captured_state)
                        pending_scan = (future, scan_index, pose, sim_time)
                    else:
                        publish_scan(lidar.scan(scan_index, actor_time), scan_index, pose, sim_time)
                    scan_index += 1
                    try:
                        last_backend = json.loads((out / "backend_latest.json").read_text())
                        goal_sent = bool(last_backend.get("jobs"))
                        last_http_error = None
                        record(save_line, backend_log, {"sim_time_s": sim_time, "data": last_backend})
                    except Exception as error:
                        last_http_error = str(error)
                if (step + 1) % 1 == 0:
                    video_states.append({"wall_monotonic_s": time.monotonic(), "physics_time_s": sim_time, "body_q": robot.state.body_q.numpy().tolist(),
                        "joint_q": row["joint_q"], "command": list(command), "command_reason": snapshot.reason,
                        "controller_phase": row["controller_phase"], "policy_calls": robot.policy_calls,
                        "stance_mode": row.get("stance_mode", "OFF"),
                        "policy_owns_joints": row.get("policy_owns_joints", True),
                        "navigation_ready": robot.navigation_ready,
                        "goal_sent": goal_sent, "last_backend_error": None if last_backend is None else last_backend["readiness"]["last_error"]})
                record(save_line, log, row)
                rows.append(row)
                last_snapshot = snapshot
                # v32: each second of simulation, collect the garbage it left (such as each scan's discarded
                # kernel objects), then freeze the survivors, so a collection covers one second of objects.
                if (step + 1) % 50 == 0:
                    gc.collect()
                    gc.freeze()
                if row["base_up_z"] < .5:
                    state.latch_case_failure("fallen")
                    results["fallen"] = True
                    break
                if (step + 1) % 50 == 0:
                    print(json.dumps({"sim": sim_time, "command": command, "reason": snapshot.reason,
                         "base": pose["position"], "backend_error": last_http_error,
                         "goal_sent": goal_sent}), flush=True)
                finish_path = external / "finish_request.json"
                if finish_path.exists():
                    finish = json.loads(finish_path.read_text())
                if not request["probe"] and finish is not None:
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
                # Every real 1 ms integration was already paced against the
                # absolute native-clock deadline; no relative policy sleep.
            if pending_scan is not None:
                future, index, captured_pose, captured_time = pending_scan
                publish_scan(future.result(timeout=2.), index, captured_pose, captured_time)
            for future in io_jobs:
                future.result(timeout=10.)
        results["realtime_pacing"] = pacer.snapshot(robot.physics_time())
        results["recording_preview"] = bool(request.get("recording_preview"))
        results.update(physics_duration_s=rows[-1]["physics_time_s"], policy_steps=robot.policy_calls,
            control_steps=len(rows), physics_steps=robot.steps, startup_mode=robot.startup_mode,
            goal_sent=goal_sent, sensor_frames=len(clouds), wall_s=time.monotonic() - started,
            displacement_xyz_m=(np.array(rows[-1]["body_sensor"]["position"]) - np.array(rows[0]["body_sensor"]["position"])).tolist(),
            max_command_norm=max(float(np.linalg.norm(r["command"])) for r in rows),
            nonzero_command_steps=sum(int(np.linalg.norm(r["command"]) > .001) for r in rows),
            last_backend=last_backend, last_http_error=last_http_error,
            command_transport=asdict(commands.stats()), telemetry_transport=asdict(telemetry.stats()),
            final_command_reason=last_snapshot.reason, final_command_stale=last_snapshot.stale,
            claim="Actual Newton physics and geometric sensing with the selected native build/configuration; outcome requires artifact review")
        if request["probe"]:
            health = json.loads((out / "artifacts/runtime_health.json").read_text())
            results["sensor_health"] = health
            stamps = health["stamps_ns"]
            sensor_ready = (all(stamps.get(key, 0) > 0 for key in ("cloud", "lidar_pose", "pct_tomogram"))
                            and stamps["cloud"] == stamps["lidar_pose"])
            if not request.get("geometry_obstacles", False):
                sensor_ready = (sensor_ready and health["tracks_complete"]
                    and health["track_source_id"] == robot.scenario["track_source_id"]
                    and all(stamps.get(key, 0) > 0 for key in ("tracker_ground", "tracked_person_snapshot")))
            results["sensor_readiness_mode"] = ("geometry_only" if request.get("geometry_obstacles", False)
                                                else "archived_person_tracking")
            results["probe_passed"] = bool(last_backend and last_backend["readiness"]["body_pose_ready"]
                and last_backend["readiness"]["applied_snapshot"].get("ready") and commands.stats().frames_received > 10
                and telemetry.stats().frames_sent > 100 and sensor_ready)
        (out / "result.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps({k: v for k, v in results.items() if k != "last_backend"}, indent=2), flush=True)
        if request["probe"] and not results["probe_passed"]:
            raise RuntimeError("Native bridge probe did not meet its data/freshness gate")
        if not request.get("recording_preview") and request.get("scene") in ("flat_empty_long", "building_full") and results.get("finish_request", {}).get("backend_terminal_status") != "FINISHED":
            raise RuntimeError("Long route did not finish; original outcome is retained in result.json")
    finally:
        if pacer is not None:
            atomic_json(out / "realtime_pacing.json", pacer.snapshot(robot.physics_time()))
        if robot.startup is not None:
            (out / "startup_events.json").write_text(json.dumps(robot.startup.events, indent=2) + "\n")
        if robot.stance is not None:
            (out / "stance_status.json").write_text(json.dumps(robot.stance.status(), indent=2) + "\n")
        (out / "video_states.json").write_text(json.dumps(video_states) + "\n")
        (out / "sensor_manifest.json").write_text(json.dumps(clouds, indent=2) + "\n")
        commands.stop()
        telemetry.stop()
        clock.stop()


if __name__ == "__main__":
    main()
